"""Hover-to-verify: every score/claim can carry a hover card with clickable source links.

Usage:
    from components.hovercard import hover_html, evidence_items
    st.markdown(hover_html("84.2 / 100", evidence_items(ids)), unsafe_allow_html=True)

The CSS is injected once per page by layout.page_setup(). Tooltips are pure CSS so links
inside remain clickable while hovered.
"""

from __future__ import annotations

import html as _html

import pandas as pd

from components import data

CSS = """
<style>
/* Hover-card mechanics:
   - transparent top-border "bridge" -> no dead gap between trigger and card
   - 0.35s hide delay -> cursor can travel into the card and click links
   - 0.12s show delay -> passing over other triggers doesn't open their cards
   - hovered tip gets a higher z-index -> its card always stacks above stale ones */
.bbi-tip{position:relative;display:inline-block;border-bottom:2px dotted #1f77b4;cursor:help;z-index:1}
.bbi-tip:hover{z-index:1000}
.bbi-tip .bbi-box{visibility:hidden;opacity:0;position:absolute;top:100%;left:0;
 border-top:10px solid transparent;background-clip:padding-box;
 background:#20222b;color:#fafafa;border-radius:10px;padding:12px 14px;
 width:380px;max-width:70vw;z-index:99999;
 filter:drop-shadow(0 6px 14px rgba(0,0,0,.4));
 transition:visibility 0s linear .35s,opacity .12s ease .23s;
 font-weight:400;font-size:.84rem;line-height:1.5;text-align:left;white-space:normal}
.bbi-tip:hover .bbi-box{visibility:visible;opacity:1;
 transition:visibility 0s linear .12s,opacity .12s ease .12s}
/* Streamlit wraps every element in stacked containers; lift the whole chain containing a
   hovered tip so sibling blocks (captions, metrics) can never paint over the card. */
div[data-testid="stElementContainer"]:has(.bbi-tip:hover),
div[data-testid="stColumn"]:has(.bbi-tip:hover),
div[data-testid="stVerticalBlock"]:has(.bbi-tip:hover){position:relative;z-index:1001}
.bbi-box a{color:#8dcbff !important;text-decoration:none;font-weight:600}
.bbi-box a:hover{text-decoration:underline}
/* All card internals are <span display:block>: Markdown ejects block tags (<div>) out of
   inline contexts, which silently emptied cards rendered mid-paragraph. */
.bbi-box .bbi-row{display:block}
.bbi-box .bbi-meta{display:block;color:#a9adbb;font-size:.74rem;margin-bottom:7px}
.bbi-box .bbi-head{display:block;font-weight:700;margin-bottom:6px;color:#ffd166}
.bbi-facttable{border-collapse:collapse;width:100%;min-width:1400px;font-size:.8rem;background:#fff}
.bbi-facttable th,.bbi-facttable td{border:1px solid #d8e1dc;padding:7px 9px;vertical-align:top;text-align:left;color:#18211e}
.bbi-facttable th{background:#eef3f0;color:#33423c;position:sticky;top:0;z-index:3}
.bbi-facttable th:first-child,.bbi-facttable td:first-child{position:sticky;left:0;background:#f8faf9;z-index:2;min-width:180px}
.bbi-facttable th:first-child{z-index:4}
.bbi-facttable td .bbi-tip{border-bottom-color:#666}
/* Right-side table columns open their cards right-aligned so they never overflow the viewport. */
.bbi-facttable td:nth-child(n+7) .bbi-box{left:auto;right:0}
/* Cards flip upward when the trigger is near the bottom of the viewport (class toggled by
   the flip script below), so the card and its links always stay reachable. */
.bbi-tip.bbi-up .bbi-box{top:auto;bottom:100%;
 border-top:none;border-bottom:10px solid transparent}
</style>
"""

# Runs from a zero-height component iframe (same origin) and watches hovers on the parent
# page: when a trigger sits in the bottom ~260px of the viewport, the card flips upward.
FLIP_SCRIPT = """
<script>
const doc = window.parent.document;
if (!doc.__bbiFlip) {
  doc.__bbiFlip = true;
  doc.addEventListener('mouseover', (e) => {
    const tip = e.target.closest ? e.target.closest('.bbi-tip') : null;
    if (!tip) return;
    const r = tip.getBoundingClientRect();
    tip.classList.toggle('bbi-up', r.bottom > window.parent.innerHeight - 260);
  }, true);
}
</script>
"""


def enable_flip() -> None:
    """Install the viewport-aware flip behavior (call once per page)."""
    import streamlit as st

    st.html(FLIP_SCRIPT, unsafe_allow_javascript=True)


_CONF_ICON = {"high": "🟢", "medium": "🟡", "low": "🔴"}
_METHOD = {"api": "official API", "scrape": "verified live", "bulk_download": "bulk download",
           "manual_curation": "curated from public page"}


def evidence_items(evidence_ids: list[int], limit: int = 5) -> list[dict]:
    """Fetch and rank evidence rows for hover display (best sources first)."""
    df = data.evidence_by_ids(evidence_ids)
    if df.empty:
        return []
    order = {"high": 0, "medium": 1, "low": 2}
    df = df.copy()
    df["_rank"] = df["confidence"].map(order).fillna(3) + df["unavailable"] * 10
    df = df.sort_values(["_rank", "quality_weight"], ascending=[True, False])
    items = []
    for _, e in df.head(limit).iterrows():
        items.append({
            "source": e["source_name"],
            "title": e["title"] or e["url"],
            "url": e["url"],
            "date": e["retrieval_date"],
            "method": e["collection_method"],
            "confidence": e["confidence"],
            "unavailable": bool(e["unavailable"]),
        })
    extra = len(df) - limit
    if extra > 0:
        items.append({"more": extra})
    return items


def hover_html(label: str, items: list[dict], head: str = "Proof — click any source") -> str:
    """Return an inline hover-card span. Render with st.markdown(..., unsafe_allow_html=True)."""
    if not items:
        return _html.escape(str(label))
    rows = []
    for it in items:
        if "more" in it:
            rows.append(f'<span class="bbi-meta">…plus {it["more"]} more in the Evidence Viewer</span>')
            continue
        icon = "🚫" if it["unavailable"] else _CONF_ICON.get(it["confidence"], "🟡")
        title = it["title"][:70] + ("…" if len(it["title"]) > 70 else "")
        rows.append(
            f'<span class="bbi-row">{icon} <a href="{_html.escape(it["url"], quote=True)}" target="_blank" '
            f'rel="noopener">{_html.escape(it["source"])}: {_html.escape(title)}</a></span>'
            f'<span class="bbi-meta">retrieved {_html.escape(str(it["date"]))} · '
            f'{_METHOD.get(it["method"], it["method"])} · confidence {it["confidence"]}'
            f'{" · no longer published" if it["unavailable"] else ""}</span>'
        )
    return (
        f'<span class="bbi-tip">{_html.escape(str(label))}'
        f'<span class="bbi-box"><span class="bbi-head">{_html.escape(head)}</span>'
        + "".join(rows) + "</span></span>"
    )


def hover_single(label: str, url: str, source: str, date: str | None = None,
                 method: str = "manual_curation", confidence: str = "medium") -> str:
    return hover_html(label, [{
        "source": source, "title": url, "url": url, "date": date or "?",
        "method": method, "confidence": confidence, "unavailable": False,
    }])
