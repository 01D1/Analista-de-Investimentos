import pandas as pd

from src.quant.historical_signals import generate_historical_features, generate_historical_scores


def _prices():
    rows = []
    closes = [10, 10.5, 10.2, 10.8, 11.4, 11.7, 12.0, 12.4, 12.1, 12.8]
    volumes = [1000, 1100, 900, 1300, 1800, 1600, 2000, 2400, 2200, 2600]
    for i, date in enumerate(pd.date_range("2026-01-01", periods=len(closes), freq="D")):
        rows.append(
            {
                "trade_date": date.strftime("%Y-%m-%d"),
                "ticker": "PETR4",
                "open": closes[i] - 0.2,
                "high": closes[i] + 0.4,
                "low": closes[i] - 0.5,
                "close": closes[i],
                "volume": volumes[i],
                "trades": 100 + i,
                "quantity": 1000 + i,
            }
        )
    return pd.DataFrame(rows)


def test_generate_historical_features_calculates_daily_indicators():
    features = generate_historical_features(_prices())

    last = features.iloc[-1]
    assert "return_1d" in features.columns
    assert "volume_relative_20" in features.columns
    assert "atr_14" in features.columns
    assert round(float(last["return_3d"]), 4) == 6.6667
    assert float(last["moving_average_9"]) > 0
    assert float(last["volume_relative_20"]) > 1.0
    assert last["trend_short"] in {"ALTA", "BAIXA", "NEUTRA"}


def test_generate_historical_scores_adds_score_components_signal_and_explanation():
    features = generate_historical_features(_prices())
    scored = generate_historical_scores(features)

    last = scored.iloc[-1]
    assert set(scored.columns) >= {
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
    assert 0 <= float(last["score_final"]) <= 100
    assert isinstance(last["signal_type"], str)
    assert "PETR4 aparece no radar" in last["explanation"]
