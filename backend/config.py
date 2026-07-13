"""Central configuration: paths, constants, and HTTP etiquette settings."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EVIDENCE_DIR = DATA_DIR / "evidence"
LOG_DIR = REPO_ROOT / "logs"

DB_PATH = Path(os.environ.get("BBI_DB_PATH", PROCESSED_DIR / "broker_index.db"))

SEEDS_DIR = REPO_ROOT / "backend" / "database" / "seeds"
SCHEMA_PATH = REPO_ROOT / "backend" / "database" / "schema.sql"

# HTTP etiquette: identify ourselves honestly and rate-limit every source.
USER_AGENT = os.environ.get(
    "BBI_USER_AGENT",
    "BestBrokerIndex/0.1 (independent public-data research; +https://github.com/)",
)
REQUEST_TIMEOUT_SECONDS = 60
MIN_SECONDS_BETWEEN_REQUESTS = 2.0

# CFPB complaint window used for stats (trailing months).
CFPB_LOOKBACK_MONTHS = 36

for _d in (RAW_DIR, PROCESSED_DIR, EVIDENCE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)
