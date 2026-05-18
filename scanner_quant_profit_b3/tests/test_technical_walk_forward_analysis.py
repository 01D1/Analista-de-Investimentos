import sqlite3

from src.db.init_db import init_database
from src.scanners.technical_walk_forward_analysis import run
from tests.technical_fixtures import sample_price_df


def test_technical_walk_forward_analysis_dry_run(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    prices = sample_price_df(180)
    with sqlite3.connect(db_path) as con:
        prices.to_sql("cotahist_daily", con, if_exists="append", index=False)
    result = run(
        start="2026-01-01",
        end="2026-06-30",
        tickers=["PETR4"],
        train_months=2,
        test_months=1,
        dedupe=True,
        optimize_thresholds=True,
        dry_run=True,
        db_path=db_path,
    )
    assert result["summary"]["robustness_class"].startswith("TECH_WF_")
    assert result["dedup_summary"]["signals_before"] >= result["dedup_summary"]["signals_after"]

