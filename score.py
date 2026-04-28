"""
Score each filtered job 1-10 against profile.md using Claude Haiku.

Why Haiku: cheapest Anthropic model, plenty smart enough for structured scoring against
a clear rubric. ~$0.25/1M input tokens. At ~30 jobs/day x ~2000 tokens each = $0.015/day.

Output per job: {score, rationale, domain, ai_signal, title_fit, concerns}.
We return the original job dict augmented with these fields.

Failures (API timeout, JSON parse, etc) get score=0 and a note in rationale.
A score=0 means "scorer failed" — distinguishable from a low quality match.
"""

import json
import os
import re
from typing import List, Dict, Any

# Anthropic SDK is imported lazily inside score_all so tests can mock the module
# without requiring the real package at import time.

# Model selection. Haiku 4.5 is the current cheapest fast model.
MODEL = "claude-haiku-4-5"

# Max tokens for the scoring response. The structured JSON we expect is ~150 tokens;
# 500 gives the model headroom for rationale without runaway cost.
MAX_OUTPUT_TOKENS = 500

# How many JD characters to include in the scoring prompt.
# Most JDs are 2000-5000 chars. We cap to keep input cost predictable.
JD_CHAR_LIMIT = 6000


def build_scoring_prompt(profile_text: str, job: Dict[str, Any]) -> str:
    """Build the user prompt for one job."""
    # Truncate JD content if too long. Keep the head — qualifications/responsibilities
    # are usually in the first half of the JD.
    content = job.get("content", "")
    if len(content) > JD_CHAR_LIMIT:
        content = content[:JD_CHAR_LIMIT] + "\n\n[...truncated...]"

    return f"""You are scoring a job posting against a candidate's profile.

CANDIDATE PROFILE:
{profile_text}

---

JOB POSTING:
Company: {job.get('company', '')}
Title: {job.get('title', '')}
Location: {job.get('location', '')}
Department: {job.get('department', '')}
URL: {job.get('url', '')}

JOB DESCRIPTION:
{content}

---

Score this role 1-10 against the candidate profile. Use the rubric and scoring anchor examples in the profile to calibrate.

Return ONLY a JSON object with this exact structure (no markdown, no preamble):
{{
  "score": <integer 1-10>,
  "rationale": "<one sentence, max 30 words, citing specific JD evidence>",
  "domain": "retail" | "fintech" | "logistics" | "adjacent" | "other",
  "ai_signal": "strong" | "moderate" | "weak" | "none",
  "title_fit": "strong" | "moderate" | "weak" | "downlevel",
  "concerns": "<optional, only if score 5-7, what's holding it back, max 20 words>"
}}"""


def parse_score_response(text: str) -> Dict[str, Any]:
    """
    Parse the LLM JSON response. Robust to common issues:
    - Leading/trailing whitespace
    - Markdown code fences (```json...```)
    - Extra text before/after JSON
    """
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    # Find the first JSON object in the text (handles preamble/postamble)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")

    parsed = json.loads(match.group(0))

    # Validate required fields
    score = parsed.get("score")
    if not isinstance(score, int) or not (1 <= score <= 10):
        raise ValueError(f"Invalid score: {score}")

    return {
        "score": score,
        "rationale": parsed.get("rationale", ""),
        "domain": parsed.get("domain", "other"),
        "ai_signal": parsed.get("ai_signal", "none"),
        "title_fit": parsed.get("title_fit", "weak"),
        "concerns": parsed.get("concerns", ""),
    }


def score_one(client, profile_text: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single job. Returns the job dict augmented with score fields."""
    prompt = build_scoring_prompt(profile_text, job)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"  [score] API error for '{job.get('title', '')}': {e}")
        return {**job, "score": 0, "rationale": f"API error: {e}",
                "domain": "other", "ai_signal": "none", "title_fit": "weak", "concerns": ""}

    # Anthropic SDK returns a list of content blocks
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    try:
        parsed = parse_score_response(text)
    except Exception as e:
        print(f"  [score] Parse error for '{job.get('title', '')}': {e}")
        return {**job, "score": 0, "rationale": f"Parse error: {e}",
                "domain": "other", "ai_signal": "none", "title_fit": "weak", "concerns": ""}

    return {**job, **parsed}


def score_all(jobs: List[Dict[str, Any]], profile_path: str = "profile.md") -> List[Dict[str, Any]]:
    """
    Score all jobs. Reads profile.md from disk.
    Requires ANTHROPIC_API_KEY in environment.
    """
    from anthropic import Anthropic  # imported lazily

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    with open(profile_path, "r", encoding="utf-8") as f:
        profile_text = f.read()

    client = Anthropic(api_key=api_key)
    print(f"Scoring {len(jobs)} jobs with {MODEL}...")

    scored = []
    for i, job in enumerate(jobs, 1):
        print(f"  [{i}/{len(jobs)}] {job.get('company', '')}: {job.get('title', '')}")
        result = score_one(client, profile_text, job)
        print(f"    → score={result['score']} ({result['title_fit']}, {result['domain']}, ai={result['ai_signal']})")
        scored.append(result)

    # Summary
    score_dist = {}
    for j in scored:
        s = j["score"]
        score_dist[s] = score_dist.get(s, 0) + 1
    print(f"\nScore distribution: {dict(sorted(score_dist.items(), reverse=True))}")
    above_threshold = [j for j in scored if j["score"] >= 8]
    print(f"Roles scoring >= 8: {len(above_threshold)}")

    return scored
