"""Governança quantitativa para candidatos de score, filtros e setups."""
from __future__ import annotations

from typing import Any

import pandas as pd


EXPERIMENTAL = "EXPERIMENTAL"
EM_OBSERVACAO = "EM_OBSERVACAO"
PROMISSOR = "PROMISSOR"
CANDIDATO_OPERACIONAL = "CANDIDATO_OPERACIONAL"
REJEITADO = "REJEITADO"
BLOQUEADO_OVERFITTING = "BLOQUEADO_OVERFITTING"
AMOSTRA_INSUFICIENTE = "AMOSTRA_INSUFICIENTE"
CONCENTRACAO_EXCESSIVA = "CONCENTRACAO_EXCESSIVA"
LIQUIDEZ_INSUFICIENTE = "LIQUIDEZ_INSUFICIENTE"
CANDIDATO_RESTRITO_A_REGIME = "CANDIDATO_RESTRITO_A_REGIME"
BLOQUEADO_REGIME_INSUFICIENTE = "BLOQUEADO_REGIME_INSUFICIENTE"
BLOQUEADO_REGIME_RISCO = "BLOQUEADO_REGIME_RISCO"
CANDIDATO_EVENT_DRIVEN = "CANDIDATO_EVENT_DRIVEN"
BLOQUEADO_EVENTO_INSUFICIENTE = "BLOQUEADO_EVENTO_INSUFICIENTE"
BLOQUEADO_EVENTO_CONTRA_SINAL = "BLOQUEADO_EVENTO_CONTRA_SINAL"
BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE = "BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE"
BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE = "BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE"

STATUS_RANK = {
    CANDIDATO_OPERACIONAL: 0,
    CANDIDATO_RESTRITO_A_REGIME: 1,
    CANDIDATO_EVENT_DRIVEN: 2,
    PROMISSOR: 3,
    EM_OBSERVACAO: 4,
    EXPERIMENTAL: 5,
    AMOSTRA_INSUFICIENTE: 6,
    BLOQUEADO_REGIME_INSUFICIENTE: 7,
    BLOQUEADO_EVENTO_INSUFICIENTE: 8,
    BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE: 9,
    BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE: 10,
    CONCENTRACAO_EXCESSIVA: 11,
    LIQUIDEZ_INSUFICIENTE: 12,
    BLOQUEADO_REGIME_RISCO: 13,
    BLOQUEADO_EVENTO_CONTRA_SINAL: 14,
    BLOQUEADO_OVERFITTING: 15,
    REJEITADO: 16,
}

DEFAULT_GOVERNANCE_RULES = {
    "min_windows": 6,
    "min_positive_windows_pct": 60.0,
    "min_test_net_return": 0.0,
    "min_hit_rate": 0.52,
    "max_top_3_concentration_pct": 50.0,
    "min_total_signals": 300,
    "max_degradation_score": 0.5,
    "promising_min_windows": 3,
    "promising_min_positive_windows_pct": 50.0,
    "promising_min_test_net_return": 0.0,
    "promising_min_total_signals": 100,
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        number = float(value)
        return default if pd.isna(number) else number
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "yes", "y"}
    return bool(value) if value is not None and not pd.isna(value) else False


def _quality_low(value: Any) -> bool:
    return str(value or "").strip().upper() in {"RUIM", "INVIAVEL"}


def _risk_and_confidence(status: str, reasons_against: list[str], approved: bool) -> tuple[str, str]:
    if approved:
        return "BAIXO", "ALTA"
    if status in {BLOQUEADO_OVERFITTING, LIQUIDEZ_INSUFICIENTE, CONCENTRACAO_EXCESSIVA, BLOQUEADO_EVENTO_CONTRA_SINAL}:
        return "ALTO", "BAIXA"
    if status in {AMOSTRA_INSUFICIENTE, BLOQUEADO_EVENTO_INSUFICIENTE, BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE, BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE}:
        return "MEDIO", "BAIXA"
    if status == PROMISSOR:
        return "MEDIO", "MEDIA"
    if reasons_against:
        return "MEDIO", "MEDIA"
    return "BAIXO", "MEDIA"


def evaluate_candidate_strategy(metrics: dict[str, Any], rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classifica um candidato quantitativo sem aplicar mudanças operacionais."""
    cfg = {**DEFAULT_GOVERNANCE_RULES, **(rules or {})}
    total = _num(metrics.get("total_signals", metrics.get("avg_test_signals")))
    windows = _num(metrics.get("windows_count"))
    positive = _num(metrics.get("positive_windows_pct"))
    mean_net = _num(metrics.get("mean_test_net_return", metrics.get("mean_net_return")))
    hit = _num(metrics.get("mean_hit_rate", metrics.get("mean_test_hit_rate")))
    top3 = _num(metrics.get("avg_top_3_concentration_pct"))
    train_net = _num(metrics.get("mean_train_net_return"))
    degradation = _num(metrics.get("degradation_score"), default=max(train_net - mean_net, 0.0))
    robustness = str(metrics.get("robustness_class", "") or "").upper()

    overfit = _bool(metrics.get("overfitting_alert")) or robustness == "OVERFIT_PROVAVEL" or (train_net > 0 and mean_net < 0)
    sample_warning = _bool(metrics.get("sample_warning")) or windows < cfg["min_windows"] or total < cfg["min_total_signals"]
    concentration_warning = _bool(metrics.get("concentration_warning")) or top3 > cfg["max_top_3_concentration_pct"]
    liquidity_warning = _bool(metrics.get("liquidity_warning")) or _quality_low(metrics.get("avg_execution_quality"))

    reasons_for: list[str] = []
    reasons_against: list[str] = []
    required_actions: list[str] = []

    if mean_net > cfg["min_test_net_return"]:
        reasons_for.append("Retorno líquido fora da amostra positivo.")
    else:
        reasons_against.append("Retorno líquido fora da amostra não é positivo.")
        required_actions.append("Revalidar filtros em novas janelas e regimes.")
    if positive >= cfg["min_positive_windows_pct"]:
        reasons_for.append("Percentual de janelas positivas atende o mínimo.")
    else:
        reasons_against.append("Percentual de janelas positivas abaixo do mínimo.")
        required_actions.append("Ampliar histórico e repetir walk-forward.")
    if hit >= cfg["min_hit_rate"]:
        reasons_for.append("Hit rate médio atende o mínimo de governança.")
    else:
        reasons_against.append("Hit rate médio abaixo do mínimo de governança.")
    if top3 <= cfg["max_top_3_concentration_pct"]:
        reasons_for.append("Concentração nos três principais ativos está dentro do limite.")
    else:
        reasons_against.append("Concentração excessiva nos três principais ativos.")
        required_actions.append("Reduzir dependência de poucos ativos.")
    if total >= cfg["min_total_signals"] and windows >= cfg["min_windows"]:
        reasons_for.append("Amostra e número de janelas são suficientes.")
    else:
        reasons_against.append("Amostra ou número de janelas insuficiente.")
        required_actions.append("Ampliar base histórica antes de promover o candidato.")
    if overfit:
        reasons_against.append("Alerta de overfitting ativo ou degradação treino/teste incompatível.")
        required_actions.append("Bloquear promoção operacional até nova validação fora da amostra.")
    if liquidity_warning:
        reasons_against.append("Liquidez ou qualidade de execução insuficiente.")
        required_actions.append("Revisar filtros de liquidez, spread, slippage e capacidade.")
    if degradation > cfg["max_degradation_score"]:
        reasons_against.append("Degradação treino/teste acima do limite aceito.")
        required_actions.append("Reduzir complexidade dos thresholds e testar estabilidade.")

    if overfit:
        status = BLOQUEADO_OVERFITTING
    elif liquidity_warning:
        status = LIQUIDEZ_INSUFICIENTE
    elif concentration_warning:
        status = CONCENTRACAO_EXCESSIVA
    elif sample_warning and windows < cfg["promising_min_windows"]:
        status = AMOSTRA_INSUFICIENTE
    elif (
        not sample_warning
        and not concentration_warning
        and mean_net > cfg["min_test_net_return"]
        and hit >= cfg["min_hit_rate"]
        and positive >= cfg["min_positive_windows_pct"]
        and degradation <= cfg["max_degradation_score"]
    ):
        status = CANDIDATO_OPERACIONAL
    elif (
        windows >= cfg["promising_min_windows"]
        and total >= cfg["promising_min_total_signals"]
        and positive >= cfg["promising_min_positive_windows_pct"]
        and mean_net > cfg["promising_min_test_net_return"]
        and not concentration_warning
    ):
        status = PROMISSOR
    elif windows >= 2 or total > 0:
        status = EM_OBSERVACAO
    else:
        status = EXPERIMENTAL

    approved = status == CANDIDATO_OPERACIONAL
    risk, confidence = _risk_and_confidence(status, reasons_against, approved)
    summary = (
        f"Configuração classificada como {status}. "
        f"Janelas positivas: {positive:.1f}%, retorno líquido teste: {mean_net:.4f}%, "
        f"hit rate: {hit:.2%}, concentração top 3: {top3:.1f}%."
    )
    return {
        "governance_status": status,
        "approved": approved,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": list(dict.fromkeys(required_actions)),
        "risk_level": risk,
        "confidence_level": confidence,
        "summary_text": summary,
        "metrics": metrics,
    }


def evaluate_threshold_candidate(threshold_result: dict[str, Any] | pd.Series, walk_forward_summary: dict[str, Any]) -> dict[str, Any]:
    """Avalia thresholds juntando evidência dentro e fora da amostra."""
    threshold = dict(threshold_result)
    walk = dict(walk_forward_summary or {})
    metrics = {
        "total_signals": walk.get("avg_test_signals", threshold.get("samples", 0)),
        "windows_count": walk.get("windows_count", 0),
        "positive_windows_pct": walk.get("positive_windows_pct", 0),
        "mean_net_return": threshold.get("mean_net_return_5d", 0),
        "mean_test_net_return": walk.get("mean_test_net_return", 0),
        "mean_hit_rate": walk.get("mean_test_hit_rate", threshold.get("hit_rate_net_5d", 0)),
        "avg_top_3_concentration_pct": walk.get("avg_top_3_concentration_pct", 0),
        "overfitting_alert": walk.get("overfitting_alert", False),
        "sample_warning": walk.get("insufficient_sample_windows_pct", 0) > 0,
        "concentration_warning": walk.get("concentration_warning_windows_pct", 0) >= 50,
        "robustness_class": walk.get("robustness_class"),
    }
    review = evaluate_candidate_strategy(metrics)
    review["candidate_name"] = "threshold_candidate"
    review["metadata"] = {"threshold_result": threshold, "walk_forward_summary": walk}
    return review


def rank_governed_candidates(candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df is None or candidates_df.empty:
        return pd.DataFrame()
    df = candidates_df.copy()
    df["_status_rank"] = df.get("governance_status", "").map(STATUS_RANK).fillna(99)
    for col in ["mean_test_net_return", "mean_hit_rate", "total_signals", "avg_top_3_concentration_pct"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.sort_values(
        ["_status_rank", "mean_test_net_return", "mean_hit_rate", "total_signals", "avg_top_3_concentration_pct"],
        ascending=[True, False, False, False, True],
    ).drop(columns=["_status_rank"]).reset_index(drop=True)


def generate_governance_report(review: dict[str, Any]) -> str:
    status = review.get("governance_status", EXPERIMENTAL)
    approved = "SIM" if review.get("approved") else "NÃO"
    risk = review.get("risk_level", "INDEFINIDO")
    confidence = review.get("confidence_level", "INDEFINIDA")
    against = review.get("reasons_against") or ["Nenhum motivo contrário registrado."]
    actions = review.get("required_actions") or ["Manter em acompanhamento estatístico."]
    return (
        f"A configuração analisada foi classificada como {status}. Aprovado: {approved}. "
        f"Risco: {risk}. Confiança: {confidence}. "
        f"Motivos contrários: {'; '.join(against)}. "
        f"Ações necessárias: {'; '.join(actions)}. "
        "Esta governança não altera score, thresholds, ranking ou pesos automaticamente."
    )


def evaluate_regime_governance(regime_summary: pd.DataFrame, base_review: dict[str, Any]) -> dict[str, Any]:
    """Avalia se um candidato deve ser amplo, restrito a regimes ou bloqueado por regime."""
    review = dict(base_review)
    if regime_summary is None or regime_summary.empty:
        review.update(
            {
                "governance_status": BLOQUEADO_REGIME_INSUFICIENTE,
                "approved": False,
                "allowed_regimes": [],
                "blocked_regimes": [],
                "regime_status": BLOQUEADO_REGIME_INSUFICIENTE,
            }
        )
        return review
    primary = regime_summary[regime_summary.get("regime_type") == "primary_regime"].copy()
    if primary.empty:
        primary = regime_summary.copy()
    tested = primary["regime_value"].dropna().astype(str).tolist()
    positive = primary[pd.to_numeric(primary.get("mean_net_return_5d"), errors="coerce") > 0]
    negative = primary[pd.to_numeric(primary.get("mean_net_return_5d"), errors="coerce") <= 0]
    allowed = positive["regime_value"].dropna().astype(str).tolist()
    blocked = negative["regime_value"].dropna().astype(str).tolist()
    worst = pd.to_numeric(primary.get("mean_net_return_5d"), errors="coerce").min()

    if len(tested) < 2:
        status = BLOQUEADO_REGIME_INSUFICIENTE
    elif worst <= -1.0 and not allowed:
        status = BLOQUEADO_REGIME_RISCO
    elif allowed and blocked:
        status = CANDIDATO_RESTRITO_A_REGIME
    elif allowed and not blocked and review.get("approved"):
        status = CANDIDATO_OPERACIONAL
    elif allowed:
        status = PROMISSOR
    else:
        status = BLOQUEADO_REGIME_RISCO

    review.update(
        {
            "governance_status": status,
            "approved": status == CANDIDATO_OPERACIONAL,
            "regime_status": status,
            "allowed_regimes": allowed,
            "blocked_regimes": blocked,
            "summary_text": (
                f"Governança por regime avaliou {len(tested)} regimes. "
                f"Regimes permitidos: {', '.join(allowed) or 'nenhum'}. "
                f"Regimes bloqueados: {', '.join(blocked) or 'nenhum'}. Status: {status}."
            ),
        }
    )
    if status == CANDIDATO_RESTRITO_A_REGIME:
        review.setdefault("required_actions", []).append("Restringir análise aos regimes permitidos e bloquear regimes frágeis.")
    if status in {BLOQUEADO_REGIME_INSUFICIENTE, BLOQUEADO_REGIME_RISCO}:
        review.setdefault("required_actions", []).append("Ampliar histórico por regime antes de qualquer promoção.")
    return review


def _event_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "sim", "yes"}


def evaluate_event_context_governance(event_summary: pd.DataFrame, base_review: dict[str, Any], coverage_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Avalia se a evidência depende de eventos ou se deve ser bloqueada."""
    review = dict(base_review)
    coverage_quality = str((coverage_metrics or {}).get("coverage_quality") or "").upper()
    if coverage_quality in {"COBERTURA_FRACA", "COBERTURA_INSUFICIENTE"}:
        review.update(
            {
                "governance_status": BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE,
                "approved": False,
                "event_status": BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE,
                "allowed_event_contexts": [],
                "blocked_event_contexts": [],
                "summary_text": (
                    f"Cobertura de eventos insuficiente ({coverage_quality}). "
                    "A análise evento x sem evento não deve gerar conclusão forte."
                ),
            }
        )
        review.setdefault("reasons_against", []).append("Cobertura de eventos insuficiente para conclusão robusta.")
        review.setdefault("required_actions", []).append("Ampliar fontes, tickers e janela temporal do pipeline de eventos.")
        return review
    if event_summary is None or event_summary.empty:
        review.update(
            {
                "governance_status": BLOQUEADO_EVENTO_INSUFICIENTE,
                "approved": False,
                "event_status": BLOQUEADO_EVENTO_INSUFICIENTE,
                "allowed_event_contexts": [],
                "blocked_event_contexts": [],
                "summary_text": "Sem amostra de eventos suficiente para governança event-driven.",
            }
        )
        return review

    summary = event_summary.copy()
    by_has_event = summary[summary.get("group_type") == "has_event"].copy()
    with_event = by_has_event[by_has_event["group_value"].apply(_event_bool)] if not by_has_event.empty else pd.DataFrame()
    without_event = by_has_event[~by_has_event["group_value"].apply(_event_bool)] if not by_has_event.empty else pd.DataFrame()
    with_signals = int(pd.to_numeric(with_event.get("signals"), errors="coerce").sum()) if not with_event.empty else 0
    with_ret = _num(with_event["mean_net_return_5d"].iloc[0]) if not with_event.empty else 0.0
    without_ret = _num(without_event["mean_net_return_5d"].iloc[0]) if not without_event.empty else 0.0

    by_context = summary[summary.get("group_type") == "event_context_type"].copy()
    contra = by_context[by_context.get("group_value").astype(str).str.upper().eq("EVENTO_CONTRA_SINAL")] if not by_context.empty else pd.DataFrame()
    contra_ret = _num(contra["mean_net_return_5d"].iloc[0]) if not contra.empty else 0.0

    if with_signals < 30:
        status = BLOQUEADO_EVENTO_INSUFICIENTE
        allowed: list[str] = []
        blocked: list[str] = []
        action = "Importar e validar mais eventos antes de avaliar setup event-driven."
    elif not contra.empty and contra_ret < 0:
        status = BLOQUEADO_EVENTO_CONTRA_SINAL
        allowed = []
        blocked = ["EVENTO_CONTRA_SINAL"]
        action = "Separar sinais técnicos de eventos contrários antes de qualquer promoção."
    elif with_ret > 0 and without_ret <= 0:
        status = CANDIDATO_EVENT_DRIVEN
        allowed = ["MOVIMENTO_EVENT_DRIVEN", "TECNICO_COM_CONFIRMACAO_EVENTO", "EVENTO_MACRO", "EVENTO_SETORIAL"]
        blocked = ["TECNICO_SEM_EVENTO"]
        action = "Tratar a configuração como restrita a contexto event-driven e validar fora da amostra."
    else:
        status = review.get("governance_status", EM_OBSERVACAO)
        allowed = []
        blocked = []
        action = "Manter eventos como variável explicativa, sem alterar score ou ranking."

    review.update(
        {
            "governance_status": status,
            "approved": False if status in {CANDIDATO_EVENT_DRIVEN, BLOQUEADO_EVENTO_INSUFICIENTE, BLOQUEADO_EVENTO_CONTRA_SINAL} else bool(review.get("approved")),
            "event_status": status,
            "allowed_event_contexts": allowed,
            "blocked_event_contexts": blocked,
            "summary_text": (
                f"Governança com eventos avaliou {with_signals} sinais com evento. "
                f"Retorno líquido com evento: {with_ret:.4f}%; sem evento: {without_ret:.4f}%. Status: {status}."
            ),
        }
    )
    review.setdefault("required_actions", []).append(action)
    if status == BLOQUEADO_EVENTO_INSUFICIENTE:
        review.setdefault("reasons_against", []).append("Amostra de eventos insuficiente.")
    if status == BLOQUEADO_EVENTO_CONTRA_SINAL:
        review.setdefault("reasons_against", []).append("Eventos contra o sinal apresentaram desempenho negativo.")
    if status == CANDIDATO_EVENT_DRIVEN:
        review.setdefault("reasons_for", []).append("Sinais com evento performaram melhor que sinais sem evento.")
        review.setdefault("reasons_against", []).append("Evidência positiva depende de contexto event-driven.")
    return review


def evaluate_event_coverage_governance(
    coverage_summary: dict[str, Any],
    coverage_by_regime: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Governa se a cobertura de eventos permite conclusões robustas."""
    coverage = dict(coverage_summary or {})
    quality = str(coverage.get("coverage_quality") or "").upper()
    sources_count = int(_num(coverage.get("sources_count")))
    signals_pct = _num(coverage.get("signals_with_event_pct"))
    tickers_pct = _num(coverage.get("tickers_with_event_pct"))
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    actions: list[str] = []

    if quality in {"COBERTURA_BOA", "COBERTURA_MEDIA"}:
        reasons_for.append(f"Cobertura geral classificada como {quality}.")
    else:
        reasons_against.append(f"Cobertura geral classificada como {quality or 'INDEFINIDA'}.")
        actions.append("Ampliar fontes, tickers e janela temporal antes de concluir evento x sem evento.")
    if sources_count >= 2:
        reasons_for.append("Há mais de uma fonte de eventos ativa.")
    else:
        reasons_against.append("Cobertura depende de fonte única ou fonte ausente.")
        actions.append("Ativar pelo menos duas fontes independentes de eventos.")
    if signals_pct >= 0.1 and tickers_pct >= 0.3:
        reasons_for.append("Cobertura mínima por sinais e tickers foi atingida.")
    else:
        reasons_against.append("Poucos sinais ou tickers possuem cobertura de eventos.")

    regime_status = None
    weak_regimes: list[str] = []
    tested_regimes = 0
    if coverage_by_regime is not None and not coverage_by_regime.empty:
        tested_regimes = int(coverage_by_regime[["regime_type", "regime_value"]].drop_duplicates().shape[0])
        weak = coverage_by_regime[
            coverage_by_regime.get("coverage_quality").astype(str).str.upper().isin({"COBERTURA_FRACA", "COBERTURA_INSUFICIENTE"})
        ]
        weak_regimes = (
            weak.assign(label=weak["regime_type"].astype(str) + "=" + weak["regime_value"].astype(str))["label"]
            .dropna()
            .unique()
            .tolist()
        )
        if weak_regimes:
            reasons_against.append("Há regimes com cobertura fraca ou insuficiente.")
            actions.append("Não tirar conclusão forte sobre eventos nos regimes sem cobertura.")
            regime_status = BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE
        else:
            reasons_for.append("Nenhum regime testado ficou com cobertura fraca.")
    elif coverage_by_regime is not None:
        reasons_against.append("Sem dados de cobertura por regime.")
        actions.append("Rodar rotina de eventos com --with-regimes após gerar market_regime_daily.")
        regime_status = BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE

    if regime_status:
        status = regime_status
    elif quality in {"COBERTURA_FRACA", "COBERTURA_INSUFICIENTE", ""}:
        status = BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE
    elif quality == "COBERTURA_MEDIA":
        status = EM_OBSERVACAO
    else:
        status = PROMISSOR

    approved = False
    risk, confidence = _risk_and_confidence(status, reasons_against, approved)
    return {
        "governance_status": status,
        "approved": approved,
        "risk_level": risk,
        "confidence_level": confidence,
        "event_status": status,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": list(dict.fromkeys(actions)),
        "metrics": {
            "coverage_quality": quality,
            "signals_with_event_pct": signals_pct,
            "tickers_with_event_pct": tickers_pct,
            "sources_count": sources_count,
            "tested_regimes": tested_regimes,
            "weak_regimes": weak_regimes,
        },
        "summary_text": (
            f"Governança de cobertura de eventos: {status}. "
            f"Cobertura geral: {quality or 'INDEFINIDA'}, sinais cobertos: {signals_pct:.2%}, "
            f"tickers cobertos: {tickers_pct:.2%}, fontes: {sources_count}, regimes fracos: {len(weak_regimes)}."
        ),
    }
