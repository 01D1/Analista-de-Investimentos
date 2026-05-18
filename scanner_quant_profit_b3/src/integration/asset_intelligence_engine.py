"""Engine de inteligência integrada por ativo."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.integration.asset_intelligence_model import normalize_asset_intelligence_frame
from src.integration.connectors.event_regime_connector import load_latest_event_context, load_latest_regime_context
from src.integration.connectors.options_connector import load_latest_option_candidates, load_latest_option_walk_forward_status
from src.integration.connectors.quant_connector import load_latest_quant_signals, load_quant_governance_by_ticker
from src.integration.connectors.technical_connector import load_latest_technical_signals, load_latest_technical_walk_forward_status
from src.integration.connectors.valuation_connector import load_latest_valuation_data
from src.integration.integrated_explanations import encode_list, generate_integrated_explanation, generate_reasons_against, generate_reasons_for, generate_required_actions
from src.integration.integrated_governance import evaluate_integrated_governance
from src.risk.risk_store import load_latest_risk_snapshots
from src.utils import load_config, project_path


def _merge(base: pd.DataFrame, other: pd.DataFrame, on: str = "ticker") -> pd.DataFrame:
    if other.empty:
        return base
    return base.merge(other, on=on, how="left")


def _num(row, col: str, default: float = 0) -> float:
    value = pd.to_numeric(pd.Series([row.get(col, default)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else default


def _series_or_default(df: pd.DataFrame, col: str, default):
    if col in df.columns:
        return df[col].fillna(default)
    return pd.Series([default] * len(df), index=df.index)


def _load_risk_context(db_path: str | Path, tickers: list[str]) -> pd.DataFrame:
    df = load_latest_risk_snapshots(db_path, tickers)
    if df.empty:
        return pd.DataFrame(columns=["ticker"])
    out = df.copy()
    out = out.rename(
        columns={
            "parametric_var_95": "var_95",
            "limiting_factor": "risk_limiting_factor",
            "explanation": "risk_explanation",
        }
    )
    cols = [
        "ticker",
        "ensemble_vol",
        "var_95",
        "expected_shortfall_95",
        "recommended_size",
        "recommended_position_value",
        "risk_status",
        "risk_limiting_factor",
        "risk_explanation",
    ]
    for col in cols:
        if col not in out.columns:
            out[col] = pd.NA
    return out[cols]


def calculate_data_quality_score(row) -> float:
    score = 0
    score += 20 if pd.notna(row.get("technical_score_final")) else 0
    score += 20 if pd.notna(row.get("quant_score")) else 0
    score += 20 if bool(row.get("valuation_available")) else 0
    score += 15 if pd.notna(row.get("primary_regime")) else 0
    score += 10 if pd.notna(row.get("event_coverage_quality")) else 0
    score += 10 if bool(row.get("option_available")) else 0
    score += 5 if pd.notna(row.get("risk_status")) else 0
    blocked = any("BLOCKED" in str(row.get(c, "")).upper() for c in ["technical_oos_status", "quant_governance_status", "option_oos_governance_status", "risk_status"])
    score += 5 if not blocked else 0
    return round(float(min(score, 100)), 2)


def calculate_integrated_score(row) -> float:
    technical = _num(row, "technical_score_final", 50)
    quant = _num(row, "quant_score", 50)
    upside = _num(row, "upside_pct", 0)
    valuation = max(0, min(100, 50 + upside))
    event = 55 if bool(row.get("has_recent_event")) else 50
    regime = 60 if str(row.get("regime_governance_status", "")).upper() == "REGIME_OK" else 40
    options = _num(row, "option_structure_score", 50)
    data_quality = _num(row, "data_quality_score", 0)
    blocked = bool(row.get("governance_blocked"))
    score = technical * 0.22 + quant * 0.25 + valuation * 0.18 + event * 0.08 + regime * 0.10 + options * 0.07 + data_quality * 0.10
    risk_status = str(row.get("risk_status", "")).upper()
    if "RISK_BLOCKED" in risk_status:
        score = min(score, 45)
    elif risk_status == "RISK_WARNING":
        score = min(score, 65)
    if blocked:
        score = min(score, 45)
    return round(float(max(0, min(100, score))), 2)


def classify_integrated_status(row) -> str:
    if "RISK_BLOCKED" in str(row.get("risk_status", "")).upper():
        return "BLOQUEADO_GOVERNANCA"
    if bool(row.get("governance_blocked")):
        return "BLOQUEADO_GOVERNANCA"
    if _num(row, "data_quality_score", 0) < 35:
        return "BLOQUEADO_DADOS_INSUFICIENTES"
    tech = _num(row, "technical_score_final", 0)
    quant = _num(row, "quant_score", 0)
    upside = _num(row, "upside_pct", 0)
    if tech >= 70 and bool(row.get("valuation_available")) and upside < 0:
        return "DIVERGENCIA_TECNICA_VALUATION"
    if tech < 45 and upside > 15:
        return "DIVERGENCIA_TECNICA_VALUATION"
    if tech >= 70 and quant < 50:
        return "DIVERGENCIA_QUANT_TECNICA"
    favorable = int(tech >= 65) + int(quant >= 70) + int(bool(row.get("valuation_available")) and upside > 0) + int(bool(row.get("option_available")))
    if favorable >= 3:
        return "ALTA_CONVERGENCIA_ANALITICA"
    if favorable >= 2:
        return "ASSIMETRIA_A_INVESTIGAR"
    return "APENAS_MONITORAR"


def _default_db_path(db_path: str | Path | None) -> Path:
    return Path(db_path) if db_path else project_path(load_config()["database_path"])


def build_asset_intelligence_snapshot(
    tickers: list[str] | None = None,
    trade_date: str | None = None,
    db_path: str | Path | None = None,
    valuation_base_path: str | Path | None = None,
    include_technical: bool = True,
    include_quant: bool = True,
    include_valuation: bool = True,
    include_events: bool = True,
    include_regimes: bool = True,
    include_options: bool = True,
    include_risk: bool = True,
) -> pd.DataFrame:
    db = _default_db_path(db_path)
    ticker_list = [str(t).upper() for t in (tickers or [])]
    frames = []
    if include_technical:
        frames.append(load_latest_technical_signals(db, ticker_list or None)[["ticker"]])
    if include_quant:
        frames.append(load_latest_quant_signals(db, ticker_list or None)[["ticker"]])
    if include_valuation and ticker_list:
        frames.append(pd.DataFrame({"ticker": ticker_list}))
    base_tickers = ticker_list or sorted(set().union(*[set(f["ticker"].dropna().astype(str)) for f in frames if not f.empty]))
    if not base_tickers:
        return normalize_asset_intelligence_frame(pd.DataFrame())
    out = pd.DataFrame({"ticker": base_tickers})
    if include_technical:
        out = _merge(out, load_latest_technical_signals(db, base_tickers))
        out = _merge(out, load_latest_technical_walk_forward_status(db, base_tickers))
    if include_quant:
        out = _merge(out, load_latest_quant_signals(db, base_tickers))
        out = _merge(out, load_quant_governance_by_ticker(db, base_tickers))
    if include_valuation:
        out = _merge(out, load_latest_valuation_data(valuation_base_path, base_tickers))
    if include_events:
        out = _merge(out, load_latest_event_context(db, base_tickers))
    if include_regimes:
        regimes = load_latest_regime_context(db)
        if not regimes.empty:
            for col in regimes.columns:
                out[col] = regimes.iloc[0][col]
    if include_options:
        out = _merge(out, load_latest_option_candidates(db, base_tickers))
        oos = load_latest_option_walk_forward_status(db, base_tickers)
        if not oos.empty:
            out = out.drop(columns=["option_oos_governance_status"], errors="ignore").merge(oos, on="ticker", how="left")
    if include_risk:
        out = _merge(out, _load_risk_context(db, base_tickers))
    default_date = trade_date or pd.Timestamp.today().date().isoformat()
    out["trade_date"] = _series_or_default(out, "trade_date", default_date)
    out["option_available"] = _series_or_default(out, "option_available", 0).astype(bool)
    out["valuation_available"] = _series_or_default(out, "valuation_available", False).astype(bool)
    out["has_recent_event"] = _series_or_default(out, "has_recent_event", 0).astype(int)
    out["governance_blocked"] = out.apply(lambda r: any("BLOCKED" in str(r.get(c, "")).upper() or "BLOQUEADO" in str(r.get(c, "")).upper() for c in ["technical_oos_status", "quant_governance_status", "option_oos_governance_status", "event_governance_status", "risk_status"]), axis=1)
    out["data_quality_score"] = out.apply(calculate_data_quality_score, axis=1)
    out["integrated_score"] = out.apply(calculate_integrated_score, axis=1)
    out["integrated_status"] = out.apply(classify_integrated_status, axis=1)
    governance = out.apply(evaluate_integrated_governance, axis=1)
    out["integrated_governance_status"] = [g["integrated_governance_status"] for g in governance]
    out["integrated_confidence"] = [g["confidence_level"] for g in governance]
    out["reasons_for"] = out.apply(lambda r: encode_list(generate_reasons_for(r)), axis=1)
    out["reasons_against"] = out.apply(lambda r: encode_list(generate_reasons_against(r)), axis=1)
    out["required_actions"] = out.apply(lambda r: encode_list(generate_required_actions(r)), axis=1)
    out["explanation"] = out.apply(generate_integrated_explanation, axis=1)
    out["metadata_json"] = out.apply(lambda r: json.dumps({"governance": evaluate_integrated_governance(r)}, ensure_ascii=False), axis=1)
    return normalize_asset_intelligence_frame(out)
