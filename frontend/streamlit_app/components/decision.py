"""Pure decision helpers used by the broker matcher and comparison views."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

PROFILE_PRESETS: dict[str, str] = {
    "All-Around": "long_term",
    "Retirement": "retirement",
    "Active Trader": "active_trader",
    "Banking Integration": "banking_focused",
    "Cash": "cash_sensitive",
    "Beginner": "beginner",
}

PRIORITY_BOOSTS: dict[str, dict[str, float]] = {
    "Balanced": {},
    "Keep costs low": {
        "costs_fees": 0.12,
        "transfer_acat": 0.06,
        "cash_yield": 0.03,
    },
    "Maximize idle cash": {
        "cash_yield": 0.18,
        "banking_integration": 0.05,
        "costs_fees": 0.02,
    },
    "Simple daily use": {
        "ease_of_use": 0.12,
        "mobile_app": 0.08,
        "customer_support": 0.06,
    },
    "Power-user tools": {
        "trading_tools": 0.14,
        "product_breadth": 0.08,
        "reliability": 0.06,
    },
    "Retirement support": {
        "retirement_rollover": 0.14,
        "advisory_options": 0.07,
        "research_education": 0.05,
    },
}

# label -> (fact key, comparison, threshold)
HARD_REQUIREMENTS: dict[str, tuple[str, str, float]] = {
    "No transfer-out fee": ("outgoing_acat_fee_usd", "eq", 0.0),
    "Fractional stocks and ETFs": ("fractional_shares_scope", "gte", 2.0),
    "24/7 support": ("support_24_7", "eq", 1.0),
    "Physical branches": ("branch_count", "gt", 0.0),
    "Crypto trading": ("crypto_trading", "eq", 1.0),
    "Futures trading": ("futures_trading", "eq", 1.0),
    "Human advisor access": ("human_advisor_access", "eq", 1.0),
}


def adjusted_weights(base: Mapping[str, float], priority: str) -> dict[str, float]:
    """Apply a transparent priority boost and normalize the result to one."""
    result = {slug: max(0.0, float(weight)) for slug, weight in base.items()}
    for slug, boost in PRIORITY_BOOSTS.get(priority, {}).items():
        result[slug] = result.get(slug, 0.0) + boost
    total = sum(result.values())
    if total <= 0:
        return result
    return {slug: value / total for slug, value in result.items()}


def eligible_broker_slugs(facts: pd.DataFrame, requirements: Sequence[str]) -> set[str]:
    """Return brokers satisfying every selected objective-fact requirement."""
    all_slugs = set(facts["broker_slug"].dropna().astype(str))
    if not requirements:
        return all_slugs

    wide = facts.pivot_table(
        index="broker_slug", columns="fact_key", values="value_numeric", aggfunc="first"
    )
    eligible = set(wide.index.astype(str))
    for label in requirements:
        rule = HARD_REQUIREMENTS.get(label)
        if rule is None:
            continue
        key, comparison, threshold = rule
        if key not in wide.columns:
            return set()
        values = wide[key]
        if comparison == "eq":
            passing = values == threshold
        elif comparison == "gte":
            passing = values >= threshold
        elif comparison == "gt":
            passing = values > threshold
        else:
            raise ValueError(f"Unknown requirement comparison: {comparison}")
        eligible &= set(wide.index[passing.fillna(False)].astype(str))
    return eligible


def broker_edges(
    dimension_scores: pd.DataFrame,
    weights: Mapping[str, float],
    broker_slug: str,
) -> tuple[list[dict], dict | None]:
    """Return the most decision-relevant advantages and trade-off versus the field."""
    medians = dimension_scores.groupby("dim_slug")["score"].median()
    sub = dimension_scores[dimension_scores["broker_slug"] == broker_slug]
    rows: list[dict] = []
    for _, row in sub.iterrows():
        weight = float(weights.get(row["dim_slug"], 0.0))
        edge = (float(row["score"]) - float(medians[row["dim_slug"]])) * weight
        rows.append(
            {
                "slug": row["dim_slug"],
                "name": row["dim_name"],
                "score": float(row["score"]),
                "edge": edge,
                "weight": weight,
            }
        )
    rows.sort(key=lambda item: item["edge"], reverse=True)
    strengths = [item for item in rows if item["edge"] > 0][:2]
    if not strengths:
        strengths = rows[:2]
    risk = min(rows, key=lambda item: item["edge"], default=None)
    return strengths, risk


def top_weighted_dimensions(weights: Mapping[str, float], limit: int = 5) -> list[str]:
    return [slug for slug, _ in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:limit]]


def confidence_label(value: float) -> str:
    if value >= 70:
        return "High confidence"
    if value >= 45:
        return "Moderate confidence"
    return "Low confidence"
