"""Freshness contracts for structured brokerage facts.

Freshness is a gate, not a cosmetic warning. Facts that can move with rates or broker
repricing expire quickly and are excluded from scoring after their SLA. Slower-moving
facts remain visible for longer, but every fact has a finite verification window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Mapping


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_days: int
    cadence: str
    blocks_scoring: bool = True


POLICIES: dict[str, FreshnessPolicy] = {
    "default_sweep_apy_pct": FreshnessPolicy(7, "daily"),
    "best_cash_apy_pct": FreshnessPolicy(7, "daily"),
    "margin_rate_pct": FreshnessPolicy(14, "weekly"),
    "ira_match_pct": FreshnessPolicy(30, "monthly"),
    "options_contract_fee_usd": FreshnessPolicy(30, "monthly"),
    "outgoing_acat_fee_usd": FreshnessPolicy(30, "monthly"),
    "account_fee_usd": FreshnessPolicy(30, "monthly"),
    "robo_advisor_fee_pct": FreshnessPolicy(30, "monthly"),
    "best_cash_minimum_usd": FreshnessPolicy(7, "daily"),
}

DEFAULT_POLICY = FreshnessPolicy(90, "quarterly")


def policy_for(fact_key: str) -> FreshnessPolicy:
    return POLICIES.get(fact_key, DEFAULT_POLICY)


def parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def age_days(as_of_date: object, *, today: date | None = None) -> int | None:
    observed = parse_date(as_of_date)
    if observed is None:
        return None
    return max(0, ((today or date.today()) - observed).days)


def freshness_status(fact_key: str, as_of_date: object, *, today: date | None = None) -> str:
    age = age_days(as_of_date, today=today)
    if age is None:
        return "invalid"
    return "fresh" if age <= policy_for(fact_key).max_age_days else "stale"


def is_fresh(fact_key: str, as_of_date: object, *, today: date | None = None) -> bool:
    return freshness_status(fact_key, as_of_date, today=today) == "fresh"


def blocks_scoring(fact_key: str, as_of_date: object, *, today: date | None = None) -> bool:
    policy = policy_for(fact_key)
    return policy.blocks_scoring and not is_fresh(fact_key, as_of_date, today=today)


def summarize(rows: Iterable[Mapping[str, object]], *, today: date | None = None) -> dict[str, int | float]:
    total = fresh = stale = invalid = 0
    for row in rows:
        total += 1
        status = freshness_status(str(row["fact_key"]), row.get("as_of_date"), today=today)
        if status == "fresh":
            fresh += 1
        elif status == "stale":
            stale += 1
        else:
            invalid += 1
    coverage = round((fresh / total * 100.0) if total else 0.0, 1)
    return {"total": total, "fresh": fresh, "stale": stale, "invalid": invalid, "coverage_pct": coverage}
