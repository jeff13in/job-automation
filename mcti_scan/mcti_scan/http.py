"""One shared HTTP session: retries, polite rate limiting, honest timeouts."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

# A real UA matters: several corporate career sites 403 the default python-requests UA.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-CA,en;q=0.9",
        }
    )
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    _session = s
    return s


def _pace() -> None:
    """Small jittered pause. We are a guest on these servers."""
    time.sleep(random.uniform(0.4, 1.1))


def get_json(url: str, *, timeout: int = 25, **kwargs: Any) -> Any:
    _pace()
    r = session().get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.json()


def post_json(url: str, payload: dict[str, Any], *, timeout: int = 25, **kwargs: Any) -> Any:
    _pace()
    headers = {"Content-Type": "application/json", **kwargs.pop("headers", {})}
    r = session().post(url, json=payload, timeout=timeout, headers=headers, **kwargs)
    r.raise_for_status()
    return r.json()


def get_text(url: str, *, timeout: int = 25, **kwargs: Any) -> str:
    _pace()
    r = session().get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.text


def probe(url: str, *, timeout: int = 12) -> bool:
    """Does this endpoint exist AND list at least one posting? Used by discovery.

    Some ATS APIs (SmartRecruiters especially) answer 200 with an empty list for
    *any* slug, so "returned JSON" is not proof the board exists. Requiring at
    least one posting avoids locking a partner onto a phantom board.
    """
    try:
        r = session().get(url, timeout=timeout)
        if r.status_code != 200:
            return False
        body = r.json()
    except Exception:
        return False
    if isinstance(body, list):
        return len(body) > 0
    if isinstance(body, dict):
        for key in ("jobs", "content", "offers", "results", "postings"):
            if isinstance(body.get(key), list):
                return len(body[key]) > 0
    return False
