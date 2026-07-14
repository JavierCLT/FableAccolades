"""Scoring engine: fully deterministic, reproducible from the data-point tables.

Per broker x dimension it computes three components (0-100):
  fact     — objective product facts via rules in fact_rules.py
             (mobile_app uses aggregate app-store ratings as its objective component)
  customer — customer-voice themes: signed, volume/severity/recency/quality-weighted;
             customer_support additionally blends a CFPB complaint-rate friction score
  expert   — quality+recency-weighted mean of normalized expert ratings for that
             dimension (falls back to overall ratings at reduced weight), minus a
             contradiction penalty when publishers disagree

Blended with COMPONENT_WEIGHTS (renormalized over available components). Volatile facts
that miss their freshness SLA are excluded before scoring. Confidence is scored separately.
Persona scores are weight-averaged dimension scores plus a bounded CFPB momentum
adjustment. All constants live in constants.py and are documented in docs/scoring_logic.md.
"""

from __future__ import annotations

import math
import sqlite3
from datetime import date

from backend.common import get_logger, utc_now_iso
from backend.database import db
from backend.freshness import blocks_scoring
from backend.scoring import constants as C
from backend.scoring.confidence import confidence_score, recency_weight
from backend.scoring.contradictions import (
    contradiction_penalty,
    find_pairwise_contradictions,
)
from backend.scoring.fact_rules import fact_component

log = get_logger("scoring")

CONFIDENCE_FACTOR = {"high": 1.0, "medium": 0.8, "low": 0.55}


# --------------------------------------------------------------------------------------
# Component computations
# --------------------------------------------------------------------------------------

def _broker_facts(
    conn: sqlite3.Connection, broker_id: int, today: date | None = None
) -> dict[str, float | None]:
    rows = conn.execute(
        "SELECT fact_key, value_numeric, as_of_date FROM product_facts WHERE broker_id = ?",
        (broker_id,),
    ).fetchall()
    return {
        r["fact_key"]: r["value_numeric"]
        for r in rows
        if not blocks_scoring(r["fact_key"], r["as_of_date"], today=today)
    }


def _mobile_fact_component(conn: sqlite3.Connection, broker_id: int) -> tuple[float | None, list[int]]:
    """Objective mobile component = review-count-weighted mean of app-store ratings."""
    rows = conn.execute(
        """SELECT ar.rating_raw, ar.rating_scale_max, ar.review_count, ar.evidence_id
           FROM aggregate_ratings ar JOIN sources s ON s.id = ar.source_id
           WHERE ar.broker_id = ? AND s.source_type = 'app_store'""",
        (broker_id,),
    ).fetchall()
    if not rows:
        return None, []
    num = den = 0.0
    ev = []
    for r in rows:
        w = math.log10(max(10, r["review_count"] or 10))
        num += (r["rating_raw"] / r["rating_scale_max"] * 100.0) * w
        den += w
        ev.append(r["evidence_id"])
    return num / den, ev


def customer_signal(themes: list[dict], today: date | None = None) -> float:
    """Signed signal from theme rows: praise adds, complaints subtract scaled by severity,
    both weighted by sqrt(volume), recency, and source quality."""
    signal = 0.0
    for t in themes:
        w = math.sqrt(max(1, t["volume"])) * recency_weight(t.get("observed_date"), today) * t.get("quality_weight", 0.7)
        if t["sentiment"] == "positive":
            signal += w
        elif t["sentiment"] == "negative":
            signal -= w * (t.get("severity", 2) / 3.0)
        # mixed contributes evidence but no direction
    return signal


def customer_component_score(themes: list[dict], today: date | None = None) -> float | None:
    if not themes:
        return None
    return 50.0 + 45.0 * math.tanh(customer_signal(themes, today) / C.CUSTOMER_SIGNAL_SCALE)


def cfpb_friction_score(complaints_12m: int, aum_billions: float | None) -> float | None:
    """Complaints per $B of client assets (trailing 12m) -> 0-100 friction score.
    Returns None when AUM is unknown (never guesses a denominator)."""
    if aum_billions is None or aum_billions <= 0:
        return None
    rate = complaints_12m / aum_billions
    if rate <= C.CFPB_FRICTION_BASELINE_RATE:
        return C.CFPB_FRICTION_BASE_SCORE + 10.0
    decades_over = math.log10(rate / C.CFPB_FRICTION_BASELINE_RATE)
    return max(C.CFPB_FRICTION_MIN, C.CFPB_FRICTION_BASE_SCORE - C.CFPB_FRICTION_SLOPE * decades_over)


def blend_components(
    fact: float | None, customer: float | None, expert: float | None
) -> float | None:
    parts = [
        (fact, C.COMPONENT_WEIGHTS["fact"]),
        (customer, C.COMPONENT_WEIGHTS["customer"]),
        (expert, C.COMPONENT_WEIGHTS["expert"]),
    ]
    avail = [(v, w) for v, w in parts if v is not None]
    if not avail:
        return None
    total_w = sum(w for _, w in avail)
    return sum(v * w for v, w in avail) / total_w


def staleness_penalty(conn: sqlite3.Connection, broker_id: int, dimension_id: int,
                      today: date | None = None) -> float:
    """Retained for schema compatibility; expired volatile facts are now withheld."""
    return 0.0


# --------------------------------------------------------------------------------------
# Full recompute
# --------------------------------------------------------------------------------------

def compute_all(conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    today = date.today()
    brokers = conn.execute("SELECT * FROM brokers WHERE active = 1").fetchall()
    dimensions = conn.execute("SELECT * FROM dimensions ORDER BY sort_order").fetchall()

    conn.execute("DELETE FROM dimension_scores")
    conn.execute("DELETE FROM contradictions")
    conn.execute("DELETE FROM persona_scores")
    conn.execute("DELETE FROM broker_signals")

    # ---- CFPB signals per broker (friction + momentum) ----
    cfpb: dict[int, dict] = {}
    for b in brokers:
        rows = conn.execute(
            "SELECT issue, complaint_count, company_name FROM cfpb_complaint_stats "
            "WHERE broker_id = ? AND product IS NULL", (b["id"],)
        ).fetchall()
        recent = prior = None
        found = any(r["company_name"] != "NOT_FOUND" for r in rows)
        for r in rows:
            if r["issue"] == "__WINDOW_RECENT_12M__":
                recent = r["complaint_count"]
            elif r["issue"] == "__WINDOW_PRIOR_12M__":
                prior = r["complaint_count"]
        momentum = 0.0
        if found and recent is not None and prior and prior >= 20:
            # Bounded: complaints doubling year-over-year => about -MOMENTUM_MAX_ABS.
            momentum = -C.MOMENTUM_MAX_ABS * math.tanh(math.log(max(recent, 1) / prior) / math.log(2))
        friction = cfpb_friction_score(recent, b["aum_usd_billions"]) if found and recent is not None else None
        cfpb[b["id"]] = {"found": found, "recent": recent, "prior": prior,
                         "momentum": round(momentum, 2), "friction": friction}
        db.upsert(conn, "broker_signals",
                  {"broker_id": b["id"], "key": "cfpb_momentum", "value": round(momentum, 2),
                   "detail": (f"CFPB complaints trailing 12m: {recent}, prior 12m: {prior}" if found
                              else "No CFPB company entity (coverage gap) — momentum neutral"),
                   "computed_at": now}, ["broker_id", "key"])

    # ---- dimension scores ----
    for b in brokers:
        facts = _broker_facts(conn, b["id"], today)
        for d in dimensions:
            evidence_ids: set[int] = set()
            quality_weights: list[float] = []
            recencies: list[float] = []

            # Fact component
            if d["slug"] == "mobile_app":
                fact, ev = _mobile_fact_component(conn, b["id"])
                evidence_ids.update(ev)
            else:
                fact = fact_component(d["slug"], facts)
                if fact is not None:
                    for r in conn.execute(
                        """SELECT pf.fact_key, pf.evidence_id, pf.as_of_date, e.confidence
                           FROM product_facts pf JOIN evidence e ON e.id = pf.evidence_id
                           WHERE pf.broker_id = ? AND pf.dimension_id = ?""",
                        (b["id"], d["id"]),
                    ).fetchall():
                        if blocks_scoring(r["fact_key"], r["as_of_date"], today=today):
                            continue
                        evidence_ids.add(r["evidence_id"])
                        quality_weights.append(0.95 * CONFIDENCE_FACTOR[r["confidence"]])
                        recencies.append(recency_weight(r["as_of_date"], today))

            # Customer component
            theme_rows = conn.execute(
                """SELECT cv.*, s.quality_weight FROM customer_voice cv
                   JOIN sources s ON s.id = cv.source_id
                   WHERE cv.broker_id = ? AND cv.dimension_id = ?""",
                (b["id"], d["id"]),
            ).fetchall()
            themes = [dict(t) for t in theme_rows]
            customer = customer_component_score(themes, today)
            for t in theme_rows:
                evidence_ids.add(t["evidence_id"])
                quality_weights.append(t["quality_weight"])
                recencies.append(recency_weight(t["observed_date"], today))
            if d["slug"] == "customer_support":
                sig = cfpb[b["id"]]
                if sig["found"] and sig["friction"] is not None:
                    ev_row = conn.execute(
                        """SELECT ccs.evidence_id FROM cfpb_complaint_stats ccs
                           WHERE ccs.broker_id = ? AND ccs.product IS NULL AND ccs.issue IS NULL""",
                        (b["id"],),
                    ).fetchone()
                    if customer is None:
                        customer = sig["friction"]
                    else:
                        customer = (1 - C.CFPB_FRICTION_WEIGHT) * customer + C.CFPB_FRICTION_WEIGHT * sig["friction"]
                    if ev_row:
                        evidence_ids.add(ev_row["evidence_id"])
                        quality_weights.append(1.0)
                        recencies.append(1.0)

            # Expert component
            # Claims whose evidence is marked unavailable (review withdrawn / URL dead) are
            # excluded from scoring entirely — a score must never rest on a dead source.
            expert_rows = conn.execute(
                """SELECT er.rating_normalized AS score, er.source_id, er.evidence_id,
                          s.quality_weight, e.retrieval_date, e.confidence
                   FROM expert_ratings er
                   JOIN sources s ON s.id = er.source_id
                   JOIN evidence e ON e.id = er.evidence_id
                   WHERE er.broker_id = ? AND er.dimension_id = ? AND e.unavailable = 0""",
                (b["id"], d["id"]),
            ).fetchall()
            fallback = False
            if not expert_rows:
                fallback = True
                expert_rows = conn.execute(
                    """SELECT er.rating_normalized AS score, er.source_id, er.evidence_id,
                              s.quality_weight, e.retrieval_date, e.confidence
                       FROM expert_ratings er
                       JOIN sources s ON s.id = er.source_id
                       JOIN evidence e ON e.id = er.evidence_id
                       WHERE er.broker_id = ? AND er.dimension_id IS NULL AND e.unavailable = 0""",
                    (b["id"],),
                ).fetchall()

            expert = None
            expert_gap = None
            if expert_rows:
                num = den = 0.0
                scores = []
                for r in expert_rows:
                    w = r["quality_weight"] * CONFIDENCE_FACTOR[r["confidence"]]
                    num += r["score"] * w
                    den += w
                    scores.append(r["score"])
                    evidence_ids.add(r["evidence_id"])
                    quality_weights.append(r["quality_weight"] * (0.7 if fallback else 1.0))
                    recencies.append(recency_weight(r["retrieval_date"], today))
                expert = num / den
                expert_gap = max(scores) - min(scores) if len(scores) > 1 else 0.0

            # Contradictions recorded only for dimension-specific ratings (not fallback),
            # since overall-rating disagreements are stored once under dimension NULL.
            penalty = 0.0
            if expert is not None and not fallback:
                penalty = contradiction_penalty(expert_gap)
                expert = max(0.0, expert - penalty)
                for c in find_pairwise_contradictions(
                    [{"source_id": r["source_id"], "score": r["score"], "evidence_id": r["evidence_id"]}
                     for r in expert_rows]
                ):
                    db.insert(conn, "contradictions",
                              {"broker_id": b["id"], "dimension_id": d["id"], **c, "computed_at": now})

            score = blend_components(fact, customer, expert)
            if score is None:
                continue
            stale = staleness_penalty(conn, b["id"], d["id"], today)
            score = max(0.0, min(100.0, score - stale))

            n_components = sum(1 for v in (fact, customer, expert) if v is not None)
            conf = confidence_score(
                evidence_count=len(evidence_ids),
                avg_quality=(sum(quality_weights) / len(quality_weights)) if quality_weights else 0.5,
                avg_recency=(sum(recencies) / len(recencies)) if recencies else 0.5,
                components_present=n_components,
                expert_gap=expert_gap,
            )
            db.insert(conn, "dimension_scores", {
                "broker_id": b["id"], "dimension_id": d["id"],
                "score": round(score, 1), "confidence": conf,
                "evidence_count": len(evidence_ids),
                "fact_component": round(fact, 1) if fact is not None else None,
                "customer_component": round(customer, 1) if customer is not None else None,
                "expert_component": round(expert, 1) if expert is not None else None,
                "contradiction_penalty": penalty, "staleness_penalty": stale,
                "computed_at": now,
            })

    # ---- overall-rating contradictions (dimension NULL) ----
    for b in brokers:
        rows = conn.execute(
            """SELECT er.rating_normalized AS score, er.source_id, er.evidence_id
               FROM expert_ratings er JOIN evidence e ON e.id = er.evidence_id
               WHERE er.broker_id = ? AND er.dimension_id IS NULL AND e.unavailable = 0""",
            (b["id"],),
        ).fetchall()
        for c in find_pairwise_contradictions([dict(r) for r in rows]):
            db.insert(conn, "contradictions",
                      {"broker_id": b["id"], "dimension_id": None, **c, "computed_at": now})

    # ---- persona scores (default weights + momentum) ----
    personas = conn.execute("SELECT * FROM personas").fetchall()
    for p in personas:
        weights = {
            r["dimension_id"]: r["weight"]
            for r in conn.execute(
                "SELECT dimension_id, weight FROM persona_weights WHERE persona_id = ?", (p["id"],)
            )
        }
        for b in brokers:
            dscores = {
                r["dimension_id"]: r
                for r in conn.execute(
                    "SELECT * FROM dimension_scores WHERE broker_id = ?", (b["id"],)
                )
            }
            num = conf_num = den = 0.0
            ev_total = 0
            for dim_id, w in weights.items():
                row = dscores.get(dim_id)
                if row is None or w == 0:
                    continue
                num += row["score"] * w
                conf_num += row["confidence"] * w
                den += w
                ev_total += row["evidence_count"]
            if den == 0:
                continue
            score = num / den + cfpb[b["id"]]["momentum"]
            db.upsert(conn, "persona_scores", {
                "persona_id": p["id"], "broker_id": b["id"],
                "score": round(max(0.0, min(100.0, score)), 1),
                "confidence": round(conf_num / den, 1),
                "evidence_count": ev_total, "computed_at": now,
            }, ["persona_id", "broker_id"])

    conn.commit()
    n_dim = conn.execute("SELECT COUNT(*) c FROM dimension_scores").fetchone()["c"]
    n_con = conn.execute("SELECT COUNT(*) c FROM contradictions").fetchone()["c"]
    log.info("Scoring complete: %d dimension scores, %d contradictions", n_dim, n_con)
