"""
Opções Risk Integration — Camada de risco para opções.

Autoritativo: data/database/scanner_quant.db → options_chain_snapshots
Universo final: 2.918 opções líquidas (S01.5)

Camada de risco calculada on-the-fly a partir de options_chain_snapshots:
  - option_risk_score       Score composto 0-100 (risk_score da chain)
  - max_loss                Perda máxima estimada por contrato
  - premium_at_risk         Prêmio em risco (bid × qtd, proxy)
  - delta_exposure          Exposição delta (delta × preço × lote)
  - gamma_exposure          Exposição gamma
  - theta_daily             Decay diário em R$ (theta × lote)
  - vega_exposure            Sensibilidade a IV
  - liquidity_risk           Score de liquidez (0-100)
  - spread_risk              Risco de spread (pct do preço)
  - dte_risk                Risco temporal (DTE < 3 = crítico)
  - iv_risk                 Risco de IV (muito alta/baixa)
  - underlying_risk_status   Status de risco do subyacente
  - blocking_reasons         Lista de reasons de bloqueio (empty = APROVADA)

Regras de bloqueio (todas aplicadas em série):
  B01: bid <= 0 ou ask <= 0 ou bid > ask
  B02: spread_pct > 50% (spread excessivo vs preço)
  B03: volume == 0 E trades == 0 (sem liquidez)
  B04: DTE < 3 (vencimento iminente)
  B05: implied_volatility == 0 ou NULL
  B06: liquidity_score < 50 (ilíquida por padrão S01.5)
  B07: max_loss é NULL (não há perda máxima definida)
  B08: delta_abs > 1.5 (delta fora de range Black-Scholes)

Autor: S03 M009
Data: 2026-05-23
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from src.dashboard.data import _db_path


# ---------------------------------------------------------------------------
# Constantes de bloqueio
# ---------------------------------------------------------------------------
MAX_SPREAD_PCT = 50.0          # B02: spread > 50% do preço
MIN_DTE = 3                    # B04: DTE < 3 → crítico
MIN_IV = 0.0001                 # B05: IV mínima (0.0001 = mesma tolerância de S02)
MAX_IV = 5.0                   # B05: IV máxima razoável (500%)
MIN_LIQUIDITY = 50.0           # B06: liquidity_score mínimo
MAX_DELTA_ABS = 1.5            # B08: delta fora de range BS

# Lot size padrão para cálculo de exposição (B3: 1 contrato = 100 ações)
LOT_SIZE = 100


# ---------------------------------------------------------------------------
# Colunas da tabela de risco (para persistência futura)
# ---------------------------------------------------------------------------
OPTIONS_RISK_COLUMNS = [
    "captured_at",
    "trade_date",
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    # Métricas de risco
    "option_risk_score",
    "max_loss",
    "premium_at_risk",
    "delta_exposure",
    "gamma_exposure",
    "theta_daily",
    "vega_exposure",
    "spread_risk",
    "dte_risk",
    "iv_risk",
    "liquidity_risk",
    "underlying_risk_status",
    # Status
    "blocked",
    "blocking_reasons",
    "trade_date",
]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _db() -> Path:
    return _db_path()


def _empty(columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns or OPTIONS_RISK_COLUMNS
    return pd.DataFrame(columns=cols)


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(val, default=0.0) -> float:
    try:
        f = float(pd.to_numeric(val, errors="coerce").iloc[0])
        return f if pd.notna(f) else default
    except Exception:
        return default


def _blocking_flags(row: pd.Series) -> tuple[bool, list[str]]:
    """Retorna (bloqueada, reasons)."""
    reasons: list[str] = []

    bid = float(pd.to_numeric(row.get("bid", 0), errors="coerce") or 0)
    ask = float(pd.to_numeric(row.get("ask", 0), errors="coerce") or 0)
    last_price = float(pd.to_numeric(row.get("last_price", 0), errors="coerce") or 0)
    spread_pct = float(pd.to_numeric(row.get("spread_pct", 0), errors="coerce") or 0)
    volume = float(pd.to_numeric(row.get("volume", 0), errors="coerce") or 0)
    trades = float(pd.to_numeric(row.get("trades", 0), errors="coerce") or 0)
    dte = int(float(pd.to_numeric(row.get("days_to_maturity", 999), errors="coerce") or 999))
    iv = float(pd.to_numeric(row.get("implied_volatility", 0), errors="coerce") or 0)
    liq = float(pd.to_numeric(row.get("liquidity_score", 0), errors="coerce") or 0)
    delta = float(pd.to_numeric(row.get("delta", 0), errors="coerce") or 0)
    intrinsic = float(pd.to_numeric(row.get("intrinsic_value", 0), errors="coerce") or 0)
    extrinsic = float(pd.to_numeric(row.get("extrinsic_value", 0), errors="coerce") or 0)

    # B01: bid/ask inválido
    # Regras simplificadas:
    # - bid > 0 AND ask > 0 AND bid <= ask → PASS (cotação normal)
    # - bid = 0 AND ask = 0 AND last_price > 0 AND extrinsic > 0 → PASS (deep ITM, bid/ask N/A em cotahist)
    # - bid = 0 AND ask = 0 AND last_price > 0 AND extrinsic <= 0 → BLOCK (preço = 0, sem justification)
    # - bid > 0 AND ask <= 0 → BLOCK (incomplete quote)
    # - bid <= 0 AND ask > 0 → BLOCK (cotação incompleta, bid obrigatório)
    # - bid > ask → BLOCK (clearly erroneous)
    if bid > 0 and ask > 0 and bid <= ask:
        pass  # Normal quote: PASS
    elif bid <= 0 and ask <= 0:
        if last_price <= 0 or extrinsic <= 0:
            reasons.append("B01_INVALID_BIDASK")
        # else: PASS — deep ITM sem bid/ask é aceitável
    elif bid > 0 and ask <= 0:
        reasons.append("B01_INVALID_BIDASK")
    elif bid <= 0 and ask > 0:
        reasons.append("B01_INVALID_BIDASK")
    elif bid > ask:
        reasons.append("B01_INVALID_BIDASK")

    # B02: spread excessivo
    if spread_pct > MAX_SPREAD_PCT:
        reasons.append("B02_EXCESSIVE_SPREAD")

    # B03: sem volume nem trades
    if volume == 0 and trades == 0:
        reasons.append("B03_NO_VOLUME_TRADES")

    # B04: DTE muito curto
    if dte < MIN_DTE:
        reasons.append("B04_DTE_CRITICAL")

    # B05: IV inválida
    if iv < MIN_IV or iv > MAX_IV:
        reasons.append("B05_INVALID_IV")

    # B06: ilíquida
    if liq < MIN_LIQUIDITY:
        reasons.append("B06_ILLIQUID")

    # B07: max_loss indefinido (preço inválido)
    if last_price <= 0:
        reasons.append("B07_MAX_LOSS_UNDEFINED")

    # B08: delta fora de range
    delta_abs = abs(delta)
    if delta_abs > MAX_DELTA_ABS:
        reasons.append("B08_DELTA_OUT_OF_RANGE")

    blocked = len(reasons) > 0
    return blocked, reasons


def _compute_risk_metrics(row: pd.Series, underlying_price: float) -> dict:
    """Calcula métricas de risco para uma opção."""
    delta = float(pd.to_numeric(row.get("delta", 0), errors="coerce") or 0)
    gamma = float(pd.to_numeric(row.get("gamma", 0), errors="coerce") or 0)
    theta = float(pd.to_numeric(row.get("theta", 0), errors="coerce") or 0)
    vega = float(pd.to_numeric(row.get("vega", 0), errors="coerce") or 0)
    bid = float(pd.to_numeric(row.get("bid", 0), errors="coerce") or 0)
    ask = float(pd.to_numeric(row.get("ask", 0), errors="coerce") or 0)
    last_price = float(pd.to_numeric(row.get("last_price", 0), errors="coerce") or 0)
    spread_pct = float(pd.to_numeric(row.get("spread_pct", 0), errors="coerce") or 0)
    dte = int(float(pd.to_numeric(row.get("days_to_maturity", 999), errors="coerce") or 999))
    iv = float(pd.to_numeric(row.get("implied_volatility", 0), errors="coerce") or 0)
    liq = float(pd.to_numeric(row.get("liquidity_score", 0), errors="coerce") or 0)
    option_type = str(row.get("option_type", "")).upper()
    strike = float(pd.to_numeric(row.get("strike", 0), errors="coerce") or 0)

    # option_risk_score — usa o risk_score da chain (composto)
    option_risk_score = float(pd.to_numeric(row.get("risk_score", 50), errors="coerce") or 50)

    # max_loss — perda máxima por contrato
    # Calls: max loss = premio pago (bid se disponível, senão ask, senão last_price)
    # Se nada disponível: None (→ B07)
    # Nota: opções deep ITM com bid=0/ask>0 são bloqueadas por B01 (não tradable)
    if bid > 0:
        max_loss = bid
    elif ask > 0:
        max_loss = ask
    elif last_price > 0:
        max_loss = last_price
    else:
        max_loss = None  # indefinido → B07

    # premium_at_risk — prêmio em risco = bid × LOT_SIZE (1 contrato)
    premium_at_risk = bid * LOT_SIZE if bid > 0 else 0.0

    # delta_exposure = delta × underlying_price × LOT_SIZE
    delta_exposure = delta * underlying_price * LOT_SIZE

    # gamma_exposure = gamma × underlying_price² × LOT_SIZE
    gamma_exposure = gamma * underlying_price * underlying_price * LOT_SIZE

    # theta_daily = theta × LOT_SIZE (em R$/dia)
    theta_daily = theta * LOT_SIZE

    # vega_exposure = vega × 0.01 (1% change in IV)
    vega_exposure = vega * 0.01

    # spread_risk — pct do preço (0=ótimo, 100=inutilizável)
    spread_risk = min(spread_pct, 100.0)

    # dte_risk — scoring de risco temporal
    # 0-3 DTE: crítico (100), 4-7: alto (75), 8-21: médio (50), 22-60: baixo (25), 61+: mínimo (10)
    if dte < 3:
        dte_risk = 100.0
    elif dte < 8:
        dte_risk = 75.0
    elif dte <= 21:
        dte_risk = 50.0
    elif dte <= 60:
        dte_risk = 25.0
    else:
        dte_risk = 10.0

    # iv_risk — risco de volatilidade
    # IV > 80% = alto, > 150% = crítico, < 10% = anomalamente baixa
    if iv <= 0 or iv > MAX_IV:
        iv_risk = 100.0
    elif iv > 1.5:
        iv_risk = 75.0
    elif iv > 0.8:
        iv_risk = 50.0
    elif iv < 0.10:
        iv_risk = 50.0
    else:
        iv_risk = 25.0

    # liquidity_risk — 0 = totalmente líquido, 100 = totalmente ilíquido
    liquidity_risk = max(0.0, 100.0 - liq)

    # underlying_risk_status — placeholder (será conectado ao risk_snapshots em S04+)
    underlying_risk_status = "UNKNOWN"

    return {
        "option_risk_score": option_risk_score,
        "max_loss": max_loss,
        "premium_at_risk": premium_at_risk,
        "delta_exposure": round(delta_exposure, 2),
        "gamma_exposure": round(gamma_exposure, 2),
        "theta_daily": round(theta_daily, 4),
        "vega_exposure": round(vega_exposure, 4),
        "spread_risk": round(spread_risk, 2),
        "dte_risk": dte_risk,
        "iv_risk": iv_risk,
        "liquidity_risk": round(liquidity_risk, 2),
        "underlying_risk_status": underlying_risk_status,
    }


def _apply_risk_layer(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Adiciona camada de risco a um DataFrame de opções."""
    if df.empty:
        return df

    df = df.copy().reset_index(drop=True)

    # underlying_price — usa o máximo do DataFrame ou fallback
    underlying_price = float(
        pd.to_numeric(df["underlying_price"], errors="coerce").dropna().max() or 0
    )

    # Aplicar blocking flags
    blocked_list: list[bool] = []
    reasons_list: list[list[str]] = []
    for _, row in df.iterrows():
        blocked, reasons = _blocking_flags(row)
        blocked_list.append(blocked)
        reasons_list.append(reasons)

    df["blocked"] = blocked_list
    df["blocking_reasons"] = ["|".join(r) for r in reasons_list]

    # Métricas de risco
    metrics_list = [_compute_risk_metrics(row, underlying_price) for _, row in df.iterrows()]
    metrics_df = pd.DataFrame(metrics_list)
    df = pd.concat([df, metrics_df], axis=1)

    return df


# ---------------------------------------------------------------------------
# Funções principais
# ---------------------------------------------------------------------------

def get_options_risk_snapshot(ticker: str) -> pd.DataFrame:
    """
    Retorna snapshot de risco de todas as opções de um ativo.

    Inclui TODAS as opções (líquidas e ilíquidas) com suas métricas de risco.
    Filtra apenas vencidas (DTE < 0) e bid/ask severamente inválidos.

    Returns
    -------
    DataFrame com colunas OPTIONS_RISK_COLUMNS + métricas + blocked + blocking_reasons.

    Example
    -------
    >>> df = get_options_risk_snapshot("PETR")
    >>> approved = df[~df["blocked"]]
    >>> blocked = df[df["blocked"]]
    """
    db = _db()
    if not db.exists():
        return _empty()

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            """SELECT * FROM options_chain_snapshots
               WHERE underlying = ?
                 AND days_to_maturity >= 0
               ORDER BY days_to_maturity, strike""",
            con, params=(str(ticker).upper(),),
        )

    if df.empty:
        return _empty()

    df = df.dropna(subset=["option_ticker"]).reset_index(drop=True)
    df = _apply_risk_layer(df, ticker)
    return df


def get_option_risk(option_ticker: str) -> dict:
    """
    Retorna perfil de risco de uma opção específica.

    Returns
    -------
    dict com todos os campos de risco ou dict vazio se não encontrada.
    """
    db = _db()
    if not db.exists():
        return {}

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            """SELECT * FROM options_chain_snapshots
               WHERE option_ticker = ?
                 AND days_to_maturity >= 0
               LIMIT 1""",
            con, params=(str(option_ticker).upper(),),
        )

    if df.empty:
        return {}

    row = df.iloc[0]
    ticker = row["underlying"]
    underlying_price = float(pd.to_numeric(row.get("underlying_price", 0), errors="coerce") or 0)
    blocked, reasons = _blocking_flags(row)
    metrics = _compute_risk_metrics(row, underlying_price)

    return {
        "option_ticker": row["option_ticker"],
        "underlying": ticker,
        "option_type": row["option_type"],
        "strike": row["strike"],
        "maturity_date": row["maturity_date"],
        "days_to_maturity": row["days_to_maturity"],
        "last_price": row["last_price"],
        "bid": row["bid"],
        "ask": row["ask"],
        "implied_volatility": row["implied_volatility"],
        "delta": row["delta"],
        "gamma": row["gamma"],
        "theta": row["theta"],
        "vega": row["vega"],
        "liquidity_score": row["liquidity_score"],
        "blocked": blocked,
        "blocking_reasons": "|".join(reasons) if reasons else "",
        "is_blocked": blocked,
        "status": "BLOCKED" if blocked else "APPROVED",
        **metrics,
    }


def get_low_risk_options(
    ticker: str,
    option_type: Literal["CALL", "PUT"] | None = None,
    max_spread_pct: float = 50.0,
    min_dte: int = 3,
    max_dte: int | None = None,
) -> pd.DataFrame:
    """
    Retorna opções APROVADAS (não bloqueadas) de um ativo.

    Filtros padrão:
      - liquidity_score >= 50 (líquidas S01.5)
      - bid > 0, ask > 0, bid <= ask
      - spread_pct <= max_spread_pct (default 50%)
      - DTE >= min_dte (default 3)
      - DTE <= max_dte (opcional)
      - IV > 0 (Greeks computados)

    Returns
    -------
    DataFrame de opções aprovadas com métricas de risco.
    """
    db = _db()
    if not db.exists():
        return _empty()

    ticker_upper = str(ticker).upper()
    sql_where = ["underlying = ?"]
    params: list = [ticker_upper]

    sql_where += [
        "bid > 0 AND ask > 0 AND bid <= ask",
        "liquidity_score >= ?",
        "implied_volatility > 0",
        "days_to_maturity >= ?",
        "spread_pct <= ?",
    ]
    params += [str(MIN_LIQUIDITY), str(min_dte), str(max_spread_pct)]

    if max_dte is not None:
        sql_where.append("days_to_maturity <= ?")
        params.append(str(max_dte))

    if option_type:
        sql_where.append("option_type = ?")
        params.append(str(option_type).upper())

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            f"""SELECT * FROM options_chain_snapshots
                WHERE {' AND '.join(sql_where)}
                ORDER BY days_to_maturity, strike""",
            con, params=params,
        )

    if df.empty:
        return _empty()

    df = _apply_risk_layer(df, ticker_upper)
    # Filtra bloqueadas
    df = df[~df["blocked"]].reset_index(drop=True)
    return df


def get_options_risk_summary(ticker: str) -> dict:
    """
    Retorna resumo de risco de opções de um ativo.

    Returns
    -------
    dict com contagens, métricas agregadas e breakdowns.
    """
    snapshot = get_options_risk_snapshot(ticker)

    if snapshot.empty:
        return {"ticker": str(ticker).upper(), "status": "NO_OPTIONS"}

    total = len(snapshot)
    approved = int((~snapshot["blocked"]).sum())
    blocked_count = int(snapshot["blocked"].sum())

    # Breakdown por reason
    reason_counts: dict[str, int] = {}
    for reasons_str in snapshot[snapshot["blocked"]]["blocking_reasons"]:
        if not reasons_str:
            continue
        for r in reasons_str.split("|"):
            r = r.strip()
            if r:
                reason_counts[r] = reason_counts.get(r, 0) + 1

    approved_df = snapshot[~snapshot["blocked"]]

    # Métricas sobre aprovadas
    def _safe_mean(col: str) -> float | None:
        vals = pd.to_numeric(approved_df[col], errors="coerce").dropna()
        return float(round(vals.mean(), 4)) if len(vals) > 0 else None

    def _safe_max(col: str) -> float | None:
        vals = pd.to_numeric(approved_df[col], errors="coerce").dropna()
        return float(round(vals.max(), 4)) if len(vals) > 0 else None

    def _safe_min(col: str) -> float | None:
        vals = pd.to_numeric(approved_df[col], errors="coerce").dropna()
        return float(round(vals.min(), 4)) if len(vals) > 0 else None

    calls_approved = int((approved_df["option_type"] == "CALL").sum()) if not approved_df.empty else 0
    puts_approved = int((approved_df["option_type"] == "PUT").sum()) if not approved_df.empty else 0

    return {
        "ticker": str(ticker).upper(),
        "status": "OK",
        "total_options_evaluated": total,
        "approved": approved,
        "blocked": blocked_count,
        "approval_rate_pct": round(approved / total * 100, 2) if total > 0 else 0,
        "calls_approved": calls_approved,
        "puts_approved": puts_approved,
        # Breakdown de bloqueios
        "blocking_reasons": dict(sorted(reason_counts.items(), key=lambda x: -x[1])),
        # Métricas sobre aprovadas
        "approved_metrics": {
            "avg_option_risk_score": _safe_mean("option_risk_score"),
            "avg_delta_exposure": _safe_mean("delta_exposure"),
            "avg_gamma_exposure": _safe_mean("gamma_exposure"),
            "avg_theta_daily": _safe_mean("theta_daily"),
            "avg_vega_exposure": _safe_mean("vega_exposure"),
            "avg_spread_risk": _safe_mean("spread_risk"),
            "avg_dte_risk": _safe_mean("dte_risk"),
            "avg_iv_risk": _safe_mean("iv_risk"),
            "avg_liquidity_risk": _safe_mean("liquidity_risk"),
            "total_premium_at_risk": float(pd.to_numeric(approved_df["premium_at_risk"], errors="coerce").sum()),
            "max_delta_exposure": _safe_max("delta_exposure"),
            "max_gamma_exposure": _safe_max("gamma_exposure"),
            "min_theta_daily": _safe_min("theta_daily"),  # theta é negativo → min é "mais negativo"
        },
        "underlying_price": float(
            pd.to_numeric(snapshot["underlying_price"], errors="coerce").dropna().max() or 0
        ),
        "trade_date": str(snapshot["trade_date"].max()),
        "captured_at": str(snapshot["captured_at"].max()),
        "latest_capture": _now(),
    }


def get_options_risk_diagnostics() -> dict:
    """
    Retorna diagnóstico global de risco do universo de opções.

    Avalia TODAS as 40.316 opções e retorna contagens consolidadas.

    Returns
    -------
    dict com:
      total_evaluated, total_approved, total_blocked,
      approval_rate_pct, by_reason, by_underlying,
      priority_underlyings_status, blocking_rules_summary.
    """
    db = _db()
    if not db.exists():
        return {"status": "DB_NOT_FOUND"}

    with sqlite3.connect(str(db)) as con:
        df = pd.read_sql_query(
            """SELECT * FROM options_chain_snapshots
               WHERE days_to_maturity >= 0""",
            con,
        )

    if df.empty:
        return {"status": "NO_OPTIONS_IN_DB"}

    total = len(df)

    # Aplicar blocking flags a todas
    blocked_list: list[bool] = []
    reasons_list: list[list[str]] = []
    for _, row in df.iterrows():
        blocked, reasons = _blocking_flags(row)
        blocked_list.append(blocked)
        reasons_list.append(reasons)

    df["blocked"] = blocked_list
    df["blocking_reasons"] = ["|".join(r) for r in reasons_list]

    total_approved = int((~df["blocked"]).sum())
    total_blocked = int(df["blocked"].sum())
    approval_rate = round(total_approved / total * 100, 2) if total > 0 else 0

    # Por reason
    reason_counts: dict[str, int] = {}
    for reasons_str in df[df["blocked"]]["blocking_reasons"]:
        if not reasons_str:
            continue
        for r in reasons_str.split("|"):
            r = r.strip()
            if r:
                reason_counts[r] = reason_counts.get(r, 0) + 1

    # Por underlying (apenas priority)
    priority = ["PETR", "VALE", "ITUB", "BBAS", "BBDC", "WEGE", "SUZB"]
    priority_status: dict[str, dict] = {}
    for t in priority:
        sub = df[df["underlying"] == t]
        if sub.empty:
            continue
        approved = int((~sub["blocked"]).sum())
        blocked_sub = int(sub["blocked"].sum())
        sub_reasons = {}
        for reasons_str in sub[sub["blocked"]]["blocking_reasons"]:
            if not reasons_str:
                continue
            for r in reasons_str.split("|"):
                r = r.strip()
                if r:
                    sub_reasons[r] = sub_reasons.get(r, 0) + 1
        priority_status[t] = {
            "total_evaluated": len(sub),
            "approved": approved,
            "blocked": blocked_sub,
            "approval_rate_pct": round(approved / len(sub) * 100, 2) if len(sub) > 0 else 0,
            "top_blocking_reasons": dict(sorted(sub_reasons.items(), key=lambda x: -x[1])[:5]),
        }

    # Por underlying (todos)
    by_underlying: list[dict] = []
    for underlying in sorted(df["underlying"].unique()):
        sub = df[df["underlying"] == underlying]
        approved = int((~sub["blocked"]).sum())
        by_underlying.append({
            "underlying": underlying,
            "total_evaluated": len(sub),
            "approved": approved,
            "blocked": int(sub["blocked"].sum()),
            "approval_rate_pct": round(approved / len(sub) * 100, 1) if len(sub) > 0 else 0,
        })

    # Bloqueios por underlying (top reasons)
    blocked_df = df[df["blocked"]]
    by_underlying_blocked: list[dict] = []
    for underlying in sorted(blocked_df["underlying"].unique()):
        sub = blocked_df[blocked_df["underlying"] == underlying]
        reasons_counts: dict[str, int] = {}
        for reasons_str in sub["blocking_reasons"]:
            if not reasons_str:
                continue
            for r in reasons_str.split("|"):
                r = r.strip()
                if r:
                    reasons_counts[r] = reasons_counts.get(r, 0) + 1
        by_underlying_blocked.append({
            "underlying": underlying,
            "blocked": len(sub),
            "top_reasons": dict(sorted(reasons_counts.items(), key=lambda x: -x[1])[:3]),
        })

    return {
        "status": "OK",
        "evaluated_at": _now(),
        "data_captured_at": str(df["captured_at"].max()),
        "trade_date": str(df["trade_date"].max()),
        # Totais
        "total_evaluated": total,
        "total_approved": total_approved,
        "total_blocked": total_blocked,
        "approval_rate_pct": approval_rate,
        # Por reason
        "by_reason": dict(sorted(reason_counts.items(), key=lambda x: -x[1])),
        # Por underlying
        "by_underlying": by_underlying,
        "by_underlying_count": len(by_underlying),
        # Priority underlyings
        "priority_underlyings": priority_status,
        # Bloqueios por underlying
        "blocked_by_underlying": by_underlying_blocked,
        "blocked_by_underlying_count": len(by_underlying_blocked),
        # Regras aplicadas
        "blocking_rules_summary": {
            "B01_INVALID_BIDASK": {
                "description": "bid <= 0 ou ask <= 0 ou bid > ask",
                "active": True,
            },
            "B02_EXCESSIVE_SPREAD": {
                "description": f"spread_pct > {MAX_SPREAD_PCT}%",
                "active": True,
            },
            "B03_NO_VOLUME_TRADES": {
                "description": "volume == 0 E trades == 0",
                "active": True,
            },
            "B04_DTE_CRITICAL": {
                "description": f"DTE < {MIN_DTE}",
                "active": True,
            },
            "B05_INVALID_IV": {
                "description": f"IV <= {MIN_IV} ou IV > {MAX_IV}",
                "active": True,
            },
            "B06_ILLIQUID": {
                "description": f"liquidity_score < {MIN_LIQUIDITY}",
                "active": True,
            },
            "B07_MAX_LOSS_UNDEFINED": {
                "description": "preço == 0 (max_loss indefinido)",
                "active": True,
            },
            "B08_DELTA_OUT_OF_RANGE": {
                "description": f"|delta| > {MAX_DELTA_ABS}",
                "active": True,
            },
        },
        "notes": [
            "Blocking flags são aplicadas em série — uma opção pode ter múltiplos bloqueios",
            "options_risk_snapshot é calculado on-the-fly (não persiste tabela separada)",
            "underlying_risk_status = UNKNOWN por enquanto (será conectado em S04+)",
            "M007 intacto — nenhuma modificação em valuation_bridge ou asset_intelligence_engine",
        ],
    }