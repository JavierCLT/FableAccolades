"""Best Broker Index: winner-first investor and industry dashboards."""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from components import data
from components.charts import (
    compact_leaderboard,
    competitive_gap_chart,
    radar_chart,
    ranking_bar_chart,
    review_platform_heatmap,
    sentiment_balance_chart,
)
from components.decision import PROFILE_PRESETS, broker_edges, top_weighted_dimensions
from components.layout import compact_disclaimer, page_setup

page_setup("Broker Dashboard", icon="📊", show_title=False)


def _rank_of(frame: pd.DataFrame, broker_slug: str) -> int | None:
    matches = frame.index[frame["broker_slug"] == broker_slug].tolist()
    return matches[0] + 1 if matches else None


def _nearest_competitors(
    dimension_scores: pd.DataFrame, broker_slug: str, limit: int = 2
) -> list[str]:
    matrix = dimension_scores.pivot_table(
        index="broker_slug", columns="dim_slug", values="score"
    )
    if broker_slug not in matrix.index:
        return []
    selected = matrix.loc[broker_slug]
    distances: list[tuple[str, float]] = []
    for slug, row in matrix.drop(index=broker_slug).iterrows():
        overlap = selected.notna() & row.notna()
        if not overlap.any():
            continue
        distances.append((slug, float((selected[overlap] - row[overlap]).abs().mean())))
    return [slug for slug, _ in sorted(distances, key=lambda item: item[1])[:limit]]


def _leaderboard_panel(title: str, subtitle: str, frame: pd.DataFrame, key: str) -> None:
    st.markdown(
        f'<div class="bbi-mini-board"><span>{_html.escape(title)}</span>'
        f'<strong>{_html.escape(subtitle)}</strong></div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        compact_leaderboard(frame, limit=5, height=235),
        width="stretch",
        key=key,
    )


brokers = data.brokers()
personas = data.personas()
dimensions = data.dimensions()
dimension_scores = data.dimension_scores()
facts = data.product_facts()
current_facts = facts[facts["is_current"]].copy()
fact_summary = data.product_fact_freshness_summary(facts)
customer_rankings = data.customer_voice_rankings()
economic_rankings = data.economic_value_rankings()
review_ratings = data.review_platform_ratings()
sentiment = data.sentiment_comparison()

cash_rankings = current_facts[
    (current_facts["fact_key"] == "default_sweep_apy_pct")
    & current_facts["value_numeric"].notna()
][["broker_slug", "broker_name", "value_numeric", "as_of_date"]].copy()
cash_rankings = cash_rankings.rename(columns={"value_numeric": "score"}).sort_values(
    ["score", "as_of_date"], ascending=False
).reset_index(drop=True)

header, mode_column = st.columns([1.65, 0.65])
with header:
    st.markdown(
        f"""
        <div class="bbi-dashboard-head">
          <div>
            <div class="bbi-kicker">Independent brokerage intelligence</div>
            <h1>Who leads, and why?</h1>
          </div>
          <div class="bbi-dashboard-status">
            <span><b>{len(brokers)}</b> brokers</span>
            <span><b>{fact_summary['fresh']}</b> current facts</span>
            <span>expired values hidden</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with mode_column:
    mode = st.segmented_control(
        "Audience",
        ["Investor", "Industry"],
        default="Investor",
        key="audience_mode",
        label_visibility="collapsed",
    )

if mode == "Investor":
    preset = st.segmented_control(
        "What best describes you?",
        list(PROFILE_PRESETS),
        default="All-Around",
        key="investor_profile",
    )
    persona_slug = PROFILE_PRESETS[preset]
    persona = personas[personas["slug"] == persona_slug].iloc[0]
    weights = data.persona_weights(int(persona["id"]))
    rankings = data.compute_persona_scores(weights).reset_index(drop=True)
    rankings["rank"] = range(1, len(rankings) + 1)
    winner = rankings.iloc[0]
    strengths, risk = broker_edges(dimension_scores, weights, winner["broker_slug"])
    strengths = strengths or [{"name": "Balanced overall profile", "score": winner["score"]}]
    risk = risk or {"name": "No material gap identified", "score": winner["score"]}
    lead = float(winner["score"] - rankings.iloc[1]["score"]) if len(rankings) > 1 else 0.0

    st.markdown(
        f"""
        <div class="bbi-winner-band">
          <div>
            <div class="label">Best for {_html.escape(preset)} investors</div>
            <h1>{_html.escape(winner['broker_name'])}</h1>
            <p>Leads the field by {lead:.1f} points using the published {_html.escape(preset.lower())} methodology.</p>
          </div>
          <div class="bbi-winner-score">
            <strong>{winner['score']:.1f}</strong>
            <small>overall fit / confidence {winner['confidence']:.0f}</small>
          </div>
        </div>
        <div class="bbi-verdict-grid">
          <div><span>Why it leads</span><strong>{_html.escape(strengths[0]['name'])}</strong></div>
          <div><span>Also strong</span><strong>{_html.escape(strengths[min(1, len(strengths)-1)]['name'])}</strong></div>
          <div class="risk"><span>Know before choosing</span><strong>{_html.escape(risk['name'])}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    radar_dimensions = top_weighted_dimensions(weights, 8)
    chart_left, chart_right = st.columns([0.9, 1.1])
    with chart_left:
        st.markdown(
            '<div class="bbi-panel-heading"><span>Top five</span><strong>Best overall fit for this situation</strong></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            ranking_bar_chart(rankings, limit=5, height=390),
            width="stretch",
            key="investor_top_five",
        )
    with chart_right:
        st.markdown(
            '<div class="bbi-panel-heading"><span>Competitive shape</span><strong>How the top three differ</strong></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            radar_chart(
                dimension_scores,
                rankings.head(3)["broker_slug"].tolist(),
                radar_dimensions,
                height=390,
            ),
            width="stretch",
            key="investor_radar",
        )

else:
    merrill_matches = brokers.index[brokers["slug"] == "merrill"].tolist()
    default_broker_index = int(merrill_matches[0]) if merrill_matches else 0
    brokerage_name = st.selectbox(
        "Benchmark brokerage",
        brokers["name"].tolist(),
        index=default_broker_index,
    )
    selected_broker = brokers[brokers["name"] == brokerage_name].iloc[0]
    selected_slug = selected_broker["slug"]
    all_around_persona = personas[personas["slug"] == PROFILE_PRESETS["All-Around"]].iloc[0]
    weights = data.persona_weights(int(all_around_persona["id"]))
    rankings = data.compute_persona_scores(weights).reset_index(drop=True)
    rankings["rank"] = range(1, len(rankings) + 1)
    selected_rank = rankings[rankings["broker_slug"] == selected_slug].iloc[0]
    strengths, risk = broker_edges(dimension_scores, weights, selected_slug)
    nearest = _nearest_competitors(dimension_scores, selected_slug)
    name_lookup = brokers.set_index("slug")["name"].to_dict()
    nearest_names = [name_lookup.get(slug, slug) for slug in nearest]
    market_leader = rankings.iloc[0]

    st.markdown(
        f"""
        <div class="bbi-benchmark-band">
          <div class="label">Competitive position</div>
          <h1>{_html.escape(brokerage_name)} ranks #{int(selected_rank['rank'])} of {len(rankings)}</h1>
          <p>{market_leader['broker_name']} leads the all-around market by {market_leader['score'] - selected_rank['score']:.1f} points. Closest profile: {_html.escape(', '.join(nearest_names) or 'not enough comparable data')}.</p>
        </div>
        <div class="bbi-verdict-grid">
          <div><span>Largest advantage</span><strong>{_html.escape(strengths[0]['name'] if strengths else 'No clear advantage')}</strong></div>
          <div><span>Closest competitor</span><strong>{_html.escape(nearest_names[0] if nearest_names else 'Insufficient overlap')}</strong></div>
          <div class="risk"><span>Largest competitive gap</span><strong>{_html.escape(risk['name'] if risk else 'No gap identified')}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    industry_left, industry_right = st.columns([1.05, 0.95])
    with industry_left:
        st.markdown(
            '<div class="bbi-panel-heading"><span>Gap to leader</span><strong>Where intervention matters most</strong></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            competitive_gap_chart(dimension_scores, selected_slug, height=390),
            width="stretch",
            key="industry_gap",
        )
    with industry_right:
        st.markdown(
            '<div class="bbi-panel-heading"><span>Competitive profile</span><strong>Selected brokerage versus closest peers</strong></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            radar_chart(
                dimension_scores,
                [selected_slug, *nearest],
                top_weighted_dimensions(weights, 8),
                height=390,
            ),
            width="stretch",
            key="industry_radar",
        )

st.markdown(
    '<div class="bbi-panel-heading"><span>Market leaders</span><strong>Three rankings that change brokerage decisions</strong></div>',
    unsafe_allow_html=True,
)
leader_columns = st.columns(3)
with leader_columns[0]:
    _leaderboard_panel(
        "Customer voice",
        "Support, reliability, app experience and trend",
        customer_rankings,
        "customer_voice_leaders",
    )
with leader_columns[1]:
    _leaderboard_panel(
        "Economic value",
        "Fees, cash economics and banking integration",
        economic_rankings,
        "economic_value_leaders",
    )
with leader_columns[2]:
    st.markdown(
        '<div class="bbi-mini-board"><span>Default cash rate</span><strong>Current automatic yield only</strong></div>',
        unsafe_allow_html=True,
    )
    if cash_rankings.empty:
        st.info("No cash rate is currently inside the seven-day verification window.")
    else:
        st.plotly_chart(
            compact_leaderboard(
                cash_rankings,
                value_col="score",
                limit=5,
                suffix="%",
                height=235,
            ),
            width="stretch",
            key="cash_rate_leaders",
        )

st.markdown(
    '<div class="bbi-panel-heading"><span>Customer review landscape</span>'
    '<strong>Platform ratings and directional customer sentiment</strong></div>',
    unsafe_allow_html=True,
)
review_columns = st.columns([1.02, 0.98])
with review_columns[0]:
    st.markdown(
        '<div class="bbi-mini-board"><span>Public platform ratings</span>'
        '<strong>Apple, Google Play and Trustpilot on their published five-point scales</strong></div>',
        unsafe_allow_html=True,
    )
    if review_ratings.empty:
        st.info("No aggregate review-platform ratings are available.")
    else:
        st.plotly_chart(
            review_platform_heatmap(review_ratings, height=430),
            width="stretch",
            key="review_platform_heatmap",
        )
with review_columns[1]:
    st.markdown(
        '<div class="bbi-mini-board"><span>Positive versus negative</span>'
        '<strong>Directional share of recorded customer-theme mentions</strong></div>',
        unsafe_allow_html=True,
    )
    if sentiment.empty:
        st.info("No customer sentiment themes are available.")
    else:
        st.plotly_chart(
            sentiment_balance_chart(sentiment, height=430),
            width="stretch",
            key="sentiment_balance",
        )

st.caption(
    "App-store ratings often reflect prompted reviews, while Trustpilot and theme mentions are "
    "self-selected. The comparison is context, not a representative customer census."
)

compact_disclaimer()
