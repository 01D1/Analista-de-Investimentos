import pandas as pd

from src.quant.event_backtest import (
    compare_event_vs_no_event,
    generate_event_context_report,
    summarize_backtest_by_event_context,
)


def _backtest():
    return pd.DataFrame(
        [
            {"ticker": "PETR4", "has_event": 1, "event_context_type": "MOVIMENTO_EVENT_DRIVEN", "event_type": "RESULTADO", "impact_direction": "POSITIVO", "future_return_5d": 1.0, "net_return_5d": 0.6, "execution_quality": "BOA", "score_final": 82},
            {"ticker": "VALE3", "has_event": 1, "event_context_type": "EVENTO_CONTRA_SINAL", "event_type": "COMMODITY", "impact_direction": "NEGATIVO", "future_return_5d": -1.0, "net_return_5d": -1.4, "execution_quality": "ACEITAVEL", "score_final": 75},
            {"ticker": "ITUB4", "has_event": 0, "event_context_type": "TECNICO_SEM_EVENTO", "event_type": "", "impact_direction": "", "future_return_5d": 0.2, "net_return_5d": -0.1, "execution_quality": "BOA", "score_final": 68},
        ]
    )


def test_summarize_backtest_by_event_context_groups_event_dimensions():
    summary = summarize_backtest_by_event_context(_backtest())

    assert {"group_type", "group_value", "signals", "mean_net_return_5d", "hit_rate_5d"}.issubset(summary.columns)
    assert "event_context_type" in summary["group_type"].tolist()
    assert "MOVIMENTO_EVENT_DRIVEN" in summary["group_value"].tolist()


def test_compare_event_vs_no_event_returns_operational_diagnostics():
    comparison = compare_event_vs_no_event(_backtest())

    assert comparison["signals_with_event"] == 2
    assert comparison["signals_without_event"] == 1
    assert comparison["mean_net_return_with_event"] == -0.4
    assert comparison["events_positive_helped"] is True


def test_generate_event_context_report_is_textual():
    report = generate_event_context_report(summarize_backtest_by_event_context(_backtest()))

    assert "amostra" in report.lower()
    assert "evento" in report.lower()
