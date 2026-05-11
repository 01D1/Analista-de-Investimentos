"""
Trade Journal — Diário de operações em SQLite.

Permite registrar manualmente cada trade executado, acompanhar
posições abertas, calcular P&L realizado e alimentar o módulo
de performance com dados reais (além do backtest simulado).

Tabela: journal_trades
  id, date_entry, date_exit, underlying, ticker, option_type,
  direction, strategy_type, entry_price, stop_price, target1,
  target2, exit_price, contracts, gross_pnl, net_pnl,
  exit_reason, notes, score, outcome

⚠️  Apenas registro informativo — não envia ordens.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd


# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS journal_trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date_entry   TEXT NOT NULL,
    date_exit    TEXT,
    underlying   TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    option_type  TEXT DEFAULT 'CALL',
    direction    TEXT DEFAULT 'COMPRA',
    strategy     TEXT DEFAULT '',
    entry_price  REAL NOT NULL,
    stop_price   REAL,
    target1      REAL,
    target2      REAL,
    exit_price   REAL,
    contracts    INTEGER DEFAULT 1,
    contract_size INTEGER DEFAULT 100,
    gross_pnl    REAL,
    net_pnl      REAL,
    cost_total   REAL DEFAULT 0,
    exit_reason  TEXT,
    notes        TEXT DEFAULT '',
    score        REAL DEFAULT 0,
    outcome      TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS journal_config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class JournalTrade:
    underlying:   str
    ticker:       str
    entry_price:  float
    date_entry:   str = field(default_factory=lambda: date.today().isoformat())
    date_exit:    Optional[str] = None
    option_type:  str = "CALL"
    direction:    str = "COMPRA"
    strategy:     str = ""
    stop_price:   Optional[float] = None
    target1:      Optional[float] = None
    target2:      Optional[float] = None
    exit_price:   Optional[float] = None
    contracts:    int = 1
    contract_size: int = 100
    gross_pnl:    Optional[float] = None
    net_pnl:      Optional[float] = None
    cost_total:   float = 0.0
    exit_reason:  Optional[str] = None
    notes:        str = ""
    score:        float = 0.0
    outcome:      Optional[str] = None  # WIN / LOSS / BREAKEVEN / ABERTO

    @property
    def risk_financial(self) -> float:
        if self.stop_price and self.entry_price:
            return abs(self.entry_price - self.stop_price) * self.contracts * self.contract_size
        return 0.0

    @property
    def is_open(self) -> bool:
        return self.date_exit is None or self.exit_price is None


class TradeJournal:
    """Interface SQLite para o diário de trades."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.executescript(_DDL)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add_trade(self, trade: JournalTrade) -> int:
        """Registra novo trade. Retorna o ID gerado."""
        sql = """
        INSERT INTO journal_trades
            (date_entry, underlying, ticker, option_type, direction, strategy,
             entry_price, stop_price, target1, target2, contracts, contract_size,
             cost_total, notes, score, outcome)
        VALUES
            (:date_entry, :underlying, :ticker, :option_type, :direction, :strategy,
             :entry_price, :stop_price, :target1, :target2, :contracts, :contract_size,
             :cost_total, :notes, :score, 'ABERTO')
        """
        with self._conn() as con:
            cur = con.execute(sql, asdict(trade))
            return cur.lastrowid

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_reason: str = "MANUAL",
        date_exit: Optional[str] = None,
        notes: str = "",
    ) -> dict:
        """Fecha um trade e calcula P&L. Retorna o trade atualizado."""
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM journal_trades WHERE id = ?", (trade_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Trade {trade_id} não encontrado")

            cols  = [d[0] for d in con.execute("SELECT * FROM journal_trades LIMIT 0").description]
            trade = dict(zip(cols, row))

        entry     = trade["entry_price"]
        contracts = trade["contracts"]
        size      = trade["contract_size"]
        cost      = trade.get("cost_total", 0.0) or 0.0
        direction = trade.get("direction", "COMPRA")

        multiplier  = 1 if direction == "COMPRA" else -1
        gross_pnl   = multiplier * (exit_price - entry) * contracts * size
        net_pnl     = gross_pnl - cost

        if net_pnl > 0:
            outcome = "WIN"
        elif net_pnl < 0:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        exit_date = date_exit or date.today().isoformat()

        with self._conn() as con:
            con.execute(
                """UPDATE journal_trades
                   SET date_exit=?, exit_price=?, gross_pnl=?, net_pnl=?,
                       exit_reason=?, outcome=?, notes=notes||?
                   WHERE id=?""",
                (exit_date, exit_price, gross_pnl, net_pnl,
                 exit_reason, outcome,
                 f"\n[{exit_date}] {notes}" if notes else "",
                 trade_id),
            )

        return {**trade, "exit_price": exit_price, "gross_pnl": gross_pnl,
                "net_pnl": net_pnl, "outcome": outcome}

    def update_notes(self, trade_id: int, notes: str):
        with self._conn() as con:
            con.execute("UPDATE journal_trades SET notes=? WHERE id=?", (notes, trade_id))

    def delete_trade(self, trade_id: int):
        with self._conn() as con:
            con.execute("DELETE FROM journal_trades WHERE id=?", (trade_id,))

    # ── Leitura ───────────────────────────────────────────────────────────────

    def list_open(self) -> pd.DataFrame:
        sql = """
        SELECT id, date_entry, underlying, ticker, strategy, direction,
               entry_price, stop_price, target1, contracts, score, notes
        FROM journal_trades WHERE outcome='ABERTO' OR date_exit IS NULL
        ORDER BY date_entry DESC
        """
        return pd.read_sql(sql, self._conn())

    def list_closed(self, limit: int = 200) -> pd.DataFrame:
        sql = """
        SELECT id, date_entry, date_exit, underlying, ticker, strategy,
               direction, entry_price, exit_price, gross_pnl, net_pnl,
               exit_reason, outcome, score, notes
        FROM journal_trades WHERE outcome != 'ABERTO' AND date_exit IS NOT NULL
        ORDER BY date_exit DESC LIMIT ?
        """
        return pd.read_sql(sql, self._conn(), params=(limit,))

    def all_trades(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT * FROM journal_trades ORDER BY date_entry DESC", self._conn()
        )

    def daily_summary(self, target_date: Optional[str] = None) -> dict:
        d = target_date or date.today().isoformat()
        sql = """
        SELECT COUNT(*) as total, SUM(net_pnl) as pnl,
               SUM(CASE WHEN outcome='WIN'  THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses
        FROM journal_trades WHERE date_exit = ?
        """
        with self._conn() as con:
            row = con.execute(sql, (d,)).fetchone()
        total, pnl, wins, losses = row
        return {
            "date": d,
            "total_closed": total or 0,
            "net_pnl": pnl or 0.0,
            "wins": wins or 0,
            "losses": losses or 0,
            "win_rate": (wins / total) if total else 0.0,
        }

    # ── Performance ───────────────────────────────────────────────────────────

    def performance_summary(self) -> dict:
        """Calcula métricas de performance dos trades fechados."""
        df = self.list_closed()
        if df.empty:
            return {"message": "Sem trades fechados no diário."}

        closed = df[df["outcome"].isin(["WIN", "LOSS", "BREAKEVEN"])].copy()
        if closed.empty:
            return {"message": "Sem trades finalizados."}

        wins   = (closed["outcome"] == "WIN").sum()
        losses = (closed["outcome"] == "LOSS").sum()
        total  = len(closed)

        pnl_series = closed["net_pnl"].fillna(0)
        gross_pnl  = pnl_series.sum()

        avg_win  = pnl_series[pnl_series > 0].mean() if wins  > 0 else 0.0
        avg_loss = pnl_series[pnl_series < 0].mean() if losses > 0 else 0.0
        payoff   = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

        # Equity curve
        equity = pnl_series.cumsum()
        peak   = equity.cummax()
        dd     = equity - peak
        max_dd = float(dd.min()) if not dd.empty else 0.0

        # Expectativa matemática por trade
        win_rate = wins / total if total > 0 else 0.0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        return {
            "total_trades":  total,
            "wins":          wins,
            "losses":        losses,
            "win_rate":      win_rate,
            "gross_pnl":     gross_pnl,
            "avg_win":       avg_win,
            "avg_loss":      avg_loss,
            "payoff":        payoff,
            "expectancy":    expectancy,
            "max_drawdown":  max_dd,
            "best_trade":    float(pnl_series.max()),
            "worst_trade":   float(pnl_series.min()),
        }

    def equity_series(self) -> pd.Series:
        df = self.list_closed()
        if df.empty:
            return pd.Series(dtype=float)
        return df.sort_values("date_exit")["net_pnl"].fillna(0).cumsum().reset_index(drop=True)

    def monthly_pnl(self) -> pd.DataFrame:
        df = self.list_closed()
        if df.empty:
            return pd.DataFrame()
        df["month"] = pd.to_datetime(df["date_exit"]).dt.to_period("M").astype(str)
        return df.groupby("month")["net_pnl"].sum().reset_index()

    # ── Importar do backtest ──────────────────────────────────────────────────

    def import_from_backtest(self, trades_df: pd.DataFrame) -> int:
        """Importa trades simulados do backtester para o diário (read-only audit)."""
        imported = 0
        with self._conn() as con:
            for _, row in trades_df.iterrows():
                try:
                    con.execute("""
                    INSERT OR IGNORE INTO journal_trades
                        (date_entry, date_exit, underlying, ticker, option_type,
                         strategy, entry_price, exit_price, gross_pnl, net_pnl,
                         exit_reason, outcome, notes)
                    VALUES (?, ?, ?, ?, ?, 'BACKTEST', ?, ?, ?, ?, ?, ?, 'Importado do backtest')
                    """, (
                        str(row.get("date_entry", "")),
                        str(row.get("date_exit", "")),
                        str(row.get("underlying", "")),
                        str(row.get("ticker", "")),
                        str(row.get("option_type", "CALL")),
                        float(row.get("entry_price", 0)),
                        float(row.get("exit_price", 0)),
                        float(row.get("gross_pnl", 0)),
                        float(row.get("net_pnl", 0)),
                        str(row.get("exit_reason", "")),
                        "WIN" if float(row.get("net_pnl", 0)) > 0 else "LOSS",
                    ))
                    imported += 1
                except Exception:
                    pass
        return imported
