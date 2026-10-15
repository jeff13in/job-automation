"""The applier. Pulls the next `new` row, prepares an application, and either leaves
it as a draft for you or submits it.

    python -m stack.applier run              # up to applier.max_per_run rows, in config mode
    python -m stack.applier run --id ID      # one specific row
    python -m stack.applier submit ID        # you've reviewed the draft packet: submit it
    python -m stack.applier requeue ID       # after fixing profile.yaml, try a blocked row again

Every run leaves a packet in data/packets/<id>/: the tailored resume, every
answer it would type (answers.json) and a full-page screenshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .. import config, gmail
from ..models import Role, Status
from ..resumes import tailor
from ..sheet import Store, open_store
from .answers import decide, draft_answer
from .browser import Browser, application_url, detect_ats


def packet_dir(role_id: str) -> Path:
    return config.path("data/packets") / role_id


def _resume_for(role: Role, jd: str, out: Path) -> tuple[Path, str, str]:
    """Tailored resume, falling back to the base variant. Returns (path, variant, note)."""
    variant = role.role_type or "general-swe"
    try:
        path, plan = tailor.tailor(variant, jd, out)
        return path, variant, f"tailored; gaps: {plan.get('notes', '')}"
    except Exception as e:  # FabricationError, API error...: the base variant is always safe
        master = tailor.load_master()
        base = tailor.variant_plan(master, tailor.load_variant(variant))
        path = tailor.render_pdf(tailor.render_html(master, base), out)
        return path, variant, f"base variant (tailoring failed: {str(e)[:120]})"


def prepare(b: Browser, role: Role) -> dict:
    """Open the form, decide every field. Returns the packet (nothing typed yet)."""
    ats = detect_ats(role.url)
    supported = config.load()["applier"]["supported_ats"]
    if ats not in supported:
        return {"blocked": [f"{ats} ATS not automated; apply by hand"], "ats": ats}

    b.open(application_url(role.url, ats))
    jd = b.text()
    pdir = packet_dir(role.id)
    resume, variant, resume_note = _resume_for(role, jd, pdir / "resume.pdf")
    master_yaml = yaml.safe_dump(tailor.load_master(), sort_keys=False)

    plan, blocked = [], []
    for f in b.fields():
        d = decide(f)
        if d.action == "fill" and d.why == "draft":
            text = draft_answer(f.label, role.company, role.role, jd, master_yaml)
            if text is None:
                d.action, d.why = ("block", f"needs you: {f.label}") if f.required else ("skip", "skill said no")
            else:
                d.value = text
        if d.action == "block":
            blocked.append(d.why)
        plan.append({"idx": f.idx, "kind": f.kind, "label": f.label, "required": f.required,
                     "action": d.action, "value": d.value, "why": d.why})
    if not any(p["action"] == "upload" for p in plan):
        blocked.append("no resume upload field found")
    if b.has_captcha():
        blocked.append("captcha on form")
    return {"ats": ats, "variant": variant, "resume": str(resume), "resume_note": resume_note,
            "fields": plan, "blocked": blocked, "jd": jd[:5000]}


def fill(b: Browser, packet: dict) -> list[str]:
    errors = []
    by_idx = {f.idx: f for f in b.fields()}
    for p in packet["fields"]:
        f = by_idx.get(p["idx"])
        if f is None or f.label != p["label"]:
            if p["action"] in ("fill", "upload"):
                errors.append(f"form changed at: {p['label']}")
            continue
        try:
            if p["action"] == "upload":
                b.upload(f, Path(packet["resume"]))
            elif p["action"] == "fill":
                b.fill(f, p["value"])
        except Exception as e:
            errors.append(f"couldn't fill {p['label']!r}: {str(e)[:80]}")
    return errors


def try_submit(b: Browser, role: Role) -> str | None:
    """Submit and confirm. Returns None on success, else the reason it's blocked."""
    b.submit()
    if b.needs_code():
        code = gmail.wait_for_code(company_hint=role.company)
        if not code:
            return "security code email never arrived"
        b.enter_code(code)
    if not b.succeeded():
        return "submitted but couldn't confirm success; check the screenshot"
    return None


def process(store: Store, role: Role, submit: bool, headless: bool) -> str:
    pdir = packet_dir(role.id)
    pdir.mkdir(parents=True, exist_ok=True)
    b = Browser(headless=headless)
    try:
        packet = prepare(b, role)
        (pdir / "answers.json").write_text(json.dumps(packet, indent=2))
        if packet["blocked"]:
            store.block(role.id, "; ".join(packet["blocked"])[:400])
            return "blocked"
        errors = fill(b, packet)
        b.screenshot(pdir / "filled.png")
        if errors:
            store.block(role.id, "; ".join(errors)[:400])
            return "blocked"
        changes = {"resume_variant": packet["variant"], "notes": f"{packet['resume_note']} | packet: {pdir}"}
        if not submit:
            store.set_status(role.id, Status.DRAFTED, **changes)
            return "drafted"
        reason = try_submit(b, role)
        b.screenshot(pdir / "after_submit.png")
        if reason:
            store.block(role.id, reason)
            return "blocked"
        store.set_status(role.id, Status.APPLIED, applied_by="agent", **changes)
        return "applied"
    except Exception as e:
        b.screenshot(pdir / "error.png")
        store.block(role.id, f"applier error: {str(e)[:200]}")
        return "error"
    finally:
        b.close()


def submit_reviewed(store: Store, role: Role, headless: bool) -> str:
    """Re-open the form, refill from the reviewed packet (edit answers.json first if
    you want changes), then submit."""
    packet = json.loads((packet_dir(role.id) / "answers.json").read_text())
    b = Browser(headless=headless)
    try:
        b.open(application_url(role.url, packet["ats"]))
        errors = fill(b, packet)
        if errors:
            store.block(role.id, "; ".join(errors)[:400])
            return "blocked"
        reason = try_submit(b, role)
        b.screenshot(packet_dir(role.id) / "after_submit.png")
        if reason:
            store.block(role.id, reason)
            return "blocked"
        store.set_status(role.id, Status.APPLIED, applied_by="agent")
        return "applied"
    finally:
        b.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="stack.applier")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--id")
    r.add_argument("--headed", action="store_true", help="show the browser")
    s = sub.add_parser("submit")
    s.add_argument("id")
    s.add_argument("--headed", action="store_true")
    q = sub.add_parser("requeue")
    q.add_argument("id")
    args = ap.parse_args(argv)

    cfg = config.load()["applier"]
    store = open_store()
    rows = {x.id: x for x in store.all()}

    if args.cmd == "requeue":
        store.set_status(args.id, Status.NEW)
        print(f"{args.id} -> new")
        return
    headless = cfg["headless"] and not args.headed
    if args.cmd == "submit":
        print(submit_reviewed(store, rows[args.id], headless))
        return

    submit = cfg["mode"] == "submit"
    todo = [rows[args.id]] if args.id else []
    while not args.id and len(todo) < cfg["max_per_run"]:
        nxt = store.claim_next()
        if nxt is None:
            break
        todo.append(nxt)
        result = process(store, nxt, submit, headless)
        print(f"{result:8} {nxt.company} — {nxt.role}")
    if args.id:
        print(process(store, todo[0], submit, headless))
    if not todo:
        print("queue empty")


if __name__ == "__main__":
    main()
