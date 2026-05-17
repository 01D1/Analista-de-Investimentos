"""
intelligence_layer.py
---------------------
Phase 4 — Intelligence Layer

Generates schema-enforced AI investment theses (InvestmentThesis) per ticker using
Claude claude-sonnet-4-6 via instructor.from_anthropic() (ANTHROPIC_TOOLS mode).

Public API:
    run_ticker(ticker: str) -> ThesisResult
    run_all() -> list[ThesisResult]

Decisions implemented:
    D-01, D-02: InvestmentThesis + Driver + Risk Pydantic schema
    D-03: DCF fair value cross-check (+-10% tolerance)
    D-04: IntelligenceClient (separate from LLMClient)
    D-05: Hard-fail on instructor validation failure -> IngestionError
    D-06: instructor.Mode.ANTHROPIC_TOOLS
    D-07, D-08: Jinja2 template with full data snapshot injection
    D-09, D-10, D-11: SHA-256 input hash gate + 2/day cap
    D-12, D-13, D-14: thesis_versions table + version_num auto-increment + thesis_latest VIEW
    D-15, D-16, D-17, D-18: opportunity_signals computation + conviction scoring + top-3 storage
    D-20: ThesisResult public return type
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.ingestion.db import get_connection
from src.utils.errors import IngestionError
from src.utils.logger import get_logger

log = get_logger(__name__)

# -- Jinja2 template directory -----------------------------------------------
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# -- Pydantic models — D-01, D-02 --------------------------------------------


class Driver(BaseModel):
    """Thesis investment driver — D-01."""

    title: str
    description: str
    impact: Literal["HIGH", "MEDIUM", "LOW"]


class Risk(BaseModel):
    """Thesis risk factor — D-01."""

    title: str
    description: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class InvestmentThesis(BaseModel):
    """Schema-enforced investment thesis — D-02.
    All fields in Portuguese. fair_value_brl is injected from DCF — never LLM-computed.
    """

    bull_case: str = Field(..., description="Narrativa otimista de investimento")
    bear_case: str = Field(..., description="Narrativa pessimista / principais riscos")
    drivers: list[Driver] = Field(..., min_length=3, max_length=5)
    risks: list[Risk] = Field(..., min_length=3, max_length=5)
    fair_value_brl: float = Field(
        ...,
        description="Preco justo em BRL — injetado do DCF, nunca calculado pelo LLM",
    )
    methodology_disclosure: str = Field(
        ..., description="Modelo utilizado (DCF/DDM) e principais inputs"
    )
    positioning: Literal["COMPRAR", "MANTER", "VENDER"]
    confidence: Literal["ALTA", "MEDIA", "BAIXA"]
    rationale: str = Field(
        ..., description="2-3 frases explicando a decisao de posicionamento"
    )
    summary_one_line: str = Field(
        ..., description="Uma frase para alertas Telegram (Phase 5)"
    )


class OpportunitySignal(BaseModel):
    """Opportunity signal for a ticker — D-16."""

    ticker: str
    signal_type: Literal["DCF_DIVERGENCE", "MOMENTUM_CROSSOVER", "IPE_EVENT"]
    description: str = Field(..., description="One sentence explanation")
    conviction_score: int = Field(..., ge=0, le=100)
    generated_at: str


# -- Public return type — D-20 ------------------------------------------------


@dataclass
class ThesisResult:
    """Return type from run_ticker() — wraps thesis + signals + skip metadata. D-20."""

    ticker: str
    skipped: bool = False
    skip_reason: Optional[str] = None  # "hash_match" | "daily_cap" | "no_financial_data"
    thesis: Optional[InvestmentThesis] = None
    signals: list[OpportunitySignal] = field(default_factory=list)
    version_num: Optional[int] = None
    dcf_deviation_flag: bool = False
    error: Optional[str] = None


# -- Stub functions — implemented in Plans 04-02, 04-03, 04-04 ----------------


def run_ticker(ticker: str) -> ThesisResult:
    """Generate investment thesis and opportunity signals for a single ticker.
    Implemented in Plan 04-02.
    """
    raise NotImplementedError("run_ticker() implemented in Plan 04-02")


def run_all() -> list[ThesisResult]:
    """Run run_ticker() for all active tickers in tickers.yaml.
    Implemented in Plan 04-04.
    """
    raise NotImplementedError("run_all() implemented in Plan 04-04")
