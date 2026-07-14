"""Refresh fast-changing facts from structured, authoritative broker documents."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from pypdf import PdfReader

from backend import config
from backend.collectors.base import BaseCollector
from backend.common import save_raw_bytes, today_iso, utc_now_iso
from backend.database import db
from backend.freshness import freshness_status, policy_for


MERRILL_RATE_SHEET_URL = (
    "https://prs.benefits.ml.com/Publish/Content/application/pdf/GWMOL/ICCRateSheet.pdf"
)


@dataclass(frozen=True)
class ExtractedFact:
    key: str
    value_numeric: float
    value_text: str
    as_of_date: str
    snippet: str


def _iso_date(raw: str) -> str:
    return datetime.strptime(raw, "%m/%d/%Y").date().isoformat()


def parse_merrill_rate_sheet(text: str) -> list[ExtractedFact]:
    """Extract the standard self-directed sweep and Preferred Deposit APYs."""
    normalized = re.sub(r"\s+", " ", text)
    sweep = re.search(
        r"Annual Percentage Yield as of (\d{1,2}/\d{1,2}/\d{4}).*?"
        r"Merrill Lynch Bank Deposit Program --- Tier 1 \(Less than \$250,000\)\s+([\d.]+)%",
        normalized,
    )
    preferred = re.search(
        r"Preferred Deposit.*?Annual Percentage Yield as of (\d{1,2}/\d{1,2}/\d{4})\s+"
        r"Less than \$100,000\s+([\d.]+)%",
        normalized,
    )
    if not sweep or not preferred:
        raise ValueError("Merrill rate sheet layout changed; expected APY rows were not found")

    sweep_date, sweep_value = _iso_date(sweep.group(1)), float(sweep.group(2))
    preferred_date, preferred_value = _iso_date(preferred.group(1)), float(preferred.group(2))
    return [
        ExtractedFact(
            key="default_sweep_apy_pct",
            value_numeric=sweep_value,
            value_text=(
                f"{sweep_value:.2f}% APY automatic bank-deposit sweep "
                "(Tier 1, balance under $250,000)"
            ),
            as_of_date=sweep_date,
            snippet=(
                "Merrill Lynch Bank Deposit Program Tier 1, for balances under "
                f"$250,000: {sweep_value:.2f}% APY."
            ),
        ),
        ExtractedFact(
            key="best_cash_apy_pct",
            value_numeric=preferred_value,
            value_text=(
                f"{preferred_value:.2f}% APY Preferred Deposit "
                "($100,000 minimum initial deposit; manual enrollment)"
            ),
            as_of_date=preferred_date,
            snippet=(
                f"Preferred Deposit standard tier: {preferred_value:.2f}% APY; "
                "$100,000 minimum initial deposit."
            ),
        ),
    ]


def _pdf_text(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    return " ".join(page.extract_text() or "" for page in reader.pages)


class VolatileFactsCollector(BaseCollector):
    name = "volatile_facts"

    def _record_result(
        self,
        conn: sqlite3.Connection,
        *,
        broker_id: int,
        fact: ExtractedFact,
        raw_path: str,
    ) -> str:
        current = conn.execute(
            "SELECT * FROM product_facts WHERE broker_id = ? AND fact_key = ?",
            (broker_id, fact.key),
        ).fetchone()
        if current is None:
            raise KeyError(f"Missing seeded product fact merrill/{fact.key}")

        source_id = db.lookup_id(conn, "sources", "broker_merrill")
        evidence_id = db.add_evidence(
            conn,
            source_id=source_id,
            broker_id=broker_id,
            url=MERRILL_RATE_SHEET_URL,
            title="Merrill Cash Management Solutions: Yields at a Glance",
            snippet=fact.snippet,
            retrieval_date=today_iso(),
            published_date=fact.as_of_date,
            collection_method="bulk_download",
            confidence="high",
            raw_path=raw_path,
            notes=(
                f"Machine-extracted official rate sheet; {policy_for(fact.key).cadence} "
                "refresh SLA."
            ),
        )
        changed_value = current["value_numeric"] != fact.value_numeric
        changed = changed_value or current["as_of_date"] != fact.as_of_date
        if changed_value:
            db.insert(
                conn,
                "fact_changes",
                {
                    "broker_id": broker_id,
                    "fact_key": fact.key,
                    "old_value_numeric": current["value_numeric"],
                    "new_value_numeric": fact.value_numeric,
                    "old_value_text": current["value_text"],
                    "new_value_text": fact.value_text,
                    "source_as_of_date": fact.as_of_date,
                    "detected_at": utc_now_iso(),
                    "evidence_id": evidence_id,
                },
            )
        conn.execute(
            """UPDATE product_facts
               SET value_numeric = ?, value_text = ?, as_of_date = ?, evidence_id = ?
               WHERE broker_id = ? AND fact_key = ?""",
            (
                fact.value_numeric,
                fact.value_text,
                fact.as_of_date,
                evidence_id,
                broker_id,
                fact.key,
            ),
        )
        status = "updated" if changed else "unchanged"
        db.insert(
            conn,
            "fact_verification_runs",
            {
                "broker_id": broker_id,
                "fact_key": fact.key,
                "source_url": MERRILL_RATE_SHEET_URL,
                "status": status,
                "observed_value_numeric": fact.value_numeric,
                "source_as_of_date": fact.as_of_date,
                "detail": "Structured value and source date extracted successfully.",
                "checked_at": utc_now_iso(),
            },
        )
        return status

    def _audit_stale_facts(self, conn: sqlite3.Connection) -> int:
        rows = conn.execute(
            """SELECT pf.broker_id, pf.fact_key, pf.as_of_date, e.url
               FROM product_facts pf JOIN evidence e ON e.id = pf.evidence_id"""
        ).fetchall()
        stale = 0
        for row in rows:
            if freshness_status(row["fact_key"], row["as_of_date"]) != "stale":
                continue
            stale += 1
            db.insert(
                conn,
                "fact_verification_runs",
                {
                    "broker_id": row["broker_id"],
                    "fact_key": row["fact_key"],
                    "source_url": row["url"],
                    "status": "stale",
                    "observed_value_numeric": None,
                    "source_as_of_date": row["as_of_date"],
                    "detail": "Freshness SLA exceeded; value withheld from scoring and current comparisons.",
                    "checked_at": utc_now_iso(),
                },
            )
        return stale

    def collect(self, conn: sqlite3.Connection) -> str:
        response = self.http.get(MERRILL_RATE_SHEET_URL)
        response.raise_for_status()
        if "pdf" not in response.headers.get("content-type", "").lower():
            raise ValueError("Merrill rate-sheet response was not a PDF")

        raw = save_raw_bytes("broker_sites", "merrill_cash_rates", response.content, ".pdf")
        raw_path = str(raw.relative_to(config.REPO_ROOT))
        facts = parse_merrill_rate_sheet(_pdf_text(response.content))
        broker_id = db.lookup_id(conn, "brokers", "merrill")
        statuses = [
            self._record_result(conn, broker_id=broker_id, fact=fact, raw_path=raw_path)
            for fact in facts
        ]
        stale = self._audit_stale_facts(conn)
        conn.commit()
        return (
            f"{len(facts)} official Merrill rate facts verified "
            f"({statuses.count('updated')} updated); {stale} expired facts withheld"
        )
