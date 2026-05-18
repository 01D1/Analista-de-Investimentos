"""
Options Chain Builder — IV real via Newton-Raphson + Greeks completos.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from src.quant.options_math import (
    black_scholes,
    implied_volatility,
    days_to_expiration,
    liquidity_score,
    _classify_moneyness,
    _moneyness_pct,
)
from src.quant.volatility import historical_volatility, build_vol_surface, iv_smile, vol_term_structure

ATM_BAND = 3.0


# ---------------------------------------------------------------------------
# Estrutura de dados
# ---------------------------------------------------------------------------

@dataclass
class OptionRecord:
    ticker: str
    underlying: str
    option_type: str        # CALL | PUT
    strike: float
    expiry: str             # YYYYMMDD
    dte: int

    # Preços de mercado
    price: float            # último preço negociado (close)
    volume: float
    trades: int
    liq_score: float

    # Moneyness
    moneyness: str          # ITM | ATM | OTM
    moneyness_pct: float

    # Volatilidade
    iv_implied: float       # IV real (Newton-Raphson); NaN se não convergir
    iv_hv: float            # HV usada como fallback
    iv_vs_hv: float         # spread IV - HV (prêmio de vol)

    # Greeks — todos calculados com iv_implied (ou hv se iv=NaN)
    delta: float
    gamma: float
    theta: float            # por dia calendário
    vega: float             # por 1pp de vol
    rho: float              # por 1pp de taxa
    vanna: float            # dDelta/dσ
    charm: float            # dDelta/dT por dia
    vomma: float            # dVega/dσ
    speed: float            # dGamma/dS

    # Decomposição de preço
    intrinsic_value: float
    time_value: float

    # Referência
    stock_price: float
    trade_date: str


# ---------------------------------------------------------------------------
# Cadeia de opções
# ---------------------------------------------------------------------------

class OptionsChain:
    def __init__(
        self,
        records: List[OptionRecord],
        underlying: str,
        stock_price: float,
        trade_date: str,
        hv: float,
        r: float = 0.1475,
    ):
        self.records     = records
        self.underlying  = underlying
        self.stock_price = stock_price
        self.trade_date  = trade_date
        self.hv          = hv
        self.r           = r

    def __len__(self) -> int:
        return len(self.records)

    def __repr__(self) -> str:
        n_iv = sum(1 for r in self.records if not math.isnan(r.iv_implied))
        return (
            f"OptionsChain({self.underlying}, {self.trade_date}, "
            f"{len(self.calls)}C/{len(self.puts)}P, "
            f"HV={self.hv:.1%}, IV={n_iv}/{len(self.records)} convergidos)"
        )

    # --- Acesso básico ---

    @property
    def calls(self) -> List[OptionRecord]:
        return sorted([r for r in self.records if r.option_type == "CALL"], key=lambda r: r.strike)

    @property
    def puts(self) -> List[OptionRecord]:
        return sorted([r for r in self.records if r.option_type == "PUT"], key=lambda r: r.strike)

    def expiries(self) -> List[str]:
        return sorted(set(r.expiry for r in self.records if r.expiry))

    def by_expiry(self, expiry: str) -> "OptionsChain":
        recs = [r for r in self.records if r.expiry == expiry]
        return OptionsChain(recs, self.underlying, self.stock_price, self.trade_date, self.hv, self.r)

    # --- Liquidez ---

    def liquid_calls(self, min_vol: float = 5_000, min_trades: int = 3) -> List[OptionRecord]:
        return [r for r in self.calls if r.volume >= min_vol and r.trades >= min_trades]

    def liquid_puts(self, min_vol: float = 5_000, min_trades: int = 3) -> List[OptionRecord]:
        return [r for r in self.puts if r.volume >= min_vol and r.trades >= min_trades]

    # --- ATM helpers ---

    def atm_call(self, expiry: str = None, liquid_only: bool = True) -> Optional[OptionRecord]:
        pool = self.liquid_calls() if liquid_only else self.calls
        if expiry:
            pool = [r for r in pool if r.expiry == expiry]
        return min(pool, key=lambda r: abs(r.moneyness_pct)) if pool else None

    def atm_put(self, expiry: str = None, liquid_only: bool = True) -> Optional[OptionRecord]:
        pool = self.liquid_puts() if liquid_only else self.puts
        if expiry:
            pool = [r for r in pool if r.expiry == expiry]
        return min(pool, key=lambda r: abs(r.moneyness_pct)) if pool else None

    def otm_calls(self, min_otm_pct: float = 2.0, expiry: str = None, liquid_only: bool = True) -> List[OptionRecord]:
        pool = self.liquid_calls() if liquid_only else self.calls
        if expiry:
            pool = [r for r in pool if r.expiry == expiry]
        return [r for r in pool if r.moneyness_pct < -min_otm_pct]

    def otm_puts(self, min_otm_pct: float = 2.0, expiry: str = None, liquid_only: bool = True) -> List[OptionRecord]:
        pool = self.liquid_puts() if liquid_only else self.puts
        if expiry:
            pool = [r for r in pool if r.expiry == expiry]
        return [r for r in pool if r.moneyness_pct < -min_otm_pct]

    # --- Análise de volatilidade ---

    def vol_surface(self, min_liq_score: float = 20.0) -> pd.DataFrame:
        """Superfície IV × Strike × Vencimento (pivot table)."""
        return build_vol_surface(self.records, min_liq_score)

    def smile(self, expiry: str, opt_type: str = "CALL", min_liq_score: float = 20.0) -> pd.DataFrame:
        """IV smile para um vencimento específico."""
        return iv_smile(self.records, expiry, opt_type, min_liq_score)

    def term_structure(self, opt_type: str = "CALL", min_liq_score: float = 20.0) -> pd.DataFrame:
        """Estrutura a termo da IV ATM por vencimento."""
        return vol_term_structure(self.records, opt_type, min_liq_score=min_liq_score)

    def iv_stats(self) -> dict:
        """Estatísticas rápidas de IV da cadeia."""
        ivs = [r.iv_implied for r in self.records if not math.isnan(r.iv_implied) and r.iv_implied > 0]
        if not ivs:
            return {"n_iv": 0, "iv_mean": float("nan"), "iv_min": float("nan"),
                    "iv_max": float("nan"), "iv_atm": float("nan")}
        atm = self.atm_call(liquid_only=False) or self.atm_put(liquid_only=False)
        iv_atm = atm.iv_implied if atm and not math.isnan(atm.iv_implied) else float("nan")
        return {
            "n_iv":    len(ivs),
            "iv_mean": round(sum(ivs) / len(ivs), 4),
            "iv_min":  round(min(ivs), 4),
            "iv_max":  round(max(ivs), 4),
            "iv_atm":  round(iv_atm, 4) if not math.isnan(iv_atm) else float("nan"),
        }

    # --- Export ---

    def to_df(self) -> pd.DataFrame:
        if not self.records:
            return pd.DataFrame()
        return pd.DataFrame([vars(r) for r in self.records])

    def to_greeks_snapshot(self, captured_at: str = None) -> pd.DataFrame:
        """DataFrame pronto para inserção na tabela options_greeks_snapshot."""
        if not captured_at:
            from datetime import datetime, timezone, timedelta
            captured_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()
        df = self.to_df().copy()
        df["captured_at"] = captured_at
        return df


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_chain(
    con: sqlite3.Connection,
    underlying: str,
    qcfg: dict,
    min_dte: int = 10,
    max_dte: int = 60,
    min_vol: float = 2_000,
    min_trades: int = 2,
) -> OptionsChain:
    """
    Monta e enriquece a cadeia completa de opções.

    Fluxo por opção:
      1. Busca dados de mercado (cotahist_daily via b3_quotes)
      2. Calcula IV implícita real (Newton-Raphson sobre preço de fechamento)
      3. Usa iv_implied para recalcular todos os Greeks (ou hv se IV não convergir)
      4. Calcula iv_vs_hv, intrinsic_value, time_value
    """
    r_free = float(qcfg.get("taxa_livre_risco", 0.1475))

    hist = _get_stock_history(con, underlying)
    if hist.empty or hist["close"].iloc[-1] <= 0:
        return OptionsChain([], underlying, 0.0, "", 0.0, r_free)

    stock_price = float(hist["close"].iloc[-1])
    trade_date  = str(hist["trade_date"].iloc[-1])
    hv_series   = historical_volatility(hist["close"], window=21)
    hv = float(hv_series.iloc[-1]) if hasattr(hv_series, "iloc") else float(hv_series)
    if not (hv > 0):
        hv = 0.30

    min_tr  = int(qcfg.get("min_negocios_opcao", 3))
    min_vol_q = float(qcfg.get("min_volume_opcao", 5_000))

    records: List[OptionRecord] = []
    prefix = underlying[:4].upper()

    for opt_type in ("CALL", "PUT"):
        df = _query_options(con, prefix, opt_type, trade_date)
        if df.empty:
            continue

        for _, row in df.iterrows():
            strike = float(row.get("strike", 0) or 0)
            price  = float(row.get("close", 0) or 0)
            if strike <= 0 or price <= 0:
                continue

            expiry = str(row.get("option_maturity", "") or "").strip()
            dte = int(days_to_expiration(trade_date, expiry))
            if dte < 0:
                continue

            volume = float(row.get("volume", 0) or 0)
            trades = int(row.get("trades", 0) or 0)
            T      = max(dte / 365.0, 1e-6)

            # ── IV implícita real ──────────────────────────────────────────
            iv_impl = implied_volatility(price, stock_price, strike, T, r_free, opt_type)

            # Usa IV se convergiu, senão HV como fallback
            sigma_use = iv_impl if (not math.isnan(iv_impl) and iv_impl > 0) else hv
            iv_vs_hv  = (iv_impl - hv) if not math.isnan(iv_impl) else float("nan")

            # ── Greeks completos ──────────────────────────────────────────
            bs = black_scholes(stock_price, strike, T, r_free, sigma_use, opt_type)

            mp  = _moneyness_pct(stock_price, strike, opt_type)
            liq = liquidity_score(trades, volume, min_tr, min_vol_q)

            records.append(OptionRecord(
                ticker=str(row.get("ticker", "")),
                underlying=underlying,
                option_type=opt_type,
                strike=round(strike, 4),
                expiry=expiry,
                dte=dte,
                price=round(price, 4),
                volume=round(volume, 2),
                trades=trades,
                liq_score=round(liq, 1),
                moneyness=_classify_moneyness(stock_price, strike, opt_type),
                moneyness_pct=round(mp, 4),
                iv_implied=round(iv_impl, 6) if not math.isnan(iv_impl) else float("nan"),
                iv_hv=round(hv, 6),
                iv_vs_hv=round(iv_vs_hv, 6) if not math.isnan(iv_vs_hv) else float("nan"),
                delta=bs.delta,
                gamma=bs.gamma,
                theta=bs.theta,
                vega=bs.vega,
                rho=bs.rho,
                vanna=bs.vanna,
                charm=bs.charm,
                vomma=bs.vomma,
                speed=bs.speed,
                intrinsic_value=bs.intrinsic_value,
                time_value=bs.time_value,
                stock_price=round(stock_price, 4),
                trade_date=trade_date,
            ))

    return OptionsChain(records, underlying, stock_price, trade_date, hv, r_free)


# ---------------------------------------------------------------------------
# Persistência de Greeks
# ---------------------------------------------------------------------------

def save_greeks_snapshot(con: sqlite3.Connection, chain: "OptionsChain", captured_at: str = None) -> int:
    """
    Persiste snapshot completo de Greeks na tabela options_greeks_snapshot.
    Retorna número de linhas inseridas.
    """
    df = chain.to_greeks_snapshot(captured_at)
    if df.empty:
        return 0
    cols = [
        "captured_at", "trade_date", "underlying", "ticker", "option_type",
        "strike", "expiry", "dte", "price", "volume", "trades", "liq_score",
        "moneyness", "moneyness_pct",
        "iv_implied", "iv_hv", "iv_vs_hv",
        "delta", "gamma", "theta", "vega", "rho",
        "vanna", "charm", "vomma", "speed",
        "intrinsic_value", "time_value", "stock_price",
    ]
    existing = [c for c in cols if c in df.columns]
    df[existing].to_sql(
        "options_greeks_snapshot", con,
        if_exists="append", index=False,
    )
    con.commit()
    return len(df)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_stock_history(con: sqlite3.Connection, ticker: str, days: int = 60) -> pd.DataFrame:
    q = """
    SELECT trade_date, AVG(close) AS close
    FROM b3_quotes
    WHERE ticker = ? AND asset_type = 'ACAO'
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT ?
    """
    try:
        df = pd.read_sql_query(q, con, params=(ticker, days))
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        return df.sort_values("trade_date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _query_options(con: sqlite3.Connection, prefix: str, opt_type: str, trade_date: str) -> pd.DataFrame:
    q = f"""
    SELECT ticker,
           AVG(close)                 AS close,
           MAX(volume)                AS volume,
           MAX(trades)                AS trades,
           AVG(option_exercise_price) AS strike,
           option_maturity,
           trade_date
    FROM b3_quotes
    WHERE ticker LIKE '{prefix}%'
      AND asset_type = '{opt_type}'
      AND trade_date = ?
    GROUP BY ticker, option_maturity
    ORDER BY volume DESC
    """
    try:
        return pd.read_sql_query(q, con, params=(trade_date,))
    except Exception:
        return pd.DataFrame()
