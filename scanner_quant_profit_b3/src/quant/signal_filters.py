"""Filtros opcionais de qualidade para sinais quantitativos."""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


EXECUTION_QUALITY_ORDER = {
    "INVIAVEL": 0,
    "RUIM": 1,
    "ACEITAVEL": 2,
    "ACEITÁVEL": 2,
    "BOA": 3,
    "EXCELENTE": 4,
}

SCORE_BUCKET_ORDER = {
    "0_20": 0,
    "0-20": 0,
    "20_40": 1,
    "20-40": 1,
    "40_60": 2,
    "40-60": 2,
    "60_80": 3,
    "60-80": 3,
    "80_100": 4,
    "80-100": 4,
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return default if pd.isna(out) else out
    except (TypeError, ValueError):
        return default


def _confidence(value: Any) -> float:
    if isinstance(value, str):
        normalized = value.strip().upper()
        mapping = {
            "ALTA": 0.85,
            "ALTO": 0.85,
            "MEDIA": 0.65,
            "MÉDIA": 0.65,
            "MEDIO": 0.65,
            "MÉDIO": 0.65,
            "BAIXA": 0.35,
            "BAIXO": 0.35,
        }
        if normalized in mapping:
            return mapping[normalized]
    number = _num(value)
    return number / 100.0 if number > 1.0 else number


def _quality_rank(value: Any) -> int:
    return EXECUTION_QUALITY_ORDER.get(str(value or "").strip().upper(), 2)


def _bucket_rank(value: Any) -> int:
    return SCORE_BUCKET_ORDER.get(str(value or "").strip().upper(), -1)


def _is_tradeable(row: pd.Series) -> bool:
    value = row.get("is_tradeable", 1)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "sim", "yes"}
    return bool(value) if pd.notna(value) else True


def classify_signal_quality(row: pd.Series | dict[str, Any]) -> str:
    """Classifica qualidade operacional do sinal sem alterar o score original."""
    item = pd.Series(row) if not isinstance(row, pd.Series) else row
    score = _num(item.get("score_final"))
    confidence = _confidence(item.get("signal_confidence", 0.0))
    liquidity_score = _num(item.get("score_liquidez"))
    risk_score = _num(item.get("score_risco"), default=50.0)
    execution_rank = _quality_rank(item.get("execution_quality", "ACEITAVEL"))
    net_5d = item.get("net_return_5d", None)

    if not _is_tradeable(item):
        return "DESCARTAR"
    if execution_rank <= EXECUTION_QUALITY_ORDER["RUIM"]:
        return "DESCARTAR"
    if score < 40 or liquidity_score < 30 or risk_score < 25:
        return "DESCARTAR"
    if net_5d is not None and pd.notna(net_5d) and _num(net_5d) <= -1.0:
        return "DESCARTAR"
    if score >= 80 and confidence >= 0.70 and execution_rank >= 3 and liquidity_score >= 70 and risk_score >= 50:
        return "ALTA_QUALIDADE"
    if score >= 70 and confidence >= 0.60 and execution_rank >= 2:
        return "BOA_QUALIDADE"
    if score >= 60 and confidence >= 0.45 and execution_rank >= 2:
        return "QUALIDADE_MEDIA"
    return "BAIXA_QUALIDADE"


def _row_filter_reasons(row: pd.Series, config: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if config.get("remove_inviavel", True) and str(row.get("execution_quality", "")).upper() == "INVIAVEL":
        reasons.append("execucao_inviavel")
    if config.get("remove_ruim", False) and str(row.get("execution_quality", "")).upper() == "RUIM":
        reasons.append("execucao_ruim")
    if config.get("only_tradeable", False) and not _is_tradeable(row):
        reasons.append("nao_tradeable")
    if _num(row.get("score_final")) < _num(config.get("min_score_final"), 0.0):
        reasons.append("score_final_baixo")
    if _confidence(row.get("signal_confidence")) < _num(config.get("min_confidence"), 0.0):
        reasons.append("confianca_baixa")
    if _num(row.get("volume")) < _num(config.get("min_volume"), 0.0):
        reasons.append("volume_baixo")
    if _num(row.get("trades")) < _num(config.get("min_trades"), 0.0):
        reasons.append("negocios_baixos")
    if _num(row.get("score_liquidez")) < _num(config.get("min_liquidity_score"), 0.0):
        reasons.append("liquidez_baixa")
    if _num(row.get("score_risco"), 100.0) < _num(config.get("min_risk_score"), 0.0):
        reasons.append("risco_excessivo")
    min_execution_quality = config.get("min_execution_quality")
    if min_execution_quality and _quality_rank(row.get("execution_quality")) < _quality_rank(min_execution_quality):
        reasons.append("qualidade_execucao_baixa")
    min_score_bucket = config.get("min_score_bucket")
    if min_score_bucket and _bucket_rank(row.get("score_bucket")) < _bucket_rank(min_score_bucket):
        reasons.append("faixa_score_baixa")
    allowed_signal_types = config.get("allowed_signal_types")
    if allowed_signal_types:
        allowed = {str(item).upper() for item in allowed_signal_types}
        if str(row.get("signal_type", "")).upper() not in allowed:
            reasons.append("tipo_sinal_fora_do_filtro")
    if config.get("require_positive_expected_net", False):
        expected = row.get("expected_net_return", row.get("net_return_5d"))
        if pd.notna(expected) and _num(expected) <= 0:
            reasons.append("retorno_liquido_esperado_nao_positivo")
    if config.get("require_no_overfitting", False) and bool(row.get("overfitting_flag", False)):
        reasons.append("overfitting_flag")
    if config.get("drop_discard_quality", False) and row.get("signal_quality") == "DESCARTAR":
        reasons.append("qualidade_descartar")
    return reasons


def apply_quality_filters(df: pd.DataFrame, config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Aplica filtros opcionais e retorna apenas sinais que passaram."""
    if df is None or df.empty:
        return pd.DataFrame()
    config = config or {}
    out = df.copy()
    out["signal_quality"] = out.apply(classify_signal_quality, axis=1)
    out["filter_reasons"] = out.apply(lambda row: ";".join(_row_filter_reasons(row, config)), axis=1)
    return out[out["filter_reasons"].eq("")].reset_index(drop=True)


def _mean(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float(values.mean()), 4) if not values.empty else 0.0


def _hit(df: pd.DataFrame, col: str) -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float((values > 0).mean()), 4) if not values.empty else 0.0


def _removed_reasons(before_df: pd.DataFrame, after_df: pd.DataFrame) -> dict[str, int]:
    if before_df is None or before_df.empty:
        return {}
    if "filter_reasons" in before_df.columns:
        candidates = before_df
    else:
        candidates = before_df.copy()
        candidates["signal_quality"] = candidates.apply(classify_signal_quality, axis=1)
        candidates["filter_reasons"] = candidates["signal_quality"].where(candidates["signal_quality"].eq("DESCARTAR"), "")

    after_index = set(after_df.index) if after_df is not None else set()
    removed = candidates.loc[~candidates.index.isin(after_index)]
    counter: Counter[str] = Counter()
    for value in removed.get("filter_reasons", pd.Series(dtype=str)).fillna(""):
        parts = [part for part in str(value).split(";") if part]
        counter.update(parts or ["sem_motivo_registrado"])
    return dict(counter)


def summarize_filter_impact(before_df: pd.DataFrame, after_df: pd.DataFrame) -> dict[str, Any]:
    """Resume impacto dos filtros em retornos, hit rate e quantidade de sinais."""
    before = before_df if before_df is not None else pd.DataFrame()
    after = after_df if after_df is not None else pd.DataFrame()
    before_count = int(len(before))
    after_count = int(len(after))
    removed_pct = (before_count - after_count) / before_count * 100.0 if before_count else 0.0
    summary = {
        "signals_before": before_count,
        "signals_after": after_count,
        "removed_pct": round(float(removed_pct), 4),
        "mean_gross_return_before": _mean(before, "future_return_5d"),
        "mean_gross_return_after": _mean(after, "future_return_5d"),
        "mean_net_return_before": _mean(before, "net_return_5d"),
        "mean_net_return_after": _mean(after, "net_return_5d"),
        "hit_rate_before": _hit(before, "net_return_5d" if "net_return_5d" in before.columns else "future_return_5d"),
        "hit_rate_after": _hit(after, "net_return_5d" if "net_return_5d" in after.columns else "future_return_5d"),
        "removed_reasons": _removed_reasons(before, after),
    }
    if "signal_type" in after.columns and not after.empty:
        summary["best_signal_type_after"] = str(after.groupby("signal_type")["net_return_5d"].mean(numeric_only=True).sort_values(ascending=False).index[0]) if "net_return_5d" in after else str(after["signal_type"].mode().iloc[0])
    if "score_bucket" in after.columns and not after.empty:
        summary["best_score_bucket_after"] = str(after.groupby("score_bucket")["net_return_5d"].mean(numeric_only=True).sort_values(ascending=False).index[0]) if "net_return_5d" in after else str(after["score_bucket"].mode().iloc[0])
    return summary


def generate_quality_filter_report(
    filter_summary: dict[str, Any],
    threshold_results: pd.DataFrame | None = None,
    capacity_summary: dict[str, Any] | None = None,
) -> str:
    before = int(filter_summary.get("signals_before", 0))
    after = int(filter_summary.get("signals_after", 0))
    net_before = float(filter_summary.get("mean_net_return_before", 0.0))
    net_after = float(filter_summary.get("mean_net_return_after", 0.0))
    removed = float(filter_summary.get("removed_pct", 0.0))
    text = (
        f"Os filtros reduziram os sinais de {before} para {after}, removendo {removed:.1f}% da amostra. "
        f"O retorno líquido médio D+5 passou de {net_before:.4f}% para {net_after:.4f}%."
    )
    if after < 100 and before >= 100:
        text += " A amostra filtrada ficou pequena e precisa de validação fora da amostra."
    if threshold_results is not None and not threshold_results.empty:
        best = threshold_results.iloc[0]
        text += (
            f" A melhor combinação testada teve {int(best.get('samples', 0))} sinais "
            f"e retorno líquido D+5 de {float(best.get('mean_net_return_5d', 0.0)):.4f}%."
        )
    if capacity_summary:
        text += f" Capacidade operacional média estimada: {capacity_summary.get('mean_capacity', 0):,.2f}."
    text += " A leitura é estatística e não substitui validação operacional nem recomendação de investimento."
    return text
