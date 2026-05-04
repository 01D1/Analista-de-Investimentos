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
            # Anchored: treino começa sempre do início, teste avança
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
            # Rolling: janela de treino deslizando
            train_w = self.cfg.rolling_window
            test_w = self.cfg.test_window
            i = 0
            while i + train_w + test_w <= n:
                train_idx = list(range(i, i + train_w))
                test_idx = list(range(i + train_w, i + train_w + test_w))
                windows.append((train_idx, test_idx))
                i += test_w  # avança o tamanho do teste

        return windows

    def run_on_signals(
        self,
        strategy_fn: Callable[[pd.DataFrame], pd.Series],
        full_data: pd.DataFrame,
        capital: float = 10_000.0,
    ) -> WalkForwardResult:
        """
        Walk-forward sobre um DataFrame de dados históricos.
        strategy_fn recebe um subset do full_data e retorna uma pd.Series de P&L.
        """
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
