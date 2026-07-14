"""Shared utilities: logging, polite HTTP client with rate limiting and robots.txt checks,
and raw-data versioning helpers."""

from __future__ import annotations

import json
import logging
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from backend import config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(config.LOG_DIR / "pipeline.log")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class PoliteSession:
    """HTTP session that enforces a per-host minimum delay and respects robots.txt."""

    def __init__(self, min_delay: float = config.MIN_SECONDS_BETWEEN_REQUESTS):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self.min_delay = min_delay
        self._last_request_at: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.log = get_logger("http")

    def _robots_allows(self, url: str) -> bool:
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.set_url(f"https://{host}/robots.txt")
                rp.read()
            except Exception:
                # If robots.txt is unreachable, be conservative but do not hard-fail.
                rp = None  # type: ignore[assignment]
            self._robots[host] = rp
        rp = self._robots[host]
        if rp is None:
            return True
        try:
            return rp.can_fetch(config.USER_AGENT, url)
        except Exception:
            return True

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host, 0.0)
        wait = self.min_delay - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at[host] = time.monotonic()

    def get(self, url: str, *, check_robots: bool = True, **kwargs: Any) -> requests.Response:
        if check_robots and not self._robots_allows(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        self._throttle(url)
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT_SECONDS)
        resp = self.session.get(url, **kwargs)
        self.log.info("GET %s -> %s (%s bytes)", url, resp.status_code, len(resp.content))
        return resp


def save_raw(source_slug: str, name: str, payload: Any) -> Path:
    """Version raw payloads under data/raw/<source>/<UTC timestamp>__<name>.json."""
    out_dir = config.RAW_DIR / source_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{stamp}__{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, default=str)
    return path


def save_raw_bytes(source_slug: str, name: str, payload: bytes, suffix: str) -> Path:
    """Version a binary source document under data/raw with its original extension."""
    out_dir = config.RAW_DIR / source_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    clean_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    path = out_dir / f"{stamp}__{name}{clean_suffix}"
    path.write_bytes(payload)
    return path
