"""Reddit collector using PRAW (official API).

Requires credentials via environment variables:
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and optionally REDDIT_USER_AGENT.

When credentials are configured, this collector pulls recent top threads from the
configured subreddits, attributes them to brokers by name matching, classifies
sentiment (lexicon-based, deterministic) and dimension (keyword-based), and refreshes
`customer_voice` rows with collection_method='api'. Every inserted theme links to
evidence carrying the thread permalink and a title snippet.

Without credentials, the collector is a clean no-op: the curated seed themes remain,
and the skip is logged in pipeline_runs so the dashboard can show honest data-age.
"""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from backend.classifiers.sentiment import label_text, score_text
from backend.classifiers.themes import classify_dimension
from backend.collectors.base import BaseCollector
from backend.common import save_raw, today_iso
from backend.database import db

SUBREDDITS = [
    "Bogleheads", "investing", "personalfinance",
    "fidelityinvestments", "Schwab", "RobinHood", "interactivebrokers", "etrade", "Vanguard",
]

BROKER_PATTERNS: dict[str, list[str]] = {
    "fidelity": ["fidelity"],
    "schwab": ["schwab"],
    "vanguard": ["vanguard"],
    "robinhood": ["robinhood", " rh "],
    "ibkr": ["interactive brokers", "ibkr"],
    "etrade": ["etrade", "e*trade", "e-trade"],
}

THREADS_PER_SUBREDDIT = 50
MIN_THREADS_PER_THEME = 2


class RedditCollector(BaseCollector):
    name = "reddit"

    def collect(self, conn: sqlite3.Connection) -> str:
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        if not client_id or not client_secret:
            return (
                "skipped: no REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET configured — "
                "curated seed themes remain in place"
            )

        import praw  # imported lazily so the pipeline runs without praw installed

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=os.environ.get("REDDIT_USER_AGENT", "BestBrokerIndex/0.1 research"),
        )
        reddit.read_only = True
        source_id = db.lookup_id(conn, "sources", "reddit")

        # theme buckets: (broker, dimension, sentiment) -> list of thread dicts
        buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        raw_threads = []
        for sub in SUBREDDITS:
            try:
                for post in reddit.subreddit(sub).top(time_filter="month", limit=THREADS_PER_SUBREDDIT):
                    text = f"{post.title}\n{getattr(post, 'selftext', '') or ''}"
                    lowered = text.lower()
                    matched = [
                        b for b, pats in BROKER_PATTERNS.items()
                        if any(p in lowered for p in pats)
                    ]
                    if len(matched) != 1:
                        continue  # skip multi-broker or non-broker threads: attribution ambiguous
                    dim = classify_dimension(text)
                    if dim is None:
                        continue
                    sentiment = label_text(text)
                    thread = {
                        "broker": matched[0], "dimension": dim, "sentiment": sentiment,
                        "score": score_text(text), "title": post.title,
                        "permalink": f"https://www.reddit.com{post.permalink}",
                        "subreddit": sub, "ups": int(post.score),
                        "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).date().isoformat(),
                    }
                    raw_threads.append(thread)
                    buckets[(matched[0], dim, sentiment)].append(thread)
            except Exception as exc:  # noqa: BLE001 — isolate per-subreddit failures
                self.log.warning("subreddit %s failed: %s", sub, exc)

        raw_path = save_raw("reddit", "classified_threads", raw_threads)

        inserted = 0
        for (broker_slug, dim_slug, sentiment), threads in buckets.items():
            if len(threads) < MIN_THREADS_PER_THEME:
                continue  # require corroboration before recording a theme
            broker_id = db.lookup_id(conn, "brokers", broker_slug)
            dim_id = db.lookup_id(conn, "dimensions", dim_slug)
            top = max(threads, key=lambda t: t["ups"])
            kind = {"positive": "praise", "negative": "complaint", "mixed": "opinion"}[sentiment]
            severity = 3 if sentiment == "negative" else 2 if sentiment == "mixed" else 1
            ev_id = db.add_evidence(
                conn,
                source_id=source_id,
                broker_id=broker_id,
                url=top["permalink"],
                title=f"Reddit threads ({len(threads)}) — r/{top['subreddit']} and others",
                snippet=f"Representative thread: \"{top['title'][:200]}\"",
                retrieval_date=today_iso(),
                collection_method="api",
                confidence="medium",
                raw_path=str(raw_path),
            )
            # Replace any previous live-collected theme for this cell; keep curated seeds
            # (they use manual_curation evidence) distinguishable by collection method.
            db.insert(
                conn,
                "customer_voice",
                {
                    "broker_id": broker_id,
                    "source_id": source_id,
                    "dimension_id": dim_id,
                    "kind": kind,
                    "sentiment": sentiment,
                    "theme": f"Recent Reddit {kind}s about {dim_slug.replace('_', ' ')}",
                    "volume": len(threads),
                    "severity": severity,
                    "snippet": top["title"][:300],
                    "observed_date": max(t["created_utc"] for t in threads),
                    "evidence_id": ev_id,
                },
            )
            inserted += 1

        conn.commit()
        return f"classified {len(raw_threads)} threads into {inserted} themes"
