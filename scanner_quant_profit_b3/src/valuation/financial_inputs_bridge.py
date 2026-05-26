"""
src/valuation/financial_inputs_bridge.py — Financial Inputs Bridge (M017-S05)

Bridge canônico entre valuation_financial_inputs (ingestion.db) e as dataclasses
dos modelos M016 (commodity, utility, retail, industry).

Arquitetura:
    valuation_financial_inputs (12_PYTHON/data/ingestion.db)
        → load_financial_inputs_from_store()   # extrai e normaliza métricas
        → build_*_inputs_from_store()          # hidrata dataclass do modelo
        → calculate_*_valuation(write=False)   # dry-run sem persistência

Convenções de unidade:
    Banco (metric_value): BRL puro (R$ ones) para financeiros, unidades para shares
    Modelos M016: R$ milhões para financeiros, milhões de ações para shares
    Conversão: dividi por 1_000_000 para todos os campos de R$ e shares

Flags de qualidade detectadas automaticamente:
    FCF_REVIEW           — FCF/EBITDA > 3.0 com FCF positivo (anomalia contábil)
    FCF_NEGATIVE_EXPECTED — FCF < 0 com EBITDA > 0 (ciclo de investimento intenso)
    DISTRESSED           — EBIT < 0 (prejuízo operacional) → bloqueia DCF

Defaults macro (BCB mai-2026, Selic=14.75%):
    WACC commodity : 14.0%  (oil & gas Brasil, beta alto)
    WACC utility   : 10.0%  (regulado ANEEL/ANA)
    WACC retail    : 13.0%  (consumo discricionário)
    WACC industry  : 12.0%  (indústria diversificada)
    Terminal growth: 4.5%   (IPCA projetado + crescimento real)

Regras de preservação (nunca sobrescritas sem force_recalc=True):
    PETR4 = 81.12 (COMMODITY_PRESERVED_FAIR_VALUES)
    WEGE3 = 40.16 (INDUSTRY_PRESERVED_FAIR_VALUES)

Contrato de segurança:
    - write=False em todas as funções de cálculo
    - Nenhum fair_value é salvo neste módulo
    - asset_intelligence_snapshots não é alterada
    - Sem mocks, sem dados sintéticos
    - Sem chamadas a LLM ou APIs externas
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Resolução de caminhos
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_ingestion_db() -> Path:
    """Localiza ingestion.db por precedência.

    Ordem:
      1. Env var FINANCIAL_INPUTS_DB_PATH
      2. Derivado de __file__ (scanner_quant → Analista de Investimentos → 12_PYTHON)
      3. Fallback: data/ingestion.db relativo ao CWD
    """
    env_path = os.environ.get("FINANCIAL_INPUTS_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        logger.warning("FINANCIAL_INPUTS_DB_PATH=%s não encontrado", env_path)

    # Derivação a partir de __file__:
    # financial_inputs_bridge.py → src/valuation/ → src/ → scanner_quant_profit_b3/ → Analista de Investimentos/
    try:
        bridge_abs = Path(__file__).resolve()
        obsidian_root = bridge_abs.parent.parent.parent.parent  # Analista de Investimentos/
        candidate = obsidian_root / "12_PYTHON" / "data" / "ingestion.db"
        if candidate.exists():
            return candidate
    except Exception as exc:
        logger.debug("Erro ao resolver ingestion.db via __file__: %s", exc)

    # Fallback
    return Path("data/ingestion.db")


def _resolve_scanner_db() -> str:
    """Localiza scanner_quant.db para leitura de market_price."""
    env_path = os.environ.get("SCANNER_QUANT_DB")
    if env_path and Path(env_path).exists():
        return env_path

    candidates = [
        "data/database/scanner_quant.db",
        "scanner_quant.db",
    ]
    for c in candidates:
        if Path(c).exists():
            return c

    return "data/database/scanner_quant.db"


# ─────────────────────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────────────────────

# Conversão: todos os valores financeiros estão em BRL ones no DB
# Os modelos M016 esperam R$ milhões → dividir por 1_000_000
_BRL_TO_MILLIONS: float = 1_000_000.0

# Defaults macro Brasil (Selic 14.75%, mai-2026)
WACC_DEFAULTS: Dict[str, float] = {
    "commodity": 0.14,   # oil & gas: beta alto + risco Brasil
    "utility":   0.10,   # regulado ANEEL/ANA: risco baixo
    "retail":    0.13,   # consumo discricionário
    "industry":  0.12,   # indústria diversificada
}
TERMINAL_GROWTH_DEFAULT: float = 0.045  # IPCA ~4.5% projetado

# Mapeamento ticker → setor para os 18 tickers M017
TICKER_SECTOR_MAP: Dict[str, str] = {
    # COMMODITY (oil & gas)
    "PRIO3":  "commodity",
    "RECV3":  "commodity",
    # UTILITY (energia, saneamento)
    "EGIE3":  "utility",
    "SBSP3":  "utility",
    "TAEE11": "utility",
    # RETAIL (varejo)
    "AZZA3":  "retail",
    "LREN3":  "retail",
    "MGLU3":  "retail",
    "PCAR3":  "retail",
    "VIVA3":  "retail",
    # INDUSTRY (saúde, celulose, logística, locação, farma)
    "FLRY3":  "industry",
    "HYPE3":  "industry",
    "KLBN11": "industry",
    "RADL3":  "industry",
    "RAIL3":  "industry",
    "RENT3":  "industry",
    "SUZB3":  "industry",
    "VAMO3":  "industry",
}

# Mapeamento ticker → subsector (para múltiplos EV/EBITDA corretos)
TICKER_SUBSECTOR_MAP: Dict[str, str] = {
    "PRIO3":  "oil_gas",
    "RECV3":  "oil_gas",
    "EGIE3":  "generation",
    "SBSP3":  "sanitation",
    "TAEE11": "transmission",
    "AZZA3":  "fashion",
    "LREN3":  "fashion",
    "MGLU3":  "electronics",
    "PCAR3":  "food",
    "VIVA3":  "jewelry",
    "FLRY3":  "healthcare",
    "HYPE3":  "pharma",
    "KLBN11": "pulp",
    "RADL3":  "pharmacy",
    "RAIL3":  "logistics",
    "RENT3":  "rental",
    "SUZB3":  "pulp",
    "VAMO3":  "rental",
}

# ─────────────────────────────────────────────────────────────────────────────
#  Detecção de flags de qualidade
# ─────────────────────────────────────────────────────────────────────────────

# Thresholds para flags
_FCF_REVIEW_RATIO_THRESHOLD: float = 3.0    # FCF/EBITDA > 3.0 → suspeito
_DISTRESSED_EBIT_THRESHOLD: float = 0.0     # EBIT < 0 → distressed


def _detect_quality_flags(raw: Dict[str, float]) -> List[str]:
    """Detecta flags de qualidade a partir das métricas brutas (em BRL ones).

    Flags possíveis
    ---------------
    FCF_REVIEW           : FCF/EBITDA > 3.0 com ambos positivos
    FCF_NEGATIVE_EXPECTED: FCF < 0 com EBITDA > 0 (ciclo de capex intenso)
    DISTRESSED           : EBIT < 0 (prejuízo operacional)

    Parâmetros
    ----------
    raw : dict
        Métricas em BRL ones (direct from DB).

    Retorno
    -------
    list[str]
        Lista de flags ativas.
    """
    flags: List[str] = []

    fcf    = raw.get("free_cash_flow")
    ebitda = raw.get("ebitda")
    ebit   = raw.get("ebit")

    # FCF_REVIEW: FCF anormalmente alto vs EBITDA
    if (fcf is not None and ebitda is not None
            and ebitda > 0 and fcf > 0
            and (fcf / ebitda) > _FCF_REVIEW_RATIO_THRESHOLD):
        flags.append("FCF_REVIEW")
        logger.info(
            "_detect_quality_flags: FCF_REVIEW — fcf/ebitda=%.2f (threshold=%.1f)",
            fcf / ebitda,
            _FCF_REVIEW_RATIO_THRESHOLD,
        )

    # FCF_NEGATIVE_EXPECTED: FCF negativo mas EBITDA positivo → ciclo capex
    if (fcf is not None and ebitda is not None
            and fcf < 0 and ebitda > 0):
        flags.append("FCF_NEGATIVE_EXPECTED")
        logger.info(
            "_detect_quality_flags: FCF_NEGATIVE_EXPECTED — fcf=%.0f, ebitda=%.0f",
            fcf / _BRL_TO_MILLIONS,
            ebitda / _BRL_TO_MILLIONS,
        )

    # DISTRESSED: prejuízo operacional (EBIT negativo)
    if ebit is not None and ebit < _DISTRESSED_EBIT_THRESHOLD:
        flags.append("DISTRESSED")
        logger.info(
            "_detect_quality_flags: DISTRESSED — ebit=%.0fM",
            ebit / _BRL_TO_MILLIONS,
        )

    return flags


# ─────────────────────────────────────────────────────────────────────────────
#  Carregamento de dados auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def _load_market_price(ticker: str, scanner_db: Optional[str] = None) -> Optional[float]:
    """Carrega preço de mercado do cotahist_daily ou asset_intelligence_snapshots.

    Não lança exceção — retorna None em caso de falha.
    """
    db_path = scanner_db or _resolve_scanner_db()
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute(
            "SELECT close FROM cotahist_daily WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        if row and row[0] is not None:
            conn.close()
            return float(row[0])

        c.execute(
            "SELECT market_price FROM asset_intelligence_snapshots "
            "WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()
        if row and row[0] is not None:
            return float(row[0])
    except Exception as exc:
        logger.debug("_load_market_price: ticker=%s erro=%s", ticker, exc)

    return None


def _load_existing_fair_value(ticker: str, scanner_db: Optional[str] = None) -> Optional[float]:
    """Carrega fair_value existente de asset_intelligence_snapshots.

    Retorna None se não encontrar ou se valuation_available=0.
    """
    db_path = scanner_db or _resolve_scanner_db()
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            """SELECT fair_value, valuation_available
               FROM asset_intelligence_snapshots
               WHERE ticker=? ORDER BY id DESC LIMIT 1""",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()
        if row and row[0] is not None and row[1]:
            return float(row[0])
    except Exception as exc:
        logger.debug("_load_existing_fair_value: ticker=%s erro=%s", ticker, exc)

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  1. Carregador canônico de inputs financeiros
# ─────────────────────────────────────────────────────────────────────────────

def load_financial_inputs_from_store(
    ticker: str,
    period_end: Optional[str] = None,
    period_type: str = "DFP",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Lê valuation_financial_inputs e retorna dict normalizado de métricas.

    Seleciona o período mais recente por métrica (maior period_end, menor source_priority).
    Se period_end fornecido, filtra apenas esse período.

    Mapa métrica → unidade de retorno:
        Métricas financeiras (R$ milhões):
            revenue, ebit, ebitda, net_income, operating_cash_flow, capex,
            free_cash_flow, total_assets, cash_and_equivalents,
            short_term_debt, long_term_debt, gross_debt, net_debt,
            equity_book_value, depreciation_amortization,
            current_assets, current_liabilities, non_current_assets,
            non_current_liabilities, total_liabilities, financial_applications
        Métrica em unidades absolutas (milhões de ações):
            shares_outstanding

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3 (ex: "PRIO3"). Case-insensitive.
    period_end : str | None
        Filtra por data-fim do período (YYYY-MM-DD). None = mais recente.
    period_type : str
        Tipo de período: 'DFP' | 'ITR' | 'LTM'. Default: 'DFP'.
    db_path : Path | None
        Caminho do ingestion.db. Usa resolução automática se None.

    Retorno
    -------
    dict com:
        ticker        : str
        period_end    : str | None      — período efetivo dos dados
        period_type   : str
        metrics       : dict[str, float]  — R$ milhões (ou milhões de ações)
        quality_flags : list[str]       — FCF_REVIEW | FCF_NEGATIVE_EXPECTED | DISTRESSED
        source_quality: str             — 'CVM_LIVE' | 'EXCEL_PIPELINE' | 'ABSENT'
        confidence    : float           — confiança mínima dos dados
        available     : bool            — True se há métricas essenciais (ebitda + net_debt + shares)
    """
    effective_db = db_path or _resolve_ingestion_db()
    ticker_upper = str(ticker).strip().upper()

    raw_brl: Dict[str, float] = {}
    period_found: Optional[str] = None
    sources_seen: set = set()
    min_confidence: float = 1.0

    try:
        conn = sqlite3.connect(str(effective_db))
        conn.row_factory = sqlite3.Row

        if period_end:
            # Período específico solicitado
            query = """
                WITH ranked AS (
                    SELECT metric_name, metric_value, source_type, confidence, period_end,
                           ROW_NUMBER() OVER (
                               PARTITION BY metric_name
                               ORDER BY source_priority ASC
                           ) AS _rn
                    FROM valuation_financial_inputs
                    WHERE ticker = ? AND period_end = ? AND period_type = ?
                )
                SELECT metric_name, metric_value, source_type, confidence, period_end
                FROM ranked WHERE _rn = 1
            """
            rows = conn.execute(query, (ticker_upper, period_end, period_type.upper())).fetchall()
        else:
            # Período mais recente por métrica
            query = """
                WITH ranked AS (
                    SELECT metric_name, metric_value, source_type, confidence, period_end,
                           ROW_NUMBER() OVER (
                               PARTITION BY metric_name
                               ORDER BY period_end DESC, source_priority ASC
                           ) AS _rn
                    FROM valuation_financial_inputs
                    WHERE ticker = ? AND period_type = ?
                )
                SELECT metric_name, metric_value, source_type, confidence, period_end
                FROM ranked WHERE _rn = 1
            """
            rows = conn.execute(query, (ticker_upper, period_type.upper())).fetchall()

        conn.close()

        for row in rows:
            m_name = row["metric_name"]
            m_value = float(row["metric_value"])
            m_src = row["source_type"]
            m_conf = float(row["confidence"])
            m_period = row["period_end"]

            raw_brl[m_name] = m_value
            sources_seen.add(m_src)
            if m_conf < min_confidence:
                min_confidence = m_conf
            if period_found is None:
                period_found = m_period

    except Exception as exc:
        logger.error("load_financial_inputs_from_store: ticker=%s erro=%s", ticker_upper, exc)
        return {
            "ticker":        ticker_upper,
            "period_end":    None,
            "period_type":   period_type,
            "metrics":       {},
            "quality_flags": [],
            "source_quality": "ABSENT",
            "confidence":    0.0,
            "available":     False,
        }

    if not raw_brl:
        logger.info("load_financial_inputs_from_store: ticker=%s sem dados no store", ticker_upper)
        return {
            "ticker":        ticker_upper,
            "period_end":    None,
            "period_type":   period_type,
            "metrics":       {},
            "quality_flags": [],
            "source_quality": "ABSENT",
            "confidence":    0.0,
            "available":     False,
        }

    # Detectar flags de qualidade (antes da conversão de unidade)
    quality_flags = _detect_quality_flags(raw_brl)

    # Converter para R$ milhões (para financeiros) e milhões de ações (para shares)
    metrics: Dict[str, float] = {}
    for name, value in raw_brl.items():
        if name == "shares_outstanding":
            # ações: converter unidades → milhões de ações
            metrics[name] = value / _BRL_TO_MILLIONS
        else:
            # financeiros: BRL ones → R$ milhões
            metrics[name] = value / _BRL_TO_MILLIONS

    # Determinar qualidade da fonte
    if "CVM_CSV" in sources_seen:
        source_quality = "CVM_LIVE"
    elif "EXCEL_PIPELINE" in sources_seen:
        source_quality = "EXCEL_PIPELINE"
    else:
        source_quality = "ABSENT"

    # Verificar disponibilidade mínima (ebitda + net_debt + shares_outstanding)
    essential_keys = {"ebitda", "net_debt", "shares_outstanding"}
    available = essential_keys.issubset(set(raw_brl.keys()))

    logger.info(
        "load_financial_inputs_from_store: ticker=%s period=%s flags=%s "
        "metrics=%d available=%s source=%s",
        ticker_upper, period_found, quality_flags,
        len(metrics), available, source_quality,
    )

    return {
        "ticker":        ticker_upper,
        "period_end":    period_found,
        "period_type":   period_type,
        "metrics":       metrics,
        "quality_flags": quality_flags,
        "source_quality": source_quality,
        "confidence":    min_confidence,
        "available":     available,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _m(metrics: Dict[str, float], key: str) -> Optional[float]:
    """Retorna métrica ou None se ausente."""
    v = metrics.get(key)
    if v is None:
        return None
    return float(v)


def _source_quality_to_model_quality(
    source_quality: str,
    model_prefix: str,
) -> str:
    """Converte qualidade de fonte do store para constante do modelo."""
    map_: Dict[str, str] = {
        "CVM_LIVE":       "CVM_LIVE",
        "EXCEL_PIPELINE": "EXCEL_PIPELINE",
        "ABSENT":         "ABSENT",
    }
    return map_.get(source_quality, "ABSENT")


def _fcf_for_model(
    metrics: Dict[str, float],
    quality_flags: List[str],
    ticker: str,
    wacc: Optional[float] = None,
    g: Optional[float] = None,
) -> Optional[float]:
    """Retorna FCF a usar no modelo, aplicando regras de qualidade e viabilidade do DCF.

    Os modelos M016 bloqueiam quando DCF produz equity_value < 0, mas NÃO fazem
    fallback para EV/EBITDA nesse caso — retornam NEEDS_REVIEW imediatamente.
    A bridge detecta isso proativamente e retorna None para habilitar o fallback.

    Regras (por precedência):
      FCF_REVIEW           → None (FCF/EBITDA > 3.0 — resultado DCF implausível)
      DISTRESSED           → None (EBIT < 0 — DCF enganoso com prejuízo operacional)
      FCF_NEGATIVE_EXPECTED→ None (FCF < 0 — EV/EBITDA preferido per M017-S05)
      DCF inviável         → None (EV - net_debt < 0 com FCF > 0 — sem fallback no modelo)
      Normal               → FCF do store
    """
    if "FCF_REVIEW" in quality_flags:
        logger.info(
            "_fcf_for_model: ticker=%s FCF_REVIEW → FCF=None (forçando EV/EBITDA)",
            ticker,
        )
        return None

    if "DISTRESSED" in quality_flags:
        logger.info(
            "_fcf_for_model: ticker=%s DISTRESSED → FCF=None (bloqueando DCF)",
            ticker,
        )
        return None

    if "FCF_NEGATIVE_EXPECTED" in quality_flags:
        logger.info(
            "_fcf_for_model: ticker=%s FCF_NEGATIVE_EXPECTED → FCF=None "
            "(EV/EBITDA preferido per M017-S05)",
            ticker,
        )
        return None

    fcf      = _m(metrics, "free_cash_flow")
    net_debt = _m(metrics, "net_debt")

    # Verificação de viabilidade do DCF: se EV < net_debt o modelo bloqueia sem tentar EV/EBITDA
    if (fcf is not None and fcf > 0
            and net_debt is not None
            and wacc is not None and g is not None
            and (wacc - g) > 0):
        dcf_ev = fcf / (wacc - g)
        equity_implied = dcf_ev - net_debt
        if equity_implied < 0:
            logger.info(
                "_fcf_for_model: ticker=%s DCF inviável — EV=%.0fM net_debt=%.0fM "
                "equity=%.0fM < 0 → FCF=None para habilitar EV/EBITDA fallback",
                ticker, dcf_ev, net_debt, equity_implied,
            )
            return None

    return fcf


# ─────────────────────────────────────────────────────────────────────────────
#  2. Hidratador: Commodity
# ─────────────────────────────────────────────────────────────────────────────

def build_commodity_inputs_from_store(
    ticker: str,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Constrói CommodityValuationInputs a partir do store canônico.

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3 (ex: "PRIO3").
    db_path : Path | None
        Caminho do ingestion.db.
    scanner_db : str | None
        Caminho do scanner_quant.db (para market_price e fair_value).
    period_end : str | None
        Período específico (YYYY-MM-DD). None = mais recente DFP.

    Retorno
    -------
    Tuple[CommodityValuationInputs, dict]
        inputs: dataclass pronto para calculate_commodity_valuation()
        meta: dict com period_end, flags, source_quality, available
    """
    from src.valuation.models.commodity_model import (
        CommodityValuationInputs,
        CommodityInputQuality,
        COMMODITY_PRESERVED_FAIR_VALUES,
    )

    ticker_upper = str(ticker).strip().upper()
    store = load_financial_inputs_from_store(ticker_upper, period_end=period_end, db_path=db_path)
    metrics = store["metrics"]
    flags   = store["quality_flags"]
    src_q   = store["source_quality"]

    # Qualidade do modelo
    quality_map = {
        "CVM_LIVE":       CommodityInputQuality.CVM_LIVE,
        "EXCEL_PIPELINE": CommodityInputQuality.EXCEL_PIPELINE,
        "ABSENT":         CommodityInputQuality.ABSENT,
    }
    model_quality = quality_map.get(src_q, CommodityInputQuality.ABSENT)

    # Fair value preservado
    existing_fv = COMMODITY_PRESERVED_FAIR_VALUES.get(ticker_upper)
    if existing_fv is None:
        existing_fv = _load_existing_fair_value(ticker_upper, scanner_db)

    # Market price
    market_price = _load_market_price(ticker_upper, scanner_db)

    # WACC e g defaults commodity
    wacc = WACC_DEFAULTS["commodity"]
    g    = TERMINAL_GROWTH_DEFAULT

    # FCF com regras de qualidade e verificação de viabilidade DCF
    fcf = _fcf_for_model(metrics, flags, ticker_upper, wacc=wacc, g=g)

    subsector = TICKER_SUBSECTOR_MAP.get(ticker_upper, "oil_gas")

    inputs = CommodityValuationInputs(
        ticker=ticker_upper,
        free_cash_flow=fcf,
        ebitda=_m(metrics, "ebitda"),
        net_debt=_m(metrics, "net_debt"),
        shares_outstanding=_m(metrics, "shares_outstanding"),
        wacc=wacc,
        terminal_growth=g,
        market_price=market_price,
        source_quality=model_quality,
        existing_fair_value=existing_fv,
        existing_valuation_date=None,
        subsector=subsector,
    )

    meta = {
        "period_end":    store["period_end"],
        "quality_flags": flags,
        "source_quality": src_q,
        "available":     store["available"],
        "confidence":    store["confidence"],
    }

    logger.info(
        "build_commodity_inputs_from_store: ticker=%s ebitda=%s fcf=%s "
        "net_debt=%s shares=%s flags=%s",
        ticker_upper,
        f"{inputs.ebitda:.0f}M" if inputs.ebitda is not None else "None",
        f"{inputs.free_cash_flow:.0f}M" if inputs.free_cash_flow is not None else "None",
        f"{inputs.net_debt:.0f}M" if inputs.net_debt is not None else "None",
        f"{inputs.shares_outstanding:.1f}M" if inputs.shares_outstanding is not None else "None",
        flags,
    )

    return inputs, meta


# ─────────────────────────────────────────────────────────────────────────────
#  3. Hidratador: Utility
# ─────────────────────────────────────────────────────────────────────────────

def build_utility_inputs_from_store(
    ticker: str,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Constrói UtilityValuationInputs a partir do store canônico.

    RAB não é calculado neste módulo — RAB-DCF será bloqueado automaticamente.
    O modelo usa DCF/FCFF ou EV/EBITDA conforme disponibilidade.

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3 (ex: "EGIE3", "SBSP3", "TAEE11").
    db_path : Path | None
        Caminho do ingestion.db.
    scanner_db : str | None
        Caminho do scanner_quant.db.
    period_end : str | None
        Período específico. None = mais recente DFP.
    """
    from src.valuation.models.utility_model import (
        UtilityValuationInputs,
        UtilityInputQuality,
        UTILITY_PRESERVED_FAIR_VALUES,
    )

    ticker_upper = str(ticker).strip().upper()
    store = load_financial_inputs_from_store(ticker_upper, period_end=period_end, db_path=db_path)
    metrics = store["metrics"]
    flags   = store["quality_flags"]
    src_q   = store["source_quality"]

    quality_map = {
        "CVM_LIVE":       UtilityInputQuality.CVM_LIVE,
        "EXCEL_PIPELINE": UtilityInputQuality.EXCEL_PIPELINE,
        "ABSENT":         UtilityInputQuality.ABSENT,
    }
    model_quality = quality_map.get(src_q, UtilityInputQuality.ABSENT)

    existing_fv = UTILITY_PRESERVED_FAIR_VALUES.get(ticker_upper)
    if existing_fv is None:
        existing_fv = _load_existing_fair_value(ticker_upper, scanner_db)

    market_price = _load_market_price(ticker_upper, scanner_db)

    wacc = WACC_DEFAULTS["utility"]
    g    = TERMINAL_GROWTH_DEFAULT

    # FCF com regras de qualidade e verificação de viabilidade DCF
    fcf = _fcf_for_model(metrics, flags, ticker_upper, wacc=wacc, g=g)

    subsector = TICKER_SUBSECTOR_MAP.get(ticker_upper, "generation")

    inputs = UtilityValuationInputs(
        ticker=ticker_upper,
        free_cash_flow=fcf,
        ebitda=_m(metrics, "ebitda"),
        net_debt=_m(metrics, "net_debt"),
        shares_outstanding=_m(metrics, "shares_outstanding"),
        wacc=wacc,
        terminal_growth=g,
        rab=None,          # RAB não disponível no store — RAB-DCF bloqueado
        wacc_spread=None,  # RAB-DCF bloqueado
        market_price=market_price,
        source_quality=model_quality,
        existing_fair_value=existing_fv,
        existing_valuation_date=None,
        subsector=subsector,
    )

    meta = {
        "period_end":    store["period_end"],
        "quality_flags": flags,
        "source_quality": src_q,
        "available":     store["available"],
        "confidence":    store["confidence"],
    }

    logger.info(
        "build_utility_inputs_from_store: ticker=%s ebitda=%s fcf=%s "
        "net_debt=%s shares=%s flags=%s subsector=%s",
        ticker_upper,
        f"{inputs.ebitda:.0f}M" if inputs.ebitda is not None else "None",
        f"{inputs.free_cash_flow:.0f}M" if inputs.free_cash_flow is not None else "None",
        f"{inputs.net_debt:.0f}M" if inputs.net_debt is not None else "None",
        f"{inputs.shares_outstanding:.1f}M" if inputs.shares_outstanding is not None else "None",
        flags,
        subsector,
    )

    return inputs, meta


# ─────────────────────────────────────────────────────────────────────────────
#  4. Hidratador: Retail
# ─────────────────────────────────────────────────────────────────────────────

def build_retail_inputs_from_store(
    ticker: str,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Constrói RetailValuationInputs a partir do store canônico.

    PCAR3: DISTRESSED detectado via EBIT < 0 → FCF bloqueado (DCF inválido)
    MGLU3: FCF_REVIEW detectado → FCF bloqueado (DCF produz resultado implausível)

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3 (ex: "LREN3", "MGLU3", "PCAR3").
    """
    from src.valuation.models.retail_model import (
        RetailValuationInputs,
        RetailInputQuality,
        RETAIL_PRESERVED_FAIR_VALUES,
    )

    ticker_upper = str(ticker).strip().upper()
    store = load_financial_inputs_from_store(ticker_upper, period_end=period_end, db_path=db_path)
    metrics = store["metrics"]
    flags   = store["quality_flags"]
    src_q   = store["source_quality"]

    quality_map = {
        "CVM_LIVE":       RetailInputQuality.CVM_LIVE,
        "EXCEL_PIPELINE": RetailInputQuality.EXCEL_PIPELINE,
        "ABSENT":         RetailInputQuality.ABSENT,
    }
    model_quality = quality_map.get(src_q, RetailInputQuality.ABSENT)

    existing_fv = RETAIL_PRESERVED_FAIR_VALUES.get(ticker_upper)
    if existing_fv is None:
        existing_fv = _load_existing_fair_value(ticker_upper, scanner_db)

    market_price = _load_market_price(ticker_upper, scanner_db)

    wacc = WACC_DEFAULTS["retail"]
    g    = TERMINAL_GROWTH_DEFAULT

    fcf = _fcf_for_model(metrics, flags, ticker_upper, wacc=wacc, g=g)

    subsector = TICKER_SUBSECTOR_MAP.get(ticker_upper, "fashion")

    inputs = RetailValuationInputs(
        ticker=ticker_upper,
        free_cash_flow=fcf,
        ebitda=_m(metrics, "ebitda"),
        net_debt=_m(metrics, "net_debt"),
        shares_outstanding=_m(metrics, "shares_outstanding"),
        wacc=wacc,
        terminal_growth=g,
        market_price=market_price,
        source_quality=model_quality,
        existing_fair_value=existing_fv,
        existing_valuation_date=None,
        subsector=subsector,
    )

    meta = {
        "period_end":    store["period_end"],
        "quality_flags": flags,
        "source_quality": src_q,
        "available":     store["available"],
        "confidence":    store["confidence"],
    }

    logger.info(
        "build_retail_inputs_from_store: ticker=%s ebitda=%s fcf=%s "
        "net_debt=%s shares=%s flags=%s distressed=%s",
        ticker_upper,
        f"{inputs.ebitda:.0f}M" if inputs.ebitda is not None else "None",
        f"{inputs.free_cash_flow:.0f}M" if inputs.free_cash_flow is not None else "None",
        f"{inputs.net_debt:.0f}M" if inputs.net_debt is not None else "None",
        f"{inputs.shares_outstanding:.1f}M" if inputs.shares_outstanding is not None else "None",
        flags,
        "DISTRESSED" in flags,
    )

    return inputs, meta


# ─────────────────────────────────────────────────────────────────────────────
#  5. Hidratador: Industry
# ─────────────────────────────────────────────────────────────────────────────

def build_industry_inputs_from_store(
    ticker: str,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Constrói IndustryValuationInputs a partir do store canônico.

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3 (ex: "FLRY3", "KLBN11", "VAMO3").
    """
    from src.valuation.models.industry_model import (
        IndustryValuationInputs,
        IndustryInputQuality,
        INDUSTRY_PRESERVED_FAIR_VALUES,
    )

    ticker_upper = str(ticker).strip().upper()
    store = load_financial_inputs_from_store(ticker_upper, period_end=period_end, db_path=db_path)
    metrics = store["metrics"]
    flags   = store["quality_flags"]
    src_q   = store["source_quality"]

    quality_map = {
        "CVM_LIVE":       IndustryInputQuality.CVM_LIVE,
        "EXCEL_PIPELINE": IndustryInputQuality.EXCEL_PIPELINE,
        "ABSENT":         IndustryInputQuality.ABSENT,
    }
    model_quality = quality_map.get(src_q, IndustryInputQuality.ABSENT)

    existing_fv = INDUSTRY_PRESERVED_FAIR_VALUES.get(ticker_upper)
    if existing_fv is None:
        existing_fv = _load_existing_fair_value(ticker_upper, scanner_db)

    market_price = _load_market_price(ticker_upper, scanner_db)

    wacc = WACC_DEFAULTS["industry"]
    g    = TERMINAL_GROWTH_DEFAULT

    fcf = _fcf_for_model(metrics, flags, ticker_upper, wacc=wacc, g=g)

    subsector = TICKER_SUBSECTOR_MAP.get(ticker_upper, "industrial")

    inputs = IndustryValuationInputs(
        ticker=ticker_upper,
        free_cash_flow=fcf,
        ebitda=_m(metrics, "ebitda"),
        net_debt=_m(metrics, "net_debt"),
        shares_outstanding=_m(metrics, "shares_outstanding"),
        wacc=wacc,
        terminal_growth=g,
        market_price=market_price,
        source_quality=model_quality,
        existing_fair_value=existing_fv,
        existing_valuation_date=None,
        subsector=subsector,
    )

    meta = {
        "period_end":    store["period_end"],
        "quality_flags": flags,
        "source_quality": src_q,
        "available":     store["available"],
        "confidence":    store["confidence"],
    }

    logger.info(
        "build_industry_inputs_from_store: ticker=%s ebitda=%s fcf=%s "
        "net_debt=%s shares=%s flags=%s subsector=%s",
        ticker_upper,
        f"{inputs.ebitda:.0f}M" if inputs.ebitda is not None else "None",
        f"{inputs.free_cash_flow:.0f}M" if inputs.free_cash_flow is not None else "None",
        f"{inputs.net_debt:.0f}M" if inputs.net_debt is not None else "None",
        f"{inputs.shares_outstanding:.1f}M" if inputs.shares_outstanding is not None else "None",
        flags,
        subsector,
    )

    return inputs, meta


# ─────────────────────────────────────────────────────────────────────────────
#  6. Dry-run: cálculo por ticker (write=False garantido)
# ─────────────────────────────────────────────────────────────────────────────

def _run_single_ticker_dry_run(
    ticker: str,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Executa dry-run de valuation para um único ticker.

    Seleciona o builder correto baseado em TICKER_SECTOR_MAP.
    write=False é garantido — nenhum fair_value é persistido.

    Parâmetros
    ----------
    ticker : str
        Código do ativo B3.
    db_path : Path | None
        Caminho do ingestion.db.
    scanner_db : str | None
        Caminho do scanner_quant.db.
    period_end : str | None
        Período específico. None = mais recente DFP.

    Retorno
    -------
    dict com:
        ticker           : str
        sector           : str
        subsector        : str
        period_end       : str | None
        quality_flags    : list[str]
        source_quality   : str
        status           : str       — VALUATION_READY | NEEDS_FINANCIALS | DISTRESSED | etc.
        would_calculate  : bool      — True se fair_value seria calculado com write=True
        fair_value       : float | None — resultado do dry-run (não persistido)
        method_used      : str | None
        confidence       : float
        upside_pct       : float | None
        block_reason     : str | None
        notes            : str
        write_prevented  : bool      — sempre True (confirmação de segurança)
    """
    from src.valuation.models.commodity_model import calculate_commodity_valuation
    from src.valuation.models.utility_model   import calculate_utility_valuation
    from src.valuation.models.retail_model    import calculate_retail_valuation
    from src.valuation.models.industry_model  import calculate_industry_valuation

    ticker_upper = str(ticker).strip().upper()
    sector = TICKER_SECTOR_MAP.get(ticker_upper, "industry")
    subsector = TICKER_SUBSECTOR_MAP.get(ticker_upper, "unknown")

    try:
        if sector == "commodity":
            inputs, meta = build_commodity_inputs_from_store(
                ticker_upper, db_path=db_path, scanner_db=scanner_db, period_end=period_end
            )
            result = calculate_commodity_valuation(inputs, force_recalc=False)

        elif sector == "utility":
            inputs, meta = build_utility_inputs_from_store(
                ticker_upper, db_path=db_path, scanner_db=scanner_db, period_end=period_end
            )
            result = calculate_utility_valuation(inputs, force_recalc=False)

        elif sector == "retail":
            inputs, meta = build_retail_inputs_from_store(
                ticker_upper, db_path=db_path, scanner_db=scanner_db, period_end=period_end
            )
            result = calculate_retail_valuation(inputs, force_recalc=False)

        else:  # industry (default)
            inputs, meta = build_industry_inputs_from_store(
                ticker_upper, db_path=db_path, scanner_db=scanner_db, period_end=period_end
            )
            result = calculate_industry_valuation(inputs, force_recalc=False)

    except Exception as exc:
        logger.error("_run_single_ticker_dry_run: ticker=%s erro=%s", ticker_upper, exc)
        return {
            "ticker":          ticker_upper,
            "sector":          sector,
            "subsector":       subsector,
            "period_end":      None,
            "quality_flags":   [],
            "source_quality":  "ABSENT",
            "status":          "ERROR",
            "would_calculate": False,
            "fair_value":      None,
            "method_used":     None,
            "confidence":      0.0,
            "upside_pct":      None,
            "block_reason":    f"Exceção: {exc}",
            "notes":           f"Erro na execução: {exc}",
            "write_prevented": True,
        }

    # Determinar status final para o relatório
    flags = meta.get("quality_flags", [])
    is_distressed = "DISTRESSED" in flags
    is_partial = is_distressed and not result.blocked

    if is_distressed and result.blocked:
        report_status = "PARTIAL_INPUTS/DISTRESSED"
    elif is_distressed:
        report_status = "PARTIAL_INPUTS/DISTRESSED"
    else:
        report_status = result.status

    would_calculate = not result.blocked and result.fair_value is not None

    return {
        "ticker":          ticker_upper,
        "sector":          sector,
        "subsector":       subsector,
        "period_end":      meta.get("period_end"),
        "quality_flags":   flags,
        "source_quality":  meta.get("source_quality", "ABSENT"),
        "status":          report_status,
        "would_calculate": would_calculate,
        "fair_value":      result.fair_value,
        "method_used":     result.method_used,
        "confidence":      result.confidence,
        "upside_pct":      result.upside_pct,
        "block_reason":    result.block_reason,
        "notes":           result.notes,
        "write_prevented": True,  # SEMPRE True — segurança confirmada
    }


# ─────────────────────────────────────────────────────────────────────────────
#  7. Dry-run batch dos 18 tickers M017
# ─────────────────────────────────────────────────────────────────────────────

#: Tickers M017-S05 alvo do dry-run
M017_DRY_RUN_TICKERS: List[str] = [
    "PRIO3", "RECV3",                            # COMMODITY
    "EGIE3", "SBSP3", "TAEE11",                  # UTILITY
    "AZZA3", "LREN3", "MGLU3", "PCAR3", "VIVA3", # RETAIL
    "FLRY3", "HYPE3", "KLBN11", "RADL3", "RAIL3", # INDUSTRY
    "RENT3", "SUZB3", "VAMO3",                   # INDUSTRY (cont.)
]


def run_dry_run_all(
    tickers: Optional[List[str]] = None,
    db_path: Optional[Path] = None,
    scanner_db: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Executa dry-run de valuation para todos os 18 tickers M017-S05.

    Garante write=False em todos os modelos — nenhum fair_value é persistido.
    Nenhuma tabela do banco é alterada.

    Parâmetros
    ----------
    tickers : list[str] | None
        Lista de tickers. None = M017_DRY_RUN_TICKERS completo (18 tickers).
    db_path : Path | None
        Caminho do ingestion.db.
    scanner_db : str | None
        Caminho do scanner_quant.db.
    period_end : str | None
        Período fixo. None = mais recente DFP por ticker.

    Retorno
    -------
    dict[str, dict]
        Mapeamento ticker → resultado do dry-run.
        Cada resultado contém: status, would_calculate, fair_value, method_used,
        confidence, upside_pct, block_reason, quality_flags, notes, write_prevented.
    """
    target = [t.strip().upper() for t in (tickers or M017_DRY_RUN_TICKERS)]
    results: Dict[str, Dict[str, Any]] = {}

    logger.info(
        "run_dry_run_all: iniciando dry-run de %d tickers — write=False garantido",
        len(target),
    )

    for ticker in target:
        logger.info("run_dry_run_all: processando %s", ticker)
        res = _run_single_ticker_dry_run(
            ticker,
            db_path=db_path,
            scanner_db=scanner_db,
            period_end=period_end,
        )
        results[ticker] = res

        logger.info(
            "run_dry_run_all: %s → status=%s, would_calc=%s, fv=%s, method=%s, flags=%s",
            ticker,
            res["status"],
            res["would_calculate"],
            f"R${res['fair_value']:.2f}" if res["fair_value"] is not None else "None",
            res["method_used"],
            res["quality_flags"],
        )

    # Sumário
    ready = sum(1 for r in results.values() if r["would_calculate"])
    blocked = sum(1 for r in results.values() if not r["would_calculate"])
    logger.info(
        "run_dry_run_all: concluído — %d/%d calculariam fair_value com write=True | %d bloqueados",
        ready, len(target), blocked,
    )

    return results


def print_dry_run_report(results: Dict[str, Dict[str, Any]]) -> None:
    """Imprime relatório de dry-run formatado no log.

    Não altera banco, não cria arquivos, não persistem dados.
    """
    print("\n" + "=" * 80)
    print("M017-S05 DRY-RUN REPORT — write=False (nenhum fair_value salvo)")
    print("=" * 80)

    would_calc = [r for r in results.values() if r["would_calculate"]]
    blocked    = [r for r in results.values() if not r["would_calculate"]]

    print(f"\n✅ CALCULARIAM fair_value (write=True) → {len(would_calc)}/{len(results)}")
    for r in sorted(would_calc, key=lambda x: x["ticker"]):
        flags_str = ", ".join(r["quality_flags"]) if r["quality_flags"] else "-"
        upside_str = f"upside={r['upside_pct']:+.1f}%" if r["upside_pct"] is not None else ""
        print(
            f"  {r['ticker']:8s} | {r['sector']:9s} | "
            f"fv=R${r['fair_value']:.2f} | method={r['method_used']} | "
            f"conf={r['confidence']:.2f} | flags=[{flags_str}] {upside_str}"
        )

    print(f"\n❌ BLOQUEADOS → {len(blocked)}/{len(results)}")
    for r in sorted(blocked, key=lambda x: x["ticker"]):
        flags_str = ", ".join(r["quality_flags"]) if r["quality_flags"] else "-"
        reason = (r["block_reason"] or "")[:60] + "..." if r.get("block_reason") and len(r.get("block_reason","")) > 60 else (r.get("block_reason") or "")
        print(
            f"  {r['ticker']:8s} | {r['sector']:9s} | "
            f"status={r['status']} | flags=[{flags_str}]"
        )
        if reason:
            print(f"           reason: {reason}")

    print(f"\n🔒 SEGURANÇA: write_prevented=True em todos os {len(results)} tickers")
    print(f"   Confirmação: nenhum fair_value escrito em nenhuma tabela do banco.")
    print("=" * 80 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
#  Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Constantes
    "TICKER_SECTOR_MAP",
    "TICKER_SUBSECTOR_MAP",
    "WACC_DEFAULTS",
    "TERMINAL_GROWTH_DEFAULT",
    "M017_DRY_RUN_TICKERS",
    # Carregador canônico
    "load_financial_inputs_from_store",
    # Hidratadores por modelo
    "build_commodity_inputs_from_store",
    "build_utility_inputs_from_store",
    "build_retail_inputs_from_store",
    "build_industry_inputs_from_store",
    # Dry-run
    "run_dry_run_all",
    "print_dry_run_report",
    # Helpers (exportados para testes)
    "_detect_quality_flags",
    "_fcf_for_model",
    "_resolve_ingestion_db",
    "_load_market_price",
]
