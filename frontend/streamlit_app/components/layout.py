"""Shared page chrome: disclaimers, headers, and small display helpers."""

from __future__ import annotations

import streamlit as st

from components import data

DISCLAIMER = (
    "**Not financial advice.** Independent research tool using only public data. "
    "Scores are evidence-based estimates, not recommendations — see "
    "*Methodology* and *Limitations & Disclosures*."
)


def page_setup(title: str, icon: str = "📊", wide: bool = True) -> None:
    st.set_page_config(page_title=f"{title} — Best Broker Index", page_icon=icon,
                       layout="wide" if wide else "centered")
    if data.db_missing():
        st.error(
            "Database not found. Build it first:\n\n"
            "```\npython -m backend.pipeline            # with live collectors\n"
            "python -m backend.pipeline --no-collect  # offline (seed data only)\n```"
        )
        st.stop()
    from components.hovercard import CSS, enable_flip  # hover-to-verify styles + flip logic
    st.markdown(CSS, unsafe_allow_html=True)
    enable_flip()
    st.title(title)
    st.info(DISCLAIMER, icon="⚖️")


def confidence_badge(value: float) -> str:
    if value >= 70:
        return f"🟢 {value:.0f}"
    if value >= 45:
        return f"🟡 {value:.0f}"
    return f"🔴 {value:.0f}"


def severity_badge(severity: str) -> str:
    return {"moderate": "🟡 moderate", "significant": "🟠 significant", "severe": "🔴 severe"}.get(
        severity, severity
    )


def method_label(method: str) -> str:
    return {
        "api": "official API",
        "scrape": "scraped (verified live)",
        "bulk_download": "bulk download",
        "manual_curation": "manually curated from public page",
    }.get(method, method)
