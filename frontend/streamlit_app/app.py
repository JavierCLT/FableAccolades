"""Best Broker Index — home page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from components import data
from components.layout import confidence_badge, page_setup

page_setup("Best Broker Index", icon="🧭")

st.markdown(
    """
An independent, public-data-only research and comparison tool for U.S. brokerage platforms.
This is **not** another ranking site that gives everyone a trophy. Every number here is
traceable to a source, and the tool deliberately surfaces where expert reviewers
**contradict each other** — and where **actual customers** disagree with the experts.

**What's inside**

| | |
|---|---|
| 🏆 **Rankings by Persona** | Weighted scores for 9 investor personas — adjust the weights yourself |
| ⚔️ **Contradiction Matrix** | Where expert sources disagree on the same broker & dimension |
| 📋 **Product Facts** | Side-by-side objective facts from brokers' own public pages |
| 🗣️ **Customer Voice** | Reddit/forum themes, review-site sentiment, and CFPB complaint data |
| 🔍 **Evidence Viewer** | The source URL, retrieval date, snippet, and confidence behind every claim |
"""
)

st.subheader("Tracked brokers (Phase 1)")
brokers = data.brokers()
ps = data.q(
    """SELECT b.slug, AVG(ds.score) AS avg_score, AVG(ds.confidence) AS avg_conf,
              SUM(ds.evidence_count) AS evidence
       FROM dimension_scores ds JOIN brokers b ON b.id = ds.broker_id GROUP BY b.slug"""
).set_index("slug")

cols = st.columns(3)
for i, (_, b) in enumerate(brokers.iterrows()):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{b['name']}**")
            row = ps.loc[b["slug"]] if b["slug"] in ps.index else None
            if row is not None:
                st.metric("Mean dimension score (unweighted)", f"{row['avg_score']:.1f} / 100")
                st.caption(
                    f"Confidence {confidence_badge(row['avg_conf'])} · "
                    f"{int(row['evidence'])} evidence links · "
                    f"SIPC: {'yes' if b['sipc_member'] else 'no'} · CRD #{b['finra_crd']}"
                )
            aum = f"~${b['aum_usd_billions']:,.0f}B" if pd.notna(b["aum_usd_billions"]) else "not disclosed separately"
            st.caption(f"Client assets: {aum} · {b['website']}")

st.subheader("Data freshness")
st.caption(
    "Every pipeline step is logged. Collectors that fail or are skipped are shown honestly — "
    "stale data is penalized in scoring, never hidden."
)
fresh = data.freshness()
if not fresh.empty:
    fresh = fresh.rename(columns={"step": "Step", "status": "Status", "detail": "Detail",
                                  "finished_at": "Finished (UTC)"})
    st.dataframe(fresh, use_container_width=True, hide_index=True)

st.warning(
    "**Read this before using rankings:** scores are estimates from public evidence at "
    "collection time. Customer reviews are self-selected and skew negative; expert reviews "
    "may carry undisclosed affiliate incentives; CFPB coverage differs by broker business "
    "model. Individual needs vary — rankings are a starting point, not advice. "
    "Full detail: **Limitations & Disclosures** page.",
    icon="⚠️",
)
