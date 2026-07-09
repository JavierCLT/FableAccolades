"""Expert review site collector.

For every expert rating in the database, this collector re-fetches the cited review URL
(respecting robots.txt, rate-limited, honest user-agent), archives an HTML snapshot under
data/raw/expert_sites/, and attempts to extract the published rating with per-site regex
patterns. When extraction succeeds and differs from the stored value, the rating and its
evidence are refreshed (collection_method='scrape', retrieval date updated).

Reality check, by design: several of these publishers block non-browser clients (403) or
render ratings client-side. Failures are logged per-URL and never overwrite curated data —
the stored evidence keeps its original retrieval date so staleness stays visible. For
stubborn sites, Playwright can be enabled selectively (see docs/sources.md).
"""

from __future__ import annotations

import re
import sqlite3

from backend.collectors.base import BaseCollector
from backend.common import save_raw, today_iso
from backend.normalizers.expert_ratings import normalize_rating

# Per-source regex patterns that capture a decimal rating out of 5 in page HTML/JSON-LD.
RATING_PATTERNS: dict[str, list[str]] = {
    "nerdwallet": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?', r'([0-9]\.[0-9])\s*/\s*5'],
    "stockbrokers_com": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?', r'([0-9]\.[0-9])\s+Overall'],
    "bankrate": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?', r'Rating:\s*([0-9.]+)'],
    "investopedia": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?'],
    "forbes_advisor": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?'],
    "motley_fool_ascent": [r'"ratingValue"\s*:\s*"?([0-9.]+)"?'],
}


class ExpertSitesCollector(BaseCollector):
    name = "expert_sites"

    def _extract_rating(self, source_slug: str, html: str) -> float | None:
        for pattern in RATING_PATTERNS.get(source_slug, []):
            m = re.search(pattern, html)
            if m:
                try:
                    value = float(m.group(1))
                except ValueError:
                    continue
                if 0 < value <= 5:
                    return value
        return None

    def collect(self, conn: sqlite3.Connection) -> str:
        rows = conn.execute(
            """
            SELECT er.id AS rating_id, er.rating_raw, er.rating_scale_max, er.evidence_id,
                   e.url, s.slug AS source_slug, b.slug AS broker_slug,
                   er.dimension_id
            FROM expert_ratings er
            JOIN evidence e ON e.id = er.evidence_id
            JOIN sources s ON s.id = er.source_id
            JOIN brokers b ON b.id = er.broker_id
            WHERE er.dimension_id IS NULL   -- overall ratings only; category scores are page-specific
            """
        ).fetchall()

        fetched = updated = confirmed = failed = 0
        seen_urls: dict[str, str | None] = {}
        for row in rows:
            url = row["url"]
            try:
                if url not in seen_urls:
                    resp = self.http.get(url)
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code}")
                    html = resp.text
                    save_raw(
                        "expert_sites",
                        f"{row['source_slug']}_{row['broker_slug']}",
                        {"url": url, "status": resp.status_code, "html_head": html[:200000]},
                    )
                    seen_urls[url] = html
                    fetched += 1
                html = seen_urls[url]
                if html is None:
                    raise RuntimeError("previous fetch failed")
            except Exception as exc:  # noqa: BLE001 — per-URL isolation
                seen_urls[url] = None
                failed += 1
                self.log.warning("fetch failed for %s: %s", url, exc)
                continue

            live = self._extract_rating(row["source_slug"], html)
            if live is None:
                continue
            if abs(live - row["rating_raw"]) < 1e-9:
                confirmed += 1
                conn.execute(
                    "UPDATE evidence SET retrieval_date = ?, collection_method = 'scrape', "
                    "confidence = 'high' WHERE id = ?",
                    (today_iso(), row["evidence_id"]),
                )
            else:
                updated += 1
                conn.execute(
                    "UPDATE expert_ratings SET rating_raw = ?, rating_normalized = ? WHERE id = ?",
                    (live, normalize_rating(live, row["rating_scale_max"]), row["rating_id"]),
                )
                conn.execute(
                    "UPDATE evidence SET retrieval_date = ?, collection_method = 'scrape', "
                    "confidence = 'high', snippet = ? WHERE id = ?",
                    (today_iso(), f"Published rating: {live} / {row['rating_scale_max']} (overall)",
                     row["evidence_id"]),
                )

        conn.commit()
        return (
            f"fetched {fetched} pages, {failed} blocked/failed, "
            f"{confirmed} ratings confirmed, {updated} ratings updated"
        )
