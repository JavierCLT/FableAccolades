"""Command-line freshness gate for scheduled data builds."""

from __future__ import annotations

import argparse
import sqlite3

from backend.database import db
from backend.freshness import freshness_status, policy_for, summarize


def database_status(conn: sqlite3.Connection) -> dict[str, int | float]:
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT pf.fact_key, pf.as_of_date
            FROM product_facts pf
            JOIN brokers b ON b.id = pf.broker_id
            WHERE b.active = 1
            ORDER BY pf.fact_key
            """
        ).fetchall()
    ]
    result = summarize(rows)
    result["blocking_stale"] = sum(
        1
        for row in rows
        if policy_for(row["fact_key"]).blocks_scoring
        and freshness_status(row["fact_key"], row["as_of_date"]) != "fresh"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail when product-fact freshness misses its SLA")
    parser.add_argument("--min-coverage", type=float, default=95.0)
    parser.add_argument("--max-blocking-stale", type=int, default=0)
    args = parser.parse_args()

    conn = db.connect()
    status = database_status(conn)
    conn.close()
    print(
        "Product facts: "
        f"{status['fresh']}/{status['total']} current ({status['coverage_pct']}%); "
        f"{status['stale']} stale; {status['blocking_stale']} score-critical stale"
    )
    if status["coverage_pct"] < args.min_coverage:
        return 1
    if status["blocking_stale"] > args.max_blocking_stale:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
