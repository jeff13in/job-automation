"""Offline tests: real ATS response shapes as fixtures, no network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcti_scan.adapters import greenhouse, lever, workday, jsonld   # noqa: E402
from mcti_scan.filters import FilterConfig, dedupe, score, shortlist  # noqa: E402
from mcti_scan.models import Job  # noqa: E402
from mcti_scan.state import SeenStore  # noqa: E402

# --------------------------------------------------------------------------
# adapter parsing
# --------------------------------------------------------------------------

GREENHOUSE = {
    "jobs": [
        {
            "id": 1,
            "title": "Security Engineering Intern",
            "absolute_url": "https://boards.greenhouse.io/x/jobs/1",
            "location": {"name": "Toronto, Ontario, Canada"},
            "departments": [{"name": "Security"}],
            "first_published": "2026-11-10T12:00:00Z",
            "content": "Work with the <b>detection</b> team.",
        }
    ]
}

LEVER = [
    {
        "text": "Software Developer Co-op (Winter 2027)",
        "hostedUrl": "https://jobs.lever.co/magnetforensics/abc",
        "categories": {"location": "Waterloo, ON", "team": "Engineering"},
        "createdAt": 1762000000000,
        "descriptionPlain": "Join our product team.",
    }
]

WORKDAY = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Junior Security Analyst",
            "externalPath": "/job/Waterloo-Ontario/Junior-Security-Analyst_123",
            "locationsText": "Waterloo, Ontario",
            "postedOn": "Posted 3 Days Ago",
        },
        {
            "title": "Director, Platform Engineering",
            "externalPath": "/job/Eden-Prairie/Director_456",
            "locationsText": "Eden Prairie, Minnesota",
            "postedOn": "Posted Today",
        },
    ],
}

JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"JobPosting","title":"Penetration Tester",
  "url":"https://isacybersecurity.com/jobs/pentest",
  "datePosted":"2026-11-14",
  "hiringOrganization":{"@type":"Organization","name":"ISA Cybersecurity"},
  "jobLocation":{"@type":"Place","address":{"addressLocality":"Toronto",
     "addressRegion":"ON","addressCountry":"CA"}},
  "description":"Identify and exploit vulnerabilities."}]}
</script></head><body></body></html>
"""


def test_greenhouse_parse():
    jobs = greenhouse.parse("Acme", GREENHOUSE)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.title == "Security Engineering Intern"
    assert j.location == "Toronto, Ontario, Canada"
    assert j.department == "Security"
    assert j.posted_at == "2026-11-10"
    assert "<b>" not in j.description and "detection" in j.description
    assert j.is_student_role


def test_lever_parse():
    jobs = lever.parse("Magnet Forensics", LEVER)
    j = jobs[0]
    assert j.location == "Waterloo, ON"
    # epoch-millis -> ISO date
    assert j.posted_at == "2025-11-01"
    assert j.is_student_role          # "Co-op" must be detected


def test_workday_parse_and_relative_dates():
    jobs = workday.parse("BlackBerry", WORKDAY, "bb.wd3.myworkdayjobs.com", "BlackBerry")
    assert len(jobs) == 2
    assert jobs[0].url == (
        "https://bb.wd3.myworkdayjobs.com/en-US/BlackBerry"
        "/job/Waterloo-Ontario/Junior-Security-Analyst_123"
    )
    assert jobs[0].posted_at and jobs[1].posted_at   # both resolve to real dates
    assert workday.approx_posted("Posted 30+ Days Ago")


def test_jsonld_extraction():
    postings = jsonld.extract_postings(JSONLD_HTML)
    assert len(postings) == 1
    jobs = jsonld.parse("ISA Cybersecurity", postings)
    assert jobs[0].title == "Penetration Tester"
    assert "Toronto" in jobs[0].location


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def test_student_security_role_in_ontario_scores_high():
    j = score(Job(company="X", title="Cybersecurity Co-op Student", url="u",
                  location="Guelph, Ontario"))
    assert j.score > 60


def test_senior_role_is_pushed_down():
    jr = score(Job(company="X", title="Security Analyst", url="u", location="Toronto, ON"))
    sr = score(Job(company="X", title="Senior Director, Security", url="u",
                   location="Toronto, ON"))
    assert sr.score < jr.score


def test_sales_and_hr_roles_are_excluded():
    for title in ("Account Executive - Enterprise", "Senior Talent Acquisition Partner",
                  "Commercial Underwriting Manager"):
        j = score(Job(company="X", title=title, url="u", location="Toronto, ON"))
        assert j.score == -999, title


def test_us_only_role_drops_out_of_shortlist():
    jobs = [
        Job(company="X", title="Security Analyst", url="u", location="Eden Prairie, Minnesota"),
        Job(company="X", title="Security Analyst", url="u", location="Toronto, Ontario"),
    ]
    picks = shortlist(jobs, FilterConfig(min_score=25))
    assert len(picks) == 1
    assert "Toronto" in picks[0].location


def test_remote_canada_is_kept():
    j = score(Job(company="X", title="Backend Developer", url="u", location="Remote - Canada"))
    assert j.score >= 25


def test_unrelated_role_excluded():
    j = score(Job(company="X", title="Registered Nurse", url="u", location="Guelph, ON"))
    assert j.score == -999


def test_dedupe_keeps_richest_copy():
    a = Job(company="eSentire", title="SOC Analyst", url="a", location="Waterloo, ON")
    b = Job(company="eSentire", title="SOC Analyst", url="b", location="Waterloo, ON",
            description="Long description with detail")
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].description


# --------------------------------------------------------------------------
# state / diffing
# --------------------------------------------------------------------------

def test_seen_store_reports_new_then_returning(tmp_path):
    path = tmp_path / "seen.json"
    jobs = [Job(company="X", title="Security Analyst", url="u", location="Toronto, ON")]

    store = SeenStore(path)
    new, old = store.mark(jobs)
    assert len(new) == 1 and not old
    store.save()

    store2 = SeenStore(path)
    new2, old2 = store2.mark(jobs)
    assert not new2 and len(old2) == 1
    assert old2[0].first_seen == new[0].first_seen


def test_corrupt_state_does_not_crash(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{not json")
    store = SeenStore(path)
    assert len(store) == 0
    assert path.with_suffix(".corrupt.json").exists()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
