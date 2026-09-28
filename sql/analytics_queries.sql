-- sql/analytics_queries.sql
-- Analytical queries using CTEs and window functions for the forecast model.
-- All queries are parameterized by AS_OF date where relevant.

-- ================================================================
-- Q1: Analog launch curve with running totals and growth rates
-- Uses LAG, SUM OVER, and RANK window functions
-- ================================================================
-- :as_of_date parameter filters to pre-AS_OF data only
CREATE OR REPLACE VIEW v_analog_curves AS
WITH base AS (
    SELECT
        drug,
        brand,
        company,
        target,
        biomarker_gated,
        orphan_flag,
        competitors_at_launch,
        quarter_index,
        quarter_label,
        sales_million_usd,
        approval_date
    FROM analog_launches
    WHERE approval_date <= '2021-04-30'  -- AS_OF gate
),
with_lag AS (
    SELECT
        *,
        LAG(sales_million_usd, 1) OVER (
            PARTITION BY drug ORDER BY quarter_index
        ) AS prev_quarter_sales,
        SUM(sales_million_usd) OVER (
            PARTITION BY drug ORDER BY quarter_index
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_sales,
        RANK() OVER (
            PARTITION BY drug ORDER BY quarter_index
        ) AS quarter_rank,
        MAX(sales_million_usd) OVER (
            PARTITION BY drug
        ) AS peak_quarterly_sales
    FROM base
)
SELECT
    *,
    CASE
        WHEN prev_quarter_sales > 0
        THEN (sales_million_usd - prev_quarter_sales) / prev_quarter_sales
        ELSE NULL
    END AS qoq_growth_rate,
    sales_million_usd / NULLIF(peak_quarterly_sales, 0) AS fraction_of_peak
FROM with_lag
ORDER BY drug, quarter_index;


-- ================================================================
-- Q2: Peak sales and time-to-peak for each analog
-- Features for the analog regression model
-- ================================================================
CREATE OR REPLACE VIEW v_analog_peak_features AS
WITH peaks AS (
    SELECT
        drug,
        brand,
        target,
        biomarker_gated,
        orphan_flag,
        competitors_at_launch,
        MAX(sales_million_usd) AS peak_quarterly_sales,
        SUM(sales_million_usd) AS total_sales_8q,
        AVG(sales_million_usd) AS avg_quarterly_sales,
        COUNT(*) AS n_quarters_observed
    FROM analog_launches
    WHERE approval_date <= '2021-04-30'
    GROUP BY drug, brand, target, biomarker_gated, orphan_flag, competitors_at_launch
),
time_to_peak AS (
    SELECT
        drug,
        quarter_index AS peak_quarter_index
    FROM (
        SELECT
            drug,
            quarter_index,
            sales_million_usd,
            RANK() OVER (PARTITION BY drug ORDER BY sales_million_usd DESC) AS rnk
        FROM analog_launches
        WHERE approval_date <= '2021-04-30'
    ) sub
    WHERE rnk = 1
)
SELECT
    p.*,
    t.peak_quarter_index
FROM peaks p
JOIN time_to_peak t ON p.drug = t.drug;


-- ================================================================
-- Q3: Competitor pipeline summary at AS_OF
-- ================================================================
CREATE OR REPLACE VIEW v_competitor_landscape AS
SELECT
    drug_name,
    company,
    highest_phase,
    phase_date,
    indication,
    notes,
    CASE highest_phase
        WHEN 'Phase 3' THEN 3
        WHEN 'Phase 2' THEN 2
        WHEN 'Phase 1/2' THEN 1.5
        WHEN 'Phase 1' THEN 1
        ELSE 0
    END AS phase_numeric,
    CASE
        WHEN highest_phase IN ('Phase 3', 'Phase 2/3') THEN 'HIGH'
        WHEN highest_phase IN ('Phase 2', 'Phase 1/2') THEN 'MEDIUM'
        ELSE 'LOW'
    END AS threat_level
FROM competitors
WHERE phase_date <= '2021-04-30'
ORDER BY phase_numeric DESC;


-- ================================================================
-- Q4: Trial phase transitions for competitor classifier
-- Counts how many KRAS G12C trials moved between phases
-- ================================================================
CREATE OR REPLACE VIEW v_trial_phase_transitions AS
SELECT
    drug_name,
    sponsor,
    phase,
    overall_status,
    start_date,
    enrollment,
    CASE
        WHEN phase = 'Phase 1' AND overall_status IN ('Completed', 'Active, not recruiting') THEN 'P1_complete'
        WHEN phase = 'Phase 2' AND overall_status IN ('Completed', 'Active, not recruiting') THEN 'P2_complete'
        WHEN phase = 'Phase 3' AND overall_status IN ('Recruiting', 'Active, not recruiting') THEN 'P3_active'
        WHEN overall_status = 'Terminated' THEN 'terminated'
        WHEN overall_status = 'Withdrawn' THEN 'withdrawn'
        ELSE 'other'
    END AS transition_status
FROM trials_asof
WHERE first_posted_date <= '2021-04-30'
ORDER BY drug_name, start_date;
