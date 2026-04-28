"""
Filter jobs by title and location BEFORE the LLM sees them.

Why pre-filter?
- LLM scoring costs money. Scoring "Software Engineer III" or "Warehouse Associate"
  is wasteful — these never match Vikram's profile.
- Title regex catches obvious non-matches (Sr. PM and below, non-PM roles).
- Location filter excludes non-US roles entirely.

What the LLM still has to decide:
- Among Director/GPM/Head of Product roles, which fit Vikram's domain and seniority.
- Whether "Lead Product Manager" at this company is senior or junior (varies).
- AI signal strength.
"""

import re
from typing import List, Dict, Any

# Titles that match Vikram's target levels.
# Match is case-insensitive. Word boundaries used to avoid false positives.
TARGET_TITLE_PATTERNS = [
    # Group / Principal / Staff (senior IC and management)
    r"\bgroup product manager\b",
    r"\bgpm\b",
    r"\bprincipal product manager\b",
    r"\bsenior principal product manager\b",
    r"\bsr\.?\s+principal product manager\b",
    r"\bstaff product manager\b",
    r"\bsenior staff product manager\b",
    r"\bsr\.?\s+staff product manager\b",

    # Director-track
    r"\bdirector,?\s+product\b",
    r"\bdirector\s+of\s+product\b",
    r"\bsenior director,?\s+product\b",
    r"\bsr\.?\s+director,?\s+product\b",
    r"\bdirector,?\s+product management\b",
    r"\bgroup\s+director,?\s+product\b",
    r"\bglobal\s+director,?\s+product\b",

    # Head of / VP
    r"\bhead of product\b",
    r"\bvp,?\s+product\b",
    r"\bvice president,?\s+product\b",
    r"\bvp\s+of\s+product\b",

    # Lead PM (we let it through; LLM decides if it's senior or not)
    r"\blead product manager\b",
]

# Compile once.
_compiled_targets = [re.compile(p, re.IGNORECASE) for p in TARGET_TITLE_PATTERNS]

# Negative patterns — explicitly excluded titles even if they partially match above.
EXCLUDE_TITLE_PATTERNS = [
    r"\bassociate product manager\b",
    r"\bjunior product manager\b",
    r"\bproduct manager\s+i+\b",          # PM I, PM II, PM III
    r"\bproduct manager,?\s+intern\b",
    r"\bproduct marketing manager\b",      # PMM, not PM
    r"\bproduct marketing director\b",
    r"\bdirector,?\s+product marketing\b",  # alt phrasing
    r"\bdirector\s+of\s+product marketing\b",
    r"\bproduct design manager\b",         # design, not PM
    r"\btechnical product manager\b\s*-\s*level\s*[12]",  # downlevel TPM
    r"\bcontract\b",                       # contractors
    r"\bcontractor\b",
    r"\bintern\b",
    r"\bassociate,?\s+product\b",
    r"\bsenior product manager\b",         # Sr. PM is below GPM, exclude
    r"\bsr\.?\s+product manager\b",
]

_compiled_excludes = [re.compile(p, re.IGNORECASE) for p in EXCLUDE_TITLE_PATTERNS]

# US location indicators (in priority order for matching).
# Pattern: state names, state codes, common US cities, "United States", "Remote - US", etc.
US_LOCATION_PATTERNS = [
    r"\b(remote|wfh)\s*[-,–]?\s*(us|usa|united states|north america)\b",
    r"\b(us|usa|united states|u\.s\.)\b",
    r"\bnorth america\b",
    # Major US cities (not exhaustive — catches the common ATS location strings)
    r"\b(new york|nyc|san francisco|sf|los angeles|la|seattle|chicago|boston|austin|denver|"
    r"atlanta|dallas|houston|miami|portland|philadelphia|phoenix|san diego|"
    r"washington dc|d\.c\.|nashville|raleigh|salt lake city|minneapolis)\b",
    # State codes — must be at word boundary, exclude common false positives
    # (CA also = Canada, so we're explicit)
    r"\b(?:ny|nj|ma|tx|wa|or|co|il|fl|ga|nc|pa|md|va|az|tn|mn|ut|mi|oh|in|wi)\b",
    r",\s*(?:ca|ny|nj|ma|tx|wa|or|co|il|fl|ga|nc|pa|md|va|az|tn|mn|ut|mi|oh|in|wi)(?:\s|$|,)",
    # Explicit US-only remote
    r"\bremote\s*[,-]\s*us only\b",
    r"\bus only\b",
    r"\bunited states only\b",
]
_compiled_us = [re.compile(p, re.IGNORECASE) for p in US_LOCATION_PATTERNS]

# Hard-exclude locations (non-US, even when "Remote" appears alongside).
NON_US_LOCATION_PATTERNS = [
    r"\b(canada|toronto|montreal|vancouver|ottawa|ontario|quebec|british columbia)\b",
    r"\b(uk|united kingdom|england|london|manchester|edinburgh|dublin|ireland)\b",
    r"\b(germany|berlin|munich|france|paris|spain|madrid|barcelona|netherlands|amsterdam)\b",
    r"\b(india|bangalore|bengaluru|mumbai|delhi|hyderabad|pune|chennai)\b",
    r"\b(singapore|tokyo|japan|china|shanghai|beijing|hong kong|sydney|australia|melbourne)\b",
    r"\b(brazil|mexico|argentina|colombia|chile)\b",
    r"\b(remote\s*[-,–]?\s*emea|remote\s*[-,–]?\s*apac|remote\s*[-,–]?\s*latam)\b",
    r"\b(emea|apac|latam)\b",
]
_compiled_non_us = [re.compile(p, re.IGNORECASE) for p in NON_US_LOCATION_PATTERNS]


def title_matches(title: str) -> bool:
    """Returns True if the title is a candidate (worth scoring)."""
    if not title:
        return False

    # Check excludes first — these short-circuit.
    for pat in _compiled_excludes:
        if pat.search(title):
            return False

    # Then check targets.
    for pat in _compiled_targets:
        if pat.search(title):
            return True

    return False


def location_is_us(location: str) -> bool:
    """
    Returns True if the location string indicates a US-based role.
    'Remote' alone is ambiguous and treated as US (most US companies default to US-only remote).
    Empty location strings are treated as US (rare; usually means "any office").
    """
    if not location:
        return True

    # Hard exclusions first.
    for pat in _compiled_non_us:
        if pat.search(location):
            return False

    # Positive US match.
    for pat in _compiled_us:
        if pat.search(location):
            return True

    # "Remote" with no other signal — default to US (we'll catch non-US in description).
    if re.search(r"\bremote\b", location, re.IGNORECASE):
        return True

    # No clear signal either way — let it through, LLM will catch in JD.
    return True


def filter_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply title and location filters to a list of jobs.
    Returns only jobs that pass both filters.
    """
    filtered = []
    title_rejects = 0
    location_rejects = 0

    for job in jobs:
        if not title_matches(job.get("title", "")):
            title_rejects += 1
            continue
        if not location_is_us(job.get("location", "")):
            location_rejects += 1
            continue
        filtered.append(job)

    print(f"Filter: {len(jobs)} input, {len(filtered)} kept "
          f"({title_rejects} title rejects, {location_rejects} location rejects)")
    return filtered
