from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@lru_cache
def load(path: str | None = None) -> dict:
    p = Path(path or os.environ.get("STACK_CONFIG", ROOT / "config.yaml"))
    with open(p) as f:
        return yaml.safe_load(f)


def path(rel: str) -> Path:
    """Resolve a config-relative path against the repo root."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
