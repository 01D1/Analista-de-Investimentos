"""Testes do núcleo quantitativo puro."""
import pandas as pd

from src.quant.backtest import evaluate_forward_returns
from src.quant.explanations import explain_signal
from src.quant.liquidity import liquidity_profile
from src.quant.metrics import intraday_metrics, pct_change
from src.quant.options_metrics import option_metrics
from src.quant.regimes import classify_market_regime
from src.quant.relative_strength import relative_strength
from src.quant.scoring import score_asset
from src.quant.signals import classify_asset_signal


def test_intraday_metrics_handles_zero_division_and_range_position():
    metrics = intraday_metrics(
        {
            "last": 10.0,
            "open": 9.5,
            "high": 10.0,
            "low": 9.0,
            "prev_close": 9.0,
        }
    )

    assert metrics["range_pct"] == 11.1111
    assert metrics["position_range_pct"] == 100.0
    assert metrics["gap_pct"] == 5.5556
    assert metrics["last_vs_open_pct"] == 5.2632
    assert pct_change(10, 0, default=0.0) == 0.0


def test_liquidity_profile_scores_relative_volume_and_spread_penalty():
    result = liquidity_profile(
        volume=180_000_000,
        trades=25_000,
        avg_volume=60_000_000,
        avg_trades=10_000,
        spread_pct=0.15,
        min_volume=50_000_000,
        min_trades=1_000,
    )

    assert result["passes_minimum"] is True
    assert result["volume_ratio"] == 3.0
    assert result["trades_ratio"] == 2.5
    assert result["liquidity_score"] >= 90


def test_score_asset_returns_component_scores_and_risk_penalty():
    metrics = {
        "variation_pct": 2.0,
        "last_vs_open_pct": 1.2,
        "last_vs_prev_close_pct": 2.0,
        "position_range_pct": 92.0,
        "range_pct": 9.0,
        "gap_pct": 4.5,
    }
    liquidity = {"liquidity_score": 90, "volume_ratio": 2.2, "passes_minimum": True}
    trend = {"price_above_fast_ma": True, "price_above_slow_ma": True, "fast_ma_above_slow_ma": True}

    result = score_asset(metrics=metrics, liquidity=liquidity, trend=trend)

    assert result["score_momentum"] >= 80
    assert result["score_tendencia"] == 100
    assert result["score_risco"] < 100
    assert 0 <= result["score_final"] <= 100
    assert result["score_final"] >= 70


def test_signal_classification_distinguishes_breakout_and_pullback_risk():
    breakout = classify_asset_signal(
        {
            "score_final": 88,
            "score_liquidez": 95,
            "score_momentum": 90,
            "score_risco": 80,
            "metrics": {"position_range_pct": 96, "range_pct": 3.0},
            "liquidity": {"volume_ratio": 2.1},
        }
    )
    stretched = classify_asset_signal(
        {
            "score_final": 68,
            "score_liquidez": 80,
            "score_momentum": 90,
            "score_risco": 35,
            "metrics": {"position_range_pct": 98, "range_pct": 11.0},
            "liquidity": {"volume_ratio": 1.1},
        }
    )

    assert breakout["signal_type"] == "ROMPIMENTO COM VOLUME"
    assert stretched["signal_type"] == "ESTICADO / RISCO DE PULLBACK"


def test_option_metrics_calculates_moneyness_intrinsic_and_extrinsic():
    result = option_metrics(
        underlying_price=42.0,
        option_price=3.2,
        strike=40.0,
        option_type="CALL",
        trade_date="2026-05-04",
        expiration_date="2026-06-20",
        bid=3.15,
        ask=3.25,
        volume=500_000,
        trades=120,
    )

    assert result["moneyness"] == "ITM"
    assert result["intrinsic_value"] == 2.0
    assert result["extrinsic_value"] == 1.2
    assert result["days_to_maturity"] == 47
    assert result["spread_pct"] == 3.125
    assert result["liquidity_score"] > 0


def test_backtest_forward_returns_reports_horizons_and_excursions():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=6, freq="D"),
            "ticker": ["PETR4"] * 6,
            "close": [10, 11, 10.5, 12, 9.5, 13],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_id": [1],
            "ticker": ["PETR4"],
            "signal_date": ["2026-01-01"],
            "entry_price": [10.0],
            "score_final": [80],
            "signal_type": ["ROMPIMENTO COM VOLUME"],
        }
    )

    result = evaluate_forward_returns(prices, signals, horizons=(1, 3, 5))

    assert result["horizon"].tolist() == [1, 3, 5]
    assert result.loc[result["horizon"] == 1, "future_return"].iloc[0] == 10.0
    assert result.loc[result["horizon"] == 3, "max_favorable_excursion"].iloc[0] == 20.0
    assert result.loc[result["horizon"] == 5, "max_adverse_excursion"].iloc[0] == -5.0


def test_regime_relative_strength_and_explanation_are_deterministic():
    close = pd.Series([10, 10.2, 10.5, 10.8, 11.0, 11.4, 11.8, 12.0])
    regime = classify_market_regime(close, short_window=3, long_window=5)
    rs = relative_strength(asset_return=0.08, benchmark_return=0.03)
    text = explain_signal(
        ticker="PETR4",
        signal_type="ROMPIMENTO COM VOLUME",
        metrics={"position_range_pct": 92, "variation_pct": 2.0},
        liquidity={"volume_ratio": 2.3},
        risks=["gap elevado"],
    )

    assert regime["trend_regime"] == "TENDENCIA_DE_ALTA"
    assert rs["relative_return"] == 5.0
    assert "PETR4 aparece no radar" in text
    assert "gap elevado" in text
