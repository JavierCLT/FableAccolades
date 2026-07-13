"""Confidence scoring: how much evidence stands behind a dimension score (0-100).

Four documented sub-scores (see docs/scoring_logic.md):
  volume        (0-40): evidence count vs a target of CONF_VOLUME_TARGET items
  quality       (0-20): mean source quality_weight of the evidence used
  recency       (0-25): exponential decay of evidence age
  corroboration (0-15): independent component types present + expert agreement
"""

from __future__ import annotations

import math
from datetime import date

from backend.scoring import constants as C


def recency_weight(evidence_date: str | None, today: date | None = None) -> float:
    """Exponential decay weight in (0, 1] from an ISO date; unknown dates get 0.5."""
    if not evidence_date:
        return 0.5
    today = today or date.today()
    try:
        d = date.fromisoformat(str(evidence_date)[:10])
    except ValueError:
        return 0.5
    age_days = max(0, (today - d).days)
    return math.exp(-age_days / C.RECENCY_TAU_DAYS)


def confidence_score(
    *,
    evidence_count: int,
    avg_quality: float,
    avg_recency: float,
    components_present: int,
    expert_gap: float | None,
) -> float:
    """Combine sub-scores; all inputs already in natural units.

    avg_quality in [0,1]; avg_recency in (0,1]; components_present in {0..3};
    expert_gap = max pairwise gap between expert sources (0-100 scale) or None.
    """
    volume = min(C.CONF_VOLUME_MAX, evidence_count / C.CONF_VOLUME_TARGET * C.CONF_VOLUME_MAX)
    quality = max(0.0, min(1.0, avg_quality)) * C.CONF_QUALITY_MAX
    recency = max(0.0, min(1.0, avg_recency)) * C.CONF_RECENCY_MAX
    corroboration = components_present / 3.0 * (C.CONF_CORROBORATION_MAX - 5.0)
    if expert_gap is not None:
        # Agreement bonus shrinks to zero as the gap approaches the 'significant' threshold.
        agreement = max(0.0, 1.0 - expert_gap / C.CONTRADICTION_SIGNIFICANT) * 5.0
        corroboration += agreement
    return round(min(100.0, volume + quality + recency + corroboration), 1)
