# Scoring Logic (full specification)

Everything below is implemented in `backend/scoring/` and covered by `tests/`. Constants
live in `backend/scoring/constants.py`. Scores are 0–100 throughout.

## 1. Component blend per dimension

```
dimension_score = blend(fact 0.45, customer 0.35, expert 0.20) − staleness_penalty
```

Weights renormalize over available components (e.g. a dimension with no fact rule uses
customer 0.35/0.55 and expert 0.20/0.55). The blend maps to the recommended pillar
framework as follows:

| Recommended pillar | Where it lives here |
|---|---|
| Objective Product Fit 30–35% | fact component (45% of each dimension, which includes non-pricing dimensions) |
| Customer Voice 25–30% | customer component (35%) |
| Expert Consensus 10–15% | expert component (20%, after disagreement penalty) |
| Pricing / Economic Value 10–15% | the *Costs & Fees* and *Cash Yield* dimensions (persona-weighted) |
| Service & Friction Signals 10% | the *Customer Support* dimension + CFPB friction blend |
| Recent Momentum 5% | bounded ±3-point CFPB momentum adjustment on composites |

This per-dimension formulation was chosen (the spec allows refinement) because persona
weights operate on dimensions; it keeps a single transparent formula everywhere.

## 2. Fact component (objective, rules-based)

Defined in `fact_rules.py`. Highlights (full ladders in code, one rule per dimension):

- **Costs & fees** — weighted sub-scores: commission (35%), options contract fee (20%),
  margin rate (20%), account fee (25%). E.g. $0 commission → 100; margin ≤7% → 95, ≤10% → 75,
  ≤12.5% → 55, else 40.
- **Cash yield** — `0.65 × default_sweep_score + 0.35 × best_available_score`. Default
  (frictionless) yield dominates deliberately: yield requiring manual fund purchases,
  subscriptions, or separate accounts earns only partial credit.
  APY→score: `min(95, 20 + 20·APY)` for default, `min(95, 25 + 17·APY)` for best-available.
- **Transfer/ACAT** — $0 → 95, ≤$50 → 65, ≤$75 → 50, ≤$100 → 38, else 25.
- **Fractional shares** — stocks+ETFs → 92, S&P-500-only → 60, own-ETFs-only → 45, none → 12.
- **Retirement** — `min(90, 50 + 15·ira_match_pct)`; the rest of the dimension comes from
  expert + customer components.
- **Advisory** — robo available 60 base, fee bonuses (≤0.20% +15, ≤0.30% +10, ≤0.40% +8,
  zero-fee +12 with cash-drag caveat), human advisors +20.
- **Support** — base 40, 24/7 +25, branches +20 (+25 if ≥100).
- **Banking** — level 0–3 → 5–95.
- **Breadth** — 35 + 15 per asset class (crypto, futures, international, bonds/CDs).
- **Security / Tax** — level ladders 30/60/90 and 25/55/90.
- **Mobile app** — objective input is the log-review-count-weighted mean of public
  app-store aggregate ratings, normalized ×20.
- **No fact rule** (rely on expert + customer): ease of use, research & education,
  trading tools, reliability.

## 3. Customer component

Each theme row (complaint/praise/opinion) contributes to a signed signal:

```
weight  = √volume × recency × source_quality       (recency = e^(−age_days/540))
signal += +weight                 if praise
signal += −weight × severity/3    if complaint      (severity 1–5)
signal += 0                       if mixed/opinion  (still counts as evidence)
score   = 50 + 45·tanh(signal / 6)
```

For **customer support** only, when the broker has a CFPB entity and disclosed client
assets, a CFPB friction score is blended in at 30%:

```
rate     = complaints_last_12m / AUM_$B
friction = 95                                if rate ≤ 0.05
         = max(10, 85 − 18·log10(rate/0.05)) otherwise
```

No AUM disclosed → no friction score (the denominator is never guessed).

## 4. Expert component

Quality×confidence-weighted mean of normalized ratings (`rating/scale × 100`) for the
dimension. If a publisher has no dimension-level rating, overall ratings are used as a
fallback at reduced evidence quality (0.7×). Then:

```
gap     = max(scores) − min(scores)
penalty = min(10, 0.4 × (gap − 15))   if gap > 15, else 0
expert  = weighted_mean − penalty
```

## 5. Contradictions

All source pairs per broker×dimension (and overall): gap ≥ 15 → *moderate*, ≥ 25 →
*significant*, ≥ 35 → *severe*. Stored with both evidence rows and displayed in the matrix.

## 6. Staleness

Volatile facts (`default_sweep_apy_pct`, `best_cash_apy_pct`, `margin_rate_pct`) older than
180 days: penalty `min(6, 2 × (age−180)/90)` points on the dimension score; age also drags
the recency confidence sub-score.

## 7. Confidence (0–100)

```
volume        = min(40, evidence_count / 6 × 40)
quality       = mean(source quality_weight × confidence_factor) × 20
recency       = mean(e^(−age/540)) × 25
corroboration = components_present/3 × 10 + max(0, 1 − gap/25) × 5
confidence    = volume + quality + recency + corroboration   (capped at 100)
```

Confidence factors: high 1.0, medium 0.8, low 0.55.

## 8. Persona composites

```
persona_score = Σ(weight_d × dimension_score_d) / Σ(weight_d) + momentum
momentum      = −3 × tanh( ln(recent_12m / prior_12m) / ln 2 )   (CFPB; needs ≥20 prior
                complaints; 0 when no CFPB entity)
```

Default weights per persona are in `backend/database/seeds/personas.json` (each sums to
1.0, enforced at load). The UI recomputes live with user-adjusted weights using the exact
same formula.
