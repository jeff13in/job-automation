"""Drives the real applier code against a local Greenhouse-style form in headless
Chromium. The Claude calls and Gmail are stubbed; everything else is real."""
from pathlib import Path

import pytest

from stack.applier import answers, run
from stack.models import Role, Status
from stack.sheet import CsvStore

HERE = Path(__file__).parent
SPONSOR_REQUIRED = ('<div class="field"><label for="sp">Will you require visa sponsorship? *</label>'
                    '<select id="sp" name="sp" required><option>Select...</option><option>Yes</option>'
                    '<option>No</option></select></div>')

PROFILE = {"fields": {"first_name": "Jeffin", "last_name": "Sam", "email": "apply@example.com"},
           "answers": [{"pattern": "how did you hear", "answer": "Online job board"}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(answers, "profile", lambda: PROFILE)
    monkeypatch.setattr(run, "detect_ats", lambda url: "greenhouse")
    monkeypatch.setattr(run, "application_url", lambda url, ats: url)
    monkeypatch.setattr(run, "packet_dir", lambda rid: tmp_path / "packets" / rid)
    monkeypatch.setattr(run, "draft_answer", lambda q, c, r, jd, m: f"Drafted answer for {c}.")
    monkeypatch.setattr(run.tailor, "tailor", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no API in tests")))
    monkeypatch.setattr(run.gmail, "wait_for_code", lambda company_hint="": "482913")

    def make(sponsor_field: str = "") -> tuple[CsvStore, Role]:
        page = tmp_path / "form.html"
        page.write_text((HERE / "fake_greenhouse.html").read_text().replace("SPONSOR_FIELD", sponsor_field))
        store = CsvStore(tmp_path / "apps.csv")
        role = Role("Acme", "Software Engineer Intern", page.as_uri(), role_type="backend")
        store.add_new([role])
        return store, store.claim_next()
    return make, tmp_path


def test_submit_mode_end_to_end(env):
    make, tmp = env
    store, role = make()
    assert run.process(store, role, submit=True, headless=True) == "applied"
    row = store.all()[0]
    assert row.status == Status.APPLIED.value and row.applied_by == "agent"
    assert "base variant" in row.notes            # tailoring failed -> safe fallback
    packet = (tmp / "packets" / role.id / "answers.json").read_text()
    assert '"Drafted answer for Acme."' in packet
    assert '"why": "sensitive"' in packet          # gender left blank, not guessed
    assert (tmp / "packets" / role.id / "after_submit.png").exists()


def test_draft_mode_never_submits(env):
    make, tmp = env
    store, role = make()
    assert run.process(store, role, submit=False, headless=True) == "drafted"
    assert store.all()[0].status == Status.DRAFTED.value
    assert (tmp / "packets" / role.id / "filled.png").exists()


def test_required_sponsorship_question_blocks(env):
    make, _ = env
    store, role = make(SPONSOR_REQUIRED)
    assert run.process(store, role, submit=True, headless=True) == "blocked"
    row = store.all()[0]
    assert row.status == "blocked" and "sponsorship" in row.blocked_reason
