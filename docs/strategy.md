# Product & Growth Strategy — Becoming the Industry Standard

Goal: make Best Broker Index the default place investors check before choosing (or leaving)
a broker — and eventually monetize it — **without destroying the one asset that makes it
valuable: verifiable neutrality.**

## 1. The strategic insight

The broker-review market is large, rich, and structurally broken. Every major "best broker"
site is paid by the brokers it ranks (affiliate commissions of $100–$200+ per funded
account). Users increasingly know this — r/personalfinance and Bogleheads threads routinely
dismiss NerdWallet-style roundups. Nobody in the market can credibly say:

> "Here is the evidence. Here is where the paid reviewers contradict each other.
> Here is what actual customers say. We take no broker money."

That position is defensible *because incumbents cannot copy it without destroying their
own revenue model.* The Contradiction Matrix and Evidence Viewer aren't features — they are
the moat. Every product and marketing decision should reinforce "the only broker ranking
you can audit."

## 2. Product roadmap (in priority order)

**P0 — Trust artifacts (differentiation):**
- "Audit this score" share links — every score gets a permalink showing its full evidence
  chain. Screenshot-friendly, designed to be pasted into Reddit arguments.
- Data-freshness SLA badge on every page ("cash yields verified N days ago").
- Public changelog of every fee/yield change detected per broker ("Broker X quietly raised
  its ACAT fee") — this is *news generation from data*, the single best organic-growth asset.

**P1 — Retention & habit:**
- **Fee & yield change alerts**: "Email me when my broker changes fees, cash yield drops,
  or complaint volume spikes." Turns a one-time comparison into a subscription relationship
  — and builds the email list that later monetizes.
- **Switching cost calculator**: "What does staying at Broker X cost you per year?"
  (cash-drag on your idle cash + fees + ACAT out). Personal, quantified, shareable.

**P2 — Scale & depth:**
- Full automated fact refresh (per-broker page parsers + Playwright for walled sites).
- Historical score tracking (trend lines per broker; "momentum" becomes real).
- Coverage expansion only after depth is excellent: HSAs, 529s, robo-only platforms, crypto
  exchanges as separate verticals reusing the same engine.

## 3. Distribution (how it becomes "standard")

1. **Win the communities that hate affiliate reviews.** Bogleheads + r/personalfinance +
   r/investing are where high-intent broker questions get asked daily. Answer with evidence
   permalinks, not marketing. The tool is built to be citable — that's the wedge.
2. **Programmatic SEO with real substance.** Generate evidence-backed pages for every
   comparison query with search volume: "Fidelity vs Schwab", "best cash sweep 2026",
   "Robinhood ACAT fee". Incumbents have thin content here; we have data. Each page carries
   the methodology and freshness stamps.
3. **The annual "Broker Truth Report."** One flagship PR asset per year: biggest expert
   contradictions, biggest gap between marketing and customer experience, fee-change hall of
   shame. Designed for journalists (they cite neutral data sources, not affiliates).
4. **Embeddable widgets.** Free score/comparison widgets for finance bloggers and creators
   (with attribution links). They get credible data; we get distribution.
5. **Data licensing PR loop.** Publish the dataset openly (non-commercial); researchers and
   journalists citing it compounds the "industry standard" perception.

## 4. Monetization — sequenced to protect trust

The core rule: **never take money that varies by which broker wins.** Monetization must be
broker-agnostic or user-paid.

| Phase | Model | Notes |
|---|---|---|
| 1 (now) | Free + email list | Alerts and reports build the audience asset. Costs are trivial (public data, static hosting). |
| 2 | **Premium subscriptions ($5–8/mo)** | Fee/yield/complaint alerts for *your* brokers, portfolio-aware switching-cost analysis, historical trends, API access for individuals. Users pay for personalization, not for rankings. |
| 3 | **B2B data licensing** | The contradiction/customer-voice/fee-change dataset is valuable to fintechs, RIAs, journalists, and brokers' own competitive-intel teams. High margin, zero conflict (they buy data, not placement). |
| 4 (optional, risky) | **Flat-rate, identical-terms referral links** | Only if: same terms offered to every tracked broker, always disclosed, links never affect scores, and a public policy page explains it. If any broker gets special treatment, the moat dies. Many successful neutral sites (e.g. в consumer space) skip this entirely — recommended default: skip. |
| Never | Paid placements, sponsored rankings, "featured" slots | Instant credibility death. |

Realistic sequencing: trust → audience → subscriptions → data licensing. The subscription
product is the primary revenue engine; licensing is the high-margin upside.

## 5. Credibility infrastructure (do early, cheap)

- Publish the methodology version-controlled (done) and announce scoring changes publicly.
- "Conflicts of interest: none" page listing exactly how the project makes money.
- Correction policy: anyone (including brokers) can dispute a data point via GitHub issue;
  disputes and resolutions are public.
- Legal hygiene: everything is opinion/analysis of public data with evidence links —
  the evidence architecture is also the defamation defense.

## 6. What NOT to do

- Don't chase breadth (100 brokers, 40 dimensions) before depth — wrong data kills trust
  faster than missing data.
- Don't add AI-generated review prose; the market is drowning in it. Numbers + evidence +
  contradictions are the differentiation.
- Don't take broker affiliate deals "just temporarily" pre-audience. The one asset that
  can't be rebuilt is neutrality.

## 7. Metrics that matter

- Evidence-permalink shares (the trust loop working)
- Organic search entrances on comparison queries
- Alert subscribers (monetizable audience)
- Repeat visit rate (habit)
- External citations (press/forums linking as a source — the "standard" KPI)
