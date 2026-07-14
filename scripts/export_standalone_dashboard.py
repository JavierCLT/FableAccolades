"""Build a single-file, offline-capable Best Broker Index dashboard."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import plotly


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "frontend" / "streamlit_app"
TEMPLATE_PATH = REPO_ROOT / "frontend" / "standalone" / "dashboard.html"
OUTPUT_PATH = REPO_ROOT / "dist" / "best-broker-index.html"
PLOTLY_BUNDLE = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
DOCS_ROOT = REPO_ROOT / "docs"

SOURCE_INCENTIVES = {
    "cfpb": "Public regulator; no referral or placement economics.",
    "investopedia": "Commercial publisher; advertising and affiliate relationships may apply.",
    "stockbrokers_com": "Commercial comparison publisher; referral economics may apply.",
    "nerdwallet": "Commercial comparison publisher with disclosed affiliate relationships.",
    "bankrate": "Commercial comparison publisher with disclosed affiliate relationships.",
    "forbes_advisor": "Commercial comparison publisher; advertising and affiliate relationships may apply.",
    "kiplinger": "Subscription and advertising-supported financial publisher.",
    "barrons": "Subscription and advertising-supported financial publisher.",
    "motley_fool_ascent": "Commercial publisher with affiliate-supported comparison content.",
    "reddit": "Community-generated and self-selected; no representative sampling.",
    "bogleheads": "Community-generated and self-selected; long-term index-investor skew.",
    "trustpilot": "Self-selected public reviews; the platform also sells business services.",
    "bbb": "Complaint-driven public record; the organization also offers business accreditation.",
    "sitejabber": "Self-selected public reviews; currently registered but not collected.",
    "apple_app_store": "Platform-hosted ratings; in-app prompts can inflate positive response rates.",
    "google_play": "Platform-hosted ratings; in-app prompts can inflate positive response rates.",
}

sys.path.insert(0, str(APP_ROOT))

from components import data  # noqa: E402
from components.charts import BROKER_COLORS, DIMENSION_SCORING_BASIS  # noqa: E402
from components.decision import PROFILE_PRESETS  # noqa: E402


def records(frame):
    """Return JSON-safe records while converting pandas nulls to JavaScript nulls."""
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def source_incentive(row) -> str:
    if row["slug"] in SOURCE_INCENTIVES:
        return SOURCE_INCENTIVES[row["slug"]]
    if row["source_type"] == "broker_official":
        return "Commercial self-interest; used only for independently checkable objective facts."
    return "Public source; incentive model has not been independently classified."


def payload() -> dict:
    brokers = data.brokers()
    dimensions = data.dimensions()
    personas = data.personas()
    facts = data.product_facts()
    current_facts = facts[facts["is_current"]].copy()
    evidence = data.q(
        """SELECT e.id, e.url, e.title, e.snippet, e.retrieval_date,
                  e.published_date, e.collection_method, e.confidence, e.raw_path,
                  e.unavailable, e.notes, s.slug AS source_slug,
                  s.name AS source_name, s.publisher, s.source_type,
                  b.slug AS broker_slug, b.name AS broker_name
           FROM evidence e
           JOIN sources s ON s.id = e.source_id
           LEFT JOIN brokers b ON b.id = e.broker_id
           ORDER BY e.id DESC"""
    )
    sources = data.q(
        """SELECT s.slug, s.name, s.publisher, s.source_type, s.base_url,
                  s.quality_weight, s.notes,
                  COUNT(e.id) AS evidence_count,
                  SUM(CASE WHEN e.unavailable = 0 THEN 1 ELSE 0 END) AS available_count,
                  SUM(CASE WHEN e.unavailable = 1 THEN 1 ELSE 0 END) AS unavailable_count,
                  MAX(e.retrieval_date) AS latest_retrieval
           FROM sources s LEFT JOIN evidence e ON e.source_id = s.id
           GROUP BY s.id ORDER BY s.source_type, s.name"""
    )
    sources = sources.copy()
    sources["incentive"] = sources.apply(source_incentive, axis=1)
    withdrawn = data.q(
        """SELECT er.rating_raw, er.rating_scale_max, er.review_cycle,
                  b.slug AS broker_slug, b.name AS broker_name,
                  s.slug AS source_slug, s.name AS source_name,
                  COALESCE(d.name, 'Overall rating') AS dim_name,
                  e.url, e.retrieval_date, e.notes, e.title
           FROM expert_ratings er
           JOIN evidence e ON e.id = er.evidence_id
           JOIN sources s ON s.id = er.source_id
           JOIN brokers b ON b.id = er.broker_id
           LEFT JOIN dimensions d ON d.id = er.dimension_id
           WHERE e.unavailable = 1
           ORDER BY s.name, b.name, dim_name"""
    )
    fact_changes = data.q(
        """SELECT fc.id, b.slug AS broker_slug, b.name AS broker_name,
                  fc.fact_key, fc.old_value_numeric, fc.new_value_numeric,
                  fc.old_value_text, fc.new_value_text, fc.source_as_of_date,
                  fc.detected_at, e.url, e.title
           FROM fact_changes fc JOIN brokers b ON b.id = fc.broker_id
           JOIN evidence e ON e.id = fc.evidence_id
           ORDER BY fc.detected_at DESC"""
    )
    verification_runs = data.q(
        """SELECT fvr.id, b.slug AS broker_slug, b.name AS broker_name,
                  fvr.fact_key, fvr.source_url, fvr.status,
                  fvr.observed_value_numeric, fvr.source_as_of_date,
                  fvr.detail, fvr.checked_at
           FROM fact_verification_runs fvr
           JOIN brokers b ON b.id = fvr.broker_id
           ORDER BY fvr.checked_at DESC, fvr.id DESC"""
    )
    pipeline_runs = data.q(
        """SELECT step, status, detail, started_at, finished_at
           FROM pipeline_runs ORDER BY id DESC"""
    )

    persona_weights = {
        row["slug"]: data.persona_weights(int(row["id"]))
        for _, row in personas.iterrows()
    }

    return {
        "generatedOn": date.today().isoformat(),
        "brokers": records(brokers[["slug", "name"]]),
        "dimensions": records(
            dimensions[["slug", "name", "description", "sort_order"]]
        ),
        "personas": records(personas[["slug", "name", "description", "sort_order"]]),
        "personaWeights": persona_weights,
        "profilePresets": PROFILE_PRESETS,
        "dimensionBasis": DIMENSION_SCORING_BASIS,
        "brokerColors": BROKER_COLORS,
        "dimensionScores": records(
            data.dimension_scores()[
                [
                    "broker_slug",
                    "broker_name",
                    "dim_slug",
                    "dim_name",
                    "dim_description",
                    "sort_order",
                    "score",
                    "confidence",
                    "evidence_count",
                    "fact_component",
                    "customer_component",
                    "expert_component",
                ]
            ]
        ),
        "momentum": records(data.momentum()[["broker_slug", "momentum"]]),
        "facts": records(
            current_facts[
                [
                    "broker_slug",
                    "broker_name",
                    "fact_key",
                    "value_text",
                    "value_numeric",
                    "unit",
                    "as_of_date",
                    "url",
                    "title",
                ]
            ]
        ),
        "factSummary": data.product_fact_freshness_summary(facts),
        "customerRankings": records(data.customer_voice_rankings()),
        "economicRankings": records(data.economic_value_rankings()),
        "reviewRatings": records(data.review_platform_ratings()),
        "sentiment": records(data.sentiment_comparison()),
        "evidence": records(evidence),
        "sources": records(sources),
        "withdrawnReviews": records(withdrawn),
        "factChanges": records(fact_changes),
        "verificationRuns": records(verification_runs),
        "pipelineRuns": records(pipeline_runs),
        "documents": {
            "methodology": (DOCS_ROOT / "methodology.md").read_text(encoding="utf-8"),
            "scoring": (DOCS_ROOT / "scoring_logic.md").read_text(encoding="utf-8"),
            "sources": (DOCS_ROOT / "sources.md").read_text(encoding="utf-8"),
            "limitations": (DOCS_ROOT / "limitations.md").read_text(encoding="utf-8"),
        },
        "executionQuality": {
            "available": False,
            "coverage": 0,
            "detail": (
                "No SEC Rule 605 or Rule 606 records are present in the current evidence "
                "ledger. Execution quality is intentionally not scored until official "
                "broker reports are collected and normalized."
            ),
        },
    }


def main() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    plotly_bundle = PLOTLY_BUNDLE.read_text(encoding="utf-8")
    dashboard_data = json.dumps(payload(), separators=(",", ":"), ensure_ascii=True)
    rendered = template.replace("/*__PLOTLY_BUNDLE__*/", plotly_bundle).replace(
        "/*__DASHBOARD_DATA__*/", dashboard_data
    )
    if "/*__PLOTLY_BUNDLE__*/" in rendered or "/*__DASHBOARD_DATA__*/" in rendered:
        raise RuntimeError("Standalone dashboard template placeholders were not replaced")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Created {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
