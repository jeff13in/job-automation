"""Decide what goes in each form field: your profile, a drafted answer, or "ask Jeffin".

Order matters:
1. profile.yaml `fields` (name, email, links...)  — your data
2. profile.yaml `answers` patterns                  — your answers to recurring questions
3. the never-answer list                            — block, a human decides
4. free-text questions                              — Claude drafts from the master resume
5. anything else required                           — block; the agent doesn't guess at choices
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from .. import config, llm
from ..config import ROOT


@dataclass
class Field:
    idx: str
    kind: str            # text | email | tel | url | textarea | select | radio | checkbox | file | combobox
    label: str
    required: bool
    options: list[str]


@dataclass
class Decision:
    action: str          # fill | upload | skip | block
    value: str = ""
    why: str = ""


PROFILE_FIELDS = [
    (r"\bfirst\s*name|given name", "first_name"),
    (r"\blast\s*name|surname|family name", "last_name"),
    (r"^\s*(full\s*)?name\s*\*?\s*$", "_full_name"),
    (r"e-?mail", "email"),
    (r"phone|mobile", "phone"),
    (r"linkedin", "linkedin"),
    (r"github", "github"),
    (r"website|portfolio|personal (site|url)", "website"),
    (r"^\s*(current\s*)?(location|city)\b", "location"),
    (r"school|university|college|institution", "school"),
    (r"^\s*degree\b", "degree"),
]

# Questions the agent must never answer on your behalf (see SKILL.md).
SENSITIVE = re.compile(
    r"authori[sz]|sponsor|visa|citizen|immigration|work permit|criminal|convict|background check|"
    r"salary|compensation|pay expectation|gender|race|ethnic|hispanic|latin|veteran|disabilit|"
    r"pronoun|sexual orientation|lgbt|indigenous|aboriginal|visible minorit|"
    r"graduat|enrol|gpa|grade point|start date|availability|relocat|"
    r"certify|attest|acknowledge|i agree|consent|non-compete|security clearance",
    re.I,
)

RESUME_UPLOAD = re.compile(r"resume|cv\b|curriculum", re.I)
COVER_LETTER = re.compile(r"cover\s*letter", re.I)


@lru_cache
def profile() -> dict:
    return yaml.safe_load(open(config.path(config.load()["applier"]["profile_file"])))


def _profile_value(key: str, prof: dict) -> str:
    f = prof.get("fields", {})
    if key == "_full_name":
        return f"{f.get('first_name', '')} {f.get('last_name', '')}".strip()
    return str(f.get(key, "") or "")


def _usable(v: str) -> bool:
    return bool(v) and "TODO" not in v


def decide(field: Field, prof: dict | None = None) -> Decision:
    prof = prof or profile()
    label = field.label.strip()

    if field.kind == "file":
        if RESUME_UPLOAD.search(label) or not label:
            return Decision("upload", why="resume")
        if COVER_LETTER.search(label):
            return Decision("skip", why="cover letter upload") if not field.required else \
                Decision("block", why=f"required cover letter: {label}")
        return Decision("block", why=f"unknown upload: {label}") if field.required else Decision("skip")

    # 2 first: your explicit answers beat everything, including the sensitive list.
    for rule in prof.get("answers", []) or []:
        if re.search(rule["pattern"], label, re.I):
            ans = str(rule["answer"])
            if not _usable(ans):
                break
            if field.options and not _match_option(ans, field.options):
                return Decision("block", why=f"your answer {ans!r} isn't an option for: {label}")
            return Decision("fill", _match_option(ans, field.options) or ans, "profile answer")

    if field.kind in ("text", "email", "tel", "url", "combobox"):
        for pat, key in PROFILE_FIELDS:
            if re.search(pat, label, re.I):
                v = _profile_value(key, prof)
                if _usable(v):
                    return Decision("fill", v, f"profile.{key}")
                return Decision("block", why=f"profile.{key} not set") if field.required else Decision("skip")

    if SENSITIVE.search(label):
        return Decision("block", why=f"needs you: {label}") if field.required else Decision("skip", why="sensitive")

    if field.kind == "textarea" or (field.kind == "text" and len(label) > 40 and label.rstrip("* ").endswith("?")):
        return Decision("fill", why="draft")       # value filled by draft_answer()

    if field.required:
        return Decision("block", why=f"unmapped required field: {label}")
    return Decision("skip")


def _match_option(answer: str, options: list[str]) -> str | None:
    if not options:
        return answer
    a = answer.strip().lower()
    for o in options:
        if o.strip().lower() == a:
            return o
    for o in options:
        if o.strip().lower().startswith(a):
            return o
    return None


SKILL = (ROOT / "skills/internship-applications/SKILL.md").read_text()


def draft_answer(question: str, company: str, role: str, jd: str, master_yaml: str) -> str | None:
    """Claude drafts a free-text answer. Returns None if the skill says to block."""
    text = llm.ask(
        SKILL,
        f"Company: {company}\nRole: {role}\n\nJob description:\n{jd[:10000]}\n\n"
        f"Master resume:\n{master_yaml}\n\nForm question: {question}\n\n"
        "Write only the answer text. If this is a question you must not answer, reply exactly BLOCKED.",
        max_tokens=600,
    ).strip()
    return None if text.upper().startswith("BLOCKED") else text
