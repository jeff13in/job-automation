from pathlib import Path

import pytest

from stack import gmail
from stack.applier.answers import Field, decide
from stack.finder import simplify
from stack.finder.run import skip_reason
from stack.listener.run import apply_outcome, candidates
from stack.models import Role, Status, normalize_url, role_id
from stack.resumes import tailor
from stack.sheet import CsvStore

FIXTURE = """
## 💻 Software Engineering Internship Roles

<table>
<thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr></thead>
<tbody>
<tr>
<td>🔥 <strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td>
<td>Software Engineer Intern</td>
<td><details><summary><strong>2 locations</strong></summary>Toronto, ON, Canada<br>SF</details></td>
<td><div align="center"><a href="https://boards.greenhouse.io/acme/jobs/1?utm_source=Simplify&ref=Simplify"><img alt="Apply"></a> <a href="https://simplify.jobs/p/x"><img alt="Simplify"></a></div></td>
<td>0d</td>
</tr>
<tr>
<td>↳</td>
<td>Security Intern 🛂</td>
<td>Austin, TX</td>
<td><div align="center"><a href="https://jobs.lever.co/acme/2"><img alt="Apply"></a></div></td>
<td>2d</td>
</tr>
<tr>
<td><strong>Beta</strong></td>
<td>ML Intern</td>
<td>Remote in Canada</td>
<td>🔒</td>
<td>1mo</td>
</tr>
</tbody>
</table>

## 📱 Product Management Internship Roles
<table><tbody><tr><td>X</td><td>PM Intern</td><td>NYC</td><td><a href="https://x.com/1">a</a></td><td>0d</td></tr></tbody></table>
"""

FINDER_CFG = {"max_age_days": 3, "locations": ["Canada", ", ON", "Remote"],
              "skip_flags": {"no_sponsorship": True, "us_citizenship": True, "advanced_degree": True}}


def test_url_normalization_strips_tracking():
    a = "https://boards.greenhouse.io/acme/jobs/1?utm_source=Simplify&ref=Simplify"
    assert normalize_url(a) == "https://boards.greenhouse.io/acme/jobs/1"
    assert role_id(a) == role_id("https://BOARDS.greenhouse.io/acme/jobs/1/")


def test_simplify_parse():
    rows = simplify.parse(FIXTURE, ["Software Engineering"])
    assert [r.company for r in rows] == ["Acme", "Acme", "Beta"]      # ↳ inherits company
    acme, sec, beta = rows
    assert acme.locations == ["Toronto, ON, Canada", "SF"]
    assert "faang" in acme.flags and acme.age_days == 0
    assert sec.role == "Security Intern" and "no_sponsorship" in sec.flags
    assert "closed" in beta.flags and beta.age_days == 30


def test_skip_reasons():
    acme, sec, beta = simplify.parse(FIXTURE, ["Software Engineering"])
    assert skip_reason(acme, FINDER_CFG) is None
    assert skip_reason(sec, FINDER_CFG) == "location"
    assert skip_reason(beta, FINDER_CFG) == "closed"


def test_csv_store_dedupes_and_queues(tmp_path):
    s = CsvStore(tmp_path / "a.csv")
    r1 = Role("Acme", "SWE Intern", "https://x.io/1?utm_source=a")
    r2 = Role("Beta", "ML Intern", "https://x.io/2")
    assert len(s.add_new([r1, r2])) == 2
    assert len(s.add_new([Role("Acme", "SWE Intern", "https://x.io/1")])) == 0
    got = s.claim_next()
    assert got.status == "in_progress"
    s.block(got.id, "captcha")
    blocked = s.by_status(Status.BLOCKED)
    assert blocked[0].blocked_reason == "captcha"
    s.set_status(got.id, Status.APPLIED)
    assert s.by_status(Status.APPLIED)[0].blocked_reason == ""


@pytest.mark.parametrize("text,code", [
    ("Your Greenhouse security code is: 482913", "482913"),
    ("Enter the code below to continue\n\nAB12CD", "AB12CD"),
    ("Verification code\n730 211", None),
    ("Use 551203 to verify your email", "551203"),
])
def test_extract_code(text, code):
    assert gmail.extract_code(text) == code


PROFILE = {"fields": {"first_name": "Jeffin", "last_name": "S", "email": "a@b.co", "phone": "TODO"},
           "answers": [{"pattern": "how did you hear", "answer": "Online job board"},
                       {"pattern": "authori[sz]ed to work in canada", "answer": "Yes"}]}


@pytest.mark.parametrize("label,kind,req,options,action", [
    ("First Name *", "text", True, [], "fill"),
    ("Phone", "tel", True, [], "block"),                       # profile value is still TODO
    ("Phone", "tel", False, [], "skip"),
    ("Resume/CV", "file", True, [], "upload"),
    ("Will you now or in the future require visa sponsorship?", "select", True, ["Yes", "No"], "block"),
    ("Are you legally authorized to work in Canada?", "select", True, ["Yes", "No"], "fill"),
    ("How did you hear about us?", "select", False, ["Online job board", "Referral"], "fill"),
    ("Gender", "select", False, ["Male", "Female"], "skip"),
    ("Why do you want to work at Acme?", "textarea", True, [], "fill"),
    ("Pick a team", "select", True, ["A", "B"], "block"),
])
def test_decide(label, kind, req, options, action):
    assert decide(Field("0", kind, label, req, options), PROFILE).action == action


def test_tailor_validator_catches_fabrication():
    master = tailor.load_master()
    ok = tailor.variant_plan(master, tailor.load_variant("backend"))
    assert tailor.validate(ok, master) == []
    bad = {"sections": [{"name": "experience", "entries": [
        {"id": "meritrium", "bullets": [{"from": "meritrium-1", "text": "Cut latency 40% for 10k users"},
                                        {"from": "made-up", "text": "x"}]},
        {"id": "google", "bullets": []}]}],
        "skills": ["Python", "Kubernetes"]}
    problems = " | ".join(tailor.validate(bad, master))
    assert "adds numbers" in problems and "made-up" in problems
    assert "google" in problems and "Kubernetes" in problems


def test_variant_pdf_renders(tmp_path):
    master = tailor.load_master()
    html = tailor.render_html(master, tailor.variant_plan(master, tailor.load_variant("security")))
    out = tailor.render_pdf(html, tmp_path / "r.pdf")
    assert out.read_bytes()[:4] == b"%PDF"


def test_listener_matching_and_outcomes(tmp_path):
    s = CsvStore(tmp_path / "a.csv")
    a = Role("Acme Corp", "SWE Intern", "https://x.io/1", status="applied")
    b = Role("Beta", "ML Intern", "https://x.io/2", status="applied")
    s.add_new([a, b])
    mail = gmail.Mail("m", "t1", "no-reply@greenhouse-mail.io", "Acme Corp Hiring",
                      "Your application to Acme Corp", 0, "Thanks for applying...", "")
    assert [r.company for r in candidates(mail, s.all())] == ["Acme Corp"]
    assert apply_outcome(s, a, "assessment", "HackerRank due Oct 20", "t1") == "oa"
    row = next(r for r in s.all() if r.id == a.id)
    assert row.status == "oa" and row.blocked_reason.startswith("take the assessment")
    # a late confirmation must not roll an OA back to applied
    assert apply_outcome(s, row, "confirmation", "received", "t1") is None
    apply_outcome(s, row, "rejection", "not moving forward", "t1")
    assert next(r for r in s.all() if r.id == a.id).blocked_reason == ""
