# Candidate Profile — Vikram Yeldandi

> This file is the rubric the LLM uses to score every job posting 1–10.
> Edit this file to tune scoring. The system re-scores nothing automatically;
> changes apply to roles found *after* the next workflow run.

## Snapshot

- **Location:** Denver, CO. Open to fully remote, hybrid, and onsite anywhere in the US. No relocation constraints stated.
- **Years of experience:** 15+ in product management.
- **Current title:** Head of Product (N28 Technologies, Dec 2024 – Jan 2026).
- **Trajectory:** Head of Product ← Global Director, PM ← Sr. Global PM ← Group PM ← PM ← Sr. Business Analyst.
- **Education:** MS Computer Management; pursuing Wharton eCPO.

## Target roles (in order of preference, but score each on its own merits)

Strong title matches:
- Group Product Manager (GPM)
- Principal Product Manager
- Director / Senior Director of Product Management
- Head of Product
- VP Product (if scope and team size match)
- Lead Product Manager (only at companies where it is a senior IC role above Sr. PM)
- Senior Principal PM / Staff PM (senior IC track)

**Downlevel** (score lower):
- Senior PM, Product Manager, Associate PM, PM I/II — these are below Vikram's level.

**Equal weight on two paths:**
- **Startup Head of Product** (Series A–C, broad scope, smaller team) — maps to N28 and Omatochi experience.
- **Enterprise Director / GPM / Principal PM** (large company, deep scope, established org) — maps to VF Corp Global Director tenure.

Do not prefer one path over the other. Score on JD signals, not company stage.

## Domain fit (highest priority)

Vikram's experience clusters in three domains. Score domain match heavily.

### 1. Retail / eCommerce
- 11+ years across VF Corp (The North Face, Vans, Timberland, JanSport, EastPak, Reef, Kipling, Smartwool), Williams-Sonoma, Gymboree.
- Owned: cart, checkout, payments, post-purchase, omnichannel, BOPIS, ship-from-store, marketplace integrations (Amazon for VF brands), mobile commerce, personalization, loyalty.
- $100M+ GMV, 99.99% uptime, 8–12% increase in digital orders, 6% checkout completion lift.
- **Strong fit:** any retail/eComm PM role at scale.

### 2. FinTech / Payments
- Wells Fargo (post-Wachovia merger, KYC, regulated systems).
- Metavante/FIS (ACH, wire, bill pay for Chase, BofA, Wells, Citi).
- VF Corp payments modernization with Adyen (PCI-DSS, CCPA, GDPR).
- AI-driven fraud decisioning, replaced rules-based with confidence-scored — $24M annual fraud loss reduction.
- **Strong fit:** payments, fraud, checkout infra, BNPL, regulated FinTech.

### 3. Shipping / Logistics
- Adjacent (not primary identity): owned ordering/fulfillment/shipping at VF Corp.
- Multi-carrier (FedEx, UPS, USPS, LaserShip), reverse logistics, dynamic carrier routing, ZIP-zone pricing.
- API design for marketplace partners.
- **Moderate fit:** logistics/supply-chain PM roles — score solidly but not as strongly as retail or FinTech unless the role is logistics + AI or logistics + commerce.

### Outside these domains
- Healthcare/biotech, gaming, deep dev tools, hardware: score low unless the role is explicitly "AI Product" and treats domain as secondary.

## AI / Applied AI signal — BOOST

Vikram's positioning is now AI Product Leader. Boost roles where AI is core to the product, not just a buzzword. Specifically:

- **Strong AI signals (boost +1 to +2):** RAG, retrieval, vector DB, embeddings, multi-agent, orchestration, HITL, human-in-the-loop, evaluation, LLM-as-Judge, prompt injection defense, guardrails, confidence scoring, fraud decisioning, AI governance, AI compliance, applied AI, AI infrastructure, agent platforms.

- **Moderate AI signals (boost +0.5 to +1):** machine learning, personalization, recommendations, predictive, NLP, computer vision when applied to product surfaces.

- **Weak / no boost:** "AI-powered" in marketing copy with no engineering substance, generic mentions of "leveraging AI."

## Compliance / regulated environment — BOOST for FinTech

PCI-DSS, KYC, AML, GDPR, CCPA, HIPAA, SOC 2, financial regulation. Vikram has deep experience here from VF, Wells Fargo, Metavante, and Omatochi (HIPAA-adjacent). Boost FinTech roles that explicitly mention compliance or regulated environments.

## Scale / seniority calibration

Vikram has operated at:
- $100M+ GMV
- 99.99% uptime SLAs
- Multi-brand global teams (NA + EMEA)
- Direct management of 5+ product owners
- Strategy, hiring, mentoring, intake-to-delivery operating models

**Match high:** roles managing other PMs, owning P&L, defining strategy across multiple products.
**Match medium:** senior IC roles (Principal/Staff) with scope across cross-functional teams.
**Match low (downscore):** roles requiring narrow execution within a single feature team.

## Geography

- Open to fully remote, hybrid, or onsite.
- Located in Denver, CO. Anything in the US is acceptable.
- **Filter (not score):** non-US roles are excluded before scoring (see filter.py).

## Compensation expectations (for context — most JDs won't disclose)

Director / Head of Product target band: $250K–$400K base + equity for tech companies in major metros.
If a JD discloses comp dramatically below this (e.g., $150K base for a "Director" role), note in rationale and score lower for seniority mismatch — likely a downleveled title.

## Red flags (downscore)

- "5+ years of experience" with no senior signal — likely Sr. PM masquerading as Director.
- Heavy unrelated domain requirement ("must have biotech experience," "must have ad tech experience").
- Crypto-only roles where the work is purely tokenomics with no product surface (Coinbase mainstream payments roles are fine; pure DeFi protocol PM is not).
- Very early-stage seed companies (<10 employees) — risk too high for someone at Vikram's career stage unless explicitly founding-team Head of Product with significant equity.

## Output format the LLM should use

For every role, produce:

```
{
  "score": <integer 1-10>,
  "rationale": "<one sentence, max 30 words, citing specific JD evidence>",
  "domain": "retail|fintech|logistics|adjacent|other",
  "ai_signal": "strong|moderate|weak|none",
  "title_fit": "strong|moderate|weak|downlevel",
  "concerns": "<optional, only if score 5-7, what's holding it back>"
}
```

## Scoring anchor examples

- **10:** "Director, Product, Payments at Stripe — owns fraud detection and checkout API. PCI-DSS mentioned. Direct overlap with VF Adyen work."
- **9:** "Group Product Manager, Logistics at Instacart — owns fulfillment, multi-sided marketplace, AI/ML partnership. Strong scale and domain match."
- **8:** "Head of Product at Series B FinTech (50 employees) — payments infrastructure, regulated environment. Title and domain match; smaller scale than past roles."
- **7:** "Principal PM, Personalization at retail company — strong domain, but role is IC-track not management."
- **6:** "Director, Product at logistics startup — domain match secondary, no AI signal, smaller scope than past roles."
- **5 or below:** off-domain, downlevel, or red flags dominant.
