"""Walk-forward fora da amostra para setups técnicos."""
from __future__ import annotations

import json

import pandas as pd

from src.technical.technical_threshold_optimizer import apply_technical_thresholds, grid_search_technical_thresholds, rank_technical_threshold_results


RESULT_COLUMNS = [
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "setup_type",
    "best_params_json",
    "train_signals",
    "test_signals",
    "train_mean_return",
    "test_mean_return",
    "train_hit_rate",
    "test_hit_rate",
    "test_positive",
    "overfitting_flag",
    "insufficient_data_flag",
    "concentration_warning",
    "stability_warning",
    "metadata_json",
]


def create_technical_walk_forward_windows(start_date, end_date, train_months: int = 3, test_months: int = 1) -> pd.DataFrame:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    rows = []
    current = start
    window_id = 1
    while True:
        train_start = current
        train_end = train_start + pd.DateOffset(months=train_months) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = test_start + pd.DateOffset(months=test_months) - pd.Timedelta(days=1)
        if test_start > end:
            break
        rows.append(
            {
                "window_id": window_id,
                "train_start": train_start.date().isoformat(),
                "train_end": min(train_end, end).date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": min(test_end, end).date().isoformat(),
            }
        )
        current = current + pd.DateOffset(months=test_months)
        window_id += 1
        if test_end >= end:
            break
    return pd.DataFrame(rows)


def _date_filter(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if df.empty or "trade_date" not in df.columns:
        return df.iloc[0:0].copy()
    dates = pd.to_datetime(df["trade_date"], errors="coerce")
    return df[(dates >= pd.to_datetime(start)) & (dates <= pd.to_datetime(end))].copy()


def _metrics(df: pd.DataFrame) -> tuple[float, float]:
    ret = pd.to_numeric(df.get("future_return_5d"), errors="coerce")
    mean = round(float(ret.mean()), 4) if ret.notna().any() else 0.0
    hit = round(float((ret.dropna() > 0).mean()) * 100, 2) if ret.notna().any() else 0.0
    return mean, hit


def _top_concentration(df: pd.DataFrame) -> float:
    if df.empty or "ticker" not in df.columns:
        return 0.0
    return round(float(df["ticker"].value_counts(normalize=True).iloc[0] * 100), 2)


def _stability_warning(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    for col in ["primary_regime", "event_context_type"]:
        if col in df.columns and df[col].dropna().nunique() <= 1 and len(df) >= 10:
            return 1
    return 0


def run_technical_walk_forward(
    features_df: pd.DataFrame,
    setups_df: pd.DataFrame,
    backtest_df: pd.DataFrame,
    train_months: int = 3,
    test_months: int = 1,
    objective: str = "mean_return_5d",
    min_samples_train: int = 100,
    min_samples_test: int = 30,
) -> pd.DataFrame:
    if backtest_df.empty or "trade_date" not in backtest_df.columns:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    dates = pd.to_datetime(backtest_df["trade_date"], errors="coerce").dropna()
    if dates.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    windows = create_technical_walk_forward_windows(dates.min(), dates.max(), train_months, test_months)
    rows = []
    for _, window in windows.iterrows():
        train = _date_filter(backtest_df, window["train_start"], window["train_end"])
        test = _date_filter(backtest_df, window["test_start"], window["test_end"])
        if len(train) < min_samples_train:
            rows.append({**window.to_dict(), "setup_type": None, "best_params_json": "{}", "train_signals": len(train), "test_signals": 0, "train_mean_return": 0.0, "test_mean_return": 0.0, "train_hit_rate": 0.0, "test_hit_rate": 0.0, "test_positive": 0, "overfitting_flag": 0, "insufficient_data_flag": 1, "concentration_warning": 0, "stability_warning": 0, "metadata_json": "{}"})
            continue
        ranked = rank_technical_threshold_results(grid_search_technical_thresholds(train, objective=objective, min_samples=min_samples_train), objective)
        if ranked.empty:
            rows.append({**window.to_dict(), "setup_type": None, "best_params_json": "{}", "train_signals": len(train), "test_signals": 0, "train_mean_return": 0.0, "test_mean_return": 0.0, "train_hit_rate": 0.0, "test_hit_rate": 0.0, "test_positive": 0, "overfitting_flag": 0, "insufficient_data_flag": 1, "concentration_warning": 0, "stability_warning": 0, "metadata_json": "{}"})
            continue
        params = json.loads(ranked.iloc[0]["params_json"])
        train_sel = apply_technical_thresholds(train, params)
        test_sel = apply_technical_thresholds(test, params)
        train_mean, train_hit = _metrics(train_sel)
        test_mean, test_hit = _metrics(test_sel)
        insufficient = int(len(test_sel) < min_samples_test)
        overfit = int(train_mean > 0 and test_mean < 0 and (train_mean - test_mean) > 0.5)
        concentration = _top_concentration(test_sel)
        rows.append(
            {
                **window.to_dict(),
                "setup_type": params.get("allowed_setup_types"),
                "best_params_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
                "train_signals": int(len(train_sel)),
                "test_signals": int(len(test_sel)),
                "train_mean_return": train_mean,
                "test_mean_return": test_mean,
                "train_hit_rate": train_hit,
                "test_hit_rate": test_hit,
                "test_positive": int(test_mean > 0),
                "overfitting_flag": overfit,
                "insufficient_data_flag": insufficient,
                "concentration_warning": int(concentration > 50),
                "stability_warning": _stability_warning(test_sel),
                "metadata_json": json.dumps({"top_asset_concentration_pct": concentration}, ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def summarize_technical_walk_forward(results_df: pd.DataFrame) -> dict:
    if results_df.empty:
        return {
            "windows_count": 0,
            "positive_windows_pct": 0.0,
            "mean_test_return": 0.0,
            "mean_test_hit_rate": 0.0,
            "avg_test_signals": 0.0,
            "overfitting_windows_pct": 0.0,
            "insufficient_windows_pct": 100.0,
            "robustness_class": "TECH_WF_DADOS_INSUFICIENTES",
        }
    windows = len(results_df)
    positive = pd.to_numeric(results_df["test_positive"], errors="coerce").fillna(0)
    insufficient = pd.to_numeric(results_df["insufficient_data_flag"], errors="coerce").fillna(0)
    overfit = pd.to_numeric(results_df["overfitting_flag"], errors="coerce").fillna(0)
    mean_ret = pd.to_numeric(results_df["test_mean_return"], errors="coerce").mean()
    hit = pd.to_numeric(results_df["test_hit_rate"], errors="coerce").mean()
    avg_signals = pd.to_numeric(results_df["test_signals"], errors="coerce").mean()
    pos_pct = round(float(positive.mean() * 100), 2)
    insuff_pct = round(float(insufficient.mean() * 100), 2)
    overfit_pct = round(float(overfit.mean() * 100), 2)
    if windows < 2 or insuff_pct >= 50:
        klass = "TECH_WF_DADOS_INSUFICIENTES"
    elif overfit_pct >= 40:
        klass = "TECH_WF_OVERFIT_PROVAVEL"
    elif pos_pct >= 60 and mean_ret > 0 and hit >= 52:
        klass = "TECH_WF_ROBUSTO"
    elif pos_pct >= 50 and mean_ret > 0:
        klass = "TECH_WF_PROMISSOR"
    else:
        klass = "TECH_WF_FRAGIL"
    return {
        "windows_count": int(windows),
        "positive_windows_pct": pos_pct,
        "mean_test_return": round(float(mean_ret), 4) if pd.notna(mean_ret) else 0.0,
        "mean_test_hit_rate": round(float(hit), 2) if pd.notna(hit) else 0.0,
        "avg_test_signals": round(float(avg_signals), 2) if pd.notna(avg_signals) else 0.0,
        "overfitting_windows_pct": overfit_pct,
        "insufficient_windows_pct": insuff_pct,
        "robustness_class": klass,
    }


def generate_technical_walk_forward_report(summary: dict, results_df: pd.DataFrame) -> str:
    if not summary.get("windows_count"):
        return "Walk-forward técnico sem janelas suficientes. Status: dados insuficientes."
    return (
        f"Walk-forward técnico com {summary['windows_count']} janelas: "
        f"{summary['positive_windows_pct']}% positivas, retorno médio OOS D+5 de {summary['mean_test_return']}% "
        f"e hit rate médio de {summary['mean_test_hit_rate']}%. Robustez: {summary['robustness_class']}."
    )

