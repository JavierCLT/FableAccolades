import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from components import data
from components.evidence import dimension_evidence_ids, evidence_expander
from components.hovercard import evidence_items, hover_html
from components.layout import confidence_badge, page_setup

page_setup("Rankings by Persona", icon="🏆")

personas = data.personas()
dims = data.dimensions()

persona_name = st.pills("Investor persona", personas["name"].tolist(),
                        default=personas["name"].iloc[0], selection_mode="single")
if not persona_name:
    persona_name = personas["name"].iloc[0]
persona = personas[personas["name"] == persona_name].iloc[0]
st.caption(persona["description"])

default_weights = data.persona_weights(int(persona["id"]))

with st.expander("⚖️ Adjust dimension weights (defaults shown for this persona)"):
    st.caption(
        "Weights are renormalized automatically. Set a dimension to 0 to exclude it. "
        "The scoring formula is documented on the Methodology page."
    )
    cols = st.columns(4)
    weights: dict[str, float] = {}
    for i, (_, d) in enumerate(dims.iterrows()):
        with cols[i % 4]:
            weights[d["slug"]] = st.slider(
                d["name"], 0.0, 0.5,
                float(default_weights.get(d["slug"], 0.0)),
                0.01, key=f"w_{persona['slug']}_{d['slug']}",
            )
    if sum(weights.values()) == 0:
        st.error("All weights are zero — restore at least one.")
        st.stop()

scores = data.compute_persona_scores(weights)
ds = data.dimension_scores()

st.subheader(f"Ranking: {persona_name}")
st.caption(
    "Score = weighted mean of per-dimension scores (each blends objective facts 45% / "
    "customer voice 35% / expert consensus 20%, renormalized when a component is missing) "
    "± a bounded CFPB complaint-momentum adjustment. "
    "Confidence reflects evidence volume, source quality, recency, and corroboration."
)

for rank, (_, row) in enumerate(scores.iterrows(), start=1):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        c1.markdown(f"### {medal} {row['broker_name']}")
        c2.metric("Weighted score", f"{row['score']:.1f}")
        c3.metric("Confidence", confidence_badge(row["confidence"]))
        c4.metric("Evidence links", int(row["evidence_count"]))
        if abs(row["momentum_adj"]) >= 0.05:
            direction = "improving" if row["momentum_adj"] > 0 else "worsening"
            c1.caption(f"Includes {row['momentum_adj']:+.1f} pts CFPB complaint momentum ({direction}).")
        st.progress(min(1.0, row["score"] / 100))

        with st.expander("Dimension breakdown & evidence"):
            sub = ds[ds["broker_slug"] == row["broker_slug"]].sort_values("sort_order")
            for _, r in sub.iterrows():
                w = weights.get(r["dim_slug"], 0.0)
                if w <= 0:
                    continue
                b1, b2 = st.columns([3, 5])
                with b1:
                    ev_ids = dimension_evidence_ids(int(r["broker_id"]), int(r["dimension_id"]))
                    st.markdown(
                        f"<b>{r['dim_name']}</b> — "
                        + hover_html(f"{r['score']:.0f}/100", evidence_items(ev_ids, limit=5))
                        + f" <span style='color:#888'>(weight {w:.2f})</span>",
                        unsafe_allow_html=True,
                    )
                    parts = []
                    for label, key in (("facts", "fact_component"), ("customers", "customer_component"),
                                       ("experts", "expert_component")):
                        if pd.notna(r[key]):
                            parts.append(f"{label} {r[key]:.0f}")
                    st.caption(
                        " · ".join(parts)
                        + f" · confidence {confidence_badge(r['confidence'])}"
                        + (f" · ⚔️ contradiction −{r['contradiction_penalty']:.1f}" if r["contradiction_penalty"] else "")
                        + (f" · ⏳ staleness −{r['staleness_penalty']:.1f}" if r["staleness_penalty"] else "")
                    )
                with b2:
                    evidence_expander(
                        f"Evidence for {r['dim_name']}",
                        dimension_evidence_ids(int(r["broker_id"]), int(r["dimension_id"])),
                    )
