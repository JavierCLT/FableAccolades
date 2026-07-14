"""SQLite helpers. Keep everything portable so migration to Postgres stays trivial."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from backend import config


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def insert(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> int:
    cols = ", ".join(row.keys())
    ph = ", ".join("?" for _ in row)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", list(row.values()))
    return int(cur.lastrowid)


def upsert(conn: sqlite3.Connection, table: str, row: dict[str, Any], conflict_cols: list[str]) -> None:
    cols = ", ".join(row.keys())
    ph = ", ".join("?" for _ in row)
    updates = ", ".join(f"{c}=excluded.{c}" for c in row if c not in conflict_cols)
    sql = (
        f"INSERT INTO {table} ({cols}) VALUES ({ph}) "
        f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {updates}"
    )
    conn.execute(sql, list(row.values()))


def lookup_id(conn: sqlite3.Connection, table: str, slug: str) -> int:
    row = conn.execute(f"SELECT id FROM {table} WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise KeyError(f"No row in {table} with slug={slug!r}")
    return int(row["id"])


def add_evidence(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    url: str,
    retrieval_date: str,
    collection_method: str,
    broker_id: int | None = None,
    title: str | None = None,
    snippet: str | None = None,
    published_date: str | None = None,
    confidence: str = "medium",
    raw_path: str | None = None,
    unavailable: bool = False,
    notes: str | None = None,
) -> int:
    return insert(
        conn,
        "evidence",
        {
            "source_id": source_id,
            "broker_id": broker_id,
            "url": url,
            "title": title,
            "snippet": snippet,
            "retrieval_date": retrieval_date,
            "published_date": published_date,
            "collection_method": collection_method,
            "confidence": confidence,
            "raw_path": raw_path,
            "unavailable": 1 if unavailable else 0,
            "notes": notes,
        },
    )
