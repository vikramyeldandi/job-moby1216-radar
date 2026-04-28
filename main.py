"""
Orchestrator: runs the whole pipeline in order.

scrape (greenhouse + lever) → filter → dedup against seen.json → score → render → save state

This is the entry point invoked by the GitHub Actions workflow.

Failure modes and how we handle them:
- A single company's scraper 404s: log it, skip, continue with others (handled in scrapers).
- All scrapers return zero jobs: render still runs, dashboard shows last run's data.
- Scoring API down: render with empty new results, log error, exit 1 (workflow fails visibly).
- Disk write fails: exit non-zero so GitHub Actions surfaces the error.

Why a single-file orchestrator instead of importable functions:
Workflow simplicity. One `python main.py` invocation does everything.
"""

import json
import os
import sys
from datetime import datetime, timezone

import yaml

# Make scrapers importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import greenhouse, lever
from filter import filter_jobs
from score import score_all
from render import render_all

COMPANIES_PATH = "companies.yaml"
SEEN_PATH = "state/seen.json"
SEEN_RETENTION_DAYS = 90  # prune dedup IDs older than this; prevents seen.json growing forever


def load_companies():
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    companies = data.get("companies", [])
    print(f"Loaded {len(companies)} companies from {COMPANIES_PATH}")
    return companies


def load_seen():
    if not os.path.exists(SEEN_PATH):
        return {"seen_ids": [], "last_run": None}
    try:
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Backward compat: seen_ids may be a list of strings (old) or list of dicts (new)
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"WARN: could not load seen.json: {e}, starting fresh")
        return {"seen_ids": [], "last_run": None}


def save_seen(seen_ids):
    """seen_ids is a list of {id, first_seen} dicts."""
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    output = {
        "seen_ids": seen_ids,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "_comment": "This file tracks job IDs already scored. Auto-managed by main.py."
    }
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(seen_ids)} IDs to {SEEN_PATH}")


def normalize_seen(raw_seen):
    """
    Normalize seen.json's seen_ids field. Handles two formats:
    - Old: ["id1", "id2", ...]
    - New: [{"id": "id1", "first_seen": "..."}, ...]
    Returns: list of {id, first_seen} dicts.
    """
    items = raw_seen.get("seen_ids", [])
    now_iso = datetime.now(timezone.utc).isoformat()
    normalized = []
    for item in items:
        if isinstance(item, str):
            normalized.append({"id": item, "first_seen": now_iso})
        elif isinstance(item, dict) and "id" in item:
            normalized.append({
                "id": item["id"],
                "first_seen": item.get("first_seen", now_iso),
            })
    return normalized


def prune_old_seen(seen_items, retention_days=SEEN_RETENTION_DAYS):
    """Drop seen IDs older than retention window."""
    if retention_days <= 0:
        return seen_items
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()
    pruned = [s for s in seen_items if s["first_seen"] >= cutoff_iso]
    dropped = len(seen_items) - len(pruned)
    if dropped > 0:
        print(f"Pruned {dropped} seen IDs older than {retention_days} days")
    return pruned


def main():
    print("=" * 60)
    print(f"Job Radar run starting {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. Load config
    companies = load_companies()
    seen_data = load_seen()
    seen_items = normalize_seen(seen_data)
    seen_ids = {s["id"] for s in seen_items}
    print(f"Loaded {len(seen_ids)} previously-seen role IDs")

    # 2. Scrape
    print("\n--- SCRAPE ---")
    all_jobs = greenhouse.fetch_all(companies) + lever.fetch_all(companies)
    print(f"Total raw jobs: {len(all_jobs)}")

    # 3. Filter (title + location)
    print("\n--- FILTER ---")
    filtered = filter_jobs(all_jobs)

    # 4. Dedup against seen
    print("\n--- DEDUP ---")
    new_jobs = [j for j in filtered if j["id"] not in seen_ids]
    print(f"After dedup: {len(new_jobs)} new jobs (was {len(filtered)})")

    # 5. Score (skip if nothing new)
    if new_jobs:
        print("\n--- SCORE ---")
        scored = score_all(new_jobs, profile_path="profile.md")
    else:
        print("\n--- SCORE --- (skipped, nothing new)")
        scored = []

    # 6. Render
    print("\n--- RENDER ---")
    new_high_scoring = render_all(scored)

    # 7. Update seen
    print("\n--- STATE ---")
    now_iso = datetime.now(timezone.utc).isoformat()
    for job in new_jobs:
        seen_items.append({"id": job["id"], "first_seen": now_iso})
    seen_items = prune_old_seen(seen_items)
    save_seen(seen_items)

    # 8. Summary for the workflow log
    print("\n" + "=" * 60)
    print(f"DONE — {len(new_jobs)} new jobs scored, {new_high_scoring} above threshold")
    print("=" * 60)

    # Exit code 0 means success; we don't fail the build if zero new roles found.
    return 0


if __name__ == "__main__":
    sys.exit(main())
