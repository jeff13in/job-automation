"""Load and save partners.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .filters import FilterConfig

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "partners.yml"


def load(path: Path | str = DEFAULT_PATH) -> tuple[list[dict[str, Any]], FilterConfig]:
    data = yaml.safe_load(Path(path).read_text()) or {}
    partners = data.get("partners", []) or []
    for p in partners:
        if "name" not in p:
            raise ValueError(f"partner entry without a name: {p}")
        p.setdefault("platform", "auto")
    f = data.get("filters", {}) or {}
    cfg = FilterConfig(
        min_score=int(f.get("min_score", 25)),
        require_canada=bool(f.get("require_canada", True)),
        allow_remote_anywhere=bool(f.get("allow_remote_anywhere", False)),
        extra_keywords=dict(f.get("extra_keywords", {}) or {}),
        extra_excludes=tuple(f.get("extra_excludes", []) or []),
    )
    return partners, cfg


def save(partners: list[dict[str, Any]], cfg_block: dict, path: Path | str = DEFAULT_PATH) -> None:
    """Write partners.yml back after discovery, preserving comments is not
    possible with safe_dump — so we keep a .bak of the hand-written file."""
    path = Path(path)
    if path.exists():
        path.with_suffix(".yml.bak").write_text(path.read_text())
    payload = {"filters": cfg_block, "partners": partners}
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100))
