import pandas as pd

from src.quant.market_regimes import (
    assign_regimes_to_backtest,
    build_market_proxy_from_universe,
    calculate_market_regime_features,
    classify_market_regime,
)


def _prices():
    rows = []
    for i in range(1, 41):
        for ticker, offset in [("AAA", 0), ("BBB", 1)]:
            close = 10 + i * 0.2 + offset
            rows.append(
                {
                    "trade_date": f"2026-01-{i:02d}" if i <= 31 else f"2026-02-{i-31:02d}",
                    "ticker": ticker,
                    "open": close - 0.1,
                    "high": close + 0.2,
                    "low": close - 0.2,
                    "close": close,
                    "volume": 1_000_000 + i * 10_000,
                }
            )
    return pd.DataFrame(rows)


def test_build_market_proxy_from_universe_creates_breadth_and_volume():
    proxy = build_market_proxy_from_universe(_prices())

    assert {"market_return_mean", "pct_assets_positive", "total_volume", "market_breadth"}.issubset(proxy.columns)
    assert proxy["total_volume"].iloc[-1] > 0
    assert proxy["pct_assets_positive"].iloc[-1] >= 0


def test_classify_market_regime_variants():
    alta = classify_market_regime(
        {"return_20d": 5, "trend_strength": 4, "volatility_20d": 1, "volatility_60d": 1.5, "volume_relative_20d": 1.2, "drawdown_20d": -2}
    )
    baixa = classify_market_regime(
        {"return_20d": -6, "trend_strength": -4, "volatility_20d": 1, "volatility_60d": 1.5, "volume_relative_20d": 1.0, "drawdown_20d": -8}
    )
    lateral = classify_market_regime(
        {"return_20d": 0.2, "trend_strength": 0.1, "volatility_20d": 1, "volatility_60d": 1.0, "volume_relative_20d": 1.0, "drawdown_20d": -1}
    )
    vol = classify_market_regime(
        {"return_20d": 1, "trend_strength": 0.5, "volatility_20d": 4, "volatility_60d": 2, "volume_relative_20d": 1.0, "drawdown_20d": -3}
    )

    assert alta["trend_regime"] == "ALTA_TENDENCIAL"
    assert baixa["trend_regime"] == "BAIXA_TENDENCIAL"
    assert lateral["trend_regime"] == "LATERAL"
    assert vol["volatility_regime"] == "ALTA_VOLATILIDADE"


def test_calculate_features_and_assign_regimes_to_backtest():
    proxy = build_market_proxy_from_universe(_prices())
    regimes = calculate_market_regime_features(proxy)
    backtest = pd.DataFrame(
        {
            "trade_date": [regimes["trade_date"].iloc[-1]],
            "ticker": ["AAA"],
            "net_return_5d": [0.2],
        }
    )
    assigned = assign_regimes_to_backtest(backtest, regimes)

    assert "primary_regime" in regimes.columns
    assert "regime_confidence" in regimes.columns
    assert assigned.loc[0, "primary_regime"] in regimes["primary_regime"].dropna().unique()
