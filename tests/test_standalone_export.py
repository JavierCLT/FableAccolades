from pathlib import Path

from scripts.export_standalone_dashboard import OUTPUT_PATH, TEMPLATE_PATH, payload


def test_standalone_payload_contains_all_decision_surfaces():
    exported = payload()

    assert len(exported["brokers"]) == 11
    assert len(exported["dimensions"]) == 16
    assert exported["profilePresets"]["All-Around"] == "long_term"
    assert exported["dimensionScores"]
    assert exported["facts"]
    fact_keys = {row["fact_key"] for row in exported["facts"]}
    assert {
        "bofa_rewards_member_card_bonus_pct",
        "bofa_rewards_premier_card_bonus_pct",
        "relationship_card_cashback_pct",
        "relationship_card_annual_cost_usd",
        "schwab_platinum_appreciation_250k_usd",
    } <= fact_keys
    assert exported["customerRankings"]
    assert exported["economicRankings"]
    assert exported["reviewRatings"]
    assert exported["sentiment"]
    assert len(exported["evidence"]) >= 500
    assert len(exported["sources"]) == 28
    assert all(source["incentive"] for source in exported["sources"])
    assert exported["withdrawnReviews"]
    assert exported["verificationRuns"]
    assert set(exported["documents"]) == {
        "methodology",
        "scoring",
        "sources",
        "limitations",
    }
    assert exported["executionQuality"]["available"] is False


def test_standalone_template_is_self_contained_after_export():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = OUTPUT_PATH.read_text(encoding="utf-8")

    assert template.count("/*__PLOTLY_BUNDLE__*/") == 1
    assert template.count("/*__DASHBOARD_DATA__*/") == 1
    assert "/*__PLOTLY_BUNDLE__*/" not in rendered
    assert "/*__DASHBOARD_DATA__*/" not in rendered
    assert '<script src="http' not in rendered
    assert Path(OUTPUT_PATH).stat().st_size > 4_000_000
    assert 'data-page="cost"' in rendered
    assert 'data-page="research"' in rendered
    assert "function renderResearch()" in rendered
    assert "What would each broker cost you?" in rendered
    assert "Include relationship and card benefits" in rendered
    assert "function relationshipBenefit(slug)" in rendered
