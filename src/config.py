"""
src/config.py – Load and validate project configuration.
"""
import yaml
from pathlib import Path
from datetime import date, datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load config.yaml and return as dict."""
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def get_as_of_date(cfg: dict = None) -> date:
    """Return the AS_OF date as a Python date object."""
    if cfg is None:
        cfg = load_config()
    return datetime.strptime(cfg["dates"]["as_of"], "%Y-%m-%d").date()


def get_approval_date(cfg: dict = None) -> date:
    """Return the FDA approval date as a Python date object."""
    if cfg is None:
        cfg = load_config()
    return datetime.strptime(cfg["dates"]["fda_approval"], "%Y-%m-%d").date()


def quarter_to_date(q_str: str, end_of_quarter: bool = True) -> date:
    """Convert 'YYYY-QN' to a date. By default returns the last day of that quarter."""
    year, qn = q_str.split("-")
    if end_of_quarter:
        quarter_ends = {
            "Q1": (3, 31),
            "Q2": (6, 30),
            "Q3": (9, 30),
            "Q4": (12, 31),
        }
        m, d = quarter_ends[qn]
        return date(int(year), m, d)
    else:
        quarter_starts = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}
        return date(int(year), quarter_starts[qn], 1)


def is_pre_asof(dt: date, cfg: dict = None) -> bool:
    """Check whether a date is on or before the AS_OF date."""
    as_of = get_as_of_date(cfg)
    return dt <= as_of


if __name__ == "__main__":
    cfg = load_config()
    print(f"Project: {cfg['project']['name']}")
    print(f"AS_OF:   {get_as_of_date(cfg)}")
    print(f"Approval: {get_approval_date(cfg)}")
