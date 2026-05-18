"""Modelo padronizado para cadeias de opções e estruturas."""
from __future__ import annotations

import pandas as pd


OPTION_COLUMNS = [
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "spread",
    "spread_pct",
    "volume",
    "trades",
    "financial_volume",
    "open_interest",
    "underlying_price",
    "moneyness_pct",
    "moneyness_class",
    "intrinsic_value",
    "extrinsic_value",
    "extrinsic_pct",
    "breakeven",
    "theoretical_value",
    "implied_volatility",
    "historical_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    "risk_score",
    "opportunity_score",
    "metadata_json",
]

STRUCTURE_COLUMNS = [
    "structure_id",
    "structure_type",
    "underlying",
    "maturity_date",
    "legs_json",
    "net_debit",
    "net_credit",
    "max_profit",
    "max_loss",
    "breakeven",
    "payoff_ratio",
    "probability_hint",
    "liquidity_score",
    "risk_score",
    "suitability_notes",
    "metadata_json",
]


def empty_options_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=OPTION_COLUMNS)


def empty_structures_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=STRUCTURE_COLUMNS)
