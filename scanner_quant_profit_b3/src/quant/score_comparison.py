"""Comparação e calibração entre score legado e score quantitativo."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd


HIGH_SCORE = 80.0
LOW_SCORE = 40.0
STRICT_NEW_SCORE_MAX = 65.0
AGGRESSIVE_LEGACY_MAX = 65.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return default if np.isnan(out) else out
    except (TypeError, ValueError):
        return default


def _signal_family(signal: Any) -> str:
    text = str(signal or "").upper()
    if any(token in text for token in ["COMPRA", "FORÇA", "ROMPIMENTO"]):
        return "FORTE"
    if any(token in text for token in ["FRAQUEZA", "SEM ASSIMETRIA", "DESCARTAR"]):
        return "FRACO"
    if any(token in text for token in ["OBSERVAR", "NEUTRO", "PULLBACK", "REVERSÃO", "REVERSAO"]):
        return "MEDIO"
    return "INDEFINIDO"


def _classify_divergence(row: Mapping[str, Any], rank_divergence_threshold: int) -> str:
    legacy = _to_float(row.get("score"))
    new = _to_float(row.get("score_final"))
    legacy_family = _signal_family(row.get("signal"))
    new_family = _signal_family(row.get("signal_type"))
    rank_change = abs(int(row.get("rank_change", 0)))

    if legacy >= HIGH_SCORE and new <= LOW_SCORE and legacy_family != new_family:
        return "DIVERGENTE"
    if rank_change >= rank_divergence_threshold and legacy_family != new_family:
        return "DIVERGENTE"
    if legacy >= HIGH_SCORE and new >= HIGH_SCORE:
        return "CONVERGENTE_FORTE"
    if legacy <= LOW_SCORE and new <= LOW_SCORE:
        return "CONVERGENTE_FRACO"
    if legacy >= HIGH_SCORE and new < HIGH_SCORE:
        return "NOVO_SCORE_MAIS_RIGOROSO"
    if legacy <= AGGRESSIVE_LEGACY_MAX and new >= HIGH_SCORE:
        return "NOVO_SCORE_MAIS_AGRESSIVO"
    if legacy_family != "INDEFINIDO" and new_family != "INDEFINIDO" and legacy_family != new_family:
        return "DIVERGENTE"
    return "NEUTRO"


def compare_scores(
    df: pd.DataFrame,
    *,
    asset_col: str = "asset",
    legacy_score_col: str = "score",
    new_score_col: str = "score_final",
    legacy_signal_col: str = "signal",
    new_signal_col: str = "signal_type",
    rank_divergence_threshold: int = 5,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy().reset_index(drop=True)
    out["score"] = pd.to_numeric(out[legacy_score_col], errors="coerce").fillna(0.0)
    out["score_final"] = pd.to_numeric(out[new_score_col], errors="coerce").fillna(0.0)
    out["score_diff"] = (out["score_final"] - out["score"]).round(4)
    out["score_diff_abs"] = out["score_diff"].abs().round(4)
    out["score_diff_pct"] = np.where(
        out["score"] != 0,
        (out["score_diff"] / out["score"] * 100.0).round(4),
        0.0,
    )

    out["legacy_rank"] = out["score"].rank(method="min", ascending=False).astype(int)
    out["new_rank"] = out["score_final"].rank(method="min", ascending=False).astype(int)
    out["rank_change"] = out["new_rank"] - out["legacy_rank"]
    out["rank_change_abs"] = out["rank_change"].abs()

    if legacy_signal_col not in out.columns:
        out[legacy_signal_col] = ""
    if new_signal_col not in out.columns:
        out[new_signal_col] = ""
    if asset_col not in out.columns:
        out[asset_col] = out.index.astype(str)

    out["legacy_signal_family"] = out[legacy_signal_col].apply(_signal_family)
    out["new_signal_family"] = out[new_signal_col].apply(_signal_family)
    out["signal_divergence"] = out["legacy_signal_family"] != out["new_signal_family"]
    out["divergence_type"] = out.apply(
        lambda row: _classify_divergence(row, rank_divergence_threshold),
        axis=1,
    )

    return out


def score_distribution(df: pd.DataFrame, score_col: str = "score_final") -> dict:
    scores = pd.to_numeric(df.get(score_col, pd.Series(dtype=float)), errors="coerce").dropna()
    if scores.empty:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "percentiles": {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0},
            "buckets": {"0_20": 0, "20_40": 0, "40_60": 0, "60_80": 0, "80_100": 0},
        }

    buckets = {
        "0_20": int(((scores >= 0) & (scores < 20)).sum()),
        "20_40": int(((scores >= 20) & (scores < 40)).sum()),
        "40_60": int(((scores >= 40) & (scores < 60)).sum()),
        "60_80": int(((scores >= 60) & (scores < 80)).sum()),
        "80_100": int(((scores >= 80) & (scores <= 100)).sum()),
    }

    return {
        "count": int(scores.count()),
        "mean": round(float(scores.mean()), 4),
        "median": round(float(scores.median()), 4),
        "std": round(float(scores.std(ddof=0)), 4),
        "min": round(float(scores.min()), 4),
        "max": round(float(scores.max()), 4),
        "percentiles": {
            "p10": round(float(scores.quantile(0.10)), 4),
            "p25": round(float(scores.quantile(0.25)), 4),
            "p50": round(float(scores.quantile(0.50)), 4),
            "p75": round(float(scores.quantile(0.75)), 4),
            "p90": round(float(scores.quantile(0.90)), 4),
        },
        "buckets": buckets,
    }


def detect_score_inflation(
    df: pd.DataFrame,
    *,
    score_col: str = "score_final",
    high_threshold: float = 80.0,
    max_share: float = 0.40,
) -> dict:
    scores = pd.to_numeric(df.get(score_col, pd.Series(dtype=float)), errors="coerce").dropna()
    if scores.empty:
        return {"has_alert": False, "high_score_share": 0.0, "message": "Sem scores para avaliar inflação."}

    share = round(float((scores >= high_threshold).mean()), 4)
    has_alert = share > max_share
    message = (
        "Possível inflação de score: muitos ativos classificados como fortes."
        if has_alert
        else "Distribuição de score sem alerta de inflação."
    )
    return {"has_alert": has_alert, "high_score_share": share, "message": message}


def score_distribution_report(df: pd.DataFrame, score_col: str = "score_final") -> dict:
    dist = score_distribution(df, score_col=score_col)
    dist["inflation_alert"] = detect_score_inflation(df, score_col=score_col)
    return dist


def textual_comparison_report(compared: pd.DataFrame, distribution: Mapping[str, Any] | None = None) -> str:
    if compared is None or compared.empty:
        return "Nenhum ativo disponível para comparação de scores."

    distribution = distribution or score_distribution_report(compared)
    counts = compared["divergence_type"].value_counts().to_dict()
    total = len(compared)
    strong = int(counts.get("CONVERGENTE_FORTE", 0))
    weak = int(counts.get("CONVERGENTE_FRACO", 0))
    strict = int(counts.get("NOVO_SCORE_MAIS_RIGOROSO", 0))
    aggressive = int(counts.get("NOVO_SCORE_MAIS_AGRESSIVO", 0))
    divergent = int(counts.get("DIVERGENTE", 0))
    mean = distribution.get("mean", 0.0)
    p90 = distribution.get("percentiles", {}).get("p90", 0.0)
    alert = distribution.get("inflation_alert", {}).get("message", "")

    return (
        f"Dos {total} ativos analisados, {strong} tiveram convergência forte entre o score legado "
        f"e o score novo. {weak} tiveram convergência fraca. Em {strict} casos, o novo score foi "
        f"mais rigoroso. Em {aggressive} casos, o novo score foi mais agressivo. "
        f"{divergent} casos ficaram divergentes. A média do score_final foi {mean}, "
        f"com percentil 90 em {p90}. {alert}"
    )
