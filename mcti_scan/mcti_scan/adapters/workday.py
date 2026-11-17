"""Workday CXS API — the one used by most large employers.

POST https://{host}/wday/cxs/{tenant}/{site}/jobs
     {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

Confirmed tenants: Arctic Wolf, BlackBerry (bb.wd3.myworkdayjobs.com/BlackBerry).

Two quirks worth knowing:
  * `limit` is capped at 20 server-side regardless of what you ask for.
  * `postedOn` is relative prose ("Posted 5 Days Ago"), not a date, so we
    convert it to an approximate ISO date rather than inventing precision.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from ..http import post_json
from ..models import Job

PAGE = 20
MAX_PAGES = 25


def api_url(host: str, tenant: str, site: str) -> str:
    return f"https://{host}/wday/cxs/{tenant}/{site}/jobs"


def job_url(host: str, site: str, external_path: str, locale: str = "en-US") -> str:
    if not external_path:
        return f"https://{host}/{locale}/{site}"
    return f"https://{host}/{locale}/{site}{external_path}"


_REL = re.compile(r"(\d+)\+?\s+(day|days|hour|hours|week|weeks|month|months)", re.I)


def approx_posted(text: str) -> str:
    """'Posted 5 Days Ago' -> ISO date. 'Posted Today' -> today."""
    if not text:
        return ""
    low = text.lower()
    today = date.today()
    if "today" in low:
        return today.isoformat()
    if "yesterday" in low:
        return (today - timedelta(days=1)).isoformat()
    m = _REL.search(low)
    if not m:
        return ""
    n = int(m.group(1))
    unit = m.group(2).rstrip("s")
    delta = {"hour": timedelta(hours=n), "day": timedelta(days=n),
             "week": timedelta(weeks=n), "month": timedelta(days=30 * n)}[unit]
    return (today - delta).isoformat()


def parse(company: str, payload: dict, host: str, site: str, locale: str = "en-US") -> list[Job]:
    jobs: list[Job] = []
    for j in payload.get("jobPostings", []) or []:
        jobs.append(
            Job(
                company=company,
                title=j.get("title", ""),
                url=job_url(host, site, j.get("externalPath", ""), locale),
                location=j.get("locationsText", "") or "",
                posted_at=approx_posted(j.get("postedOn", "")),
                source="workday",
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    host = partner["host"]
    site = partner["site"]
    # The tenant is the host's first label (bb.wd3.myworkdayjobs.com -> "bb"),
    # which is usually NOT the same as the site name.
    tenant = partner.get("tenant") or host.split(".")[0]
    locale = partner.get("locale", "en-US")
    search = partner.get("search_text", "")
    url = api_url(host, tenant, site)

    out: list[Job] = []
    offset = 0
    for _ in range(MAX_PAGES):
        payload = post_json(
            url,
            {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": search},
        )
        batch = parse(partner["name"], payload, host, site, locale)
        out.extend(batch)
        total = payload.get("total", 0)
        offset += PAGE
        if not batch or offset >= total:
            break
    return out
