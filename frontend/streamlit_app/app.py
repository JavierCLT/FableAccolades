"""Best Broker Index — home page: answer "which broker is best for ME?" immediately."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from components import data
from components.layout import confidence_badge, page_setup

page_setup("Best Broker Index", icon="🧭")

st.markdown(
    "**Every score traceable to a source. Expert contradictions exposed. Real customer voice.** "
    "An independent, public-data-only comparison of 11 U.S. brokers across 16 dimensions."
)

# ----------------------------------------------------------------------------------
# 1. Instant answer: pick who you are -> top 3 brokers
# ----------------------------------------------------------------------------------
st.header("Which broker is best for you?")
personas = data.personas()
persona_name = st.pills(
    "I am a…", personas["name"].tolist(), default=personas["name"].iloc[0],
    selection_mode="single",
)
if not persona_name:
    persona_name = personas["name"].iloc[0]
persona = personas[personas["name"] == persona_name].iloc[0]
st.caption(persona["description"])

weights = data.persona_weights(int(persona["id"]))
scores = data.compute_persona_scores(weights)
ds = data.dimension_scores()
dim_median = ds.groupby("dim_slug")["score"].median()


def why_summary(broker_slug: str) -> tuple[str, str]:
    """Plain-language strongest edges and biggest watch-out vs the field, weight-aware."""
    sub = ds[ds["broker_slug"] == broker_slug]
    contrib = []
    for _, r in sub.iterrows():
        w = weights.get(r["dim_slug"], 0.0)
        edge = (r["score"] - dim_median[r["dim_slug"]]) * w
        contrib.append((edge, r["dim_name"], r["score"]))
    contrib.sort(reverse=True)
    strengths = [f"{name} ({score:.0f}/100)" for edge, name, score in contrib[:2] if edge > 0]
    worst = min(contrib, key=lambda c: c[0])
    weakness = f"{worst[1]} ({worst[2]:.0f}/100)" if worst[0] < 0 else ""
    return " · ".join(strengths), weakness


top3 = scores.head(3)
medals = ["🥇", "🥈", "🥉"]
cols = st.columns(3)
for i, (_, row) in enumerate(top3.iterrows()):
    with cols[i]:
        with st.container(border=True):
            st.markdown(f"## {medals[i]} {row['broker_name']}")
            st.metric("Score for you", f"{row['score']:.1f} / 100")
            st.caption(f"Confidence {confidence_badge(row['confidence'])} · "
                       f"{int(row['evidence_count'])} evidence links")
            strengths, weakness = why_summary(row["broker_slug"])
            if strengths:
                st.markdown(f"**Why:** {strengths}")
            if weakness:
                st.markdown(f"**Watch out:** {weakness}")

rest = scores.iloc[3:]
with st.expander(f"Full ranking for {persona_name} ({len(rest)} more brokers)"):
    view = scores[["broker_name", "score", "confidence", "evidence_count"]].copy()
    view.insert(0, "Rank", range(1, len(view) + 1))
    st.dataframe(
        view.rename(columns={"broker_name": "Broker", "score": "Score",
                             "confidence": "Confidence", "evidence_count": "Evidence"}),
        use_container_width=True, hide_index=True,
    )
st.page_link("pages/1_🏆_Rankings_by_Persona.py",
             label="→ Adjust the weights yourself and see every score's evidence",
             icon="🏆")

# ----------------------------------------------------------------------------------
# 2. Best-for cheat sheet
# ----------------------------------------------------------------------------------
st.header("Cheat sheet: best broker by need")
rows = []
for _, p in personas.iterrows():
    s = data.compute_persona_scores(data.persona_weights(int(p["id"])))
    if s.empty:
        continue
    winner, runner = s.iloc[0], s.iloc[1]
    rows.append({"If you are a…": p["name"], "Top pick": f"🏆 {winner['broker_name']} ({winner['score']:.0f})",
                 "Runner-up": f"{runner['broker_name']} ({runner['score']:.0f})"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption("Scores 0-100 with default persona weights. These are starting points, not advice — "
           "click into Rankings to see the evidence and set your own priorities.")

# ----------------------------------------------------------------------------------
# 3. The differentiators
# ----------------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    n_con = data.q("SELECT COUNT(*) c FROM contradictions")["c"].iloc[0]
    st.metric("Expert contradictions detected", int(n_con))
    st.page_link("pages/2_⚔️_Contradiction_Matrix.py", label="See where experts disagree", icon="⚔️")
with c2:
    n_ev = data.q("SELECT COUNT(*) c FROM evidence")["c"].iloc[0]
    st.metric("Evidence links", int(n_ev))
    st.page_link("pages/8_🔍_Evidence_Viewer.py", label="Audit any claim", icon="🔍")
with c3:
    n_cfpb = data.q("SELECT SUM(complaint_count) c FROM cfpb_complaint_stats "
                    "WHERE product IS NULL AND issue IS NULL")["c"].iloc[0]
    st.metric("CFPB complaints analyzed (36m)", int(n_cfpb or 0))
    st.page_link("pages/4_🗣️_Customer_Voice.py", label="Hear actual customers", icon="🗣️")

# ----------------------------------------------------------------------------------
# 4. Coverage, freshness, and honesty (tucked away but present)
# ----------------------------------------------------------------------------------
with st.expander("Tracked brokers, data freshness & how to read these numbers"):
    brokers = data.brokers()
    ps = data.q(
        """SELECT b.slug, AVG(ds.score) AS avg_score, AVG(ds.confidence) AS avg_conf,
                  SUM(ds.evidence_count) AS evidence
           FROM dimension_scores ds JOIN brokers b ON b.id = ds.broker_id GROUP BY b.slug"""
    ).set_index("slug")
    overview = []
    for _, b in brokers.iterrows():
        r = ps.loc[b["slug"]] if b["slug"] in ps.index else None
        overview.append({
            "Broker": b["name"],
            "Mean score (unweighted)": round(r["avg_score"], 1) if r is not None else None,
            "Confidence": round(r["avg_conf"], 0) if r is not None else None,
            "Client assets": f"~${b['aum_usd_billions']:,.0f}B" if pd.notna(b["aum_usd_billions"]) else "not disclosed",
            "SIPC": "yes" if b["sipc_member"] else "no",
            "Site": b["website"],
        })
    st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)

    st.markdown("**Data freshness** — every pipeline step is logged; failures and skips are shown, "
                "and stale data is penalized in scoring, never hidden.")
    fresh = data.freshness()
    if not fresh.empty:
        st.dataframe(
            fresh.rename(columns={"step": "Step", "status": "Status", "detail": "Detail",
                                  "finished_at": "Finished (UTC)"}),
            use_container_width=True, hide_index=True,
        )
    st.warning(
        "Scores are estimates from public evidence at collection time. Customer reviews are "
        "self-selected and skew negative; expert reviews may carry affiliate incentives; CFPB "
        "coverage differs by business model. Individual needs vary — see **Limitations & "
        "Disclosures** for the full picture.",
        icon="⚠️",
    )
