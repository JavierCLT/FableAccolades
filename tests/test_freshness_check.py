import sqlite3

from backend.database import db
from backend.freshness_check import database_status


def test_database_status_counts_blocking_stale(tmp_path) -> None:
    conn = db.connect(tmp_path / "freshness.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO brokers (slug, name) VALUES ('test', 'Test Broker')")
    conn.execute(
        """INSERT INTO sources (slug, name, source_type, quality_weight)
           VALUES ('official', 'Official', 'broker_official', 1.0)"""
    )
    broker_id = conn.execute("SELECT id FROM brokers").fetchone()["id"]
    source_id = conn.execute("SELECT id FROM sources").fetchone()["id"]
    evidence_id = db.add_evidence(
        conn,
        source_id=source_id,
        broker_id=broker_id,
        url="https://example.com/rates",
        retrieval_date="2020-01-01",
        collection_method="manual_curation",
    )
    conn.execute(
        """INSERT INTO product_facts
           (broker_id, fact_key, value_numeric, as_of_date, evidence_id)
           VALUES (?, 'default_sweep_apy_pct', 1.0, '2020-01-01', ?)""",
        (broker_id, evidence_id),
    )
    conn.commit()
    result = database_status(conn)
    assert result["stale"] == 1
    assert result["blocking_stale"] == 1


def test_database_status_ignores_inactive_brokers(tmp_path) -> None:
    conn = db.connect(tmp_path / "freshness.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO brokers (slug, name, active) VALUES ('old', 'Old Broker', 0)")
    conn.execute(
        """INSERT INTO sources (slug, name, source_type, quality_weight)
           VALUES ('official', 'Official', 'broker_official', 1.0)"""
    )
    broker_id = conn.execute("SELECT id FROM brokers").fetchone()["id"]
    source_id = conn.execute("SELECT id FROM sources").fetchone()["id"]
    evidence_id = db.add_evidence(
        conn,
        source_id=source_id,
        broker_id=broker_id,
        url="https://example.com/rates",
        retrieval_date="2020-01-01",
        collection_method="manual_curation",
    )
    conn.execute(
        """INSERT INTO product_facts
           (broker_id, fact_key, value_numeric, as_of_date, evidence_id)
           VALUES (?, 'default_sweep_apy_pct', 1.0, '2020-01-01', ?)""",
        (broker_id, evidence_id),
    )
    conn.commit()
    result = database_status(conn)
    assert result == {
        "total": 0,
        "fresh": 0,
        "stale": 0,
        "invalid": 0,
        "coverage_pct": 0.0,
        "blocking_stale": 0,
    }
