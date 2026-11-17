"""Ashby job board API — keyless.

GET https://api.ashbyhq.com/posting-api/job-board/{token}
"""

from __future__ import annotations

from ..http import get_json
from ..models import Job

BASE = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def url_for(token: str) -> str:
    return BASE.format(token=token)


def parse(company: str, payload: dict) -> list[Job]:
    jobs: list[Job] = []
    for j in payload.get("jobs", []) or []:
        jobs.append(
            Job(
                company=company,
                title=j.get("title", ""),
                url=j.get("jobUrl", "") or j.get("applyUrl", ""),
                location=j.get("location", "") or "",
                department=j.get("department", "") or j.get("team", "") or "",
                posted_at=(j.get("publishedAt") or "")[:10],
                description=j.get("descriptionPlain", "") or "",
                source="ashby",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    payload = get_json(url_for(partner["token"]))
    return parse(partner["name"], payload)
