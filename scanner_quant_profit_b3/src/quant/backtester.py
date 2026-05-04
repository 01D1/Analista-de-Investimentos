"""
Backtesting Engine — Quant Research Layer.

Simula a execução histórica da estratégia sobre dados OHLCV.
Modela: slippage, custo operacional, stop, alvos, stop por tempo.

Abordagem para opções sem histórico de prêmio:
  O P&L é calculado via delta-aproximação sobre o movimento do ativo.
  option_pnl ≈ delta × (ativo_exit - ativo_entry) × contract_size
  Uma alternativa mais simples (default) usa o % de movimento do prêmio
  estimado pelo BS no momento da entrada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from .performance import full_summary


# ---------------------------------------------------------------------------
# Configuração do backtest
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    initial_capital: float = 10_000.0
    risk_pct: float = 0.005             # % capital por trade
    stop_pct: float = 0.30              # stop: perda de 30% no prêmio
    target1_pct: float = 0.50           # alvo 1: +50% no prêmio
    target2_pct: float = 1.00           # alvo 2: +100% no prêmio
    contract_size: int = 100
    slippage_pct: float = 0.005         # 0.5% de slippage na entrada e saída
    cost_per_contract: float = 0.50     # custo operacional por contrato (R$)
    brokerage_pct: float = 0.0          # corretagem % do valor negociado
    max_holding_days: int = 45          # stop por tempo (DTE máx)
    use_target2_partial: bool = True    # fecha 50% no alvo 1, restante no alvo 2
    min_signal_score: float = 50.0      # score mínimo para abrir um trade


# ---------------------------------------------------------------------------
# Trade simulado
# ---------------------------------------------------------------------------

@dataclass
class BacktestTrade:
    date_entry: str
    date_exit: str
    ticker: str
    underlying: str
    option_type: str
    score: float
    entry_price: float          # prêmio de entrada (após slippage)
    exit_price: float           # prêmio de saída (após slippage)
    stop: float
    target1: float
    target2: float
    contracts: int
    contract_size: int = 100
    slippage_cost: float = 0.0
    op_cost: float = 0.0        # custo operacional total
    exit_reason: str = ""       # STOP / ALVO_1 / ALVO_2 / TEMPO / PARCIAL

    @property
    def gross_pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.contracts * self.contract_size

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.slippage_cost - self.op_cost

    @property
    def return_pct(self) -> float:
        return (self.exit_price / self.entry_price - 1.0) * 100.0 if self.entry_price > 0 else 0.0

    @property
    def result(self) -> str:
        return self.exit_reason

    def to_dict(self) -> dict:
        return {
            "date_entry": self.date_entry,
            "date_exit": self.date_exit,
            "ticker": self.ticker,
            "underlying": self.underlying,
            "option_type": self.option_type,
            "score": self.score,
            "entry_price": round(self.entry_price, 4),
            "exit_price": round(self.exit_price, 4),
            "stop": round(self.stop, 4),
            "target1": round(self.target1, 4),
            "target2": round(self.target2, 4),
            "contracts": self.contracts,
            "gross_pnl": round(self.gross_pnl, 2),
            "slippage_cost": round(self.slippage_cost, 2),
            "op_cost": round(self.op_cost, 2),
            "net_pnl": round(self.net_pnl, 2),
            "return_pct": round(self.return_pct, 2),
            "exit_reason": self.exit_reason,
        }


# ---------------------------------------------------------------------------
# Motor de backtesting
# ---------------------------------------------------------------------------

class BacktestEngine:
    """
    Backtesting engine orientado a events sobre sinais históricos.

    Uso típico:
        engine = BacktestEngine(config)
        engine.run_from_signals(signals_df, price_data)
        print(engine.summary())
        engine.equity_curve().plot()
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.cfg = config or BacktestConfig()
        self._trades: list[BacktestTrade] = []
        self._capital = self.cfg.initial_capital

    # ------------------------------------------------------------------
    # Carga de trades de uma fonte externa (journal CSV)
    # ------------------------------------------------------------------

    def load_from_journal(self, journal_df: pd.DataFrame) -> None:
        """
        Carrega trades do trade_journal.csv.
        Colunas necessárias: data_sinal, opcao, ativo, tipo, entrada_planejada,
        stop, alvo_1, alvo_2, quantidade, resultado, retorno_pct
        """
        for _, row in journal_df.iterrows():
            entry = float(row.get("entrada_planejada", 0) or 0)
            if entry <= 0:
                continue

            result = str(row.get("resultado", "")).upper()
            ret_pct = float(row.get("retorno_pct", 0) or 0)
            exit_price = round(entry * (1.0 + ret_pct / 100.0), 4)

            contracts = int(row.get("quantidade", 1) or 1)
            op_cost = contracts * self.cfg.cost_per_contract
            slip = entry * self.cfg.slippage_pct * contracts * self.cfg.contract_size * 2

            t = BacktestTrade(
                date_entry=str(row.get("data_sinal", "")),
                date_exit=str(row.get("data_sinal", "")),
                ticker=str(row.get("opcao", "")),
                underlying=str(row.get("ativo", "")),
                option_type=str(row.get("tipo", "CALL")),
                score=0.0,
                entry_price=entry,
                exit_price=exit_price,
                stop=float(row.get("stop", 0) or 0),
                target1=float(row.get("alvo_1", 0) or 0),
                target2=float(row.get("alvo_2", 0) or 0),
                contracts=contracts,
                contract_size=self.cfg.contract_size,
                slippage_cost=round(slip, 2),
                op_cost=round(op_cost, 2),
                exit_reason=result or "FECHADO",
            )
            self._trades.append(t)

    # ------------------------------------------------------------------
    # Simulação a partir de sinais históricos + preços do ativo
    # ------------------------------------------------------------------

    def run_from_signals(
        self,
        signals_df: pd.DataFrame,
        price_data: dict[str, pd.DataFrame],
    ) -> None:
        """
        Simula o backtest sobre sinais históricos.

        Args:
            signals_df: DataFrame com colunas: date, ticker, underlying, option_type,
                        entry_price, stop_pct, target1_pct, target2_pct, score, dte
            price_data: dict {underlying: DataFrame com trade_date, close, high, low}
        """
        for _, sig in signals_df.iterrows():
            if float(sig.get("score", 0) or 0) < self.cfg.min_signal_score:
                continue

            entry_raw = float(sig.get("entry_price", 0) or 0)
            if entry_raw <= 0:
                continue

            entry = round(entry_raw * (1.0 + self.cfg.slippage_pct), 4)
            stop = round(entry * (1.0 - self.cfg.stop_pct), 4)
            target1 = round(entry * (1.0 + self.cfg.target1_pct), 4)
            target2 = round(entry * (1.0 + self.cfg.target2_pct), 4)

            risk_per_contract = (entry - stop) * self.cfg.contract_size
            if risk_per_contract <= 0:
                continue
            risk_budget = self._capital * self.cfg.risk_pct
            contracts = max(int(risk_budget / risk_per_contract), 0)
            if contracts == 0:
                continue

            # Simula saída via movimento do ativo objeto
            underlying = str(sig.get("underlying", ""))
            prices = price_data.get(underlying, pd.DataFrame())
            entry_date = str(sig.get("date", ""))
            dte = int(sig.get("dte", self.cfg.max_holding_days) or self.cfg.max_holding_days)
            max_days = min(dte, self.cfg.max_holding_days)

            exit_price, exit_date, exit_reason = self._simulate_exit(
                prices=prices,
                entry_date=entry_date,
                entry=entry,
                stop=stop,
                target1=target1,
                target2=target2,
                max_days=max_days,
            )

            op_cost = contracts * self.cfg.cost_per_contract
            slip = entry_raw * self.cfg.slippage_pct * contracts * self.cfg.contract_size * 2

            trade = BacktestTrade(
                date_entry=entry_date,
                date_exit=exit_date,
                ticker=str(sig.get("ticker", "")),
                underlying=underlying,
                option_type=str(sig.get("option_type", "CALL")),
                score=float(sig.get("score", 0) or 0),
                entry_price=entry,
                exit_price=exit_price,
                stop=stop,
                target1=target1,
                target2=target2,
                contracts=contracts,
                contract_size=self.cfg.contract_size,
                slippage_cost=round(slip, 2),
                op_cost=round(op_cost, 2),
                exit_reason=exit_reason,
            )
            self._trades.append(trade)
            self._capital += trade.net_pnl

    def _simulate_exit(
        self,
        prices: pd.DataFrame,
        entry_date: str,
        entry: float,
        stop: float,
        target1: float,
        target2: float,
        max_days: int,
    ) -> tuple[float, str, str]:
        """
        Simula a saída de uma opção usando o movimento do ativo.
        A opção é mapeada via delta-proxy: assume delta=0.5 (ATM).
        Retorna (exit_price, exit_date, exit_reason).
        """
        if prices.empty or "close" not in prices.columns:
            return round(entry * (1.0 - self.cfg.stop_pct), 4), entry_date, "SEM_DADOS"

        prices = prices.sort_values("trade_date").reset_index(drop=True)
        try:
            idx0 = prices[prices["trade_date"] >= entry_date].index[0]
        except IndexError:
            return round(entry * (1.0 - self.cfg.stop_pct), 4), entry_date, "SEM_DADOS"

        s0 = float(prices.loc[idx0, "close"])
        if s0 <= 0:
            return stop, entry_date, "STOP"

        delta_proxy = 0.5  # assume ATM

        current_opt_price = entry
        for day in range(1, max_days + 1):
            i = idx0 + day
            if i >= len(prices):
                break
            s1 = float(prices.loc[i, "close"])
            ds = (s1 - s0) / s0   # retorno diário do ativo
            # aproximação do movimento da opção
            current_opt_price = max(current_opt_price * (1.0 + delta_proxy * ds * 2), 0.01)
            exit_date = str(prices.loc[i, "trade_date"])

            if current_opt_price <= stop:
                return round(stop * (1.0 - self.cfg.slippage_pct), 4), exit_date, "STOP"
            if current_opt_price >= target2:
                return round(target2 * (1.0 - self.cfg.slippage_pct), 4), exit_date, "ALVO_2"
            if current_opt_price >= target1:
                return round(target1 * (1.0 - self.cfg.slippage_pct), 4), exit_date, "ALVO_1"

        # Expirou sem atingir stop ou alvo
        return round(current_opt_price * (1.0 - self.cfg.slippage_pct), 4), exit_date if max_days > 0 else entry_date, "TEMPO"

    # ------------------------------------------------------------------
    # Análise de resultados
    # ------------------------------------------------------------------

    def trades_df(self) -> pd.DataFrame:
        if not self._trades:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in self._trades])

    def equity_curve(self) -> pd.Series:
        """Curva de capital acumulada (trade a trade)."""
        capital = self.cfg.initial_capital
        curve = [capital]
        dates = [None]
        for t in self._trades:
            capital += t.net_pnl
            curve.append(round(capital, 2))
            dates.append(t.date_exit)
        s = pd.Series(curve, name="equity")
        s.index = range(len(s))
        return s

    def drawdown_series(self) -> tuple[pd.Series, float]:
        """Retorna (série de drawdown, máx drawdown)."""
        from .performance import drawdown as dd_func
        return dd_func(self.equity_curve())

    def summary(self) -> dict:
        df = self.trades_df()
        if df.empty:
            return {"message": "Nenhum trade simulado."}
        pnl = df["net_pnl"]
        return full_summary(pnl, capital=self.cfg.initial_capital)

    def print_summary(self) -> None:
        s = self.summary()
        print("\n" + "=" * 50)
        print("  BACKTEST SUMMARY")
        print("=" * 50)
        for k, v in s.items():
            if k == "message":
                print(f"  {v}")
            else:
                print(f"  {k:<26}: {v}")
        print("=" * 50 + "\n")

    def reset(self) -> None:
        self._trades = []
        self._capital = self.cfg.initial_capital

    @classmethod
    def from_qcfg(cls, qcfg: dict) -> "BacktestEngine":
        cfg = BacktestConfig(
            initial_capital=qcfg.get("capital_inicial", 10_000.0),
            risk_pct=qcfg.get("risco_por_trade", 0.005),
            stop_pct=qcfg.get("stop_opcao_pct", 0.30),
            target1_pct=qcfg.get("alvo_1_pct", 0.50),
            target2_pct=qcfg.get("alvo_2_pct", 1.00),
            contract_size=qcfg.get("contract_size", 100),
            slippage_pct=qcfg.get("backtest", {}).get("slippage_pct", 0.005),
            cost_per_contract=qcfg.get("backtest", {}).get("custo_por_contrato", 0.50),
            min_signal_score=qcfg.get("backtest", {}).get("score_minimo", 50.0),
        )
        return cls(cfg)
