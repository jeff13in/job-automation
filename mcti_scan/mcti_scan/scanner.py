"""Run every partner's board concurrently and collect normalized postings."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from . import adapters
from .models import Job, ScanResult

log = logging.getLogger(__name__)

MAX_WORKERS = 6   # modest: we're hitting two dozen third-party boards


def scan_one(partner: dict[str, Any]) -> ScanResult:
    name = partner["name"]
    platform = partner.get("platform", "auto")

    if platform in ("manual", "auto"):
        undiscovered = platform == "auto"
        return ScanResult(
            company=name,
            ok=True,
            manual_url=partner.get("careers_url", ""),
            undiscovered=undiscovered,
            error="" if undiscovered else "no machine-readable board",
        )

    fetcher = adapters.get(platform)
    if fetcher is None:
        return ScanResult(company=name, ok=False, error=f"unknown platform '{platform}'")

    try:
        jobs: list[Job] = fetcher(partner)
    except LookupError as e:
        # Adapter ran but found nothing parseable — a manual check, not a failure.
        log.info("%-32s nothing parseable — manual check (%s)", name, e)
        return ScanResult(
            company=name, ok=True, manual_url=partner.get("careers_url", ""), error=str(e)
        )
    except Exception as e:  # network, JSON, schema drift
        log.warning("%-32s ERROR %s: %s", name, type(e).__name__, e)
        return ScanResult(
            company=name,
            ok=False,
            error=f"{type(e).__name__}: {e}",
            manual_url=partner.get("careers_url", ""),
        )

    log.info("%-32s %3d postings (%s)", name, len(jobs), platform)
    return ScanResult(company=name, jobs=jobs, ok=True)


def scan_all(partners: list[dict[str, Any]], max_workers: int = MAX_WORKERS) -> list[ScanResult]:
    results: list[ScanResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(scan_one, p): p for p in partners}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                results.append(
                    ScanResult(company=p["name"], ok=False, error=f"worker crashed: {e}")
                )
    results.sort(key=lambda r: r.company)
    return results


def all_jobs(results: list[ScanResult]) -> list[Job]:
    out: list[Job] = []
    for r in results:
        out.extend(r.jobs)
    return out
