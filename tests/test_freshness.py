from datetime import date

from backend.freshness import (
    age_days,
    blocks_scoring,
    freshness_status,
    policy_for,
    summarize,
)


TODAY = date(2026, 7, 13)


def test_volatile_rate_expires_after_seven_days() -> None:
    assert freshness_status("default_sweep_apy_pct", "2026-07-06", today=TODAY) == "fresh"
    assert freshness_status("default_sweep_apy_pct", "2026-07-05", today=TODAY) == "stale"
    assert blocks_scoring("default_sweep_apy_pct", "2026-07-05", today=TODAY)


def test_every_fact_has_a_finite_policy() -> None:
    assert policy_for("support_24_7").max_age_days == 90
    assert age_days("2026-07-09", today=TODAY) == 4


def test_summary_reports_coverage() -> None:
    result = summarize(
        [
            {"fact_key": "default_sweep_apy_pct", "as_of_date": "2026-07-06"},
            {"fact_key": "margin_rate_pct", "as_of_date": "2025-06-30"},
            {"fact_key": "support_24_7", "as_of_date": "not-a-date"},
        ],
        today=TODAY,
    )
    assert result == {"total": 3, "fresh": 1, "stale": 1, "invalid": 1, "coverage_pct": 33.3}
