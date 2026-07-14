import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.charts import contradiction_heatmap
from components.evidence import evidence_expander
from components.hovercard import evidence_items, hover_html
from components.layout import page_setup, severity_badge

page_setup("Reviewer Contradiction Matrix", icon="⚔️")

st.markdown(
    "Expert reviewers often **disagree sharply about the same broker on the same dimension** — "
    "a fact most 'best broker' roundups never mention. A contradiction is recorded whenever two "
    "publishers' normalized scores (0–100) differ by **15+ points**; 25+ is *significant*, "
    "35+ is *severe*. Contradictions reduce both the affected score and its confidence."
)

con = data.q(
    """SELECT c.*, b.name AS broker_name, b.slug AS broker_slug,
              COALESCE(d.name, 'Overall rating') AS dim_name,
              sa.name AS source_a, sb.name AS source_b
       FROM contradictions c
       JOIN brokers b ON b.id = c.broker_id
       LEFT JOIN dimensions d ON d.id = c.dimension_id
       JOIN sources sa ON sa.id = c.source_a_id
       JOIN sources sb ON sb.id = c.source_b_id
       ORDER BY c.gap DESC"""
)

if con.empty:
    st.success("No contradictions detected in the current data.")
    st.stop()

# ---- Heatmap: max gap per broker x dimension (incl. overall) ----
st.subheader("Where experts disagree (max gap per cell)")
pivot = con.pivot_table(index="broker_name", columns="dim_name", values="gap", aggfunc="max")
# Stable column order: Overall first, then dimension sort order.
dim_order = ["Overall rating"] + [d for d in data.dimensions()["name"] if d in pivot.columns]
pivot = pivot.reindex(columns=[c for c in dim_order if c in pivot.columns])
st.plotly_chart(contradiction_heatmap(pivot), width="stretch")
st.caption("Grey = publishers agree (gap < 15 points) or no overlapping coverage. Hover for exact gaps.")

# ---- Detail table with evidence ----
st.subheader("All detected contradictions")
broker_f = st.pills("Filter by broker (optional)", sorted(con["broker_name"].unique()),
                    selection_mode="multi")
sev_f = st.pills("Severity", ["moderate", "significant", "severe"], selection_mode="multi")

view = con.copy()
if broker_f:
    view = view[view["broker_name"].isin(broker_f)]
if sev_f:
    view = view[view["severity"].isin(sev_f)]

st.caption(f"{len(view)} contradiction(s) shown. Every row expands into full source evidence.")

for _, r in view.iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([5, 2])
        side_a = hover_html(f"{r['score_a']:.0f}", evidence_items([int(r["evidence_a_id"])]),
                            head=f"{r['source_a']} — source")
        side_b = hover_html(f"{r['score_b']:.0f}", evidence_items([int(r["evidence_b_id"])]),
                            head=f"{r['source_b']} — source")
        c1.markdown(
            f"<b>{r['broker_name']} · {r['dim_name']}</b> — "
            f"{r['source_a']} says <b>{side_a}</b>, {r['source_b']} says <b>{side_b}</b> "
            f"(gap <b>{r['gap']:.0f}</b> pts)",
            unsafe_allow_html=True,
        )
        c2.markdown(severity_badge(r["severity"]))
        evidence_expander(
            "Both sides' evidence",
            [int(r["evidence_a_id"]), int(r["evidence_b_id"])],
        )

st.divider()
st.markdown("#### Experts vs. customers")
st.caption(
    "Expert/customer divergence is visible per dimension on the Rankings page (compare the "
    "'experts' vs 'customers' components) — e.g. brokers whose expert mobile-app scores sit far "
    "above their public Android ratings. The Customer Voice page shows the underlying themes."
)
gap_df = data.dimension_scores()
gap_df = gap_df.dropna(subset=["expert_component", "customer_component"]).copy()
gap_df["expert_customer_gap"] = (gap_df["expert_component"] - gap_df["customer_component"]).round(1)
top_gaps = gap_df.reindex(gap_df["expert_customer_gap"].abs().sort_values(ascending=False).index).head(10)
st.dataframe(
    top_gaps[["broker_name", "dim_name", "expert_component", "customer_component", "expert_customer_gap"]]
    .rename(columns={"broker_name": "Broker", "dim_name": "Dimension",
                     "expert_component": "Experts say", "customer_component": "Customers say",
                     "expert_customer_gap": "Gap (experts − customers)"}),
    width="stretch", hide_index=True,
)
