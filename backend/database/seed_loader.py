"""Load seed JSON files into the database, creating an evidence row for every data point.

Seed data is manually curated from public pages (collection_method='manual_curation').
Collectors overwrite/refresh these rows with live data where available (e.g. CFPB).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend import config
from backend.common import get_logger
from backend.database import db
from backend.normalizers.expert_ratings import normalize_rating

log = get_logger("seed_loader")


def _read_seed(name: str) -> dict[str, Any]:
    return json.loads((config.SEEDS_DIR / name).read_text(encoding="utf-8"))


def load_reference_tables(conn: sqlite3.Connection) -> None:
    for b in _read_seed("brokers.json")["brokers"]:
        db.upsert(conn, "brokers", b, ["slug"])
    for d in _read_seed("dimensions.json")["dimensions"]:
        db.upsert(conn, "dimensions", d, ["slug"])
    for s in _read_seed("sources.json")["sources"]:
        db.upsert(conn, "sources", s, ["slug"])

    personas = _read_seed("personas.json")["personas"]
    for p in personas:
        weights = p.pop("weights")
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Persona {p['slug']} weights sum to {total}, expected 1.0")
        db.upsert(conn, "personas", p, ["slug"])
        pid = db.lookup_id(conn, "personas", p["slug"])
        for dim_slug, w in weights.items():
            did = db.lookup_id(conn, "dimensions", dim_slug)
            db.upsert(
                conn,
                "persona_weights",
                {"persona_id": pid, "dimension_id": did, "weight": w},
                ["persona_id", "dimension_id"],
            )
    conn.commit()
    log.info("Reference tables loaded (brokers, dimensions, sources, personas)")


def load_product_facts(conn: sqlite3.Connection) -> None:
    seed = _read_seed("product_facts.json")
    defaults = seed["defaults"]
    n = 0
    for f in seed["facts"]:
        broker_id = db.lookup_id(conn, "brokers", f["broker"])
        dim_id = db.lookup_id(conn, "dimensions", f["dimension"])
        source_id = db.lookup_id(conn, "sources", f"broker_{f['broker']}")
        ev_id = db.add_evidence(
            conn,
            source_id=source_id,
            broker_id=broker_id,
            url=f["url"],
            title=f.get("title"),
            snippet=f.get("snippet"),
            retrieval_date=defaults["retrieval_date"],
            collection_method=defaults["collection_method"],
            confidence=f.get("confidence", "medium"),
            notes=f.get("notes"),
        )
        db.upsert(
            conn,
            "product_facts",
            {
                "broker_id": broker_id,
                "dimension_id": dim_id,
                "fact_key": f["key"],
                "value_text": f.get("value_text"),
                "value_numeric": f.get("value_numeric"),
                "unit": f.get("unit"),
                "as_of_date": f["as_of"],
                "evidence_id": ev_id,
            },
            ["broker_id", "fact_key"],
        )
        n += 1
    conn.commit()
    log.info("Loaded %d product facts", n)


def load_expert_reviews(conn: sqlite3.Connection) -> None:
    seed = _read_seed("expert_reviews.json")
    d = seed["defaults"]
    n = 0
    for block in seed["blocks"]:
        source_id = db.lookup_id(conn, "sources", block["source"])
        dim_id = db.lookup_id(conn, "dimensions", block["dimension"]) if block.get("dimension") else None
        scale = block.get("scale_max", d["scale_max"])
        for broker_slug, rating in block["ratings"].items():
            broker_id = db.lookup_id(conn, "brokers", broker_slug)
            ev_id = db.add_evidence(
                conn,
                source_id=source_id,
                broker_id=broker_id,
                url=block["urls"][broker_slug],
                title=block.get("title"),
                snippet=f"Published rating: {rating} / {scale}"
                + (f" for {block['dimension']}" if block.get("dimension") else " (overall)"),
                retrieval_date=d["retrieval_date"],
                collection_method=d["collection_method"],
                confidence=block.get("confidence", "medium"),
            )
            db.upsert(
                conn,
                "expert_ratings",
                {
                    "broker_id": broker_id,
                    "source_id": source_id,
                    "dimension_id": dim_id,
                    "rating_raw": rating,
                    "rating_scale_max": scale,
                    "rating_normalized": normalize_rating(rating, scale),
                    "review_cycle": block.get("review_cycle", d["review_cycle"]),
                    "evidence_id": ev_id,
                },
                ["broker_id", "source_id", "dimension_id", "review_cycle"],
            )
            n += 1
    conn.commit()
    log.info("Loaded %d expert ratings", n)


def load_accolades(conn: sqlite3.Connection) -> None:
    seed = _read_seed("accolades.json")
    d = seed["defaults"]
    conn.execute("DELETE FROM accolades")  # idempotent reload (no natural key)
    n = 0
    for a in seed["accolades"]:
        broker_id = db.lookup_id(conn, "brokers", a["broker"])
        source_id = db.lookup_id(conn, "sources", a["source"])
        ev_id = db.add_evidence(
            conn,
            source_id=source_id,
            broker_id=broker_id,
            url=a["url"],
            title=a.get("title"),
            snippet=a.get("snippet"),
            retrieval_date=d["retrieval_date"],
            collection_method=d["collection_method"],
            confidence=a.get("confidence", d["confidence"]),
        )
        db.insert(
            conn,
            "accolades",
            {
                "broker_id": broker_id,
                "source_id": source_id,
                "award_title": a["award_title"],
                "category": a.get("category"),
                "year": a.get("year"),
                "rank": a.get("rank"),
                "evidence_id": ev_id,
            },
        )
        n += 1
    conn.commit()
    log.info("Loaded %d accolades", n)


def load_customer_voice(conn: sqlite3.Connection) -> None:
    seed = _read_seed("customer_voice.json")
    d = seed["defaults"]
    conn.execute("DELETE FROM customer_voice")  # idempotent reload
    n = 0
    for t in seed["themes"]:
        broker_id = db.lookup_id(conn, "brokers", t["broker"])
        source_id = db.lookup_id(conn, "sources", t["source"])
        dim_id = db.lookup_id(conn, "dimensions", t["dimension"])
        ev_id = db.add_evidence(
            conn,
            source_id=source_id,
            broker_id=broker_id,
            url=t["url"],
            title=t.get("title") or f"{t['source']} — {t['theme']}",
            snippet=t.get("snippet"),
            retrieval_date=d["retrieval_date"],
            collection_method=d["collection_method"],
            confidence=t.get("confidence", d["confidence"]),
            notes=t.get("notes"),
        )
        db.insert(
            conn,
            "customer_voice",
            {
                "broker_id": broker_id,
                "source_id": source_id,
                "dimension_id": dim_id,
                "kind": t["kind"],
                "sentiment": t["sentiment"],
                "theme": t["theme"],
                "volume": t.get("volume", 1),
                "severity": t.get("severity", 2),
                "snippet": t.get("snippet"),
                "observed_date": t.get("observed_date"),
                "evidence_id": ev_id,
            },
        )
        n += 1
    conn.commit()
    log.info("Loaded %d customer voice themes", n)


def load_aggregate_ratings(conn: sqlite3.Connection) -> None:
    seed = _read_seed("aggregate_ratings.json")
    d = seed["defaults"]
    n = 0
    for r in seed["ratings"]:
        broker_id = db.lookup_id(conn, "brokers", r["broker"])
        source_id = db.lookup_id(conn, "sources", r["source"])
        ev_id = db.add_evidence(
            conn,
            source_id=source_id,
            broker_id=broker_id,
            url=r["url"],
            title=r.get("title"),
            snippet=f"Aggregate rating {r['rating']} / {r.get('scale_max', d['scale_max'])} "
            f"(~{r.get('review_count', '?')} reviews)",
            retrieval_date=d["retrieval_date"],
            collection_method=d["collection_method"],
            confidence=r.get("confidence", d["confidence"]),
            notes=r.get("notes"),
        )
        db.upsert(
            conn,
            "aggregate_ratings",
            {
                "broker_id": broker_id,
                "source_id": source_id,
                "rating_raw": r["rating"],
                "rating_scale_max": r.get("scale_max", d["scale_max"]),
                "review_count": r.get("review_count"),
                "as_of_date": r.get("as_of", d["as_of"]),
                "evidence_id": ev_id,
            },
            ["broker_id", "source_id"],
        )
        n += 1
    conn.commit()
    log.info("Loaded %d aggregate ratings", n)


def load_all(conn: sqlite3.Connection) -> None:
    load_reference_tables(conn)
    load_product_facts(conn)
    load_expert_reviews(conn)
    load_accolades(conn)
    load_customer_voice(conn)
    load_aggregate_ratings(conn)
