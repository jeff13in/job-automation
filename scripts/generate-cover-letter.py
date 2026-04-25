#!/usr/bin/env python3
"""
Cover letter generator using Google Gemini API (free tier — 1500 req/day).
Follows the Brock Co-op framework: extract requirements → build evidence → write narrative.
Requires: GEMINI_API_KEY environment variable
"""

import json
import os
import sys
import google.generativeai as genai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


def generate_cover_letter(job: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = BROCK_FRAMEWORK_PROMPT.format(
        job_description=job.get("description", "No description available."),
        company=job["company"],
        title=job["title"],
    )

    print(f"Generating cover letter for: {job['title']} at {job['company']}")
    response = model.generate_content(prompt)
    return response.text


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
