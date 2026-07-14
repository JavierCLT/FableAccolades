# Data Sources

All sources are public. Quality weights (0–1) feed confidence scoring and are listed in
`backend/database/seeds/sources.json`.

## Regulator / official data

| Source | Access | Notes |
|---|---|---|
| CFPB Consumer Complaint Database | **Official public API** (no key), JSON export, trailing 36 months | Company entities verified via the API's company-suggest endpoint: Robinhood (`ROBINHOOD MARKETS INC.`), Schwab (`CHARLES SCHWAB CORPORATION, THE`), E*TRADE (`E*TRADE BANK`), SoFi (`SOFI TECHNOLOGIES, INC.`, attribution caveat: spans lending/banking), Webull (`WEBULL PAY HOLDINGS (US) INC`, attribution caveat: payments affiliate). Fidelity, Vanguard, IBKR, and Public have **no CFPB entity** — recorded explicitly as a coverage gap. Merrill (Bank of America) and J.P. Morgan Self-Directed (JPMorgan Chase) are **deliberately excluded**: their parents' complaint streams are dominated by unrelated business lines and cannot be fairly attributed to the brokerage product. Attribution-caveat entities are shown for context but never move friction/momentum scores. |

## Broker official pages (objective facts)

Pricing pages, fee schedules, cash/sweep pages, and feature pages for the eleven tracked
brokers. Facts carry URLs and source as-of dates. Structured adapters parse supported
official documents (currently including Merrill's published cash-rate sheet), record every
verification and detected value change, and archive the original payload. The `broker_sites`
collector also archives timestamped page snapshots under `data/raw/broker_sites/` for
auditability. Marketing claims are excluded — only checkable product facts are recorded.

## Expert review publishers

Investopedia, StockBrokers.com, NerdWallet, Bankrate, Forbes Advisor, Kiplinger, Barron's
(publicly visible results only — most content is paywalled), The Motley Fool Money/Ascent.

The `expert_sites` collector re-fetches every cited review page (robots.txt-respecting,
rate-limited, honest user-agent) and classifies each stored claim:

- **verified** — rating machine-extracted from the live page (JSON-LD/regex); confirmed or
  corrected, evidence upgraded to high confidence with a fresh retrieval date.
- **unverified** — page live but the rating is not machine-extractable, or the publisher
  blocks automated clients; the curated value is retained at **low confidence** with an
  explicit note, reducing its scoring weight.
- **no longer published** — the URL is dead or the page no longer mentions the broker
  (publishers add/drop coverage and change ratings without notice); the evidence is marked
  unavailable and the claim is **excluded from scoring and contradiction detection**,
  remaining visible in the Evidence Viewer as a historical record.

A score never rests on a URL that no longer backs it. For stubborn JS-rendered pages,
Playwright can be enabled selectively (`pip install playwright && playwright install
chromium`) — kept out of the default path deliberately.

## Customer voice

| Source | Access | Notes |
|---|---|---|
| Reddit | **PRAW (official API)** when `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` are set; curated high-signal thread themes otherwise | Subreddits: r/Bogleheads, r/investing, r/personalfinance, r/fidelityinvestments, r/Schwab, r/RobinHood, r/interactivebrokers, r/etrade, r/Vanguard |
| Bogleheads.org forum | Curated thread themes | Skews long-term index investors |
| Trustpilot / BBB | Aggregate scores + complaint themes, curated with as-of dates | Self-selected, skews negative for all large brokers |
| Apple App Store / Google Play | Aggregate ratings + review counts | Very large samples; prompt-inflated |
| Sitejabber | Registered as a source; **not yet collected** (low volume for brokers) | Marked unavailable rather than estimated |

## Update cadence

GitHub Actions (`.github/workflows/update_data.yml`) runs the pipeline daily. CFPB,
expert-page verification, structured fact adapters, and source archiving run on each pass.
The build then enforces at least 95% current product-fact coverage and zero expired
score-critical facts. A failed freshness gate is visible in CI, while the database and raw
artifacts are still uploaded for diagnosis. Raw payloads are versioned under `data/raw/`.
