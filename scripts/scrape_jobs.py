#!/usr/bin/env python3
"""
Job board scraper - uses Remotive API, We Work Remotely RSS, and intern-list.com
"""

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(BASE_DIR, "data", "jobs.json")

# Remotive categories mapped to our role tracks (no security category on Remotive)
REMOTIVE_CATEGORIES = {
    "software_engineering": "software-dev",
    "data_ml": "data",
}

# RemoteOK tags mapped to our role tracks
REMOTEOK_TAGS = {
    "cybersecurity": ["security", "cybersecurity"],
    "software_engineering": ["backend", "api"],
    "data_ml": ["data", "machine-learning"],
}

# Keywords to filter jobs by title relevance
ROLE_KEYWORDS = {
    "cybersecurity": [
        "soc analyst", "security analyst", "cybersecurity", "threat detection",
        "security operations", "incident response", "grc analyst", "security engineer",
        "penetration tester", "security consultant"
    ],
    "software_engineering": [
        "software engineer", "software developer", "backend developer",
        "full stack", "api developer", "platform engineer"
    ],
    "data_ml": [
        "data analyst", "data engineer", "ml engineer",
        "data scientist", "analytics", "business intelligence", "machine learning"
    ],
}

def load_existing_jobs() -> Dict:
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, 'r') as f:
            return json.load(f)
    return {"jobs": []}

def save_jobs(jobs_data: Dict):
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs_data, f, indent=2)

def generate_job_id(title: str, company: str) -> str:
    clean_title = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    clean_company = re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')
    return f"{clean_company}-{clean_title}"[:80]

def classify_role(title: str, description: str = "") -> List[str]:
    text = f"{title} {description}".lower()
    categories = []
    for category, keywords in ROLE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            categories.append(category)
    return categories if categories else ["general"]

def scrape_remotive(track: str, category: str) -> List[Dict]:
    """Fetch jobs from Remotive's free public API."""
    jobs = []
    try:
        url = "https://remotive.com/api/remote-jobs"
        resp = requests.get(url, params={"category": category, "limit": 20}, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("jobs", []):
            title = item.get("title", "")
            company = item.get("company_name", "")
            if not title or not company:
                continue

            categories = classify_role(title, item.get("description", ""))
            if track not in categories:
                continue

            jobs.append({
                "id": generate_job_id(title, company),
                "title": title,
                "company": company,
                "url": item.get("url", ""),
                "location": item.get("candidate_required_location", "Remote"),
                "source": "remotive",
                "categories": categories,
                "discovered_date": datetime.now().isoformat(),
                "status": "new",
            })
    except Exception as e:
        print(f"  Remotive ({category}) error: {e}")
    return jobs

def scrape_weworkremotely(track: str) -> List[Dict]:
    """Fetch jobs from We Work Remotely RSS feed."""
    feeds = {
        "software_engineering": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "data_ml": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "cybersecurity": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    }

    feed_url = feeds.get(track)
    if not feed_url:
        return []

    jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(feed_url, headers=headers, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

        for item in root.findall(".//item")[:20]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            company_region = title_elem.text if title_elem is not None else ""

            # WWR title format: "Company: Job Title at Location"
            if ":" in company_region:
                company, job_title = company_region.split(":", 1)
                company = company.strip()
                job_title = job_title.strip()
            else:
                continue

            categories = classify_role(job_title)
            if track not in categories:
                continue

            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

            jobs.append({
                "id": generate_job_id(job_title, company),
                "title": job_title,
                "company": company,
                "url": link,
                "location": "Remote",
                "source": "weworkremotely",
                "categories": categories,
                "discovered_date": datetime.now().isoformat(),
                "status": "new",
            })
    except Exception as e:
        print(f"  We Work Remotely ({track}) error: {e}")
    return jobs

def scrape_remoteok(track: str, tags: List[str]) -> List[Dict]:
    """Fetch jobs from RemoteOK's free public API using tag search."""
    jobs = []
    seen_ids: set = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    for tag in tags:
        try:
            resp = requests.get(
                f"https://remoteok.com/api?tag={tag}",
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = [j for j in data if isinstance(j, dict) and "position" in j]
            for item in items[:15]:
                title = item.get("position", "")
                company = item.get("company", "")
                if not title or not company:
                    continue

                job_id = generate_job_id(title, company)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                categories = classify_role(title, item.get("description", ""))

                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "url": item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id', '')}"),
                    "location": "Remote",
                    "source": "remoteok",
                    "categories": categories if categories else [track],
                    "discovered_date": datetime.now().isoformat(),
                    "status": "new",
                })
        except Exception as e:
            print(f"  RemoteOK ({tag}) error: {e}")
    return jobs


# intern-list.com category paths mapped to our role tracks
INTERN_LIST_TRACKS = {
    "software_engineering": "/swe-intern-list",
    "data_ml": "/da-intern-list",
}


def parse_intern_list_slug(slug: str):
    """Parse title and company from a slug like 'software_engineer_intern_at_google_12345'."""
    slug_no_id = re.sub(r'_\d+$', '', slug)
    if '_at_' in slug_no_id:
        title_part, company_part = slug_no_id.split('_at_', 1)
        title = ' '.join(w.capitalize() for w in title_part.split('_'))
        company = ' '.join(w.capitalize() for w in company_part.split('_'))
    else:
        title = ' '.join(w.capitalize() for w in slug_no_id.split('_'))
        company = ""
    return title, company


def scrape_intern_list(track: str, list_path: str, max_pages: int = 3) -> List[Dict]:
    """Fetch internship listings from intern-list.com."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("  beautifulsoup4 not installed, skipping intern-list")
        return []

    jobs = []
    seen_slugs: set = set()
    base_url = "https://www.intern-list.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    page_url = f"{base_url}{list_path}"
    pages_fetched = 0

    while page_url and pages_fetched < max_pages:
        try:
            time.sleep(1.5)
            resp = requests.get(page_url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            prefix = list_path + "/"
            found_on_page = 0

            for tag in soup.find_all("a", href=True):
                href = tag["href"]
                if not href.startswith(prefix):
                    continue
                slug = href.split("/")[-1]
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                title, company = parse_intern_list_slug(slug)
                if not title:
                    continue

                categories = classify_role(title)

                jobs.append({
                    "id": generate_job_id(title, company),
                    "title": title,
                    "company": company,
                    "url": base_url + href,
                    "location": "USA",
                    "source": "intern-list",
                    "categories": categories if categories else [track],
                    "discovered_date": datetime.now().isoformat(),
                    "status": "new",
                })
                found_on_page += 1

            print(f"  Page {pages_fetched + 1}: {found_on_page} jobs")

            # Find the Next page link
            next_tag = soup.find("a", string=re.compile(r"^\s*next\s*$", re.IGNORECASE))
            if not next_tag:
                next_tag = soup.find("a", attrs={"aria-label": re.compile(r"next", re.IGNORECASE)})
            if next_tag and next_tag.get("href"):
                href = next_tag["href"]
                page_url = href if href.startswith("http") else base_url + href
            else:
                page_url = None

            pages_fetched += 1

        except Exception as e:
            print(f"  intern-list ({track}) page {pages_fetched + 1} error: {e}")
            break

    return jobs


def main():
    print("=== Job Board Scraper ===")
    print(f"Run time: {datetime.now().isoformat()}\n")

    jobs_data = load_existing_jobs()
    existing_ids = {job["id"] for job in jobs_data.get("jobs", [])}

    new_jobs = []

    all_tracks = set(REMOTIVE_CATEGORIES.keys()) | set(REMOTEOK_TAGS.keys())

    for track in all_tracks:
        found: List[Dict] = []

        if track in REMOTIVE_CATEGORIES:
            print(f"Scraping Remotive ({track})...")
            found += scrape_remotive(track, REMOTIVE_CATEGORIES[track])

        print(f"Scraping RemoteOK ({track})...")
        found += scrape_remoteok(track, REMOTEOK_TAGS.get(track, []))

        print(f"Scraping We Work Remotely ({track})...")
        found += scrape_weworkremotely(track)

        print(f"  → {len(found)} total for {track}")

        for job in found:
            if job["id"] not in existing_ids:
                new_jobs.append(job)
                existing_ids.add(job["id"])

    # intern-list.com (internship-focused)
    for track, list_path in INTERN_LIST_TRACKS.items():
        print(f"\nScraping intern-list.com ({track})...")
        found = scrape_intern_list(track, list_path)
        print(f"  → {len(found)} total for {track}")
        for job in found:
            if job["id"] not in existing_ids:
                new_jobs.append(job)
                existing_ids.add(job["id"])

    print(f"\nFound {len(new_jobs)} new jobs")

    jobs_data["jobs"].extend(new_jobs)
    jobs_data["last_updated"] = datetime.now().isoformat()
    save_jobs(jobs_data)

    if new_jobs:
        print("\nNew jobs by category:")
        counts: Dict[str, int] = {}
        for job in new_jobs:
            for cat in job.get("categories", ["general"]):
                counts[cat] = counts.get(cat, 0) + 1
        for cat, count in counts.items():
            print(f"  {cat}: {count}")

    print(f"\nTotal jobs in database: {len(jobs_data['jobs'])}")

if __name__ == "__main__":
    main()
