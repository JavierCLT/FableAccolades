# Data Sources

All sources are public. Quality weights (0–1) feed confidence scoring and are listed in
`backend/database/seeds/sources.json`.

## Regulator / official data

| Source | Access | Notes |
|---|---|---|
| CFPB Consumer Complaint Database | **Official public API** (no key), JSON export, trailing 36 months | Company entities verified via the API's company-suggest endpoint: Robinhood (`ROBINHOOD MARKETS INC.`), Schwab (`CHARLES SCHWAB CORPORATION, THE`), E*TRADE (`E*TRADE BANK`). Fidelity, Vanguard, and IBKR have **no CFPB entity** — recorded explicitly as a coverage gap. |

## Broker official pages (objective facts)

Pricing pages, fee schedules, cash/sweep pages, and feature pages for Fidelity, Charles
Schwab, Vanguard, Robinhood, Interactive Brokers, and E*TRADE. Facts are curated from these
pages with URLs and as-of dates; the `broker_sites` collector archives timestamped page
snapshots under `data/raw/broker_sites/` for auditability. Marketing claims are excluded —
only checkable product facts are recorded.

## Expert review publishers

Investopedia, StockBrokers.com, NerdWallet, Bankrate, Forbes Advisor, Kiplinger, Barron's
(publicly visible results only — most content is paywalled), The Motley Fool Money/Ascent.

The `expert_sites` collector re-fetches cited review pages (robots.txt-respecting,
rate-limited, honest user-agent) and verifies published overall ratings via JSON-LD/regex
extraction where pages allow it. Several publishers block automated clients; their ratings
remain curated values with visible retrieval dates until re-verified. For stubborn
JS-rendered pages, Playwright can be enabled selectively (`pip install playwright &&
playwright install chromium`) — kept out of the default path deliberately.

## Customer voice

| Source | Access | Notes |
|---|---|---|
| Reddit | **PRAW (official API)** when `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` are set; curated high-signal thread themes otherwise | Subreddits: r/Bogleheads, r/investing, r/personalfinance, r/fidelityinvestments, r/Schwab, r/RobinHood, r/interactivebrokers, r/etrade, r/Vanguard |
| Bogleheads.org forum | Curated thread themes | Skews long-term index investors |
| Trustpilot / BBB | Aggregate scores + complaint themes, curated with as-of dates | Self-selected, skews negative for all large brokers |
| Apple App Store / Google Play | Aggregate ratings + review counts | Very large samples; prompt-inflated |
| Sitejabber | Registered as a source; **not yet collected** (low volume for brokers) | Marked unavailable rather than estimated |

## Update cadence

GitHub Actions (`.github/workflows/update_data.yml`) runs the pipeline on a schedule:
CFPB and expert-page verification refresh with each run; volatile facts (yields, margin
rates) are flagged for manual re-curation when the staleness penalty engages. Raw payloads
are versioned by timestamp under `data/raw/`.
