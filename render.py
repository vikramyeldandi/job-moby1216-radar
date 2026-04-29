"""
Render the scored results into docs/results.json.

Note: this module USED to also write docs/index.html, but index.html is now
a hand-maintained static file (with the status tracking UI baked in).
The workflow no longer regenerates it.

Threshold: only roles scoring >= 8 are written to the dashboard.
History is preserved: previous runs' high-scoring roles stay until manually pruned.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

THRESHOLD = 8
RESULTS_PATH = "docs/results.json"


def load_existing_results() -> List[Dict[str, Any]]:
    """Load existing results.json if present, return empty list otherwise."""
    if not os.path.exists(RESULTS_PATH):
        return []
    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("roles", [])
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [render] could not load existing results: {e}")
        return []


def merge_and_dedupe(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge new high-scoring roles with existing ones, deduplicating by role ID.
    New entries take precedence (re-scored roles get updated scores).
    """
    by_id = {r["id"]: r for r in existing}
    for r in new:
        by_id[r["id"]] = r  # overwrites if exists

    # Sort: highest score first, ties broken by most recent
    merged = list(by_id.values())
    merged.sort(key=lambda r: (-r.get("score", 0), -hash(r.get("first_seen", "")) % 10000))
    return merged


def render_results_json(scored_jobs: List[Dict[str, Any]]) -> int:
    """
    Filter to roles >= threshold, merge with history, write results.json.
    Returns count of roles >= threshold from THIS run (for email digest).
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Tag this batch with first_seen timestamp
    high_scoring = []
    for job in scored_jobs:
        if job.get("score", 0) >= THRESHOLD:
            high_scoring.append({
                **job,
                "first_seen": now_iso,
                # Strip the bulky 'content' field — JD is on the URL, not needed in the dashboard
                "content": "",
            })

    existing = load_existing_results()
    merged = merge_and_dedupe(existing, high_scoring)

    output = {
        "last_run": now_iso,
        "threshold": THRESHOLD,
        "total_roles": len(merged),
        "new_this_run": len(high_scoring),
        "roles": merged,
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  [render] wrote {len(merged)} total roles to {RESULTS_PATH} ({len(high_scoring)} new this run)")
    return len(high_scoring)


def render_all(scored_jobs: List[Dict[str, Any]]) -> int:
    """
    Run the render step. Only writes results.json now —
    index.html is a hand-maintained static file that the workflow leaves alone.
    Returns count of new roles >=8 from this run.
    """
    return render_results_json(scored_jobs)
