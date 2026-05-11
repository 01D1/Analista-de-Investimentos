"""Busca conservadora de thresholds para filtros de sinais."""
from __future__ import annotations

from itertools import product
from typing import Any

import pandas as pd

from .signal_filters import apply_quality_filters, summarize_filter_impact


DEFAULT_PARAM_GRID = {
    "score_final_min": [70, 80],
    "signal_confidence_min": [0.6, 0.7],
    "score_liquidez_min": [0, 70],
    "score_risco_min": [0, 50],
    "min_volume": [0, 5_000_000],
    "allowed_execution_quality": [["ACEITAVEL", "BOA", "EXCELENTE"], ["BOA", "EXCELENTE"]],
    "allowed_signal_types": [None],
}


def _normalize_param_name(name: str) -> str:
    return {
        "score_final_min": "min_score_final",
        "signal_confidence_min": "min_confidence",
        "score_liquidez_min": "min_liquidity_score",
        "score_risco_min": "min_risk_score",
        "allowed_execution_quality": "allowed_execution_quality",
    }.get(name, name)


def _iter_grid(param_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(param_grid.keys())
    values = [v if isinstance(v, list) else [v] for v in param_grid.values()]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def _mean(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float(values.mean()), 4) if not values.empty else 0.0


def _hit(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float((values > 0).mean()), 4) if not values.empty else 0.0


def _payoff(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    gains = values[values > 0]
    losses = values[values < 0].abs()
    if gains.empty or losses.empty:
        return 0.0
    return round(float(gains.mean() / losses.mean()), 4)


def _concentration(df: pd.DataFrame) -> float:
    if df is None or df.empty or "ticker" not in df.columns:
        return 0.0
    shares = df["ticker"].value_counts(normalize=True)
    return round(float(shares.iloc[0]), 4) if not shares.empty else 0.0


def params_to_filter_config(params: dict[str, Any]) -> dict[str, Any]:
    config = {
        _normalize_param_name(key): value
        for key, value in params.items()
        if value is not None
    }
    if "allowed_execution_quality" in config:
        allowed = {str(v).upper() for v in config.pop("allowed_execution_quality")}
        if "ACEITAVEL" not in allowed and "ACEITÁVEL" not in allowed:
            min_rank = min(["INVIAVEL", "RUIM", "ACEITAVEL", "BOA", "EXCELENTE"].index(q) for q in allowed)
            config["min_execution_quality"] = ["INVIAVEL", "RUIM", "ACEITAVEL", "BOA", "EXCELENTE"][min_rank]
    config.setdefault("remove_inviavel", False)
    config.setdefault("remove_ruim", False)
    config.setdefault("only_tradeable", False)
    return config


def grid_search_thresholds(
    backtest_df: pd.DataFrame,
    param_grid: dict[str, list[Any]] | None,
    objective: str = "mean_net_return_5d",
    min_samples: int = 100,
) -> pd.DataFrame:
    """Testa combinações de thresholds sem aplicá-las ao scanner principal."""
    columns = [
        "params",
        "samples",
        "sample_ok",
        "mean_net_return_1d",
        "mean_net_return_3d",
        "mean_net_return_5d",
        "mean_net_return_10d",
        "hit_rate_net_5d",
        "payoff_net_5d",
        "mean_drawdown_5d",
        "removed_pct",
        "asset_concentration",
        "best_signal_type",
        "best_score_bucket",
        "objective_value",
    ]
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for params in _iter_grid(param_grid or DEFAULT_PARAM_GRID):
        config = params_to_filter_config(params)
        filtered = apply_quality_filters(backtest_df, config)
        impact = summarize_filter_impact(backtest_df, filtered)
        row = {
            "params": params,
            "samples": int(len(filtered)),
            "sample_ok": bool(len(filtered) >= min_samples),
            "mean_net_return_1d": _mean(filtered, "net_return_1d"),
            "mean_net_return_3d": _mean(filtered, "net_return_3d"),
            "mean_net_return_5d": _mean(filtered, "net_return_5d"),
            "mean_net_return_10d": _mean(filtered, "net_return_10d"),
            "hit_rate_net_5d": _hit(filtered, "net_return_5d"),
            "payoff_net_5d": _payoff(filtered, "net_return_5d"),
            "mean_drawdown_5d": _mean(filtered, "mae_5d" if "mae_5d" in filtered.columns else "max_adverse_excursion_5d"),
            "removed_pct": impact.get("removed_pct", 0.0),
            "asset_concentration": _concentration(filtered),
            "best_signal_type": impact.get("best_signal_type_after", ""),
            "best_score_bucket": impact.get("best_score_bucket_after", ""),
        }
        row["objective_value"] = float(row.get(objective, 0.0))
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def rank_threshold_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """Ordena resultados priorizando amostra, retorno líquido, hit rate e baixa concentração."""
    if results_df is None or results_df.empty:
        return pd.DataFrame()
    df = results_df.copy()
    for col in ["sample_ok", "mean_net_return_5d", "hit_rate_net_5d", "mean_drawdown_5d", "asset_concentration"]:
        if col not in df.columns:
            df[col] = 0
    df["positive_net"] = pd.to_numeric(df["mean_net_return_5d"], errors="coerce").fillna(0) > 0
    return df.sort_values(
        ["sample_ok", "positive_net", "mean_net_return_5d", "hit_rate_net_5d", "mean_drawdown_5d", "asset_concentration"],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)


def generate_threshold_report(best_results_df: pd.DataFrame) -> str:
    if best_results_df is None or best_results_df.empty:
        return "Nao houve combinacoes de thresholds com dados suficientes para avaliacao."
    best = best_results_df.iloc[0]
    samples = int(best.get("samples", 0))
    net_5d = float(best.get("mean_net_return_5d", 0.0))
    hit = float(best.get("hit_rate_net_5d", 0.0))
    removed = float(best.get("removed_pct", 0.0))
    warning = " A amostra ainda é pequena, então os filtros devem ser testados fora da amostra." if not bool(best.get("sample_ok", False)) else ""
    return (
        f"Os melhores thresholds avaliados deixaram {samples} sinais, com retorno líquido médio D+5 de "
        f"{net_5d:.4f}% e hit rate de {hit:.2%}. Eles removeram {removed:.1f}% dos sinais originais."
        f"{warning} Nenhum threshold foi aplicado automaticamente ao ranking principal."
    )
