# 🧭 Best Broker Index

A personal, independent, **public-data-only** research and comparison tool for U.S.
brokerage platforms. Not another ranking site that gives everyone a trophy — a transparent,
evidence-backed comparison engine that shows:

- what expert reviewers claim,
- **where expert sources directly contradict each other** on the same broker and dimension,
- what objective product facts show (from brokers' own public pages),
- what **actual customers** experience (Reddit, Bogleheads, Trustpilot/BBB, app stores, and
  the official **CFPB Consumer Complaint Database**),
- which brokers fit different investor personas — with user-adjustable weights.

**Phase 1 brokers:** Fidelity, Charles Schwab, Vanguard, Robinhood, Interactive Brokers,
E\*TRADE.

> ⚖️ **Not financial advice.** Scores are evidence-based estimates from public data at
> collection time. See [docs/limitations.md](docs/limitations.md).

## Quick start

```bash
# 1. Install (Python 3.11+)
pip install -r requirements.txt

# 2. Build the database
python -m backend.pipeline                # seeds + live collectors (CFPB API, page checks) + scoring
#   or, fully offline:
python -m backend.pipeline --no-collect   # seeds + scoring only

# 3. Launch the dashboard
streamlit run frontend/streamlit_app/app.py
```

Optional environment variables:

| Variable | Purpose |
|---|---|
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Enables live Reddit collection via PRAW (otherwise curated seed themes are used and the skip is logged) |
| `REDDIT_USER_AGENT` | Custom PRAW user agent |
| `BBI_DB_PATH` | Alternate SQLite path |

Run the tests:

```bash
python -m pytest tests/ -q
```

## What's in the dashboard

| Page | What it does |
|---|---|
| 🏆 Rankings by Persona | 9 personas, weighted scores + confidence + evidence counts, live weight sliders |
| ⚔️ Contradiction Matrix | Heatmap + detail of expert-vs-expert disagreements (15+ point gaps), each with both sides' evidence; plus the biggest expert-vs-customer gaps |
| 📋 Product Facts | Side-by-side objective facts with as-of dates and staleness flags |
| 🗣️ Customer Voice | Per-broker sentiment, complaint/praise themes with volume & severity, CFPB complaint stats by product/issue, aggregate ratings |
| 🏅 Accolade Tracker | Public awards by publisher/category/year (context only — not score inputs) |
| 📈 Compare Brokers | 2–4 broker side-by-side with radar chart, per-dimension zoom, fact table |
| 🔎 Filters | Hard screens (no ACAT fee, cash yield ≥ X, mobile rating, crypto, IRA match, …) with exclusion reasons |
| 🔍 Evidence Viewer | The full evidence ledger: URL, publisher, retrieval date, snippet, method, confidence — every claim traces here |
| 📖 Methodology / ⚠️ Limitations | Full scoring spec and honest disclosure of biases and gaps |

## How scoring works (short version)

Each broker × dimension score (0–100) blends **objective facts (45%) / customer voice (35%)
/ expert consensus (20%)**, renormalized when a component is missing. Expert disagreement is
penalized (and displayed); stale volatile data is penalized; a separate **confidence score**
reflects evidence volume, source quality, recency, and corroboration. Persona scores are
weighted dimension averages plus a bounded CFPB complaint-momentum adjustment. Deterministic
end-to-end — the full spec is in [docs/scoring_logic.md](docs/scoring_logic.md) and pinned by
tests. An LLM is never required and never produces a score.

## Repository structure

```
backend/
  collectors/          # cfpb (official API), reddit (PRAW), expert_sites, broker_sites
  normalizers/         # rating normalization
  classifiers/         # deterministic sentiment + theme/dimension classifiers
  scoring/             # fact rules, confidence, contradictions, engine, constants
  database/            # schema.sql, db helpers, seed loader, seeds/*.json
  pipeline.py          # orchestrator: rebuild + collect + score
frontend/streamlit_app/
  app.py               # home: positioning, broker cards, data freshness
  components/          # data access, evidence viewer widget, charts, layout
  pages/               # the 10 dashboard pages
data/
  raw/                 # timestamped raw payloads (versioned, gitignored)
  processed/           # broker_index.db (gitignored; rebuild with the pipeline)
  evidence/            # reserved for larger evidence artifacts
docs/                  # methodology, scoring_logic, limitations, sources
tests/                 # scoring, confidence, contradictions, integration
.github/workflows/     # scheduled data updates
```

## Independence & compliance rules

Only publicly available information; identical methodology for every broker (no broker
names appear in scoring code); every data point stores source URL, title, publisher,
retrieval date, and snippet; unavailable sources are marked, never estimated; no broker
data feeds, partnerships, affiliate links, or paid placements.

## Roadmap (post-MVP)

Merrill Edge, SoFi Invest, Webull, Ally Invest, J.P. Morgan Self-Directed; per-broker page
parsers for automated fact refresh; Playwright for 403-walled expert pages; Postgres
migration (schema is already portable); optional LLM theme extraction for Reddit at scale.
