import pandas as pd

from src.paper.limit_signal_source_apply import apply_limit_signal_source_variant


def test_apply_limit_signal_source_variant_limits_target_source():
    signals = pd.DataFrame({"trade_date": ["2026-01-01"] * 4, "ticker": ["A", "B", "C", "D"], "signal_source": ["quant"] * 4})
    variant = {"variant_id": "LIMIT_QUANT_ONLY", "target_source": "quant", "parameters_json": '{"action":"limit_source","keep_every_n":2}'}
    kept, removed, summary = apply_limit_signal_source_variant(signals, variant)
    assert len(kept) == 2
    assert len(removed) == 2
    assert summary["removed_pct"] == 0.5


def test_apply_limit_signal_source_variant_requires_two_sources():
    quant = pd.DataFrame({"trade_date": ["2026-01-01", "2026-01-02"], "ticker": ["PETR4", "VALE3"], "signal_source": ["quant", "quant"]})
    technical = pd.DataFrame({"trade_date": ["2026-01-01"], "ticker": ["PETR4"], "signal_source": ["technical"]})
    variant = {"variant_id": "REQUIRE_TWO_SOURCE_CONFIRMATION", "parameters_json": '{"action":"require_confirmations"}', "required_confirmations": 2}
    kept, removed, _ = apply_limit_signal_source_variant(quant, variant, context={"signals_by_source": {"quant": quant, "technical": technical}})
    assert kept["ticker"].tolist() == ["PETR4"]
    assert removed["ticker"].tolist() == ["VALE3"]

