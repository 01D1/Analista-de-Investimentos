"""Tendências de cobertura da camada de eventos."""
from __future__ import annotations

from typing import Any

import pandas as pd


QUALITY_RANK = {
    "COBERTURA_BOA": 3,
    "COBERTURA_MEDIA": 2,
    "COBERTURA_FRACA": 1,
    "COBERTURA_INSUFICIENTE": 0,
}


def _direction(values: pd.Series) -> str:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2:
        return "INSUFICIENTE"
    delta = float(clean.iloc[-1] - clean.iloc[0])
    if delta > 0.02:
        return "MELHORANDO"
    if delta < -0.02:
        return "PIORANDO"
    return "ESTAVEL"


def _quality(values: pd.Series, best: bool) -> str:
    if values is None or values.empty:
        return ""
    ranked = values.dropna().astype(str).str.upper().map(QUALITY_RANK).dropna()
    if ranked.empty:
        return ""
    target = ranked.max() if best else ranked.min()
    for name, rank in QUALITY_RANK.items():
        if rank == target:
            return name
    return ""


def _source_count(value: Any) -> int:
    return len([part for part in str(value or "").split(",") if part.strip()])


def calculate_event_coverage_trend(coverage_runs_df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    columns = [
        "period",
        "runs_count",
        "avg_signals_with_event_pct",
        "avg_tickers_with_event_pct",
        "avg_events_loaded",
        "avg_events_after_dedup",
        "avg_sources_count",
        "best_coverage_quality",
        "worst_coverage_quality",
        "coverage_trend_direction",
    ]
    if coverage_runs_df is None or coverage_runs_df.empty:
        return pd.DataFrame(columns=columns)
    df = coverage_runs_df.copy()
    date_col = "created_at" if "created_at" in df.columns else "start_date"
    df["created_at_dt"] = pd.to_datetime(df.get(date_col), errors="coerce")
    df = df[df["created_at_dt"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=columns)
    df["period"] = df["created_at_dt"].dt.to_period(freq).astype(str)
    df["signals_pct"] = pd.to_numeric(df.get("signals_with_event_pct"), errors="coerce")
    df["tickers_pct"] = pd.to_numeric(df.get("tickers_with_event_pct"), errors="coerce")
    df["events_loaded_num"] = pd.to_numeric(df.get("events_loaded"), errors="coerce")
    df["events_after_dedup_num"] = pd.to_numeric(df.get("events_after_dedup"), errors="coerce")
    df["sources_count"] = df.get("sources", pd.Series(dtype=str)).apply(_source_count)
    rows = []
    grouped = df.sort_values("created_at_dt").groupby("period", sort=True)
    for period, group in grouped:
        rows.append(
            {
                "period": period,
                "runs_count": int(len(group)),
                "avg_signals_with_event_pct": round(float(group["signals_pct"].mean()), 6) if group["signals_pct"].notna().any() else 0.0,
                "avg_tickers_with_event_pct": round(float(group["tickers_pct"].mean()), 6) if group["tickers_pct"].notna().any() else 0.0,
                "avg_events_loaded": round(float(group["events_loaded_num"].mean()), 4) if group["events_loaded_num"].notna().any() else 0.0,
                "avg_events_after_dedup": round(float(group["events_after_dedup_num"].mean()), 4) if group["events_after_dedup_num"].notna().any() else 0.0,
                "avg_sources_count": round(float(group["sources_count"].mean()), 4) if not group.empty else 0.0,
                "best_coverage_quality": _quality(group.get("coverage_quality", pd.Series(dtype=str)), best=True),
                "worst_coverage_quality": _quality(group.get("coverage_quality", pd.Series(dtype=str)), best=False),
                "coverage_trend_direction": "",
            }
        )
    out = pd.DataFrame(rows, columns=columns)
    direction = _direction(out["avg_signals_with_event_pct"])
    out["coverage_trend_direction"] = direction
    return out


def calculate_regime_coverage_trend(coverage_by_regime_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "regime_type",
        "regime_value",
        "avg_coverage_pct",
        "runs_count",
        "coverage_quality_mode",
        "regimes_without_coverage_count",
        "trend_direction",
    ]
    if coverage_by_regime_df is None or coverage_by_regime_df.empty:
        return pd.DataFrame(columns=columns)
    df = coverage_by_regime_df.copy()
    df["coverage_pct"] = pd.to_numeric(df.get("signals_with_event_pct"), errors="coerce").fillna(0)
    sort_col = "coverage_run_id" if "coverage_run_id" in df.columns else None
    if sort_col:
        df = df.sort_values(sort_col)
    rows = []
    for (rtype, rval), group in df.groupby(["regime_type", "regime_value"], dropna=False):
        quality = group.get("coverage_quality", pd.Series(dtype=str)).fillna("INDEFINIDO").astype(str)
        rows.append(
            {
                "regime_type": rtype,
                "regime_value": rval,
                "avg_coverage_pct": round(float(group["coverage_pct"].mean()), 6),
                "runs_count": int(len(group)),
                "coverage_quality_mode": quality.mode().iloc[0] if not quality.mode().empty else "",
                "regimes_without_coverage_count": int((group["coverage_pct"] <= 0).sum()),
                "trend_direction": _direction(group["coverage_pct"]),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def generate_coverage_trend_report(coverage_trend_df: pd.DataFrame, regime_trend_df: pd.DataFrame | None = None) -> str:
    if coverage_trend_df is None or coverage_trend_df.empty:
        return "Sem histórico suficiente de cobertura de eventos para avaliar tendência."
    latest = coverage_trend_df.iloc[-1]
    avg = float(latest.get("avg_signals_with_event_pct") or 0)
    direction = latest.get("coverage_trend_direction") or "INSUFICIENTE"
    weak_text = ""
    if regime_trend_df is not None and not regime_trend_df.empty:
        weak = regime_trend_df[
            regime_trend_df["coverage_quality_mode"].astype(str).str.upper().isin(["COBERTURA_FRACA", "COBERTURA_INSUFICIENTE"])
        ]
        if not weak.empty:
            labels = (weak["regime_type"].astype(str) + "=" + weak["regime_value"].astype(str)).head(5).tolist()
            weak_text = f" Regimes com cobertura fraca: {', '.join(labels)}."
    return (
        f"A cobertura de eventos no período mais recente foi de {avg:.2%} dos sinais, "
        f"com tendência {direction}."
        f"{weak_text} Não use ausência de evento como evidência forte quando a cobertura estiver baixa."
    )
