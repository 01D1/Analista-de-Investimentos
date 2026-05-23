"""Aplicação simulada de variações LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd


def _variant_dict(variant: Any) -> dict:
    if isinstance(variant, pd.Series):
        return variant.to_dict()
    if is_dataclass(variant):
        return asdict(variant)
    return dict(variant)


def _params(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _source_col(df: pd.DataFrame) -> pd.Series:
    return df["signal_source"].astype(str).str.lower() if "signal_source" in df.columns else pd.Series("", index=df.index)


def _confirmation_keys(context: dict, min_count: int) -> set[tuple[str, str]]:
    signals_by_source = (context or {}).get("signals_by_source", {})
    counter: Counter[tuple[str, str]] = Counter()
    for df in signals_by_source.values():
        if df is None or df.empty or not {"trade_date", "ticker"}.issubset(df.columns):
            continue
        keys = set(zip(df["trade_date"].astype(str), df["ticker"].astype(str).str.upper()))
        counter.update(keys)
    return {key for key, count in counter.items() if count >= int(min_count)}


def _integrated_keys(context: dict) -> set[tuple[str, str]]:
    integrated = (context or {}).get("signals_by_source", {}).get("integrated", pd.DataFrame())
    if integrated is None or integrated.empty or not {"trade_date", "ticker"}.issubset(integrated.columns):
        return set()
    return set(zip(integrated["trade_date"].astype(str), integrated["ticker"].astype(str).str.upper()))


def _regime_dates(context: dict, regimes: set[str]) -> set[str]:
    regimes_df = (context or {}).get("regimes_df", pd.DataFrame())
    if regimes_df is None or regimes_df.empty or "trade_date" not in regimes_df.columns:
        return set()
    cols = [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes_df.columns]
    mask = pd.Series(False, index=regimes_df.index)
    for col in cols:
        mask = mask | regimes_df[col].astype(str).str.upper().isin(regimes)
    return set(regimes_df.loc[mask, "trade_date"].astype(str))


def _mark_removed(df: pd.DataFrame, mask: pd.Series, reason: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    removed = df.loc[mask].copy()
    kept = df.loc[~mask].copy()
    if not removed.empty:
        removed["exclusion_reason"] = reason
    return kept, removed


def apply_limit_signal_source_variant(signals_df: pd.DataFrame, variant, context: dict | None = None):
    """Aplica uma variação paramétrica em sinais simulados.

    Retorna sinais remanescentes, sinais removidos e resumo de aplicação. É uma
    hipótese em estudo, sem recomendação e sem aplicação automática.
    """
    if signals_df is None or signals_df.empty:
        summary = {"original_signals": 0, "remaining_signals": 0, "removed_signals": 0, "removed_pct": 0.0, "sources_removed_json": "{}", "reasons_json": "{}"}
        return pd.DataFrame(), pd.DataFrame(), summary
    df = signals_df.copy()
    df["trade_date"] = df["trade_date"].astype(str)
    df["ticker"] = df["ticker"].astype(str).str.upper()
    if "signal_source" not in df.columns:
        df["signal_source"] = str((context or {}).get("signal_source", "")).lower()
    var = _variant_dict(variant)
    params = _params(var.get("parameters_json"))
    action = str(params.get("action", "")).lower()
    target = str(var.get("target_source") or "").lower()
    source = _source_col(df)
    mask = pd.Series(False, index=df.index)
    reason = "NO_FILTER"

    if action == "limit_source":
        target_mask = source.eq(target) if target else pd.Series(True, index=df.index)
        keep_every = max(2, int(params.get("keep_every_n", 2) or 2))
        order = df.groupby("signal_source").cumcount()
        mask = target_mask & (order % keep_every != 0)
        reason = f"LIMIT_SOURCE_{target or 'ALL'}"
    elif action == "require_confirmations":
        keys = _confirmation_keys(context or {}, int(var.get("required_confirmations") or 2))
        mask = ~df.apply(lambda r: (str(r["trade_date"]), str(r["ticker"]).upper()) in keys, axis=1)
        reason = "MISSING_TWO_SOURCE_CONFIRMATION"
    elif action == "require_integrated":
        keys = _integrated_keys(context or {})
        mask = ~df.apply(lambda r: (str(r["trade_date"]), str(r["ticker"]).upper()) in keys, axis=1)
        reason = "MISSING_INTEGRATED_CONFIRMATION"
    elif action == "cost_drag_filter":
        limit = float(var.get("cost_limit") or 0.002)
        cost_by_source = (context or {}).get("source_cost_drag", {})
        if "estimated_cost_drag" in df.columns:
            mask = pd.to_numeric(df["estimated_cost_drag"], errors="coerce").fillna(0) > limit
        else:
            mask = source.map(lambda s: float(cost_by_source.get(str(s), 0)) > limit)
        reason = "CONTROL_COST_LIMIT"
    elif action == "regime_filter":
        regimes = {r.strip().upper() for r in str(var.get("regime_filter") or "").split(",") if r.strip()}
        dates = _regime_dates(context or {}, regimes)
        mask = df["trade_date"].isin(dates)
        reason = "CONTROL_REGIME_FRAGILITY"
    elif action == "asset_filter":
        fragile_assets = {str(x).upper() for x in (context or {}).get("fragile_assets", [])}
        if not fragile_assets and "signal_score" in df.columns:
            scores = pd.to_numeric(df["signal_score"], errors="coerce")
            fragile_assets = set(df.loc[scores <= scores.quantile(0.25), "ticker"].astype(str).str.upper())
        mask = df["ticker"].isin(fragile_assets)
        reason = "CONTROL_ASSET_FRAGILITY"
    elif action == "slippage_filter":
        limit = float(var.get("slippage_limit") or 0.0015)
        slippage_by_source = (context or {}).get("source_slippage", {})
        if "estimated_slippage" in df.columns:
            mask = pd.to_numeric(df["estimated_slippage"], errors="coerce").fillna(0) > limit
        else:
            mask = source.map(lambda s: float(slippage_by_source.get(str(s), 0)) > limit)
        reason = "CONTROL_SLIPPAGE_LIMIT"
    elif action == "turnover_filter":
        limit = float(params.get("turnover_limit", 0.35))
        turnover_by_source = (context or {}).get("source_turnover", {})
        mask = source.map(lambda s: float(turnover_by_source.get(str(s), 0)) > limit)
        reason = "CONTROL_TURNOVER_LIMIT"

    filtered, removed = _mark_removed(df, mask.fillna(False), reason)
    sources_removed = removed["signal_source"].astype(str).value_counts().to_dict() if not removed.empty else {}
    reasons = removed["exclusion_reason"].astype(str).value_counts().to_dict() if not removed.empty else {}
    summary = {
        "original_signals": int(len(df)),
        "remaining_signals": int(len(filtered)),
        "removed_signals": int(len(removed)),
        "removed_pct": round(float(len(removed) / len(df)), 4) if len(df) else 0.0,
        "sources_removed_json": json.dumps(sources_removed, ensure_ascii=False, default=str),
        "reasons_json": json.dumps(reasons, ensure_ascii=False, default=str),
    }
    return filtered.reset_index(drop=True), removed.reset_index(drop=True), summary
