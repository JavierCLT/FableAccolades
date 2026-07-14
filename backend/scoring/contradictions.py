"""Detection of expert-vs-expert contradictions on the same broker and dimension.

A contradiction is a pairwise gap between two publishers' normalized scores (0-100)
for the same broker+dimension at or above the moderate threshold. Severity buckets and
the score penalty are defined in constants.py and documented in docs/scoring_logic.md.
"""

from __future__ import annotations

from itertools import combinations

from backend.scoring import constants as C


def severity_for_gap(gap: float) -> str | None:
    if gap >= C.CONTRADICTION_SEVERE:
        return "severe"
    if gap >= C.CONTRADICTION_SIGNIFICANT:
        return "significant"
    if gap >= C.CONTRADICTION_MODERATE:
        return "moderate"
    return None


def contradiction_penalty(max_gap: float | None) -> float:
    """Points subtracted from a dimension's expert component for internal disagreement."""
    if max_gap is None or max_gap <= C.CONTRADICTION_MODERATE:
        return 0.0
    return round(min(C.MAX_CONTRADICTION_PENALTY, (max_gap - C.CONTRADICTION_MODERATE) * 0.4), 2)


def find_pairwise_contradictions(
    ratings: list[dict],
) -> list[dict]:
    """ratings: [{source_id, score, evidence_id}, ...] for one broker+dimension cell.
    Returns contradiction dicts for every pair at/above the moderate threshold."""
    out = []
    for a, b in combinations(ratings, 2):
        if a["source_id"] == b["source_id"]:
            continue
        gap = abs(a["score"] - b["score"])
        severity = severity_for_gap(gap)
        if severity is None:
            continue
        lo, hi = (a, b) if a["score"] <= b["score"] else (b, a)
        out.append(
            {
                "source_a_id": lo["source_id"],
                "source_b_id": hi["source_id"],
                "score_a": lo["score"],
                "score_b": hi["score"],
                "gap": round(gap, 2),
                "severity": severity,
                "evidence_a_id": lo["evidence_id"],
                "evidence_b_id": hi["evidence_id"],
            }
        )
    return out
