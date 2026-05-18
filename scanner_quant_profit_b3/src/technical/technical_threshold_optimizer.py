"""Otimização exploratória de thresholds técnicos.

Os resultados são sugestões para estudo. Nenhum threshold é aplicado ao scanner
principal automaticamente.
"""
from __future__ import annotations

import itertools
import json

import pandas as pd


RETURN_COLS = {
    "mean_return_1d": "future_return_1d",
    "mean_return_3d": "future_return_3d",
    "mean_return_5d": "future_return_5d",
    "mean_return_10d": "future_return_10d",
}


def _default_grid(backtest_df: pd.DataFrame) -> dict:
    setup_types = sorted(backtest_df.get("setup_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    directions = sorted(backtest_df.get("setup_direction", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    return {
        "min_technical_score": [0, 60, 70],
        "min_setup_score": [0, 60, 70],
        "min_setup_confidence": [0, 0.5],
        "allowed_setup_types": [None] + setup_types[:6],
        "allowed_directions": [None] + directions[:3],
        "max_volatility_score": [None],
        "min_volume_score": [0, 40],
        "min_trend_score": [0, 50],
        "min_momentum_score": [0, 50],
    }


def _as_list(value) -> list:
    if value is None:
        return [None]
    if isinstance(value, list):
        return value
    return [value]


def apply_technical_thresholds(backtest_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    if backtest_df.empty:
        return backtest_df.copy()
    df = backtest_df.copy()
    mask = pd.Series(True, index=df.index)
    checks = [
        ("technical_score_final", "min_technical_score", ">="),
        ("setup_score", "min_setup_score", ">="),
        ("setup_confidence", "min_setup_confidence", ">="),
        ("volatility_score", "max_volatility_score", "<="),
        ("volume_score", "min_volume_score", ">="),
        ("trend_score", "min_trend_score", ">="),
        ("momentum_score", "min_momentum_score", ">="),
    ]
    for col, param, op in checks:
        threshold = params.get(param)
        if threshold is None or col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        mask &= values <= float(threshold) if op == "<=" else values >= float(threshold)
    setup_type = params.get("allowed_setup_types")
    if setup_type and "setup_type" in df.columns:
        allowed = setup_type if isinstance(setup_type, list) else [setup_type]
        mask &= df["setup_type"].astype(str).isin([str(x) for x in allowed])
    direction = params.get("allowed_directions")
    if direction and "setup_direction" in df.columns:
        allowed = direction if isinstance(direction, list) else [direction]
        mask &= df["setup_direction"].astype(str).isin([str(x) for x in allowed])
    return df[mask].copy()


def _metrics(df: pd.DataFrame, params: dict, min_samples: int) -> dict:
    ret5 = pd.to_numeric(df.get("future_return_5d"), errors="coerce")
    gains = ret5[ret5 > 0]
    losses = ret5[ret5 < 0].abs()
    row = {
        "params_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
        "signals_count": int(len(df)),
        "hit_rate_5d": round(float((ret5.dropna() > 0).mean()) * 100, 2) if ret5.notna().any() else 0.0,
        "payoff": round(float(gains.mean() / losses.mean()), 4) if not gains.empty and not losses.empty and losses.mean() else 0.0,
        "sample_warning": int(len(df) < min_samples),
        "overfitting_risk_hint": "AMOSTRA_PEQUENA" if len(df) < min_samples else "OK",
    }
    for metric, col in RETURN_COLS.items():
        ret = pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(dtype=float)
        row[metric] = round(float(ret.mean()), 4) if ret.notna().any() else 0.0
    if not df.empty and "ticker" in df.columns:
        row["concentration_top_asset_pct"] = round(float(df["ticker"].value_counts(normalize=True).iloc[0] * 100), 2)
        if row["concentration_top_asset_pct"] > 50:
            row["overfitting_risk_hint"] = "CONCENTRACAO_ELEVADA"
    else:
        row["concentration_top_asset_pct"] = 0.0
    return row


def grid_search_technical_thresholds(
    backtest_df: pd.DataFrame,
    param_grid: dict | None = None,
    objective: str = "mean_return_5d",
    min_samples: int = 100,
) -> pd.DataFrame:
    columns = [
        "params_json",
        "signals_count",
        "mean_return_1d",
        "mean_return_3d",
        "mean_return_5d",
        "mean_return_10d",
        "hit_rate_5d",
        "payoff",
        "concentration_top_asset_pct",
        "sample_warning",
        "overfitting_risk_hint",
    ]
    if backtest_df.empty:
        return pd.DataFrame(columns=columns)
    grid = param_grid or _default_grid(backtest_df)
    keys = list(grid.keys())
    rows = []
    for values in itertools.product(*[_as_list(grid[k]) for k in keys]):
        params = dict(zip(keys, values))
        filtered = apply_technical_thresholds(backtest_df, params)
        rows.append(_metrics(filtered, params, min_samples))
    return pd.DataFrame(rows, columns=columns)


def rank_technical_threshold_results(results_df: pd.DataFrame, objective: str = "mean_return_5d") -> pd.DataFrame:
    if results_df.empty:
        return results_df.copy()
    out = results_df.copy()
    if objective not in out.columns:
        objective = "mean_return_5d"
    out["_risk_order"] = out["overfitting_risk_hint"].map({"OK": 0, "CONCENTRACAO_ELEVADA": 1, "AMOSTRA_PEQUENA": 2}).fillna(3)
    return (
        out.sort_values(["sample_warning", "_risk_order", objective, "hit_rate_5d", "signals_count"], ascending=[True, True, False, False, False])
        .drop(columns=["_risk_order"])
        .reset_index(drop=True)
    )


def generate_technical_threshold_report(results_df: pd.DataFrame) -> str:
    if results_df.empty:
        return "Nenhum threshold técnico foi testado por falta de dados."
    best = rank_technical_threshold_results(results_df).iloc[0]
    return (
        f"A melhor configuração exploratória gerou {int(best['signals_count'])} sinais, "
        f"retorno médio D+5 de {best['mean_return_5d']}% e hit rate de {best['hit_rate_5d']}%. "
        "Essa configuração é apenas candidata a estudo e não é aplicada automaticamente."
    )
