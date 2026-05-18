import pandas as pd

from src.technical.setup_deduplication import deduplicate_setups


def test_deduplicate_setups_keeps_best_by_group():
    df = pd.DataFrame(
        [
            {"trade_date": "2026-01-02", "ticker": "PETR4", "setup_direction": "BULLISH", "setup_type": "BREAKOUT_VOLUME", "setup_score": 80, "setup_confidence": 0.7},
            {"trade_date": "2026-01-02", "ticker": "PETR4", "setup_direction": "BULLISH", "setup_type": "MOMENTUM_CONTINUATION", "setup_score": 70, "setup_confidence": 0.9},
            {"trade_date": "2026-01-02", "ticker": "PETR4", "setup_direction": "BULLISH", "setup_type": "MEAN_REVERSION", "setup_score": 60, "setup_confidence": 0.6},
        ]
    )
    deduped, removed, summary = deduplicate_setups(df)
    assert len(deduped) == 2
    assert len(removed) == 1
    assert summary["removed_pct"] > 0

