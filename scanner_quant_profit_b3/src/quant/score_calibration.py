"""Avaliacao estatistica para calibrar pesos do score_final sem altera-los."""
from __future__ import annotations

import numpy as np
import pandas as pd


COMPONENTS = [
    "score_final",
    "score_momentum",
    "score_tendencia",
    "score_liquidez",
    "score_volatilidade",
    "score_risco",
]


def _corr(x: pd.Series, y: pd.Series) -> float:
    data = pd.concat([pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")], axis=1).dropna()
    if len(data) < 3 or data.iloc[:, 0].nunique() < 2 or data.iloc[:, 1].nunique() < 2:
        return 0.0
    return round(float(data.iloc[:, 0].corr(data.iloc[:, 1])), 4)


def _return_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if col.startswith("future_return_")]


def evaluate_score_predictiveness(backtest_df: pd.DataFrame) -> dict:
    if backtest_df is None or backtest_df.empty:
        return {
            "correlations": {},
            "return_by_score_quintile": pd.DataFrame(),
            "monotonicity": {},
            "risk_penalty": {},
            "sample_size": 0,
        }

    df = backtest_df.copy()
    returns = _return_columns(df)
    correlations: dict[str, dict[str, float]] = {}
    for component in COMPONENTS:
        if component not in df.columns:
            continue
        correlations[component] = {ret: _corr(df[component], df[ret]) for ret in returns}

    quintile_rows = []
    if "score_final" in df.columns and pd.to_numeric(df["score_final"], errors="coerce").dropna().nunique() >= 2:
        labels = [f"Q{i}" for i in range(1, 6)]
        df["score_quintile"] = pd.qcut(
            pd.to_numeric(df["score_final"], errors="coerce").rank(method="first"),
            q=5,
            labels=labels,
            duplicates="drop",
        )
        for quintile, group in df.groupby("score_quintile", observed=False):
            row = {"score_quintile": str(quintile), "signals": int(len(group))}
            for ret in returns:
                row[f"mean_{ret}"] = round(float(pd.to_numeric(group[ret], errors="coerce").mean()), 4)
            quintile_rows.append(row)
    quintile_df = pd.DataFrame(quintile_rows)

    monotonicity = {}
    for ret in returns:
        col = f"mean_{ret}"
        if not quintile_df.empty and col in quintile_df.columns:
            values = pd.to_numeric(quintile_df[col], errors="coerce").dropna().tolist()
            monotonicity[ret] = {
                "is_monotonic_increasing": bool(all(b >= a for a, b in zip(values, values[1:]))),
                "spread_top_bottom": round(float(values[-1] - values[0]), 4) if len(values) >= 2 else 0.0,
            }

    risk_penalty = {}
    if "score_risco" in df.columns and "max_adverse_excursion_5d" in df.columns:
        risk_penalty["score_risco_vs_mae_5d_corr"] = _corr(df["score_risco"], df["max_adverse_excursion_5d"])

    return {
        "correlations": correlations,
        "return_by_score_quintile": quintile_df,
        "monotonicity": monotonicity,
        "risk_penalty": risk_penalty,
        "sample_size": int(len(df)),
    }


def suggest_weight_adjustments(evaluation: dict) -> str:
    correlations = evaluation.get("correlations", {}) if evaluation else {}
    target = "future_return_3d"
    component_scores = {
        component: values.get(target, 0.0)
        for component, values in correlations.items()
        if component != "score_final"
    }
    if not component_scores:
        return "Sugestão: amostra insuficiente para calibrar pesos; não altera automaticamente os pesos."

    best = max(component_scores, key=lambda key: component_scores[key])
    worst = min(component_scores, key=lambda key: component_scores[key])
    pieces = [
        f"Sugestão: {best.replace('score_', '')} apresentou a maior relação com retorno D+3.",
    ]
    if component_scores[worst] < 0:
        pieces.append(
            f"{worst.replace('score_', '')} apresentou relação negativa e merece revisão de peso."
        )

    monotonic = evaluation.get("monotonicity", {}).get(target, {})
    if monotonic and not monotonic.get("is_monotonic_increasing", False):
        pieces.append("O score_final ainda não mostrou monotonicidade clara por quintil.")
    else:
        pieces.append("O score_final mostrou monotonicidade inicial, sujeito ao tamanho da amostra.")

    pieces.append("Esta análise não altera automaticamente os pesos; ela apenas orienta nova validação.")
    return " ".join(pieces)


def _stable_corr(train_df: pd.DataFrame, test_df: pd.DataFrame, component: str, ret_col: str) -> tuple[float, float]:
    if component not in train_df.columns or component not in test_df.columns:
        return 0.0, 0.0
    if ret_col not in train_df.columns or ret_col not in test_df.columns:
        return 0.0, 0.0
    train_corr = _corr(train_df[component], train_df[ret_col])
    test_corr = _corr(test_df[component], test_df[ret_col])
    return train_corr, test_corr


def suggest_weight_adjustments_oos(train_df: pd.DataFrame, test_df: pd.DataFrame) -> str:
    """Sugere ajustes apenas quando a relacao aparece no treino e no teste."""
    if train_df is None or test_df is None or train_df.empty or test_df.empty:
        return "Sugestão OOS: amostra insuficiente; não altera automaticamente os pesos."

    components = [c for c in COMPONENTS if c != "score_final"]
    stable_positive = []
    unstable = []
    negative = []

    for component in components:
        c3_train, c3_test = _stable_corr(train_df, test_df, component, "future_return_3d")
        c5_train, c5_test = _stable_corr(train_df, test_df, component, "future_return_5d")
        if c3_train > 0 and c3_test > 0 and c5_train > 0 and c5_test > 0:
            stable_positive.append((component, c3_train, c3_test, c5_train, c5_test))
        elif (c3_train > 0 or c5_train > 0) and (c3_test <= 0 or c5_test <= 0):
            unstable.append((component, c3_train, c3_test, c5_train, c5_test))
        elif c3_train < 0 and c3_test < 0 and c5_train < 0 and c5_test < 0:
            negative.append((component, c3_train, c3_test, c5_train, c5_test))

    parts = ["Sugestão OOS:"]
    if stable_positive:
        best = max(stable_positive, key=lambda item: item[1] + item[2] + item[3] + item[4])
        parts.append(
            f"{best[0]} apresentou relação positiva com retorno D+3 no treino e no teste, "
            "sugerindo manutenção ou leve aumento de peso em nova validação."
        )
    else:
        parts.append("nenhum componente confirmou relação positiva simultânea no treino e no teste.")

    if unstable:
        names = ", ".join(item[0] for item in unstable[:3])
        parts.append(f"{names} funcionou no treino, mas perdeu força fora da amostra; sugere cautela.")

    if negative:
        names = ", ".join(item[0] for item in negative[:3])
        parts.append(f"{names} apresentou relação negativa persistente e merece revisão.")

    parts.append("Esta análise não altera automaticamente os pesos; ela apenas orienta testes futuros.")
    return " ".join(parts)
