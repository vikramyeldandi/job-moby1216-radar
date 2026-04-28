"""
Render the scored results into:
- docs/results.json: machine-readable data for the dashboard JS
- docs/index.html: the static dashboard that loads results.json

Threshold: only roles scoring >= 8 are written to the dashboard.
History is preserved: previous runs' high-scoring roles stay until manually pruned.

Why static HTML + fetch(results.json) instead of server-rendered:
GitHub Pages is static-only. Keeping the data in JSON lets us update the dashboard
without re-rendering HTML on every run. Faster page load too.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

THRESHOLD = 8
RESULTS_PATH = "docs/results.json"
INDEX_PATH = "docs/index.html"


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


# Static HTML for the dashboard.
# Single-file: HTML + CSS + JS inline. Loads results.json via fetch().
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Radar — PM roles ≥8</title>
<style>
  :root {
    --bg: #0f1419;
    --card: #1a1f29;
    --card-hi: #232936;
    --text: #e8eaed;
    --text-dim: #9aa0a6;
    --accent: #7F77DD;
    --accent-hi: #9c95e8;
    --score-10: #4ade80;
    --score-9: #86efac;
    --score-8: #fbbf24;
    --border: #2a3140;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 2rem 1rem;
  }
  .container {
    max-width: 1100px;
    margin: 0 auto;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 1rem;
  }
  h1 {
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--accent);
  }
  .meta {
    color: var(--text-dim);
    font-size: 0.875rem;
  }
  .controls {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  .filter-btn {
    background: var(--card);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s;
  }
  .filter-btn:hover { background: var(--card-hi); }
  .filter-btn.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .role {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
    transition: transform 0.1s, border-color 0.1s;
  }
  .role:hover {
    border-color: var(--accent);
    transform: translateY(-1px);
  }
  .role-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }
  .role-title-block { flex: 1; }
  .role-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.25rem;
  }
  .role-title a {
    color: inherit;
    text-decoration: none;
  }
  .role-title a:hover { color: var(--accent-hi); }
  .role-company {
    color: var(--text-dim);
    font-size: 0.95rem;
  }
  .score-badge {
    font-size: 1.5rem;
    font-weight: 700;
    width: 3rem;
    height: 3rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: #0f1419;
  }
  .score-10 { background: var(--score-10); }
  .score-9  { background: var(--score-9); }
  .score-8  { background: var(--score-8); }
  .role-rationale {
    color: var(--text);
    margin-bottom: 0.75rem;
    line-height: 1.55;
  }
  .role-meta {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    color: var(--text-dim);
    font-size: 0.85rem;
  }
  .tag {
    background: var(--card-hi);
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .tag-fintech  { color: #93c5fd; }
  .tag-retail   { color: #fcd34d; }
  .tag-logistics { color: #c4b5fd; }
  .tag-adjacent { color: #f9a8d4; }
  .tag-ai-strong   { color: #4ade80; }
  .tag-ai-moderate { color: #86efac; }
  .tag-ai-weak     { color: #9aa0a6; }
  .role-concerns {
    background: rgba(251, 191, 36, 0.08);
    border-left: 3px solid var(--score-8);
    padding: 0.5rem 0.75rem;
    margin-top: 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  .empty {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--text-dim);
  }
  footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--text-dim);
    font-size: 0.8rem;
    text-align: center;
  }
  footer a { color: var(--accent-hi); text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>Job Radar</h1>
      <div class="meta" id="meta">Loading...</div>
    </div>
  </header>

  <div class="controls">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="10">Score 10</button>
    <button class="filter-btn" data-filter="9">Score 9</button>
    <button class="filter-btn" data-filter="8">Score 8</button>
    <button class="filter-btn" data-filter="fintech">FinTech</button>
    <button class="filter-btn" data-filter="retail">Retail</button>
    <button class="filter-btn" data-filter="logistics">Logistics</button>
  </div>

  <div id="roles"></div>

  <footer>
    Threshold: ≥8 · Updated daily 6am MT · Source <a href="https://github.com/vikramyeldandi/job-moby1216-radar">github</a>
  </footer>
</div>

<script>
let allRoles = [];
let activeFilter = 'all';

async function loadResults() {
  try {
    const res = await fetch('results.json?t=' + Date.now());
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    allRoles = data.roles || [];
    document.getElementById('meta').textContent =
      `${allRoles.length} roles · last run ${new Date(data.last_run).toLocaleString()}`;
    renderRoles();
  } catch (e) {
    document.getElementById('meta').textContent = 'No results yet — workflow has not run.';
    document.getElementById('roles').innerHTML =
      '<div class="empty">Run the workflow once via Actions → Daily Job Radar → Run workflow.</div>';
  }
}

function renderRoles() {
  const filtered = allRoles.filter(r => {
    if (activeFilter === 'all') return true;
    if (['10', '9', '8'].includes(activeFilter)) return r.score === parseInt(activeFilter);
    return r.domain === activeFilter;
  });

  const container = document.getElementById('roles');
  if (filtered.length === 0) {
    container.innerHTML = '<div class="empty">No roles matching this filter.</div>';
    return;
  }

  container.innerHTML = filtered.map(r => `
    <div class="role">
      <div class="role-header">
        <div class="role-title-block">
          <div class="role-title">
            <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener">${escapeHtml(r.title)}</a>
          </div>
          <div class="role-company">${escapeHtml(r.company)} · ${escapeHtml(r.location || 'Location not stated')}</div>
        </div>
        <div class="score-badge score-${r.score}">${r.score}</div>
      </div>
      <div class="role-rationale">${escapeHtml(r.rationale || '')}</div>
      <div class="role-meta">
        <span class="tag tag-${r.domain}">${escapeHtml(r.domain || '')}</span>
        <span class="tag tag-ai-${r.ai_signal}">AI: ${escapeHtml(r.ai_signal || 'none')}</span>
        <span>${escapeHtml(r.title_fit || '')} fit</span>
        <span>${r.first_seen ? new Date(r.first_seen).toLocaleDateString() : ''}</span>
      </div>
      ${r.concerns ? `<div class="role-concerns">⚠ ${escapeHtml(r.concerns)}</div>` : ''}
    </div>
  `).join('');
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderRoles();
  });
});

loadResults();
</script>
</body>
</html>
"""


def render_dashboard_html() -> None:
    """Write the static index.html. Idempotent — overwrites on every run, that's fine."""
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(DASHBOARD_HTML)
    print(f"  [render] wrote {INDEX_PATH}")


def render_all(scored_jobs: List[Dict[str, Any]]) -> int:
    """Run both render steps. Returns count of new roles >=8 from this run."""
    render_dashboard_html()
    return render_results_json(scored_jobs)
