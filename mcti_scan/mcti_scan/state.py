"""Seen-state so each run can say what's actually new."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Job, today


class SeenStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                # Corrupt state is not worth crashing a scan over; start fresh
                # but keep the old file so nothing is silently destroyed.
                self.path.rename(self.path.with_suffix(".corrupt.json"))
                self._data = {}

    def mark(self, jobs: list[Job]) -> tuple[list[Job], list[Job]]:
        """Return (new_jobs, returning_jobs) and stamp first_seen on each."""
        new: list[Job] = []
        old: list[Job] = []
        stamp = today()
        for j in jobs:
            rec = self._data.get(j.key)
            if rec is None:
                j.first_seen = stamp
                self._data[j.key] = {
                    "first_seen": stamp,
                    "last_seen": stamp,
                    "company": j.company,
                    "title": j.title,
                    "url": j.url,
                }
                new.append(j)
            else:
                j.first_seen = rec.get("first_seen", stamp)
                rec["last_seen"] = stamp
                old.append(j)
        return new, old

    def applied(self, key: str) -> bool:
        return bool(self._data.get(key, {}).get("applied"))

    def mark_applied(self, key: str) -> None:
        self._data.setdefault(key, {})["applied"] = today()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

    def __len__(self) -> int:
        return len(self._data)
