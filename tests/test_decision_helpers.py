import pandas as pd
import pytest

from frontend.streamlit_app.components.decision import (
    adjusted_weights,
    broker_edges,
    eligible_broker_slugs,
)


def test_priority_boosts_are_normalized_and_directional():
    base = {"costs_fees": 0.5, "cash_yield": 0.5}
    boosted = adjusted_weights(base, "Keep costs low")
    assert sum(boosted.values()) == pytest.approx(1.0)
    assert boosted["costs_fees"] > boosted["cash_yield"]


def test_requirements_use_objective_facts_and_combine():
    facts = pd.DataFrame(
        [
            {"broker_slug": "a", "fact_key": "outgoing_acat_fee_usd", "value_numeric": 0},
            {"broker_slug": "a", "fact_key": "support_24_7", "value_numeric": 1},
            {"broker_slug": "b", "fact_key": "outgoing_acat_fee_usd", "value_numeric": 75},
            {"broker_slug": "b", "fact_key": "support_24_7", "value_numeric": 1},
        ]
    )
    assert eligible_broker_slugs(facts, ["24/7 support"]) == {"a", "b"}
    assert eligible_broker_slugs(facts, ["24/7 support", "No transfer-out fee"]) == {"a"}


def test_edges_prioritize_weighted_difference_from_field():
    scores = pd.DataFrame(
        [
            {"broker_slug": "a", "dim_slug": "costs_fees", "dim_name": "Costs", "score": 90},
            {"broker_slug": "a", "dim_slug": "mobile_app", "dim_name": "Mobile", "score": 40},
            {"broker_slug": "b", "dim_slug": "costs_fees", "dim_name": "Costs", "score": 50},
            {"broker_slug": "b", "dim_slug": "mobile_app", "dim_name": "Mobile", "score": 60},
        ]
    )
    strengths, risk = broker_edges(scores, {"costs_fees": 0.8, "mobile_app": 0.2}, "a")
    assert strengths[0]["slug"] == "costs_fees"
    assert risk["slug"] == "mobile_app"
