"""
Walk-Forward Analysis — Quant Research Layer.

Divide o histórico em janelas treino/teste para medir a robustez da
estratégia fora da amostra e detectar overfitting.

Metodologia:
  - Anchored (expanding): treino cresce, teste sempre no período seguinte
  - Rolling: janela de treino fixa, deslizando no tempo

Métricas comparadas (in-sample vs out-of-sample):
  - Win rate, payoff, expectancy, Sharpe, Sortino, drawdown máx
  - Índice de robustez: OOS_sharpe / IS_sharpe (ideal ≥ 0.60)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .performance import full_summary


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardConfig:
    train_pct: float = 0.70      # % do período total para treino (anchored)
    rolling_window: int = 252    # tamanho da janela de treino (rolling), em dias
    test_window: int = 63        # tamanho da janela de teste, em dias (~1 tri)
    anchored: bool = True        # True=anchored, False=rolling
    min_trades_per_window: int = 5  # janelas com menos trades são descartadas


# ---------------------------------------------------------------------------
# Resultado de uma janela
# ---------------------------------------------------------------------------

@dataclass
class WFWindow:
    period: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_stats: dict
    test_stats: dict

    @property
    def robustness_index(self) -> float:
        """OOS Sharpe / IS Sharpe — ideal ≥ 0.60."""
        is_sharpe = self.train_stats.get("sharpe", 0)
        oos_sharpe = self.test_stats.get("sharpe", 0)
        if is_sharpe == 0:
            return 0.0
        return round(oos_sharpe / is_sharpe, 3)

    def to_dict(self) -> dict:
        row = {
            "period": self.period,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "robustness_index": self.robustness_index,
        }
        for k, v in self.train_stats.items():
            row[f"IS_{k}"] = v
        for k, v in self.test_stats.items():
            row[f"OOS_{k}"] = v
        return row


@dataclass
class WalkForwardResult:
    windows: list[WFWindow] = field(default_factory=list)
    config: WalkForwardConfig = field(default_factory=WalkForwardConfig)

    def summary_df(self) -> pd.DataFrame:
        return pd.DataFrame([w.to_dict() for w in self.windows]) if self.windows else pd.DataFrame()

    def avg_robustness(self) -> float:
        if not self.windows:
            return 0.0
        return round(np.mean([w.robustness_index for w in self.windows]), 3)

    def print_summary(self) -> None:
        df = self.summary_df()
        if df.empty:
            print("Nenhuma janela de walk-forward gerada.")
            return
        print("\n" + "=" * 80)
        print("  WALK-FORWARD ANALYSIS")
        print("=" * 80)
        cols = [
            "period", "train_start", "test_start",
            "IS_total_trades", "IS_win_rate", "IS_sharpe",
            "OOS_total_trades", "OOS_win_rate", "OOS_sharpe",
            "robustness_index",
        ]
        existing = [c for c in cols if c in df.columns]
        print(df[existing].to_string(index=False))
        ri = self.avg_robustness()
        verdict = "✅ ROBUSTO" if ri >= 0.60 else ("⚠️  MARGINAL" if ri >= 0.40 else "❌ OVERFITTING")
        print(f"\n  Índice de Robustez Médio: {ri:.3f}  →  {verdict}")
        print("=" * 80 + "\n")


# ---------------------------------------------------------------------------
# Motor de walk-forward
# ---------------------------------------------------------------------------

class WalkForwardEngine:
    """
    Walk-forward analysis sobre uma série de P&L ou sinais.

    Uso:
        wf = WalkForwardEngine(config)
        result = wf.run_on_pnl(dates, pnl_series)
        result.print_summary()
    """

    def __init__(self, config: WalkForwardConfig | None = None):
        self.cfg = config or WalkForwardConfig()

    def run_on_pnl(
        self,
        dates: pd.Series,
        pnl: pd.Series,
        capital: float = 10_000.0,
    ) -> WalkForwardResult:
        """
        Walk-forward sobre uma série de P&L (uma linha por trade).

        Args:
            dates: datas dos trades (pd.Series de strings ou datetime)
            pnl:   P&L líquido por trade (pd.Series de floats)
            capital: capital inicial para cálculo de retorno %
        """
        df = pd.DataFrame({"date": pd.to_datetime(dates), "pnl": pnl}).sort_values("date")
        df = df.dropna().reset_index(drop=True)

        if len(df) < self.cfg.min_trades_per_window * 2:
            return WalkForwardResult(config=self.cfg)

        windows_data = self._split_windows(df)
        result = WalkForwardResult(config=self.cfg)

        for period, (train_idx, test_idx) in enumerate(windows_data, start=1):
            train = df.iloc[train_idx]
            test = df.iloc[test_idx]

            if len(train) < self.cfg.min_trades_per_window:
                continue
            if len(test) < self.cfg.min_trades_per_window:
                continue

            train_stats = full_summary(train["pnl"], capital=capital)
            test_stats = full_summary(test["pnl"], capital=capital)

            window = WFWindow(
                period=period,
                train_start=str(train["date"].iloc[0].date()),
                train_end=str(train["date"].iloc[-1].date()),
                test_start=str(test["date"].iloc[0].date()),
                test_end=str(test["date"].iloc[-1].date()),
                train_stats=train_stats,
                test_stats=test_stats,
            )
            result.windows.append(window)

        return result

    def _split_windows(self, df: pd.DataFrame) -> list[tuple[list, list]]:
        n = len(df)
        windows = []

        if self.cfg.anchored:
            train_end = int(n * self.cfg.train_pct)
            test_start = train_end
            test_end = n
            test_window = self.cfg.test_window

            i = test_start
            while i < test_end:
                j = min(i + test_window, test_end)
                train_idx = list(range(0, i))
                test_idx = list(range(i, j))
                if len(train_idx) >= self.cfg.min_trades_per_window:
                    windows.append((train_idx, test_idx))
                i = j
        else:
            train_w = self.cfg.rolling_window
            test_w = self.cfg.test_window
            i = 0
            while i + train_w + test_w <= n:
                train_idx = list(range(i, i + train_w))
                test_idx = list(range(i + train_w, i + train_w + test_w))
                windows.append((train_idx, test_idx))
                i += test_w

        return windows

    def run_on_signals(
        self,
        strategy_fn: Callable[[pd.DataFrame], pd.Series],
        full_data: pd.DataFrame,
        capital: float = 10_000.0,
    ) -> WalkForwardResult:
        """Walk-forward sobre um DataFrame de dados históricos."""
        windows_data = self._split_windows(full_data)
        result = WalkForwardResult(config=self.cfg)

        for period, (train_idx, test_idx) in enumerate(windows_data, start=1):
            train_data = full_data.iloc[train_idx]
            test_data = full_data.iloc[test_idx]

            try:
                train_pnl = strategy_fn(train_data)
                test_pnl = strategy_fn(test_data)
            except Exception as e:
                print(f"  Walk-forward período {period}: erro na estratégia — {e}")
                continue

            if len(train_pnl.dropna()) < self.cfg.min_trades_per_window:
                continue
            if len(test_pnl.dropna()) < self.cfg.min_trades_per_window:
                continue

            train_dates = train_data.index
            test_dates = test_data.index

            window = WFWindow(
                period=period,
                train_start=str(train_dates[0]) if len(train_dates) > 0 else "",
                train_end=str(train_dates[-1]) if len(train_dates) > 0 else "",
                test_start=str(test_dates[0]) if len(test_dates) > 0 else "",
                test_end=str(test_dates[-1]) if len(test_dates) > 0 else "",
                train_stats=full_summary(train_pnl, capital=capital),
                test_stats=full_summary(test_pnl, capital=capital),
            )
            result.windows.append(window)

        return result


# ---------------------------------------------------------------------------
# Walk-forward estatistico para resultados do backtest historico
# ---------------------------------------------------------------------------

def create_walk_forward_windows(
    start_date: str,
    end_date: str,
    train_months: int = 12,
    test_months: int = 3,
) -> list[dict]:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    windows: list[dict] = []
    train_start = start
    window_id = 1

    while True:
        train_end = train_start + pd.DateOffset(months=train_months) - pd.DateOffset(days=1)
        test_start = train_end + pd.DateOffset(days=1)
        test_end = test_start + pd.DateOffset(months=test_months) - pd.DateOffset(days=1)
        if test_start > end:
            break
        if test_end > end:
            test_end = end
        windows.append(
            {
                "window_id": window_id,
                "train_start": train_start.date().isoformat(),
                "train_end": train_end.date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": test_end.date().isoformat(),
            }
        )
        window_id += 1
        train_start = train_start + pd.DateOffset(months=test_months)
    return windows


def _wf_return_col(horizon: int) -> str:
    return f"future_return_{int(horizon)}d"


def _group_perf(df: pd.DataFrame, group_col: str, metric_col: str) -> pd.DataFrame:
    if df.empty or group_col not in df.columns or metric_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "signals", "mean_return", "hit_rate"])
    rows = []
    for value, group in df.groupby(group_col, dropna=False):
        returns = pd.to_numeric(group[metric_col], errors="coerce").dropna()
        rows.append(
            {
                group_col: value,
                "signals": int(len(group)),
                "mean_return": round(float(returns.mean()), 4) if not returns.empty else 0.0,
                "hit_rate": round(float((returns > 0).mean()), 4) if not returns.empty else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_return", ascending=False)


def _value_perf(df: pd.DataFrame, group_col: str, value: str | None, metric_col: str) -> tuple[float, float, int]:
    if value is None or df.empty or group_col not in df.columns:
        return 0.0, 0.0, 0
    group = df[df[group_col].astype(str) == str(value)]
    returns = pd.to_numeric(group.get(metric_col), errors="coerce").dropna()
    if returns.empty:
        return 0.0, 0.0, int(len(group))
    return round(float(returns.mean()), 4), round(float((returns > 0).mean()), 4), int(len(group))


def run_walk_forward_analysis(
    backtest_df: pd.DataFrame,
    train_months: int = 12,
    test_months: int = 3,
    horizon: int = 5,
    return_prefix: str = "future_return",
    only_tradeable: bool = False,
) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame()
    df = backtest_df.copy()
    df["_trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df = df.dropna(subset=["_trade_date"]).sort_values("_trade_date")
    if only_tradeable and "is_tradeable" in df.columns:
        df = df[df["is_tradeable"].astype(bool)]
    if df.empty:
        return pd.DataFrame()

    metric_col = f"{return_prefix}_{int(horizon)}d"
    if metric_col not in df.columns:
        metric_col = _wf_return_col(horizon)
    start = df["_trade_date"].min().date().isoformat()
    end = df["_trade_date"].max().date().isoformat()
    windows = create_walk_forward_windows(start, end, train_months=train_months, test_months=test_months)
    rows = []
    for window in windows:
        train = df[(df["_trade_date"] >= pd.to_datetime(window["train_start"])) & (df["_trade_date"] <= pd.to_datetime(window["train_end"]))]
        test = df[(df["_trade_date"] >= pd.to_datetime(window["test_start"])) & (df["_trade_date"] <= pd.to_datetime(window["test_end"]))]
        if train.empty or test.empty:
            continue

        signal_perf = _group_perf(train, "signal_type", metric_col)
        bucket_perf = _group_perf(train, "score_bucket", metric_col)
        best_signal = str(signal_perf.iloc[0]["signal_type"]) if not signal_perf.empty else None
        best_bucket = str(bucket_perf.iloc[0]["score_bucket"]) if not bucket_perf.empty else None
        train_signal_return = float(signal_perf.iloc[0]["mean_return"]) if not signal_perf.empty else 0.0
        train_bucket_return = float(bucket_perf.iloc[0]["mean_return"]) if not bucket_perf.empty else 0.0
        test_signal_return, test_signal_hit, test_signal_n = _value_perf(test, "signal_type", best_signal, metric_col)
        test_bucket_return, test_bucket_hit, test_bucket_n = _value_perf(test, "score_bucket", best_bucket, metric_col)
        test_returns = pd.to_numeric(test.get(metric_col), errors="coerce").dropna()
        mean_test_return = round(float(test_returns.mean()), 4) if not test_returns.empty else 0.0
        mean_test_hit = round(float((test_returns > 0).mean()), 4) if not test_returns.empty else 0.0
        degradation = round(float(train_signal_return - test_signal_return), 4)
        overfit = bool(train_signal_return > 0 and test_signal_return < 0)
        rows.append(
            {
                **window,
                "train_signals": int(len(train)),
                "test_signals": int(len(test)),
                "best_train_signal_type": best_signal,
                "train_return_best_signal": round(train_signal_return, 4),
                "test_return_best_signal": test_signal_return,
                "test_hit_rate_best_signal": test_signal_hit,
                "test_signals_best_signal": test_signal_n,
                "best_train_score_bucket": best_bucket,
                "train_return_best_bucket": round(train_bucket_return, 4),
                "test_return_best_bucket": test_bucket_return,
                "test_hit_rate_best_bucket": test_bucket_hit,
                "test_signals_best_bucket": test_bucket_n,
                "mean_test_return": mean_test_return,
                "mean_test_hit_rate": mean_test_hit,
                "score_stability": round(float(pd.to_numeric(test.get("score_final"), errors="coerce").std(ddof=0) or 0.0), 4),
                "degradation_score": degradation,
                "overfitting_flag": overfit,
                "return_mode": return_prefix,
            }
        )
    return pd.DataFrame(rows)


def summarize_walk_forward_results(walk_df: pd.DataFrame) -> dict:
    if walk_df is None or walk_df.empty:
        return {
            "windows_count": 0,
            "positive_windows_pct": 0.0,
            "mean_test_return": 0.0,
            "mean_test_hit_rate": 0.0,
            "overfitting_alert": False,
            "relatorio": "Nenhuma janela de walk-forward foi gerada.",
        }

    returns = pd.to_numeric(walk_df["mean_test_return"], errors="coerce").dropna()
    hit = pd.to_numeric(walk_df["mean_test_hit_rate"], errors="coerce").dropna()
    positive = round(float((returns > 0).mean() * 100.0), 4) if not returns.empty else 0.0
    overfit_rate = float(walk_df["overfitting_flag"].mean()) if "overfitting_flag" in walk_df else 0.0
    robust_signals = (
        walk_df["best_train_signal_type"].value_counts().idxmax()
        if "best_train_signal_type" in walk_df and not walk_df["best_train_signal_type"].dropna().empty
        else None
    )
    robust_buckets = (
        walk_df["best_train_score_bucket"].value_counts().idxmax()
        if "best_train_score_bucket" in walk_df and not walk_df["best_train_score_bucket"].dropna().empty
        else None
    )
    overfitting_alert = bool(overfit_rate >= 0.4 or positive < 40.0)
    relatorio = (
        f"Walk-forward gerou {len(walk_df)} janelas, com {positive:.1f}% de janelas positivas. "
        f"Retorno médio de teste: {returns.mean():.4f}. "
        f"Sinal mais recorrente no treino: {robust_signals}. Bucket mais recorrente: {robust_buckets}. "
        + ("Há alerta de overfitting." if overfitting_alert else "Não há alerta forte de overfitting.")
    )
    return {
        "windows_count": int(len(walk_df)),
        "mean_test_return": round(float(returns.mean()), 4) if not returns.empty else 0.0,
        "mean_test_hit_rate": round(float(hit.mean()), 4) if not hit.empty else 0.0,
        "positive_windows_pct": positive,
        "signal_stability": robust_signals,
        "bucket_stability": robust_buckets,
        "robust_signals": robust_signals,
        "robust_buckets": robust_buckets,
        "overfitting_alert": overfitting_alert,
        "relatorio": relatorio,
    }
