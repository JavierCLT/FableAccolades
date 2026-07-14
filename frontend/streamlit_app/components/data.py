"""Cached data access for the Streamlit app (read-only against the SQLite DB)."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.freshness import age_days, freshness_status, policy_for, summarize

DB_PATH = Path(os.environ.get("BBI_DB_PATH", REPO_ROOT / "data" / "processed" / "broker_index.db"))


def db_missing() -> bool:
    return not DB_PATH.exists()


def _mtime() -> float:
    return DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0


@st.cache_data(show_spinner=False)
def query(sql: str, _mtime: float | None = None, params: tuple = ()) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Query with cache invalidation tied to the DB file's mtime."""
    return query(sql, _mtime(), params)


# ---------------------------------------------------------------------------
# Common frames
# ---------------------------------------------------------------------------

def brokers() -> pd.DataFrame:
    return q("SELECT * FROM brokers WHERE active = 1 ORDER BY name")


def dimensions() -> pd.DataFrame:
    return q("SELECT * FROM dimensions ORDER BY sort_order")


def personas() -> pd.DataFrame:
    return q("SELECT * FROM personas ORDER BY sort_order")


def persona_weights(persona_id: int) -> dict[str, float]:
    df = q(
        """SELECT d.slug, pw.weight FROM persona_weights pw
           JOIN dimensions d ON d.id = pw.dimension_id WHERE pw.persona_id = ?""",
        (persona_id,),
    )
    return dict(zip(df["slug"], df["weight"]))


def dimension_scores() -> pd.DataFrame:
    return q(
        """SELECT ds.*, b.slug AS broker_slug, b.name AS broker_name,
                  d.slug AS dim_slug, d.name AS dim_name,
                  d.description AS dim_description, d.sort_order
           FROM dimension_scores ds
           JOIN brokers b ON b.id = ds.broker_id
           JOIN dimensions d ON d.id = ds.dimension_id
           ORDER BY b.name, d.sort_order"""
    )


def momentum() -> pd.DataFrame:
    return q(
        """SELECT bs.broker_id, b.slug AS broker_slug, bs.value AS momentum, bs.detail
           FROM broker_signals bs JOIN brokers b ON b.id = bs.broker_id
           WHERE bs.key = 'cfpb_momentum'"""
    )


def evidence_by_ids(ids: list[int]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame()
    ph = ",".join("?" for _ in ids)
    return q(
        f"""SELECT e.*, s.name AS source_name, s.publisher, s.source_type, s.quality_weight
            FROM evidence e JOIN sources s ON s.id = e.source_id
            WHERE e.id IN ({ph})""",
        tuple(ids),
    )


def compute_persona_scores(weights: dict[str, float]) -> pd.DataFrame:
    """Recompute persona scores live from dimension scores with user-supplied weights.
    Mirrors backend.scoring.engine exactly: weighted mean + bounded CFPB momentum."""
    ds = dimension_scores()
    mom = momentum().set_index("broker_slug")["momentum"] if not momentum().empty else pd.Series(dtype=float)
    rows = []
    for slug, grp in ds.groupby("broker_slug"):
        num = conf = den = 0.0
        ev = 0
        for _, r in grp.iterrows():
            w = weights.get(r["dim_slug"], 0.0)
            if w <= 0:
                continue
            num += r["score"] * w
            conf += r["confidence"] * w
            den += w
            ev += int(r["evidence_count"])
        if den == 0:
            continue
        m = float(mom.get(slug, 0.0) or 0.0)
        rows.append(
            {
                "broker_slug": slug,
                "broker_name": grp["broker_name"].iloc[0],
                "score": max(0.0, min(100.0, num / den + m)),
                "confidence": conf / den,
                "evidence_count": ev,
                "momentum_adj": m,
            }
        )
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


def freshness() -> pd.DataFrame:
    return q(
        """SELECT step, status, detail, finished_at FROM pipeline_runs
           WHERE id IN (SELECT MAX(id) FROM pipeline_runs GROUP BY step)
           ORDER BY finished_at DESC"""
    )


def product_facts() -> pd.DataFrame:
    frame = q(
        """SELECT pf.*, b.name AS broker_name, b.slug AS broker_slug,
                  d.name AS dim_name, d.slug AS dim_slug, d.sort_order,
                  e.confidence, e.retrieval_date, e.url, e.title,
                  e.collection_method
           FROM product_facts pf
           JOIN brokers b ON b.id = pf.broker_id
           JOIN dimensions d ON d.id = pf.dimension_id
           JOIN evidence e ON e.id = pf.evidence_id
           WHERE b.active = 1
           ORDER BY d.sort_order, pf.fact_key, b.name"""
    )
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["freshness_status"] = frame.apply(
        lambda row: freshness_status(row["fact_key"], row["as_of_date"]), axis=1
    )
    frame["age_days"] = frame["as_of_date"].map(age_days)
    frame["max_age_days"] = frame["fact_key"].map(lambda key: policy_for(key).max_age_days)
    frame["is_current"] = frame["freshness_status"] == "fresh"
    return frame


def product_fact_freshness_summary(frame: pd.DataFrame | None = None) -> dict[str, int | float]:
    facts = product_facts() if frame is None else frame
    return summarize(facts[["fact_key", "as_of_date"]].to_dict("records"))


def customer_voice_rankings() -> pd.DataFrame:
    """Comparable customer-experience ranking with neutral treatment for coverage gaps."""
    scores = dimension_scores()
    brokers_frame = brokers()[["slug", "name"]].rename(
        columns={"slug": "broker_slug", "name": "broker_name"}
    )
    rows: list[dict] = []
    momentum_frame = momentum()
    momentum_lookup = (
        momentum_frame.set_index("broker_slug")["momentum"].to_dict()
        if not momentum_frame.empty
        else {}
    )

    for _, broker in brokers_frame.iterrows():
        sub = scores[scores["broker_slug"] == broker["broker_slug"]]

        def component(dim_slug: str, column: str) -> tuple[float, float, bool]:
            match = sub[sub["dim_slug"] == dim_slug]
            if match.empty or pd.isna(match.iloc[0][column]):
                return 50.0, 0.0, False
            return (
                float(match.iloc[0][column]),
                float(match.iloc[0]["confidence"]),
                True,
            )

        support, support_conf, support_ok = component("customer_support", "customer_component")
        reliability, reliability_conf, reliability_ok = component("reliability", "customer_component")
        app, app_conf, app_ok = component("mobile_app", "fact_component")
        trend = max(20.0, min(80.0, 50.0 + float(momentum_lookup.get(broker["broker_slug"], 0.0)) * 10.0))
        covered = sum((support_ok, reliability_ok, app_ok))
        coverage = covered / 3.0
        confidence_values = [
            value
            for value, present in (
                (support_conf, support_ok),
                (reliability_conf, reliability_ok),
                (app_conf, app_ok),
            )
            if present
        ]
        confidence = (sum(confidence_values) / len(confidence_values) if confidence_values else 0.0) * coverage
        rows.append(
            {
                "broker_slug": broker["broker_slug"],
                "broker_name": broker["broker_name"],
                "score": 0.35 * support + 0.30 * reliability + 0.20 * app + 0.15 * trend,
                "support": support,
                "reliability": reliability,
                "app": app,
                "trend": trend,
                "coverage": coverage * 100.0,
                "confidence": confidence,
                "evidence_count": int(sub["evidence_count"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["score", "confidence"], ascending=False).reset_index(drop=True)


def economic_value_rankings() -> pd.DataFrame:
    """Rank current economic value across cost, cash, and banking dimensions."""
    scores = dimension_scores()
    weights = {"costs_fees": 0.45, "cash_yield": 0.35, "banking_integration": 0.20}
    rows: list[dict] = []
    for slug, sub in scores.groupby("broker_slug"):
        by_dim = sub.set_index("dim_slug")
        weighted = confidence = den = 0.0
        evidence_count = 0
        for dim_slug, weight in weights.items():
            if dim_slug not in by_dim.index:
                continue
            row = by_dim.loc[dim_slug]
            weighted += float(row["score"]) * weight
            confidence += float(row["confidence"]) * weight
            den += weight
            evidence_count += int(row["evidence_count"])
        if den:
            rows.append(
                {
                    "broker_slug": slug,
                    "broker_name": sub.iloc[0]["broker_name"],
                    "score": weighted / den,
                    "confidence": confidence / den,
                    "evidence_count": evidence_count,
                }
            )
    return pd.DataFrame(rows).sort_values(["score", "confidence"], ascending=False).reset_index(drop=True)


def review_platform_ratings() -> pd.DataFrame:
    """Aggregate public ratings used for cross-platform context, not direct ranking."""
    return q(
        """SELECT b.slug AS broker_slug, b.name AS broker_name,
                  s.slug AS source_slug, s.name AS source_name, s.notes AS source_notes,
                  ar.rating_raw, ar.rating_scale_max, ar.review_count, ar.as_of_date,
                  e.url, e.confidence
           FROM aggregate_ratings ar
           JOIN brokers b ON b.id = ar.broker_id
           JOIN sources s ON s.id = ar.source_id
           JOIN evidence e ON e.id = ar.evidence_id
           WHERE b.active = 1
             AND s.slug IN ('apple_app_store', 'google_play', 'trustpilot')
           ORDER BY b.name, s.slug"""
    )


def sentiment_comparison() -> pd.DataFrame:
    """Positive and negative customer-theme volume by active broker."""
    frame = q(
        """SELECT b.slug AS broker_slug, b.name AS broker_name,
                  COALESCE(SUM(CASE WHEN cv.sentiment = 'positive' THEN cv.volume END), 0) AS positive,
                  COALESCE(SUM(CASE WHEN cv.sentiment = 'negative' THEN cv.volume END), 0) AS negative,
                  COALESCE(SUM(CASE WHEN cv.sentiment = 'mixed' THEN cv.volume END), 0) AS mixed,
                  COUNT(DISTINCT cv.evidence_id) AS evidence_count
           FROM brokers b
           LEFT JOIN customer_voice cv ON cv.broker_id = b.id
           WHERE b.active = 1
           GROUP BY b.id, b.slug, b.name
           ORDER BY b.name"""
    )
    if frame.empty:
        return frame
    frame = frame.copy()
    directional = frame["positive"] + frame["negative"]
    frame["positive_share"] = (frame["positive"] / directional.where(directional > 0, 1)) * 100.0
    frame["negative_share"] = (frame["negative"] / directional.where(directional > 0, 1)) * 100.0
    frame["net"] = frame["positive_share"] - frame["negative_share"]
    return frame.sort_values(["net", "positive"], ascending=True).reset_index(drop=True)
