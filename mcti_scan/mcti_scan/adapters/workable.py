"""Workable public widget API — keyless.

GET https://apply.workable.com/api/v1/widget/accounts/{token}?details=true
"""

from __future__ import annotations

from ..http import get_json
from ..models import Job

BASE = "https://apply.workable.com/api/v1/widget/accounts/{token}"


def url_for(token: str) -> str:
    return BASE.format(token=token)


def parse(company: str, payload: dict) -> list[Job]:
    jobs: list[Job] = []
    for j in payload.get("jobs", []) or []:
        loc = j.get("location") or {}
        if isinstance(loc, dict):
            location = ", ".join(
                p for p in (loc.get("city"), loc.get("region"), loc.get("country")) if p
            )
        else:
            location = str(loc)
        jobs.append(
            Job(
                company=company,
                title=j.get("title", ""),
                url=j.get("url", "") or j.get("shortlink", ""),
                location=location,
                department=j.get("department", "") or "",
                posted_at=(j.get("published_on") or j.get("created_at") or "")[:10],
                description=j.get("description", "") or "",
                source="workable",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    payload = get_json(url_for(partner["token"]), params={"details": "true"})
    return parse(partner["name"], payload)
