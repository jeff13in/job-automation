"""Map a role title to one of the resume variants by keyword (first match wins)."""
from __future__ import annotations

import re
from functools import lru_cache

import yaml

from .. import config


@lru_cache
def _rules() -> list[tuple[str, re.Pattern | None]]:
    with open(config.path(config.load()["resumes"]["variants"])) as f:
        variants = yaml.safe_load(f)["variants"]
    rules = []
    for v in variants:
        words = [re.escape(k.strip()) for k in v.get("keywords", []) if k.strip()]
        rules.append((v["id"], re.compile(r"\b(" + "|".join(words) + r")\b", re.I) if words else None))
    return rules


def classify(title: str) -> str:
    fallback = "general-swe"
    for vid, pat in _rules():
        if pat is None:
            fallback = vid
        elif pat.search(title):
            return vid
    return fallback
