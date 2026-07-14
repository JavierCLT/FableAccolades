"""Current fees, rates, and product leaders."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.charts import ranking_bar_chart
from components.layout import compact_disclaimer, page_setup

page_setup(
    "Fees & Products",
    icon="📋",
    subtitle="Current economics first. Expired values are excluded, never carried forward.",
    eyebrow="Current decision facts",
)

brokers = data.brokers()
facts = data.product_facts()
current = facts[facts["is_current"]].copy()
summary = data.product_fact_freshness_summary(facts)
economic = data.economic_value_rankings()


def _fact_rows(key: str) -> pd.DataFrame:
    return current[(current["fact_key"] == key) & current["value_numeric"].notna()].copy()


def _winner(key: str, direction: str = "max") -> pd.Series | None:
    rows = _fact_rows(key)
    if rows.empty:
        return None
    index = rows["value_numeric"].idxmax() if direction == "max" else rows["value_numeric"].idxmin()
    return rows.loc[index]


def _winner_rows(key: str, direction: str = "max") -> pd.DataFrame:
    rows = _fact_rows(key)
    if rows.empty:
        return rows
    winning_value = rows["value_numeric"].max() if direction == "max" else rows["value_numeric"].min()
    return rows[rows["value_numeric"].eq(winning_value)].copy()


def _money(value: float) -> str:
    return f"${value:g}"


default_cash = _winner("default_sweep_apy_pct")
best_cash = _winner("best_cash_apy_pct")
options = _winner_rows("options_contract_fee_usd", "min")
free_transfers = _fact_rows("outgoing_acat_fee_usd").query("value_numeric == 0")

default_cash_name = default_cash["broker_name"] if default_cash is not None else "Not enough current data"
default_cash_detail = (
    f"{default_cash['value_numeric']:.2f}% / verified {default_cash['as_of_date']}"
    if default_cash is not None
    else "No value inside the seven-day verification window"
)
best_cash_name = best_cash["broker_name"] if best_cash is not None else "Not enough current data"
best_cash_detail = (
    f"{best_cash['value_numeric']:.2f}% / conditions may apply"
    if best_cash is not None
    else "No value inside the seven-day verification window"
)
if options.empty:
    options_name = "Not enough current data"
    options_detail = "No value inside the 30-day verification window"
elif len(options) == 1:
    options_name = options.iloc[0]["broker_name"]
    options_detail = f"{_money(float(options.iloc[0]['value_numeric']))} per contract before regulatory fees"
else:
    options_name = f"{len(options)} brokers tie"
    options_detail = f"{_money(float(options.iloc[0]['value_numeric']))} per contract before regulatory fees"

st.markdown(
    f"""
    <div class="bbi-kpi-grid">
      <div class="bbi-kpi primary"><span>Best automatic cash yield</span><strong>{default_cash_name}</strong><small>{default_cash_detail}</small></div>
      <div class="bbi-kpi"><span>Best available cash yield</span><strong>{best_cash_name}</strong><small>{best_cash_detail}</small></div>
      <div class="bbi-kpi"><span>Lowest options commission</span><strong>{options_name}</strong><small>{options_detail}</small></div>
      <div class="bbi-kpi"><span>No transfer-out fee</span><strong>{len(free_transfers)} brokers</strong><small>verified inside the 30-day fee SLA</small></div>
    </div>
    """,
    unsafe_allow_html=True,
)

overview_left, overview_right = st.columns([0.82, 1.18])
with overview_left:
    st.markdown(
        '<div class="bbi-panel-heading"><span>Economic value</span><strong>Fees, cash and banking integration combined</strong></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        ranking_bar_chart(economic, limit=11, height=440),
        width="stretch",
        key="economic_ranking",
    )

with overview_right:
    st.markdown(
        '<div class="bbi-panel-heading"><span>Cash and margin</span><strong>Blank means the verification window expired</strong></div>',
        unsafe_allow_html=True,
    )
    rate_keys = {
        "default_sweep_apy_pct": "Automatic cash",
        "best_cash_apy_pct": "Best available",
        "margin_rate_pct": "Margin APR",
    }
    rate_view = current[current["fact_key"].isin(rate_keys)].copy()
    rate_view["Metric"] = rate_view["fact_key"].map(rate_keys)
    rate_view["Rate"] = rate_view["value_numeric"].map(lambda value: f"{value:.2f}%")
    rate_table = rate_view.pivot_table(
        index="broker_name", columns="Metric", values="Rate", aggfunc="first"
    ).reindex(brokers["name"])
    rate_dates = rate_view.groupby("broker_name")["as_of_date"].max().reindex(brokers["name"])
    rate_table["Latest verification"] = rate_dates
    rate_table = rate_table.rename_axis("Broker").reset_index()
    st.dataframe(
        rate_table,
        width="stretch",
        height=440,
        hide_index=True,
        column_config={"Broker": st.column_config.TextColumn(width="medium")},
    )

st.markdown(
    '<div class="bbi-panel-heading"><span>Trading and account fees</span><strong>Comparable current charges across all eleven brokers</strong></div>',
    unsafe_allow_html=True,
)
fee_keys = {
    "stock_etf_commission_usd": "Stock / ETF",
    "options_contract_fee_usd": "Options contract",
    "outgoing_acat_fee_usd": "Transfer out",
    "account_fee_usd": "Account fee",
}
fee_view = current[current["fact_key"].isin(fee_keys)].copy()
fee_view["Fee"] = fee_view["fact_key"].map(fee_keys)
fee_view["Amount"] = fee_view["value_numeric"].map(_money)
fee_table = fee_view.pivot_table(
    index="broker_name", columns="Fee", values="Amount", aggfunc="first"
).reindex(brokers["name"])
fee_table = fee_table.rename_axis("Broker").reset_index()
st.dataframe(fee_table, width="stretch", hide_index=True, height=430)

st.markdown(
    '<div class="bbi-panel-heading"><span>Product access</span><strong>A quick market map of the capabilities investors ask for most</strong></div>',
    unsafe_allow_html=True,
)
product_keys = {
    "fractional_shares_scope": ("Fractional investing", {0: "No", 1: "Limited", 2: "Stocks + ETFs"}),
    "banking_level": ("Banking integration", {0: "None", 1: "Basic", 2: "Strong", 3: "Full"}),
    "crypto_trading": ("Crypto", {0: "No", 1: "Yes"}),
    "futures_trading": ("Futures", {0: "No", 1: "Yes"}),
    "international_trading": ("International", {0: "No", 1: "Yes"}),
    "bonds_cds_available": ("Bonds / CDs", {0: "No", 1: "Yes"}),
    "human_advisor_access": ("Human advisor", {0: "No", 1: "Yes"}),
}
product_view = current[current["fact_key"].isin(product_keys)].copy()
product_view["Product"] = product_view["fact_key"].map(lambda key: product_keys[key][0])
product_view["Access"] = product_view.apply(
    lambda row: product_keys[row["fact_key"]][1].get(int(row["value_numeric"]), "Unknown"),
    axis=1,
)
product_table = product_view.pivot_table(
    index="broker_name", columns="Product", values="Access", aggfunc="first"
).reindex(brokers["name"])
product_table = product_table.rename_axis("Broker").reset_index()
st.dataframe(product_table, width="stretch", hide_index=True, height=430)

st.caption(
    f"{summary['fresh']} of {summary['total']} facts are currently inside their verification window. "
    "Rates expire after 7 days, margin after 14 days, fees after 30 days, and product features after 90 days."
)

compact_disclaimer()
