"""Probe candidate slugs against each keyless ATS to find a company's board.

Board tokens change when a company switches ATS, which is the main reason a
scanner like this quietly stops working. Running `discover` re-detects them
instead of leaving you to debug an empty report.
"""

from __future__ import annotations

import logging
from typing import Any

from . import adapters
from .adapters import greenhouse, lever, ashby, smartrecruiters, workable, recruitee
from .http import probe

log = logging.getLogger(__name__)

URL_BUILDERS = {
    "greenhouse": greenhouse.url_for,
    "lever": lever.url_for,
    "ashby": ashby.url_for,
    "smartrecruiters": smartrecruiters.url_for,
    "workable": workable.url_for,
    "recruitee": recruitee.url_for,
}


def slug_candidates(partner: dict[str, Any]) -> list[str]:
    if partner.get("candidates"):
        return list(partner["candidates"])
    name = partner["name"].lower()
    for junk in ("(", ")", ".", ","):
        name = name.replace(junk, "")
    compact = name.replace(" ", "").replace("-", "")
    hyphen = name.replace(" ", "-")
    first = name.split()[0] if name.split() else name
    return list(dict.fromkeys([compact, hyphen, first]))


def discover_one(partner: dict[str, Any]) -> dict[str, Any] | None:
    """Return the config patch that makes this partner work, or None."""
    hint = partner.get("hint")
    order = list(adapters.PROBEABLE)
    if hint in order:                       # try the hinted platform first
        order.remove(hint)
        order.insert(0, hint)

    for platform in order:
        build = URL_BUILDERS[platform]
        for slug in slug_candidates(partner):
            url = build(slug)
            if probe(url):
                log.info("  %s -> %s / %s", partner["name"], platform, slug)
                return {"platform": platform, "token": slug}
    return None


def run(partners: list[dict[str, Any]], only_auto: bool = True) -> tuple[list[dict], list[str]]:
    """Mutate partners in place with discovered tokens. Returns (patched, unresolved)."""
    patched: list[dict] = []
    unresolved: list[str] = []

    for p in partners:
        if p.get("platform") == "manual":
            continue
        if only_auto and p.get("platform") != "auto":
            continue

        log.info("probing %s ...", p["name"])
        patch = discover_one(p)
        if patch:
            p.update(patch)
            p.pop("candidates", None)
            p.pop("hint", None)
            patched.append(p)
        else:
            # Fall back to scraping the careers page; if that has no JSON-LD the
            # scan will flag it for a manual check rather than failing silently.
            if p.get("careers_url"):
                p["platform"] = "jsonld"
            else:
                p["platform"] = "manual"
            unresolved.append(p["name"])

    return patched, unresolved
