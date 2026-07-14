from backend.collectors.volatile_facts.collector import parse_merrill_rate_sheet


SAMPLE = """
Annual Percentage Yield as of 7/10/2026
Merrill Lynch Bank Deposit Program --- Tier 1 (Less than $250,000) 0.01%
Merrill Lynch Bank Deposit Program --- Tier 2 ($250,000 - $999,999) 0.01%
Preferred Deposit ($100,000 minimum initial deposit requirement)
Annual Percentage Yield as of 7/10/2026
Less than $100,000 2.89%
"""


def test_parse_merrill_rate_sheet() -> None:
    facts = {fact.key: fact for fact in parse_merrill_rate_sheet(SAMPLE)}
    assert facts["default_sweep_apy_pct"].value_numeric == 0.01
    assert facts["default_sweep_apy_pct"].as_of_date == "2026-07-10"
    assert facts["best_cash_apy_pct"].value_numeric == 2.89
    assert "$100,000 minimum" in facts["best_cash_apy_pct"].value_text
