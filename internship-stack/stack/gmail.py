"""Gmail access for the dedicated application inbox: alert emails, verification codes, replies.

First run opens a browser for OAuth consent and caches a token. Use a separate Gmail
account for applications so the agent never needs your personal inbox.
"""
from __future__ import annotations

import base64
import re
import time
from dataclasses import dataclass
from email.utils import parseaddr

from bs4 import BeautifulSoup

from . import config

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]  # read + add labels


@dataclass
class Mail:
    id: str
    thread_id: str
    sender: str          # bare address
    sender_name: str
    subject: str
    date_ms: int
    text: str
    html: str

    @property
    def sender_domain(self) -> str:
        return self.sender.rsplit("@", 1)[-1].lower()


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    cfg = config.load()["gmail"]
    token = config.path(cfg["token_file"])
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(config.path(cfg["credentials_file"])), SCOPES)
            creds = flow.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _bodies(payload: dict) -> tuple[str, str]:
    text, html = "", ""
    stack = [payload]
    while stack:
        part = stack.pop()
        stack.extend(part.get("parts", []))
        data = part.get("body", {}).get("data")
        if not data:
            continue
        if part.get("mimeType") == "text/plain" and not text:
            text = _decode(data)
        elif part.get("mimeType") == "text/html" and not html:
            html = _decode(data)
    if not text and html:
        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    return text, html


def _to_mail(m: dict) -> Mail:
    headers = {h["name"].lower(): h["value"] for h in m["payload"].get("headers", [])}
    name, addr = parseaddr(headers.get("from", ""))
    text, html = _bodies(m["payload"])
    return Mail(m["id"], m["threadId"], addr.lower(), name, headers.get("subject", ""),
                int(m.get("internalDate", 0)), text, html)


def search(query: str, limit: int = 50) -> list[Mail]:
    svc = _service()
    res = svc.users().messages().list(userId="me", q=query, maxResults=limit).execute()
    out = []
    for ref in res.get("messages", []):
        m = svc.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        out.append(_to_mail(m))
    return out


def add_label(message_id: str, label_name: str) -> None:
    """Tag processed mail so the listener never handles it twice."""
    svc = _service()
    labels = svc.users().labels().list(userId="me").execute().get("labels", [])
    label = next((l for l in labels if l["name"] == label_name), None)
    if label is None:
        label = svc.users().labels().create(userId="me", body={"name": label_name}).execute()
    svc.users().messages().modify(userId="me", id=message_id,
                                  body={"addLabelIds": [label["id"]]}).execute()


# ---- verification codes ------------------------------------------------------

_CODE_WORD = re.compile(r"\b(?:code|passcode|pin|otp)\b", re.I)
_TOKEN = re.compile(r"\b[A-Za-z0-9]{4,8}\b")
_SIX_DIGITS = re.compile(r"\b\d{6}\b")


def extract_code(text: str) -> str | None:
    # Prefer a token shortly after the word "code"; a real code contains a digit,
    # which skips words like "below" or "continue".
    for m in _CODE_WORD.finditer(text):
        for tok in _TOKEN.findall(text[m.end():m.end() + 80]):
            if any(c.isdigit() for c in tok):
                return tok
    m = _SIX_DIGITS.search(text)
    return m.group(0) if m else None


def wait_for_code(company_hint: str = "", timeout_s: int = 120, poll_s: int = 10) -> str | None:
    """Poll for a fresh verification email and return its code, or None on timeout."""
    mins = config.load()["gmail"]["code_lookback_minutes"]
    query = f"newer_than:{mins}m (subject:code OR subject:verify OR subject:verification OR subject:passcode)"
    started_ms = int(time.time() * 1000) - mins * 60_000
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        mails = sorted(search(query, limit=10), key=lambda m: -m.date_ms)
        for mail in mails:
            if mail.date_ms < started_ms:
                continue
            blob = f"{mail.sender_name} {mail.sender} {mail.subject} {mail.text}"
            if company_hint and company_hint.lower() not in blob.lower() and len(mails) > 1:
                continue
            code = extract_code(mail.subject + "\n" + mail.text)
            if code:
                return code
        time.sleep(poll_s)
    return None
