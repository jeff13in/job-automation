"""Shared data model. The Google Sheet is the source of truth; every component
reads and writes rows shaped like `Role`."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class Status(str, Enum):
    NEW = "new"                  # found, not yet touched
    IN_PROGRESS = "in_progress"  # claimed by an applier run
    DRAFTED = "drafted"          # form filled, waiting for you to press submit
    APPLIED = "applied"
    BLOCKED = "blocked"          # needs a human: see blocked_reason
    OA = "oa"                    # online assessment received
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    SKIPPED = "skipped"          # filtered out (closed, ineligible, duplicate...)

    @classmethod
    def terminal(cls) -> set["Status"]:
        return {cls.REJECTED, cls.OFFER, cls.SKIPPED}


# Ordered — this is also the sheet's header row.
COLUMNS = [
    "id", "company", "role", "url", "location", "source", "date_found",
    "role_type", "resume_variant", "status", "applied_by", "blocked_reason",
    "notes", "thread_id", "last_update",
]

# Query params that only track where a click came from; strip before hashing.
_TRACKING = re.compile(r"^(utm_.*|ref|source|gh_src|lever-source.*|src|trk.*)$", re.I)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), ""))


def role_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Role:
    company: str
    role: str
    url: str
    location: str = ""
    source: str = ""
    role_type: str = ""
    resume_variant: str = ""
    status: str = Status.NEW.value
    applied_by: str = ""        # "agent" | "me"
    blocked_reason: str = ""
    notes: str = ""
    thread_id: str = ""         # Gmail thread of the latest reply
    date_found: str = field(default_factory=now_iso)
    last_update: str = field(default_factory=now_iso)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = role_id(self.url)

    def to_row(self) -> list[str]:
        d = asdict(self)
        return [str(d[c]) for c in COLUMNS]

    @classmethod
    def from_dict(cls, d: dict) -> "Role":
        names = {f.name for f in fields(cls)}
        return cls(**{k: str(v) for k, v in d.items() if k in names})
