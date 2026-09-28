-- sql/data_quality.sql
-- Data quality checks. Output saved to reports/data_quality.md.
-- Each query returns a result set that should be EMPTY for clean data.

-- ================================================================
-- DQ1: Duplicate rows in analog_launches
-- ================================================================
SELECT 'DQ1_duplicate_analogs' AS check_name,
       drug, quarter_index, COUNT(*) AS cnt
FROM analog_launches
GROUP BY drug, quarter_index
HAVING COUNT(*) > 1;

-- ================================================================
-- DQ2: NULL approval dates
-- ================================================================
SELECT 'DQ2_null_approval_dates' AS check_name,
       drug, brand
FROM analog_launches
WHERE approval_date IS NULL;

-- ================================================================
-- DQ3: Negative or zero sales
-- ================================================================
SELECT 'DQ3_negative_sales' AS check_name,
       drug, quarter_index, sales_million_usd
FROM analog_launches
WHERE sales_million_usd <= 0;

-- ================================================================
-- DQ4: Drug name mismatches (brand vs generic inconsistency)
-- ================================================================
SELECT 'DQ4_brand_generic_mismatch' AS check_name,
       a.drug, a.brand, b.drug AS other_drug, b.brand AS other_brand
FROM (SELECT DISTINCT drug, brand FROM analog_launches) a
JOIN (SELECT DISTINCT drug, brand FROM analog_launches) b
  ON a.drug = b.drug AND a.brand != b.brand;

-- ================================================================
-- DQ5: Gaps in quarter_index sequence per drug
-- ================================================================
SELECT 'DQ5_quarter_gaps' AS check_name,
       drug,
       quarter_index,
       LAG(quarter_index) OVER (PARTITION BY drug ORDER BY quarter_index) AS prev_qi,
       quarter_index - LAG(quarter_index) OVER (PARTITION BY drug ORDER BY quarter_index) AS gap
FROM analog_launches
HAVING gap > 1;

-- ================================================================
-- DQ6: Post-AS_OF data in analog_launches (CRITICAL)
-- ================================================================
SELECT 'DQ6_post_asof_analog_data' AS check_name,
       drug, quarter_label, approval_date
FROM analog_launches
WHERE approval_date > '2021-04-30';

-- ================================================================
-- DQ7: Actuals with missing sales values
-- ================================================================
SELECT 'DQ7_null_actuals' AS check_name,
       quarter
FROM actuals_quarterly_sales
WHERE sales_million_usd IS NULL;

-- ================================================================
-- DQ8: Duplicate actuals quarters
-- ================================================================
SELECT 'DQ8_duplicate_actuals' AS check_name,
       quarter, COUNT(*) AS cnt
FROM actuals_quarterly_sales
GROUP BY quarter
HAVING COUNT(*) > 1;
