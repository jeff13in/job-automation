"""Tailor the master resume to one posting, enforce "nothing new", render to PDF.

    python -m stack.resumes.tailor --variant backend --jd posting.txt --out out.pdf
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from .. import config, llm
from ..config import ROOT

SKILL = (ROOT / "skills/internship-applications/SKILL.md").read_text()
ENTRY_SECTIONS = ("experience", "projects", "leadership", "education")


class FabricationError(ValueError):
    pass


def load_master() -> dict:
    return yaml.safe_load(open(config.path(config.load()["resumes"]["master"])))


def load_variant(vid: str) -> dict:
    variants = yaml.safe_load(open(config.path(config.load()["resumes"]["variants"])))["variants"]
    for v in variants:
        if v["id"] == vid:
            return v
    raise KeyError(f"unknown variant {vid!r}")


def bullet_index(master: dict) -> dict[str, tuple[str, str, str]]:
    """bullet id -> (section, entry id, text)"""
    out = {}
    for section in ENTRY_SECTIONS:
        for entry in master.get(section, []):
            for b in entry.get("bullets", []):
                out[b["id"]] = (section, entry["id"], b["text"])
    return out


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?%?", text))


def _all_skills(master: dict) -> set[str]:
    return {s.lower() for group in master.get("skills", {}).values() for s in group}


def validate(plan: dict, master: dict) -> list[str]:
    """Problems with a tailoring plan; empty list means it only uses what's in the master."""
    problems = []
    bullets = bullet_index(master)
    entries = {e["id"] for s in ENTRY_SECTIONS for e in master.get(s, [])}
    for section in plan.get("sections", []):
        for entry in section.get("entries", []):
            if entry.get("id") not in entries:
                problems.append(f"unknown entry {entry.get('id')!r}")
            for b in entry.get("bullets", []):
                src = bullets.get(b.get("from"))
                if src is None:
                    problems.append(f"bullet cites unknown id {b.get('from')!r}")
                    continue
                if src[1] != entry.get("id"):
                    problems.append(f"bullet {b['from']} moved under {entry.get('id')}")
                new_nums = _numbers(b.get("text", "")) - _numbers(src[2])
                if new_nums:
                    problems.append(f"bullet {b['from']} adds numbers {sorted(new_nums)}")
    known = _all_skills(master)
    for s in plan.get("skills", []):
        if s.lower() not in known:
            problems.append(f"skill not in master: {s!r}")
    return problems


PLAN_SHAPE = """{
  "sections": [{"name": "experience", "entries": [{"id": "<entry id>",
      "bullets": [{"from": "<bullet id>", "text": "<reworded bullet>"}]}]}],
  "skills": ["<skill from master>", ...],
  "notes": "<one line: gaps between the posting and the master>"
}"""


def plan(master: dict, variant: dict, jd: str) -> dict:
    user = (
        f"Variant:\n{yaml.safe_dump(variant)}\n\nMaster resume:\n{yaml.safe_dump(master, sort_keys=False)}"
        f"\n\nJob description:\n{jd[:15000]}\n\nReturn the tailoring plan as JSON in this shape:\n{PLAN_SHAPE}"
    )
    result = llm.ask_json(SKILL, user, max_tokens=4000)
    problems = validate(result, master)
    if problems:  # one retry with the problems spelled out, then give up loudly
        retry = user + "\n\nYour previous plan broke the one rule:\n- " + "\n- ".join(problems) + \
            f"\n\nPrevious plan:\n{json.dumps(result)}\n\nFix it."
        result = llm.ask_json(SKILL, retry, max_tokens=4000)
        problems = validate(result, master)
        if problems:
            raise FabricationError("; ".join(problems))
    return result


def render_html(master: dict, plan_: dict) -> str:
    from jinja2 import Template

    entries = {e["id"]: (s, e) for s in ENTRY_SECTIONS for e in master.get(s, [])}
    sections = []
    for sec in plan_["sections"]:
        rows = []
        for ent in sec["entries"]:
            _, e = entries[ent["id"]]
            rows.append({
                "head": e.get("org") or e.get("school") or e.get("name"),
                "sub": e.get("title") or e.get("degree") or e.get("stack", ""),
                "dates": e.get("dates", ""),
                "bullets": [b["text"] for b in ent["bullets"]],
            })
        sections.append({"name": sec["name"].title(), "rows": rows})
    tpl = Template((ROOT / "resumes/template.html").read_text())
    return tpl.render(m=master, sections=sections, skills=plan_.get("skills", []))


def render_pdf(html: str, out: Path) -> Path:
    from weasyprint import HTML

    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(out))
    return out


def variant_plan(master: dict, variant: dict, per_entry: int = 3) -> dict:
    """The untailored variant: bullets ranked by tag overlap, no model call.
    Used for the 8 base PDFs and as the fallback when tailoring fails."""
    want = set(variant["tags"])
    sections = []
    for name in variant["section_order"]:
        if name == "skills" or name not in master:
            continue
        entries = []
        for e in master[name]:
            ranked = sorted(e.get("bullets", []), key=lambda b: -len(want & set(b.get("tags", []))))
            entries.append({"id": e["id"], "bullets": [{"from": b["id"], "text": b["text"]} for b in ranked[:per_entry]]})
        sections.append({"name": name, "entries": entries})
    skills = [s for group in master.get("skills", {}).values() for s in group]
    skills.sort(key=lambda s: 0 if any(t in s.lower() for t in want) else 1)
    return {"sections": sections, "skills": skills, "notes": "base variant"}


def build_variants(out_dir: Path) -> list[Path]:
    master = load_master()
    variants = yaml.safe_load(open(config.path(config.load()["resumes"]["variants"])))["variants"]
    return [render_pdf(render_html(master, variant_plan(master, v)), out_dir / f"{v['id']}.pdf") for v in variants]


def tailor(variant_id: str, jd: str, out: Path) -> tuple[Path, dict]:
    master = load_master()
    p = plan(master, load_variant(variant_id), jd)
    return render_pdf(render_html(master, p), out), p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant")
    ap.add_argument("--jd", help="text file with the job description")
    ap.add_argument("--out")
    ap.add_argument("--build-variants", action="store_true", help="render all 8 base variant PDFs")
    a = ap.parse_args()
    if a.build_variants:
        out_dir = config.path(config.load()["resumes"]["output_dir"]) / "variants"
        for p in build_variants(out_dir):
            print(f"wrote {p}")
        return
    if not (a.variant and a.jd and a.out):
        ap.error("--variant, --jd and --out are required unless --build-variants")
    path, p = tailor(a.variant, Path(a.jd).read_text(), Path(a.out))
    print(f"wrote {path}\nnotes: {p.get('notes', '')}")


if __name__ == "__main__":
    main()
