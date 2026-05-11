"""Integração do core quantitativo com o scanner realtime sem quebrar legado."""
import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.scanners.realtime_profit_scanner import (
    calculate_intraday_metrics,
    demo_data,
    run_once,
    save_realtime_signals,
    score_realtime,
)


def _cfg():
    return {
        "database_path": "data/database/scanner_quant.db",
        "filtros": {
            "rompimento_tolerancia": 0.995,
            "volume_minimo": 50_000_000,
            "negocios_minimos": 1000,
            "variacao_minima_pct": 0.3,
        },
    }


def test_score_realtime_preserves_legacy_score_and_adds_quant_core_columns():
    metrics = calculate_intraday_metrics(demo_data())
    ranked = score_realtime(metrics, _cfg())

    required = {
        "score",
        "signal",
        "motivos",
        "score_final",
        "score_momentum",
        "score_tendencia",
        "score_liquidez",
        "score_volatilidade",
        "score_risco",
        "signal_type",
        "signal_confidence",
        "explanation",
    }

    assert required.issubset(ranked.columns)
    assert ranked["score"].max() == 100
    assert ranked["score_final"].between(0, 100).all()
    assert ranked.iloc[0]["signal_type"] in {
        "ROMPIMENTO COM VOLUME",
        "FORÇA COM LIQUIDEZ",
        "ESTICADO / RISCO DE PULLBACK",
        "OBSERVAR",
    }
    assert str(ranked.iloc[0]["asset"]) in ranked.iloc[0]["explanation"]


def test_save_realtime_signals_persists_quant_core_columns(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    ranked = score_realtime(calculate_intraday_metrics(demo_data()), _cfg())

    save_realtime_signals(ranked, db_path)

    with sqlite3.connect(db_path) as con:
        stored = pd.read_sql_query(
            """
            SELECT asset, score, score_final, score_momentum, score_liquidez,
                   score_risco, signal_type, signal_confidence, explanation
            FROM realtime_signals
            ORDER BY score_final DESC
            """,
            con,
        )

    assert not stored.empty
    assert stored["score_final"].between(0, 100).all()
    assert stored["signal_type"].notna().all()
    assert stored["explanation"].str.contains("aparece no radar").any()


def test_run_once_compare_scores_mode_returns_divergence_columns():
    cfg = _cfg()
    ranked = run_once(cfg, save_db=False, print_top=2, write_csv=False, demo=True, compare_scores_flag=True)

    assert "divergence_type" in ranked.columns
    assert "rank_change" in ranked.columns
    assert ranked["divergence_type"].notna().all()


def test_run_once_save_calibration_without_compare_warns(capsys):
    cfg = _cfg()
    ranked = run_once(
        cfg,
        save_db=False,
        print_top=1,
        write_csv=False,
        demo=True,
        compare_scores_flag=False,
        save_calibration=True,
    )

    captured = capsys.readouterr()
    assert "use --compare-scores junto com --save-calibration" in captured.out
    assert "divergence_type" not in ranked.columns
