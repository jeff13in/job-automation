"""Recruitee public offers API — keyless.

GET https://{token}.recruitee.com/api/offers/
"""

from __future__ import annotations

from ..http import get_json
from ..models import Job

BASE = "https://{token}.recruitee.com/api/offers/"


def url_for(token: str) -> str:
    return BASE.format(token=token)


def parse(company: str, payload: dict) -> list[Job]:
    jobs: list[Job] = []
    for j in payload.get("offers", []) or []:
        location = ", ".join(
            p for p in (j.get("city"), j.get("state_name"), j.get("country_code")) if p
        )
        jobs.append(
            Job(
                company=company,
                title=j.get("title", ""),
                url=j.get("careers_url", "") or j.get("careers_apply_url", ""),
                location=location,
                department=j.get("department", "") or "",
                posted_at=(j.get("published_at") or "")[:10],
                description=j.get("description", "") or "",
                source="recruitee",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    payload = get_json(url_for(partner["token"]))
    return parse(partner["name"], payload)
