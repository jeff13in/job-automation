"""Greenhouse job board API — keyless, one board token per company.

GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
"""

from __future__ import annotations

from datetime import datetime

from ..http import get_json
from ..models import Job

BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def url_for(token: str) -> str:
    return BASE.format(token=token)


def parse(company: str, payload: dict) -> list[Job]:
    jobs: list[Job] = []
    for j in payload.get("jobs", []) or []:
        loc = (j.get("location") or {}).get("name", "")
        depts = j.get("departments") or []
        dept = depts[0].get("name", "") if depts else ""
        posted = j.get("first_published") or j.get("updated_at") or ""
        if posted:
            posted = posted[:10]
        jobs.append(
            Job(
                company=company,
                title=j.get("title", ""),
                url=j.get("absolute_url", ""),
                location=loc,
                department=dept,
                posted_at=posted,
                description=j.get("content", "") or "",
                source="greenhouse",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    token = partner["token"]
    payload = get_json(url_for(token), params={"content": "true"})
    return parse(partner["name"], payload)
