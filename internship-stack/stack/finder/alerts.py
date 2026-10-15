"""Turn job-alert emails (LinkedIn, Handshake, Indeed, Intern Insider) into roles.

Reading the alert emails those sites send you is much safer than scraping or
automating the sites themselves, which their terms prohibit and which can get the
account banned. Set the alerts up on each site, filter them into a Gmail label
(config: finder.alert_labels), and this module reads that label.
"""
from __future__ import annotations

import re

from .. import gmail, llm

JOB_LINK = re.compile(
    r"https?://[^\s\"'<>]*(?:linkedin\.com/(?:comm/)?jobs/view/\d+|indeed\.com/(?:rc/clk|viewjob|pagead/clk)\S*?jk=\w+"
    r"|joinhandshake\.com/\S*?jobs/\d+|interninsider\S*)",
    re.I,
)

SYSTEM = """You extract job postings from a job-alert email. Return
{"jobs": [{"company": str, "role": str, "location": str, "url": str}]}.
Only include internship / co-op roles. `url` must be copied exactly from the
provided link list; never construct or guess a URL. If unsure about a field, use ""."""


def from_mail(mail: gmail.Mail) -> list[dict]:
    body = mail.html or mail.text
    links = list(dict.fromkeys(m.group(0).rstrip(".,)") for m in JOB_LINK.finditer(body)))
    if not links:
        return []
    user = f"Subject: {mail.subject}\n\nEmail text:\n{mail.text[:12000]}\n\nLinks:\n" + "\n".join(links)
    jobs = llm.ask_json(SYSTEM, user).get("jobs", [])
    allowed = set(links)
    # Guard against invented links: keep only URLs that were really in the email.
    return [j for j in jobs if j.get("url") in allowed and j.get("company") and j.get("role")]


def fetch_alert_jobs(labels: list[str], days: int) -> list[tuple[str, dict]]:
    out = []
    for label in labels:
        for mail in gmail.search(f"label:{label} newer_than:{days}d -label:stack-processed"):
            source = mail.sender_domain.split(".")[-2] if "." in mail.sender_domain else "alert"
            for job in from_mail(mail):
                out.append((source, job))
            gmail.add_label(mail.id, "stack-processed")
    return out
