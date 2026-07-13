"""Deterministic rules mapping objective product facts to 0-100 dimension fact-components.

Every rule below is documented in docs/scoring_logic.md. Rules only consume facts that
exist in the database (each backed by evidence); missing facts simply reduce coverage,
they are never invented. Dimensions without objective-fact rules (ease of use, research,
trading tools, reliability) return no fact component and rely on expert + customer data.
"""

from __future__ import annotations

Facts = dict[str, float | None]  # fact_key -> value_numeric


def _get(facts: Facts, key: str) -> float | None:
    return facts.get(key)


def score_costs_fees(facts: Facts) -> float | None:
    parts: list[tuple[float, float]] = []  # (score, weight)
    commission = _get(facts, "stock_etf_commission_usd")
    if commission is not None:
        parts.append((100.0 if commission == 0 else 60.0 if commission <= 5 else 30.0, 0.35))
    opt = _get(facts, "options_contract_fee_usd")
    if opt is not None:
        parts.append((100.0 if opt == 0 else 75.0 if opt <= 0.65 else 55.0 if opt <= 1.0 else 40.0, 0.20))
    margin = _get(facts, "margin_rate_pct")
    if margin is not None:
        parts.append((95.0 if margin <= 7 else 75.0 if margin <= 10 else 55.0 if margin <= 12.5 else 40.0, 0.20))
    acct = _get(facts, "account_fee_usd")
    if acct is not None:
        parts.append((100.0 if acct == 0 else 70.0 if acct <= 25 else 40.0, 0.25))
    if not parts:
        return None
    total_w = sum(w for _, w in parts)
    return sum(s * w for s, w in parts) / total_w


def _apy_to_score(apy: float, floor: float, slope: float) -> float:
    return min(95.0, floor + apy * slope)


def score_cash_yield(facts: Facts) -> float | None:
    default_apy = _get(facts, "default_sweep_apy_pct")
    best_apy = _get(facts, "best_cash_apy_pct")
    if default_apy is None and best_apy is None:
        return None
    default_score = _apy_to_score(default_apy, 20.0, 20.0) if default_apy is not None else 20.0
    best_score = _apy_to_score(best_apy, 25.0, 17.0) if best_apy is not None else default_score
    # Default (frictionless) yield dominates; opt-in yield gets partial credit because it
    # requires action (manual fund purchases, subscriptions, or separate accounts).
    return 0.65 * default_score + 0.35 * best_score


def score_transfer_acat(facts: Facts) -> float | None:
    fee = _get(facts, "outgoing_acat_fee_usd")
    if fee is None:
        return None
    return 95.0 if fee == 0 else 65.0 if fee <= 50 else 50.0 if fee <= 75 else 38.0 if fee <= 100 else 25.0


def score_fractional_shares(facts: Facts) -> float | None:
    level = _get(facts, "fractional_shares_scope")
    if level is None:
        return None
    return {2.0: 92.0, 1.0: 60.0, 0.5: 45.0, 0.0: 12.0}.get(level, 12.0)


def score_retirement_rollover(facts: Facts) -> float | None:
    match = _get(facts, "ira_match_pct")
    if match is None:
        return None
    return min(90.0, 50.0 + match * 15.0)


def score_advisory_options(facts: Facts) -> float | None:
    robo_fee = _get(facts, "robo_advisor_fee_pct")
    human = _get(facts, "human_advisor_access")
    if robo_fee is None and human is None:
        return None
    score = 30.0
    if robo_fee is not None:
        score = 60.0
        if robo_fee <= 0.0:
            score += 12.0  # zero-fee robo, but cash-allocation caveat (see scoring docs)
        elif robo_fee <= 0.2:
            score += 15.0
        elif robo_fee <= 0.3:
            score += 10.0
        elif robo_fee <= 0.4:
            score += 8.0
    if human:
        score += 20.0
    return min(100.0, score)


def score_customer_support(facts: Facts) -> float | None:
    always_on = _get(facts, "support_24_7")
    branches = _get(facts, "branch_count")
    if always_on is None and branches is None:
        return None
    score = 40.0
    if always_on:
        score += 25.0
    if branches:
        score += 25.0 if branches >= 100 else 20.0
    return score


def score_banking_integration(facts: Facts) -> float | None:
    level = _get(facts, "banking_level")
    if level is None:
        return None
    return max(5.0, min(95.0, level * 30.0 + 5.0))


def score_product_breadth(facts: Facts) -> float | None:
    flags = [_get(facts, k) for k in
             ("crypto_trading", "futures_trading", "international_trading", "bonds_cds_available")]
    known = [f for f in flags if f is not None]
    if not known:
        return None
    return 35.0 + 15.0 * sum(1 for f in known if f)


def score_security(facts: Facts) -> float | None:
    level = _get(facts, "security_level")
    if level is None:
        return None
    return {2.0: 90.0, 1.0: 60.0, 0.0: 30.0}.get(level, 30.0)


def score_tax_reporting(facts: Facts) -> float | None:
    level = _get(facts, "tax_lot_control")
    if level is None:
        return None
    return {2.0: 90.0, 1.0: 55.0, 0.0: 25.0}.get(level, 25.0)


FACT_RULES = {
    "costs_fees": score_costs_fees,
    "cash_yield": score_cash_yield,
    "transfer_acat": score_transfer_acat,
    "fractional_shares": score_fractional_shares,
    "retirement_rollover": score_retirement_rollover,
    "advisory_options": score_advisory_options,
    "customer_support": score_customer_support,
    "banking_integration": score_banking_integration,
    "product_breadth": score_product_breadth,
    "security": score_security,
    "tax_reporting": score_tax_reporting,
    # mobile_app fact component comes from aggregate app-store ratings (see engine).
    # ease_of_use / research_education / trading_tools / reliability: no objective-fact
    # rule exists — those dimensions rely on expert + customer components.
}


def fact_component(dimension_slug: str, facts: Facts) -> float | None:
    rule = FACT_RULES.get(dimension_slug)
    return None if rule is None else rule(facts)
