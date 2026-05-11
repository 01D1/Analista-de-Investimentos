"""Walk-forward dos filtros de qualidade e thresholds."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pandas as pd

from .signal_filters import apply_quality_filters
from .threshold_optimizer import grid_search_thresholds, params_to_filter_config, rank_threshold_results
from .walk_forward import create_walk_forward_windows


DEFAULT_FILTER_WF_PARAM_GRID = {
    "score_final_min": [70, 80],
    "signal_confidence_min": [0.6],
    "score_liquidez_min": [0, 70],
    "score_risco_min": [0],
    "min_volume": [0, 5_000_000],
    "allowed_execution_quality": [["ACEITAVEL", "BOA", "EXCELENTE"], ["BOA", "EXCELENTE"]],
    "allowed_signal_types": [None],
}

RESULT_COLUMNS = [
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_params_json",
    "train_signals",
    "test_signals",
    "train_mean_net_return",
    "test_mean_net_return",
    "train_hit_rate",
    "test_hit_rate",
    "train_best_score_bucket",
    "test_best_score_bucket",
    "top_asset_concentration_pct",
    "top_3_assets_concentration_pct",
    "positive_test_window",
    "overfitting_flag",
    "sample_warning",
    "concentration_warning",
]


def _metric_from_objective(objective: str) -> str:
    if objective.startswith("mean_"):
        return objective.replace("mean_", "")
    return "net_return_5d"


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


def _best_bucket(df: pd.DataFrame, metric_col: str) -> str:
    if df is None or df.empty or "score_bucket" not in df.columns or metric_col not in df.columns:
        return ""
    grouped = df.groupby("score_bucket")[metric_col].mean(numeric_only=True).sort_values(ascending=False)
    return str(grouped.index[0]) if not grouped.empty else ""


def _top_concentration(df: pd.DataFrame) -> tuple[float, float]:
    if df is None or df.empty or "ticker" not in df.columns:
        return 0.0, 0.0
    shares = df["ticker"].astype(str).value_counts(normalize=True)
    top1 = round(float(shares.iloc[0] * 100.0), 4) if not shares.empty else 0.0
    top3 = round(float(shares.head(3).sum() * 100.0), 4) if not shares.empty else 0.0
    return top1, top3


def _date_filtered(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    return df[(df["_trade_date"] >= pd.to_datetime(start)) & (df["_trade_date"] <= pd.to_datetime(end))].copy()


def _empty_results() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def run_filter_walk_forward(
    backtest_df: pd.DataFrame,
    train_months: int = 1,
    test_months: int = 1,
    param_grid: dict[str, list[Any]] | None = None,
    objective: str = "mean_net_return_5d",
    min_samples_train: int = 100,
    min_samples_test: int = 30,
) -> pd.DataFrame:
    """Seleciona thresholds no treino e mede desempenho líquido no teste seguinte."""
    if backtest_df is None or backtest_df.empty:
        return _empty_results()

    df = backtest_df.copy()
    if "trade_date" not in df.columns:
        return _empty_results()
    metric_col = _metric_from_objective(objective)
    if metric_col not in df.columns:
        return _empty_results()

    df["_trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df = df.dropna(subset=["_trade_date"]).sort_values("_trade_date")
    if df.empty:
        return _empty_results()

    windows = create_walk_forward_windows(
        df["_trade_date"].min().date().isoformat(),
        df["_trade_date"].max().date().isoformat(),
        train_months=train_months,
        test_months=test_months,
    )
    rows = []
    for window in windows:
        train = _date_filtered(df, window["train_start"], window["train_end"])
        test = _date_filtered(df, window["test_start"], window["test_end"])
        if train.empty or test.empty:
            continue

        grid = grid_search_thresholds(
            train,
            param_grid or DEFAULT_FILTER_WF_PARAM_GRID,
            objective=objective,
            min_samples=min_samples_train,
        )
        ranked = rank_threshold_results(grid)
        if ranked.empty:
            continue
        eligible = ranked[ranked["sample_ok"].astype(bool)]
        best = (eligible if not eligible.empty else ranked).iloc[0]
        params = best.get("params", {}) or {}
        config = params_to_filter_config(params)
        filtered_train = apply_quality_filters(train, config)
        filtered_test = apply_quality_filters(test, config)

        train_mean = _mean(filtered_train, metric_col)
        test_mean = _mean(filtered_test, metric_col)
        train_hit = _hit(filtered_train, metric_col)
        test_hit = _hit(filtered_test, metric_col)
        top1, top3 = _top_concentration(filtered_test)
        sample_warning = len(filtered_test) < min_samples_test
        concentration_warning = top3 >= 50.0 if len(filtered_test) else True
        overfit = bool(train_mean > 0 and test_mean <= 0) or bool((train_mean - test_mean) > max(abs(train_mean) * 0.75, 0.5))

        rows.append(
            {
                **window,
                "best_params_json": json.dumps(params, ensure_ascii=False, default=str),
                "train_signals": int(len(filtered_train)),
                "test_signals": int(len(filtered_test)),
                "train_mean_net_return": train_mean,
                "test_mean_net_return": test_mean,
                "train_hit_rate": train_hit,
                "test_hit_rate": test_hit,
                "train_best_score_bucket": _best_bucket(filtered_train, metric_col),
                "test_best_score_bucket": _best_bucket(filtered_test, metric_col),
                "top_asset_concentration_pct": top1,
                "top_3_assets_concentration_pct": top3,
                "positive_test_window": bool(test_mean > 0),
                "overfitting_flag": overfit,
                "sample_warning": bool(sample_warning),
                "concentration_warning": bool(concentration_warning),
            }
        )

    out = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    for col in ["positive_test_window", "overfitting_flag", "sample_warning", "concentration_warning"]:
        if col in out.columns:
            out[col] = out[col].map(bool).astype(object)
    return out


def _most_common(series: pd.Series, limit: int = 3) -> list[str]:
    values = [str(value) for value in series.dropna().tolist() if str(value)]
    return [value for value, _ in Counter(values).most_common(limit)]


def summarize_filter_walk_forward(results_df: pd.DataFrame) -> dict[str, Any]:
    if results_df is None or results_df.empty:
        summary = {
            "windows_count": 0,
            "positive_windows_pct": 0.0,
            "mean_test_net_return": 0.0,
            "mean_test_hit_rate": 0.0,
            "avg_test_signals": 0.0,
            "insufficient_sample_windows_pct": 0.0,
            "concentration_warning_windows_pct": 0.0,
            "avg_top_3_concentration_pct": 0.0,
            "most_frequent_params": [],
            "robust_signal_types": [],
            "robust_score_buckets": [],
            "overfitting_alert": False,
        }
        summary["robustness_class"] = classify_filter_robustness(summary)
        return summary

    df = results_df.copy()
    windows = len(df)
    positive = pd.Series(df.get("positive_test_window", False)).astype(bool)
    sample_warn = pd.Series(df.get("sample_warning", False)).astype(bool)
    conc_warn = pd.Series(df.get("concentration_warning", False)).astype(bool)
    overfit = pd.Series(df.get("overfitting_flag", False)).astype(bool)
    summary = {
        "windows_count": int(windows),
        "positive_windows_pct": round(float(positive.mean() * 100.0), 4),
        "mean_test_net_return": _mean(df, "test_mean_net_return"),
        "mean_test_hit_rate": _mean(df, "test_hit_rate"),
        "avg_test_signals": round(float(pd.to_numeric(df.get("test_signals"), errors="coerce").mean()), 4),
        "insufficient_sample_windows_pct": round(float(sample_warn.mean() * 100.0), 4),
        "concentration_warning_windows_pct": round(float(conc_warn.mean() * 100.0), 4),
        "avg_top_3_concentration_pct": _mean(df, "top_3_assets_concentration_pct"),
        "most_frequent_params": _most_common(df.get("best_params_json", pd.Series(dtype=str))),
        "robust_signal_types": [],
        "robust_score_buckets": _most_common(df.get("test_best_score_bucket", pd.Series(dtype=str))),
        "overfitting_alert": bool(overfit.mean() >= 0.4 or positive.mean() < 0.4 or conc_warn.mean() >= 0.5),
    }
    summary["robustness_class"] = classify_filter_robustness(summary)
    return summary


def classify_filter_robustness(summary: dict[str, Any]) -> str:
    windows = int(summary.get("windows_count", 0) or 0)
    avg_signals = float(summary.get("avg_test_signals", 0.0) or 0.0)
    positive = float(summary.get("positive_windows_pct", 0.0) or 0.0)
    mean_ret = float(summary.get("mean_test_net_return", 0.0) or 0.0)
    hit = float(summary.get("mean_test_hit_rate", 0.0) or 0.0)
    top3 = float(summary.get("avg_top_3_concentration_pct", 0.0) or 0.0)
    overfit = bool(summary.get("overfitting_alert", False))

    if windows < 2 or avg_signals < 5:
        return "AMOSTRA_INSUFICIENTE"
    if overfit or top3 >= 70.0 or (positive < 40.0 and mean_ret < 0):
        return "OVERFIT_PROVAVEL"
    if positive >= 60.0 and mean_ret > 0 and hit > 0.50 and top3 < 50.0:
        return "ROBUSTO"
    if positive >= 50.0 and mean_ret > 0 and top3 < 65.0:
        return "PROMISSOR"
    return "FRAGIL"


def generate_filter_walk_forward_report(summary: dict[str, Any], results_df: pd.DataFrame | None = None) -> str:
    windows = int(summary.get("windows_count", 0) or 0)
    positive = float(summary.get("positive_windows_pct", 0.0) or 0.0)
    mean_ret = float(summary.get("mean_test_net_return", 0.0) or 0.0)
    hit = float(summary.get("mean_test_hit_rate", 0.0) or 0.0)
    top3 = float(summary.get("avg_top_3_concentration_pct", 0.0) or 0.0)
    robustness = summary.get("robustness_class") or classify_filter_robustness(summary)
    conclusion = "há evidência suficiente para continuar estudando os filtros" if robustness in {"ROBUSTO", "PROMISSOR"} else "a evidência ainda não é suficiente para considerar os filtros robustos"
    return (
        f"O walk-forward dos filtros gerou {windows} janelas. Os filtros foram positivos em {positive:.1f}% "
        f"das janelas. O retorno líquido médio fora da amostra foi {mean_ret:.4f}%, com hit rate médio de "
        f"{hit:.2%}. A concentração média nos 3 principais ativos foi {top3:.1f}%. "
        f"Classificação de robustez: {robustness}. Portanto, {conclusion}. "
        "Nenhum threshold foi aplicado automaticamente ao scanner."
    )


def evaluate_filter_by_regime(walk_forward_results: pd.DataFrame, backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Resume desempenho dos sinais filtrados por regime quando o backtest possui regimes."""
    columns = ["primary_regime", "signals", "mean_net_return_5d", "hit_rate_5d", "top_asset_concentration_pct", "robustness_class"]
    if backtest_df is None or backtest_df.empty or "primary_regime" not in backtest_df.columns:
        return pd.DataFrame(columns=columns)
    df = backtest_df.copy()
    if "net_return_5d" not in df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for regime, group in df.groupby("primary_regime", dropna=False):
        returns = pd.to_numeric(group["net_return_5d"], errors="coerce").dropna()
        concentration = 0.0
        if "ticker" in group.columns and not group.empty:
            concentration = float(group["ticker"].astype(str).value_counts(normalize=True).iloc[0] * 100.0)
        mean_ret = round(float(returns.mean()), 4) if not returns.empty else 0.0
        hit = round(float((returns > 0).mean() * 100.0), 4) if not returns.empty else 0.0
        robustness = "ROBUSTO" if len(group) >= 30 and mean_ret > 0 and hit >= 52 else ("PROMISSOR" if mean_ret > 0 else "FRAGIL")
        rows.append(
            {
                "primary_regime": regime,
                "signals": int(len(group)),
                "mean_net_return_5d": mean_ret,
                "hit_rate_5d": hit,
                "top_asset_concentration_pct": round(concentration, 4),
                "robustness_class": robustness,
            }
        )
    return pd.DataFrame(rows, columns=columns)
