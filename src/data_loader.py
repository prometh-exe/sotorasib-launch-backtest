"""
src/data_loader.py – Load raw CSVs into DuckDB and fetch competitor trial data.
Enforces AS_OF gating on all inputs.
"""
import duckdb
import pandas as pd
import requests
import json
from pathlib import Path
from datetime import datetime, date
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import load_config, get_as_of_date, quarter_to_date

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_database(cfg: dict) -> duckdb.DuckDBPyConnection:
    """Create DuckDB database and run schema creation."""
    db_path = PROJECT_ROOT / cfg["database"]["path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    # Run schema creation
    schema_sql = (PROJECT_ROOT / "sql" / "create_tables.sql").read_text()
    # Split on semicolons and execute each statement
    for stmt in schema_sql.split(";"):
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if clean_stmt:
            con.execute(clean_stmt)

    return con


def load_analog_launches(con: duckdb.DuckDBPyConnection, as_of: date):
    """Load analog launches CSV into DuckDB, filtering to pre-AS_OF only."""
    csv_path = PROJECT_ROOT / "data" / "raw" / "analog_launches.csv"
    df = pd.read_csv(csv_path, comment='#')

    # Convert boolean columns
    df["biomarker_gated"] = df["biomarker_gated"].map({"yes": True, "no": False})
    df["orphan_flag"] = df["orphan_flag"].map({"yes": True, "no": False})

    # Convert approval_date to date
    df["approval_date"] = pd.to_datetime(df["approval_date"]).dt.date

    # AS_OF GATE: Filter to only pre-AS_OF data
    df_pre = df[df["approval_date"] <= as_of].copy()

    # Also filter individual quarter data points to pre-AS_OF
    df_pre["quarter_date"] = df_pre["quarter_label"].apply(quarter_to_date)
    df_pre = df_pre[df_pre["quarter_date"] <= as_of].drop(columns=["quarter_date"])

    # Clear and reload
    con.execute("DELETE FROM analog_launches")
    con.execute("INSERT INTO analog_launches SELECT * FROM df_pre")

    n = con.execute("SELECT COUNT(*) FROM analog_launches").fetchone()[0]
    drugs = con.execute("SELECT DISTINCT drug FROM analog_launches").fetchall()
    print(f"  Loaded {n} analog data points for {len(drugs)} drugs (pre-AS_OF)")
    return n


def load_actuals(con: duckdb.DuckDBPyConnection):
    """Load actual quarterly sales into DuckDB (for back-testing only)."""
    csv_path = PROJECT_ROOT / "data" / "raw" / "actuals_quarterly_sales.csv"
    df = pd.read_csv(csv_path, comment='#')

    con.execute("DELETE FROM actuals_quarterly_sales")
    con.execute("INSERT INTO actuals_quarterly_sales SELECT * FROM df")

    n = con.execute("SELECT COUNT(*) FROM actuals_quarterly_sales").fetchone()[0]
    print(f"  Loaded {n} actual quarterly sales data points (post-AS_OF, for backtest only)")
    return n


def load_patient_funnel(con: duckdb.DuckDBPyConnection):
    """Load patient funnel parameters from manual_inputs.csv."""
    csv_path = PROJECT_ROOT / "data" / "manual_inputs.csv"
    df = pd.read_csv(csv_path, comment='#')

    # Filter to non-placeholder values
    df_valid = df[df["is_placeholder"] != "yes"].copy()
    df_funnel = df_valid[["parameter", "value", "unit", "source", "confidence", "notes"]].copy()
    df_funnel["value"] = df_funnel["value"].astype(float)

    con.execute("DELETE FROM patient_funnel")
    con.execute("INSERT INTO patient_funnel SELECT * FROM df_funnel")

    n = con.execute("SELECT COUNT(*) FROM patient_funnel").fetchone()[0]
    print(f"  Loaded {n} patient funnel parameters")
    return n


def fetch_competitor_trials(con: duckdb.DuckDBPyConnection, as_of: date):
    """
    Fetch KRAS G12C clinical trials from ClinicalTrials.gov API (v2).
    Only trials posted before AS_OF are included.
    """
    print("  Fetching KRAS G12C trials from ClinicalTrials.gov API...")

    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": "KRAS G12C",
        "filter.advanced": f"AREA[StudyFirstPostDate]RANGE[MIN,{as_of.isoformat()}]",
        "pageSize": 100,
        "fields": (
            "NCTId,BriefTitle,OfficialTitle,OverallStatus,Phase,"
            "StartDate,CompletionDate,EnrollmentCount,"
            "LeadSponsorName,Condition,InterventionType,"
            "InterventionName,StudyFirstPostDate,LastUpdatePostDate"
        ),
    }

    trials = []
    next_token = None

    for page in range(10):  # max 10 pages
        if next_token:
            params["pageToken"] = next_token

        try:
            resp = requests.get(base_url, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"    API returned {resp.status_code}, using cached/empty data")
                break

            data = resp.json()
            studies = data.get("studies", [])
            if not studies:
                break

            for study in studies:
                proto = study.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status = proto.get("statusModule", {})
                design = proto.get("designModule", {})
                sponsor = proto.get("sponsorCollaboratorsModule", {})
                conditions_mod = proto.get("conditionsModule", {})
                interventions_mod = proto.get("armsInterventionsModule", {})

                # Extract intervention info
                interventions = interventions_mod.get("interventions", [])
                int_type = interventions[0].get("type", "") if interventions else ""
                int_name = interventions[0].get("name", "") if interventions else ""

                # Parse dates safely
                start_str = status.get("startDateStruct", {}).get("date", "")
                comp_str = status.get("completionDateStruct", {}).get("date", "")
                first_post = status.get("studyFirstPostDateStruct", {}).get("date", "")
                last_update = status.get("lastUpdatePostDateStruct", {}).get("date", "")

                def parse_ct_date(s):
                    if not s:
                        return None
                    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%B %Y", "%Y-%m"):
                        try:
                            return datetime.strptime(s, fmt).date()
                        except ValueError:
                            continue
                    return None

                trial = {
                    "nct_id": ident.get("nctId", ""),
                    "brief_title": ident.get("briefTitle", ""),
                    "official_title": ident.get("officialTitle", ""),
                    "overall_status": status.get("overallStatus", ""),
                    "phase": ",".join(design.get("phases", [])),
                    "start_date": parse_ct_date(start_str),
                    "completion_date": parse_ct_date(comp_str),
                    "enrollment": design.get("enrollmentInfo", {}).get("count", None),
                    "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
                    "drug_name": int_name,
                    "conditions": ",".join(conditions_mod.get("conditions", [])),
                    "intervention_type": int_type,
                    "intervention_name": int_name,
                    "first_posted_date": parse_ct_date(first_post),
                    "last_update_date": parse_ct_date(last_update),
                }
                trials.append(trial)

            next_token = data.get("nextPageToken")
            if not next_token:
                break

        except requests.exceptions.RequestException as e:
            print(f"    API request failed: {e}")
            break

    if trials:
        df = pd.DataFrame(trials)

        # AS_OF GATE: Only keep trials first posted before AS_OF
        df["first_posted_date"] = pd.to_datetime(df["first_posted_date"]).dt.date
        df_pre = df[df["first_posted_date"].apply(lambda d: d is not None and d <= as_of)].copy()

        con.execute("DELETE FROM trials_asof")
        con.execute("INSERT INTO trials_asof SELECT * FROM df_pre")
        n = con.execute("SELECT COUNT(*) FROM trials_asof").fetchone()[0]
        print(f"  Loaded {n} trials posted before AS_OF")
    else:
        print("  No trials fetched (API may be unavailable). Continuing with empty table.")

    # Also populate the competitors table from known data
    _load_known_competitors(con, as_of)


def _load_known_competitors(con: duckdb.DuckDBPyConnection, as_of: date):
    """Load known KRAS G12C competitors from curated data."""
    competitors = [
        ("adagrasib (MRTX849)", "Mirati Therapeutics", "KRAS G12C", "covalent inhibitor",
         "Phase 1/2", date(2019, 1, 15), "NCT03785249", "NSCLC",
         "KRYSTAL-1 Phase 1/2; data presented at AACR 2020 showing 45% ORR"),
        ("adagrasib (MRTX849)", "Mirati Therapeutics", "KRAS G12C", "covalent inhibitor",
         "Phase 3", date(2021, 3, 1), "NCT04685135", "NSCLC",
         "KRYSTAL-12 Phase 3 vs docetaxel; initiated Q1 2021"),
        ("GDC-6036 (divarasib)", "Genentech/Roche", "KRAS G12C", "covalent inhibitor",
         "Phase 1", date(2020, 9, 1), "NCT04449874", "Solid tumors",
         "Phase 1 dose-escalation"),
        ("JNJ-74699157", "Johnson & Johnson", "KRAS G12C", "covalent inhibitor",
         "Phase 1", date(2020, 3, 1), "NCT04006301", "Solid tumors",
         "Phase 1; later discontinued"),
        ("LY3537982", "Eli Lilly", "KRAS G12C", "covalent inhibitor",
         "Phase 1", date(2021, 2, 1), "NCT04956640", "Solid tumors",
         "Phase 1 dose-escalation; early stage at AS_OF"),
        ("D-1553 (garsorasib)", "InventisBio", "KRAS G12C", "covalent inhibitor",
         "Phase 1/2", date(2020, 12, 1), "NCT04585035", "Solid tumors",
         "Phase 1/2 in China primarily"),
        ("JAB-21822", "Jacobio Pharma", "KRAS G12C", "covalent inhibitor",
         "Phase 1/2", date(2020, 8, 1), "NCT05002270", "Solid tumors",
         "Phase 1/2; China-based"),
    ]

    df_comp = pd.DataFrame(competitors, columns=[
        "drug_name", "company", "target", "mechanism",
        "highest_phase", "phase_date", "nct_id", "indication", "notes"
    ])

    # AS_OF GATE
    df_comp = df_comp[df_comp["phase_date"] <= as_of].copy()

    con.execute("DELETE FROM competitors")
    con.execute("INSERT INTO competitors SELECT * FROM df_comp")
    n = con.execute("SELECT COUNT(*) FROM competitors").fetchone()[0]
    print(f"  Loaded {n} competitor entries (pre-AS_OF)")


def main():
    cfg = load_config()
    as_of = get_as_of_date(cfg)
    print(f"Data Loader – AS_OF = {as_of}")
    print(f"{'='*50}")

    con = create_database(cfg)

    print("\n[1/4] Loading analog launches...")
    load_analog_launches(con, as_of)

    print("\n[2/4] Loading actuals (for backtest only)...")
    load_actuals(con)

    print("\n[3/4] Loading patient funnel parameters...")
    load_patient_funnel(con)

    print("\n[4/4] Fetching competitor trial data...")
    fetch_competitor_trials(con, as_of)

    # Export processed data
    print("\n[Export] Saving processed tables to data/processed/...")
    processed_dir = PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    for table in ["analog_launches", "actuals_quarterly_sales", "patient_funnel", "competitors", "trials_asof"]:
        df = con.execute(f"SELECT * FROM {table}").fetchdf()
        df.to_csv(processed_dir / f"{table}.csv", index=False)
        print(f"  -> data/processed/{table}.csv ({len(df)} rows)")

    con.close()
    print(f"\n{'='*50}")
    print("Data loading complete.")


if __name__ == "__main__":
    main()
