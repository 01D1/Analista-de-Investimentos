from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.integration.valuation_bridge import get_valuations_batch


VALUATION_COLUMNS = [
    "ticker",
    "valuation_available",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "valuation_governance_status",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=VALUATION_COLUMNS)


def _outputs_dir(base_path: str | Path | None) -> Path:
    if base_path is None:
        return Path("..") / "12_PYTHON" / "pipeline banco completo" / "outputs"
    base = Path(base_path)
    if (base / "outputs").exists():
        return base / "outputs"
    return base


def normalize_valuation_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in VALUATION_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out["valuation_available"] = out["valuation_available"].fillna(False).astype(bool)
    return out[VALUATION_COLUMNS]


def load_latest_valuation_data(base_path: str | Path | None, tickers: list[str] | None = None) -> pd.DataFrame:
    tickers = [str(t).upper() for t in (tickers or [])]
    if not tickers:
        return _empty()
    outputs = _outputs_dir(base_path)
    if not outputs.exists():
        return _empty()
    valuations = get_valuations_batch(tickers, outputs)
    rows = []
    for ticker in tickers:
        val = valuations.get(ticker, {}) or {}
        available = bool(val)
        rows.append(
            {
                "ticker": ticker,
                "valuation_available": available,
                "fair_value": val.get("preco_alvo"),
                "upside_pct": val.get("upside_pct"),
                "valuation_method": "DCF/planilha" if available else pd.NA,
                "valuation_confidence": 0.6 if available else 0.0,
                "fundamental_quality_score": pd.NA,
                "financial_health_score": pd.NA,
                "profitability_score": pd.NA,
                "growth_score": pd.NA,
                "leverage_score": pd.NA,
                "valuation_governance_status": "VALUATION_AVAILABLE" if available else "VALUATION_MISSING",
            }
        )
    return normalize_valuation_data(pd.DataFrame(rows))


def load_fair_values(base_path: str | Path | None, tickers: list[str] | None = None) -> pd.DataFrame:
    return load_latest_valuation_data(base_path, tickers)[["ticker", "fair_value", "upside_pct", "valuation_method"]]


def load_fundamental_quality(base_path: str | Path | None, tickers: list[str] | None = None) -> pd.DataFrame:
    return load_latest_valuation_data(base_path, tickers)[["ticker", "fundamental_quality_score", "financial_health_score", "profitability_score", "growth_score", "leverage_score"]]

