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
                  d.slug AS dim_slug, d.name AS dim_name, d.sort_order
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
