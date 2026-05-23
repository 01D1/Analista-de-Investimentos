"""
Options Chain Collector — S01: Popula options_chain_snapshots com dados reais de cotahist_daily (B3).

Objetivo: auditar, enriquecer e persistir cadeias de opções reais para os ativos prioritários.
Não calcula gregas ainda (S02), não gera oportunidade (S04), não cria posição (S06).

Fonte: data/database/scanner_quant.db / cotahist_daily
Alvo: options_chain_snapshots (mesmo DB)
Ativos: PETR4, VALE3, ITUB4, BBAS3, BBDC4, WEGE3, SUZB3
"""
from __future__ import annotations

import math
import sqlite3
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

# Bootstrap: resolve project root for all import modes.
# - parents[2]: via -m (package resolved to src/collectors/, go 2 up to project root)
# - parents[1]: fallback via direct script invocation
_FILE = Path(__file__).resolve()
ROOT = (_FILE.parents[2] if (_FILE.parents[2] / "src").is_dir() else _FILE.parents[1])
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.options.greeks import (
    black_scholes_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    estimate_implied_volatility,
)
from src.options.options_chain_normalizer import validate_options_chain
from src.options.options_metrics import calculate_days_to_maturity, calculate_spread_metrics
from src.utils import load_config, project_path


DB_PATH = project_path("data/database/scanner_quant.db")
PRIORITY = ["PETR", "VALE", "ITUB", "BBAS", "BBDC", "WEGE", "SUZB"]

# TRADE_DATE: dinâmica — usa a última data disponível no COTAHIST.
# Atualizado pelo scheduler operacional. Não hardcodar datas futuras.
# Se não houver dados no banco, usa fallback "2026-05-21" (último pregão disponível).
_TRADE_DATE_OVERRIDE: str | None = None


def set_trade_date_override(date_str: str | None) -> None:
    """Permite que o scheduler substitua TRADE_DATE em runtime."""
    global _TRADE_DATE_OVERRIDE
    _TRADE_DATE_OVERRIDE = date_str


def get_trade_date() -> str:
    """Resolve TRADE_DATE: usa override > latest DB date > fallback."""
    if _TRADE_DATE_OVERRIDE:
        return _TRADE_DATE_OVERRIDE
    try:
        db = project_path("data/database/scanner_quant.db")
        import sqlite3
        with sqlite3.connect(str(db)) as con:
            row = con.execute(
                "SELECT MAX(trade_date) FROM cotahist_daily WHERE market_type IN ('010','10',10)"
            ).fetchone()
            latest = row[0] if row and row[0] else None
            if latest:
                return str(latest)
    except Exception:
        pass
    return "2026-05-21"  # fallback: último pregão com dados reais


TRADE_DATE: str = get_trade_date()  # resolve once at import time
RISK_FREE = 0.1475


def _load_underlying_prices(con: sqlite3.Connection, trade_date: str) -> dict[str, float]:
    """Carrega preços das ações (market_type 010/10) para calcular moneyness."""
    rows = con.execute(
        """
        SELECT ticker, close
        FROM cotahist_daily
        WHERE market_type IN ('010', '10', 10)
          AND trade_date = ?
        """,
        (trade_date,),
    ).fetchall()
    return {str(r[0])[:4].upper(): float(r[1]) for r in rows if r[1] and r[1] > 0}


def _classify_moneyness(S: float, K: float, opt_type: str) -> tuple[str, float]:
    """Classifica ITM/ATM/OTM e retorna moneyness_pct."""
    if opt_type == "CALL":
        if K < S:
            cls = "ITM"
            pct = (S - K) / S * 100
        elif K > S:
            cls = "OTM"
            pct = (K - S) / S * 100
        else:
            cls = "ATM"
            pct = 0.0
    else:  # PUT
        if K > S:
            cls = "ITM"
            pct = (K - S) / S * 100
        elif K < S:
            cls = "OTM"
            pct = (S - K) / S * 100
        else:
            cls = "ATM"
            pct = 0.0
    return cls, round(pct, 4)


def _calc_liquidity_score(volume: float, trades: int) -> float:
    """Score simples de liquidez 0-100 baseado em volume e trades."""
    if volume <= 0 or trades <= 0:
        return 0.0
    vol_score = min(math.log1p(volume) / math.log1p(10_000_000), 1.0) * 50
    trade_score = min(trades / 100, 1.0) * 50
    return round(vol_score + trade_score, 1)


def _collect_for_prefix(
    con: sqlite3.Connection,
    prefix: str,
    trade_date: str,
    underlying_prices: dict[str, float],
) -> pd.DataFrame:
    """Carrega e enriquece opções para um prefixo de ativo."""
    rows = con.execute(
        """
        SELECT
            ticker,
            strike,
            option_type,
            expiration_date,
            trade_date,
            close,
            best_bid,
            best_ask,
            quantity,
            trades,
            volume
        FROM cotahist_daily
        WHERE substr(ticker, 1, 4) = ?
          AND option_type IN ('CALL', 'PUT')
          AND trade_date = ?
        ORDER BY quantity DESC
        """,
        (prefix, trade_date),
    ).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "option_ticker", "strike", "option_type", "maturity_date",
        "trade_date", "last_price", "bid", "ask", "quantity", "trades", "volume",
    ])

    for col in ["strike", "last_price", "bid", "ask", "quantity", "trades", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    S = underlying_prices.get(prefix, 0.0)
    if S <= 0:
        df["underlying_price"] = 0.0
        df["moneyness_class"] = "UNKNOWN"
        df["moneyness_pct"] = float("nan")
        df["days_to_maturity"] = 0
        return df

    df["underlying_price"] = S
    df["underlying"] = prefix

    # DTE
    ref = date.fromisoformat(trade_date)
    df["days_to_maturity"] = df["maturity_date"].apply(
        lambda x: calculate_days_to_maturity(str(x), ref)
    )

    # Moneyness
    moneyness = [_classify_moneyness(S, k, t) for t, k in zip(df["option_type"], df["strike"])]
    df["moneyness_class"] = [m[0] for m in moneyness]
    df["moneyness_pct"] = [m[1] for m in moneyness]

    # Spread
    spreads = [calculate_spread_metrics(b, a, p) for b, a, p in zip(df["bid"], df["ask"], df["last_price"])]
    df["spread"] = [s[0] for s in spreads]
    df["spread_pct"] = [s[1] for s in spreads]

    # Volume financeiro
    df["financial_volume"] = df["quantity"].fillna(0) * df["last_price"].fillna(0)

    # Liquidity score
    df["liquidity_score"] = [
        _calc_liquidity_score(float(v or 0), int(t or 0))
        for v, t in zip(df["quantity"], df["trades"])
    ]

    # Greeks (com fallback HV se IV não convergir)
    hv = 0.30
    greeks_rows = []
    for _, row in df.iterrows():
        K = float(row["strike"]) if row["strike"] and row["strike"] > 0 else 0
        price = float(row["last_price"]) if row["last_price"] and row["last_price"] > 0 else 0
        dte = int(row["days_to_maturity"]) if row["days_to_maturity"] and row["days_to_maturity"] > 0 else 0
        opt = str(row["option_type"])
        T = max(dte / 365.0, 1e-4)

        iv = estimate_implied_volatility(price, S, K, T, RISK_FREE, opt)
        iv_ok = not (iv != iv) and iv > 0 and iv < 5.0
        sigma = iv if iv_ok else hv

        # Intrinsic e time value
        intrinsic = max(0, S - K) if opt == "CALL" else max(0, K - S)
        time_val = max(0, price - intrinsic)

        # BS decomposition
        bs = black_scholes_price(S, K, T, RISK_FREE, sigma, opt)

        greeks_rows.append({
            "implied_volatility": round(iv, 6) if iv_ok else float("nan"),
            "historical_volatility": round(hv, 6),
            "delta": round(calculate_delta(S, K, T, RISK_FREE, sigma, opt), 6),
            "gamma": round(calculate_gamma(S, K, T, RISK_FREE, sigma), 6),
            "theta": round(calculate_theta(S, K, T, RISK_FREE, sigma, opt), 6),
            "vega": round(calculate_vega(S, K, T, RISK_FREE, sigma), 6),
            "intrinsic_value": round(intrinsic, 4),
            "extrinsic_value": round(time_val, 4),
            "breakeven": round(K + (price - intrinsic) if opt == "CALL" else K - (price - intrinsic), 4),
            "risk_score": round(min(abs(K - S) / S * 100, 50) / 50 * 100, 1),
        })

    greeks_df = pd.DataFrame(greeks_rows)
    df = pd.concat([df, greeks_df], axis=1)

    return df


def collect_all() -> pd.DataFrame:
    """Coleta cadeias de opções para todos os ativos prioritários."""
    if not Path(DB_PATH).exists():
        print(f"[S01] Banco não encontrado: {DB_PATH}")
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as con:
        underlying_prices = _load_underlying_prices(con, TRADE_DATE)
        print(f"[S01] Preços carregados: {len(underlying_prices)} ações")

        all_dfs = []
        for prefix in PRIORITY:
            S = underlying_prices.get(prefix, 0.0)
            if S <= 0:
                print(f"  {prefix}: SEM PREÇO (sem dados de ação no banco)")
                continue

            df = _collect_for_prefix(con, prefix, TRADE_DATE, underlying_prices)
            if df.empty:
                print(f"  {prefix}: SEM OPÇÕES para {TRADE_DATE}")
                continue

            # Validação
            valid, issues = validate_options_chain(df)
            issues_str = ", ".join(f"{r['issue']}={r['count']}" for _, r in issues.iterrows() if r["count"] > 0)
            print(f"  {prefix}: {len(df)} opções raw, {len(valid)} válidas | {issues_str}")

            if not valid.empty:
                all_dfs.append(valid)

    if not all_dfs:
        print("[S01] NENHUMA opção real coletada.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"\n[S01] Total coletado: {len(combined)} opções válidas")
    return combined


def save_snapshots(df: pd.DataFrame, captured_at: str | None = None) -> int:
    """Persiste DataFrame de opções na tabela options_chain_snapshots."""
    if df.empty:
        return 0

    if captured_at is None:
        captured_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()

    cols = [
        "captured_at", "trade_date", "option_ticker", "underlying", "option_type",
        "strike", "maturity_date", "days_to_maturity",
        "last_price", "bid", "ask", "spread_pct",
        "volume", "trades", "financial_volume",
        "open_interest",
        "underlying_price",
        "moneyness_pct", "moneyness_class",
        "intrinsic_value", "extrinsic_value", "breakeven",
        "implied_volatility", "historical_volatility",
        "delta", "gamma", "theta", "vega",
        "liquidity_score", "risk_score",
        "metadata_json",
    ]

    save = df.copy()
    save["captured_at"] = captured_at
    save["trade_date"] = str(TRADE_DATE)
    save["open_interest"] = pd.NA
    save["metadata_json"] = '{"source":"cotahist_daily","collector":"S01"}'

    existing = [c for c in cols if c in save.columns]
    to_insert = save[existing].copy()

    # Replace inf/-inf
    for col in to_insert.select_dtypes(include="number").columns:
        to_insert[col] = to_insert[col].replace([float("inf"), -float("inf")], pd.NA)

    n = len(to_insert)
    with sqlite3.connect(DB_PATH) as con:
        to_insert.to_sql("options_chain_snapshots", con, if_exists="append", index=False)
        con.commit()
    print(f"[S01] Salvas {n} opções em options_chain_snapshots @ {captured_at}")
    return n


def run() -> dict:
    """Executa coleta completa e persiste snapshots."""
    captured_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()

    print("=" * 60)
    print("  S01: Options B3 Data Source")
    print(f"  Data: {TRADE_DATE}")
    print(f"  Ativos: {', '.join(PRIORITY)}")
    print("=" * 60)

    df = collect_all()
    if df.empty:
        return {"status": "empty", "snapshots_saved": 0, "captured_at": captured_at, "error": "no_data"}

    n = save_snapshots(df, captured_at)

    # Resumo por ativo
    print("\n[S01] Resumo por ativo:")
    for prefix in PRIORITY:
        sub = df[df["underlying"] == prefix]
        if sub.empty:
            continue
        n_calls = int((sub["option_type"] == "CALL").sum())
        n_puts = int((sub["option_type"] == "PUT").sum())
        S = float(sub["underlying_price"].iloc[0])
        expiries = sub["maturity_date"].nunique()
        vol_range = f"{float(sub['volume'].min()):.0f}-{float(sub['volume'].max()):.0f}"
        iv_mean = float(sub["implied_volatility"].mean()) if not sub["implied_volatility"].isna().all() else float("nan")
        print(f"  {prefix}: {n_calls}C/{n_puts}P | S={S:.2f} | {expiries} exp | vol {vol_range} | IV mean={iv_mean:.2%}")

    return {
        "status": "success",
        "snapshots_saved": n,
        "captured_at": captured_at,
        "trade_date": TRADE_DATE,
        "assets": PRIORITY,
        "total_options": len(df),
    }


if __name__ == "__main__":
    result = run()
    print(f"\n[S01] Resultado: {result['status']} | {result.get('snapshots_saved', 0)} snapshots")