"""Testes do backtest estatístico de calibração."""
import pandas as pd

from src.quant.calibration_backtest import (
    calculate_forward_returns,
    generate_calibration_report,
    summarize_by_divergence,
    summarize_by_score_bucket,
)


def _signals():
    return pd.DataFrame(
        [
            {
                "signal_id": 1,
                "captured_at": "2026-01-01",
                "asset": "PETR4",
                "score_final": 85,
                "divergence_type": "CONVERGENTE_FORTE",
            },
            {
                "signal_id": 2,
                "captured_at": "2026-01-01",
                "asset": "ITUB4",
                "score_final": 35,
                "divergence_type": "CONVERGENTE_FRACO",
            },
        ]
    )


def _prices():
    rows = []
    petr = [10, 11, 10.5, 12, 11.5, 13]
    itub = [20, 19, 18, 18.5, 17, 16]
    for i, date in enumerate(pd.date_range("2026-01-01", periods=6, freq="D")):
        rows.append({"trade_date": date, "ticker": "PETR4", "close": petr[i]})
        rows.append({"trade_date": date, "ticker": "ITUB4", "close": itub[i]})
    return pd.DataFrame(rows)


def test_calculate_forward_returns_handles_horizons_and_missing_data():
    out = calculate_forward_returns(_signals(), _prices(), horizons=[1, 3, 5, 10])

    assert set(out["horizon"]) == {1, 3, 5}
    petr_d3 = out[(out["asset"] == "PETR4") & (out["horizon"] == 3)].iloc[0]
    assert petr_d3["future_return"] == 20.0
    assert bool(petr_d3["hit"]) is True
    assert petr_d3["max_favorable_excursion"] == 20.0


def test_summarize_by_divergence_returns_wide_statistics():
    bt = calculate_forward_returns(_signals(), _prices(), horizons=[1, 3, 5])
    summary = summarize_by_divergence(bt)

    row = summary[summary["divergence_type"] == "CONVERGENTE_FORTE"].iloc[0]
    assert row["signals"] == 1
    assert row["mean_return_d1"] == 10.0
    assert row["mean_return_d3"] == 20.0
    assert row["hit_rate_d5"] == 1.0


def test_summarize_by_score_bucket_groups_by_score_range():
    bt = calculate_forward_returns(_signals(), _prices(), horizons=[1, 3])
    summary = summarize_by_score_bucket(bt)

    assert set(summary["score_bucket"]) == {"20_40", "80_100"}
    high = summary[summary["score_bucket"] == "80_100"].iloc[0]
    assert high["mean_return_d1"] == 10.0


def test_generate_calibration_report_without_and_with_backtest():
    history = pd.DataFrame(
        [
            {
                "total_assets": 42,
                "mean_score_final": 61.3,
                "count_80_100": 9,
                "inflation_alert": 0,
                "inflation_message": "Distribuição de score sem alerta de inflação.",
            }
        ]
    )
    latest = pd.DataFrame(
        [
            {"asset": "A", "divergence_type": "CONVERGENTE_FRACO", "score_final": 35},
            {"asset": "B", "divergence_type": "CONVERGENTE_FRACO", "score_final": 30},
            {"asset": "C", "divergence_type": "CONVERGENTE_FORTE", "score_final": 85},
        ]
    )
    bt_summary = pd.DataFrame(
        [
            {"divergence_type": "CONVERGENTE_FORTE", "mean_return_d3": 2.5, "signals": 3},
            {"divergence_type": "CONVERGENTE_FRACO", "mean_return_d3": -0.5, "signals": 10},
        ]
    )

    report = generate_calibration_report(history, latest, bt_summary)

    assert "A última rodada analisou 42 ativos" in report
    assert "9 ativos acima de 80" in report
    assert "CONVERGENTE_FRACO" in report
    assert "CONVERGENTE_FORTE apresentaram melhor retorno médio em D+3" in report
