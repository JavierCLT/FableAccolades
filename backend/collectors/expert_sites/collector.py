"""Expert review site collector: verification-first.

For every expert rating in the database this collector re-fetches the cited review URL
(respecting robots.txt, rate-limited, honest user-agent) and classifies the claim:

  verified          — page live, rating machine-extracted; value confirmed or corrected,
                      evidence upgraded (collection_method='scrape', confidence high).
  unverified        — page live and mentions the broker, but the rating isn't
                      machine-extractable (client-side rendering), OR the publisher blocks
                      automated clients (403 etc.). The curated value is retained but
                      downgraded to low confidence with an explicit note. Unverified claims
                      carry reduced weight in scoring via the confidence factor.
  no_longer_published — page 404s, redirects away, or no longer mentions the broker
                      (publishers silently drop brokers from coverage). The evidence row is
                      marked unavailable and the rating is EXCLUDED from scoring and from
                      contradiction detection. The row stays visible in the Evidence Viewer
                      as a historical, no-longer-supported claim.

This guarantees the evidence chain: no score ever rests on a URL that no longer backs it.
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

# Name variants used to confirm a page still covers the broker at all.
BROKER_NAME_VARIANTS: dict[str, list[str]] = {
    "fidelity": ["Fidelity"],
    "schwab": ["Schwab"],
    "vanguard": ["Vanguard"],
    "robinhood": ["Robinhood"],
    "ibkr": ["Interactive Brokers", "IBKR"],
    "etrade": ["E*TRADE", "ETRADE", "E-Trade", "Etrade"],
    "merrill": ["Merrill"],
    "sofi": ["SoFi"],
    "webull": ["Webull"],
    "ally": ["Ally"],
    "jpmorgan": ["J.P. Morgan", "JP Morgan", "JPMorgan"],
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

    def _note(self, conn: sqlite3.Connection, evidence_id: int, note: str) -> None:
        conn.execute(
            "UPDATE evidence SET notes = COALESCE(notes || ' | ', '') || ? WHERE id = ?",
            (note, evidence_id),
        )

    def collect(self, conn: sqlite3.Connection) -> str:
        rows = conn.execute(
            """
            SELECT er.id AS rating_id, er.rating_raw, er.rating_scale_max, er.evidence_id,
                   er.dimension_id, e.url, e.collection_method,
                   s.slug AS source_slug, b.slug AS broker_slug
            FROM expert_ratings er
            JOIN evidence e ON e.id = er.evidence_id
            JOIN sources s ON s.id = er.source_id
            JOIN brokers b ON b.id = er.broker_id
            """
        ).fetchall()

        # Fetch each unique URL once. value: ("ok", html) | ("missing", None) | ("blocked", None)
        pages: dict[str, tuple[str, str | None]] = {}
        for row in rows:
            url = row["url"]
            if url in pages:
                continue
            try:
                resp = self.http.get(url)
                if resp.status_code in (404, 410):
                    pages[url] = ("missing", None)
                elif resp.status_code == 200:
                    pages[url] = ("ok", resp.text)
                    save_raw(
                        "expert_sites",
                        f"{row['source_slug']}_{abs(hash(url)) % 10**8}",
                        {"url": url, "status": resp.status_code, "html_head": resp.text[:200000]},
                    )
                else:
                    pages[url] = ("blocked", None)
            except Exception as exc:  # noqa: BLE001 — per-URL isolation
                self.log.warning("fetch failed for %s: %s", url, exc)
                pages[url] = ("blocked", None)

        today = today_iso()
        verified = updated = unverified = removed = blocked = 0
        for row in rows:
            status, html = pages[row["url"]]

            if status == "missing":
                removed += 1
                # Keep the original retrieval_date: it records when the claim was last seen.
                conn.execute(
                    "UPDATE evidence SET unavailable = 1, confidence = 'low' WHERE id = ?",
                    (row["evidence_id"],),
                )
                self._note(conn, row["evidence_id"],
                           f"WITHDRAWN|dead_url|{today}| Review URL no longer resolves — "
                           "claim excluded from scoring, retained for the record.")
                continue

            if status == "blocked":
                blocked += 1
                if row["collection_method"] == "manual_curation":
                    conn.execute("UPDATE evidence SET confidence = 'low' WHERE id = ?",
                                 (row["evidence_id"],))
                    self._note(conn, row["evidence_id"],
                               f"Publisher blocks automated verification (checked {today}) — "
                               "curated value retained as an UNVERIFIED claim at reduced weight.")
                continue

            # status == "ok": does the page still cover this broker at all?
            variants = BROKER_NAME_VARIANTS.get(row["broker_slug"], [])
            if not any(v.lower() in html.lower() for v in variants):
                removed += 1
                conn.execute(
                    "UPDATE evidence SET unavailable = 1, confidence = 'low' WHERE id = ?",
                    (row["evidence_id"],),
                )
                self._note(conn, row["evidence_id"],
                           f"WITHDRAWN|dropped_coverage|{today}| Publisher page no longer "
                           "mentions this broker — the review appears withdrawn; "
                           "claim excluded from scoring.")
                continue

            if row["dimension_id"] is None:
                live = self._extract_rating(row["source_slug"], html)
                if live is not None:
                    if abs(live - row["rating_raw"]) < 1e-9:
                        verified += 1
                    else:
                        updated += 1
                        conn.execute(
                            "UPDATE expert_ratings SET rating_raw = ?, rating_normalized = ? "
                            "WHERE id = ?",
                            (live, normalize_rating(live, row["rating_scale_max"]), row["rating_id"]),
                        )
                        conn.execute(
                            "UPDATE evidence SET snippet = ? WHERE id = ?",
                            (f"Published rating: {live} / {row['rating_scale_max']} (overall)",
                             row["evidence_id"]),
                        )
                    conn.execute(
                        "UPDATE evidence SET retrieval_date = ?, collection_method = 'scrape', "
                        "confidence = 'high', unavailable = 0 WHERE id = ?",
                        (today, row["evidence_id"]),
                    )
                    continue

            # Page live and mentions the broker, but the specific rating isn't extractable.
            unverified += 1
            if row["collection_method"] == "manual_curation":
                conn.execute("UPDATE evidence SET confidence = 'low' WHERE id = ?",
                             (row["evidence_id"],))
                self._note(conn, row["evidence_id"],
                           f"Page live but rating not machine-verifiable (checked {today}) — "
                           "curated value retained as an UNVERIFIED claim at reduced weight.")

        conn.commit()
        return (
            f"{verified} confirmed, {updated} corrected, {unverified} unverified (kept at low "
            f"confidence), {removed} no-longer-published (excluded from scoring), "
            f"{blocked} blocked from verification"
        )
