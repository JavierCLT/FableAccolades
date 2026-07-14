"""Pipeline orchestrator.

Usage:
    python -m backend.pipeline                # rebuild DB from seeds + run collectors + score
    python -m backend.pipeline --no-collect   # seeds + scoring only (offline mode)
    python -m backend.pipeline --keep-db      # don't delete the existing DB first

The default is a full from-scratch rebuild so every run is reproducible: schema, seeds,
live collectors (each isolated — one failure never blocks the rest), then scoring.
"""

from __future__ import annotations

import argparse

from backend import config
from backend.common import get_logger, utc_now_iso
from backend.database import db, seed_loader
from backend.scoring import engine

log = get_logger("pipeline")


def run(collect: bool = True, keep_db: bool = False) -> None:
    if not keep_db and config.DB_PATH.exists():
        config.DB_PATH.unlink()
        log.info("Removed existing database for a clean rebuild")

    conn = db.connect()
    db.init_schema(conn)
    started = utc_now_iso()
    seed_loader.load_all(conn)
    db.insert(conn, "pipeline_runs", {"step": "seed", "status": "success",
                                      "detail": "seed data loaded", "started_at": started,
                                      "finished_at": utc_now_iso()})
    conn.commit()

    if collect:
        from backend.collectors.broker_sites.collector import BrokerSitesCollector
        from backend.collectors.cfpb.collector import CfpbCollector
        from backend.collectors.expert_sites.collector import ExpertSitesCollector
        from backend.collectors.reddit.collector import RedditCollector
        from backend.collectors.volatile_facts.collector import VolatileFactsCollector

        for collector_cls in (
            CfpbCollector,
            RedditCollector,
            ExpertSitesCollector,
            VolatileFactsCollector,
            BrokerSitesCollector,
        ):
            collector_cls().run(conn)

    started = utc_now_iso()
    engine.compute_all(conn)
    db.insert(conn, "pipeline_runs", {"step": "score", "status": "success",
                                      "detail": "scores recomputed", "started_at": started,
                                      "finished_at": utc_now_iso()})
    conn.commit()
    conn.close()
    log.info("Pipeline finished. Database at %s", config.DB_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Best Broker Index data pipeline")
    parser.add_argument("--no-collect", action="store_true", help="skip live collectors (offline)")
    parser.add_argument("--keep-db", action="store_true", help="do not delete the existing DB first")
    args = parser.parse_args()
    run(collect=not args.no_collect, keep_db=args.keep_db)
