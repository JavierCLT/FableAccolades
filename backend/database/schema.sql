-- Best Broker Index — SQLite schema (MVP).
-- Design principle: every substantive data point (fact, rating, theme, complaint stat,
-- accolade) references a row in `evidence`, which stores the source URL, page title,
-- publisher, retrieval date, snippet, and confidence. Nothing is scored without evidence.
-- The schema uses plain INTEGER PRIMARY KEYs and portable types for a clean path to Postgres.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS brokers (
    id              INTEGER PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,          -- e.g. 'fidelity'
    name            TEXT NOT NULL,                 -- display name
    legal_name      TEXT,                          -- broker-dealer legal entity
    website         TEXT,
    founded_year    INTEGER,
    aum_usd_billions REAL,                         -- assets under administration/management (context only)
    aum_as_of       TEXT,                          -- ISO date the AUM figure refers to
    sipc_member     INTEGER NOT NULL DEFAULT 1,    -- 1 = yes (standard for tracked brokers)
    finra_crd       TEXT,                          -- FINRA CRD number of the broker-dealer
    regulatory_notes TEXT,
    active          INTEGER NOT NULL DEFAULT 1
);

-- Scoring dimensions (the 16 core dimensions).
CREATE TABLE IF NOT EXISTS dimensions (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,              -- e.g. 'cash_yield'
    name        TEXT NOT NULL,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Investor personas with default dimension weights (users may override in the UI).
CREATE TABLE IF NOT EXISTS personas (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS persona_weights (
    persona_id   INTEGER NOT NULL REFERENCES personas(id),
    dimension_id INTEGER NOT NULL REFERENCES dimensions(id),
    weight       REAL NOT NULL,                    -- weights per persona sum to 1.0
    PRIMARY KEY (persona_id, dimension_id)
);

-- Data sources (publishers). quality_weight in [0,1] feeds confidence scoring.
CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,            -- e.g. 'nerdwallet'
    name          TEXT NOT NULL,
    publisher     TEXT,
    source_type   TEXT NOT NULL CHECK (source_type IN
                    ('expert','customer','regulator','broker_official','forum','app_store','aggregate')),
    base_url      TEXT,
    quality_weight REAL NOT NULL DEFAULT 0.7,
    notes         TEXT
);

-- ---------------------------------------------------------------------------
-- Evidence: the traceability backbone
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS evidence (
    id                INTEGER PRIMARY KEY,
    source_id         INTEGER NOT NULL REFERENCES sources(id),
    broker_id         INTEGER REFERENCES brokers(id),   -- NULL when evidence is not broker-specific
    url               TEXT NOT NULL,
    title             TEXT,                             -- page title
    snippet           TEXT,                             -- short quoted/paraphrased evidence excerpt
    retrieval_date    TEXT NOT NULL,                    -- ISO date the data was retrieved/curated
    published_date    TEXT,                             -- ISO date content was published, if known
    collection_method TEXT NOT NULL CHECK (collection_method IN
                        ('api','scrape','bulk_download','manual_curation')),
    confidence        TEXT NOT NULL DEFAULT 'medium' CHECK (confidence IN ('high','medium','low')),
    raw_path          TEXT,                             -- pointer into data/raw for reproducibility
    unavailable       INTEGER NOT NULL DEFAULT 0,       -- 1 = source checked but data unavailable
    notes             TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_broker ON evidence(broker_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source_id);

-- ---------------------------------------------------------------------------
-- Data point tables (each row links to evidence)
-- ---------------------------------------------------------------------------

-- Objective product facts from broker public pages (fees, yields, features...).
CREATE TABLE IF NOT EXISTS product_facts (
    id            INTEGER PRIMARY KEY,
    broker_id     INTEGER NOT NULL REFERENCES brokers(id),
    dimension_id  INTEGER REFERENCES dimensions(id),
    fact_key      TEXT NOT NULL,                   -- e.g. 'outgoing_acat_fee_usd'
    value_text    TEXT,                            -- human-readable value
    value_numeric REAL,                            -- machine-usable value when applicable
    unit          TEXT,                            -- 'usd', 'pct_apy', 'bool', ...
    as_of_date    TEXT NOT NULL,                   -- date the fact was observed / last verified
    evidence_id   INTEGER NOT NULL REFERENCES evidence(id),
    UNIQUE (broker_id, fact_key)
);

-- Expert review ratings (overall or per dimension), normalized to 0-100.
CREATE TABLE IF NOT EXISTS expert_ratings (
    id               INTEGER PRIMARY KEY,
    broker_id        INTEGER NOT NULL REFERENCES brokers(id),
    source_id        INTEGER NOT NULL REFERENCES sources(id),
    dimension_id     INTEGER REFERENCES dimensions(id),  -- NULL = overall rating
    rating_raw       REAL NOT NULL,                       -- as published (e.g. 4.6)
    rating_scale_max REAL NOT NULL,                       -- e.g. 5.0
    rating_normalized REAL NOT NULL,                      -- 0-100
    review_cycle     TEXT,                                -- e.g. '2025'
    evidence_id      INTEGER NOT NULL REFERENCES evidence(id),
    UNIQUE (broker_id, source_id, dimension_id, review_cycle)
);

-- Public awards / rankings ("accolades").
CREATE TABLE IF NOT EXISTS accolades (
    id          INTEGER PRIMARY KEY,
    broker_id   INTEGER NOT NULL REFERENCES brokers(id),
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    award_title TEXT NOT NULL,
    category    TEXT,
    year        INTEGER,
    rank        INTEGER,                             -- 1 = winner; NULL if unranked mention
    evidence_id INTEGER NOT NULL REFERENCES evidence(id)
);

-- Aggregated CFPB complaint statistics per broker / product / issue over a window.
CREATE TABLE IF NOT EXISTS cfpb_complaint_stats (
    id              INTEGER PRIMARY KEY,
    broker_id       INTEGER NOT NULL REFERENCES brokers(id),
    company_name    TEXT NOT NULL,                   -- exact CFPB company string (or 'NOT_FOUND')
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    product         TEXT,                            -- CFPB product category; NULL = all
    issue           TEXT,                            -- CFPB issue; NULL = all
    complaint_count INTEGER NOT NULL,
    timely_response_pct REAL,
    evidence_id     INTEGER NOT NULL REFERENCES evidence(id)
);
CREATE INDEX IF NOT EXISTS idx_cfpb_broker ON cfpb_complaint_stats(broker_id);

-- Customer voice themes distilled from Reddit / forums / review sites / app stores.
CREATE TABLE IF NOT EXISTS customer_voice (
    id           INTEGER PRIMARY KEY,
    broker_id    INTEGER NOT NULL REFERENCES brokers(id),
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    dimension_id INTEGER REFERENCES dimensions(id),
    kind         TEXT NOT NULL CHECK (kind IN ('complaint','praise','opinion')),
    sentiment    TEXT NOT NULL CHECK (sentiment IN ('positive','negative','mixed')),
    theme        TEXT NOT NULL,                     -- short theme label
    volume       INTEGER NOT NULL DEFAULT 1,        -- approximate number of independent mentions
    severity     INTEGER NOT NULL DEFAULT 2 CHECK (severity BETWEEN 1 AND 5),
    snippet      TEXT,                              -- representative quote/paraphrase
    observed_date TEXT,                             -- date theme was observed (recency signal)
    evidence_id  INTEGER NOT NULL REFERENCES evidence(id)
);
CREATE INDEX IF NOT EXISTS idx_voice_broker ON customer_voice(broker_id);

-- Aggregate public ratings (Trustpilot / BBB / app stores) as numeric context.
CREATE TABLE IF NOT EXISTS aggregate_ratings (
    id           INTEGER PRIMARY KEY,
    broker_id    INTEGER NOT NULL REFERENCES brokers(id),
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    rating_raw   REAL NOT NULL,
    rating_scale_max REAL NOT NULL,
    review_count INTEGER,
    as_of_date   TEXT NOT NULL,
    evidence_id  INTEGER NOT NULL REFERENCES evidence(id),
    UNIQUE (broker_id, source_id)
);

-- ---------------------------------------------------------------------------
-- Computed tables (fully reproducible from the data-point tables)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dimension_scores (
    id                 INTEGER PRIMARY KEY,
    broker_id          INTEGER NOT NULL REFERENCES brokers(id),
    dimension_id       INTEGER NOT NULL REFERENCES dimensions(id),
    score              REAL NOT NULL,               -- 0-100 blended score
    confidence         REAL NOT NULL,               -- 0-100 confidence score
    evidence_count     INTEGER NOT NULL,
    fact_component     REAL,                        -- 0-100 or NULL if no facts
    customer_component REAL,
    expert_component   REAL,
    contradiction_penalty REAL NOT NULL DEFAULT 0,
    staleness_penalty  REAL NOT NULL DEFAULT 0,
    computed_at        TEXT NOT NULL,
    UNIQUE (broker_id, dimension_id)
);

-- Detected expert-vs-expert contradictions on the same broker + dimension.
CREATE TABLE IF NOT EXISTS contradictions (
    id           INTEGER PRIMARY KEY,
    broker_id    INTEGER NOT NULL REFERENCES brokers(id),
    dimension_id INTEGER REFERENCES dimensions(id),  -- NULL = overall ratings disagree
    source_a_id  INTEGER NOT NULL REFERENCES sources(id),
    source_b_id  INTEGER NOT NULL REFERENCES sources(id),
    score_a      REAL NOT NULL,                      -- normalized 0-100
    score_b      REAL NOT NULL,
    gap          REAL NOT NULL,                      -- |score_a - score_b|
    severity     TEXT NOT NULL CHECK (severity IN ('moderate','significant','severe')),
    evidence_a_id INTEGER NOT NULL REFERENCES evidence(id),
    evidence_b_id INTEGER NOT NULL REFERENCES evidence(id),
    computed_at  TEXT NOT NULL
);

-- Default persona scores (UI can recompute live with user-adjusted weights).
CREATE TABLE IF NOT EXISTS persona_scores (
    id             INTEGER PRIMARY KEY,
    persona_id     INTEGER NOT NULL REFERENCES personas(id),
    broker_id      INTEGER NOT NULL REFERENCES brokers(id),
    score          REAL NOT NULL,
    confidence     REAL NOT NULL,
    evidence_count INTEGER NOT NULL,
    computed_at    TEXT NOT NULL,
    UNIQUE (persona_id, broker_id)
);

-- Small computed per-broker signals (e.g. CFPB complaint momentum) that the UI needs
-- when recomputing persona scores live with user-adjusted weights.
CREATE TABLE IF NOT EXISTS broker_signals (
    id          INTEGER PRIMARY KEY,
    broker_id   INTEGER NOT NULL REFERENCES brokers(id),
    key         TEXT NOT NULL,
    value       REAL,
    detail      TEXT,
    computed_at TEXT NOT NULL,
    UNIQUE (broker_id, key)
);

-- Pipeline run log for data versioning / freshness display.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          INTEGER PRIMARY KEY,
    step        TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('success','partial','failed')),
    detail      TEXT,
    started_at  TEXT NOT NULL,
    finished_at TEXT
);
