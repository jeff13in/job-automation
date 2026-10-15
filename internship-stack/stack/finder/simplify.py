"""Parse the SimplifyJobs internship list (an HTML table per section inside README.md)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

FLAGS = {
    "🛂": "no_sponsorship",
    "🇺🇸": "us_citizenship",
    "🔒": "closed",
    "🎓": "advanced_degree",
    "🔥": "faang",
}


@dataclass
class Listing:
    section: str
    company: str
    role: str
    locations: list[str]
    url: str
    age_days: int | None
    flags: set[str] = field(default_factory=set)


def fetch(url: str) -> str:
    r = httpx.get(url, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.text


def _age_days(text: str) -> int | None:
    m = re.match(r"\s*(\d+)\s*(d|w|mo|y)", text.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return n * {"d": 1, "w": 7, "mo": 30, "y": 365}[unit]


def _flags(text: str) -> set[str]:
    return {name for emoji, name in FLAGS.items() if emoji in text}


def _clean(text: str) -> str:
    for emoji in FLAGS:
        text = text.replace(emoji, "")
    return re.sub(r"\s+", " ", text).strip()


def _locations(td) -> list[str]:
    details = td.find("details")
    if details:
        summary = details.find("summary")
        if summary:
            summary.extract()
        td = details
    return [s.strip() for s in td.get_text("\n").split("\n") if s.strip()]


def parse(readme: str, sections: list[str] | None = None) -> list[Listing]:
    out: list[Listing] = []
    # Each "## heading" chunk holds at most one table.
    for chunk in re.split(r"\n(?=## )", readme):
        heading = chunk.split("\n", 1)[0].lstrip("# ").strip()
        if sections and not any(s.lower() in heading.lower() for s in sections):
            continue
        start = chunk.find("<table>")
        if start < 0:
            continue
        soup = BeautifulSoup(chunk[start:], "html.parser")
        tbody = soup.find("tbody")
        if tbody is None:
            continue
        last_company = ""
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue
            raw_company = tds[0].get_text(" ", strip=True)
            company = _clean(raw_company)
            if company in ("↳", ""):
                company = last_company
            last_company = company
            raw_role = tds[1].get_text(" ", strip=True)
            link = tds[3].find("a", href=True)
            flags = _flags(raw_company + raw_role + tds[3].get_text())
            if link is None:
                flags.add("closed")
            out.append(Listing(
                section=heading,
                company=company,
                role=_clean(raw_role),
                locations=_locations(tds[2]),
                url=link["href"] if link else "",
                age_days=_age_days(tds[4].get_text()),
                flags=flags,
            ))
    return out
