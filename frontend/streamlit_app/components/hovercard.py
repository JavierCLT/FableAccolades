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
.bbi-tip{position:relative;display:inline-block;border-bottom:2px dotted #1f77b4;cursor:help}
.bbi-tip .bbi-box{visibility:hidden;opacity:0;transition:opacity .12s ease-in;position:absolute;
 top:130%;left:0;background:#20222b;color:#fafafa;border-radius:10px;padding:12px 14px;
 width:380px;max-width:70vw;z-index:99999;box-shadow:0 6px 18px rgba(0,0,0,.45);
 font-weight:400;font-size:.84rem;line-height:1.5;text-align:left;white-space:normal}
.bbi-tip:hover .bbi-box{visibility:visible;opacity:1}
.bbi-box a{color:#8dcbff !important;text-decoration:none;font-weight:600}
.bbi-box a:hover{text-decoration:underline}
.bbi-box .bbi-meta{color:#a9adbb;font-size:.74rem;margin-bottom:7px}
.bbi-box .bbi-head{font-weight:700;margin-bottom:6px;color:#ffd166}
.bbi-facttable{border-collapse:collapse;width:100%;font-size:.83rem}
.bbi-facttable th,.bbi-facttable td{border:1px solid #3a3d4a;padding:6px 8px;vertical-align:top;text-align:left}
.bbi-facttable th{background:#262935;color:#fafafa;position:sticky;top:0}
.bbi-facttable td .bbi-tip{border-bottom-color:#666}
</style>
"""

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
            rows.append(f'<div class="bbi-meta">…plus {it["more"]} more in the Evidence Viewer</div>')
            continue
        icon = "🚫" if it["unavailable"] else _CONF_ICON.get(it["confidence"], "🟡")
        title = it["title"][:70] + ("…" if len(it["title"]) > 70 else "")
        rows.append(
            f'<div>{icon} <a href="{_html.escape(it["url"], quote=True)}" target="_blank" '
            f'rel="noopener">{_html.escape(it["source"])}: {_html.escape(title)}</a>'
            f'<div class="bbi-meta">retrieved {_html.escape(str(it["date"]))} · '
            f'{_METHOD.get(it["method"], it["method"])} · confidence {it["confidence"]}'
            f'{" · no longer published" if it["unavailable"] else ""}</div></div>'
        )
    return (
        f'<span class="bbi-tip">{_html.escape(str(label))}'
        f'<span class="bbi-box"><div class="bbi-head">{_html.escape(head)}</div>'
        + "".join(rows) + "</span></span>"
    )


def hover_single(label: str, url: str, source: str, date: str | None = None,
                 method: str = "manual_curation", confidence: str = "medium") -> str:
    return hover_html(label, [{
        "source": source, "title": url, "url": url, "date": date or "?",
        "method": method, "confidence": confidence, "unavailable": False,
    }])
