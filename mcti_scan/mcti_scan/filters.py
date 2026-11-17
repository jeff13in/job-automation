"""Relevance scoring: turn a few hundred raw postings into a shortlist.

Scoring is additive and transparent — every job carries the tags that earned
its score, so a shortlist that looks wrong tells you which rule to change
instead of leaving you guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Job

# --- role families worth applying to -------------------------------------
ROLE_KEYWORDS: dict[str, int] = {
    # security
    "security": 18, "cyber": 20, "soc ": 18, "threat": 16, "incident response": 16,
    "penetration test": 20, "pentest": 20, "vulnerability": 16, "appsec": 18,
    "application security": 18, "detection": 12, "forensic": 14, "grc": 10,
    "identity": 10, "iam": 10, "red team": 16, "blue team": 16, "malware": 14,
    # software / backend / AI — his stated focus
    "software": 16, "developer": 16, "engineer": 14, "backend": 18, "back-end": 18,
    "full stack": 14, "full-stack": 14, "python": 14, "api": 8, "platform": 10,
    "machine learning": 14, "ml ": 10, "artificial intelligence": 14, "ai ": 10,
    "llm": 16, "data engineer": 12,
    # devops / cloud / qa
    "devops": 16, "site reliability": 14, "sre": 14, "cloud": 12, "infrastructure": 10,
    "automation": 12, "qa ": 12, "quality assurance": 12, "test engineer": 12,
    # analyst-track entry points
    "analyst": 10, "technical support": 6, "it support": 6,
}

# --- seniority: entry-level boosts, senior roles pushed out ---------------
LEVEL_BOOST: dict[str, int] = {
    "intern": 30, "internship": 30, "co-op": 30, "coop": 30, "student": 25,
    "new grad": 30, "new graduate": 30, "campus": 20, "junior": 22, "jr ": 18,
    "entry level": 25, "entry-level": 25, "associate": 10, "i ": 0, "tier 1": 14,
    "graduate program": 25, "rotational": 14, "trainee": 20,
}

SENIOR_PENALTY: dict[str, int] = {
    "senior": -30, "sr.": -30, "sr ": -30, "staff ": -28, "principal": -35,
    "lead ": -22, "manager": -35, "director": -45, "vp ": -50, "head of": -45,
    "chief": -50, "architect": -28, "executive": -35, "president": -50,
    "distinguished": -40, "fellow": -30, "ii i": 0,
}

# Roles that are never a fit regardless of keywords.
HARD_EXCLUDE = (
    "sales", "account executive", "account manager", "business development",
    "sdr", "bdr", "territory", "channel", "partner manager", "quota",
    "marketing", "brand", "content writer", "copywriter", "social media",
    "recruiter", "talent acquisition", "human resources", "hr ", "payroll",
    "benefits", "accountant", "accounting", "tax ", "audit manager",
    "controller", "bookkeep", "legal counsel", "paralegal", "attorney",
    "receptionist", "administrative assistant", "executive assistant",
    "facilities", "janitor", "driver", "warehouse", "retail", "cashier",
    "store ", "nurse", "underwriter", "mortgage", "teller", "actuar",
    "insurance advisor", "claims adjuster", "financial advisor",
    "portfolio manager", "investment analyst", "wealth",
)

# --- geography ------------------------------------------------------------
PREFERRED_LOCATIONS: dict[str, int] = {
    "guelph": 30, "kitchener": 22, "waterloo": 22, "cambridge, on": 18,
    "toronto": 25, "mississauga": 20, "brampton": 16, "markham": 16,
    "vaughan": 14, "oakville": 14, "burlington": 14, "hamilton": 16,
    "niagara": 22, "st. catharines": 20, "ontario": 14, "ottawa": 10,
    "remote": 18, "canada": 8, "hybrid": 4,
}

# Locations that disqualify outright unless the posting is also remote-Canada.
FOREIGN_MARKERS = (
    "united states", "usa", ", us", "california", "texas", "new york",
    "minnesota", "eden prairie", "virginia", "washington", "colorado",
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "ireland",
    "cork", "dublin", "united kingdom", "london, u", "newcastle",
    "germany", "france", "singapore", "australia", "japan", "brazil",
    "mexico", "poland", "romania", "netherlands", "sweden", "israel",
)

CANADA_MARKERS = ("canada", "ontario", ", on", "toronto", "guelph", "waterloo",
                  "kitchener", "ottawa", "montreal", "vancouver", "calgary")


@dataclass
class FilterConfig:
    min_score: int = 25
    require_canada: bool = True
    allow_remote_anywhere: bool = False
    extra_keywords: dict[str, int] = field(default_factory=dict)
    extra_excludes: tuple[str, ...] = ()


def _hits(blob: str, table: dict[str, int]) -> list[tuple[str, int]]:
    return [(k.strip(), v) for k, v in table.items() if k in blob and v]


def location_ok(job: Job, cfg: FilterConfig) -> bool:
    if not cfg.require_canada:
        return True
    loc = job.location.lower()
    if not loc:
        # No location given: keep it and let a human judge rather than silently dropping.
        return True
    is_remote = "remote" in loc or "anywhere" in loc
    if any(m in loc for m in CANADA_MARKERS):
        return True
    if is_remote and cfg.allow_remote_anywhere:
        return True
    if any(m in loc for m in FOREIGN_MARKERS):
        return False
    # Unrecognized location string — keep, flag later.
    return True


def score(job: Job, cfg: FilterConfig | None = None) -> Job:
    cfg = cfg or FilterConfig()
    title = job.title.lower()
    blob = f" {title} {job.department.lower()} "
    loc = f" {job.location.lower()} "

    tags: list[str] = []
    total = 0

    for kw in HARD_EXCLUDE + cfg.extra_excludes:
        if kw in blob:
            job.score = -999
            job.tags = [f"excluded:{kw.strip()}"]
            return job

    roles = _hits(blob, {**ROLE_KEYWORDS, **cfg.extra_keywords})
    for name, pts in roles:
        total += pts
        tags.append(f"role:{name}")

    if not roles:
        job.score = -999
        job.tags = ["excluded:no-matching-role"]
        return job

    for name, pts in _hits(blob, LEVEL_BOOST):
        total += pts
        tags.append(f"level:{name}")

    for name, pts in _hits(blob, SENIOR_PENALTY):
        total += pts
        tags.append(f"senior:{name}")

    for name, pts in _hits(loc, PREFERRED_LOCATIONS):
        total += pts
        tags.append(f"loc:{name}")

    if not location_ok(job, cfg):
        total -= 60
        tags.append("loc:outside-canada")

    # Freshness nudge: a posting from this week is worth more than one from last quarter.
    if job.posted_at:
        tags.append(f"posted:{job.posted_at}")

    job.score = total
    job.tags = tags
    return job


def shortlist(jobs: list[Job], cfg: FilterConfig | None = None) -> list[Job]:
    cfg = cfg or FilterConfig()
    scored = [score(j, cfg) for j in jobs]
    keep = [j for j in scored if j.score >= cfg.min_score]
    keep.sort(key=lambda j: (-j.score, j.company, j.title))
    return keep


def dedupe(jobs: list[Job]) -> list[Job]:
    """Same role syndicated to two boards shows up once."""
    seen: dict[str, Job] = {}
    for j in jobs:
        prev = seen.get(j.key)
        if prev is None or len(j.description) > len(prev.description):
            seen[j.key] = j
    return list(seen.values())
