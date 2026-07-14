import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.hovercard import hover_single
from components.layout import page_setup

page_setup("Withdrawn Reviews Tracker", icon="🕳️")

st.markdown(
    "Review publishers **add, change, and silently delete broker reviews** — without notice, "
    "corrections, or archives. This page tracks every expert claim we recorded whose source "
    "page has since **gone dead or stopped mentioning the broker**. These claims are "
    "**excluded from all scoring and contradiction detection** the moment withdrawal is "
    "detected; they are preserved here because *what publishers quietly remove is itself "
    "information*."
)

wd = data.q(
    """SELECT er.rating_raw, er.rating_scale_max, er.review_cycle,
              b.name AS broker_name, s.name AS source_name,
              COALESCE(d.name, 'Overall rating') AS dim_name,
              e.url, e.retrieval_date, e.notes, e.title
       FROM expert_ratings er
       JOIN evidence e ON e.id = er.evidence_id
       JOIN sources s ON s.id = er.source_id
       JOIN brokers b ON b.id = er.broker_id
       LEFT JOIN dimensions d ON d.id = er.dimension_id
       WHERE e.unavailable = 1
       ORDER BY s.name, b.name, dim_name"""
)

if wd.empty:
    st.success("No withdrawn reviews detected in the current data. The tracker populates "
               "automatically whenever the verification collector finds a dead or "
               "de-listed review page.")
    st.stop()


def parse_status(notes: str) -> tuple[str, str]:
    """Collector notes encode WITHDRAWN|<reason>|<date>| …"""
    for part in (notes or "").split(" | "):
        if part.startswith("WITHDRAWN|"):
            bits = part.split("|")
            reason = {"dead_url": "🔗 URL dead", "dropped_coverage": "👻 Broker de-listed"}.get(
                bits[1], bits[1])
            return reason, bits[2]
    return "unknown", "?"


wd[["Status", "Detected"]] = wd["notes"].apply(lambda n: pd.Series(parse_status(n)))

c1, c2, c3 = st.columns(3)
c1.metric("Withdrawn claims", len(wd))
c2.metric("Publishers involved", wd["source_name"].nunique())
c3.metric("Brokers affected", wd["broker_name"].nunique())

st.subheader("Withdrawal scoreboard by publisher")
score = (wd.groupby(["source_name", "Status"]).size().unstack(fill_value=0))
st.dataframe(score, width="stretch")
st.caption(
    "High counts don't necessarily mean bad faith — publishers restructure sites and rotate "
    "coverage. But every one of these was a public claim that quietly vanished. "
    "'Broker de-listed' means the cited page still exists but no longer mentions the broker."
)

st.subheader("Every withdrawn claim")
broker_f = st.pills("Filter by broker (optional)", sorted(wd["broker_name"].unique()),
                    selection_mode="multi")
view = wd[wd["broker_name"].isin(broker_f)] if broker_f else wd

for _, r in view.iterrows():
    with st.container(border=True):
        left, right = st.columns([5, 2])
        claim = (f"{r['source_name']} rated {r['broker_name']} "
                 f"{r['rating_raw']:g}/{r['rating_scale_max']:g} on {r['dim_name']}"
                 + (f" ({r['review_cycle']} cycle)" if r["review_cycle"] else ""))
        left.markdown(
            hover_single(claim, r["url"], r["source_name"], r["retrieval_date"]),
            unsafe_allow_html=True,
        )
        left.caption(f"Last seen/curated: {r['retrieval_date']} · Detected withdrawn: {r['Detected']} · "
                     f"Dead link kept for the record: {r['url']}")
        right.markdown(f"**{r['Status']}**")

st.divider()
st.caption(
    "Methodology: on every pipeline run, each stored expert claim's URL is re-fetched "
    "(rate-limited, robots.txt-respecting). 404/410 → 'URL dead'; page live but broker name "
    "absent → 'broker de-listed'. Both are marked unavailable, excluded from scores, and "
    "listed here. See docs/sources.md for the full verification taxonomy."
)
