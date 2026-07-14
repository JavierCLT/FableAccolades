# 🧭 Best Broker Index

A personal, independent, **public-data-only** research and comparison tool for U.S.
brokerage platforms. Not another ranking site that gives everyone a trophy — a transparent,
evidence-backed comparison engine that shows:

- what expert reviewers claim,
- **where expert sources directly contradict each other** on the same broker and dimension,
- what objective product facts show (from brokers' own public pages),
- what **actual customers** experience (Reddit, Bogleheads, Trustpilot/BBB, app stores, and
  the official **CFPB Consumer Complaint Database**),
- which brokers fit six plain-language investor situations, with an industry benchmark mode.

**Tracked brokers (11):** Fidelity, Charles Schwab, Vanguard, Robinhood, Interactive
Brokers, E\*TRADE, Merrill Edge, SoFi Invest, Webull, Public, and J.P. Morgan
Self-Directed Investing.

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
| Dashboard | Winner-first Investor view with six presets; Industry view benchmarks one brokerage against the market |
| Fees & Products | Current cash, margin, fee, and product leaders; expired values are blank |
| Compare | Focused two- or three-broker radar, score, customer voice, and economics comparison |
| Audit trail | Sources, methodology, withdrawn reviews, and limitations remain available from the disclosure panel |

Everywhere a score or claim appears, **hovering it opens a proof card** with clickable
source links, retrieval dates, and confidence — credibility by mouseover.

## How scoring works (short version)

Each broker × dimension score (0–100) blends **objective facts (45%) / customer voice (35%)
/ expert consensus (20%)**, renormalized when a component is missing. Expert disagreement is
penalized (and displayed); expired score-critical facts are withheld from scoring; a separate **confidence score**
reflects evidence volume, source quality, recency, and corroboration. Persona scores are
weighted dimension averages plus a bounded CFPB complaint-momentum adjustment. Deterministic
end-to-end — the full spec is in [docs/scoring_logic.md](docs/scoring_logic.md) and pinned by
tests. An LLM is never required and never produces a score.

## Repository structure

```
backend/
  collectors/          # cfpb, reddit, expert_sites, broker_sites, structured volatile facts
  normalizers/         # rating normalization
  classifiers/         # deterministic sentiment + theme/dimension classifiers
  scoring/             # fact rules, confidence, contradictions, engine, constants
  database/            # schema.sql, db helpers, seed loader, seeds/*.json
  pipeline.py          # orchestrator: rebuild + collect + score
frontend/streamlit_app/
  app.py               # home: decision dashboard, radar, rankings, current facts
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

Per-broker page parsers for automated fact refresh; Playwright for 403-walled expert pages;
Postgres migration (schema is already portable); optional LLM theme extraction for Reddit at
scale; fee/yield change alerts and historical score tracking. Product & growth strategy:
[docs/strategy.md](docs/strategy.md).
