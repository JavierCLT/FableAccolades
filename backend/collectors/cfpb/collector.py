"""CFPB Consumer Complaint Database collector (official public API, no key required).

Notes on coverage (important for fair interpretation, also surfaced in the UI):
the CFPB database covers *consumer financial products* (checking/savings, money movement,
credit). Classic brokerage disputes are handled by FINRA/SEC and rarely appear here.
Brokers with consumer banking arms (Robinhood, Schwab, E*TRADE Bank) therefore appear,
while Fidelity, Vanguard, and IBKR have no matching CFPB company entity. Absence is a
coverage gap — NOT a clean record — and is stored explicitly as 'checked, not found'.

Company-name mappings below were verified against the live API's company suggest endpoint.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import date, timedelta

from backend import config
from backend.collectors.base import BaseCollector
from backend.common import save_raw, today_iso
from backend.database import db

API_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
PUBLIC_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/"

# Verified CFPB company strings per broker (checked against the company-suggest endpoint).
# Empty list = verified absent (coverage gap), or deliberately excluded because the CFPB
# entity is a diversified parent whose complaints cannot be fairly attributed to the retail
# brokerage brand (recorded with an explanation, never silently).
# attribution_caveat=True keeps the data visible but disables the complaint-rate friction
# score, because the complaint stream spans products beyond investing.
COMPANY_MAP: dict[str, dict] = {
    "fidelity": {"companies": []},
    "schwab": {"companies": ["CHARLES SCHWAB CORPORATION, THE"]},
    "vanguard": {"companies": []},
    "robinhood": {"companies": ["ROBINHOOD MARKETS INC."]},
    "ibkr": {"companies": []},
    # E*TRADE's consumer bank entity. Morgan Stanley entities are deliberately excluded:
    # attributing all Morgan Stanley complaints to E*TRADE would be unfair.
    "etrade": {"companies": ["E*TRADE BANK"]},
    # SoFi: single retail brand, but complaints span lending/banking, not just Invest.
    "sofi": {"companies": ["SOFI TECHNOLOGIES, INC."], "attribution_caveat": True},
    # Webull's CFPB entity is its payments/crypto affiliate (tiny volume).
    "webull": {"companies": ["WEBULL PAY HOLDINGS (US) INC"], "attribution_caveat": True},
    "public": {"companies": []},
    # Diversified parents excluded: complaints are dominated by auto lending (Ally) and
    # consumer banking (JPMorgan Chase, Bank of America/Merrill) — attributing them to the
    # brokerage product would be unfair and violate same-methodology neutrality.
    "merrill": {"companies": [], "exclusion_note": "Bank of America/Merrill complaints cannot be isolated to Merrill Edge self-directed."},
    "jpmorgan": {"companies": [], "exclusion_note": "JPMORGAN CHASE & CO. complaints are bank-wide and cannot be isolated to Self-Directed Investing."},
}

TOP_N_CATEGORIES = 8


class CfpbCollector(BaseCollector):
    name = "cfpb"

    def _fetch_company(self, company: str, date_min: str) -> list[dict]:
        resp = self.http.get(
            API_URL,
            params={
                "company": company,
                "date_received_min": date_min,
                "format": "json",
                "field": "all",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        # format=json returns a full export: a list of {_source: {...}} hits.
        return [h.get("_source", h) for h in payload if isinstance(h, dict)]

    def collect(self, conn: sqlite3.Connection) -> str:
        source_id = db.lookup_id(conn, "sources", "cfpb")
        today = date.today()
        period_start = (today - timedelta(days=config.CFPB_LOOKBACK_MONTHS * 30)).isoformat()
        period_end = today.isoformat()
        one_year_ago = (today - timedelta(days=365)).isoformat()
        two_years_ago = (today - timedelta(days=730)).isoformat()

        conn.execute("DELETE FROM cfpb_complaint_stats")
        results = []
        for broker_slug, cfg in COMPANY_MAP.items():
            companies = cfg["companies"]
            broker_id = db.lookup_id(conn, "brokers", broker_slug)
            if not companies:
                snippet = cfg.get("exclusion_note") or (
                    "No matching company entity in the CFPB database (verified via the "
                    "company-suggest endpoint). Coverage gap: this broker has no consumer "
                    "banking arm subject to CFPB complaint intake, NOT a clean record."
                )
                ev_id = db.add_evidence(
                    conn,
                    source_id=source_id,
                    broker_id=broker_id,
                    url=PUBLIC_URL,
                    title="CFPB Consumer Complaint Database — company lookup",
                    snippet=snippet,
                    retrieval_date=today_iso(),
                    collection_method="api",
                    confidence="high",
                    unavailable=True,
                )
                db.insert(
                    conn,
                    "cfpb_complaint_stats",
                    {
                        "broker_id": broker_id,
                        "company_name": "NOT_FOUND",
                        "period_start": period_start,
                        "period_end": period_end,
                        "product": None,
                        "issue": None,
                        "complaint_count": 0,
                        "timely_response_pct": None,
                        "evidence_id": ev_id,
                    },
                )
                results.append(f"{broker_slug}: not in CFPB (recorded as coverage gap)")
                continue

            caveat = bool(cfg.get("attribution_caveat"))
            records: list[dict] = []
            for company in companies:
                records.extend(self._fetch_company(company, period_start))
            raw_path = save_raw("cfpb", f"{broker_slug}_complaints", records)
            company_label = "; ".join(companies)

            timely_yes = sum(1 for r in records if str(r.get("timely", "")).lower() == "yes")
            timely_pct = round(100.0 * timely_yes / len(records), 1) if records else None

            snippet = (
                f"{len(records)} complaints received {period_start} to {period_end} "
                f"(official API export); {timely_pct}% received a timely company response."
            )
            if caveat:
                snippet += (
                    " ATTRIBUTION CAVEAT: this CFPB entity spans business lines beyond the "
                    "brokerage product (e.g. lending/payments), so complaint volume is shown "
                    "for context only and is excluded from friction/momentum scoring."
                )
            ev_id = db.add_evidence(
                conn,
                source_id=source_id,
                broker_id=broker_id,
                url=f"{PUBLIC_URL}?company={companies[0].replace(' ', '%20')}",
                title=f"CFPB complaints for {company_label}",
                snippet=snippet,
                retrieval_date=today_iso(),
                collection_method="api",
                confidence="high" if not caveat else "medium",
                raw_path=str(raw_path),
            )

            def stat_row(product, issue, count, p_start=period_start, p_end=period_end):
                return {
                    "broker_id": broker_id,
                    "company_name": company_label,
                    "period_start": p_start,
                    "period_end": p_end,
                    "product": product,
                    "issue": issue,
                    "complaint_count": count,
                    "timely_response_pct": timely_pct if product is None and issue is None else None,
                    "evidence_id": ev_id,
                }

            # Overall window total.
            db.insert(conn, "cfpb_complaint_stats", stat_row(None, None, len(records)))
            # Momentum windows: trailing 12 months vs the 12 months before that. Skipped for
            # attribution-caveat entities so unrelated business lines never move scores.
            if not caveat:
                recent = sum(1 for r in records if str(r.get("date_received", "")) >= one_year_ago)
                prior = sum(
                    1
                    for r in records
                    if two_years_ago <= str(r.get("date_received", "")) < one_year_ago
                )
                db.insert(conn, "cfpb_complaint_stats",
                          stat_row(None, "__WINDOW_RECENT_12M__", recent, one_year_ago, period_end))
                db.insert(conn, "cfpb_complaint_stats",
                          stat_row(None, "__WINDOW_PRIOR_12M__", prior, two_years_ago, one_year_ago))
            # Category breakdowns.
            for product, count in Counter(r.get("product") or "Unknown" for r in records).most_common(TOP_N_CATEGORIES):
                db.insert(conn, "cfpb_complaint_stats", stat_row(product, None, count))
            for issue, count in Counter(r.get("issue") or "Unknown" for r in records).most_common(TOP_N_CATEGORIES):
                db.insert(conn, "cfpb_complaint_stats", stat_row(None, issue, count))

            results.append(f"{broker_slug}: {len(records)} complaints ({company_label})")

        conn.commit()
        return " | ".join(results)
