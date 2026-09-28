# Lumakras Launch Back-Test – Makefile
# Usage: make all  (runs the full pipeline from scratch)
# Requires: Python 3.10+, pip

.PHONY: setup data sql model backtest report all clean test

# ── Setup ──────────────────────────────────────────────────────────────
setup:
	pip install -r requirements.txt

# ── Data ingestion & processing ────────────────────────────────────────
data:
	python src/data_loader.py

# ── SQL layer (DuckDB) ─────────────────────────────────────────────────
sql:
	python src/sql_layer.py

# ── Models (Bass, analog regression, competitor classifier, funnel) ────
model:
	python src/models.py

# ── Back-test against actuals ──────────────────────────────────────────
backtest:
	python src/backtest.py

# ── Reports (Excel, dashboard, deck) ──────────────────────────────────
report:
	python src/reports.py

# ── Tests ──────────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v

# ── Full pipeline ──────────────────────────────────────────────────────
all: setup data sql model backtest report test
	@echo "=== Full pipeline complete ==="

# ── Clean generated files ─────────────────────────────────────────────
clean:
	del /Q data\forecast.duckdb 2>nul || true
	del /Q data\processed\*.csv 2>nul || true
	del /Q models\*.pkl 2>nul || true
	del /Q reports\forecast_model.xlsx 2>nul || true
	del /Q reports\dashboard.html 2>nul || true
	del /Q reports\deck.pptx 2>nul || true
	del /Q reports\data_quality.md 2>nul || true
