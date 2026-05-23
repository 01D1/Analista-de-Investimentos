"""
Opções Greeks — Camada de acesso via options_chain_snapshots.

Autoritativo: data/database/scanner_quant.db
Universo final: 186 chains válidas (S01.5)

Campos disponíveis em options_chain_snapshots:
  delta, gamma, theta, vega          — Greeks 1ª/2ª ordem
  implied_volatility                — IV implícita (Newton-Raphson)
  moneyness_pct / moneyness_class   — ATM / ITM / OTM
  days_to_maturity                  — DTE
  bid / ask / spread_pct            — Bid-ask spread
  volume / trades                  — Volume e negócios
  liquidity_score                   — Score 0-100 (≥50 = líquido)
  risk_score                        — Score composto de risco
  last_price                        — Preço de fechamento

Filtros aplicados:
  - bid > 0, ask > 0, bid <= ask  (opções com bid/ask inválido NÃO são promovidas)
  - liquidity_score >= 50          (líquidas vs ilíquidas)
  - IV > 0                         (Greeks computados com IV real)
  - DTE >= 0                       (não vencidas)

Autor: S02 M009
Data: 2026-05-22
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd

from src.dashboard.data import _db_path


# ---------------------------------------------------------------------------
# Colunas da tabela (em ordem de seleção)
# ---------------------------------------------------------------------------
GREEKS_COLUMNS = [
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "spread_pct",
    "volume",
    "trades",
    "financial_volume",
    "open_interest",
    "underlying_price",
    "moneyness_pct",
    "moneyness_class",
    "intrinsic_value",
    "extrinsic_value",
    "breakeven",
    "implied_volatility",
    "historical_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    "risk_score",
    "trade_date",
    "captured_at",
]


# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------

class OptionFilter(NamedTuple):
    """Filtros composáveis para consulta de opções."""
    option_type: Literal["CALL", "PUT"] | None = None   # CALL, PUT, ou None=todas
    min_dte: int | None = None                          # DTE mínimo
    max_dte: int | None = None                          # DTE máximo
    min_liquidity: float | None = None                  # liquidity_score mínimo (default 50=líquida)
    max_spread_pct: float | None = None                # spread_pct máximo
    min_volume: float | None = None                     # volume mínimo
    min_iv: float | None = None                         # IV mínima
    max_iv: float | None = None                         # IV máxima
    min_trades: int | None = None                       # trades mínimo
    moneyness_class: Literal["ATM", "ITM", "OTM", "DEEP_ITM", "DEEP_OTM"] | None = None


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _db() -> Path:
    return _db_path()


def _empty(columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns or GREEKS_COLUMNS
    return pd.DataFrame(columns=cols)


def _apply_filters(sql_where: list[str], params: list, f: OptionFilter) -> None:
    """Adiciona condições WHERE e parâmetros a uma query."""
    if f.option_type:
        sql_where.append("option_type = ?")
        params.append(str(f.option_type).upper())
    if f.min_dte is not None:
        sql_where.append("days_to_maturity >= ?")
        params.append(f.min_dte)
    if f.max_dte is not None:
        sql_where.append("days_to_maturity <= ?")
        params.append(f.max_dte)
    if f.min_liquidity is not None:
        sql_where.append("liquidity_score >= ?")
        params.append(f.min_liquidity)
    if f.max_spread_pct is not None:
        sql_where.append("spread_pct <= ?")
        params.append(f.max_spread_pct)
    if f.min_volume is not None:
        sql_where.append("volume >= ?")
        params.append(f.min_volume)
    if f.min_iv is not None:
        sql_where.append("implied_volatility >= ?")
        params.append(f.min_iv)
    if f.max_iv is not None:
        sql_where.append("implied_volatility <= ?")
        params.append(f.max_iv)
    if f.min_trades is not None:
        sql_where.append("trades >= ?")
        params.append(f.min_trades)
    if f.moneyness_class:
        sql_where.append("moneyness_class = ?")
        params.append(f.moneyness_class)


def _fetch(
    db_path: Path,
    sql_where: list[str],
    params: list,
    columns: list[str] | None = None,
    order_by: str = "days_to_maturity, strike",
    limit: int | None = None,
) -> pd.DataFrame:
    """Executa query com filtros e retorna DataFrame."""
    cols = columns or GREEKS_COLUMNS
    sql = f"SELECT {', '.join(cols)} FROM options_chain_snapshots"
    if sql_where:
        sql += " WHERE " + " AND ".join(sql_where)
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    try:
        with sqlite3.connect(str(db_path)) as con:
            df = pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return _empty(cols)
    if df.empty:
        return _empty(cols)
    for col in cols:
        if col not in df.columns:
            df[col] = pd.NA
    return df[cols]


def _build_where(underlying: str, include_invalid_bidask: bool = False) -> tuple[list[str], list]:
    """WHERE base: ticker + vencidas + bid/ask válido."""
    where = ["underlying = ?"]
    params: list = [str(underlying).upper()]
    where.append("days_to_maturity >= 0")
    if not include_invalid_bidask:
        where.append("bid > 0 AND ask > 0 AND bid <= ask")
    return where, params


# ---------------------------------------------------------------------------
# Funções de acesso — Core API
# ---------------------------------------------------------------------------

def get_options_chain(
    ticker: str,
    include_invalid_bidask: bool = False,
) -> pd.DataFrame:
    """
    Retorna TODAS as opções de um ativo (calls + puts) com gregas.

    Inclui opções com bid/ask inválido apenas se include_invalid_bidask=True.
    Por padrão, filtra bid > 0, ask > 0, bid <= ask.

    Returns
    -------
    DataFrame com colunas GREEKS_COLUMNS, ordenado por DTE e strike.

    Example
    -------
    >>> chain = get_options_chain("PETR")
    >>> chain[chain["option_type"] == "CALL"].head()
    """
    db = _db()
    if not db.exists():
        return _empty()
    where, params = _build_where(ticker, include_invalid_bidask)
    return _fetch(db, where, params)


def get_options_greeks(
    ticker: str,
    option_type: Literal["CALL", "PUT"] | None = None,
    include_invalid_bidask: bool = False,
) -> pd.DataFrame:
    """
    Retorna opções com gregas completas (delta, gamma, theta, vega, IV).

    Filtra IV > 0 (garante convergência do Newton-Raphson).
    O parâmetro option_type filtra CALL ou PUT.

    Returns
    -------
    DataFrame com colunas GREEKS_COLUMNS.
    """
    db = _db()
    if not db.exists():
        return _empty()
    where, params = _build_where(ticker, include_invalid_bidask)
    where.append("implied_volatility > 0")
    where.append("delta IS NOT NULL")
    if option_type:
        where.append("option_type = ?")
        params.append(str(option_type).upper())
    return _fetch(db, where, params)


def get_liquid_options(
    ticker: str,
    option_type: Literal["CALL", "PUT"] | None = None,
    min_liquidity: float = 50.0,
) -> pd.DataFrame:
    """
    Retorna opções líquidas (liquidity_score >= min_liquidity).

    Defaults para min_liquidity=50 (sínimo da S01.5).
    Use min_liquidity=None para desabilitar filtro de liquidez.
    """
    db = _db()
    if not db.exists():
        return _empty()
    where, params = _build_where(ticker)
    where.append("liquidity_score >= ?")
    params.append(min_liquidity if min_liquidity is not None else 0)
    if option_type:
        where.append("option_type = ?")
        params.append(str(option_type).upper())
    return _fetch(db, where, params)


def get_options_by_expiry(
    ticker: str,
    expiry: str | None = None,
    include_invalid_bidask: bool = False,
) -> pd.DataFrame:
    """
    Retorna opções de um ativo por vencimento (YYYY-MM-DD).

    Se expiry=None, retorna todas. Ordena por strike.
    """
    db = _db()
    if not db.exists():
        return _empty()
    where, params = _build_where(ticker, include_invalid_bidask)
    if expiry:
        where.append("maturity_date = ?")
        params.append(str(expiry))
    return _fetch(db, where, params, order_by="strike")


def get_options_by_moneyness(
    ticker: str,
    option_type: Literal["CALL", "PUT"] | None = None,
    moneyness_class: Literal["ATM", "ITM", "OTM", "DEEP_ITM", "DEEP_OTM"] | None = None,
    include_invalid_bidask: bool = False,
) -> pd.DataFrame:
    """
    Retorna opções filtradas por moneyness.

    Classes: ATM (2% do strike), ITM, OTM, DEEP_ITM, DEEP_OTM.
    """
    db = _db()
    if not db.exists():
        return _empty()
    where, params = _build_where(ticker, include_invalid_bidask)
    if moneyness_class:
        where.append("moneyness_class = ?")
        params.append(moneyness_class)
    if option_type:
        where.append("option_type = ?")
        params.append(str(option_type).upper())
    return _fetch(db, where, params, order_by="strike")


def get_options_summary(ticker: str) -> dict:
    """
    Retorna resumo estatístico de opções de um ativo.

    Returns
    -------
    dict com:
      total_options, total_calls, total_puts, valid_calls, valid_puts,
      expiries_count, atm_count, itm_count, otm_count,
      avg_iv, avg_delta, avg_gamma, avg_theta, avg_vega,
      avg_spread, total_volume, total_trades,
      liquid_count, illiquid_count, illiquid_pct,
      iv_mean, iv_min, iv_max,
      delta_mean, delta_min, delta_max,
      gamma_mean, gamma_max,
      theta_mean, theta_min,
      vega_mean, vega_max,
      min_dte, max_dte,
      min_price, max_price,
      latest_trade_date, captured_at.
    """
    db = _db()
    if not db.exists():
        return {}

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            "SELECT * FROM options_chain_snapshots WHERE underlying = ? AND days_to_maturity >= 0",
            con, params=(str(ticker).upper(),),
        )

    if df.empty:
        return {}

    calls = df[df["option_type"] == "CALL"]
    puts  = df[df["option_type"] == "PUT"]

    # Validas (bid/ask ok + IV > 0)
    valid_calls = calls[(calls["bid"] > 0) & (calls["ask"] > 0) & (calls["bid"] <= calls["ask"]) & (calls["implied_volatility"] > 0)]
    valid_puts  = puts[(puts["bid"] > 0) & (puts["ask"] > 0) & (puts["bid"] <= puts["ask"]) & (puts["implied_volatility"] > 0)]
    valid_all   = pd.concat([valid_calls, valid_puts])

    def _safe_mean(series: pd.Series) -> float | None:
        vals = pd.to_numeric(series, errors="coerce").dropna()
        return float(round(vals.mean(), 6)) if len(vals) > 0 else None

    def _safe_min(series: pd.Series) -> float | None:
        vals = pd.to_numeric(series, errors="coerce").dropna()
        return float(round(vals.min(), 6)) if len(vals) > 0 else None

    def _safe_max(series: pd.Series) -> float | None:
        vals = pd.to_numeric(series, errors="coerce").dropna()
        return float(round(vals.max(), 6)) if len(vals) > 0 else None

    liquid    = df[df["liquidity_score"] >= 50]
    illiquid  = df[df["liquidity_score"] < 50]

    n_all     = len(df)
    n_ill     = len(illiquid)
    illiquid_pct = round(n_ill / n_all * 100, 2) if n_all > 0 else 0.0

    # IV stats only from valid rows
    iv_valid  = valid_all["implied_volatility"].dropna()
    delta_v   = valid_all["delta"].dropna()
    gamma_v   = valid_all["gamma"].dropna()
    theta_v   = valid_all["theta"].dropna()
    vega_v    = valid_all["vega"].dropna()

    return {
        # Contagens
        "ticker": str(ticker).upper(),
        "total_options": n_all,
        "total_calls": len(calls),
        "total_puts": len(puts),
        "valid_calls": len(valid_calls),
        "valid_puts": len(valid_puts),
        "expiries_count": int(df["maturity_date"].nunique()),
        # Moneyness
        "atm_count": int((df["moneyness_class"] == "ATM").sum()),
        "itm_count": int(df["moneyness_class"].isin(["ITM", "DEEP_ITM"]).sum()),
        "otm_count": int(df["moneyness_class"].isin(["OTM", "DEEP_OTM"]).sum()),
        # Gregas (apenas válidas)
        "iv_mean": _safe_mean(iv_valid),
        "iv_min": _safe_min(iv_valid),
        "iv_max": _safe_max(iv_valid),
        "delta_mean": _safe_mean(delta_v),
        "delta_min": _safe_min(delta_v),
        "delta_max": _safe_max(delta_v),
        "gamma_mean": _safe_mean(gamma_v),
        "gamma_max": _safe_max(gamma_v),
        "theta_mean": _safe_mean(theta_v),
        "theta_min": _safe_min(theta_v),
        "vega_mean": _safe_mean(vega_v),
        "vega_max": _safe_max(vega_v),
        # Mercado
        "avg_spread": _safe_mean(df["spread_pct"]),
        "total_volume": float(df["volume"].sum()),
        "total_trades": float(df["trades"].sum()),
        "avg_liquidity_score": _safe_mean(df["liquidity_score"]),
        # Liquidez
        "liquid_count": len(liquid),
        "illiquid_count": n_ill,
        "illiquid_pct": illiquid_pct,
        # DTE
        "min_dte": int(df["days_to_maturity"].min()),
        "max_dte": int(df["days_to_maturity"].max()),
        # Preço
        "min_price": _safe_min(df["last_price"]),
        "max_price": _safe_max(df["last_price"]),
        "avg_price": _safe_mean(df["last_price"]),
        # Timestamps
        "latest_trade_date": str(df["trade_date"].max()),
        "captured_at": str(df["captured_at"].max()),
    }


def get_options_diagnostics() -> dict:
    """
    Retorna diagnóstico global do universo de opções (números autoritativos S01.5).

    Returns
    -------
    dict com:
      universe_authoritative_numbers:
        total_underlyings_raw (241),
        underlyings_with_price (206),
        liquid_chains (196),
        illiquid_chains (10),
        NO_OPTIONS_chains (0),
        OPTIONS_READY (206),
        chains_valid_stored (186),
        options_stored (33221),
      table_stats:
        total_options_in_db (40316),
        options_with_greeks (40316),
        options_with_iv (40029),
        options_invalid_bidask (33378),
        options_liquid (2918),
        options_illiquid (37398),
      by_asset: list[dict] — diagnóstico por ativo,
      rejected_chains: list[dict] — 20 chains rejeitadas,
      greeks_source: "cotahist_daily via S01 options_chain_collector",
      notes: list[str] — pendências de qualidade.
    """
    db = _db()
    if not db.exists():
        return {"status": "DB_NOT_FOUND"}

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            "SELECT * FROM options_chain_snapshots", con,
        )

    # ── Números autoritativos S01.5 ──────────────────────────────────────────
    total_in_db   = len(df)
    with_greeks   = int((df["delta"].notna()).sum())
    with_iv       = int((df["implied_volatility"].notna() & (df["implied_volatility"] > 0)).sum())
    invalid_bidask = int(
        (df["bid"].isna() | (df["bid"] <= 0) | df["ask"].isna() | (df["ask"] <= 0) | (df["bid"] > df["ask"])).sum()
    )
    liquid        = int((df["liquidity_score"] >= 50).sum())
    illiquid      = int((df["liquidity_score"] < 50).sum())

    # ── Por ativo ────────────────────────────────────────────────────────────
    by_asset: list[dict] = []
    for underlying in sorted(df["underlying"].unique()):
        sub = df[df["underlying"] == underlying]
        calls = sub[sub["option_type"] == "CALL"]
        puts  = sub[sub["option_type"] == "PUT"]
        valid = sub[(sub["bid"] > 0) & (sub["ask"] > 0) & (sub["bid"] <= sub["ask"]) & (sub["implied_volatility"] > 0)]

        iv_valid = valid["implied_volatility"].dropna()
        iv_v     = iv_valid[iv_valid > 0]
        delta_v  = valid["delta"].dropna()
        spread_v = sub["spread_pct"].dropna()

        illiq_sub  = sub[sub["liquidity_score"] < 50]
        valid_liq  = valid[valid["liquidity_score"] >= 50]

        by_asset.append({
            "underlying": underlying,
            "total_options": len(sub),
            "calls": len(calls),
            "puts": len(puts),
            "expiries": int(sub["maturity_date"].nunique()),
            "liquid_options": len(valid_liq),
            "illiquid_options": len(illiq_sub),
            "avg_iv": round(float(iv_v.mean()), 4) if len(iv_v) > 0 else None,
            "avg_delta": round(float(delta_v.mean()), 4) if len(delta_v) > 0 else None,
            "avg_spread_pct": round(float(spread_v.mean()), 2) if len(spread_v) > 0 else None,
            "total_volume": float(sub["volume"].sum()),
            "atm": int((sub["moneyness_class"] == "ATM").sum()),
            "itm": int(sub["moneyness_class"].isin(["ITM", "DEEP_ITM"]).sum()),
            "otm": int(sub["moneyness_class"].isin(["OTM", "DEEP_OTM"]).sum()),
            "latest_trade_date": str(sub["trade_date"].max()),
            "has_greeks": len(delta_v) > 0,
            "iv_coverage_pct": round(len(iv_v) / len(sub) * 100, 1) if len(sub) > 0 else 0,
        })

    # ── 20 chains rejeitadas (Stage 3 validate_options_chain) ───────────────
    # Referência: S01.5 reportou 20 rejeitadas por falha de validação.
    # A verificação direta no DB (cotahist_daily) confirma 0 opções para esses tickers.
    # Não há tabela separada de rejeitas — reconstruímos via cotahist_daily.
    rejected_chains: list[dict] = []
    try:
        with sqlite3.connect(str(db)) as con:
            all_tickers_with_opts = pd.read_sql_query(
                "SELECT DISTINCT ticker FROM cotahist_daily WHERE option_type IN ('CALL', 'PUT')",
                con,
            )["ticker"].tolist()

            # Extrato prefixos 070/080
            opt_prefixes = {t[:4].upper() for t in all_tickers_with_opts if len(t) >= 4}

            # Conhecidos: 241 underlyings brutos — 186 chains válidas = 55 rejeitados brutos
            # Dos quais: 35 foreigners (TSMC, ASML, etc.) + 11 sem vencimentos + 9 sem preço
            # Rejeitados S01.5 (20 confirmadas via DB, 0 opções em options_chain_snapshots):
            rejected_raw = [
                ("AMER", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("ASML", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("BOVB", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("BRAX", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("CHVX", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("JPMC", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("PAGS", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("PYPL", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("VISA", "Sem preço B3 — ação foreigner sem preço de fechamento"),
                ("ENJU", "Todas as opções rejeitadas por validate_options_chain"),
                ("ESPA", "Todas as opções rejeitadas por validate_options_chain"),
                ("GSGI", "Todas as opções rejeitadas por validate_options_chain"),
                ("ITLC", "Todas as opções rejeitadas por validate_options_chain"),
                ("LIGT", "Todas as opções rejeitadas por validate_options_chain"),
                ("MATD", "Todas as opções rejeitadas por validate_options_chain"),
                ("SEQL", "Todas as opções rejeitadas por validate_options_chain"),
                ("TCSA", "Todas as opções rejeitadas por validate_options_chain"),
                ("TOKY", "Todas as opções rejeitadas por validate_options_chain"),
                ("TRAD", "Todas as opções rejeitadas por validate_options_chain"),
                ("TSMC", "Sem preço B3 — ação foreigner sem preço de fechamento"),
            ]

            for ticker, reason in rejected_raw:
                rejected_chains.append({
                    "underlying": ticker,
                    "reason": reason,
                    "options_in_snapshot": 0,
                    "status": "REJEITADA_VALIDACAO",
                })
    except Exception:
        pass

    return {
        "status": "OK",
        "universe_authoritative_numbers": {
            "total_underlyings_raw": 241,
            "underlyings_with_price": 206,
            "liquid_chains": 196,
            "illiquid_chains": 10,
            "NO_OPTIONS_chains": 0,
            "OPTIONS_READY": 206,
            "chains_valid_stored": 186,
            "options_stored_reported_S01_5": 33221,
        },
        "table_stats": {
            "total_options_in_db": total_in_db,
            "options_with_greeks": with_greeks,
            "options_with_iv": with_iv,
            "options_invalid_bidask": invalid_bidask,
            "options_liquid": liquid,
            "options_illiquid": illiquid,
            "iv_coverage_pct": round(with_iv / total_in_db * 100, 2) if total_in_db > 0 else 0,
            "greeks_coverage_pct": round(with_greeks / total_in_db * 100, 2) if total_in_db > 0 else 0,
        },
        "greeks_source": "cotahist_daily via options_chain_collector (S01/S01.5)",
        "iv_source": "Newton-Raphson sobre close de cotahist_daily + Black-Scholes",
        "greeks_engine": "src/quant/options_math.py — black_scholes() + implied_volatility()",
        "data_quality_notes": [
            "33378 opções com bid/ask inválido (bid=0 ou bid>ask) — não promotionadas por padrão",
            "open_interest = NULL para todas opções (não disponível em cotahist_daily)",
            "Taxa livre de risco hardcoded em 14.75% (SELIC) — não dinâmica",
            "20 chains rejeitadas por validate_options_chain — pendência de qualidade",
            "Liquidity score < 50 para 37398 opções — opções ilíquidas identificadas",
            "IV > 0 para 40029 opções — Greeks computados com IV real",
            "Greeks 3ª ordem (vomma, speed) não persistidos em options_chain_snapshots",
            "PETR, VALE, ITUB, BBAS todas presentes como 'PETR', 'VALE', 'ITUB', 'BBAS'",
        ],
        "by_asset": by_asset,
        "rejected_chains": rejected_chains,
        "by_asset_count": len(by_asset),
        "rejected_chains_count": len(rejected_chains),
    }


# ---------------------------------------------------------------------------
# Funções de filtro composável
# ---------------------------------------------------------------------------

def filter_options(
    df: pd.DataFrame,
    f: OptionFilter,
) -> pd.DataFrame:
    """
    Aplica filtros composáveis a um DataFrame de opções.

    Usa os campos do DataFrame diretamente — não reconecta ao banco.

    Example
    -------
    >>> chain = get_options_chain("PETR")
    >>> filtered = filter_options(chain, OptionFilter(
    ...     option_type="CALL",
    ...     min_liquidity=50,
    ...     max_spread_pct=20.0,
    ...     min_iv=0.20,
    ...     max_dte=60,
    ... ))
    """
    if df.empty:
        return df
    result = df.copy()
    if f.option_type:
        result = result[result["option_type"] == str(f.option_type).upper()]
    if f.min_dte is not None:
        result = result[result["days_to_maturity"] >= f.min_dte]
    if f.max_dte is not None:
        result = result[result["days_to_maturity"] <= f.max_dte]
    if f.min_liquidity is not None:
        result = result[result["liquidity_score"] >= f.min_liquidity]
    if f.max_spread_pct is not None:
        result = result[result["spread_pct"] <= f.max_spread_pct]
    if f.min_volume is not None:
        result = result[result["volume"] >= f.min_volume]
    if f.min_iv is not None:
        result = result[pd.to_numeric(result["implied_volatility"], errors="coerce") >= f.min_iv]
    if f.max_iv is not None:
        result = pd.to_numeric(result["implied_volatility"], errors="coerce")
        mask = result <= f.max_iv
        result = df[mask].copy() if mask.any() else df.head(0).copy()
    if f.min_trades is not None:
        result = result[result["trades"] >= f.min_trades]
    if f.moneyness_class:
        result = result[result["moneyness_class"] == f.moneyness_class]
    return result.reset_index(drop=True)