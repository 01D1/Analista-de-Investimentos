import sqlite3

from src.db.init_db import init_database
from src.signals.signal_source_unifier import (
    load_integrated_signals_for_paper,
    load_quant_signals_for_paper,
    load_technical_signals_for_paper,
    unify_signals_for_paper,
    validate_unified_signals,
)


def test_signal_source_unifier_loads_and_validates(tmp_path):
    db = tmp_path / "unifier.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO historical_backtest_results (id, run_id, trade_date, ticker, score_final, signal_type, signal_confidence) VALUES (1, 1, '2026-01-02', 'PETR4', 70, 'OBSERVAR', 'MEDIA')")
        con.execute("INSERT INTO technical_setup_signals (id, created_at, trade_date, ticker, setup_type, setup_score, setup_confidence, setup_direction) VALUES (2, '2026-01-02', '2026-01-02', 'PETR4', 'BREAKOUT_VOLUME', 75, 0.7, 'BULLISH')")
        con.execute("INSERT INTO asset_intelligence_snapshots (id, created_at, trade_date, ticker, integrated_score, integrated_status, integrated_confidence) VALUES (3, '2026-01-02', '2026-01-02', 'PETR4', 55, 'APENAS_MONITORAR', 'BAIXA')")
        con.commit()
    unified = unify_signals_for_paper(
        {
            "quant": load_quant_signals_for_paper(db),
            "technical": load_technical_signals_for_paper(db),
            "integrated": load_integrated_signals_for_paper(db),
        }
    )
    validation = validate_unified_signals(unified)
    assert set(unified["signal_source"]) == {"quant", "technical", "integrated"}
    assert validation["valid"] is True

