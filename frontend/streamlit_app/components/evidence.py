"""The Evidence Viewer widget: every score/claim in the app can expand into this.

Renders, for each evidence row: publisher, page title, URL, retrieval date, collection
method, confidence, snippet, and any caveat notes — the full traceability contract.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import data
from components.layout import method_label

_CONF_ICON = {"high": "🟢", "medium": "🟡", "low": "🔴"}


def render_evidence_rows(df: pd.DataFrame) -> None:
    if df.empty:
        st.caption("No evidence rows found.")
        return
    for _, e in df.iterrows():
        unavailable = bool(e.get("unavailable", 0))
        icon = "🚫" if unavailable else _CONF_ICON.get(e["confidence"], "🟡")
        st.markdown(
            f"{icon} **{e['source_name']}** — [{e['title'] or e['url']}]({e['url']})"
        )
        meta = (
            f"Publisher: {e['publisher']} · Retrieved: {e['retrieval_date']} · "
            f"Method: {method_label(e['collection_method'])} · Confidence: {e['confidence']}"
        )
        if e.get("published_date"):
            meta += f" · Published: {e['published_date']}"
        st.caption(meta)
        if unavailable:
            st.warning("Source checked but data unavailable — recorded explicitly, never estimated.", icon="🚫")
        if e.get("snippet"):
            st.markdown(f"> {e['snippet']}")
        if e.get("notes"):
            st.caption(f"⚠️ {e['notes']}")
        st.divider()


def evidence_expander(label: str, evidence_ids: list[int], *, expanded: bool = False) -> None:
    """Click-to-reveal evidence. Uses a popover so it can live inside expanders/cards."""
    n = len(evidence_ids)
    with st.popover(
        f"🔍 {label} ({n} evidence item{'s' if n != 1 else ''})",
        width="stretch",
    ):
        render_evidence_rows(data.evidence_by_ids(evidence_ids))


def dimension_evidence_ids(broker_id: int, dimension_id: int) -> list[int]:
    """All evidence ids feeding one broker x dimension score (mirrors the engine)."""
    ids: set[int] = set()
    frames = [
        data.q("SELECT evidence_id FROM product_facts WHERE broker_id=? AND dimension_id=?",
               (broker_id, dimension_id)),
        data.q("SELECT evidence_id FROM customer_voice WHERE broker_id=? AND dimension_id=?",
               (broker_id, dimension_id)),
        data.q("""SELECT evidence_id FROM expert_ratings WHERE broker_id=? AND
                  (dimension_id=? OR (dimension_id IS NULL AND NOT EXISTS
                     (SELECT 1 FROM expert_ratings e2 WHERE e2.broker_id=? AND e2.dimension_id=?)))""",
               (broker_id, dimension_id, broker_id, dimension_id)),
    ]
    dim = data.q("SELECT slug FROM dimensions WHERE id=?", (dimension_id,))
    if not dim.empty and dim["slug"].iloc[0] == "mobile_app":
        frames.append(data.q(
            """SELECT ar.evidence_id FROM aggregate_ratings ar JOIN sources s ON s.id=ar.source_id
               WHERE ar.broker_id=? AND s.source_type='app_store'""", (broker_id,)))
    if not dim.empty and dim["slug"].iloc[0] == "customer_support":
        frames.append(data.q(
            "SELECT evidence_id FROM cfpb_complaint_stats WHERE broker_id=? AND product IS NULL AND issue IS NULL",
            (broker_id,)))
    for f in frames:
        ids.update(int(x) for x in f["evidence_id"].tolist())
    return sorted(ids)
