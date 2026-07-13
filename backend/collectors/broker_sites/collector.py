"""Broker official-site collector.

Fetches and archives snapshots of every broker page cited as evidence for a product fact
(pricing pages, fee schedules, feature pages), respecting robots.txt with rate limiting.
Snapshots land in data/raw/broker_sites/ so any curated fact can be audited against the
page as it looked at collection time.

Extraction of structured values from marketing pages is broker-specific and fragile, so
this MVP stage verifies reachability and archives content; curated fact values are only
touched by humans (or future per-broker parsers) reviewing the snapshots. Pages that fail
to fetch are flagged on the evidence row (notes) so the dashboard can show verification
status honestly.
"""

from __future__ import annotations

import sqlite3

from backend.collectors.base import BaseCollector
from backend.common import save_raw, today_iso


class BrokerSitesCollector(BaseCollector):
    name = "broker_sites"

    def collect(self, conn: sqlite3.Connection) -> str:
        rows = conn.execute(
            """
            SELECT DISTINCT e.id AS evidence_id, e.url, b.slug AS broker_slug
            FROM product_facts pf
            JOIN evidence e ON e.id = pf.evidence_id
            JOIN brokers b ON b.id = pf.broker_id
            ORDER BY b.slug, e.url
            """
        ).fetchall()

        ok = failed = 0
        fetched: dict[str, bool] = {}
        for row in rows:
            url = row["url"]
            if url not in fetched:
                try:
                    resp = self.http.get(url)
                    success = resp.status_code == 200
                    if success:
                        save_raw(
                            "broker_sites",
                            f"{row['broker_slug']}_{abs(hash(url)) % 10**8}",
                            {"url": url, "status": resp.status_code, "html_head": resp.text[:200000]},
                        )
                except Exception as exc:  # noqa: BLE001 — per-URL isolation
                    self.log.warning("fetch failed for %s: %s", url, exc)
                    success = False
                fetched[url] = success
            if fetched[url]:
                ok += 1
                conn.execute(
                    "UPDATE evidence SET notes = COALESCE(notes || ' | ', '') || "
                    "'Page snapshot archived ' || ? WHERE id = ?",
                    (today_iso(), row["evidence_id"]),
                )
            else:
                failed += 1
                conn.execute(
                    "UPDATE evidence SET notes = COALESCE(notes || ' | ', '') || "
                    "'Snapshot fetch FAILED ' || ? WHERE id = ?",
                    (today_iso(), row["evidence_id"]),
                )
        conn.commit()
        return f"{ok} fact evidence pages archived, {failed} failed"
