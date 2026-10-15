"""Inbox listener: read replies in the application inbox, match each to a sheet row,
write the new status back, and flag what needs you (blocked_reason is non-empty).

    python -m stack.listener once        # one pass
    python -m stack.listener watch       # poll forever (listener.poll_seconds)
    python -m stack.listener once --dry-run
"""
from __future__ import annotations

import argparse
import re
import time

from .. import config, gmail, llm
from ..models import Role, Status
from ..sheet import Store, open_store

ATS_SENDERS = ("greenhouse", "lever.co", "ashbyhq", "myworkday", "workday", "smartrecruiters",
               "icims", "hackerrank", "codesignal", "codility", "hirevue", "karat", "jobvite")

ACTIVE = (Status.DRAFTED, Status.APPLIED, Status.BLOCKED, Status.OA, Status.INTERVIEW, Status.IN_PROGRESS)

# category -> (new status, what you need to do or "" if nothing)
OUTCOMES = {
    "confirmation": (Status.APPLIED, ""),
    "rejection": (Status.REJECTED, ""),
    "assessment": (Status.OA, "take the assessment"),
    "interview": (Status.INTERVIEW, "schedule / prep the interview"),
    "needs_info": (Status.BLOCKED, "they asked for something"),
    "offer": (Status.OFFER, "review the offer"),
}

SYSTEM = """You triage replies to internship applications. Given one email and a
numbered list of applications, return:
{"match": <number from the list or null>, "category": "confirmation"|"rejection"|
"assessment"|"interview"|"needs_info"|"offer"|"other", "summary": "<= 15 words, include any deadline"}
Match only when the email clearly concerns that company and role. A confirmation is
"we received your application". If the email is marketing or unrelated, category "other"."""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def candidates(mail: gmail.Mail, rows: list[Role]) -> list[Role]:
    """Rows whose company name appears in the email, so we only ask about plausible matches."""
    blob = _norm(f"{mail.sender_name} {mail.sender} {mail.subject} {mail.text[:4000]}")
    hits = [r for r in rows if len(_norm(r.company)) >= 3 and _norm(r.company) in blob]
    return hits


def triage(mail: gmail.Mail, cands: list[Role]) -> dict:
    listing = "\n".join(f"{i}. {r.company} — {r.role} (status {r.status})" for i, r in enumerate(cands))
    user = (f"From: {mail.sender_name} <{mail.sender}>\nSubject: {mail.subject}\n\n{mail.text[:6000]}"
            f"\n\nApplications:\n{listing}")
    out = llm.ask_json(SYSTEM, user, max_tokens=300)
    m = out.get("match")
    out["role"] = cands[m] if isinstance(m, int) and 0 <= m < len(cands) else None
    return out


def apply_outcome(store: Store, role: Role, category: str, summary: str, thread_id: str) -> str | None:
    if category not in OUTCOMES:
        return None
    status, todo = OUTCOMES[category]
    # A confirmation must not undo a later state (e.g. arrives after an OA invite).
    if category == "confirmation" and role.status not in (Status.DRAFTED.value, Status.IN_PROGRESS.value,
                                                          Status.APPLIED.value, Status.BLOCKED.value):
        return None
    changes = {"thread_id": thread_id, "notes": summary}
    if category == "confirmation" and not role.applied_by:
        changes["applied_by"] = "me"         # you submitted it yourself from the draft
    if todo:
        changes["blocked_reason"] = f"{todo}: {summary}"
    store.set_status(role.id, status, **changes)
    return status.value


def once(dry_run: bool = False) -> None:
    cfg = config.load()["listener"]
    store = open_store()
    rows = [r for r in store.all() if r.status in {s.value for s in ACTIVE}]
    for mail in gmail.search(cfg["query"] + " -label:stack-processed", limit=50):
        cands = candidates(mail, rows)
        if not cands and not any(a in mail.sender_domain for a in ATS_SENDERS):
            continue
        if not cands:
            print(f"? unmatched ATS mail: {mail.subject}")
            continue
        t = triage(mail, cands)
        role = t["role"]
        if role and t["category"] != "other":
            if dry_run:
                print(f"would set {role.company} — {role.role}: {t['category']} ({t['summary']})")
            else:
                new = apply_outcome(store, role, t["category"], t["summary"], mail.thread_id)
                if new:
                    print(f"{new:10} {role.company} — {role.role}: {t['summary']}")
        if not dry_run:
            gmail.add_label(mail.id, "stack-processed")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="stack.listener")
    ap.add_argument("cmd", choices=["once", "watch"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "once":
        once(a.dry_run)
        return
    while True:
        try:
            once(a.dry_run)
        except Exception as e:
            print(f"listener pass failed: {e}")
        time.sleep(config.load()["listener"]["poll_seconds"])


if __name__ == "__main__":
    main()
