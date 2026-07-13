import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

import html as _html

from components import data
from components.evidence import evidence_expander
from components.hovercard import hover_html
from components.layout import page_setup

page_setup("Product Fact Comparison", icon="📋")

st.markdown(
    "Objective facts from each broker's **own public pages** — no editorial spin. "
    "Volatile values (yields, margin rates) show their *as-of* date; anything past its "
    "freshness window is flagged and penalized in scoring, never silently trusted."
)

facts = data.q(
    """SELECT pf.*, b.name AS broker_name, b.slug AS broker_slug,
              d.name AS dim_name, d.sort_order,
              e.confidence, e.retrieval_date, e.url, e.title
       FROM product_facts pf
       JOIN brokers b ON b.id = pf.broker_id
       JOIN dimensions d ON d.id = pf.dimension_id
       JOIN evidence e ON e.id = pf.evidence_id
       ORDER BY d.sort_order, pf.fact_key, b.name"""
)

FACT_LABELS = {
    "stock_etf_commission_usd": "Stock/ETF commission",
    "options_contract_fee_usd": "Options per-contract fee",
    "margin_rate_pct": "Margin rate (≈$25k balance) ⏳",
    "account_fee_usd": "Account/inactivity fee",
    "default_sweep_apy_pct": "Default cash sweep APY ⏳",
    "best_cash_apy_pct": "Best available cash APY ⏳",
    "outgoing_acat_fee_usd": "Outgoing ACAT fee (full)",
    "fractional_shares_scope": "Fractional shares",
    "ira_match_pct": "IRA contribution match",
    "robo_advisor_fee_pct": "Robo-advisor fee",
    "human_advisor_access": "Human advisor access",
    "support_24_7": "24/7 support",
    "branch_count": "Branches",
    "banking_level": "Banking features",
    "crypto_trading": "Crypto trading",
    "futures_trading": "Futures trading",
    "international_trading": "International markets",
    "bonds_cds_available": "Bonds & CDs",
    "security_level": "Security features",
    "tax_lot_control": "Tax-lot control",
}

dim_filter = st.pills("Filter by dimension (optional)", facts["dim_name"].unique().tolist(),
                      selection_mode="multi")
view = facts[facts["dim_name"].isin(dim_filter)] if dim_filter else facts

view = view.copy()
view["Fact"] = view["fact_key"].map(FACT_LABELS).fillna(view["fact_key"])

# Hover-to-verify fact matrix: every cell carries its source link, as-of date, and
# confidence on mouseover. (⏳ = volatile fact; verify the as-of date before acting.)
brokers_order = sorted(view["broker_name"].unique())
cell_lookup = {(r["Fact"], r["broker_name"]): r for _, r in view.iterrows()}
fact_rows = view[["sort_order", "dim_name", "Fact"]].drop_duplicates().sort_values(
    ["sort_order", "Fact"])

html_parts = ['<table class="bbi-facttable"><thead><tr><th>Fact</th>']
html_parts += [f"<th>{_html.escape(b)}</th>" for b in brokers_order]
html_parts.append("</tr></thead><tbody>")
last_dim = None
for _, fr in fact_rows.iterrows():
    if fr["dim_name"] != last_dim:
        last_dim = fr["dim_name"]
        html_parts.append(
            f'<tr><td colspan="{len(brokers_order) + 1}" style="background:#262935;'
            f'color:#fafafa;font-weight:700">{_html.escape(last_dim)}</td></tr>'
        )
    html_parts.append(f"<tr><td><b>{_html.escape(fr['Fact'])}</b></td>")
    for b in brokers_order:
        r = cell_lookup.get((fr["Fact"], b))
        if r is None:
            html_parts.append('<td style="color:#777">—</td>')
            continue
        cell = hover_html(
            r["value_text"],
            [{"source": f"{b} (official page)", "title": r["title"] or r["url"], "url": r["url"],
              "date": r["retrieval_date"], "method": "manual_curation",
              "confidence": r["confidence"], "unavailable": False}],
            head=f"Source · as of {r['as_of_date']}",
        )
        html_parts.append(f"<td>{cell}</td>")
    html_parts.append("</tr>")
html_parts.append("</tbody></table>")
st.markdown("".join(html_parts), unsafe_allow_html=True)
st.caption("💡 Hover any value for its source link, as-of date, and confidence. "
           "⏳ marks volatile facts that move with rates.")

st.subheader("Evidence & data age for a specific fact")
broker_choice = st.pills("Broker", sorted(view["broker_name"].unique()),
                         default=sorted(view["broker_name"].unique())[0], selection_mode="single")
if not broker_choice:
    broker_choice = sorted(view["broker_name"].unique())[0]
fact_choice = st.selectbox("Fact", sorted(view["Fact"].unique()))
sel = view[(view["Fact"] == fact_choice) & (view["broker_name"] == broker_choice)]
if sel.empty:
    st.caption("No data recorded for this combination.")
else:
    r = sel.iloc[0]
    st.markdown(f"**{r['broker_name']} — {fact_choice}:** {r['value_text']}")
    st.caption(f"As of: {r['as_of_date']} · Evidence confidence: {r['confidence']}")
    evidence_expander("Source evidence", [int(r["evidence_id"])], expanded=True)

st.divider()
stale = facts[facts["fact_key"].isin(["default_sweep_apy_pct", "best_cash_apy_pct", "margin_rate_pct"])]
oldest = pd.to_datetime(stale["as_of_date"]).min().date()
st.caption(
    f"⏳ Volatile facts on this page carry as-of dates back to {oldest}. Rates move with the "
    "Fed and with broker repricing — always verify against the linked source page before acting."
)
