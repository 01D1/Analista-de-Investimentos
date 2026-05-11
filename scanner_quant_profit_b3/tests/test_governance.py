import pandas as pd

from src.quant.governance import (
    AMOSTRA_INSUFICIENTE,
    BLOQUEADO_OVERFITTING,
    CANDIDATO_OPERACIONAL,
    CANDIDATO_RESTRITO_A_REGIME,
    CANDIDATO_EVENT_DRIVEN,
    BLOQUEADO_REGIME_INSUFICIENTE,
    BLOQUEADO_REGIME_RISCO,
    BLOQUEADO_EVENTO_INSUFICIENTE,
    BLOQUEADO_EVENTO_CONTRA_SINAL,
    BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE,
    CONCENTRACAO_EXCESSIVA,
    EM_OBSERVACAO,
    LIQUIDEZ_INSUFICIENTE,
    PROMISSOR,
    evaluate_candidate_strategy,
    evaluate_threshold_candidate,
    evaluate_regime_governance,
    evaluate_event_context_governance,
    generate_governance_report,
    rank_governed_candidates,
)


def _approved_metrics():
    return {
        "total_signals": 600,
        "windows_count": 8,
        "positive_windows_pct": 70,
        "mean_test_net_return": 0.25,
        "mean_net_return": 0.25,
        "mean_hit_rate": 0.55,
        "avg_top_3_concentration_pct": 35,
        "overfitting_alert": False,
        "sample_warning": False,
        "concentration_warning": False,
        "liquidity_warning": False,
        "mean_train_net_return": 0.35,
        "degradation_score": 0.1,
        "avg_execution_quality": "BOA",
        "robustness_class": "ROBUSTO",
    }


def test_evaluate_candidate_strategy_approves_robust_candidate():
    review = evaluate_candidate_strategy(_approved_metrics())

    assert review["governance_status"] == CANDIDATO_OPERACIONAL
    assert review["approved"] is True
    assert review["risk_level"] == "BAIXO"
    assert review["confidence_level"] == "ALTA"


def test_evaluate_candidate_strategy_blocks_overfitting():
    metrics = _approved_metrics()
    metrics.update(
        {
            "overfitting_alert": True,
            "robustness_class": "OVERFIT_PROVAVEL",
            "mean_train_net_return": 0.8,
            "mean_test_net_return": -0.2,
        }
    )

    review = evaluate_candidate_strategy(metrics)

    assert review["governance_status"] == BLOQUEADO_OVERFITTING
    assert review["approved"] is False
    assert any("overfitting" in reason.lower() for reason in review["reasons_against"])


def test_evaluate_candidate_strategy_flags_sample_concentration_and_liquidity():
    insufficient = evaluate_candidate_strategy({"windows_count": 1, "total_signals": 20})
    concentrated = evaluate_candidate_strategy({**_approved_metrics(), "avg_top_3_concentration_pct": 75})
    illiquid = evaluate_candidate_strategy({**_approved_metrics(), "liquidity_warning": True, "avg_execution_quality": "RUIM"})

    assert insufficient["governance_status"] == AMOSTRA_INSUFICIENTE
    assert concentrated["governance_status"] == CONCENTRACAO_EXCESSIVA
    assert illiquid["governance_status"] == LIQUIDEZ_INSUFICIENTE


def test_evaluate_candidate_strategy_promissor_and_observacao():
    promising = _approved_metrics()
    promising.update({"windows_count": 5, "positive_windows_pct": 55, "mean_test_net_return": 0.05, "mean_hit_rate": 0.51, "total_signals": 250})
    observation = _approved_metrics()
    observation.update({"positive_windows_pct": 45, "mean_test_net_return": 0.01, "mean_hit_rate": 0.49, "total_signals": 200})

    assert evaluate_candidate_strategy(promising)["governance_status"] == PROMISSOR
    assert evaluate_candidate_strategy(observation)["governance_status"] == EM_OBSERVACAO


def test_evaluate_threshold_candidate_uses_walk_forward_summary():
    threshold_result = {"samples": 978, "mean_net_return_5d": 0.16, "hit_rate_net_5d": 0.5566}
    walk_summary = {
        "windows_count": 3,
        "positive_windows_pct": 33.3,
        "mean_test_net_return": -0.3026,
        "mean_test_hit_rate": 0.4612,
        "avg_test_signals": 172,
        "avg_top_3_concentration_pct": 36.7,
        "overfitting_alert": True,
        "robustness_class": "OVERFIT_PROVAVEL",
    }

    review = evaluate_threshold_candidate(threshold_result, walk_summary)

    assert review["governance_status"] == BLOQUEADO_OVERFITTING
    assert review["approved"] is False


def test_rank_governed_candidates_prioritizes_status_and_oos_quality():
    candidates = pd.DataFrame(
        [
            {"candidate": "bloqueado", "governance_status": BLOQUEADO_OVERFITTING, "mean_test_net_return": 1.0, "mean_hit_rate": 0.7, "avg_top_3_concentration_pct": 10},
            {"candidate": "aprovado", "governance_status": CANDIDATO_OPERACIONAL, "mean_test_net_return": 0.2, "mean_hit_rate": 0.55, "avg_top_3_concentration_pct": 35},
            {"candidate": "promissor", "governance_status": PROMISSOR, "mean_test_net_return": 0.3, "mean_hit_rate": 0.56, "avg_top_3_concentration_pct": 25},
        ]
    )

    ranked = rank_governed_candidates(candidates)

    assert ranked.iloc[0]["candidate"] == "aprovado"
    assert ranked.iloc[-1]["candidate"] == "bloqueado"


def test_generate_governance_report_is_institutional():
    review = evaluate_candidate_strategy({"windows_count": 3, "positive_windows_pct": 33.3, "mean_test_net_return": -0.3, "overfitting_alert": True})
    report = generate_governance_report(review)

    assert "classificada como" in report
    assert "não altera" in report


def test_evaluate_regime_governance_restricts_or_blocks_by_regime():
    base = evaluate_candidate_strategy(_approved_metrics())
    regime_summary = pd.DataFrame(
        [
            {"regime_type": "primary_regime", "regime_value": "ALTA_TENDENCIAL", "signals_count": 200, "mean_net_return_5d": 0.4, "hit_rate_5d": 0.56},
            {"regime_type": "primary_regime", "regime_value": "ALTA_VOLATILIDADE", "signals_count": 180, "mean_net_return_5d": -0.8, "hit_rate_5d": 0.42},
        ]
    )
    restricted = evaluate_regime_governance(regime_summary, base)
    insufficient = evaluate_regime_governance(regime_summary.head(1), base)
    risky = evaluate_regime_governance(regime_summary.assign(mean_net_return_5d=-1.2), base)

    assert restricted["governance_status"] == CANDIDATO_RESTRITO_A_REGIME
    assert "ALTA_TENDENCIAL" in restricted["allowed_regimes"]
    assert "ALTA_VOLATILIDADE" in restricted["blocked_regimes"]
    assert insufficient["governance_status"] == BLOQUEADO_REGIME_INSUFICIENTE
    assert risky["governance_status"] == BLOQUEADO_REGIME_RISCO


def test_evaluate_event_context_governance_flags_insufficient_event_sample():
    base = evaluate_candidate_strategy(_approved_metrics())
    event_summary = pd.DataFrame(
        [{"group_type": "has_event", "group_value": True, "signals": 8, "mean_net_return_5d": 0.4, "hit_rate_5d": 0.6}]
    )

    review = evaluate_event_context_governance(event_summary, base)

    assert review["governance_status"] == BLOQUEADO_EVENTO_INSUFICIENTE
    assert review["approved"] is False


def test_evaluate_event_context_governance_restricts_event_driven_candidate():
    base = evaluate_candidate_strategy(_approved_metrics())
    event_summary = pd.DataFrame(
        [
            {"group_type": "has_event", "group_value": True, "signals": 80, "mean_net_return_5d": 0.5, "hit_rate_5d": 0.58},
            {"group_type": "has_event", "group_value": False, "signals": 300, "mean_net_return_5d": -0.2, "hit_rate_5d": 0.47},
        ]
    )

    review = evaluate_event_context_governance(event_summary, base)

    assert review["governance_status"] == CANDIDATO_EVENT_DRIVEN
    assert "MOVIMENTO_EVENT_DRIVEN" in review["allowed_event_contexts"]


def test_evaluate_event_context_governance_blocks_contra_signal():
    base = evaluate_candidate_strategy(_approved_metrics())
    event_summary = pd.DataFrame(
        [
            {"group_type": "event_context_type", "group_value": "EVENTO_CONTRA_SINAL", "signals": 50, "mean_net_return_5d": -0.8, "hit_rate_5d": 0.35},
            {"group_type": "has_event", "group_value": True, "signals": 80, "mean_net_return_5d": -0.3, "hit_rate_5d": 0.44},
        ]
    )

    review = evaluate_event_context_governance(event_summary, base)

    assert review["governance_status"] == BLOQUEADO_EVENTO_CONTRA_SINAL
    assert review["approved"] is False


def test_evaluate_event_context_governance_blocks_insufficient_coverage_before_contra_signal():
    base = evaluate_candidate_strategy(_approved_metrics())
    event_summary = pd.DataFrame(
        [
            {"group_type": "event_context_type", "group_value": "EVENTO_CONTRA_SINAL", "signals": 50, "mean_net_return_5d": -0.8, "hit_rate_5d": 0.35},
            {"group_type": "has_event", "group_value": True, "signals": 80, "mean_net_return_5d": -0.3, "hit_rate_5d": 0.44},
        ]
    )

    review = evaluate_event_context_governance(
        event_summary,
        base,
        coverage_metrics={"coverage_quality": "COBERTURA_INSUFICIENTE", "signals_with_event_pct": 0.05},
    )

    assert review["governance_status"] == BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE
    assert review["approved"] is False
