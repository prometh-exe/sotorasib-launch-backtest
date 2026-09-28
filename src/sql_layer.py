"""
src/sql_layer.py – Execute SQL analytics queries and generate data quality report.
Creates analytical views in DuckDB and runs data quality checks.
"""
import duckdb
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import load_config, get_as_of_date

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_analytics_queries(con: duckdb.DuckDBPyConnection):
    """Create analytical views from sql/analytics_queries.sql."""
    sql_path = PROJECT_ROOT / "sql" / "analytics_queries.sql"
    sql_text = sql_path.read_text()

    # Split by CREATE OR REPLACE VIEW and execute each
    statements = []
    current = []
    for line in sql_text.split("\n"):
        if line.strip().startswith("CREATE OR REPLACE VIEW") and current:
            statements.append("\n".join(current))
            current = [line]
        elif line.strip().startswith("--") and not current:
            continue
        else:
            current.append(line)
    if current:
        statements.append("\n".join(current))

    for stmt in statements:
        stmt = stmt.strip()
        if stmt and "CREATE OR REPLACE VIEW" in stmt:
            # Extract view name for logging
            view_name = stmt.split("CREATE OR REPLACE VIEW")[1].split(" AS")[0].strip()
            try:
                con.execute(stmt)
                n = con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
                print(f"  Created view {view_name} ({n} rows)")
            except Exception as e:
                print(f"  Warning creating {view_name}: {e}")


def run_data_quality_checks(con: duckdb.DuckDBPyConnection) -> str:
    """Run data quality SQL queries and return a markdown report."""
    report_lines = [
        "# Data Quality Report",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*AS_OF: {get_as_of_date()}*",
        "",
        "---",
        "",
    ]

    checks = [
        ("DQ1: Duplicate Analog Rows", """
            SELECT drug, quarter_index, COUNT(*) AS cnt
            FROM analog_launches
            GROUP BY drug, quarter_index
            HAVING COUNT(*) > 1
        """),
        ("DQ2: NULL Approval Dates", """
            SELECT drug, brand
            FROM analog_launches
            WHERE approval_date IS NULL
        """),
        ("DQ3: Negative or Zero Sales", """
            SELECT drug, quarter_index, sales_million_usd
            FROM analog_launches
            WHERE sales_million_usd <= 0
        """),
        ("DQ4: Brand/Generic Name Mismatch", """
            SELECT a.drug, a.brand, b.drug AS other_drug, b.brand AS other_brand
            FROM (SELECT DISTINCT drug, brand FROM analog_launches) a
            JOIN (SELECT DISTINCT drug, brand FROM analog_launches) b
              ON a.drug = b.drug AND a.brand != b.brand
        """),
        ("DQ5: Gaps in Quarter Index", """
            WITH lagged AS (
                SELECT
                    drug,
                    quarter_index,
                    LAG(quarter_index) OVER (PARTITION BY drug ORDER BY quarter_index) AS prev_qi
                FROM analog_launches
            )
            SELECT drug, quarter_index, prev_qi,
                   quarter_index - prev_qi AS gap
            FROM lagged
            WHERE prev_qi IS NOT NULL AND quarter_index - prev_qi > 1
        """),
        ("DQ6: Post-AS_OF Analog Data (CRITICAL)", """
            SELECT DISTINCT drug, approval_date
            FROM analog_launches
            WHERE approval_date > '2021-04-30'
        """),
        ("DQ7: NULL Actuals Sales", """
            SELECT quarter
            FROM actuals_quarterly_sales
            WHERE sales_million_usd IS NULL
        """),
        ("DQ8: Duplicate Actuals Quarters", """
            SELECT quarter, COUNT(*) AS cnt
            FROM actuals_quarterly_sales
            GROUP BY quarter
            HAVING COUNT(*) > 1
        """),
        ("DQ9: Patient Funnel Completeness", """
            SELECT 'Missing: ' || expected.param AS issue
            FROM (
                VALUES
                    ('us_nsclc_new_cases_annual'),
                    ('advanced_metastatic_fraction'),
                    ('kras_g12c_prevalence_direct'),
                    ('biomarker_testing_rate_at_launch'),
                    ('second_line_eligible_fraction'),
                    ('wac_per_month'),
                    ('net_to_gross_ratio')
            ) AS expected(param)
            LEFT JOIN patient_funnel pf ON pf.parameter = expected.param
            WHERE pf.parameter IS NULL
        """),
    ]

    all_pass = True
    for check_name, query in checks:
        try:
            df = con.execute(query).fetchdf()
            if len(df) == 0:
                report_lines.append(f"## ✅ {check_name}")
                report_lines.append("No issues found.")
                report_lines.append("")
            else:
                all_pass = False
                report_lines.append(f"## ⚠️ {check_name}")
                report_lines.append(f"**{len(df)} issue(s) found:**")
                report_lines.append("")
                report_lines.append(df.to_markdown(index=False))
                report_lines.append("")
        except Exception as e:
            report_lines.append(f"## ❌ {check_name}")
            report_lines.append(f"Query error: {e}")
            report_lines.append("")
            all_pass = False

    # Summary statistics
    report_lines.append("---")
    report_lines.append("## Summary Statistics")
    report_lines.append("")

    summaries = [
        ("Analog drugs loaded", "SELECT COUNT(DISTINCT drug) FROM analog_launches"),
        ("Analog data points", "SELECT COUNT(*) FROM analog_launches"),
        ("Actual quarters loaded", "SELECT COUNT(*) FROM actuals_quarterly_sales"),
        ("Patient funnel params", "SELECT COUNT(*) FROM patient_funnel"),
        ("Competitor entries", "SELECT COUNT(*) FROM competitors"),
        ("Clinical trials loaded", "SELECT COUNT(*) FROM trials_asof"),
    ]

    for label, query in summaries:
        try:
            val = con.execute(query).fetchone()[0]
            report_lines.append(f"- **{label}**: {val}")
        except Exception:
            report_lines.append(f"- **{label}**: N/A")

    report_lines.append("")
    if all_pass:
        report_lines.append("> [!NOTE]")
        report_lines.append("> All data quality checks passed. ✅")
    else:
        report_lines.append("> [!WARNING]")
        report_lines.append("> Some data quality checks found issues. Review above.")

    return "\n".join(report_lines)


def main():
    cfg = load_config()
    db_path = PROJECT_ROOT / cfg["database"]["path"]

    if not db_path.exists():
        print("Database not found. Run `make data` first.")
        sys.exit(1)

    con = duckdb.connect(str(db_path))
    print(f"SQL Layer – Connected to {db_path}")
    print(f"{'='*50}")

    print("\n[1/2] Creating analytical views...")
    run_analytics_queries(con)

    print("\n[2/2] Running data quality checks...")
    report = run_data_quality_checks(con)

    # Save report
    report_path = PROJECT_ROOT / "reports" / "data_quality.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\n  Data quality report saved to {report_path}")

    # Also print a preview of the analog curves view
    print("\n[Preview] Analog curve summary:")
    try:
        df = con.execute("""
            SELECT drug, COUNT(*) AS quarters,
                   ROUND(MIN(sales_million_usd), 1) AS min_sales,
                   ROUND(MAX(sales_million_usd), 1) AS max_sales,
                   ROUND(SUM(sales_million_usd), 1) AS total_sales
            FROM v_analog_curves
            GROUP BY drug
            ORDER BY total_sales DESC
        """).fetchdf()
        print(df.to_string(index=False))
    except Exception as e:
        print(f"  Could not preview: {e}")

    con.close()
    print(f"\n{'='*50}")
    print("SQL layer complete.")


if __name__ == "__main__":
    main()
