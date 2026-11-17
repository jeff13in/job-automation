"""Best-effort adapter for career pages with no JSON API.

Pulls schema.org JobPosting blocks out of the HTML. Most career sites emit
these for Google Jobs indexing, so it works more often than scraping markup —
and when it finds nothing it says so rather than guessing, which lets the
report fall back to a manual-check link.
"""

from __future__ import annotations

import json
import re

from ..http import get_text
from ..models import Job

SCRIPT_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def _walk(node, found: list[dict]) -> None:
    """Collect every JobPosting object anywhere in the JSON-LD tree."""
    if isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            found.append(node)
        for v in node.values():
            _walk(v, found)
    elif isinstance(node, list):
        for v in node:
            _walk(v, found)


def extract_postings(html: str) -> list[dict]:
    found: list[dict] = []
    for block in SCRIPT_RE.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _walk(data, found)
    return found


def _location(p: dict) -> str:
    loc = p.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if not isinstance(loc, dict):
        return str(loc or "")
    addr = loc.get("address") or {}
    if not isinstance(addr, dict):
        return str(addr)
    parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
    parts = [p if isinstance(p, str) else (p or {}).get("name") for p in parts]
    out = ", ".join(p for p in parts if p)
    if (p.get("jobLocationType") or "") == "TELECOMMUTE":
        out = f"{out} (Remote)".strip(", ").strip()
    return out


def parse(company: str, postings: list[dict], fallback_url: str = "") -> list[Job]:
    jobs: list[Job] = []
    for p in postings:
        org = p.get("hiringOrganization") or {}
        org_name = org.get("name") if isinstance(org, dict) else None
        jobs.append(
            Job(
                company=company,
                title=p.get("title", ""),
                url=p.get("url", "") or fallback_url,
                location=_location(p),
                department=(p.get("occupationalCategory") or "") if isinstance(
                    p.get("occupationalCategory"), str
                ) else "",
                posted_at=(p.get("datePosted") or "")[:10],
                description=p.get("description", "") or "",
                source="jsonld",
                tags=[f"org:{org_name}"] if org_name and org_name != company else [],
            )
        )
    return jobs


def fetch(partner: dict) -> list[Job]:
    url = partner.get("careers_url") or partner.get("url")
    if not url:
        raise ValueError(f"{partner['name']}: jsonld adapter needs a careers_url")
    try:
        html = get_text(url)
    except Exception as e:
        # A careers page that 404s, blocks bots or times out is still worth a
        # human look — flag it for a manual check with the reason, not an error.
        raise LookupError(f"careers page unreachable ({type(e).__name__}) — verify this link") from e
    postings = extract_postings(html)
    if not postings:
        raise LookupError(f"no JSON-LD JobPosting found at {url}")
    return parse(partner["name"], postings, fallback_url=url)
