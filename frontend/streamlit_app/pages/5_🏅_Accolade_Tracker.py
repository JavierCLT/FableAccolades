import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components import data
from components.evidence import evidence_expander
from components.layout import page_setup

page_setup("Accolade Tracker", icon="🏅")

st.markdown(
    "Public awards and rankings by publisher, category, and year. Accolades are recorded as "
    "**publisher claims with evidence** — they provide context but do **not** directly drive "
    "scores (expert ratings do, with contradiction penalties). Remember that many award "
    "publishers earn affiliate revenue from the brokers they rank."
)

acc = data.q(
    """SELECT a.*, b.name AS broker_name, s.name AS source_name, s.publisher
       FROM accolades a
       JOIN brokers b ON b.id = a.broker_id
       JOIN sources s ON s.id = a.source_id
       ORDER BY a.year DESC, s.name, a.award_title"""
)

f1, f2, f3 = st.columns(3)
broker_f = f1.multiselect("Broker", sorted(acc["broker_name"].unique()))
pub_f = f2.multiselect("Publisher", sorted(acc["source_name"].unique()))
year_f = f3.multiselect("Year", sorted(acc["year"].dropna().unique(), reverse=True))

view = acc.copy()
if broker_f:
    view = view[view["broker_name"].isin(broker_f)]
if pub_f:
    view = view[view["source_name"].isin(pub_f)]
if year_f:
    view = view[view["year"].isin(year_f)]

st.dataframe(
    view[["broker_name", "award_title", "category", "source_name", "year", "rank"]]
    .rename(columns={"broker_name": "Broker", "award_title": "Award", "category": "Category",
                     "source_name": "Publisher", "year": "Year", "rank": "Rank"}),
    use_container_width=True, hide_index=True,
)

st.subheader("Accolades per broker")
counts = view.groupby("broker_name").size().sort_values(ascending=False)
st.bar_chart(counts)

st.subheader("Evidence")
for _, r in view.iterrows():
    evidence_expander(
        f"{r['broker_name']} — {r['award_title']} ({r['source_name']}, {r['year']})",
        [int(r["evidence_id"])],
    )
