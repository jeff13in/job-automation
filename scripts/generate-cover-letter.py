#!/usr/bin/env python3
"""
Cover letter generator using Gemini REST API (free tier — 1500 req/day).
Uses requests directly — no Google SDK dependency.
Requires: GEMINI_API_KEY environment variable
"""

import json
import os
import sys
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

BROCK_FRAMEWORK_PROMPT = """You are helping a Computer Science student write cover letters using the Brock Co-op framework.

CRITICAL RULES:
1. 1-page maximum, full block format
2. Extract 3-5 key requirements from the job posting
3. Build evidence stories for each requirement with quantifiable results
4. Write in narrative/story form — NOT bullet lists
5. Explicitly link the company's needs to the candidate's experience
6. Use plain, direct language — NO AI-pattern connectors like "demonstrating" or "directly applicable to"
7. Address obvious gaps honestly if they exist (e.g., 3+ years required)

CANDIDATE PROFILE:
Name: Jeffin Sam Joji
Graduating: April 2026
Location: Niagara Falls, ON
Email: ejffinsam14@gmail.com
Phone: (289) 501-1917

KEY EXPERIENCES:
1. Karmeka (Software Engineer Intern, Aug 2025–Present):
   - RESTful APIs with AI service integration
   - CI/CD pipelines (GitHub Actions) — 40% faster releases
   - OCR document parsing — 60% reduction in manual work
   - Cross-platform mobile/web development (React Native, Flask)

2. Venture for Canada (Software Developer/AI Engineer, Oct–Nov 2025):
   - Content aggregation pipelines from 50+ sources
   - NLP/ML models for filtering — 60% better signal-to-noise
   - Docker containerization — 99.5% uptime

3. Projects:
   - VibeMap: Full-stack ML app, 125 unit tests at 88% coverage, K-Means/KNN, deployed to production
   - AI Threat Detection: Isolation Forest/DBSCAN, Kafka/Elasticsearch, multi-source threat intel APIs
   - SecureShop Risk Assessment: NIST CSF, PCI-DSS, GDPR, OWASP — 18 control gaps, $450K loss expectancy
   - Instagram Automation: OAuth 2.0, 98.7% success rate, CI/CD deployment

4. Certifications:
   - Google Cybersecurity Professional
   - TryHackMe Jr. Penetration Tester & Security Engineer
   - HTB Junior Cybersecurity Associate
   - AWS Cloud Practitioner
   - Deloitte & PwC Virtual Security Analyst

JOB POSTING:
{job_description}

COMPANY: {company}
ROLE: {title}

Generate a cover letter following the Brock Co-op framework. Start with a strong opening that shows you understand what the company needs, then build 2–3 narrative paragraphs linking specific experiences to their requirements, and close with genuine enthusiasm.

Output only the cover letter text — no preamble, no notes, no formatting markers."""


def fetch_description(url: str) -> str:
    """Try to fetch job description from the listing URL."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self._skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = False

                def handle_data(self, data):
                    if not self._skip and data.strip():
                        self.text.append(data.strip())

            parser = TextExtractor()
            parser.feed(resp.text)
            return " ".join(parser.text)[:3000]
    except Exception:
        pass
    return ""


def generate_cover_letter(job: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    description = job.get("description", "")
    if not description and job.get("url"):
        print(f"No description stored — fetching from {job['url']}")
        description = fetch_description(job["url"])

    if not description:
        description = f"{job['title']} position at {job['company']}. No job description available — write a strong general cover letter based on the role title and company."

    prompt = BROCK_FRAMEWORK_PROMPT.format(
        job_description=description,
        company=job["company"],
        title=job["title"],
    )

    print(f"Generating cover letter for: {job['title']} at {job['company']}")

    for attempt in range(4):
        response = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )
        if response.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"Rate limited. Waiting {wait}s before retry {attempt + 1}/3...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    print("ERROR: Failed after 4 attempts due to rate limiting")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate-cover-letter.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]

    jobs_path = os.path.join(BASE_DIR, "data", "jobs.json")
    with open(jobs_path) as f:
        jobs_data = json.load(f)

    job = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)
    if not job:
        print(f"Job not found: {job_id}")
        sys.exit(1)

    cover_letter = generate_cover_letter(job)

    out_path = os.path.join(BASE_DIR, "applications", "pending", f"{job_id}-cover-letter.txt")
    with open(out_path, "w") as f:
        f.write(cover_letter)

    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
