"""Report writers: markdown to read, CSV to sort, JSON to hand to the applier."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Job, ScanResult, today


def _row(j: Job) -> str:
    loc = j.location or "—"
    when = j.posted_at or "—"
    flag = " **·student/new-grad**" if j.is_student_role else ""
    return f"| [{j.title}]({j.url}) | {j.company} | {loc} | {when} | {j.score}{flag} |"


def markdown(
    new: list[Job],
    returning: list[Job],
    results: list[ScanResult],
    *,
    total_raw: int,
) -> str:
    pending = [r for r in results if r.undiscovered]
    manual = [r for r in results if r.needs_manual_check]
    failed = [r for r in results if not r.ok]
    ok = [r for r in results if r.ok and not r.needs_manual_check and not r.undiscovered]

    lines = [
        f"# MCTI partner job scan — {today()}",
        "",
        f"**{len(new)} new** · {len(returning)} still open · "
        f"{total_raw} postings pulled from {len(ok)} boards",
        "",
    ]

    if new:
        lines += [
            "## New since last run",
            "",
            "| Role | Company | Location | Posted | Score |",
            "|---|---|---|---|---|",
            *[_row(j) for j in new],
            "",
        ]
    else:
        lines += ["## New since last run", "", "_Nothing new._", ""]

    students = [j for j in new + returning if j.is_student_role]
    if students:
        lines += [
            "## Student / co-op / new-grad roles (all currently open)",
            "",
            "| Role | Company | Location | Posted | Score |",
            "|---|---|---|---|---|",
            *[_row(j) for j in sorted(students, key=lambda x: -x.score)],
            "",
        ]

    if returning:
        lines += [
            "## Still open from earlier runs",
            "",
            "| Role | Company | Location | First seen | Score |",
            "|---|---|---|---|---|",
            *[
                f"| [{j.title}]({j.url}) | {j.company} | {j.location or '—'} "
                f"| {j.first_seen or '—'} | {j.score} |"
                for j in returning
            ],
            "",
        ]

    if manual:
        lines += ["## Check by hand (no machine-readable board)", ""]
        for r in manual:
            note = f" — {r.error}" if r.error else ""
            lines.append(f"- **{r.company}**: {r.manual_url}{note}")
        lines.append("")

    if pending:
        lines += [
            f"## Not wired up yet ({len(pending)})",
            "",
            "Run `python -m mcti_scan.cli discover --write` to detect these boards:",
            "",
            *[f"- {r.company}" for r in pending],
            "",
        ]

    if failed:
        lines += ["## Scan errors", ""]
        for r in failed:
            lines.append(f"- **{r.company}**: {r.error}")
        lines += [
            "",
            "_A repeated error usually means the board token moved. "
            "Run `python -m mcti_scan.cli discover` to re-detect it._",
            "",
        ]

    return "\n".join(lines)


def write_markdown(text: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today()}.md"
    path.write_text(text)
    (out_dir / "latest.md").write_text(text)
    return path


def write_csv(jobs: list[Job], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "company", "title", "location", "department", "posted_at",
        "score", "is_student_role", "first_seen", "url", "source", "tags",
    ]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for j in jobs:
            d = j.to_dict()
            d["tags"] = "; ".join(j.tags)
            w.writerow(d)
    return path


def write_json(jobs: list[Job], path: Path) -> Path:
    """Handoff file for the internship-stack applier."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([j.to_dict() for j in jobs], indent=2))
    return path
