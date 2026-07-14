"""Focused two- or three-broker comparison dashboard."""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.charts import dimension_heatmap, radar_chart
from components.decision import PROFILE_PRESETS, broker_edges, top_weighted_dimensions
from components.layout import compact_disclaimer, page_setup

page_setup(
    "Compare Brokers",
    icon="📈",
    subtitle="Two or three contenders, the differences that matter, and a direct verdict.",
    eyebrow="Decision workspace",
)

brokers = data.brokers()
personas = data.personas()
dimension_scores = data.dimension_scores()

controls = st.columns([1.25, 1])
with controls[0]:
    chosen = st.multiselect(
        "Brokers",
        brokers["name"].tolist(),
        default=[name for name in ["Fidelity", "Charles Schwab"] if name in brokers["name"].tolist()],
        max_selections=3,
        placeholder="Choose two or three",
    )
with controls[1]:
    preset = st.selectbox("Investor situation", list(PROFILE_PRESETS), index=0)

if len(chosen) < 2:
    st.info("Choose at least two brokers.")
    st.stop()

slug_lookup = brokers.set_index("name")["slug"].to_dict()
slugs = [slug_lookup[name] for name in chosen]
persona = personas[personas["slug"] == PROFILE_PRESETS[preset]].iloc[0]
weights = data.persona_weights(int(persona["id"]))
rankings = data.compute_persona_scores(weights).reset_index(drop=True)
rankings["rank"] = range(1, len(rankings) + 1)
selected_rankings = rankings[rankings["broker_slug"].isin(slugs)].sort_values("score", ascending=False)
winner = selected_rankings.iloc[0]
runner_up = selected_rankings.iloc[1]
strengths, risk = broker_edges(dimension_scores, weights, winner["broker_slug"])

st.markdown(
    f"""
    <div class="bbi-winner-band">
      <div>
        <div class="label">Best of these brokers for {_html.escape(preset)}</div>
        <h1>{_html.escape(winner['broker_name'])}</h1>
        <p>Leads {_html.escape(runner_up['broker_name'])} by {winner['score'] - runner_up['score']:.1f} points.</p>
      </div>
      <div class="bbi-winner-score"><strong>{winner['score']:.1f}</strong><small>fit score / rank #{int(winner['rank'])} market-wide</small></div>
    </div>
    <div class="bbi-verdict-grid">
      <div><span>Decisive strength</span><strong>{_html.escape(strengths[0]['name'] if strengths else 'Balanced profile')}</strong></div>
      <div><span>Confidence</span><strong>{winner['confidence']:.0f} / 100</strong></div>
      <div class="risk"><span>Main trade-off</span><strong>{_html.escape(risk['name'] if risk else 'No major gap')}</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

radar_dimensions = top_weighted_dimensions(weights, 8)
charts = st.columns([1.05, 0.95])
with charts[0]:
    st.markdown(
        '<div class="bbi-panel-heading"><span>Competitive shape</span><strong>Strengths and weaknesses at a glance</strong></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        radar_chart(dimension_scores, slugs, radar_dimensions, height=410),
        width="stretch",
        key="compare_radar",
    )
with charts[1]:
    st.markdown(
        '<div class="bbi-panel-heading"><span>Exact scores</span><strong>Same dimensions, easier gap detection</strong></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        dimension_heatmap(dimension_scores, slugs, radar_dimensions, height=410),
        width="stretch",
        key="compare_heatmap",
    )

customer = data.customer_voice_rankings()
customer = customer[customer["broker_slug"].isin(slugs)].set_index("broker_name").reindex(chosen)
customer_table = customer[["score", "support", "reliability", "app", "trend", "coverage"]].copy()
customer_table.columns = [
    "Customer Voice",
    "Support",
    "Reliability",
    "App",
    "Trend",
    "Coverage",
]

st.markdown(
    '<div class="bbi-panel-heading"><span>Customer voice</span><strong>Support and reliability carry the most weight</strong></div>',
    unsafe_allow_html=True,
)
st.dataframe(
    customer_table.style.format("{:.0f}"),
    width="stretch",
    height=155,
)

facts = data.product_facts()
facts = facts[facts["broker_name"].isin(chosen) & facts["is_current"]].copy()
fact_labels = {
    "stock_etf_commission_usd": "Stock / ETF trade",
    "options_contract_fee_usd": "Options contract",
    "default_sweep_apy_pct": "Automatic cash rate",
    "best_cash_apy_pct": "Best cash rate",
    "margin_rate_pct": "Margin APR",
    "outgoing_acat_fee_usd": "Transfer-out fee",
    "fractional_shares_scope": "Fractional investing",
    "banking_level": "Banking integration",
}
fact_view = facts[facts["fact_key"].isin(fact_labels)].copy()
fact_view["Decision fact"] = fact_view["fact_key"].map(fact_labels)
fact_view["Current value"] = fact_view["value_text"]
fact_table = fact_view.pivot_table(
    index="Decision fact", columns="broker_name", values="Current value", aggfunc="first"
).reindex(fact_labels.values()).reindex(columns=chosen)

st.markdown(
    '<div class="bbi-panel-heading"><span>Current economics</span><strong>Expired rates and fees are omitted</strong></div>',
    unsafe_allow_html=True,
)
st.dataframe(fact_table, width="stretch", height=350)

compact_disclaimer()
