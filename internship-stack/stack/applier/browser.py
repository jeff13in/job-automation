"""Playwright side of the applier: read the posting, find the form fields, fill them,
optionally submit, and handle the emailed security code.

ATS pages change often. Greenhouse, Lever and Ashby are handled by the generic
label-based filler below; Workday and anything else are sent to `blocked`.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from .answers import Field

ATS_HOSTS = {
    "greenhouse": ("greenhouse.io",),
    "lever": ("lever.co",),
    "ashby": ("ashbyhq.com",),
    "workday": ("myworkdayjobs.com", "workday.com"),
    "smartrecruiters": ("smartrecruiters.com",),
    "icims": ("icims.com",),
}


def detect_ats(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    for name, hosts in ATS_HOSTS.items():
        if any(h in host for h in hosts):
            return name
    return "other"


def application_url(url: str, ats: str) -> str:
    """Jump straight to the form where the ATS has a predictable URL for it."""
    if ats == "lever" and not url.rstrip("/").endswith("/apply"):
        return url.split("?")[0].rstrip("/") + "/apply"
    if ats == "ashby" and "/application" not in url:
        return url.split("?")[0].rstrip("/") + "/application"
    return url


# Tags every visible form control with data-stack-idx and returns its label text.
DISCOVER_JS = r"""
() => {
  const visible = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return (r.width > 0 || r.height > 0 || el.type === 'file') && s.visibility !== 'hidden'; };
  const text = el => (el ? el.innerText || el.textContent || '' : '').replace(/\s+/g, ' ').trim();
  const labelFor = el => {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    const lb = el.getAttribute('aria-labelledby');
    if (lb) return lb.split(' ').map(id => text(document.getElementById(id))).join(' ');
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return text(l); }
    const wrap = el.closest('label'); if (wrap) return text(wrap);
    const fs = el.closest('fieldset'); if (fs && (el.type === 'radio' || el.type === 'checkbox')) {
      const lg = fs.querySelector('legend'); if (lg) return text(lg); }
    const box = el.closest('.field, .application-question, [class*="field"], [class*="question"]');
    if (box) { const l = box.querySelector('label, .label, [class*="label"]'); if (l) return text(l); }
    return el.placeholder || el.name || '';
  };
  const out = []; const seenGroups = new Set(); let i = 0;
  for (const el of document.querySelectorAll('input, textarea, select')) {
    const type = (el.getAttribute('type') || el.tagName).toLowerCase();
    if (['hidden', 'submit', 'button', 'search', 'image', 'reset'].includes(type)) continue;
    if (!visible(el)) continue;
    let kind = el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : type;
    if (el.getAttribute('role') === 'combobox') kind = 'combobox';
    if (kind === 'input') kind = 'text';
    let options = [];
    if (kind === 'select') options = [...el.options].map(o => o.text.trim()).filter(t => t && !/^select/i.test(t));
    if (kind === 'radio' || kind === 'checkbox') {
      const key = el.name || el.id; if (seenGroups.has(key)) continue; seenGroups.add(key);
      const group = el.name ? document.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`) : [el];
      options = [...group].map(g => { const l = g.id && document.querySelector(`label[for="${CSS.escape(g.id)}"]`);
        return text(l || g.closest('label')) || g.value; });
    }
    const idx = String(i++); el.setAttribute('data-stack-idx', idx);
    const label = labelFor(el);
    const required = el.required || el.getAttribute('aria-required') === 'true' || /\*\s*$/.test(label);
    out.push({ idx, kind, label: label.slice(0, 300), required, options, name: el.name || '' });
  }
  return out;
}
"""

CAPTCHA = re.compile(r"recaptcha|hcaptcha|turnstile|captcha", re.I)
SUCCESS = re.compile(r"thank(s| you) for (applying|your (application|interest))|application (has been )?(submitted|received)|we('ve| have) received your application", re.I)
CODE_PROMPT = re.compile(r"(security|verification|confirmation) code", re.I)


class Browser:
    def __init__(self, headless: bool = True):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless)
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 1600})

    def close(self) -> None:
        self.browser.close()
        self._pw.stop()

    def open(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        self.page.wait_for_timeout(2500)
        # Lever/Greenhouse sometimes need an "Apply" click before the form renders.
        for name in ("Apply for this job", "Apply Now", "Apply"):
            btn = self.page.get_by_role("button", name=name, exact=False)
            if btn.count() and not self.page.locator("form input[type=file]").count():
                try:
                    btn.first.click(timeout=3000)
                    self.page.wait_for_timeout(2000)
                except Exception:
                    pass
                break

    def text(self) -> str:
        return self.page.inner_text("body")[:20000]

    def has_captcha(self) -> bool:
        return bool(self.page.locator("iframe[src*='captcha'], iframe[title*='captcha' i], .g-recaptcha, .h-captcha").count()) \
            or bool(CAPTCHA.search(self.page.content()[:200000]) and self.page.locator("iframe").count())

    def fields(self) -> list[Field]:
        return [Field(f["idx"], f["kind"], f["label"], f["required"], f["options"])
                for f in self.page.evaluate(DISCOVER_JS)]

    def _el(self, idx: str):
        return self.page.locator(f"[data-stack-idx='{idx}']")

    def fill(self, field: Field, value: str) -> None:
        el = self._el(field.idx)
        if field.kind == "select":
            el.select_option(label=value)
        elif field.kind in ("radio", "checkbox"):
            name = el.get_attribute("name")
            group = self.page.locator(f"input[name='{name}']") if name else el
            for i in range(group.count()):
                g = group.nth(i)
                gid = g.get_attribute("id")
                lbl = self.page.locator(f"label[for='{gid}']").inner_text() if gid else g.get_attribute("value")
                if (lbl or "").strip().lower() == value.strip().lower():
                    g.check(force=True)
                    return
            raise ValueError(f"option {value!r} not found")
        elif field.kind == "combobox":
            el.click()
            el.fill(value)
            self.page.wait_for_timeout(800)
            self.page.keyboard.press("Enter")
        else:
            el.fill(value)

    def upload(self, field: Field, path: Path) -> None:
        self._el(field.idx).set_input_files(str(path))

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def submit(self) -> None:
        for name in ("Submit application", "Submit Application", "Submit"):
            btn = self.page.get_by_role("button", name=name, exact=False)
            if btn.count():
                btn.first.click()
                self.page.wait_for_timeout(5000)
                return
        self.page.locator("button[type=submit], input[type=submit]").first.click()
        self.page.wait_for_timeout(5000)

    def needs_code(self) -> bool:
        return bool(CODE_PROMPT.search(self.text()))

    def enter_code(self, code: str) -> None:
        boxes = self.page.locator("input[maxlength='1']")
        if boxes.count() >= len(code):            # one box per character (Greenhouse style)
            for i, ch in enumerate(code):
                boxes.nth(i).fill(ch)
        else:
            self.page.get_by_label(CODE_PROMPT).first.fill(code)
        self.submit()

    def succeeded(self) -> bool:
        return bool(SUCCESS.search(self.text()))
