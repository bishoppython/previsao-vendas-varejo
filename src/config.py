from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "us_retail_sales.csv"
DB = ROOT / "data" / "warehouse.duckdb"
SQL = ROOT / "sql"
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"

SOURCE_URL = "https://raw.githubusercontent.com/facebook/prophet/main/examples/example_retail_sales.csv"
SOURCE_SHA256 = "6556f0683b78362c4bc4390b8feb66870beecd7189cc052e650ccac9b21cd65c"
HORIZON = 12          # meses à frente
BACKTEST_ORIGINS = 5  # origens anuais no backtest (últimos 5 anos)
