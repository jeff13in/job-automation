"""Role finder. Run daily:

    python -m stack.finder run            # SimplifyJobs + alert emails -> sheet
    python -m stack.finder run --dry-run  # print what would be added
    python -m stack.finder add --json roles.json   # push roles found elsewhere
                                                   # (e.g. a Claude session using the Indeed connector)
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from .. import config
from ..models import Role
from ..sheet import open_store
from . import simplify
from .classify import classify

CA_PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
_US_WORDS = re.compile(r"\b(SF|NYC|USA|US|United States)\b")
_STATE = re.compile(r",\s*([A-Z]{2})\s*$")


def _is_us(loc: str) -> bool:
    if "canada" in loc.lower():
        return False
    m = _STATE.search(loc)
    if m:
        return m.group(1) not in CA_PROVINCES
    return bool(_US_WORDS.search(loc))


def _location_ok(locs: list[str], wanted: list[str]) -> bool:
    if not wanted:
        return True
    joined = " | ".join(locs).lower()
    return any(w.lower() in joined for w in wanted)


def _keep_locs(locs: list[str], wanted: list[str]) -> list[str]:
    """Only the locations you'd actually work from, so the sheet stays readable."""
    hits = [l for l in locs if any(w.lower() in l.lower() for w in wanted)] if wanted else locs
    return hits or locs


def skip_reason(listing: simplify.Listing, cfg: dict) -> str | None:
    flags, skip = listing.flags, cfg["skip_flags"]
    if "closed" in flags or not listing.url:
        return "closed"
    if listing.age_days is not None and listing.age_days > cfg["max_age_days"]:
        return "too old"
    if not _location_ok(listing.locations, cfg["locations"]):
        return "location"
    if skip.get("advanced_degree") and "advanced_degree" in flags:
        return "advanced degree"
    kept = _keep_locs(listing.locations, cfg["locations"])
    us_only = all(_is_us(l) for l in kept)
    if us_only and skip.get("no_sponsorship") and "no_sponsorship" in flags:
        return "no sponsorship"
    if us_only and skip.get("us_citizenship") and "us_citizenship" in flags:
        return "US citizenship"
    return None


def from_simplify(cfg: dict) -> tuple[list[Role], dict[str, int]]:
    listings = simplify.parse(simplify.fetch(cfg["simplify_readme"]), cfg["sections"])
    roles, skipped = [], {}
    for l in listings:
        reason = skip_reason(l, cfg)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        roles.append(Role(
            company=l.company, role=l.role, url=l.url,
            location="; ".join(_keep_locs(l.locations, cfg["locations"])),
            source="simplify", role_type=classify(l.role),
        ))
    return roles, skipped


def from_alerts(cfg: dict) -> list[Role]:
    from .alerts import fetch_alert_jobs

    roles = []
    for source, j in fetch_alert_jobs(cfg["alert_labels"], days=cfg["max_age_days"]):
        if not _location_ok([j.get("location", "")], cfg["locations"]) and j.get("location"):
            continue
        roles.append(Role(company=j["company"], role=j["role"], url=j["url"],
                          location=j.get("location", ""), source=source, role_type=classify(j["role"])))
    return roles


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="stack.finder")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-alerts", action="store_true", help="skip Gmail alert emails")
    a = sub.add_parser("add")
    a.add_argument("--json", required=True, help='file with [{"company","role","url","location","source"}]')
    args = p.parse_args(argv)

    cfg = config.load()["finder"]

    if args.cmd == "add":
        items = json.load(open(args.json))
        roles = [Role(company=i["company"], role=i["role"], url=i["url"], location=i.get("location", ""),
                      source=i.get("source", "manual"), role_type=classify(i["role"])) for i in items]
        added = open_store().add_new(roles)
        print(f"added {len(added)} of {len(roles)}")
        return

    roles, skipped = from_simplify(cfg)
    if not args.no_alerts and not args.dry_run:
        try:
            roles += from_alerts(cfg)
        except Exception as e:  # alerts are a bonus; never block the main list
            print(f"alert emails skipped: {e}", file=sys.stderr)

    print(f"simplify: {len(roles)} candidates, skipped {skipped}")
    if args.dry_run:
        for role in roles:
            print(f"  [{role.role_type:12}] {role.company} — {role.role} ({role.location})")
        return
    added = open_store().add_new(roles)
    print(f"added {len(added)} new rows")
    for role in added:
        print(f"  + {role.company} — {role.role}")


if __name__ == "__main__":
    main()
