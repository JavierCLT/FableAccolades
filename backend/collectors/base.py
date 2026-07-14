"""Base collector with per-source error isolation and run logging."""

from __future__ import annotations

import sqlite3
import traceback

from backend.common import PoliteSession, get_logger, utc_now_iso
from backend.database import db


class BaseCollector:
    """Subclasses implement `collect(conn)`. `run(conn)` isolates failures per source:
    one broken source never blocks the rest of the pipeline, and every run is recorded
    in `pipeline_runs` for freshness display in the dashboard."""

    name: str = "base"

    def __init__(self) -> None:
        self.log = get_logger(f"collector.{self.name}")
        self.http = PoliteSession()

    def collect(self, conn: sqlite3.Connection) -> str:
        """Do the work; return a short human-readable detail string."""
        raise NotImplementedError

    def run(self, conn: sqlite3.Connection) -> bool:
        started = utc_now_iso()
        try:
            detail = self.collect(conn)
            status = "success"
        except Exception as exc:  # noqa: BLE001 — deliberate isolation boundary
            detail = f"{type(exc).__name__}: {exc}"
            status = "failed"
            self.log.error("Collector %s failed: %s\n%s", self.name, exc, traceback.format_exc())
        db.insert(
            conn,
            "pipeline_runs",
            {
                "step": f"collect:{self.name}",
                "status": status,
                "detail": detail,
                "started_at": started,
                "finished_at": utc_now_iso(),
            },
        )
        conn.commit()
        self.log.info("Collector %s finished: %s (%s)", self.name, status, detail)
        return status == "success"
