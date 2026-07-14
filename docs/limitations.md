# Limitations & Disclosures

**Read this before acting on anything in this tool.**

## Not financial advice

This is a personal, independent research project. Nothing here is investment, legal, or tax
advice, and nothing here is a recommendation to open, close, or transfer any account.
Individual needs vary widely — **rankings are starting points for your own research, not
conclusions.**

## Only public data is used

Every input comes from public web pages, public APIs, and public communities. There are no
broker data feeds, no partnerships, no paid placements, no affiliate links, and no
non-public information. The same methodology is applied to every broker with zero
preferential logic.

## Scores are estimates, bounded by their evidence

- Scores reflect the evidence **available at collection time**. Each data point carries a
  retrieval date and an as-of date. Expired score-critical values are withheld from the
  dashboard and removed from score inputs rather than silently trusted. **Always verify
  current terms on the linked source page before making decisions.**
- Some seed data was **manually curated from public pages** (marked as such in the Evidence
  Viewer, with lower confidence grades where warranted). Collectors re-verify what they can
  (CFPB via official API; expert ratings via live page checks). Every expert claim carries a
  verification status: live-verified claims are upgraded; claims the publisher blocks or
  renders client-side are kept as clearly labeled *unverified* values at reduced weight; and
  claims whose pages are gone or no longer mention the broker are marked unavailable and
  **excluded from scoring** — publishers change and silently withdraw reviews, and a dead
  URL is treated as a dead claim, not as evidence.
- A separate **confidence score** quantifies evidence volume, quality, recency, and
  corroboration. Treat low-confidence scores as weakly supported.

## Known biases in the sources

- **Customer reviews are self-selected and skew negative.** People with problems review;
  satisfied customers rarely do. Every large broker scores poorly on Trustpilot — levels are
  comparable *between* brokers but not interpretable as absolute satisfaction. App-store
  ratings skew the other way (in-app prompts after positive moments).
- **Expert reviews may contain undisclosed or disclosed affiliate relationships.** Most
  tracked publishers earn commissions when readers open accounts. This is one reason expert
  consensus receives the lowest weight and disagreement is penalized and surfaced.
- **CFPB coverage is uneven by business model.** The CFPB database covers consumer *banking*
  products; classic brokerage disputes go to FINRA/SEC (not public in comparable form).
  Brokers with banking arms (Robinhood, Schwab, E*TRADE Bank) appear; Fidelity, Vanguard,
  and Interactive Brokers have no CFPB entity. **Absence is a coverage gap, not a clean
  record**, and is displayed as such. Complaint volumes also scale with customer counts;
  scoring normalizes by disclosed client assets, an imperfect denominator.
- **Conglomerate attribution.** Merrill Edge (Bank of America) and J.P. Morgan
  Self-Directed (JPMorgan Chase) sit inside parents whose CFPB
  complaint streams are dominated by unrelated business lines (auto loans, credit cards,
  retail banking) — those entities are deliberately excluded rather than unfairly counted.
  SoFi's and Webull's entities are shown with an explicit attribution caveat and never move
  scores. Similarly, some aggregate app/review ratings for bank-owned brokers cover the
  whole banking app, not just investing — flagged in the evidence notes.
- **Reddit/forum themes are directional, not statistical.** Volumes are approximate mention
  counts from curated or API-collected threads, not a survey. Communities differ in
  composition (e.g. Bogleheads skews toward long-term index investors).

## Freshness and completeness

- The home-page coverage KPI and Product Fact Ledger show the current/withheld split. A
  daily pipeline records each structured verification, archives the source payload, and
  fails its freshness gate when current coverage falls below 95% or any score-critical fact
  is expired. Several expert
  sites block automated verification (HTTP 403); those ratings rely on curated values until
  re-verified.
- Phase 1 tracks eleven brokers and sixteen dimensions. Anything not measured (e.g. options
  execution quality, HSA offerings) is simply out of scope — absence of a dimension is not a
  judgment.
- AUM/size figures are approximate public figures used only for context and complaint-rate
  normalization. Morgan Stanley does not disclose standalone E*TRADE client assets; that is
  recorded as unavailable, and E*TRADE receives no complaint-rate score rather than a
  guessed one.

## Methodology limits

- Deterministic rules encode judgment calls (e.g. how much a $100 ACAT fee should cost a
  score). All ladders are published in [scoring_logic.md](scoring_logic.md) — if you would
  weigh things differently, the persona sliders let you, and the code is open.
- Contradiction detection compares publishers' *published numbers*; publishers use different
  rubrics and review dates, which explains some disagreement. That context is preserved via
  links to both sources.
- Cost Lab relationship benefits depend on card approval, program enrollment, qualifying
  balances, eligible purchases, redemption behavior, and continued program terms. The
  calculator shows conditional estimates, not guaranteed savings, and does not model credit
  card interest. Carrying a balance can overwhelm any rewards value.
