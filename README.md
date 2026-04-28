# Job Radar

Daily PM job aggregator for retail/eCommerce, FinTech, and shipping/logistics roles in the US.

Scrapes Greenhouse and Lever public APIs across ~50 target companies, filters by title and location, scores every role 1–10 using Claude Haiku against a personal profile rubric, and surfaces matches scored 8+ via:
- **Dashboard:** [vikramyeldandi.github.io/job-moby1216-radar](https://vikramyeldandi.github.io/job-moby1216-radar/)
- **Email digest:** daily at 6am MT (added in Phase 2)

## How it works

```
.github/workflows/daily.yml   ← cron 6am MT triggers everything
                ↓
scrapers/greenhouse.py        ← hits boards-api.greenhouse.io
scrapers/lever.py             ← hits api.lever.co
                ↓
filter.py                     ← title regex + US-only location
                ↓
score.py                      ← Anthropic API scores 1-10 vs profile.md
                ↓
render.py                     ← writes docs/results.json + index.html
                ↓
state/seen.json               ← dedup tracking, committed back to repo
                ↓
email.py                      ← Resend digest (Phase 2)
```

## Files

- `companies.yaml` — target list with ATS slug per company
- `profile.md` — scoring rubric (edit this to tune what gets scored high)
- `scrapers/` — one Python module per ATS
- `filter.py` — title and location filters applied before LLM scoring
- `score.py` — Claude Haiku scoring with structured output
- `render.py` — writes the dashboard HTML and results JSON
- `email.py` — Resend digest (Phase 2)
- `state/seen.json` — list of role IDs already seen, prevents re-alerting
- `docs/` — GitHub Pages output (dashboard)
- `.github/workflows/daily.yml` — cron schedule + manual trigger

## Local testing

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python -m scrapers.greenhouse > /tmp/raw.json
python filter.py < /tmp/raw.json > /tmp/filtered.json
python score.py < /tmp/filtered.json > /tmp/scored.json
python render.py < /tmp/scored.json
open docs/index.html
```

## Adjusting the system

- **Add a company:** append to `companies.yaml` with its ATS slug.
- **Change title filter:** edit the regex in `filter.py`.
- **Change scoring weights:** edit `profile.md`. The LLM reads it on every run.
- **Change score threshold:** edit `THRESHOLD` constant in `render.py` and `email.py`.
- **Change cron timing:** edit the cron expression in `.github/workflows/daily.yml`.

## Cost

- GitHub Actions: free (public repo)
- GitHub Pages: free
- Anthropic API: ~$0.50/month at current scrape volume (Claude Haiku)
- Resend: free tier (100 emails/day) — using <1/day
- Domain registration on companies.yaml: $0

## Status

- [x] Repo created
- [ ] Chunk 1: companies.yaml, profile.md, README
- [ ] Chunk 2: scrapers + filter
- [ ] Chunk 3: scorer
- [ ] Chunk 4: dashboard + workflow
- [ ] Phase 2: Resend email digest
