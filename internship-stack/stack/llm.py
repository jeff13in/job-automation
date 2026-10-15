"""Thin wrapper around the Anthropic API so every component calls Claude the same way."""
from __future__ import annotations

import json
import re

from . import config

_client = None


def client():
    global _client
    if _client is None:
        import anthropic  # reads ANTHROPIC_API_KEY from the environment
        _client = anthropic.Anthropic()
    return _client


def ask(system: str, user: str, max_tokens: int | None = None) -> str:
    cfg = config.load()["llm"]
    msg = client().messages.create(
        model=cfg["model"],
        max_tokens=max_tokens or cfg["max_tokens"],
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def ask_json(system: str, user: str, max_tokens: int | None = None) -> dict:
    """Ask for a single JSON object; tolerate a ```json fence around it."""
    text = ask(system + "\n\nRespond with one JSON object and nothing else.", user, max_tokens)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"No JSON in model reply: {text[:200]}")
    return json.loads(m.group(0))
