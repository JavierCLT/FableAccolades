import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.charts import radar_chart, score_bar
from components.evidence import dimension_evidence_ids, evidence_expander
from components.hovercard import evidence_items, hover_html
from components.layout import confidence_badge, page_setup

page_setup("Multi-Broker Comparison", icon="📈")

brokers = data.brokers()
default = ["Fidelity", "Charles Schwab"]
chosen = st.multiselect("Select 2–4 brokers", brokers["name"].tolist(), default=default,
                        max_selections=4)
if len(chosen) < 2:
    st.info("Select at least two brokers to compare.")
    st.stop()

slugs = brokers[brokers["name"].isin(chosen)].set_index("name").loc[chosen]["slug"].tolist()
ids = brokers[brokers["name"].isin(chosen)].set_index("slug")["id"].to_dict()
ds = data.dimension_scores()
sel = ds[ds["broker_slug"].isin(slugs)]

st.subheader("Dimension radar")
st.plotly_chart(radar_chart(sel, slugs), use_container_width=True)
st.caption("Each axis is the blended 0–100 dimension score (facts 45 / customers 35 / experts 20).")

st.subheader("Score table")
table = sel.pivot_table(index=["sort_order", "dim_name"], columns="broker_name", values="score")
table = table.droplevel(0)[chosen]
best = table.max(axis=1)
styled = table.style.format("{:.0f}").highlight_max(axis=1, props="background-color:#d4f7d4;font-weight:bold")
st.dataframe(styled, use_container_width=True, height=600)

conf_table = sel.pivot_table(index=["sort_order", "dim_name"], columns="broker_name",
                             values="confidence").droplevel(0)[chosen]
with st.expander("Confidence behind each cell"):
    st.dataframe(conf_table.style.format("{:.0f}"), use_container_width=True)
    st.caption("Confidence 0–100: evidence volume, source quality, recency, corroboration.")

st.subheader("Zoom into one dimension")
_dims = data.dimensions()["name"].tolist()
dim_name = st.pills("Dimension", _dims, default=_dims[0], selection_mode="single")
if not dim_name:
    dim_name = _dims[0]
zoom = sel[sel["dim_name"] == dim_name].sort_values("score", ascending=False)
st.plotly_chart(score_bar(zoom, "broker_name", "score", "broker_slug"), use_container_width=True)
for _, r in zoom.iterrows():
    comp = " · ".join(
        f"{lbl} {r[key]:.0f}" for lbl, key in
        (("facts", "fact_component"), ("customers", "customer_component"), ("experts", "expert_component"))
        if pd.notna(r[key])
    )
    ev_ids = dimension_evidence_ids(int(r["broker_id"]), int(r["dimension_id"]))
    st.markdown(
        f"<b>{r['broker_name']}</b> — "
        + hover_html(f"{r['score']:.0f}/100", evidence_items(ev_ids, limit=5))
        + f" (confidence {confidence_badge(r['confidence'])}) · {comp}",
        unsafe_allow_html=True,
    )
    evidence_expander(f"Evidence — {r['broker_name']} / {dim_name}", ev_ids)

st.subheader("Objective facts side-by-side")
facts = data.q(
    """SELECT pf.fact_key, pf.value_text, b.name AS broker_name, d.sort_order
       FROM product_facts pf JOIN brokers b ON b.id = pf.broker_id
       JOIN dimensions d ON d.id = pf.dimension_id"""
)
facts = facts[facts["broker_name"].isin(chosen)]
ft = facts.pivot_table(index="fact_key", columns="broker_name", values="value_text",
                       aggfunc="first")[chosen]
st.dataframe(ft, use_container_width=True, height=600)
st.caption("Full labels, data ages, and per-fact evidence: Product Fact Comparison page.")
