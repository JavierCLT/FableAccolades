import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components import data
from components.evidence import render_evidence_rows
from components.layout import page_setup

page_setup("Evidence Viewer", icon="🔍")

st.markdown(
    "The full evidence ledger. **Every score, rating, and claim in this tool links to a row "
    "here**, carrying: source URL, page title, publisher, retrieval date, snippet, collection "
    "method, and confidence. Rows marked 🚫 record sources that were checked but unavailable — "
    "gaps are documented, never papered over."
)

ev = data.q(
    """SELECT e.*, s.name AS source_name, s.publisher, s.source_type, b.name AS broker_name
       FROM evidence e
       JOIN sources s ON s.id = e.source_id
       LEFT JOIN brokers b ON b.id = e.broker_id
       ORDER BY e.id DESC"""
)

search = st.text_input("Search title / snippet / URL")
with st.expander("Refine (broker, source type, method, confidence)"):
    broker_f = st.pills("Broker", sorted(ev["broker_name"].dropna().unique()), selection_mode="multi")
    type_f = st.pills("Source type", sorted(ev["source_type"].unique()), selection_mode="multi")
    method_f = st.pills("Collection method", sorted(ev["collection_method"].unique()), selection_mode="multi")
    conf_f = st.pills("Confidence", ["high", "medium", "low"], selection_mode="multi")

view = ev.copy()
if broker_f:
    view = view[view["broker_name"].isin(broker_f)]
if type_f:
    view = view[view["source_type"].isin(type_f)]
if method_f:
    view = view[view["collection_method"].isin(method_f)]
if conf_f:
    view = view[view["confidence"].isin(conf_f)]
if search:
    s = search.lower()
    view = view[
        view["title"].str.lower().str.contains(s, na=False)
        | view["snippet"].str.lower().str.contains(s, na=False)
        | view["url"].str.lower().str.contains(s, na=False)
    ]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Evidence rows shown", len(view))
m2.metric("Distinct sources", view["source_name"].nunique())
m3.metric("From official APIs", int((view["collection_method"] == "api").sum()))
m4.metric("Marked unavailable", int(view["unavailable"].sum()))

st.dataframe(
    view[["id", "broker_name", "source_name", "title", "retrieval_date",
          "collection_method", "confidence", "url"]]
    .rename(columns={"id": "ID", "broker_name": "Broker", "source_name": "Source",
                     "title": "Title", "retrieval_date": "Retrieved",
                     "collection_method": "Method", "confidence": "Confidence", "url": "URL"}),
    use_container_width=True, hide_index=True, height=420,
)

st.subheader("Inspect")
page_size = 20
page = st.number_input("Page", min_value=1,
                       max_value=max(1, (len(view) - 1) // page_size + 1), value=1)
chunk = view.iloc[(page - 1) * page_size: page * page_size]
render_evidence_rows(chunk)
