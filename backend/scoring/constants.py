"""All scoring constants in one place, mirrored in docs/scoring_logic.md.

Component blend inside each dimension (renormalized over available components):
objective facts dominate, customer voice second, expert claims third. This is the
per-dimension expression of the recommended pillar framework (see scoring_logic.md
for the mapping, including how Pricing and Service map to their dimensions).
"""

COMPONENT_WEIGHTS = {
    "fact": 0.45,      # Objective Product Fit + Pricing/Economic Value
    "customer": 0.35,  # Customer Voice + Service & Friction Signals
    "expert": 0.20,    # Expert Consensus (after disagreement penalty)
}

# Expert disagreement: gap thresholds on the 0-100 normalized scale.
CONTRADICTION_MODERATE = 15.0
CONTRADICTION_SIGNIFICANT = 25.0
CONTRADICTION_SEVERE = 35.0

# Max points subtracted from a dimension score due to expert contradictions.
MAX_CONTRADICTION_PENALTY = 10.0

# Staleness: volatile facts older than this start losing score (linear, capped).
STALENESS_GRACE_DAYS = 180
MAX_STALENESS_PENALTY = 6.0
VOLATILE_FACT_KEYS = {
    "default_sweep_apy_pct", "best_cash_apy_pct", "margin_rate_pct",
}

# Recency decay half-life-ish constant (days) for evidence weighting.
RECENCY_TAU_DAYS = 540.0

# Confidence sub-score caps (sum to 100).
CONF_VOLUME_MAX = 40.0
CONF_QUALITY_MAX = 20.0
CONF_RECENCY_MAX = 25.0
CONF_CORROBORATION_MAX = 15.0
CONF_VOLUME_TARGET = 6  # evidence items for full volume credit

# Customer-voice signal scaling: score = 50 + 45*tanh(signal / CUSTOMER_SIGNAL_SCALE)
CUSTOMER_SIGNAL_SCALE = 6.0

# Momentum: bounded composite adjustment from CFPB 12m-vs-prior-12m complaint trend.
MOMENTUM_MAX_ABS = 3.0

# CFPB friction: complaints per $B AUM (trailing 12m) mapped to a 0-100 friction score,
# folded into the customer component of the customer_support dimension.
CFPB_FRICTION_BASELINE_RATE = 0.05   # complaints per $B/yr treated as "excellent"
CFPB_FRICTION_BASE_SCORE = 85.0
CFPB_FRICTION_SLOPE = 18.0           # points lost per decade (log10) above baseline
CFPB_FRICTION_MIN = 10.0
CFPB_FRICTION_WEIGHT = 0.3           # share of the customer component on customer_support
