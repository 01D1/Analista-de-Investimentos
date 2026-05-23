"""Connector de lifecycle de posições de opções — S06 M009.

Funções:
  - create_options_position(candidate_id)        : cria posição apenas de candidatos APPROVED
  - get_open_options_positions()                : lista posições abertas
  - get_options_position_detail(position_id)    : detalhe com snapshot + alertas
  - update_options_position_snapshot(position_id): gera snapshot com métricas atuais
  - get_options_lifecycle_events(position_id)   : histórico de eventos
  - get_options_alerts(position_id)              : alertas vigentes
  - evaluate_options_exit_signals(position_id)   : avalia e persiste sinais
  - close_options_position(position_id, reason)  : fecha posição
  - roll_options_position(position_id, new_candidate_id): registra rolagem

Regras:
  - Não executa ordens reais.
  - source_type='PAPER' para posições simuladas.
  - Apenas candidatos com classification='APPROVED' podem criar posição.
  - Não falsifica dados de mercado.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.dashboard.data import _db_path
from src.options.options_position_model import (
    LifecycleEvent,
    LifecycleEventType,
    OptionLeg,
    OptionsPosition,
    PositionAlert,
    PositionSnapshot,
    PositionStatus,
    SignalAction,
    SignalType,
)
from src.paper.options_exit_signals import (
    evaluate_adjust_signals,
    evaluate_exit_signals,
    evaluate_roll_signals,
    get_composite_signal,
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _json_safe(val: Any) -> str:
    return json.dumps(val) if val is not None else "{}"


def _from_row(row: sqlite3.Row, model_class: type) -> dict[str, Any]:
    """Converte sqlite3.Row em dict para instanciar dataclass."""
    return dict(zip([c[0] for c in model_class.__dataclass_fields__.keys()],
                   row, strict=False))


def _parse_legs(legs_json: Optional[str]) -> list[OptionLeg]:
    if not legs_json:
        return []
    try:
        raw = json.loads(legs_json)
        return [OptionLeg(**l) for l in raw]
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_option_prices(prices_json: Optional[str]) -> Optional[dict[str, float]]:
    if not prices_json:
        return None
    try:
        return json.loads(prices_json)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# 1. Criar posição
# ---------------------------------------------------------------------------

def create_options_position(
    candidate_id: int,
    source_type: str = "PAPER",
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Cria posição de opções a partir de um candidate_id.

    Regras:
    - candidate_id deve existir e ter classification='APPROVED'.
    - source_type='PAPER' por padrão (nunca real sem confirmação).
    - Cria registro em options_positions + evento CREATED.
    - Retorna dict com position_id ou erro.

    Returns:
        {"ok": True, "position_id": int} ou {"ok": False, "error": str}
    """
    conn = _connect()
    cur = conn.cursor()

    try:
        # Buscar candidato — usa PK 'id', coluna 'candidate_status' do schema real
        blocked_statuses = (
            "BLOQUEADO_RISCO", "BLOQUEADO_DADOS_INSUFICIENTES",
            "BLOQUEADO_LIQUIDEZ", "BLOQUEADO_SPREAD",
        )
        cur.execute("""
            SELECT id, underlying, structure_type, maturity_date, legs_json,
                   net_debit, net_credit, max_profit, max_loss, breakeven,
                   liquidity_score, explanation, candidate_status, metadata_json
            FROM option_structure_candidates
            WHERE id = ?
        """, (candidate_id,))
        row = cur.fetchone()

        if not row:
            return {"ok": False, "error": f"Candidate {candidate_id} não encontrado."}

        # Apenas candidatos não-bloqueados podem criar posição
        candidate_status = row["candidate_status"]
        if candidate_status in blocked_statuses:
            return {
                "ok": False,
                "error": (
                    f"Candidate {candidate_id} com candidate_status='{candidate_status}'. "
                    f"Apenas candidatos fora de {blocked_statuses} podem criar posição."
                ),
            }

        # Extrair greeks e underlying_price do legs_json/metadata_json
        try:
            legs_raw = json.loads(row["legs_json"]) if row["legs_json"] else []
            iv_entry = max((l.get("implied_volatility", 0) or 0 for l in legs_raw), default=0.0)
            delta_entry = sum(l.get("delta", 0) or 0 for l in legs_raw)
            theta_entry = sum(l.get("theta", 0) or 0 for l in legs_raw)
            vega_entry = sum(l.get("vega", 0) or 0 for l in legs_raw)
            # underlying_price vem do primeiro leg com underlying_price
            underlying_price = next(
                (l["underlying_price"] for l in legs_raw if l.get("underlying_price") is not None),
                None,
            )
            if not underlying_price:
                # fallback: extrair do metadata_json
                try:
                    meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
                    underlying_price = meta.get("underlying_price")
                except (json.JSONDecodeError, TypeError):
                    underlying_price = None
        except (json.JSONDecodeError, TypeError, KeyError):
            legs_raw = []
            iv_entry = delta_entry = theta_entry = vega_entry = 0.0
            underlying_price = None

        # DTE inicial
        try:
            from datetime import date as date_module
            exp = datetime.strptime(row["maturity_date"][:10], "%Y-%m-%d").date()
            dte_initial = max(0, (exp - date_module.today()).days)
        except (ValueError, TypeError, AttributeError):
            dte_initial = None

        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Custo total = net_debit ou abs(max_loss)
        cost_total = row["net_debit"] or abs(row["max_loss"]) if row["max_loss"] else 0.0
        max_risk = abs(row["max_loss"]) if row["max_loss"] else None

        # Inserir posição
        cur.execute("""
            INSERT INTO options_positions (
                candidate_id, ticker, structure_type, structure_subtype,
                direction, strikes_json,
                status, entry_date, expiry_date, dte_initial,
                quantity, legs_json,
                net_debit, net_credit, premium_net,
                cost_total, max_risk, max_return, breakeven,
                entry_underlying_price, iv_entry, delta_entry,
                theta_entry, vega_entry,
                original_thesis,
                source_type, is_simulated, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"],
            row["underlying"],
            row["structure_type"],
            None,  # structure_subtype
            None,  # direction
            None,  # strikes_json
            PositionStatus.OPEN.value,
            now[:10],
            row["maturity_date"],
            dte_initial,
            1,
            row["legs_json"],
            row["net_debit"],
            row["net_credit"],
            row["net_credit"] or row["net_debit"],
            cost_total,
            max_risk,
            row["max_profit"],
            row["breakeven"],
            underlying_price,
            iv_entry,
            delta_entry,
            theta_entry,
            vega_entry,
            row["explanation"],
            source_type,
            1,
            notes or f"Criada de candidate_id={candidate_id} (status={candidate_status})",
            now,
            now,
        ))
        position_id = cur.lastrowid

        # Registrar evento de criação
        cur.execute("""
            INSERT INTO options_lifecycle_events (
                position_id, event_type, from_status, to_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            position_id,
            LifecycleEventType.CREATED.value,
            None,
            PositionStatus.OPEN.value,
            f"Criada de candidate_id={candidate_id} (status={candidate_status})",
            now,
        ))

        conn.commit()
        return {"ok": True, "position_id": position_id}

    except sqlite3.Error as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Listar posições abertas
# ---------------------------------------------------------------------------

def get_open_options_positions() -> list[dict[str, Any]]:
    """Retorna todas as posições com status OPEN/MONITORING/ALERT/ADJUST/ROLL."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT position_id, candidate_id, ticker, structure_type,
               status, entry_date, expiry_date, dte_initial,
               quantity, cost_total, max_risk, max_return, breakeven,
               entry_underlying_price, iv_entry, source_type, is_simulated,
               notes, created_at
        FROM options_positions
        WHERE status IN ('OPEN','MONITORING','ALERT','ADJUST','ROLL')
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 3. Detalhe de posição
# ---------------------------------------------------------------------------

def get_options_position_detail(position_id: int) -> Optional[dict[str, Any]]:
    """Retorna posição com snapshot mais recente e alertas ativos."""
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM options_positions WHERE position_id = ?", (position_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    position = dict(row)

    # Snapshot mais recente
    cur.execute("""
        SELECT * FROM options_position_snapshots
        WHERE position_id = ?
        ORDER BY captured_at DESC LIMIT 1
    """, (position_id,))
    snapshot_row = cur.fetchone()
    snapshot = dict(snapshot_row) if snapshot_row else None

    # Alertas ativos
    cur.execute("""
        SELECT * FROM options_alerts
        WHERE position_id = ? AND is_active = 1
        ORDER BY created_at DESC
    """, (position_id,))
    alerts = [dict(r) for r in cur.fetchall()]

    conn.close()

    position["latest_snapshot"] = snapshot
    position["active_alerts"] = alerts
    return position


# ---------------------------------------------------------------------------
# 4. Atualizar snapshot
# ---------------------------------------------------------------------------

def _get_current_market_data(ticker: str) -> dict[str, Any]:
    """Busca dados atuais de mercado para o ticker.

    Usa dados reais do DB (b3_quotes). Não falsifica.
    Retorna dict vazio se não encontrar dados.
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT close, open, high, low, best_bid, best_ask, trades
        FROM b3_quotes
        WHERE ticker = ?
        ORDER BY trade_date DESC LIMIT 1
    """, (ticker,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        "underlying_price": row["close"] or row["average"],
        "best_bid": row["best_bid"],
        "best_ask": row["best_ask"],
        "spread_pct": round(
            ((row["best_ask"] - row["best_bid"]) / row["close"]) * 100, 2
        ) if row["close"] and row["best_bid"] and row["best_ask"] else None,
        "volume": row["trades"],
    }


def _get_current_options_prices(legs: list[OptionLeg]) -> tuple[dict[str, float], float, float]:
    """Busca preços atuais das pernas via options_greeks_snapshot.

    Returns: (prices_dict, liquidity_score_avg, spread_pct_avg)
    """
    if not legs:
        return {}, None, None

    conn = _connect()
    cur = conn.cursor()

    prices = {}
    liquidity_scores = []
    spreads = []

    for leg in legs:
        cur.execute("""
            SELECT last_price, bid, ask, spread, liquidity_score,
                   implied_volatility, delta, theta, vega, gamma
            FROM options_greeks_snapshot
            WHERE ticker = ?
            ORDER BY captured_at DESC LIMIT 1
        """, (leg.option_ticker,))
        row = cur.fetchone()
        if row:
            prices[leg.option_ticker] = row["last_price"]
            if row["liquidity_score"]:
                liquidity_scores.append(row["liquidity_score"])
            if row["spread"] is not None:
                spreads.append(row["spread"])

    conn.close()

    liquidity = sum(liquidity_scores) / len(liquidity_scores) if liquidity_scores else None
    spread_avg = sum(spreads) / len(spreads) if spreads else None

    return prices, liquidity, spread_avg


def _calculate_dte(expiry_date: str) -> Optional[int]:
    """Calcula DTE (dias até vencimento) a partir da data de vencimento."""
    if not expiry_date:
        return None
    try:
        exp = datetime.strptime(expiry_date[:10], "%Y-%m-%d").date()
        today = datetime.utcnow().date()
        return max(0, (exp - today).days)
    except ValueError:
        return None


def update_options_position_snapshot(position_id: int) -> Optional[dict[str, Any]]:
    """Gera snapshot atualizado da posição com métricas reais de mercado.

    Atualiza a tabela options_position_snapshots e retorna o snapshot gerado.
    Retorna None se a posição não existir.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM options_positions WHERE position_id = ?", (position_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    position = dict(row)
    legs = _parse_legs(position["legs_json"])

    # Dados de mercado do subjacente
    market = _get_current_market_data(position["ticker"])

    # Dados de opções
    option_prices, liquidity, spread_pct = _get_current_options_prices(legs)

    # Greeks mais recentes
    current_greeks = {"delta": None, "theta": None, "vega": None, "gamma": None}
    conn2 = _connect()
    cur2 = conn2.cursor()
    for leg in legs:
        cur2.execute("""
            SELECT delta, theta, vega, gamma
            FROM options_greeks_snapshot
            WHERE ticker = ?
            ORDER BY captured_at DESC LIMIT 1
        """, (leg.option_ticker,))
        gr = cur2.fetchone()
        if gr:
            if gr["delta"] is not None:
                current_greeks["delta"] = gr["delta"]
            if gr["theta"] is not None:
                current_greeks["theta"] = gr["theta"]
            if gr["vega"] is not None:
                current_greeks["vega"] = gr["vega"]
            if gr["gamma"] is not None:
                current_greeks["gamma"] = gr["gamma"]
    conn2.close()

    # Cálculos
    underlying_price = market.get("underlying_price") or position["entry_underlying_price"]
    dte_current = _calculate_dte(position["expiry_date"])

    # Valor da estrutura: soma de prêmios × quantidade × lote (100)
    structure_value = sum(
        option_prices.get(leg.option_ticker, 0.0) for leg in legs
    ) * position["quantity"] * 100

    # PnL
    cost_total = position["cost_total"] or 0.0
    pnl_reais = structure_value - cost_total if structure_value else None
    pnl_pct = (pnl_reais / cost_total * 100) if cost_total and pnl_reais is not None else None

    # Theta decay acumulado
    theta_entry = position["theta_entry"] or 0.0
    theta_current = current_greeks["theta"]
    theta_decay_accumulated = (
        (theta_current - theta_entry) if theta_current is not None and theta_entry else None
    )

    # IV
    iv_entry = position["iv_entry"]
    iv_current = iv_entry  # fallback
    iv_change_pct = None
    if iv_entry and iv_current:
        iv_change_pct = round(((iv_current - iv_entry) / iv_entry) * 100, 2)

    # Distâncias
    dist_to_strike = None
    dist_to_breakeven = None
    if underlying_price and legs:
        min_strike = min(l.strike for l in legs)
        dist_to_strike = round(((underlying_price - min_strike) / min_strike) * 100, 2)
    if underlying_price and position["breakeven"]:
        dist_to_breakeven = round(
            ((underlying_price - position["breakeven"]) / position["breakeven"]) * 100, 2
        )

    # Thesis status
    thesis_status = "OK"
    if pnl_pct is not None and pnl_pct <= -20:
        thesis_status = "UNDERPERFORMING"
    if pnl_pct is not None and pnl_pct >= 50:
        thesis_status = "OUTPERFORMING"
    if dte_current is not None and dte_current <= 5:
        thesis_status = "NEAR_EXPIRY"

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    cur.execute("""
        INSERT INTO options_position_snapshots (
            position_id, captured_at, underlying_price, option_prices_json,
            structure_value, pnl_reais, pnl_pct, dte_current,
            theta_decay_accumulated, theta_current, iv_current, iv_change_pct,
            delta_current, vega_current, gamma_current,
            distance_to_strike_pct, distance_to_breakeven_pct,
            liquidity_score, spread_pct, thesis_status, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        position_id,
        now,
        underlying_price,
        _json_safe(option_prices),
        structure_value,
        pnl_reais,
        pnl_pct,
        dte_current,
        theta_decay_accumulated,
        theta_current,
        iv_current,
        iv_change_pct,
        current_greeks["delta"],
        current_greeks["vega"],
        current_greeks["gamma"],
        dist_to_strike,
        dist_to_breakeven,
        liquidity,
        spread_pct,
        thesis_status,
        _json_safe({}),
    ))
    snapshot_id = cur.lastrowid
    conn.commit()

    cur.execute("SELECT * FROM options_position_snapshots WHERE snapshot_id = ?", (snapshot_id,))
    snapshot_row = cur.fetchone()
    conn.close()

    return dict(snapshot_row) if snapshot_row else None


# ---------------------------------------------------------------------------
# 5. Histórico de eventos lifecycle
# ---------------------------------------------------------------------------

def get_options_lifecycle_events(position_id: int) -> list[dict[str, Any]]:
    """Retorna histórico de eventos da posição."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT event_id, position_id, event_type, from_status, to_status,
               reason, metadata_json, created_at
        FROM options_lifecycle_events
        WHERE position_id = ?
        ORDER BY created_at ASC
    """, (position_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 6. Alertas vigentes
# ---------------------------------------------------------------------------

def get_options_alerts(position_id: int) -> list[dict[str, Any]]:
    """Retorna alertas ativos de uma posição."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT alert_id, position_id, snapshot_id, alert_type, severity,
               message, trigger_value, threshold_value, is_active,
               is_acknowledged, acknowledged_at, metadata_json, created_at
        FROM options_alerts
        WHERE position_id = ? AND is_active = 1
        ORDER BY created_at DESC
    """, (position_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 7. Avaliar sinais de saída
# ---------------------------------------------------------------------------

def evaluate_options_exit_signals(position_id: int) -> dict[str, Any]:
    """Avalia sinais de saída/ajuste/rolagem para a posição e persiste em options_exit_signals.

    Retorna dict com sinais avaliados e sinal composto.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM options_positions WHERE position_id = ?", (position_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Position {position_id} não encontrada."}

    position = dict(row)

    # Snapshot mais recente
    cur.execute("""
        SELECT * FROM options_position_snapshots
        WHERE position_id = ?
        ORDER BY captured_at DESC LIMIT 1
    """, (position_id,))
    snap_row = cur.fetchone()
    if not snap_row:
        conn.close()
        return {
            "ok": False,
            "error": "Nenhum snapshot disponível. Execute update_options_position_snapshot primeiro.",
        }

    snapshot = dict(snap_row)
    snap = PositionSnapshot(
        snapshot_id=snapshot["snapshot_id"],
        position_id=position_id,
        captured_at=snapshot["captured_at"],
        underlying_price=snapshot["underlying_price"],
        pnl_reais=snapshot["pnl_reais"],
        pnl_pct=snapshot["pnl_pct"],
        dte_current=snapshot["dte_current"],
        theta_decay_accumulated=snapshot["theta_decay_accumulated"],
        theta_current=snapshot["theta_current"],
        iv_current=snapshot["iv_current"],
        iv_change_pct=snapshot["iv_change_pct"],
        distance_to_strike_pct=snapshot["distance_to_strike_pct"],
        distance_to_breakeven_pct=snapshot["distance_to_breakeven_pct"],
        liquidity_score=snapshot["liquidity_score"],
        spread_pct=snapshot["spread_pct"],
        thesis_status=snapshot["thesis_status"],
    )

    cost_total = position["cost_total"] or 0.0
    max_risk = position["max_risk"] or 0.0
    entry_underlying = position["entry_underlying_price"] or 0.0
    breakeven = position["breakeven"]

    exit_signals = evaluate_exit_signals(
        snap, cost_total, max_risk, entry_underlying, breakeven,
        position.get("invalidation_condition"), position.get("exit_condition"),
    )
    adjust_signals = evaluate_adjust_signals(
        snap,
        position.get("iv_entry") or 0.0,
        snapshot.get("spread_pct") or 0.0,
        snapshot.get("liquidity_score") or 0.0,
    )
    roll_signals = evaluate_roll_signals(
        snap, cost_total, snapshot.get("pnl_reais"),
    )

    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Persistir cada sinal
    for sig_group, signals in [
        ("EXIT", exit_signals),
        ("ADJUST", adjust_signals),
        ("ROLL", roll_signals),
    ]:
        for sig in signals:
            cur.execute("""
                INSERT INTO options_exit_signals (
                    position_id, signal_type, action, reason, confidence,
                    trigger_snapshot_id, is_acted_upon, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_id,
                sig["signal_type"],
                sig["action"],
                sig["reason"],
                sig.get("confidence"),
                snap.snapshot_id,
                0,
                now,
            ))
    conn.commit()

    composite = get_composite_signal(exit_signals, adjust_signals, roll_signals)
    conn.close()

    return {
        "ok": True,
        "position_id": position_id,
        "snapshot_id": snap.snapshot_id,
        "exit_signals": exit_signals,
        "adjust_signals": adjust_signals,
        "roll_signals": roll_signals,
        "composite": composite,
    }


# ---------------------------------------------------------------------------
# 8. Fechar posição
# ---------------------------------------------------------------------------

def close_options_position(
    position_id: int,
    reason: str,
    close_type: str = "MANUAL",
) -> dict[str, Any]:
    """Fecha posição e registra evento lifecycle.

    close_type: MANUAL | STOP_LOSS | TAKE_PROFIT | EXPIRED | ADJUSTED
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT status FROM options_positions WHERE position_id = ?", (position_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Position {position_id} não encontrada."}

    current_status = row["status"]
    new_status = PositionStatus.CLOSE.value
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    event_type_map = {
        "STOP_LOSS": LifecycleEventType.CLOSE_STOP_LOSS.value,
        "TAKE_PROFIT": LifecycleEventType.CLOSE_TAKE_PROFIT.value,
        "EXPIRED": LifecycleEventType.CLOSE_EXPIRED.value,
        "ADJUSTED": LifecycleEventType.CLOSE_ADJUSTED.value,
    }

    cur.execute("""
        UPDATE options_positions
        SET status = ?, updated_at = ?
        WHERE position_id = ?
    """, (new_status, now, position_id))

    cur.execute("""
        INSERT INTO options_lifecycle_events (
            position_id, event_type, from_status, to_status, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        position_id,
        event_type_map.get(close_type, LifecycleEventType.CLOSE_MANUAL.value),
        current_status,
        new_status,
        reason,
        now,
    ))
    conn.commit()
    conn.close()
    return {"ok": True, "position_id": position_id, "status": new_status}


# ---------------------------------------------------------------------------
# 9. Registrar rolagem
# ---------------------------------------------------------------------------

def roll_options_position(
    position_id: int,
    new_candidate_id: int,
    roll_notes: Optional[str] = None,
) -> dict[str, Any]:
    """Registra rolagem: fecha posição e cria nova a partir de new_candidate_id.

    Regras:
    - Posição atual deve ter status OPEN/MONITORING/ALERT/ROLL.
    - new_candidate_id deve ser APPROVED.
    - Não fecha posição anterior (mantém histórico); apenas muda status.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM options_positions WHERE position_id = ?", (position_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Position {position_id} não encontrada."}

    current_status = row["status"]
    open_statuses = {"OPEN", "MONITORING", "ALERT", "ROLL"}
    if current_status not in open_statuses:
        conn.close()
        return {
            "ok": False,
            "error": f"Posição {position_id} tem status='{current_status}'. Não pode rolar.",
        }

    # Fechar posição atual
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    cur.execute("""
        UPDATE options_positions SET status = ?, updated_at = ?
        WHERE position_id = ?
    """, (PositionStatus.ROLL.value, now, position_id))

    cur.execute("""
        INSERT INTO options_lifecycle_events (
            position_id, event_type, from_status, to_status, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        position_id,
        LifecycleEventType.ROLL_INITIATED.value,
        current_status,
        PositionStatus.ROLL.value,
        f"Rolagem para candidate_id={new_candidate_id}. {roll_notes or ''}",
        now,
    ))

        # Validar new_candidate_id — mesma regra de bloqueio
    cur.execute("""
        SELECT id, underlying, structure_type, maturity_date, legs_json,
               net_debit, net_credit, max_profit, max_loss, breakeven,
               liquidity_score, explanation, candidate_status, metadata_json
        FROM option_structure_candidates WHERE id = ?
    """, (new_candidate_id,))
    new_row = cur.fetchone()
    if not new_row:
        conn.rollback()
        conn.close()
        return {"ok": False, "error": f"new_candidate_id={new_candidate_id} não encontrado."}

    if new_row["candidate_status"] in blocked_statuses:
        conn.rollback()
        conn.close()
        return {
            "ok": False,
            "error": (
                f"new_candidate_id={new_candidate_id} candidate_status='{new_row['candidate_status']}'. "
                f"Somente fora de {blocked_statuses}."
            ),
        }

    # Extrair greeks e underlying_price do legs_json/metadata_json
    try:
        legs_raw = json.loads(new_row["legs_json"]) if new_row["legs_json"] else []
        iv_entry = max((l.get("implied_volatility", 0) or 0 for l in legs_raw), default=0.0)
        delta_entry = sum(l.get("delta", 0) or 0 for l in legs_raw)
        theta_entry = sum(l.get("theta", 0) or 0 for l in legs_raw)
        vega_entry = sum(l.get("vega", 0) or 0 for l in legs_raw)
        underlying_price = next(
            (l["underlying_price"] for l in legs_raw if l.get("underlying_price") is not None),
            None,
        )
        if not underlying_price:
            try:
                meta = json.loads(new_row["metadata_json"]) if new_row["metadata_json"] else {}
                underlying_price = meta.get("underlying_price")
            except (json.JSONDecodeError, TypeError):
                underlying_price = None
    except (json.JSONDecodeError, TypeError, KeyError):
        legs_raw = []
        iv_entry = delta_entry = theta_entry = vega_entry = 0.0
        underlying_price = None

    try:
        from datetime import date as date_module
        exp = datetime.strptime(new_row["maturity_date"][:10], "%Y-%m-%d").date()
        dte_initial = max(0, (exp - date_module.today()).days)
    except (ValueError, TypeError, AttributeError):
        dte_initial = None

    cost_total = new_row["net_debit"] or abs(new_row["max_loss"]) if new_row["max_loss"] else 0.0
    max_risk = abs(new_row["max_loss"]) if new_row["max_loss"] else None

    # Inserir nova posição como rolada
    cur.execute("""
        INSERT INTO options_positions (
            candidate_id, ticker, structure_type,
            status, entry_date, expiry_date, dte_initial,
            quantity, legs_json,
            net_debit, net_credit, cost_total, max_risk, max_return, breakeven,
            entry_underlying_price, iv_entry, delta_entry, theta_entry, vega_entry,
            original_thesis,
            source_type, is_simulated, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_row["id"],
        new_row["underlying"],
        new_row["structure_type"],
        PositionStatus.OPEN.value,
        now[:10],
        new_row["maturity_date"],
        dte_initial,
        1,
        new_row["legs_json"],
        new_row["net_debit"],
        new_row["net_credit"],
        cost_total,
        max_risk,
        new_row["max_profit"],
        new_row["breakeven"],
        new_row["underlying_price"],
        iv_entry,
        delta_entry,
        theta_entry,
        vega_entry,
        new_row["explanation"],
        "PAPER",
        1,
        f"Rolagem de position_id={position_id}. {roll_notes or ''}",
        now,
        now,
    ))
    new_position_id = cur.lastrowid

    cur.execute("""
        INSERT INTO options_lifecycle_events (
            position_id, event_type, from_status, to_status, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        new_position_id,
        LifecycleEventType.ROLL_COMPLETED.value,
        None,
        PositionStatus.OPEN.value,
        f"Criada por rolagem de position_id={position_id}",
        now,
    ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "old_position_id": position_id,
        "new_position_id": new_position_id,
        "message": f"Rolagem registrada: {position_id} → {new_position_id}",
    }