"""Testes da persistência do histórico de calibração."""
import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.quant.calibration_store import (
    get_score_distribution_history,
    load_calibration_assets,
    load_calibration_runs,
    save_calibration_run,
)
from src.quant.score_comparison import compare_scores, detect_score_inflation, score_distribution_report


def _comparison_df():
    raw = pd.DataFrame(
        [
            {
                "captured_at": "2026-05-10T10:00:00",
                "asset": "PETR4",
                "score": 95,
                "score_final": 88,
                "score_momentum": 90,
                "score_tendencia": 85,
                "score_liquidez": 92,
                "score_volatilidade": 80,
                "score_risco": 75,
                "signal": "COMPRA/FORÇA",
                "signal_type": "FORÇA COM LIQUIDEZ",
                "signal_confidence": "ALTA",
                "explanation": "PETR4 aparece no radar.",
            },
            {
                "captured_at": "2026-05-10T10:00:00",
                "asset": "ITUB4",
                "score": 30,
                "score_final": 35,
                "score_momentum": 20,
                "score_tendencia": 40,
                "score_liquidez": 80,
                "score_volatilidade": 50,
                "score_risco": 60,
                "signal": "NEUTRO",
                "signal_type": "SEM ASSIMETRIA",
                "signal_confidence": "BAIXA",
                "explanation": "ITUB4 aparece no radar.",
            },
        ]
    )
    return compare_scores(raw)


def test_init_database_creates_calibration_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    with sqlite3.connect(db_path) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert "score_calibration_runs" in tables
    assert "score_calibration_assets" in tables


def test_save_and_load_calibration_run_and_assets(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    compared = _comparison_df()
    distribution = score_distribution_report(compared)
    inflation = detect_score_inflation(compared)

    run_id = save_calibration_run(
        compared,
        distribution,
        inflation,
        db_path,
        source="pytest",
    )

    runs = load_calibration_runs(db_path)
    assets = load_calibration_assets(db_path, run_id)
    history = get_score_distribution_history(db_path)

    assert run_id == 1
    assert len(runs) == 1
    assert runs.loc[0, "source"] == "pytest"
    assert runs.loc[0, "total_assets"] == 2
    assert len(assets) == 2
    assert set(assets["asset"]) == {"PETR4", "ITUB4"}
    assert history.loc[0, "mean_score_final"] == distribution["mean"]


def test_save_calibration_run_handles_missing_optional_columns(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    compared = compare_scores(
        pd.DataFrame(
            [
                {"asset": "A", "score": 80, "score_final": 82},
                {"asset": "B", "score": 10, "score_final": 12},
            ]
        )
    )
    distribution = score_distribution_report(compared)

    run_id = save_calibration_run(compared, distribution, distribution["inflation_alert"], db_path)
    assets = load_calibration_assets(db_path, run_id)

    assert len(assets) == 2
    assert "metadata_json" in assets.columns
    assert assets["legacy_signal"].isna().all() or (assets["legacy_signal"] == "").all()
