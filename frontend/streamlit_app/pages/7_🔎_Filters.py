import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.evidence import evidence_expander
from components.layout import page_setup

page_setup("Filter Brokers by Criteria", icon="🔎")

st.markdown("Screen the tracked brokers on hard criteria. Every surviving row shows the "
            "matching values, and every value is evidence-linked.")

facts = data.q(
    """SELECT pf.*, b.name AS broker_name, b.slug AS broker_slug
       FROM product_facts pf JOIN brokers b ON b.id = pf.broker_id"""
)
wide_num = facts.pivot_table(index="broker_name", columns="fact_key", values="value_numeric",
                             aggfunc="first")
wide_txt = facts.pivot_table(index="broker_name", columns="fact_key", values="value_text",
                             aggfunc="first")
ds = data.dimension_scores()
mobile = ds[ds["dim_slug"] == "mobile_app"].set_index("broker_name")["score"]

c1, c2, c3 = st.columns(3)
with c1:
    f_no_acat = st.checkbox("No outgoing ACAT fee")
    f_fractional = st.checkbox("Fractional stocks AND ETFs")
    f_247 = st.checkbox("24/7 customer support")
    f_branches = st.checkbox("Has physical branches")
with c2:
    f_cash = st.slider("Min. default cash sweep APY (%)", 0.0, 5.0, 0.0, 0.25)
    f_best_cash = st.slider("Min. best-available cash APY (%)", 0.0, 5.0, 0.0, 0.25)
    f_mobile = st.slider("Min. mobile app score (0–100)", 0, 100, 0, 5)
with c3:
    f_crypto = st.checkbox("Crypto trading")
    f_futures = st.checkbox("Futures trading")
    f_intl = st.checkbox("International markets")
    f_ira_match = st.checkbox("IRA contribution match")
    f_human = st.checkbox("Human advisor access")

result = wide_num.copy()
reasons: dict[str, list[str]] = {b: [] for b in result.index}

def apply(mask: pd.Series, label: str):
    global result
    for b in result.index:
        if b in mask.index and not bool(mask.loc[b]):
            reasons[b].append(label)
    result = result[result.index.isin(mask[mask].index)]

if f_no_acat:
    apply(wide_num["outgoing_acat_fee_usd"] == 0, "charges an outgoing ACAT fee")
if f_fractional:
    apply(wide_num["fractional_shares_scope"] >= 2, "no full fractional stock+ETF support")
if f_247:
    apply(wide_num["support_24_7"] == 1, "no 24/7 support")
if f_branches:
    apply(wide_num["branch_count"] > 0, "no branches")
if f_cash > 0:
    apply(wide_num["default_sweep_apy_pct"] >= f_cash, f"default sweep below {f_cash}%")
if f_best_cash > 0:
    apply(wide_num["best_cash_apy_pct"] >= f_best_cash, f"best cash APY below {f_best_cash}%")
if f_mobile > 0:
    apply(mobile >= f_mobile, f"mobile score below {f_mobile}")
if f_crypto:
    apply(wide_num["crypto_trading"] == 1, "no crypto")
if f_futures:
    apply(wide_num["futures_trading"] == 1, "no futures")
if f_intl:
    apply(wide_num["international_trading"] == 1, "no international markets")
if f_ira_match:
    apply(wide_num["ira_match_pct"] > 0, "no IRA match")
if f_human:
    apply(wide_num["human_advisor_access"] == 1, "no human advisors")

st.subheader(f"✅ {len(result)} broker(s) match")
show_cols = ["outgoing_acat_fee_usd", "default_sweep_apy_pct", "best_cash_apy_pct",
             "fractional_shares_scope", "ira_match_pct"]
for b in result.index:
    with st.container(border=True):
        st.markdown(f"### {b}")
        st.metric("Mobile app score", f"{mobile.get(b, float('nan')):.0f}/100")
        vals = wide_txt.loc[b]
        st.caption(
            f"ACAT out: {vals.get('outgoing_acat_fee_usd')} · "
            f"Default sweep: {vals.get('default_sweep_apy_pct')} · "
            f"Best cash: {vals.get('best_cash_apy_pct')} · "
            f"Fractional: {vals.get('fractional_shares_scope')} · "
            f"Support: {vals.get('support_24_7')}"
        )
        ev_ids = facts[facts["broker_name"] == b]["evidence_id"].astype(int).tolist()
        evidence_expander(f"All product-fact evidence for {b}", ev_ids)

excluded = {b: r for b, r in reasons.items() if r}
if excluded:
    st.subheader("❌ Excluded and why")
    for b, r in excluded.items():
        st.markdown(f"- **{b}**: {', '.join(r)}")
st.caption("Filters use objective product facts (broker-official pages) and computed mobile scores. "
           "Volatile values carry as-of dates — verify before acting.")
