"""Lever postings API — keyless.

GET https://api.lever.co/v0/postings/{token}?mode=json
Confirmed in use by Magnet Forensics (jobs.lever.co/magnetforensics).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..http import get_json
from ..models import Job

BASE = "https://api.lever.co/v0/postings/{token}"


def url_for(token: str) -> str:
    return BASE.format(token=token)


def parse(company: str, payload: list) -> list[Job]:
    jobs: list[Job] = []
    for j in payload or []:
        cats = j.get("categories") or {}
        posted = ""
        ms = j.get("createdAt")
        if isinstance(ms, (int, float)):
            posted = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()
        jobs.append(
            Job(
                company=company,
                title=j.get("text", ""),
                url=j.get("hostedUrl", "") or j.get("applyUrl", ""),
                location=cats.get("location", "") or "",
                department=cats.get("team", "") or cats.get("department", "") or "",
                posted_at=posted,
                description=j.get("descriptionPlain", "") or j.get("description", "") or "",
                source="lever",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    payload = get_json(url_for(partner["token"]), params={"mode": "json"})
    return parse(partner["name"], payload)
