"""End-to-end pipeline test on a temp database: seeds -> scoring, no network."""

import pytest

from backend.database import db, seed_loader
from backend.scoring import engine


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    db.init_schema(c)
    seed_loader.load_all(c)
    engine.compute_all(c)
    yield c
    c.close()


def test_every_active_broker_gets_scores(conn):
    rows = conn.execute(
        """SELECT b.slug, COUNT(ds.id) AS n FROM brokers b
           LEFT JOIN dimension_scores ds ON ds.broker_id = b.id
           WHERE b.active = 1 GROUP BY b.slug"""
    ).fetchall()
    assert len(rows) == 11
    for r in rows:
        assert r["n"] == 16, f"{r['slug']} has {r['n']} dimension scores, expected 16"


def test_scores_and_confidence_bounded(conn):
    for r in conn.execute("SELECT score, confidence FROM dimension_scores"):
        assert 0 <= r["score"] <= 100
        assert 0 <= r["confidence"] <= 100


def test_every_score_has_evidence(conn):
    for r in conn.execute("SELECT evidence_count FROM dimension_scores"):
        assert r["evidence_count"] > 0


def test_persona_scores_cover_all_brokers(conn):
    n = conn.execute("SELECT COUNT(*) c FROM persona_scores").fetchone()["c"]
    assert n == 9 * 11


def test_contradictions_detected_from_seed_data(conn):
    # Seed data contains real publisher disagreements (e.g. Robinhood, Vanguard overall).
    n = conn.execute("SELECT COUNT(*) c FROM contradictions").fetchone()["c"]
    assert n > 0
    for r in conn.execute("SELECT gap, severity FROM contradictions"):
        assert r["gap"] >= 15.0
        assert r["severity"] in ("moderate", "significant", "severe")


def test_all_data_points_link_to_evidence(conn):
    for table in ("product_facts", "expert_ratings", "accolades", "customer_voice", "aggregate_ratings"):
        orphan = conn.execute(
            f"SELECT COUNT(*) c FROM {table} t LEFT JOIN evidence e ON e.id = t.evidence_id "
            "WHERE e.id IS NULL"
        ).fetchone()["c"]
        assert orphan == 0, f"{table} has {orphan} rows without evidence"


def test_unavailable_evidence_excluded_from_scoring(conn):
    # Simulate a publisher withdrawing its reviews of one broker: mark all of
    # StockBrokers.com's Vanguard rating evidence unavailable, recompute, and verify no
    # score or contradiction rests on the withdrawn claims.
    conn.execute(
        """UPDATE evidence SET unavailable = 1 WHERE id IN (
             SELECT er.evidence_id FROM expert_ratings er
             JOIN sources s ON s.id = er.source_id
             JOIN brokers b ON b.id = er.broker_id
             WHERE s.slug = 'stockbrokers_com' AND b.slug = 'vanguard')"""
    )
    conn.commit()
    engine.compute_all(conn)
    n = conn.execute(
        """SELECT COUNT(*) c FROM contradictions c
           JOIN brokers b ON b.id = c.broker_id
           JOIN sources s ON s.id IN (c.source_a_id, c.source_b_id)
           WHERE b.slug = 'vanguard' AND s.slug = 'stockbrokers_com'"""
    ).fetchone()["c"]
    assert n == 0, "withdrawn claims must not appear in contradictions"
    # Scores still exist for every dimension (other evidence remains).
    n_scores = conn.execute(
        """SELECT COUNT(*) c FROM dimension_scores ds JOIN brokers b ON b.id = ds.broker_id
           WHERE b.slug = 'vanguard'"""
    ).fetchone()["c"]
    assert n_scores == 16


def test_persona_weights_sum_to_one(conn):
    rows = conn.execute(
        "SELECT persona_id, SUM(weight) s FROM persona_weights GROUP BY persona_id"
    ).fetchall()
    assert len(rows) == 9
    for r in rows:
        assert abs(r["s"] - 1.0) < 1e-6
