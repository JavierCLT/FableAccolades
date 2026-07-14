# Methodology

**Best Broker Index** is a personal, independent, public-data-only research tool. This page
explains exactly how data is collected and how scores are produced. Nothing here is financial
advice; see [limitations.md](limitations.md) for what this tool cannot tell you.

## Principles

1. **Public data only.** Broker public pages, expert publishers' public reviews, the official
   CFPB Consumer Complaint Database API, and public communities (Reddit, Bogleheads) and
   review platforms (Trustpilot, BBB, app stores). No broker data feeds, partnerships, or
   paid placements. No affiliate links.
2. **Identical methodology for every broker.** The same collectors, rules, weights, and
   penalties run against all brokers. There is no per-broker special-casing anywhere in the
   scoring code (verify: `backend/scoring/` contains no broker names).
3. **Every data point carries evidence.** Each fact, rating, theme, and complaint statistic
   references an `evidence` row storing the source URL, page title, publisher, retrieval
   date, snippet, collection method, and a confidence grade. The Evidence Viewer exposes all
   of it.
4. **Never fabricate; mark gaps.** When a source is checked and has no data (e.g. a broker
   with no CFPB company entity), that is recorded explicitly as *unavailable* — it is shown
   as a coverage gap, never invented and never silently treated as a good or bad signal
   beyond what is documented below.
5. **Deterministic scoring.** All scores come from rules and arithmetic that are documented
   in [scoring_logic.md](scoring_logic.md) and reproducible from the database. An LLM may
   optionally assist with *classification, theme extraction, summarization, and
   normalization* only — it never produces a score, and the default pipeline uses
   deterministic lexicon/keyword classifiers instead.

## What is measured

Sixteen dimensions: costs & fees; cash yield & cash management; ease of use; mobile app
quality; research & education; retirement & rollover; trading tools; investment product
breadth; customer support; transfer/ACAT; banking integration; advisory/managed options;
platform reliability; security; tax reporting & cost basis; fractional shares.

Each broker × dimension score (0–100) blends up to three components:

| Component | Weight* | Source |
|---|---|---|
| **Objective facts** | 45% | Rules over facts from the broker's own public pages (e.g. ACAT fee ladders, sweep APY curves). Mobile app quality uses aggregate app-store ratings as its objective input. |
| **Customer voice** | 35% | Themes from Reddit/Bogleheads/review sites: signed by sentiment, weighted by volume (√), severity (complaints), recency (exponential decay), and source quality. Customer support additionally blends a CFPB complaint-rate score (complaints per $B client assets). |
| **Expert consensus** | 20% | Quality- and recency-weighted mean of published expert ratings normalized to 0–100, **minus a disagreement penalty** when publishers contradict each other. |

\* Renormalized when a component has no data — a missing component reduces confidence, not
the score's validity.

**Persona scores** are weighted averages of dimension scores using per-persona weights
(user-adjustable in the UI), plus a bounded ±3-point CFPB complaint-momentum adjustment.

## Confidence scores

Every score has a separate 0–100 confidence value built from four documented sub-scores:
evidence volume (0–40), source quality (0–20), recency (0–25), and corroboration/agreement
(0–15). Low evidence, stale data, weak sources, and expert disagreement all reduce
confidence. Exact formulas: [scoring_logic.md](scoring_logic.md).

## Cost Lab and relationship benefits

The Cost Lab is a separate decision model; it does not alter dimension or persona scores.
It estimates annual net impact as missed cash interest plus current trading, account,
transfer, and margin costs, minus relationship benefits the user explicitly chooses to
include.

Relationship benefits follow three rules:

1. Only current, official-source terms with explicit dollar or percentage values are
   eligible for calculation.
2. Card rewards are incremental. Fidelity and Robinhood rewards are compared with the
   user's current-card reward rate; Merrill's BofA Rewards value counts only the tier bonus
   applied to the entered eligible-card base rate.
3. Eligibility costs and conditions remain visible. Robinhood Gold's required subscription
   is deducted, BofA Rewards tiers depend on entered qualifying Bank of America and Merrill
   balances, and optional subscription credits are counted only when the user says they
   expect to use them.

Welcome offers, loan discounts, ATM reimbursements, lounge access, tax effects, and premium
card benefits without a comparable personal dollar value are displayed as context but are
not added to the result. This avoids treating a feature list as guaranteed savings.

## Contradiction detection

For each broker × dimension (and for overall ratings), all pairs of expert sources are
compared on the normalized 0–100 scale. Gaps ≥ 15 points are recorded as contradictions
(15+ moderate, 25+ significant, 35+ severe), displayed in the Contradiction Matrix, and
penalize both the expert component (up to −10 points) and confidence.

## Penalties and rewards

- **Withheld:** expired score-critical facts are removed from score inputs and shown as
  withheld in the dashboard. Cash yields use a 7-day SLA; margin rates use 14 days;
  common fees and IRA matches use 30 days; other facts use a 90-day default.
- **Penalized:** low evidence counts (via confidence), expert contradictions (score + confidence),
  self-reported claims (broker marketing statements are excluded; only checkable product
  facts are recorded), worsening CFPB complaint trends (momentum).
- **Rewarded:** verifiable objective facts with high-quality evidence, consistent customer
  voice across independent sources (corroboration), fresh data, timely complaint responses.

## Data collection etiquette

Official APIs and bulk downloads are preferred (CFPB uses the official public API). Where
scraping is necessary it is rate-limited (≥2s per host), respects `robots.txt`, and uses an
honest user-agent. Raw payloads are versioned under `data/raw/` with timestamps so any
number can be audited against the source as it appeared at collection time.

## Reproducibility

`python -m backend.pipeline` rebuilds the entire database from seeds + collectors and
recomputes every score. All constants live in `backend/scoring/constants.py`. Tests in
`tests/` pin the scoring behavior.
