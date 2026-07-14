import json
from pathlib import Path


SEED_PATH = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "database"
    / "seeds"
    / "relationship_benefits.json"
)


def test_relationship_benefits_are_current_and_source_linked():
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    facts = seed["facts"]

    assert seed["defaults"]["retrieval_date"] == "2026-07-13"
    assert len(facts) == 16
    assert all(fact["as_of"] == "2026-07-13" for fact in facts)
    assert all(fact["url"].startswith("https://") for fact in facts)
    assert all(fact["confidence"] == "high" for fact in facts)


def test_relationship_benefit_values_match_the_program_contracts():
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    values = {
        (fact["broker"], fact["key"]): fact["value_numeric"]
        for fact in seed["facts"]
    }

    assert values[("merrill", "bofa_rewards_member_card_bonus_pct")] == 10
    assert values[("merrill", "bofa_rewards_premier_card_bonus_pct")] == 75
    assert values[("merrill", "bofa_rewards_premier_balance_usd")] == 1_000_000
    assert values[("fidelity", "relationship_card_cashback_pct")] == 2
    assert values[("fidelity", "relationship_card_annual_cost_usd")] == 0
    assert values[("robinhood", "relationship_card_cashback_pct")] == 3
    assert values[("robinhood", "relationship_card_annual_cost_usd")] == 50
    assert values[("schwab", "schwab_platinum_appreciation_10m_usd")] == 1_000
