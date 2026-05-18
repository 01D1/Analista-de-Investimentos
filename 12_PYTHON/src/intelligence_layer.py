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


# ── Jinja2 helpers — D-07, D-08 ──────────────────────────────────────────────


def _get_jinja_env():
    """Return Jinja2 Environment with StrictUndefined — raises on missing variables."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined

    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
    )


def _render_thesis_prompt(data: dict) -> str:
    """Render thesis_prompt.j2 with the given data dict.
    Raises jinja2.UndefinedError if any required variable is missing.
    """
    env = _get_jinja_env()
    template = env.get_template("thesis_prompt.j2")
    return template.render(**data)


# ── Hash computation — D-09 ───────────────────────────────────────────────────


def compute_input_hash(
    fair_value_brl: Optional[float],
    upside_pct: Optional[float],
    multiples: dict,
    selic: Optional[float],
    cds: Optional[float],
    momentum_score: Optional[int],
    news_urls: list[str],
) -> str:
    """Compute stable SHA-256 hash of key financial inputs.

    Floats rounded before hashing to prevent precision-drift false mismatches (D-09).
    news_urls sorted for order-independence. Returns 64-char hex digest.
    """
    hash_dict = {
        "fair_value_brl": round(fair_value_brl, 2) if fair_value_brl is not None else None,
        "upside_pct": round(upside_pct, 4) if upside_pct is not None else None,
        "pe_ratio": round(multiples.get("pe_ratio") or 0.0, 2),
        "ev_ebitda": round(multiples.get("ev_ebitda") or 0.0, 2),
        "pb_ratio": round(multiples.get("pb_ratio") or 0.0, 2),
        "dividend_yield": round(multiples.get("dividend_yield") or 0.0, 4),
        "ev_revenue": round(multiples.get("ev_revenue") or 0.0, 2),
        "selic": round(selic, 4) if selic is not None else None,
        "cds": round(cds, 4) if cds is not None else None,
        "momentum_score": momentum_score,
        "news_urls": sorted(news_urls)[:3],
    }
    payload = json.dumps(hash_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


# ── DCF cross-check — D-03 ───────────────────────────────────────────────────


def _check_dcf_deviation(thesis: InvestmentThesis, dcf_fair_value: float) -> bool:
    """Return True if thesis.fair_value_brl deviates >10% from computed DCF value.

    The thesis is still stored — dcf_deviation_flag is set for observability.
    """
    if dcf_fair_value <= 0:
        return False
    deviation = abs(thesis.fair_value_brl - dcf_fair_value) / dcf_fair_value
    return deviation > 0.10


# ── IntelligenceClient — D-04, D-05, D-06 ────────────────────────────────────


class IntelligenceClient:
    """Wraps instructor.from_anthropic() for schema-enforced thesis generation.

    D-04: Separate from LLMClient — no shared state.
    D-05: Hard-fail on validation exhaustion → IngestionError (never partial thesis).
    D-06: ANTHROPIC_TOOLS mode — native tool-call API with validation retry loop.
    """

    def __init__(self) -> None:
        # Lazy import to avoid import-time settings read — matches llm_client.py pattern
        from config.settings import settings
        import instructor

        # instructor 1.15.1 uses from_provider (from_anthropic removed in >=1.0 refactor)
        # mode=ANTHROPIC_TOOLS passed explicitly — D-06
        self._client = instructor.from_provider(
            "anthropic/claude-sonnet-4-6",
            mode=instructor.Mode.ANTHROPIC_TOOLS,
            api_key=settings.anthropic_api_key,
        )

    def generate_thesis(
        self,
        ticker: str,
        prompt: str,
        system: str,
    ) -> InvestmentThesis:
        """Generate a validated InvestmentThesis via instructor + Claude.

        instructor feeds Pydantic validation errors back to LLM for up to max_retries=3
        attempts before raising InstructorRetryException — caught and re-raised as
        IngestionError per D-05. temperature=0.1 (not 0 — Pitfall 8).
        API key is NEVER logged.
        """
        try:
            return self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                response_model=InvestmentThesis,
                max_retries=3,
                temperature=0.1,
            )
        except Exception as exc:
            # Catches InstructorRetryException + anthropic.RateLimitError + any other API error.
            # D-05: never return partial or empty thesis.
            raise IngestionError("generate_thesis", exc) from exc


# ── Prompt data assembly — D-08 ───────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Você é um analista sênior de investimentos especializado no mercado brasileiro (B3). "
    "Gere análises fundamentalistas rigorosas em Português. "
    "Responda exclusivamente com o objeto JSON InvestmentThesis conforme o schema fornecido. "
    "Não adicione campos extras. Não calcule valores — apenas sintetize os dados fornecidos."
)


def _assemble_prompt_data(ticker: str, conn: sqlite3.Connection) -> Optional[dict]:
    """Read all 6 source tables and assemble the template data dict.

    Returns None if critical data (financial_ltm) is missing — caller skips generation.
    All SQL uses parameterized queries (T-DCF-02 anti-pattern: never f-string ticker).
    news_articles: LIKE query with f'%{ticker}%' as a PARAMETER — not in SQL string.
    """
    from src.valuation.sector_config import SectorConfig

    ltm = conn.execute(
        "SELECT * FROM financial_ltm WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if ltm is None:
        log.warning(f"[{ticker}] sem financial_ltm — skipping thesis generation")
        return None

    multiples = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    dcf = conn.execute(
        "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    if dcf is None or dcf["fair_value_brl"] is None:
        log.warning(f"[{ticker}] sem financial_dcf.fair_value_brl — skipping thesis generation (Pitfall 5)")
        return None

    signals = conn.execute(
        "SELECT * FROM financial_signals WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    # Macro: latest value per series — series_code 11=selic, 433=ipca_12m, 29039=cds
    macro_rows = conn.execute(
        """
        SELECT series_code, value FROM macro_series
        WHERE series_code IN (11, 433, 29039)
        ORDER BY date DESC
        """,
    ).fetchall()
    macro: dict[int, Optional[float]] = {}
    for r in macro_rows:
        if r["series_code"] not in macro:
            macro[r["series_code"]] = r["value"]

    # News: top 3 for ticker — LIKE pattern is a PARAMETER (A2 assumption, Pitfall: not f-string)
    news_rows = conn.execute(
        """
        SELECT title, published_at, url FROM news_articles
        WHERE ticker_tags LIKE ?
        ORDER BY published_at DESC LIMIT 3
        """,
        (f"%{ticker}%",),
    ).fetchall()

    # Sector metadata
    try:
        cfg = SectorConfig.for_ticker(ticker)
        sector = getattr(cfg, "sector", "Desconhecido")
        is_bank_model = getattr(cfg, "is_bank_model", False)
    except Exception:
        sector = "Desconhecido"
        is_bank_model = False

    # MACD trend from histogram sign
    macd_trend = None
    if signals and signals["macd_histogram"] is not None:
        macd_trend = "ALTA" if signals["macd_histogram"] > 0 else "BAIXA"

    return {
        # Ticker metadata
        "ticker": ticker,
        "sector": sector,
        "is_bank_model": is_bank_model,
        # LTM
        "net_revenue": ltm["net_revenue"],
        "ebitda": ltm["ebitda"],
        "net_income": ltm["net_income"],
        "fcf": ltm["fcf"],
        "net_debt": ltm["net_debt"],
        # Multiples
        "pe_ratio": multiples["pe_ratio"] if multiples else None,
        "ev_ebitda": multiples["ev_ebitda"] if multiples else None,
        "pb_ratio": multiples["pb_ratio"] if multiples else None,
        "dividend_yield": multiples["dividend_yield"] if multiples else None,
        # DCF — fair_value_brl guaranteed non-None here (Pitfall 5 guard above)
        "dcf_fair_value": dcf["fair_value_brl"],
        "upside_pct": dcf["upside_pct"],
        "wacc": dcf["wacc"],
        "terminal_growth": dcf["terminal_growth"],
        "confidence_flag": dcf["confidence_flag"],
        # Macro (None if missing)
        "selic": macro.get(11),
        "ipca_12m": macro.get(433),
        "cds_brasil": macro.get(29039),
        # Signals
        "rsi_14": signals["rsi_14"] if signals else None,
        "macd_trend": macd_trend,
        "momentum_score": signals["momentum_score"] if signals else None,
        # News
        "news_items": [dict(n) for n in news_rows],
    }


# ── Thesis versioning helpers — D-12, D-13 ────────────────────────────────────


def _next_version_num(ticker: str, conn: sqlite3.Connection) -> int:
    """Return MAX(version_num) + 1 for the ticker, or 1 if no prior rows."""
    row = conn.execute(
        "SELECT MAX(version_num) FROM thesis_versions WHERE ticker = ?",
        (ticker,),
    ).fetchone()
    current_max = row[0]  # None if no rows
    return (current_max or 0) + 1


def _compute_diff_summary(
    prior_json: Optional[str],
    new_thesis: InvestmentThesis,
) -> Optional[str]:
    """Compute a human-readable diff of current vs previous thesis JSON.

    Returns None for the first thesis version (no prior). D-13.
    Covers: positioning change, fair_value_brl change %, bull_case prefix change.
    """
    if prior_json is None:
        return None  # first version — no diff
    try:
        old = json.loads(prior_json)
    except (json.JSONDecodeError, TypeError):
        return "diff indisponível (prior_json inválido)"

    parts = []
    if old.get("positioning") != new_thesis.positioning:
        parts.append(f"Positioning: {old.get('positioning')}→{new_thesis.positioning}")
    old_fv = old.get("fair_value_brl", 0.0) or 0.0
    if old_fv > 0:
        pct = (new_thesis.fair_value_brl - old_fv) / old_fv * 100
        if abs(pct) > 0.5:  # ignore sub-0.5% noise
            parts.append(f"Fair value: R${old_fv:.2f}→R${new_thesis.fair_value_brl:.2f} ({pct:+.1f}%)")
    old_bull = (old.get("bull_case") or "")[:80]
    new_bull = new_thesis.bull_case[:80]
    if old_bull != new_bull:
        parts.append("Bull case alterado")
    return "; ".join(parts) if parts else "Sem alteracoes materiais"


def _maybe_send_thesis_alert(
    ticker: str,
    new_positioning: str,
    prev_positioning: Optional[str],
    confidence: str,
    summary_one_line: str,
    conn: sqlite3.Connection,
) -> None:
    """Dispara alerta Telegram quando posicionamento muda. D-13.

    Nunca levanta excecao — falha no alerta nao bloqueia armazenamento de tese.
    Pattern G (PATTERNS.md): alert never raises.
    """
    if prev_positioning is None or new_positioning == prev_positioning:
        return
    opp_row = conn.execute(
        "SELECT description FROM opportunity_signals WHERE ticker = ? "
        "ORDER BY conviction_score DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    top_opp_desc = opp_row["description"] if opp_row else "-"
    try:
        from src.delivery.telegram_bot import get_bot

        get_bot().send_thesis_alert(
            ticker=ticker,
            old_positioning=prev_positioning,
            new_positioning=new_positioning,
            confidence=confidence,
            rationale_one_line=summary_one_line,
            top_opportunity_desc=top_opp_desc,
        )
    except Exception as exc:
        log.warning(f"[{ticker}] Telegram alert failed: {exc}")
        # Nunca re-raise — falha no alerta nao bloqueia armazenamento de tese


# ── Opportunity signal computation — D-15, D-16, D-17, D-18 ──────────────────


def _score_dcf_divergence(price: float, fair_value: float) -> int:
    """Compute DCF_DIVERGENCE conviction score (0–40).

    Returns 0 if divergence is <= 20% (below emission threshold).
    Proportional scale: 20% divergence = 0pts; 100%+ divergence = 40pts (capped).
    D-17.
    """
    if fair_value <= 0 or price <= 0:
        return 0
    divergence = abs(fair_value - price) / price
    if divergence <= 0.20:
        return 0
    score = int(min((divergence - 0.20) / 0.80 * 40, 40))
    return score


def _score_momentum_crossover(
    golden_cross: Optional[int],
    death_cross: Optional[int],
    momentum_score: Optional[int],
) -> int:
    """Compute MOMENTUM_CROSSOVER conviction score (0–60).

    Returns 0 if no qualifying crossover. D-17.
    golden_cross=1 AND momentum_score>=60 → bullish signal (up to 60pts)
    death_cross=1 AND momentum_score<=40 → bearish signal (up to 60pts)
    Score scales linearly with momentum_score strength.
    """
    if momentum_score is None:
        return 0
    if golden_cross == 1 and momentum_score >= 60:
        return int(min(momentum_score / 100 * 60, 60))
    if death_cross == 1 and momentum_score <= 40:
        return int(min((100 - momentum_score) / 100 * 60, 60))
    return 0


def _score_ipe_event(ticker: str, conn: sqlite3.Connection) -> int:
    """Return 30 (binary) if IPE event in last 30 days, else 0. D-17.

    CRITICAL: No normalized_name IS NOT NULL filter — IPE rows have NULL normalized_name
    (Pitfall 7). Query uses period_type = 'IPE' only.
    """
    row = conn.execute(
        """
        SELECT COUNT(*) FROM cvm_statements
        WHERE ticker = ? AND period_type = 'IPE'
          AND reference_date >= DATE('now', '-30 days')
        """,
        (ticker,),
    ).fetchone()
    return 30 if (row[0] or 0) > 0 else 0


def compute_opportunity_signals(
    ticker: str,
    conn: sqlite3.Connection,
) -> list[OpportunitySignal]:
    """Compute all opportunity signals for a ticker and return top-3 by conviction_score.

    Signal types: DCF_DIVERGENCE, MOMENTUM_CROSSOVER, IPE_EVENT.
    Only signals with conviction_score >= 40 are included.
    Result is sorted by conviction_score DESC, top-3 returned.
    D-15, D-17.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    signals: list[OpportunitySignal] = []

    # Fetch latest multiples for price and fair_value
    mult_row = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    dcf_row = conn.execute(
        "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    sig_row = conn.execute(
        "SELECT * FROM financial_signals WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    # ── DCF_DIVERGENCE ──────────────────────────────────────────────────────
    if mult_row and dcf_row and mult_row["price"] and dcf_row["fair_value_brl"]:
        price = float(mult_row["price"])
        fair_value = float(dcf_row["fair_value_brl"])
        score = _score_dcf_divergence(price, fair_value)
        if score > 0:
            direction = "subvalorizado" if fair_value > price else "sobrevalorizado"
            divergence_pct = abs(fair_value - price) / price * 100
            signals.append(OpportunitySignal(
                ticker=ticker,
                signal_type="DCF_DIVERGENCE",
                description=(
                    f"{ticker} {direction}: preço R${price:.2f} vs preço justo R${fair_value:.2f} "
                    f"({divergence_pct:.1f}% de divergência)"
                ),
                conviction_score=score,
                generated_at=generated_at,
            ))

    # ── MOMENTUM_CROSSOVER ─────────────────────────────────────────────────
    if sig_row:
        golden = sig_row["golden_cross"]
        death = sig_row["death_cross"]
        momentum = sig_row["momentum_score"]
        score = _score_momentum_crossover(golden, death, momentum)
        if score > 0:
            cross_type = "golden cross (alta)" if golden == 1 else "death cross (baixa)"
            signals.append(OpportunitySignal(
                ticker=ticker,
                signal_type="MOMENTUM_CROSSOVER",
                description=(
                    f"{ticker}: {cross_type} com momentum score {momentum}/100 — "
                    f"sinal técnico de {'compra' if golden == 1 else 'venda'}"
                ),
                conviction_score=score,
                generated_at=generated_at,
            ))

    # ── IPE_EVENT ──────────────────────────────────────────────────────────
    score = _score_ipe_event(ticker, conn)
    if score > 0:
        signals.append(OpportunitySignal(
            ticker=ticker,
            signal_type="IPE_EVENT",
            description=(
                f"{ticker}: evento corporativo relevante (IPE) publicado na CVM nos últimos 30 dias"
            ),
            conviction_score=score,
            generated_at=generated_at,
        ))

    # Sort by conviction_score DESC, return top-3 (D-17: filter >= 40 already applied above)
    signals.sort(key=lambda s: s.conviction_score, reverse=True)
    return signals[:3]


def _write_opportunity_signals(
    ticker: str,
    signals: list[OpportunitySignal],
    conn: sqlite3.Connection,
) -> None:
    """Write top signals to opportunity_signals table via INSERT OR REPLACE.

    Keyed by (ticker, computed_date, signal_type) UNIQUE constraint — safe to call
    multiple times for the same day. D-18.
    All SQL parameterized — ticker never in SQL string.
    """
    computed_date = date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).isoformat()
    for sig in signals:
        conn.execute(
            """
            INSERT OR REPLACE INTO opportunity_signals
            (id, ticker, computed_date, signal_type, description, conviction_score, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                ticker,
                computed_date,
                sig.signal_type,
                sig.description,
                sig.conviction_score,
                ingested_at,
            ),
        )


# ── Gate checks — D-10, D-11 ─────────────────────────────────────────────────


def _is_hash_match(ticker: str, input_hash: str, conn: sqlite3.Connection) -> bool:
    """Return True if thesis_versions already has a row with this exact input_hash for ticker."""
    row = conn.execute(
        "SELECT 1 FROM thesis_versions WHERE ticker = ? AND input_hash = ? LIMIT 1",
        (ticker, input_hash),
    ).fetchone()
    return row is not None


def _is_daily_cap_reached(ticker: str, conn: sqlite3.Connection) -> bool:
    """Return True if >= 2 thesis rows for this ticker were generated today. D-11."""
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM thesis_versions WHERE ticker = ? AND DATE(generated_at) = ?",
        (ticker, today),
    ).fetchone()
    return (row[0] or 0) >= 2


def run_ticker(ticker: str) -> ThesisResult:
    """Generate investment thesis and store versioned result for a single ticker.

    Flow:
      1. Assemble prompt data from 6 DB tables (_assemble_prompt_data)
      2. Compute input hash from key financial inputs (compute_input_hash)
      3. Check hash gate — skip if same hash already stored (D-10)
      4. Check daily cap — skip if >= 2 theses today (D-11)
      5. Render Jinja2 prompt + call IntelligenceClient.generate_thesis()
      6. Cross-check fair_value_brl vs DCF (D-03) — set dcf_deviation_flag
      7. Compute version_num + diff_summary
      8. INSERT OR REPLACE into thesis_versions

    Signals are computed separately in Plan 04-03 (compute_opportunity_signals).
    All SQL parameterized — never f-string with ticker.
    """
    conn = get_connection()
    try:
        # ── 1. Assemble prompt data ──────────────────────────────────────────
        data = _assemble_prompt_data(ticker, conn)
        if data is None:
            log.info(f"[{ticker}] sem dados financeiros — thesis skipped")
            return ThesisResult(
                ticker=ticker, skipped=True, skip_reason="no_financial_data"
            )

        # ── 2. Compute input hash ────────────────────────────────────────────
        multiples_dict = {
            "pe_ratio": data.get("pe_ratio"),
            "ev_ebitda": data.get("ev_ebitda"),
            "pb_ratio": data.get("pb_ratio"),
            "dividend_yield": data.get("dividend_yield"),
            "ev_revenue": None,  # not in _assemble_prompt_data — will default to 0.0 in compute_input_hash
        }
        news_urls = [n.get("url", "") for n in data.get("news_items", [])]
        current_hash = compute_input_hash(
            fair_value_brl=data.get("dcf_fair_value"),
            upside_pct=data.get("upside_pct"),
            multiples=multiples_dict,
            selic=data.get("selic"),
            cds=data.get("cds_brasil"),
            momentum_score=data.get("momentum_score"),
            news_urls=news_urls,
        )

        # ── 3. Hash gate (D-10) ──────────────────────────────────────────────
        if _is_hash_match(ticker, current_hash, conn):
            log.info(f"[{ticker}] hash idêntico — thesis generation skipped (D-10)")
            return ThesisResult(
                ticker=ticker, skipped=True, skip_reason="hash_match"
            )

        # ── 4. Daily cap (D-11) ──────────────────────────────────────────────
        if _is_daily_cap_reached(ticker, conn):
            log.info(f"[{ticker}] cap diário atingido — thesis generation skipped (D-11)")
            return ThesisResult(
                ticker=ticker, skipped=True, skip_reason="daily_cap"
            )

        # ── 5. Render prompt + generate thesis ───────────────────────────────
        prompt = _render_thesis_prompt(data)
        client = IntelligenceClient()
        thesis = client.generate_thesis(ticker, prompt, _SYSTEM_PROMPT)

        # ── 6. DCF cross-check (D-03) ────────────────────────────────────────
        dcf_fair_value = data["dcf_fair_value"]
        deviation_flag = _check_dcf_deviation(thesis, dcf_fair_value)
        if deviation_flag:
            log.warning(
                f"[{ticker}] DCF deviation >10%%: thesis.fair_value_brl={thesis.fair_value_brl:.2f} "
                f"vs dcf={dcf_fair_value:.2f} — storing with dcf_deviation_flag=1"
            )

        # ── 7. Version number + diff_summary (D-13) ──────────────────────────
        version_num = _next_version_num(ticker, conn)
        prior_row = conn.execute(
            "SELECT thesis_json FROM thesis_versions "
            "WHERE ticker = ? ORDER BY version_num DESC LIMIT 1",
            (ticker,),
        ).fetchone()
        prior_json = prior_row["thesis_json"] if prior_row else None
        diff_summary = _compute_diff_summary(prior_json, thesis)

        # ── 8. Persist to thesis_versions (D-12, INSERT OR REPLACE) ──────────
        generated_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO thesis_versions
            (id, ticker, version_num, generated_at, input_hash, positioning, confidence,
             fair_value_brl, dcf_deviation_flag, thesis_json, diff_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                ticker,
                version_num,
                generated_at,
                current_hash,
                thesis.positioning,
                thesis.confidence,
                thesis.fair_value_brl,
                1 if deviation_flag else 0,
                thesis.model_dump_json(),
                diff_summary,
            ),
        )
        conn.commit()
        log.info(
            f"[{ticker}] thesis v{version_num} gravada - "
            f"positioning={thesis.positioning} fair_value={thesis.fair_value_brl:.2f} "
            f"deviation_flag={deviation_flag}"
        )

        # ── 8b. Positioning-change Telegram alert (D-13) ─────────────────────
        prev_positioning: Optional[str] = None
        if prior_json:
            try:
                prev_positioning = json.loads(prior_json).get("positioning")
            except (json.JSONDecodeError, TypeError):
                pass
        _maybe_send_thesis_alert(
            ticker=ticker,
            new_positioning=thesis.positioning,
            prev_positioning=prev_positioning,
            confidence=thesis.confidence,
            summary_one_line=thesis.summary_one_line,
            conn=conn,
        )

        # ── 9. Compute and persist opportunity signals (D-15) ────────────────
        signals = compute_opportunity_signals(ticker, conn)
        if signals:
            _write_opportunity_signals(ticker, signals, conn)
            conn.commit()
            log.info(f"[{ticker}] {len(signals)} sinais de oportunidade gravados")

        return ThesisResult(
            ticker=ticker,
            skipped=False,
            thesis=thesis,
            signals=signals,
            version_num=version_num,
            dcf_deviation_flag=deviation_flag,
        )

    except IngestionError:
        # D-05: re-raise — caller (run_all) logs and continues to next ticker
        raise
    except Exception as exc:
        log.warning(f"[{ticker}] run_ticker falhou: {exc}")
        return ThesisResult(ticker=ticker, error=str(exc))
    finally:
        conn.close()


def run_all() -> list[ThesisResult]:
    """Generate investment theses and opportunity signals for all active tickers.

    Loads tickers from config/tickers.yaml (active=True only).
    Calls run_ticker() per ticker; catches IngestionError and appends error result
    so one failure does not abort the entire run.
    Mirrors financial_engine.run_all() pattern (D-20).
    """
    import yaml
    from pathlib import Path

    tickers_path = Path(__file__).parent.parent / "config" / "tickers.yaml"
    try:
        with open(tickers_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        active_tickers = [
            t["ticker"]
            for t in data.get("tickers", [])
            if t.get("active", True)
        ]
    except Exception as exc:
        log.error(f"[run_all] falha ao carregar tickers.yaml: {exc}")
        return []

    results: list[ThesisResult] = []
    for ticker in active_tickers:
        try:
            result = run_ticker(ticker)
            results.append(result)
        except IngestionError as exc:
            # D-05: IngestionError = hard fail on LLM validation; log and continue
            log.warning(f"[{ticker}] IngestionError em run_ticker: {exc}")
            results.append(ThesisResult(ticker=ticker, error=str(exc)))
        except Exception as exc:
            log.warning(f"[{ticker}] excecao nao capturada em run_ticker: {exc}")
            results.append(ThesisResult(ticker=ticker, error=str(exc)))

    ok = sum(1 for r in results if not r.skipped and r.thesis is not None)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if r.error is not None)
    log.info(
        f"[run_all] concluido — ok={ok} skipped={skipped} failed={failed} total={len(results)}"
    )
    return results
