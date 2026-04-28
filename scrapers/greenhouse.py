"""
Greenhouse scraper.

Hits the public Greenhouse Job Board API for every company in companies.yaml
where ats == 'greenhouse'. Returns a normalized list of job postings.

API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
- 'content=true' includes the full job description in the response
- Public, no auth required
- Returns JSON: {"jobs": [...]}
"""

import requests
import time
from typing import List, Dict, Any

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards"
TIMEOUT_SECONDS = 15
RATE_LIMIT_DELAY = 0.5  # seconds between requests to be polite


def fetch_company_jobs(slug: str, name: str) -> List[Dict[str, Any]]:
    """
    Fetch all open jobs for a single Greenhouse company.
    Returns a list of normalized job dicts. Empty list on any failure.
    """
    url = f"{GREENHOUSE_BASE}/{slug}/jobs?content=true"

    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        print(f"  [greenhouse:{slug}] network error: {e}")
        return []

    if response.status_code == 404:
        print(f"  [greenhouse:{slug}] 404 — slug not found, prune from companies.yaml")
        return []
    if response.status_code != 200:
        print(f"  [greenhouse:{slug}] HTTP {response.status_code}")
        return []

    try:
        data = response.json()
    except ValueError:
        print(f"  [greenhouse:{slug}] non-JSON response")
        return []

    jobs = data.get("jobs", [])
    normalized = []

    for job in jobs:
        # Greenhouse content field is HTML; we keep it as-is for the LLM to read.
        # The LLM handles HTML fine; stripping tags loses formatting cues.
        normalized.append({
            "id": f"greenhouse:{slug}:{job.get('id')}",
            "company": name,
            "title": job.get("title", "").strip(),
            "location": (job.get("location") or {}).get("name", "").strip(),
            "url": job.get("absolute_url", ""),
            "department": " / ".join(d.get("name", "") for d in job.get("departments", [])),
            "content": job.get("content", ""),
            "updated_at": job.get("updated_at", ""),
            "ats": "greenhouse",
            "ats_slug": slug,
        })

    print(f"  [greenhouse:{slug}] {len(normalized)} jobs")
    return normalized


def fetch_all(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch jobs from all Greenhouse companies in the list.
    Companies are dicts from companies.yaml; only those with ats=='greenhouse' are scraped.
    """
    greenhouse_companies = [c for c in companies if c.get("ats") == "greenhouse"]
    print(f"Greenhouse: scraping {len(greenhouse_companies)} companies")

    all_jobs = []
    for company in greenhouse_companies:
        jobs = fetch_company_jobs(company["slug"], company["name"])
        all_jobs.extend(jobs)
        time.sleep(RATE_LIMIT_DELAY)

    print(f"Greenhouse: {len(all_jobs)} total jobs across all companies")
    return all_jobs
