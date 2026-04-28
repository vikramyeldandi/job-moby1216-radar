"""
Lever scraper.

Hits the public Lever Postings API for every company in companies.yaml
where ats == 'lever'. Returns a normalized list of job postings.

API: https://api.lever.co/v0/postings/{slug}?mode=json
- Public, no auth required
- Returns JSON array of postings
"""

import requests
import time
from typing import List, Dict, Any

LEVER_BASE = "https://api.lever.co/v0/postings"
TIMEOUT_SECONDS = 15
RATE_LIMIT_DELAY = 0.5


def fetch_company_jobs(slug: str, name: str) -> List[Dict[str, Any]]:
    """
    Fetch all open jobs for a single Lever company.
    Returns normalized job dicts. Empty list on any failure.
    """
    url = f"{LEVER_BASE}/{slug}?mode=json"

    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        print(f"  [lever:{slug}] network error: {e}")
        return []

    if response.status_code == 404:
        print(f"  [lever:{slug}] 404 — slug not found, prune from companies.yaml")
        return []
    if response.status_code != 200:
        print(f"  [lever:{slug}] HTTP {response.status_code}")
        return []

    try:
        data = response.json()
    except ValueError:
        print(f"  [lever:{slug}] non-JSON response")
        return []

    # Lever returns a flat list, not wrapped
    jobs = data if isinstance(data, list) else []
    normalized = []

    for job in jobs:
        categories = job.get("categories", {}) or {}
        # Lever location can be in categories.location or categories.allLocations
        location = categories.get("location", "")
        all_locations = categories.get("allLocations", [])
        if all_locations and not location:
            location = ", ".join(all_locations)

        # Lever description: descriptionPlain is text, description is HTML.
        # We use the HTML so the LLM gets the same fidelity as Greenhouse.
        content = job.get("description", "") or job.get("descriptionPlain", "")

        # Lists field has structured sections (responsibilities, qualifications, etc).
        # Append them so the LLM sees full role context.
        for lst in job.get("lists", []) or []:
            if lst.get("text") or lst.get("content"):
                content += f"\n\n<h3>{lst.get('text', '')}</h3>\n{lst.get('content', '')}"

        normalized.append({
            "id": f"lever:{slug}:{job.get('id')}",
            "company": name,
            "title": job.get("text", "").strip(),
            "location": location.strip() if isinstance(location, str) else "",
            "url": job.get("hostedUrl", "") or job.get("applyUrl", ""),
            "department": categories.get("department", "") or categories.get("team", ""),
            "content": content,
            "updated_at": str(job.get("createdAt", "")),
            "ats": "lever",
            "ats_slug": slug,
        })

    print(f"  [lever:{slug}] {len(normalized)} jobs")
    return normalized


def fetch_all(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch jobs from all Lever companies in the list.
    """
    lever_companies = [c for c in companies if c.get("ats") == "lever"]
    print(f"Lever: scraping {len(lever_companies)} companies")

    all_jobs = []
    for company in lever_companies:
        jobs = fetch_company_jobs(company["slug"], company["name"])
        all_jobs.extend(jobs)
        time.sleep(RATE_LIMIT_DELAY)

    print(f"Lever: {len(all_jobs)} total jobs across all companies")
    return all_jobs
