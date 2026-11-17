"""Adapter registry.

Each adapter is a callable: fetch(partner: dict) -> list[Job].
`partner` is one entry from partners.yml.
"""

from __future__ import annotations

from typing import Callable

from ..models import Job

from . import greenhouse, lever, ashby, smartrecruiters, workable, recruitee, workday, jsonld

Fetcher = Callable[[dict], list[Job]]

REGISTRY: dict[str, Fetcher] = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workable": workable.fetch,
    "recruitee": recruitee.fetch,
    "workday": workday.fetch,
    "jsonld": jsonld.fetch,
}

# Platforms the discovery probe can test by slug alone.
PROBEABLE = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee")


def get(platform: str) -> Fetcher | None:
    return REGISTRY.get(platform)
