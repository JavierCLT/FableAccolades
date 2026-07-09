from backend.scoring.fact_rules import fact_component


def test_costs_fees_zero_everything_is_top():
    facts = {
        "stock_etf_commission_usd": 0,
        "options_contract_fee_usd": 0,
        "margin_rate_pct": 6.0,
        "account_fee_usd": 0,
    }
    score = fact_component("costs_fees", facts)
    assert score is not None and score > 95


def test_costs_fees_partial_facts_still_scores():
    assert fact_component("costs_fees", {"stock_etf_commission_usd": 0}) == 100.0


def test_costs_fees_no_facts_returns_none():
    assert fact_component("costs_fees", {}) is None


def test_cash_yield_default_beats_optin():
    # Frictionless money-market default...
    auto = fact_component("cash_yield", {"default_sweep_apy_pct": 4.0, "best_cash_apy_pct": 4.0})
    # ...must beat identical yield that requires manual action from a near-zero default.
    manual = fact_component("cash_yield", {"default_sweep_apy_pct": 0.05, "best_cash_apy_pct": 4.0})
    assert auto > manual + 20


def test_acat_fee_ladder_is_monotonic():
    scores = [
        fact_component("transfer_acat", {"outgoing_acat_fee_usd": fee})
        for fee in (0, 50, 75, 100, 150)
    ]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 95.0


def test_fractional_levels():
    full = fact_component("fractional_shares", {"fractional_shares_scope": 2})
    partial = fact_component("fractional_shares", {"fractional_shares_scope": 1})
    none = fact_component("fractional_shares", {"fractional_shares_scope": 0})
    assert full > partial > none


def test_unknown_dimension_has_no_fact_rule():
    assert fact_component("ease_of_use", {"anything": 1}) is None
