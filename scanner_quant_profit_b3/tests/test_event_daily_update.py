import json
import sqlite3

from src.db.init_db import init_database
from src.scanners.event_daily_update import run


def test_event_daily_update_dry_run_with_macro_calendar(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO historical_backtest_results (run_id, trade_date, ticker) VALUES (1, '2026-01-05', 'PETR4')")
        con.execute(
            """
            INSERT INTO market_regime_daily (
                trade_date, primary_regime, trend_regime, volatility_regime, liquidity_regime, risk_regime
            ) VALUES ('2026-01-05', 'ALTA_TENDENCIAL', 'ALTA_TENDENCIAL', 'BAIXA_VOLATILIDADE', 'LIQUIDEZ_FORTE', 'RISCO_CONTROLADO')
            """
        )
        con.commit()
    macro_path = tmp_path / "calendar.json"
    macro_path.write_text(
        json.dumps([{"data": "2026-01-05", "pais": "Brasil", "indicador": "IPCA", "importancia": "alta"}], ensure_ascii=False),
        encoding="utf-8",
    )
    config_path = tmp_path / "events.yaml"
    macro_path_text = macro_path.as_posix()
    config_path.write_text(
        f"""
sources:
  macro_calendar:
    enabled: true
    path: "{macro_path_text}"
coverage:
  min_signals_with_event_pct: 10
  min_tickers_with_event_pct: 30
  min_sources_count: 1
""",
        encoding="utf-8",
    )

    result = run(
        start="2026-01-01",
        end="2026-01-31",
        sources=["macro_calendar"],
        save_db=True,
        dry_run=True,
        with_regimes=True,
        db_path=db_path,
        config_path=config_path,
    )

    assert result["events_loaded"] == 1
    assert result["coverage"]["signals_with_coverage"] == 1
    assert not result["coverage_by_regime"].empty
    assert result["coverage_run_id"] is None
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM market_events").fetchone()[0] == 0


def test_event_daily_update_saves_coverage_by_regime(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO historical_backtest_results (run_id, trade_date, ticker) VALUES (1, '2026-01-05', 'PETR4')")
        con.execute("INSERT INTO market_regime_daily (trade_date, primary_regime) VALUES ('2026-01-05', 'LATERAL')")
        con.commit()
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "event_date,ticker,event_type,event_source,event_title,event_summary,event_url,impact_direction,impact_score,confidence\n"
        "2026-01-05,PETR4,FATO_RELEVANTE,manual,Fato relevante,,,,0.8,0.9\n",
        encoding="utf-8",
    )

    result = run(
        start="2026-01-01",
        end="2026-01-31",
        sources=["csv"],
        csv_path=str(csv_path),
        save_db=True,
        with_regimes=True,
        db_path=db_path,
    )

    assert result["coverage_run_id"] == 1
    assert result["regime_rows_saved"] >= 1
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM event_coverage_by_regime").fetchone()[0] >= 1
