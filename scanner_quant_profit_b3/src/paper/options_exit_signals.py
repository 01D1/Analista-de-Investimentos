"""Avaliação de sinais de saída, ajuste e rolagem para posições de opções — S06 M009.

Regras:
- Não gera ordens reais, apenas sinaliza condições.
- Avalia com base em snapshots reais do mercado (não dados simulados).
- Não altera posição sem sinal atuar.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

from src.options.options_position_model import (
    PositionSnapshot,
    PositionStatus,
    SignalAction,
    SignalType,
)


def _calculate_distance_pct(
    current: float, reference: float
) -> Optional[float]:
    """Distância percentual de current para reference."""
    if not reference or reference == 0:
        return None
    return round(((current - reference) / reference) * 100, 2)


def evaluate_exit_signals(
    snapshot: PositionSnapshot,
    position_cost_total: float,
    position_max_risk: float,
    entry_underlying: float,
    breakeven: Optional[float],
    invalidation_condition: Optional[str],
    exit_condition: Optional[str],
) -> list[dict[str, Any]]:
    """Avalia sinais de saída com base no snapshot atual.

    Retorna lista de sinais com type, action, reason, confidence.
    """
    signals = []

    # 1. DTE crítico — vencimento próximo
    if snapshot.dte_current is not None:
        if snapshot.dte_current <= 3:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.CLOSE_FULL.value,
                "reason": f"DTE crítico: {snapshot.dte_current} dias. Fechar ou assumir vencimento.",
                "confidence": 0.95,
            })
        elif snapshot.dte_current <= 5:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.HOLD.value,
                "reason": f"DTE baixo: {snapshot.dte_current} dias. Avaliar thetaremaining.",
                "confidence": 0.60,
            })

    # 2. Stop loss — perda máxima próxima
    if position_max_risk and position_max_risk > 0:
        if snapshot.pnl_reais is not None:
            loss_pct = abs(snapshot.pnl_reais) / position_max_risk
            if loss_pct >= 0.90:
                signals.append({
                    "signal_type": SignalType.EXIT.value,
                    "action": SignalAction.CLOSE_FULL.value,
                    "reason": f"Atingiu 90% do risco máximo (R$ {abs(snapshot.pnl_reais):.2f} de R$ {position_max_risk:.2f}).",
                    "confidence": 0.90,
                })
            elif loss_pct >= 0.70:
                signals.append({
                    "signal_type": SignalType.EXIT.value,
                    "action": SignalAction.HOLD.value,
                    "reason": f"Perda em 70% do risco máximo. Monitorar.",
                    "confidence": 0.60,
                })

    # 3. Lucro parcial — lucro superior a 50% do retorno máximo
    if snapshot.pnl_reais is not None and position_max_risk is not None:
        profit_pct = snapshot.pnl_reais / position_cost_total if position_cost_total else 0
        if profit_pct >= 0.50:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.CLOSE_HALF.value,
                "reason": f"Lucro parcial atingido ({profit_pct:.0%}). Considerar realizar 50%.",
                "confidence": 0.75,
            })
        if profit_pct >= 0.80:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.CLOSE_FULL.value,
                "reason": f"Lucro em {profit_pct:.0%} do custo. Realizar lucro.",
                "confidence": 0.85,
            })

    # 4. Tese invalidada — subyacente rompendo condição de invalidação
    if invalidation_condition and snapshot.underlying_price is not None and entry_underlying:
        dist_pct = _calculate_distance_pct(snapshot.underlying_price, entry_underlying)
        # Exemplo: "BAIXA: rompu -10%" → se dist_pct < -10
        if "BAIXA" in invalidation_condition.upper():
            try:
                threshold_str = invalidation_condition.split("-")[-1].strip().replace("%", "")
                threshold_val = float(threshold_str)
                if dist_pct is not None and dist_pct <= threshold_val:
                    signals.append({
                        "signal_type": SignalType.EXIT.value,
                        "action": SignalAction.CLOSE_FULL.value,
                        "reason": f"Tese invalidada: subyacente {dist_pct:.1f}% (limite: {threshold_val:.1f}%).",
                        "confidence": 0.88,
                    })
            except (ValueError, IndexError):
                pass
        # ALTA: se dist_pct > +threshold
        elif "ALTA" in invalidation_condition.upper():
            try:
                threshold_str = invalidation_condition.split("+")[-1].strip().replace("%", "")
                threshold_val = float(threshold_str)
                if dist_pct is not None and dist_pct >= threshold_val:
                    signals.append({
                        "signal_type": SignalType.EXIT.value,
                        "action": SignalAction.CLOSE_FULL.value,
                        "reason": f"Tese invalidada para Alta: subyacente {dist_pct:.1f}% (limite: +{threshold_val:.1f}%).",
                        "confidence": 0.88,
                    })
            except (ValueError, IndexError):
                pass

    # 5. Breakeven atingido
    if breakeven and snapshot.underlying_price:
        dist_be = _calculate_distance_pct(snapshot.underlying_price, breakeven)
        if dist_be is not None and dist_be <= -3:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.HOLD.value,
                "reason": f"Preço próximo ao breakeven ({breakeven:.2f}, {dist_be:.1f}%).",
                "confidence": 0.55,
            })

    # 6. Theta acceleration — theta decay acelerado
    if snapshot.theta_decay_accumulated is not None and snapshot.dte_current:
        daily_theta = abs(snapshot.theta_decay_accumulated) / max(snapshot.dte_current, 1)
        # heuristic: theta > 2% do custo por dia = acelerado
        if position_cost_total and daily_theta > position_cost_total * 0.02:
            signals.append({
                "signal_type": SignalType.EXIT.value,
                "action": SignalAction.HOLD.value,
                "reason": f"Theta acelerado: {daily_theta:.2f}/dia ({abs(snapshot.theta_decay_accumulated):.2f} acumulado).",
                "confidence": 0.60,
            })

    return signals


def evaluate_adjust_signals(
    snapshot: PositionSnapshot,
    iv_entry: float,
    spread_pct_entry: float,
    liquidity_entry: float,
) -> list[dict[str, Any]]:
    """Avalia sinais de ajuste baseados em mudanças de condições de mercado."""
    signals = []

    # 1. Mudança significativa de IV
    if iv_entry and snapshot.iv_current:
        iv_change = ((snapshot.iv_current - iv_entry) / iv_entry) * 100
        if iv_change >= 25:
            signals.append({
                "signal_type": SignalType.ADJUST.value,
                "action": SignalAction.HOLD.value,
                "reason": f"IV aumentou {iv_change:.1f}%. Posição beneficiada (vega positivo) ou penalizada.",
                "confidence": 0.70,
            })
        elif iv_change <= -25:
            signals.append({
                "signal_type": SignalType.ADJUST.value,
                "action": SignalAction.HOLD.value,
                "reason": f"IV caiu {abs(iv_change):.1f}%. Posição pode perder valor com compressing de IV.",
                "confidence": 0.65,
            })

    # 2. Spread piorou
    if spread_pct_entry and snapshot.spread_pct:
        if snapshot.spread_pct >= spread_pct_entry * 2:
            signals.append({
                "signal_type": SignalType.ADJUST.value,
                "action": SignalAction.CLOSE_HALF.value,
                "reason": f"Spread quadruplicou: {snapshot.spread_pct:.2f}% (era {spread_pct_entry:.2f}%). Liquidez deteriorada.",
                "confidence": 0.75,
            })
        elif snapshot.spread_pct >= spread_pct_entry * 1.5:
            signals.append({
                "signal_type": SignalType.ADJUST.value,
                "action": SignalAction.HOLD.value,
                "reason": f"Spread aumentou 50%: {snapshot.spread_pct:.2f}%. Monitorar liquidez.",
                "confidence": 0.55,
            })

    # 3. Liquidez caiu significativamente
    if liquidity_entry and snapshot.liquidity_score:
        if snapshot.liquidity_score <= liquidity_entry * 0.4:
            signals.append({
                "signal_type": SignalType.ADJUST.value,
                "action": SignalAction.HOLD.value,
                "reason": f"Liquidez caiu para {snapshot.liquidity_score:.2f} (era {liquidity_entry:.2f}). Executar com cuidado.",
                "confidence": 0.65,
            })

    return signals


def evaluate_roll_signals(
    snapshot: PositionSnapshot,
    position_cost_total: float,
    pnl_current: Optional[float],
) -> list[dict[str, Any]]:
    """Avalia sinais de rolagem para próximo vencimento."""
    signals = []

    # 1. DTE muito baixo e posição ainda aberta com PnL positivo
    if snapshot.dte_current is not None and snapshot.dte_current <= 7:
        if pnl_current is not None and pnl_current > 0:
            signals.append({
                "signal_type": SignalType.ROLL.value,
                "action": SignalAction.ROLL_FORWARD.value,
                "reason": f"DTE {snapshot.dte_current} dias com lucro R$ {pnl_current:.2f}. Considerar rolagem para próximo vencimento.",
                "confidence": 0.70,
            })
        elif pnl_current is not None and pnl_current < 0:
            # rolagem para recuperação de theta
            signals.append({
                "signal_type": SignalType.ROLL.value,
                "action": SignalAction.ROLL_FORWARD.value,
                "reason": f"DTE {snapshot.dte_current} dias com loss R$ {abs(pnl_current):.2f}. Rolagem pode recuperar theta.",
                "confidence": 0.55,
            })

    # 2. Theta muito acelerado e PnL negativo
    if snapshot.theta_decay_accumulated is not None and pnl_current is not None:
        if abs(snapshot.theta_decay_accumulated) > position_cost_total * 0.15 and pnl_current < 0:
            signals.append({
                "signal_type": SignalType.ROLL.value,
                "action": SignalAction.ROLL_FORWARD.value,
                "reason": f"Theta acelerou {abs(snapshot.theta_decay_accumulated):.2f} (>15% do custo) com loss. Rolagem recomendada.",
                "confidence": 0.65,
            })

    return signals


def get_composite_signal(
    exit_signals: list[dict],
    adjust_signals: list[dict],
    roll_signals: list[dict],
) -> dict[str, Any]:
    """Funde sinais individuais em sinal composto para a posição."""
    all_signals = exit_signals + adjust_signals + roll_signals
    if not all_signals:
        return {
            "signal_type": "HOLD",
            "action": SignalAction.HOLD.value,
            "reason": "Nenhuma condição de saída, ajuste ou rolagem atingida.",
            "confidence": 1.0,
            "signals_count": 0,
        }

    # Prioridade: EXIT > ADJUST > ROLL > HOLD
    priority_order = ["EXIT", "ADJUST", "ROLL"]
    for p in priority_order:
        for s in all_signals:
            if s.get("signal_type") == p and s.get("action") != SignalAction.HOLD.value:
                return {
                    "signal_type": p,
                    "action": s["action"],
                    "reason": s["reason"],
                    "confidence": s.get("confidence", 0.5),
                    "signals_count": len(all_signals),
                }

    # Nenhum sinal acionável
    return {
        "signal_type": "HOLD",
        "action": SignalAction.HOLD.value,
        "reason": "Condições monitoradas, nenhuma ação recomendada.",
        "confidence": 1.0,
        "signals_count": len(all_signals),
    }