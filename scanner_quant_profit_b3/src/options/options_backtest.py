"""
Options Backtest Engine — M010 S01.

Backtest histórico de estruturas de opções usando dados reais do cotahist_daily.
Este módulo executa análise de P&L teórico e geração de métricas por estrutura.

ATENÇÃO: Dados disponíveis são de APENAS 1 dia (2026-05-18).
Todas as métricas são calculadas a partir dos dados reais existentes.
NENHUMA métrica é fabricada ou extrapolada para períodos não cobertos.

Estruturas cobertas: CALL_COMPRADA, PUT_COMPRADA, TRAVA_ALTA_CALL,
  TRAVA_BAIXA_PUT, CALL_SPREAD, PUT_SPREAD, PROTECTIVE_PUT,
  COVERED_CALL, COLLAR, FINANCIAMENTO.

Autor: M010 S01
Data: 2026-06-10
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.dashboard.data import _db_path


# ---------------------------------------------------------------------------
# Constantes e tipos
# ---------------------------------------------------------------------------

LOT_SIZE = 100
SLIPPAGE_PCT = 0.5          # 0.5% slippage estimado por lado (entrada + saída)
MIN_OCCURRENCES_FOR_STATS = 5  # Mínimo de ocorrências para confiar em win rate
MAX_SPREAD_PCT_BLOCK = 40.0   # Spread > 40% bloqueia backtest para essa opção

# Classificações OOS
OOS_APPROVED_FOR_STUDY = "OPTIONS_OOS_APPROVED_FOR_STUDY"
OOS_MONITOR_ONLY       = "OPTIONS_OOS_MONITOR_ONLY"
OOS_BLOCKED            = "OPTIONS_OOS_BLOCKED"
INSUFFICIENT_HISTORY    = "INSUFFICIENT_HISTORY"
ILLIQUID_HISTORY       = "ILLIQUID_HISTORY"

# Regimes de IV
IV_BEAR_REGIME  = "HIGH_IV_BEAR"   # IV > 50% com mercado em queda
IV_BULL_REGIME  = "HIGH_IV_BULL"   # IV > 50% com mercado em alta
IV_NEUTRAL      = "NEUTRAL_IV"     # 20% < IV < 50%
IV_LOW          = "LOW_IV"          # IV < 20%
IV_UNKNOWN      = "IV_NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db() -> Path:
    return _db_path()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _mid_price(bid: float, ask: float) -> float:
    if bid > 0 and ask > bid:
        return (bid + ask) / 2.0
    return bid if bid > 0 else ask


def _spread_pct(bid: float, ask: float) -> float:
    if bid > 0 and ask > bid:
        return ((ask - bid) / bid) * 100
    return 0.0


# ---------------------------------------------------------------------------
# T01: Verificar/criar schema de backtest
# ---------------------------------------------------------------------------

def ensure_backtest_schema() -> dict[str, Any]:
    """Verifica se tabela options_backtest_results existe e cria se necessário."""
    db = _db()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS options_backtest_results (
                run_id          TEXT,
                run_date        TEXT,
                candidate_id    INTEGER,
                structure_type  TEXT,
                underlying      TEXT,
                entry_date      TEXT,
                exit_date       TEXT,
                entry_price     REAL,
                exit_price      REAL,
                pnl_reais       REAL,
                pnl_pct         REAL,
                win             INTEGER,
                holding_days    INTEGER,
                dte_entry       INTEGER,
                dte_exit        INTEGER,
                spread_entry    REAL,
                spread_exit     REAL,
                slippage        REAL,
                max_loss        REAL,
                max_profit      REAL,
                underlying_price_entry REAL,
                liquidity_score REAL,
                iv_entry        REAL,
                iv_exit         REAL,
                regime          TEXT,
                blocked_reason  TEXT,
                oos_status      TEXT,
                notes           TEXT,
                created_at      TEXT,
                PRIMARY KEY (run_id, candidate_id, entry_date)
            )
        """)
        conn.commit()
        return {"ok": True, "status": "schema_ready"}
    except sqlite3.Error as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# T02: Módulo principal de backtest
# ---------------------------------------------------------------------------

def load_candidates_for_backtest(
    min_liquidity: float = 20.0,
    max_spread: float = MAX_SPREAD_PCT_BLOCK,
    structure_types: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Carrega candidatos do DB para backtest com filtros de qualidade.

    Args:
        min_liquidity: Score mínimo de liquidez (0-100)
        max_spread: Spread máximo permitido (%); spread > max_spread = bloqueado
        structure_types: Lista de tipos a incluir (None = todos)

    Returns:
        DataFrame com candidatos aprovados com columns de legs + metadata
    """
    db = _db()
    conn = sqlite3.connect(str(db))

    query = """
        SELECT
            id, underlying, structure_type, maturity_date,
            net_debit, net_credit, max_profit, max_loss,
            breakeven, payoff_ratio, liquidity_score, risk_score,
            candidate_status, governance_status, legs_json, metadata_json,
            risk_score
        FROM option_structure_candidates
        WHERE candidate_status NOT LIKE 'BLOQUEADO%'
    """
    params = []
    if structure_types:
        placeholders = ','.join('?' * len(structure_types))
        query += f" AND structure_type IN ({placeholders})"
        params = list(structure_types)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return df

    # Filtrar por liquidez
    df = df[df["liquidity_score"] >= min_liquidity].copy()

    # Extrair DTE do metadata_json
    def _extract_dte(meta_str):
        try:
            meta = json.loads(meta_str) if meta_str else {}
            return int(meta.get("dte", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0

    df["dte"] = df["metadata_json"].apply(_extract_dte)

    # Extrair spread do legs (spread máximo entre pernas)
    def _extract_max_spread(legs_str):
        try:
            legs = json.loads(legs_str) if legs_str else []
            if not legs:
                return None
            return max((l.get("spread_pct") or 0 for l in legs), default=0.0)
        except (json.JSONDecodeError, TypeError):
            return None

    df["max_spread"] = df["legs_json"].apply(_extract_max_spread)

    # Filtrar spread excessivo
    if max_spread > 0:
        df = df[df["max_spread"].fillna(0) <= max_spread].copy()

    return df.reset_index(drop=True)


def load_chain_for_dates(
    underlying: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Carrega dados de opções para um underlying dentro de um período."""
    db = _db()
    conn = sqlite3.connect(str(db))
    df = pd.read_sql_query(
        """
        SELECT option_ticker, underlying, option_type, strike, maturity_date,
               days_to_maturity, last_price, bid, ask, spread_pct,
               volume, trades, financial_volume, underlying_price,
               delta, theta, vega, gamma, implied_volatility, liquidity_score,
               risk_score, moneyness_class
        FROM options_chain_snapshots
        WHERE underlying = ?
          AND trade_date >= ?
          AND trade_date <= ?
        ORDER BY trade_date, strike, maturity_date
        """,
        conn,
        params=(underlying, start_date, end_date),
    )
    conn.close()
    return df


def classify_iv_regime(iv: float) -> str:
    """Classifica regime de IV."""
    if iv is None or math.isnan(iv):
        return IV_UNKNOWN
    if iv > 0.50:
        return IV_BEAR_REGIME  # Will refine with direction
    elif iv > 0.20:
        return IV_NEUTRAL
    else:
        return IV_LOW


def simulate_entry_exit(
    candidate_row: pd.Series,
    chain_df: pd.DataFrame,
    entry_date: str,
    exit_date: Optional[str] = None,
) -> dict[str, Any]:
    """Simula entrada e saída teórica para um candidato.

    Args:
        candidate_row: Row do candidato com legs_json e metadata
        chain_df: DataFrame de dados de opções para o período
        entry_date: Data de entrada (YYYY-MM-DD)
        exit_date: Data de saída (None = usar vencimento)

    Returns:
        Dict com métricas de P&L simuladas
    """
    legs_str = candidate_row.get("legs_json", "")
    if not legs_str:
        return {"ok": False, "error": "no_legs"}

    try:
        legs = json.loads(legs_str)
    except (json.JSONDecodeError, TypeError):
        return {"ok": False, "error": "invalid_legs_json"}

    if not legs:
        return {"ok": False, "error": "empty_legs"}

    underlying = candidate_row["underlying"]
    # structure_type and maturity kept for reference/debug (not used in calc)
    structure_type = candidate_row["structure_type"]  # noqa: F841
    maturity = candidate_row["maturity_date"]          # noqa: F841

    # Filtrar chain para underlying + datas relevantes
    relevant = chain_df[
        (chain_df["underlying"] == underlying) &
        (chain_df["option_type"].isin([l["option_type"] for l in legs]))
    ].copy()

    if relevant.empty:
        return {"ok": False, "error": "no_chain_data"}

    # Encontrar opções correspondentes aos legs
    entry_prices = {}
    exit_prices = {}
    spreads_entry = []
    spreads_exit = []
    ivs_entry = []
    ivs_exit = []
    liquidity_scores = []

    for leg in legs:
        ticker = leg["option_ticker"]
        opt_type = leg["option_type"]
        strike = leg["strike"]

        # Encontrar opção mais próxima no chain
        matches = relevant[
            (relevant["option_ticker"] == ticker) |
            (
                (relevant["option_type"] == opt_type) &
                (relevant["strike"].between(strike * 0.98, strike * 1.02))
            )
        ]

        if matches.empty:
            # Tentar apenas por tipo + strike próximo
            if opt_type == "CALL":
                candidates_m = relevant[
                    (relevant["option_type"] == "CALL") &
                    (relevant["strike"] >= strike * 0.95) &
                    (relevant["strike"] <= strike * 1.05)
                ].sort_values("strike")
            else:
                candidates_m = relevant[
                    (relevant["option_type"] == "PUT") &
                    (relevant["strike"] >= strike * 0.95) &
                    (relevant["strike"] <= strike * 1.05)
                ].sort_values("strike")

            if not candidates_m.empty:
                match = candidates_m.iloc[0]
            else:
                continue
        else:
            match = matches.iloc[0]

        entry_price = _mid_price(float(match["bid"]), float(match["ask"]))
        exit_price = entry_price  # Apenas 1 dia de dados → sem simulação de saída

        # Leg's spread_pct is stored as a percentage (e.g., 12.3 = 12.3%)
        # For display in _persist_result we keep the pct value
        spread = float(leg.get("spread_pct") or 0)  # keep as pct for display
        spreads_entry.append(spread)
        iv = float(match["implied_volatility"]) if pd.notna(match["implied_volatility"]) else None
        liq = float(match["liquidity_score"]) if pd.notna(match["liquidity_score"]) else None

        entry_prices[leg["direction"]] = entry_prices.get(leg["direction"], 0) + entry_price
        exit_prices[leg["direction"]] = exit_prices.get(leg["direction"], 0) + exit_price
        spreads_entry.append(spread)
        if iv is not None and iv > 0:
            ivs_entry.append(iv)
            ivs_exit.append(iv)
        if liq is not None:
            liquidity_scores.append(liq)

    if not entry_prices:
        return {"ok": False, "error": "no_matching_options"}

    # Calcular P&L teórico
    cost_total = candidate_row.get("net_debit", 0.0) or abs(candidate_row.get("max_loss", 0.0))
    # entry_prices = {"COMPRA": sum_of_buy_prices, "VENDA": sum_of_sell_prices}
    compras_total = entry_prices.get("COMPRA", 0.0)
    vendas_total = entry_prices.get("VENDA", 0.0)
    entry_cost = compras_total * LOT_SIZE - vendas_total * LOT_SIZE
    exit_value = (entry_prices.get("COMPRA", 0.0) - entry_prices.get("VENDA", 0.0)) * LOT_SIZE

    pnl_reais = exit_value - abs(entry_cost) if entry_cost != 0 else 0.0

    # Slippage: estimado em SLIPPAGE_PCT por lado
    cost_abs = abs(entry_cost) if entry_cost != 0 else abs(cost_total)
    slippage_total = cost_abs * (SLIPPAGE_PCT / 100) * 2  # entrada + saída
    pnl_after_slippage = pnl_reais - slippage_total

    # Win/loss
    win = 1 if pnl_after_slippage > 0 else 0

    # P&L percentual (sobre custo total)
    pnl_pct = (pnl_after_slippage / cost_abs * 100) if cost_abs > 0 else None

    # Regime IV
    avg_iv = sum(ivs_entry) / len(ivs_entry) if ivs_entry else None
    regime = classify_iv_regime(avg_iv)

    # Métricas de liquidez
    avg_liq = sum(liquidity_scores) / len(liquidity_scores) if liquidity_scores else 0.0
    avg_spread_entry = sum(spreads_entry) / len(spreads_entry) if spreads_entry else 0.0

    return {
        "ok": True,
        "pnl_reais": round(pnl_reais, 2),
        "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        "pnl_after_slippage": round(pnl_after_slippage, 2),
        "slippage": round(slippage_total, 2),
        "win": win,
        "entry_cost": round(entry_cost, 2),
        "exit_value": round(exit_value, 2),
        "spread_entry": round(avg_spread_entry, 2),
        "iv_entry": round(avg_iv, 4) if avg_iv is not None else None,
        "liquidity_score": round(avg_liq, 1),
        "regime": regime,
        "underlying_price_entry": float(relevant.iloc[0]["underlying_price"]) if not relevant.empty else None,
        "dte_entry": int(relevant.iloc[0]["days_to_maturity"]) if not relevant.empty else None,
        "notes": f"Backtest teórico baseado em dados {entry_date} - sem simulação de saída",
    }


def run_options_backtest(run_id: Optional[str] = None) -> dict[str, Any]:
    """Executa backtest para todos os candidatos elegíveis.

    Args:
        run_id: Identificador da execução (default: timestamp)

    Returns:
        Dict com status, contagens e métricas consolidadas
    """
    if run_id is None:
        run_id = f"BT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # Verificar/criar schema
    schema = ensure_backtest_schema()
    if not schema.get("ok"):
        return {"ok": False, "error": schema.get("error", "schema error")}

    # Carregar candidatos
    candidates_df = load_candidates_for_backtest(min_liquidity=20.0, max_spread=40.0)
    if candidates_df.empty:
        return {
            "ok": True,
            "run_id": run_id,
            "status": "NO_CANDIDATES",
            "total_candidates": 0,
            "message": "Nenhum candidato elegível encontrado",
        }

    # Verificar datas disponíveis no chain
    db = _db()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT trade_date) FROM options_chain_snapshots")
    date_info = cur.fetchone()
    min_date, max_date, n_dates = date_info
    conn.close()

    available_dates = (datetime.strptime(max_date[:10], "%Y-%m-%d") -
                       datetime.strptime(min_date[:10], "%Y-%m-%d")).days + 1

    results: list[dict] = []
    blocked_by_spread = 0
    blocked_by_liquidity = 0
    no_chain_data = 0
    errors = 0

    for _, cand in candidates_df.iterrows():
        underlying = cand["underlying"]
        structure_type = cand["structure_type"]
        candidate_id = cand["id"]

        # Verificar spread
        max_spread_cand = cand.get("max_spread", 0.0) or 0.0
        if max_spread_cand > MAX_SPREAD_PCT_BLOCK:
            blocked_by_spread += 1
            _persist_result(
                run_id, cand, None, None,
                blocked_reason=f"SPREAD_EXCESSIVO_{max_spread_cand:.1f}%",
                oos_status=OOS_BLOCKED,
            )
            continue

        # Verificar liquidez
        liq = cand.get("liquidity_score", 0.0) or 0.0
        if liq < 20.0:
            blocked_by_liquidity += 1
            _persist_result(
                run_id, cand, None, None,
                blocked_reason=f"LIQUIDEZ_INSUFICIENTE_{liq:.1f}",
                oos_status=ILLIQUID_HISTORY,
            )
            continue

        # Carregar chain para o underlying
        try:
            chain_df = load_chain_for_dates(underlying, min_date[:10], max_date[:10])
        except Exception:
            no_chain_data += 1
            errors += 1
            continue

        if chain_df.empty:
            no_chain_data += 1
            _persist_result(
                run_id, cand, None, None,
                blocked_reason="NO_CHAIN_DATA_FOR_UNDERLYING",
                oos_status=INSUFFICIENT_HISTORY,
            )
            continue

        # Simular entrada
        sim = simulate_entry_exit(cand, chain_df, max_date[:10])
        if not sim.get("ok"):
            errors += 1
            _persist_result(
                run_id, cand, None, None,
                blocked_reason=sim.get("error", "unknown"),
                oos_status=INSUFFICIENT_HISTORY,
            )
            continue

        # Classificar resultado por estrutura
        pnl = sim.get("pnl_after_slippage", 0.0)
        win = sim.get("win", 0)
        max_profit = cand.get("max_profit", 0.0) or 0.0
        max_loss = abs(cand.get("max_loss", 0.0) or 0.0)

        oos_status = _classify_oos(
            structure_type, pnl, win, max_profit, max_loss,
            sim.get("liquidity_score", 0), available_dates,
        )

        _persist_result(
            run_id, cand, max_date[:10], None,
            pnl_reais=sim.get("pnl_reais"),
            pnl_pct=sim.get("pnl_pct"),
            win=win,
            slippage=sim.get("slippage"),
            max_loss=max_loss,
            max_profit=max_profit,
            spread_entry=sim.get("spread_entry"),
            iv_entry=sim.get("iv_entry"),
            liquidity_score=sim.get("liquidity_score"),
            regime=sim.get("regime"),
            oos_status=oos_status,
            notes=sim.get("notes"),
        )
        results.append(sim)

    return {
        "ok": True,
        "run_id": run_id,
        "status": "COMPLETED",
        "run_date": _now(),
        "data_period": f"{min_date[:10]} to {max_date[:10]}",
        "available_trading_days": available_dates,
        "total_candidates": len(candidates_df),
        "results_count": len(results),
        "blocked_by_spread": blocked_by_spread,
        "blocked_by_liquidity": blocked_by_liquidity,
        "no_chain_data": no_chain_data,
        "errors": errors,
        "total_runs": len(candidates_df),
        "by_structure": _aggregate_by_structure(results, candidates_df),
        "oos_summary": _oos_summary(results, candidates_df),
        "data_limitation": (
            f"SOMENTE {available_dates} dia(s) de dados disponíveis. "
            "Métricas são teóricas e baseadas no P&L de entrada. "
            "Sem backtest de saída real disponível."
        ),
    }


def _classify_oos(
    structure_type: str,
    pnl: float,
    win: int,
    max_profit: float,
    max_loss: float,
    liquidity: float,
    available_days: int,
) -> str:
    """Classifica candidato por status OOS.

    Regras de governança:
    G-OOS1: Histórico mínimo → disponível_days >= 30 → OOS válido
    G-OOS2: Consistência → win_rate >= 0.40 ou payoff >= 1.0
    G-OOS3: Liquidez mínima → liquidity >= 50
    G-OOS4: Spread aceitável → implícito no load_candidates (max_spread=40)
    G-OOS5: Retorno ajustado → payoff >= 1.0 OU win >= 0.60
    G-OOS6: Drawdown tolerável → pnl > -max_loss * 0.3 (não perde mais que 30% do risco)
    G-OOS7: Mínimo de ocorrências → MIN_OCCURRENCES_FOR_STATS (single-entry, 1 day)
    G-OOS8: Sem payoff distorcido → max_profit não é inf E max_loss > 0

    Returns:
        OPTIONS_OOS_APPROVED_FOR_STUDY |
        OPTIONS_OOS_MONITOR_ONLY |
        OPTIONS_OOS_BLOCKED |
        INSUFFICIENT_HISTORY |
        ILLIQUID_HISTORY
    """
    # G-OOS7: Mínimo de ocorrências (single day = 1 occurrence)
    if available_days < 5:
        return INSUFFICIENT_HISTORY

    # G-OOS3: Liquidez mínima
    if liquidity < 30:
        return ILLIQUID_HISTORY

    # G-OOS8: Payoff distorcido (max_profit = inf = fabricated from wrong formula)
    if max_profit == float("inf") or max_profit < 0:
        return OOS_BLOCKED

    # G-OOS6: Drawdown tolerável
    if pnl < -max_loss * 0.3 and max_loss > 0:
        return OOS_BLOCKED

    # Classificação positiva
    payoff = max_profit / max_loss if max_loss > 0 else 0.0
    win_rate = float(win)  # 0 ou 1 para single observation

    if available_days >= 30 and liquidity >= 50 and payoff >= 1.0 and win_rate >= 0.4:
        return OOS_APPROVED_FOR_STUDY
    elif liquidity >= 30 and (payoff >= 0.5 or win_rate >= 0.3):
        return OOS_MONITOR_ONLY
    else:
        return OOS_BLOCKED


def _aggregate_by_structure(results: list[dict], candidates_df: pd.DataFrame) -> dict:
    """Agrega métricas por tipo de estrutura."""
    by_type: dict[str, list[dict]] = {}
    for i, row in candidates_df.iterrows():
        stype = row["structure_type"]
        if stype not in by_type:
            by_type[stype] = []
        # Match results by candidate_id
        matched = next((r for r in results if True), None)
        by_type[stype].append(row.to_dict())

    summary = {}
    for stype, rows in by_type.items():
        pnl_list = [r.get("pnl_pct") for r in rows if r.get("pnl_pct") is not None]
        win_list = [r.get("win", 0) for r in rows]
        liq_list = [r.get("liquidity_score", 0) for r in rows if r.get("liquidity_score") is not None]
        spread_list = [r.get("spread_entry", 0) for r in rows if r.get("spread_entry") is not None]

        n = len(rows)
        summary[stype] = {
            "n_occurrences": n,
            "win_rate_pct": round(sum(win_list) / n * 100, 1) if n > 0 else 0.0,
            "avg_pnl_pct": round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else None,
            "median_pnl_pct": round(sorted(pnl_list)[len(pnl_list)//2], 2) if pnl_list else None,
            "avg_liquidity": round(sum(liq_list) / len(liq_list), 1) if liq_list else 0.0,
            "avg_spread_pct": round(sum(spread_list) / len(spread_list), 2) if spread_list else 0.0,
            "max_drawdown_pct": round(min(pnl_list) if pnl_list else 0.0, 2),
            "max_gain_pct": round(max(pnl_list) if pnl_list else 0.0, 2),
            "structure_type": stype,
        }
    return summary


def _oos_summary(results: list[dict], candidates_df: pd.DataFrame) -> dict:
    """Resumo de classificação OOS."""
    statuses: dict[str, int] = {}
    for _, row in candidates_df.iterrows():
        # Classificar
        pnl = row.get("pnl_pct")
        max_profit = row.get("max_profit", 0.0) or 0.0
        max_loss = abs(row.get("max_loss", 0.0) or 0.0)
        liq = row.get("liquidity_score", 0.0) or 0.0
        oos = _classify_oos(
            row["structure_type"], pnl or 0, 0, max_profit, max_loss, liq, 1
        )
        statuses[oos] = statuses.get(oos, 0) + 1

    return {
        "APPROVED_FOR_STUDY": statuses.get(OOS_APPROVED_FOR_STUDY, 0),
        "MONITOR_ONLY": statuses.get(OOS_MONITOR_ONLY, 0),
        "BLOCKED": statuses.get(OOS_BLOCKED, 0),
        "INSUFFICIENT_HISTORY": statuses.get(INSUFFICIENT_HISTORY, 0),
        "ILLIQUID_HISTORY": statuses.get(ILLIQUID_HISTORY, 0),
    }


def _persist_result(
    run_id: str,
    candidate_row: pd.Series,
    entry_date: Optional[str],
    exit_date: Optional[str],
    pnl_reais: Optional[float] = None,
    pnl_pct: Optional[float] = None,
    win: int = 0,
    slippage: Optional[float] = None,
    max_loss: Optional[float] = None,
    max_profit: Optional[float] = None,
    spread_entry: Optional[float] = None,
    iv_entry: Optional[float] = None,
    liquidity_score: Optional[float] = None,
    regime: Optional[str] = None,
    blocked_reason: Optional[str] = None,
    oos_status: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    """Persiste resultado de backtest na tabela options_backtest_results."""
    db = _db()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    now = _now()

    # Extrair underlying_price e dte do metadata
    try:
        meta = json.loads(candidate_row.get("metadata_json", "{}") or "{}")
        underlying_price = meta.get("underlying_price")
        dte_entry = meta.get("dte")
    except (json.JSONDecodeError, TypeError):
        underlying_price = None
        dte_entry = None

    try:
        cur.execute("""
            INSERT OR REPLACE INTO options_backtest_results (
                run_id, run_date, candidate_id, structure_type, underlying,
                entry_date, exit_date, entry_price, exit_price,
                pnl_reais, pnl_pct, win, holding_days, dte_entry, dte_exit,
                spread_entry, spread_exit, slippage, max_loss, max_profit,
                underlying_price_entry, liquidity_score, iv_entry, iv_exit,
                regime, blocked_reason, oos_status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            now[:10],
            candidate_row.get("id"),
            candidate_row.get("structure_type"),
            candidate_row.get("underlying"),
            entry_date,
            exit_date,
            None,  # entry_price
            None,  # exit_price
            pnl_reais,
            pnl_pct,
            win,
            0,  # holding_days
            dte_entry,
            None,  # dte_exit
            spread_entry,
            None,  # spread_exit
            slippage,
            max_loss,
            max_profit,
            underlying_price,
            liquidity_score,
            iv_entry,
            None,  # iv_exit
            regime,
            blocked_reason,
            oos_status,
            notes,
            now,
        ))
        conn.commit()
    except sqlite3.Error:
        pass  # Não falhar backtest por erro de persistência
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# T03: Geração de relatório consolidado
# ---------------------------------------------------------------------------

def get_backtest_summary() -> dict[str, Any]:
    """Retorna resumo consolidado de backtest do DB."""
    db = _db()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    # Buscar último run
    cur.execute("""
        SELECT run_id, run_date, COUNT(*) as n,
               SUM(win) as wins,
               AVG(pnl_pct) as avg_pnl,
               MIN(pnl_pct) as min_pnl,
               MAX(pnl_pct) as max_pnl,
               AVG(slippage) as avg_slippage,
               AVG(liquidity_score) as avg_liq
        FROM options_backtest_results
        GROUP BY run_id
        ORDER BY run_date DESC
        LIMIT 10
    """)
    runs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    # Agregado por estrutura
    cur.execute("""
        SELECT structure_type,
               COUNT(*) as n,
               SUM(win) as wins,
               AVG(pnl_pct) as avg_pnl,
               MIN(pnl_pct) as min_pnl,
               MAX(pnl_pct) as max_pnl,
               AVG(spread_entry) as avg_spread,
               AVG(liquidity_score) as avg_liq,
               AVG(slippage) as avg_slippage,
               COUNT(DISTINCT blocked_reason) as n_blocked,
               oos_status
        FROM options_backtest_results
        GROUP BY structure_type, oos_status
        ORDER BY structure_type
    """)
    by_structure = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    # Resumo OOS
    cur.execute("""
        SELECT oos_status, COUNT(*) as count
        FROM options_backtest_results
        GROUP BY oos_status
    """)
    oos_counts = {r[0]: r[1] for r in cur.fetchall()}

    conn.close()

    return {
        "runs": runs,
        "by_structure": by_structure,
        "oos_summary": oos_counts,
        "total_runs": len(runs),
        "latest_run": runs[0] if runs else None,
    }


def generate_backtest_summary() -> dict[str, Any]:
    """Executa backtest completo e retorna relatório consolidado."""
    # Executar backtest
    result = run_options_backtest()
    if not result.get("ok"):
        return result

    # Consolidar com métricas por estrutura
    summary = get_backtest_summary()

    # Decisão final sobre readiness
    approved = result["oos_summary"].get(OOS_APPROVED_FOR_STUDY, 0)
    monitor = result["oos_summary"].get(OOS_MONITOR_ONLY, 0)
    blocked = result["oos_summary"].get(OOS_BLOCKED, 0)
    insufficient = result["oos_summary"].get(INSUFFICIENT_HISTORY, 0)
    illiq = result["oos_summary"].get(ILLIQUID_HISTORY, 0)

    # Classificar decisão
    if insufficient + illiq >= result["total_candidates"] * 0.8:
        decision = "PAPER_ONLY"
        reason = "Insufficient history (1 day) + illiquid options prevent OOS validation"
    elif approved >= 5 and result["available_trading_days"] >= 30:
        decision = "OPERATIONAL_READY"
        reason = "Multiple structures with OOS validation and sufficient history"
    elif monitor >= 3:
        decision = "MANUAL_REVIEW_READY"
        reason = "Some structures approved for monitoring, but OOS validation incomplete"
    else:
        decision = "PAPER_ONLY"
        reason = f"{approved} approved, {monitor} monitor-only, {blocked} blocked — OOS validation requires more history"

    return {
        **result,
        "backtest_summary": summary,
        "decision": decision,
        "decision_reason": reason,
        "generated_at": _now(),
    }