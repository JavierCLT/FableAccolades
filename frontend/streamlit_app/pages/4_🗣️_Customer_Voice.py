import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import data
from components.evidence import evidence_expander
from components.layout import page_setup

page_setup("Customer Voice Dashboard", icon="🗣️")

st.markdown(
    "What **actual customers** say across public sources — kept deliberately separate from "
    "expert opinion. Themes are labeled complaint / praise / opinion, with approximate volume, "
    "severity, and source. CFPB numbers come straight from the official complaint database API."
)

brokers = data.brokers()
broker_name = st.selectbox("Broker", brokers["name"].tolist())
broker = brokers[brokers["name"] == broker_name].iloc[0]
bid = int(broker["id"])

voice = data.q(
    """SELECT cv.*, s.name AS source_name, s.source_type, d.name AS dim_name
       FROM customer_voice cv
       JOIN sources s ON s.id = cv.source_id
       JOIN dimensions d ON d.id = cv.dimension_id
       WHERE cv.broker_id = ? ORDER BY cv.volume DESC""",
    (bid,),
)

# ---- Overall sentiment summary ----
st.subheader("Overall customer sentiment")
c1, c2, c3, c4 = st.columns(4)
n_complaints = int(voice[voice["kind"] == "complaint"]["volume"].sum())
n_praise = int(voice[voice["kind"] == "praise"]["volume"].sum())
n_opinion = int(voice[voice["kind"] == "opinion"]["volume"].sum())
total = max(1, n_complaints + n_praise)
c1.metric("Praise mentions (≈)", n_praise)
c2.metric("Complaint mentions (≈)", n_complaints)
c3.metric("Praise share", f"{100 * n_praise / total:.0f}%")
cust = data.q(
    """SELECT AVG(customer_component) v FROM dimension_scores
       WHERE broker_id = ? AND customer_component IS NOT NULL""", (bid,))
c4.metric("Mean customer-voice score", f"{cust['v'].iloc[0]:.0f}/100" if pd.notna(cust["v"].iloc[0]) else "n/a")
st.caption(
    "Volumes are approximate independent mentions from curated/collected themes — indicative, "
    "not a census. Self-selected review platforms skew negative for every large broker."
)

# ---- Aggregate ratings context ----
agg = data.q(
    """SELECT ar.*, s.name AS source_name FROM aggregate_ratings ar
       JOIN sources s ON s.id = ar.source_id WHERE ar.broker_id = ?""", (bid,))
if not agg.empty:
    st.subheader("Aggregate public ratings")
    cols = st.columns(len(agg))
    for i, (_, r) in enumerate(agg.iterrows()):
        cols[i].metric(r["source_name"], f"{r['rating_raw']:.1f}/5",
                       help=f"~{int(r['review_count'] or 0):,} reviews · as of {r['as_of_date']}")
    evidence_expander("Evidence for aggregate ratings", [int(x) for x in agg["evidence_id"]])

# ---- Themes ----
st.subheader("Key themes")
kind_tabs = st.tabs(["🔴 Complaints", "🟢 Praise", "⚪ General opinions"])
for tab, kind in zip(kind_tabs, ["complaint", "praise", "opinion"]):
    with tab:
        sub = voice[voice["kind"] == kind]
        if sub.empty:
            st.caption("No recorded themes of this type.")
        for _, t in sub.iterrows():
            with st.container(border=True):
                sev = "▲" * int(t["severity"])
                st.markdown(f"**{t['theme']}**")
                st.caption(
                    f"Source: {t['source_name']} ({t['source_type']}) · Dimension: {t['dim_name']} · "
                    f"Volume ≈{int(t['volume'])} mentions · Severity {sev} ({int(t['severity'])}/5) · "
                    f"Observed: {t['observed_date'] or 'unknown'}"
                )
                if t["snippet"]:
                    st.markdown(f"> {t['snippet']}")
                evidence_expander("Source evidence", [int(t["evidence_id"])])

# ---- CFPB ----
st.subheader("CFPB Consumer Complaint Database (official)")
cfpb = data.q("SELECT * FROM cfpb_complaint_stats WHERE broker_id = ?", (bid,))
if cfpb.empty or (cfpb["company_name"] == "NOT_FOUND").all():
    st.warning(
        "**No CFPB company entity matches this broker** (verified via the official API). "
        "The CFPB database covers consumer *banking* products; classic brokerage disputes go to "
        "FINRA/SEC instead. This is a **coverage gap, not a clean record**.",
        icon="🚫",
    )
    ev = data.q(
        """SELECT DISTINCT evidence_id FROM cfpb_complaint_stats WHERE broker_id = ?""", (bid,))
    if not ev.empty:
        evidence_expander("Lookup evidence", [int(x) for x in ev["evidence_id"]])
else:
    overall = cfpb[(cfpb["product"].isna()) & (cfpb["issue"].isna())].iloc[0]
    recent = cfpb[cfpb["issue"] == "__WINDOW_RECENT_12M__"]
    prior = cfpb[cfpb["issue"] == "__WINDOW_PRIOR_12M__"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Complaints ({overall['period_start'][:7]} → {overall['period_end'][:7]})",
              int(overall["complaint_count"]))
    if not recent.empty and not prior.empty:
        r, p = int(recent["complaint_count"].iloc[0]), int(prior["complaint_count"].iloc[0])
        c2.metric("Trailing 12 months", r, delta=f"{r - p:+d} vs prior 12m", delta_color="inverse")
    if pd.notna(overall["timely_response_pct"]):
        c3.metric("Timely response rate", f"{overall['timely_response_pct']:.0f}%")
    c4.metric("CFPB entity", overall["company_name"], help="Exact company string in the CFPB database")

    prod = cfpb[cfpb["product"].notna()].sort_values("complaint_count", ascending=True)
    iss = cfpb[cfpb["issue"].notna() & ~cfpb["issue"].str.startswith("__")].sort_values(
        "complaint_count", ascending=True)
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(
            go.Figure(go.Bar(x=prod["complaint_count"], y=prod["product"], orientation="h",
                             marker_color="#d7191c"))
            .update_layout(title="By product category", height=360, margin={"t": 40, "b": 10}),
            use_container_width=True)
    with g2:
        st.plotly_chart(
            go.Figure(go.Bar(x=iss["complaint_count"], y=iss["issue"], orientation="h",
                             marker_color="#fd8d3c"))
            .update_layout(title="By issue", height=360, margin={"t": 40, "b": 10}),
            use_container_width=True)
    st.caption(
        "Complaint counts are raw volume — larger customer bases generate more complaints. "
        "Scoring normalizes by client assets where disclosed (see Methodology). "
        "Note the CFPB entity may cover only part of the business (e.g. E*TRADE Bank)."
    )
    evidence_expander("CFPB evidence & raw data pointer",
                      [int(x) for x in cfpb["evidence_id"].unique()])
