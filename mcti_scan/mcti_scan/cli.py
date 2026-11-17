"""Command line entry point.

    python -m mcti_scan.cli discover      # find/repair board tokens, writes partners.yml
    python -m mcti_scan.cli scan          # full run: report + csv + json handoff
    python -m mcti_scan.cli scan --dry    # scan without touching seen-state
    python -m mcti_scan.cli show          # reprint the latest report
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config, discover, report, scanner
from .filters import dedupe, shortlist
from .state import SeenStore

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
STATE = ROOT / "state" / "seen.json"


def _log(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
        stream=sys.stderr,
    )


def cmd_discover(args: argparse.Namespace) -> int:
    partners, cfg = config.load(args.partners)
    patched, unresolved = discover.run(partners, only_auto=not args.all)

    print(f"resolved {len(patched)} board(s)")
    for p in patched:
        print(f"  ✓ {p['name']:<34} {p['platform']}/{p.get('token','')}")
    if unresolved:
        print(f"\n{len(unresolved)} left without an API — will be scraped or flagged by hand:")
        for n in unresolved:
            print(f"  · {n}")

    if args.write:
        cfg_block = {
            "min_score": cfg.min_score,
            "require_canada": cfg.require_canada,
            "allow_remote_anywhere": cfg.allow_remote_anywhere,
        }
        config.save(partners, cfg_block, args.partners)
        print(f"\nwrote {args.partners} (previous version kept as partners.yml.bak)")
    else:
        print("\n(nothing written — re-run with --write to save these to partners.yml)")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    partners, cfg = config.load(args.partners)
    if args.company:
        want = args.company.lower()
        partners = [p for p in partners if want in p["name"].lower()]
        if not partners:
            print(f"no partner matching {args.company!r}", file=sys.stderr)
            return 1
    if args.min_score is not None:
        cfg.min_score = args.min_score

    results = scanner.scan_all(partners)
    raw = scanner.all_jobs(results)
    picks = shortlist(dedupe(raw), cfg)

    store = SeenStore(STATE)
    new, returning = store.mark(picks)

    text = report.markdown(new, returning, results, total_raw=len(raw))
    md_path = report.write_markdown(text, REPORTS)
    csv_path = report.write_csv(picks, ROOT / "reports" / "shortlist.csv")
    json_path = report.write_json(new, ROOT / "reports" / "new_jobs.json")

    if not args.dry:
        store.save()

    print(text)
    print(
        f"\n---\nwrote {md_path.name}, {csv_path.name}, {json_path.name} in {REPORTS}"
        + ("  [dry run: seen-state not updated]" if args.dry else "")
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    latest = REPORTS / "latest.md"
    if not latest.exists():
        print("no report yet — run `scan` first", file=sys.stderr)
        return 1
    print(latest.read_text())
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mcti_scan", description=__doc__)
    ap.add_argument("--partners", default=str(config.DEFAULT_PATH), help="path to partners.yml")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="probe ATS platforms and fill in board tokens")
    d.add_argument("--write", action="store_true", help="save results into partners.yml")
    d.add_argument("--all", action="store_true", help="re-probe every partner, not just auto")
    d.set_defaults(func=cmd_discover)

    s = sub.add_parser("scan", help="pull all boards and write the report")
    s.add_argument("--dry", action="store_true", help="don't update seen-state")
    s.add_argument("--company", help="scan only partners matching this name")
    s.add_argument("--min-score", type=int, help="override the shortlist threshold")
    s.set_defaults(func=cmd_scan)

    sh = sub.add_parser("show", help="reprint the latest report")
    sh.set_defaults(func=cmd_show)

    args = ap.parse_args(argv)
    _log(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
