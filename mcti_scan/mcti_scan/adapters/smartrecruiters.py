"""SmartRecruiters public postings API — keyless, paginated.

GET https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100&offset=N
"""

from __future__ import annotations

from ..http import get_json
from ..models import Job

BASE = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
PAGE = 100
MAX_PAGES = 12


def url_for(token: str) -> str:
    return BASE.format(token=token)


def _location(j: dict) -> str:
    loc = j.get("location") or {}
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    s = ", ".join(p for p in parts if p)
    if loc.get("remote"):
        s = f"{s} (Remote)".strip()
    return s


def parse(company: str, items: list) -> list[Job]:
    jobs: list[Job] = []
    for j in items or []:
        dept = (j.get("department") or {}).get("label", "") or (
            j.get("function") or {}
        ).get("label", "")
        jobs.append(
            Job(
                company=company,
                title=j.get("name", ""),
                url=j.get("ref", "") or j.get("applyUrl", "")
                or f"https://jobs.smartrecruiters.com/{j.get('id','')}",
                location=_location(j),
                department=dept,
                posted_at=(j.get("releasedDate") or "")[:10],
                source="smartrecruiters",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    token = partner["token"]
    out: list[Job] = []
    offset = 0
    for _ in range(MAX_PAGES):
        payload = get_json(url_for(token), params={"limit": PAGE, "offset": offset})
        items = payload.get("content", []) or []
        out.extend(parse(partner["name"], items))
        total = payload.get("totalFound", 0)
        offset += PAGE
        if offset >= total or not items:
            break
    return out
