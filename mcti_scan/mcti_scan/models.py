"""Core data types shared by every adapter."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any


def _clean(text: str | None) -> str:
    if not text:
        return ""
    # Strip HTML tags and collapse whitespace — ATS descriptions arrive as HTML.
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Job:
    """One posting, normalized across every ATS."""

    company: str
    title: str
    url: str
    location: str = ""
    department: str = ""
    posted_at: str = ""          # ISO date string when the ATS gives one
    description: str = ""        # trimmed; only used for keyword matching
    source: str = ""             # which adapter produced this
    score: int = 0
    tags: list[str] = field(default_factory=list)
    first_seen: str = ""

    def __post_init__(self) -> None:
        self.title = _clean(self.title)
        self.location = _clean(self.location)
        self.department = _clean(self.department)
        self.description = _clean(self.description)[:4000]

    @property
    def key(self) -> str:
        """Stable identity for diffing across runs.

        Deliberately excludes the URL: some boards mint a new URL for the same
        posting when it is edited, which would otherwise look like a new job.
        """
        raw = f"{self.company.lower()}|{self.title.lower()}|{self.location.lower()}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def is_student_role(self) -> bool:
        blob = f"{self.title} {self.department}".lower()
        return any(
            w in blob
            for w in ("intern", "co-op", "coop", "student", "new grad", "new graduate", "campus")
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["key"] = self.key
        d["is_student_role"] = self.is_student_role
        return d


@dataclass
class ScanResult:
    """What one partner's scan produced, successful or not."""

    company: str
    jobs: list[Job] = field(default_factory=list)
    ok: bool = True
    error: str = ""
    manual_url: str = ""         # set when the partner needs a human to look
    undiscovered: bool = False   # platform still "auto": run discover, don't check by hand yet
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def needs_manual_check(self) -> bool:
        return self.ok and bool(self.manual_url) and not self.undiscovered


def today() -> str:
    return date.today().isoformat()
