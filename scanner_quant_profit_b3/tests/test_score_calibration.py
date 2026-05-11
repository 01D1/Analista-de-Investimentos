import pandas as pd

from src.quant.score_calibration import (
    evaluate_score_predictiveness,
    suggest_weight_adjustments,
    suggest_weight_adjustments_oos,
)


def test_evaluate_score_predictiveness_measures_correlations_and_monotonicity():
    df = pd.DataFrame(
        {
            "score_final": [10, 30, 50, 70, 90],
            "score_momentum": [15, 35, 55, 75, 95],
            "score_tendencia": [20, 30, 40, 50, 60],
            "score_liquidez": [80, 80, 80, 80, 80],
            "score_volatilidade": [90, 70, 50, 30, 10],
            "score_risco": [30, 40, 50, 60, 70],
            "future_return_3d": [-2, -1, 0, 2, 4],
            "future_return_5d": [-3, -1, 1, 3, 5],
            "max_adverse_excursion_5d": [-5, -4, -3, -2, -1],
        }
    )

    evaluation = evaluate_score_predictiveness(df)

    assert evaluation["correlations"]["score_final"]["future_return_3d"] > 0.9
    assert evaluation["monotonicity"]["future_return_5d"]["is_monotonic_increasing"] is True
    assert not evaluation["return_by_score_quintile"].empty


def test_suggest_weight_adjustments_returns_non_binding_text():
    evaluation = {
        "correlations": {
            "score_momentum": {"future_return_3d": 0.42},
            "score_volatilidade": {"future_return_3d": -0.35},
            "score_final": {"future_return_3d": 0.2},
        },
        "monotonicity": {"future_return_3d": {"is_monotonic_increasing": False}},
    }

    text = suggest_weight_adjustments(evaluation)

    assert "Sugestão" in text
    assert "momentum" in text.lower()
    assert "não altera automaticamente" in text


def test_suggest_weight_adjustments_oos_requires_train_and_test_confirmation():
    train = pd.DataFrame(
        {
            "score_liquidez": [10, 30, 60, 90],
            "score_volatilidade": [10, 30, 60, 90],
            "score_momentum": [90, 60, 30, 10],
            "score_tendencia": [20, 40, 60, 80],
            "score_risco": [80, 70, 60, 50],
            "future_return_3d": [0, 1, 2, 3],
            "future_return_5d": [0, 1, 2, 3],
        }
    )
    test = pd.DataFrame(
        {
            "score_liquidez": [15, 35, 65, 95],
            "score_volatilidade": [95, 65, 35, 15],
            "score_momentum": [10, 30, 60, 90],
            "score_tendencia": [80, 60, 40, 20],
            "score_risco": [50, 60, 70, 80],
            "future_return_3d": [0, 1, 2, 3],
            "future_return_5d": [0, 1, 2, 3],
        }
    )

    result = suggest_weight_adjustments_oos(train, test)

    assert "score_liquidez" in result
    assert "treino e no teste" in result
    assert "não altera automaticamente" in result
