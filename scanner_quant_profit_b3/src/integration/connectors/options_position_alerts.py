"""Gerador de alertas para posições de opções — S06 M009.

Gera alertas baseados no snapshot atual da posição.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from src.options.options_position_model import (
    AlertSeverity,
    AlertType,
    PositionAlert,
    PositionSnapshot,
)


def generate_position_alerts(
    snapshot: PositionSnapshot,
    position_id: int,
    dte_initial: Optional[int],
    cost_total: float,
    max_risk: float,
    max_return: float,
    invalidation_threshold: Optional[float] = None,
    entry_price: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Gera alertas com base no snapshot atual da posição.

    Retorna lista de dicts prontos para inserção no banco.
    """
    alerts = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. DTE baixo
    if snapshot.dte_current is not None:
        if snapshot.dte_current <= 3:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.DTE_LOW.value,
                "severity": AlertSeverity.CRITICAL.value,
                "message": f"Vencimento iminente: apenas {snapshot.dte_current} dias para o vencimento.",
                "trigger_value": snapshot.dte_current,
                "threshold_value": 3,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })
        elif snapshot.dte_current <= 7:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.DTE_LOW.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"DTE baixo: {snapshot.dte_current} dias. Preparar decisão de saída/rolagem.",
                "trigger_value": snapshot.dte_current,
                "threshold_value": 7,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 2. Perda máxima próxima (80%+ do risco)
    if max_risk > 0 and snapshot.pnl_reais is not None:
        loss_pct = abs(snapshot.pnl_reais) / max_risk
        if loss_pct >= 0.80:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.MAX_LOSS_APPROACHING.value,
                "severity": AlertSeverity.CRITICAL.value,
                "message": f"Atingindo perda máxima: {loss_pct:.0%} do risco (R$ {abs(snapshot.pnl_reais):.2f} de R$ {max_risk:.2f}).",
                "trigger_value": loss_pct,
                "threshold_value": 0.80,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })
        elif loss_pct >= 0.60:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.MAX_LOSS_APPROACHING.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"Perda significativa: {loss_pct:.0%} do risco máximo. Monitorar.",
                "trigger_value": loss_pct,
                "threshold_value": 0.60,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 3. Lucro parcial atingido
    if cost_total > 0 and snapshot.pnl_reais is not None:
        profit_pct = snapshot.pnl_reais / cost_total
        if profit_pct >= 0.50:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.PROFIT_PARTIAL_TARGET.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"Lucro parcial: {profit_pct:.0%} do custo (R$ {snapshot.pnl_reais:.2f}). Considerar realizar parte.",
                "trigger_value": profit_pct,
                "threshold_value": 0.50,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 4. Theta acceleration
    if snapshot.theta_decay_accumulated is not None:
        daily_theta = abs(snapshot.theta_decay_accumulated) / max(snapshot.dte_current or 1, 1)
        if cost_total > 0 and daily_theta > cost_total * 0.02:
            severity = AlertSeverity.CRITICAL if daily_theta > cost_total * 0.04 else AlertSeverity.WARNING
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.THETA_ACCELERATION.value,
                "severity": severity.value,
                "message": f"Theta acelerado: R$ {daily_theta:.2f}/dia (>{cost_total * 0.02:.2f} limiar). Decay acelerou.",
                "trigger_value": daily_theta,
                "threshold_value": cost_total * 0.02,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 5. Ativo perto do strike (distância < 5%)
    if snapshot.distance_to_strike_pct is not None:
        if abs(snapshot.distance_to_strike_pct) <= 5:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.UNDERLYING_AT_STRIKE.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"Ativo a {abs(snapshot.distance_to_strike_pct):.1f}% do strike. Decisão próxima.",
                "trigger_value": abs(snapshot.distance_to_strike_pct),
                "threshold_value": 5,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 6. Invalidação triggered
    if entry_price and snapshot.underlying_price:
        dist_pct = ((snapshot.underlying_price - entry_price) / entry_price) * 100
        if invalidation_threshold is not None:
            if abs(dist_pct) >= abs(invalidation_threshold):
                alerts.append({
                    "position_id": position_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "alert_type": AlertType.INVALIDATION_TRIGGERED.value,
                    "severity": AlertSeverity.CRITICAL.value,
                    "message": f"Tese invalidada: subyacente moveu {dist_pct:.1f}% (limite: {invalidation_threshold:.1f}%).",
                    "trigger_value": dist_pct,
                    "threshold_value": invalidation_threshold,
                    "is_active": 1,
                    "is_acknowledged": 0,
                    "created_at": now,
                    "metadata_json": "{}",
                })

    # 7. IV mudou significativamente
    if snapshot.iv_change_pct is not None:
        if abs(snapshot.iv_change_pct) >= 20:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.IV_SIGNIFICANT_CHANGE.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"IV mudou {snapshot.iv_change_pct:+.1f}%. Impacto em vega/theta.",
                "trigger_value": snapshot.iv_change_pct,
                "threshold_value": 20,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 8. Spread piorou (>100% do spread de entrada)
    if snapshot.spread_pct is not None:
        if snapshot.spread_pct >= 2.0:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.SPREAD_WORSENED.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"Spread elevado: {snapshot.spread_pct:.2f}%. Execução custará mais.",
                "trigger_value": snapshot.spread_pct,
                "threshold_value": 2.0,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })
        elif snapshot.spread_pct >= 1.0:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.SPREAD_WORSENED.value,
                "severity": AlertSeverity.INFO.value,
                "message": f"Spread moderado: {snapshot.spread_pct:.2f}%. Executar com cuidado.",
                "trigger_value": snapshot.spread_pct,
                "threshold_value": 1.0,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 9. Baixa liquidez
    if snapshot.liquidity_score is not None:
        if snapshot.liquidity_score <= 0.3:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.LOW_LIQUIDITY.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"Liquidez baixa: {snapshot.liquidity_score:.2f}. Spread/Impactcustam mais.",
                "trigger_value": snapshot.liquidity_score,
                "threshold_value": 0.3,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 10. Rolagem sugerida
    if snapshot.dte_current is not None and snapshot.dte_current <= 7 and snapshot.pnl_reais is not None:
        if snapshot.pnl_reais < 0:
            alerts.append({
                "position_id": position_id,
                "snapshot_id": snapshot.snapshot_id,
                "alert_type": AlertType.ROLL_SUGGESTED.value,
                "severity": AlertSeverity.WARNING.value,
                "message": f"DTE {snapshot.dte_current} dias com loss. Rolagem para próximo vencimento sugerida.",
                "trigger_value": snapshot.dte_current,
                "threshold_value": 7,
                "is_active": 1,
                "is_acknowledged": 0,
                "created_at": now,
                "metadata_json": "{}",
            })

    # 11. Encerramento sugerido
    if snapshot.dte_current is not None and snapshot.dte_current <= 3 and snapshot.pnl_reais is not None and snapshot.pnl_reais < 0:
        alerts.append({
            "position_id": position_id,
            "snapshot_id": snapshot.snapshot_id,
            "alert_type": AlertType.EXIT_SUGGESTED.value,
            "severity": AlertSeverity.CRITICAL.value,
            "message": f"Encerramento sugerido: DTE {snapshot.dte_current} dias + loss R$ {abs(snapshot.pnl_reais):.2f}.",
            "trigger_value": snapshot.dte_current,
            "threshold_value": 3,
            "is_active": 1,
            "is_acknowledged": 0,
            "created_at": now,
            "metadata_json": "{}",
        })

    return alerts