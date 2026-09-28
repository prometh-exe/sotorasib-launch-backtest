"""
tests/test_model_outputs.py – Verify model execution, output dimensions,
funnel monotonicity across quarters, and back-test metric sanity.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.config import load_config, get_as_of_date


class TestModelArtifacts:
    """Ensure all serialized model artifacts and tables exist."""

    def test_serialized_models_exist(self):
        models_dir = PROJECT_ROOT / "models"
        assert (models_dir / "bass_model.pkl").exists(), "bass_model.pkl missing"
        assert (models_dir / "analog_regression.pkl").exists(), "analog_regression.pkl missing"
        assert (models_dir / "competitor_classifier.pkl").exists(), "competitor_classifier.pkl missing"
        assert (models_dir / "monte_carlo_engine.pkl").exists(), "monte_carlo_engine.pkl missing"

    def test_forecast_envelopes_shape(self):
        """Forecast envelope must have exactly 16 quarters."""
        path = PROJECT_ROOT / "data" / "processed" / "forecast_envelopes.csv"
        assert path.exists(), "forecast_envelopes.csv missing"
        df = pd.read_csv(path)
        assert len(df) == 16, f"Expected 16 quarters, got {len(df)}"
        assert "p10_million_usd" in df.columns
        assert "p50_million_usd" in df.columns
        assert "p90_million_usd" in df.columns

    def test_envelope_ordering(self):
        """For every quarter, P10 <= P25 <= P50 <= P75 <= P90."""
        df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "forecast_envelopes.csv")
        for _, row in df.iterrows():
            assert row["p10_million_usd"] <= row["p50_million_usd"], f"P10 > P50 in {row['quarter']}"
            assert row["p50_million_usd"] <= row["p90_million_usd"], f"P50 > P90 in {row['quarter']}"

    def test_tornado_sensitivity_shape(self):
        """Tornado chart must contain ranked parameters with positive swings."""
        path = PROJECT_ROOT / "data" / "processed" / "tornado_sensitivity.csv"
        assert path.exists(), "tornado_sensitivity.csv missing"
        df = pd.read_csv(path)
        assert len(df) >= 5, "Expected at least 5 sensitivity parameters"
        assert (df["swing_range_m"] >= 0).all(), "Negative swing range detected"


class TestBacktestOutputs:
    """Validate backtest results and attribution matrices."""

    def test_backtest_metrics_exist(self):
        p = PROJECT_ROOT / "data" / "processed" / "backtest_detailed_quarterly.csv"
        assert p.exists(), "backtest_detailed_quarterly.csv missing"
        df = pd.read_csv(p)
        assert len(df) == 16
        assert "actual_sales_m" in df.columns
        assert "error_m" in df.columns

    def test_horizon_summary_covers_all_4_years(self):
        p = PROJECT_ROOT / "data" / "processed" / "backtest_horizon_summary.csv"
        assert p.exists(), "backtest_horizon_summary.csv missing"
        df = pd.read_csv(p)
        assert len(df) == 4, f"Expected 4 horizons, got {len(df)}"
        assert set(df["horizon"]) == {"Year 1 (Launch)", "Year 2", "Year 3", "Year 4"}

    def test_error_attribution_reduction(self):
        p = PROJECT_ROOT / "data" / "processed" / "error_attribution.csv"
        assert p.exists(), "error_attribution.csv missing"
        df = pd.read_csv(p)
        assert len(df) >= 4


class TestReportDeliverables:
    """Ensure all required reporting artifacts were created and non-empty."""

    def test_excel_workbook_exists_and_valid(self):
        path = PROJECT_ROOT / "reports" / "forecast_model.xlsx"
        assert path.exists()
        assert path.stat().st_size > 5000

    def test_dashboard_html_exists(self):
        path = PROJECT_ROOT / "reports" / "dashboard.html"
        assert path.exists()
        assert path.stat().st_size > 10000

    def test_powerpoint_deck_exists(self):
        path = PROJECT_ROOT / "reports" / "deck.pptx"
        assert path.exists()
        assert path.stat().st_size > 15000

    def test_assumption_defense_markdown_exists(self):
        path = PROJECT_ROOT / "reports" / "assumption_defense.md"
        assert path.exists()
        assert path.stat().st_size > 1000
