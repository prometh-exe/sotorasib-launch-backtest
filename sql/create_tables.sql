-- sql/create_tables.sql
-- DuckDB schema for the Lumakras launch forecast back-test
-- WHY DuckDB: Zero-config embedded OLAP engine, columnar storage for analytics,
-- native CSV/Parquet ingestion, full SQL:2016 with CTEs and window functions,
-- runs in the same Python process without a server.

-- ================================================================
-- TABLE: analog_launches
-- Quarterly sales for 8-12 targeted oncology launches, indexed to
-- launch quarter. Used to fit Bass diffusion and analog regression.
-- All data must be pre-AS_OF.
-- ================================================================
CREATE TABLE IF NOT EXISTS analog_launches (
    drug              VARCHAR NOT NULL,
    brand             VARCHAR NOT NULL,
    company           VARCHAR NOT NULL,
    target            VARCHAR NOT NULL,
    indication        VARCHAR NOT NULL,
    approval_date     DATE NOT NULL,
    line_of_therapy   VARCHAR,
    biomarker_gated   BOOLEAN NOT NULL,
    orphan_flag       BOOLEAN NOT NULL,
    competitors_at_launch INTEGER NOT NULL,
    quarter_index     INTEGER NOT NULL,     -- 0 = launch quarter
    quarter_label     VARCHAR NOT NULL,     -- e.g. '2021-Q2'
    sales_million_usd DOUBLE NOT NULL,
    source            VARCHAR,
    PRIMARY KEY (drug, quarter_index)
);

-- ================================================================
-- TABLE: actuals_quarterly_sales
-- Reported Lumakras sales (post-AS_OF). Used ONLY for back-testing.
-- ================================================================
CREATE TABLE IF NOT EXISTS actuals_quarterly_sales (
    quarter           VARCHAR NOT NULL PRIMARY KEY,  -- e.g. '2021-Q2'
    sales_million_usd DOUBLE NOT NULL,
    source            VARCHAR,
    confidence        VARCHAR,
    notes             VARCHAR
);

-- ================================================================
-- TABLE: competitors
-- KRAS G12C competitive landscape at the time of forecast (pre-AS_OF)
-- ================================================================
CREATE TABLE IF NOT EXISTS competitors (
    drug_name         VARCHAR NOT NULL,
    company           VARCHAR NOT NULL,
    target            VARCHAR NOT NULL,
    mechanism         VARCHAR,
    highest_phase     VARCHAR,
    phase_date        DATE,
    nct_id            VARCHAR,
    indication        VARCHAR,
    notes             VARCHAR,
    PRIMARY KEY (drug_name, nct_id)
);

-- ================================================================
-- TABLE: trials_asof
-- Clinical trials for KRAS G12C therapies as known before AS_OF.
-- Pulled from ClinicalTrials.gov API / AACT.
-- ================================================================
CREATE TABLE IF NOT EXISTS trials_asof (
    nct_id            VARCHAR NOT NULL PRIMARY KEY,
    brief_title       VARCHAR,
    official_title    VARCHAR,
    overall_status    VARCHAR,
    phase             VARCHAR,
    start_date        DATE,
    completion_date   DATE,
    enrollment        INTEGER,
    sponsor           VARCHAR,
    drug_name         VARCHAR,
    conditions        VARCHAR,
    intervention_type VARCHAR,
    intervention_name VARCHAR,
    first_posted_date DATE,
    last_update_date  DATE
);

-- ================================================================
-- TABLE: patient_funnel
-- Pre-AS_OF patient funnel parameters
-- ================================================================
CREATE TABLE IF NOT EXISTS patient_funnel (
    parameter         VARCHAR NOT NULL PRIMARY KEY,
    value             DOUBLE NOT NULL,
    unit              VARCHAR,
    source            VARCHAR,
    confidence        VARCHAR,
    notes             VARCHAR
);
