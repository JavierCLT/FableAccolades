import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components import data
from components.hovercard import evidence_items, hover_html
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

broker_f = st.pills("Filter by broker (optional)", sorted(acc["broker_name"].unique()),
                    selection_mode="multi")
view = acc.copy()
if broker_f:
    view = view[view["broker_name"].isin(broker_f)]

st.dataframe(
    view[["broker_name", "award_title", "category", "source_name", "year", "rank"]]
    .rename(columns={"broker_name": "Broker", "award_title": "Award", "category": "Category",
                     "source_name": "Publisher", "year": "Year", "rank": "Rank"}),
    use_container_width=True, hide_index=True,
)

st.subheader("Accolades per broker")
counts = view.groupby("broker_name").size().sort_values(ascending=False)
st.bar_chart(counts)

st.subheader("Evidence — hover any award to verify")
for _, r in view.iterrows():
    st.markdown(
        "🏅 " + hover_html(
            f"{r['broker_name']} — {r['award_title']} ({r['source_name']}, {r['year']})",
            evidence_items([int(r["evidence_id"])]),
            head="Award source",
        ),
        unsafe_allow_html=True,
    )
