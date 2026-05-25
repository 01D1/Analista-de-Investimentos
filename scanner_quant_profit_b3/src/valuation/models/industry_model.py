"""
src/valuation/models/industry_model.py — Industry / Tech-Fallback Valuation Model (M016-S04)

Modelo de valuation para indústria, saúde, celulose, logística e telecom (TECH/FALLBACK)
usando metodologia DCF/EV-EBITDA:
  - DCF/FCFF como método primário (Gordon Growth sobre FCF)
  - EV/EBITDA como método secundário (se EBITDA > 0)
  - Bloqueio total se dados insuficientes

Grupo INDUSTRY confirmado (M016-S01/S04):
  FLRY3  — Fleury Medicina e Saúde (healthcare diagnostics)
  HYPE3  — Hypera Pharma (farmacêutico)
  KLBN11 — Klabin (celulose e papel)
  RADL3  — RaiaDrogasil (farmácias)
  RAIL3  — Rumo Logística (logística ferroviária)
  RENT3  — Localiza (locação de veículos)
  SUZB3  — Suzano (celulose)
  VAMO3  — Vamos (locação de frotas/máquinas)
  WEGE3  — WEG (motores elétricos/industrial) → PRESERVE=40.16

Grupo TECH/FALLBACK (M016-S01/S04):
  VIVT3  — Vivo/Telefônica Brasil (telecom) → roteado via INDUSTRY como tech_fallback

Diagnóstico de fontes (M016-S04):
  FLRY3:  market_price=15.69, fair_value=None, ri_docs=128 → NEEDS_FINANCIALS
  HYPE3:  market_price=22.56, fair_value=None, ri_docs=132 → NEEDS_FINANCIALS
  KLBN11: market_price=16.46, fair_value=None, ri_docs=129 → NEEDS_FINANCIALS
  RADL3:  market_price=18.19, fair_value=None, ri_docs=129 → NEEDS_FINANCIALS
  RAIL3:  market_price=14.21, fair_value=None, ri_docs=135 → NEEDS_FINANCIALS
  RENT3:  market_price=43.35, fair_value=None, ri_docs=129 → NEEDS_FINANCIALS
  SUZB3:  market_price=41.70, fair_value=None, ri_docs=131 → NEEDS_FINANCIALS
  VAMO3:  market_price=3.25,  fair_value=None, ri_docs=17  → NEEDS_FINANCIALS (baixo RI)
  WEGE3:  market_price=42.73, fair_value=40.16,ri_docs=124 → PRESERVE_EXISTING
  VIVT3:  market_price=34.81, fair_value=None, ri_docs=128 → NEEDS_FINANCIALS (TECH_FALLBACK)

Regras HARD BLOCK (nunca produz fair_value se violadas):
  I-IND-01: free_cash_flow ausente → DCF/FCFF bloqueado
  I-IND-02: WACC <= terminal_growth → modelo DCF indefinido
  I-IND-03: net_debt ausente → enterprise value indefinido
  I-IND-04: shares_outstanding <= 0 → per-share indefinido
  I-IND-05: ebitda <= 0 → EV/EBITDA múltiplo bloqueado

Regras de preservação:
  WEGE3 = 40.16 → PRESERVE_EXISTING (não sobrescrever sem force_recalc=True)

Fórmulas utilizadas (inputs reais obrigatórios):
  DCF/FCFF (Gordon Growth):
    enterprise_value = FCF / (WACC - terminal_growth)
    equity_value     = enterprise_value - net_debt
    fair_value       = equity_value / shares_outstanding

  EV/EBITDA:
    enterprise_value = EBITDA × ev_ebitda_multiple
    equity_value     = enterprise_value - net_debt
    fair_value       = equity_value / shares_outstanding

Proibido neste módulo:
  - Fazer chamadas a LLM ou APIs externas
  - Usar dados mockados ou sintéticos
  - Alterar banco de dados diretamente
  - Calcular fair_value quando inputs reais forem insuficientes
  - Alterar módulos de opções/OOS/paper/scheduler
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Constantes e enumerações
# ─────────────────────────────────────────────────────────────────────────────

#: Tickers do grupo INDUSTRY confirmados pelo SectorNormalizer (M016-S01)
INDUSTRY_TICKERS: frozenset[str] = frozenset({
    "FLRY3",   # Fleury — healthcare diagnostics
    "HYPE3",   # Hypera Pharma — farmacêutico
    "KLBN11",  # Klabin — celulose/papel
    "RADL3",   # RaiaDrogasil — farmácias
    "RAIL3",   # Rumo — logística ferroviária
    "RENT3",   # Localiza — locação de veículos
    "SUZB3",   # Suzano — celulose
    "VAMO3",   # Vamos — locação de frotas
    "WEGE3",   # WEG — motores elétricos/industrial
})

#: Ticker TECH/FALLBACK roteado via industry_model (M016-S01: D108)
TECH_FALLBACK_TICKERS: frozenset[str] = frozenset({
    "VIVT3",   # Vivo/Telefônica — telecom (sem modelo próprio)
})

#: Todos os tickers tratados por este módulo (INDUSTRY + TECH_FALLBACK)
ALL_INDUSTRY_TICKERS: frozenset[str] = INDUSTRY_TICKERS | TECH_FALLBACK_TICKERS

#: Fair values existentes a preservar (só podem ser sobrescritos com force_recalc=True)
#: WEGE3=40.16 vem do campo fair_value em asset_intelligence_snapshots (M016-S04 diagnóstico)
INDUSTRY_PRESERVED_FAIR_VALUES: dict[str, float] = {
    "WEGE3": 40.16,
}

#: Múltiplo EV/EBITDA de referência para indústria brasileira (consenso setorial)
DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE: float = 8.0

#: Múltiplos EV/EBITDA por subsector industrial
INDUSTRY_EV_EBITDA_BY_SUBSECTOR: dict[str, float] = {
    "healthcare":    12.0,  # Healthcare diagnostics: FLRY3 (margens estáveis)
    "pharma":        12.0,  # Farmacêutico: HYPE3
    "pulp":          7.0,   # Celulose commodity: KLBN11, SUZB3 (ciclos)
    "pharmacy":      10.0,  # Farmácias/drogarias: RADL3 (crescimento forte)
    "logistics":     9.0,   # Logística ferroviária: RAIL3 (concessão ANTT)
    "rental":        10.0,  # Locação de veículos/frota: RENT3, VAMO3
    "industrial":    14.0,  # Industrial diversificado: WEGE3 (premium global)
    "telecom":       8.0,   # Telecom: VIVT3 (maturidade, dividendos)
    "tech_fallback": 8.0,   # TECH/FALLBACK genérico
}


class IndustryValuationMethod:
    """Constantes de método para valuation de indústria."""
    DCF_FCFF      = "DCF_FCFF"          # DCF/FCFF (Gordon Growth) — primário
    EV_EBITDA     = "EV_EBITDA"         # Múltiplo EV/EBITDA — secundário
    PRESERVE      = "PRESERVE_EXISTING" # Preservar valor existente
    BLOCKED       = "BLOCKED"           # Sem método disponível


class IndustryInputQuality:
    """Qualidade dos inputs de dados."""
    CVM_LIVE       = "CVM_LIVE"          # Dados ao vivo CVM / RI estruturado
    EXCEL_PIPELINE = "EXCEL_PIPELINE"    # Modelo Excel pipeline
    ESTIMATED      = "ESTIMATED"         # Estimativas derivadas
    ABSENT         = "ABSENT"            # Dados ausentes


class IndustryValuationStatus:
    """Status do diagnóstico do ticker."""
    VALUATION_READY    = "VALUATION_READY"     # Dados suficientes para calcular
    PRESERVE_EXISTING  = "PRESERVE_EXISTING"   # Valor existente a preservar
    NEEDS_FINANCIALS   = "NEEDS_FINANCIALS"    # EBITDA/FCF ausentes no banco
    NEEDS_DATA         = "NEEDS_DATA"          # ri_docs=0 (bloqueio absoluto)
    NEEDS_REVIEW       = "NEEDS_REVIEW"        # Dados presentes mas suspeitos
    TECH_FALLBACK      = "TECH_FALLBACK"       # TECH/FALLBACK: sem modelo próprio


# ─────────────────────────────────────────────────────────────────────────────
#  Dataclasses de inputs e resultado
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IndustryValuationInputs:
    """Inputs para valuation de indústria / TECH-FALLBACK.

    Todos os campos opcionais — modelo bloqueia com block_reason se mínimos ausentes.
    Nunca usar valores mockados aqui.

    Campos
    ------
    ticker : str
        Código do ativo B3 (ex: "WEGE3", "RENT3", "VIVT3").
    free_cash_flow : float | None
        FCF/FCFF anual — R$ milhões.
        I-IND-01: bloqueia DCF/FCFF se ausente.
    ebitda : float | None
        EBITDA anual — R$ milhões.
        I-IND-05: bloqueia EV/EBITDA se <= 0.
    net_debt : float | None
        Dívida líquida = dívida bruta − caixa — R$ milhões.
        I-IND-03: bloqueia todos os métodos se ausente.
    shares_outstanding : float | None
        Número de ações em circulação — milhões de ações.
        I-IND-04: bloqueia per-share se <= 0.
    wacc : float | None
        Custo médio ponderado de capital (decimal, ex: 0.11 = 11%).
        I-IND-02: bloqueia DCF se None ou <= terminal_growth.
    terminal_growth : float | None
        Taxa de crescimento terminal g (decimal, ex: 0.04 = 4%).
        I-IND-02: bloqueia DCF se WACC <= g.
    ev_ebitda_multiple : float | None
        Múltiplo EV/EBITDA de referência setorial.
        Se None, usa default por subsector ou DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE.
    market_price : float | None
        Preço de mercado atual (R$). Usado para calcular upside.
    source_quality : str
        Qualidade dos dados de origem (IndustryInputQuality constants).
    existing_fair_value : float | None
        Fair value já registrado (para lógica PRESERVE).
    existing_valuation_date : str | None
        Data do valuation existente (ISO format, ex: "2026-04-16").
    subsector : str | None
        Subsector: "healthcare", "pharma", "pulp", "pharmacy", "logistics",
                   "rental", "industrial", "telecom", "tech_fallback".
        Usado para default de múltiplo EV/EBITDA.
    """

    ticker: str
    free_cash_flow: Optional[float] = None
    ebitda: Optional[float] = None
    net_debt: Optional[float] = None
    shares_outstanding: Optional[float] = None
    wacc: Optional[float] = None
    terminal_growth: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    market_price: Optional[float] = None
    source_quality: str = IndustryInputQuality.ABSENT
    existing_fair_value: Optional[float] = None
    existing_valuation_date: Optional[str] = None
    subsector: Optional[str] = None

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker).strip().upper()

    @property
    def effective_ev_ebitda_multiple(self) -> float:
        """Múltiplo EV/EBITDA efetivo — explícito ou default por subsector."""
        if self.ev_ebitda_multiple is not None and self.ev_ebitda_multiple > 0:
            return self.ev_ebitda_multiple
        if self.subsector:
            sub_lower = self.subsector.lower()
            for key, mult in INDUSTRY_EV_EBITDA_BY_SUBSECTOR.items():
                if key in sub_lower:
                    return mult
        return DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE

    @property
    def is_tech_fallback(self) -> bool:
        """True se ticker pertence ao grupo TECH/FALLBACK."""
        return self.ticker in TECH_FALLBACK_TICKERS

    @property
    def fcf_per_share(self) -> Optional[float]:
        """FCF por ação (R$)."""
        if (self.free_cash_flow is not None
                and self.shares_outstanding is not None
                and self.shares_outstanding > 0):
            return self.free_cash_flow / self.shares_outstanding
        return None


@dataclass
class IndustryValuationResult:
    """Resultado de valuation para indústria / TECH-FALLBACK.

    Campos
    ------
    ticker : str
        Código do ativo B3.
    fair_value : float | None
        Preço-alvo calculado (R$). None se bloqueado ou sem dados.
    valuation_method : str | None
        Método principal utilizado.
    method_used : str | None
        Método que efetivamente produziu o fair_value.
    confidence : float
        Confiança do resultado (0.0 a 1.0). 0.0 se bloqueado.
    input_quality : str
        Qualidade dos inputs utilizados.
    status : str
        Status do diagnóstico (IndustryValuationStatus constants).
    blocked : bool
        True se o cálculo foi bloqueado por dados insuficientes.
    block_reason : str | None
        Razão do bloqueio.
    is_tech_fallback : bool
        True se ticker é TECH/FALLBACK (VIVT3).
    upside_pct : float | None
        Upside potencial em relação ao preço de mercado (%).
    valuation_date : str
        Data de referência do valuation (ISO format).
    enterprise_value : float | None
        Enterprise value calculado (R$ milhões).
    equity_value : float | None
        Equity value = EV - net_debt (R$ milhões).
    ev_ebitda_used : float | None
        Múltiplo EV/EBITDA utilizado.
    wacc_used : float | None
        WACC utilizado no DCF.
    terminal_growth_used : float | None
        Terminal growth g utilizado.
    notes : str
        Notas de auditoria e diagnóstico.
    """

    ticker: str
    fair_value: Optional[float] = None
    valuation_method: Optional[str] = None
    method_used: Optional[str] = None
    confidence: float = 0.0
    input_quality: str = IndustryInputQuality.ABSENT
    status: str = IndustryValuationStatus.NEEDS_FINANCIALS
    blocked: bool = True
    block_reason: Optional[str] = None
    is_tech_fallback: bool = False
    upside_pct: Optional[float] = None
    valuation_date: str = field(default_factory=lambda: date.today().isoformat())
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    ev_ebitda_used: Optional[float] = None
    wacc_used: Optional[float] = None
    terminal_growth_used: Optional[float] = None
    notes: str = ""

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker).strip().upper()
        if self.blocked and self.confidence > 0:
            self.confidence = 0.0

    @classmethod
    def blocked_result(
        cls,
        ticker: str,
        block_reason: str,
        status: str = IndustryValuationStatus.NEEDS_FINANCIALS,
        input_quality: str = IndustryInputQuality.ABSENT,
        is_tech_fallback: bool = False,
        notes: str = "",
    ) -> "IndustryValuationResult":
        """Factory para resultado bloqueado — sem fair_value."""
        return cls(
            ticker=ticker,
            fair_value=None,
            valuation_method=None,
            method_used=None,
            confidence=0.0,
            input_quality=input_quality,
            status=status,
            blocked=True,
            block_reason=block_reason,
            is_tech_fallback=is_tech_fallback,
            notes=notes,
        )

    @classmethod
    def preserved_result(
        cls,
        ticker: str,
        fair_value: float,
        market_price: Optional[float] = None,
        valuation_date: Optional[str] = None,
        is_tech_fallback: bool = False,
        notes: str = "",
    ) -> "IndustryValuationResult":
        """Factory para resultado preservado (não recalculado)."""
        upside = None
        if market_price is not None and market_price > 0 and fair_value > 0:
            upside = round((fair_value / market_price - 1) * 100, 2)
        return cls(
            ticker=ticker,
            fair_value=fair_value,
            valuation_method=IndustryValuationMethod.PRESERVE,
            method_used=IndustryValuationMethod.PRESERVE,
            confidence=0.9,
            input_quality=IndustryInputQuality.EXCEL_PIPELINE,
            status=IndustryValuationStatus.PRESERVE_EXISTING,
            blocked=False,
            block_reason=None,
            is_tech_fallback=is_tech_fallback,
            upside_pct=upside,
            valuation_date=valuation_date or date.today().isoformat(),
            notes=notes or "Valor preservado. Use force_recalc=True para recalcular.",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Validações e hard blocks
# ─────────────────────────────────────────────────────────────────────────────

def _validate_industry_shares_and_net_debt(inputs: IndustryValuationInputs) -> Optional[str]:
    """Validações comuns a todos os métodos industry.

    Hard blocks:
      I-IND-03: net_debt ausente → EV indefinido
      I-IND-04: shares_outstanding <= 0 → per-share indefinido
    """
    if inputs.net_debt is None:
        return (
            "I-IND-03: net_debt ausente — não é possível calcular equity value. "
            "Forneça dívida líquida."
        )
    if inputs.shares_outstanding is None:
        return "I-IND-04: shares_outstanding ausente — per-share indefinido"
    if inputs.shares_outstanding <= 0:
        return (
            f"I-IND-04: shares_outstanding={inputs.shares_outstanding:.0f} ≤ 0 — inválido"
        )
    return None


def _validate_industry_dcf_prerequisites(inputs: IndustryValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para DCF/FCFF industry.

    Hard blocks:
      I-IND-01: free_cash_flow ausente
      I-IND-02: WACC ausente ou WACC <= terminal_growth
    """
    if inputs.free_cash_flow is None:
        return "I-IND-01: free_cash_flow ausente — DCF/FCFF indisponível"

    if inputs.wacc is None:
        return "I-IND-02: wacc ausente — DCF/FCFF indisponível"
    if inputs.wacc <= 0:
        return f"I-IND-02: wacc={inputs.wacc:.4f} ≤ 0 — inválido"

    if inputs.terminal_growth is None:
        return "I-IND-02: terminal_growth ausente — DCF/FCFF indisponível"

    if inputs.wacc <= inputs.terminal_growth:
        return (
            f"I-IND-02: HARD BLOCK — WACC={inputs.wacc:.4f} ≤ terminal_growth={inputs.terminal_growth:.4f}. "
            "Modelo DCF indefinido: divisor (WACC − g) ≤ 0. "
            "Ajuste as premissas (WACC deve superar o crescimento terminal)."
        )

    if inputs.terminal_growth < -0.10:
        return (
            f"I-IND-02: terminal_growth={inputs.terminal_growth:.4f} < −10% — improvável. "
            "Verifique as premissas de crescimento."
        )
    return None


def _validate_industry_ev_ebitda_prerequisites(inputs: IndustryValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para EV/EBITDA industry.

    Hard blocks:
      I-IND-05: EBITDA <= 0 → múltiplo inválido
    """
    if inputs.ebitda is None:
        return "I-IND-05: ebitda ausente — EV/EBITDA indisponível"
    if inputs.ebitda <= 0:
        return (
            f"I-IND-05: HARD BLOCK — ebitda={inputs.ebitda:.2f} ≤ 0. "
            "EV/EBITDA múltiplo inválido para EBITDA não-positivo."
        )
    multiple = inputs.effective_ev_ebitda_multiple
    if multiple <= 0:
        return f"I-IND-05: ev_ebitda_multiple={multiple:.2f} ≤ 0 — inválido"
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Motores de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_industry_dcf_fcff(inputs: IndustryValuationInputs) -> tuple[float, float, float]:
    """Calcula fair_value via DCF/FCFF (Gordon Growth)."""
    fcf = inputs.free_cash_flow
    wacc = inputs.wacc
    g = inputs.terminal_growth
    net_debt = inputs.net_debt
    shares = inputs.shares_outstanding

    enterprise_value = round(fcf / (wacc - g), 2)
    equity_value = round(enterprise_value - net_debt, 2)
    fair_value = round(equity_value / shares, 2)

    return fair_value, enterprise_value, equity_value


def _calculate_industry_ev_ebitda(inputs: IndustryValuationInputs) -> tuple[float, float, float, float]:
    """Calcula fair_value via EV/EBITDA."""
    ebitda = inputs.ebitda
    multiple = inputs.effective_ev_ebitda_multiple
    net_debt = inputs.net_debt
    shares = inputs.shares_outstanding

    enterprise_value = round(ebitda * multiple, 2)
    equity_value = round(enterprise_value - net_debt, 2)
    fair_value = round(equity_value / shares, 2)

    return fair_value, enterprise_value, equity_value, multiple


def _confidence_from_quality_industry(source_quality: str) -> float:
    """Deriva confiança a partir da qualidade dos inputs."""
    return {
        IndustryInputQuality.CVM_LIVE:       0.90,
        IndustryInputQuality.EXCEL_PIPELINE: 0.75,
        IndustryInputQuality.ESTIMATED:      0.45,
        IndustryInputQuality.ABSENT:         0.00,
    }.get(source_quality, 0.45)


# ─────────────────────────────────────────────────────────────────────────────
#  Motor principal de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def calculate_industry_valuation(
    inputs: IndustryValuationInputs,
    force_recalc: bool = False,
) -> IndustryValuationResult:
    """Calcula valuation para um ticker de indústria ou TECH/FALLBACK.

    Motor seguro — nunca inventa dados, nunca ignora hard blocks.

    Hierarquia de métodos:
      1. PRESERVE_EXISTING — se existing_fair_value preenchido E force_recalc=False
         (WEGE3=40.16 preservado por padrão)
      2. DCF/FCFF          — se FCF, WACC, g, net_debt, shares disponíveis e WACC > g
      3. EV/EBITDA         — se EBITDA > 0, net_debt, shares disponíveis
      4. BLOCKED           — se nenhum método disponível

    TECH/FALLBACK (VIVT3):
      Mesmo fluxo que INDUSTRY — sem modelo separado em M016-S04.
      Marcado com is_tech_fallback=True e status=TECH_FALLBACK quando bloqueado.

    Parâmetros
    ----------
    inputs : IndustryValuationInputs
        Inputs do ticker. Nunca passados mockados.
    force_recalc : bool
        Se True, recalcula mesmo com valor existente. Default: False.
        WEGE3=40.16 só pode ser sobrescrito com force_recalc=True.

    Retorno
    -------
    IndustryValuationResult
        Resultado com fair_value calculado ou blocked=True se dados insuficientes.
    """
    ticker = inputs.ticker
    is_tech = inputs.is_tech_fallback

    # ── Passo 0: Verificar se deve preservar valor existente ──────────────────
    if not force_recalc and inputs.existing_fair_value is not None:
        logger.info(
            "ticker=%s: fair_value existente=%.2f preservado (force_recalc=False)",
            ticker, inputs.existing_fair_value,
        )
        return IndustryValuationResult.preserved_result(
            ticker=ticker,
            fair_value=inputs.existing_fair_value,
            market_price=inputs.market_price,
            valuation_date=inputs.existing_valuation_date,
            is_tech_fallback=is_tech,
            notes=(
                f"Valor existente preservado (force_recalc=False). "
                f"fair_value={inputs.existing_fair_value:.2f}, "
                f"source_quality={inputs.source_quality}."
            ),
        )

    # ── Passo 1: Validar shares_outstanding e net_debt ────────────────────────
    common_block = _validate_industry_shares_and_net_debt(inputs)

    # ── Passo 2: Tentar DCF/FCFF ──────────────────────────────────────────────
    dcf_block = _validate_industry_dcf_prerequisites(inputs)
    if common_block and not dcf_block:
        dcf_block = common_block

    if dcf_block is None:
        try:
            fair_value, ev, equity_v = _calculate_industry_dcf_fcff(inputs)

            if equity_v < 0:
                return IndustryValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"I-IND-03: equity_value={equity_v:.2f} < 0 via DCF → "
                        f"EV={ev:.2f}, net_debt={inputs.net_debt:.2f}."
                    ),
                    status=IndustryValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    is_tech_fallback=is_tech,
                    notes="Equity value negativo via DCF — revisar premissas.",
                )

            if fair_value <= 0:
                return IndustryValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=f"fair_value DCF={fair_value:.2f} ≤ 0 — resultado implausível.",
                    status=IndustryValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    is_tech_fallback=is_tech,
                )

            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            logger.info(
                "ticker=%s: DCF/FCFF — FCF=%.2f, WACC=%.4f, g=%.4f → "
                "EV=%.2f, equity=%.2f, fair_value=%.2f",
                ticker, inputs.free_cash_flow, inputs.wacc, inputs.terminal_growth,
                ev, equity_v, fair_value,
            )

            return IndustryValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=IndustryValuationMethod.DCF_FCFF,
                method_used=IndustryValuationMethod.DCF_FCFF,
                confidence=_confidence_from_quality_industry(inputs.source_quality),
                input_quality=inputs.source_quality,
                status=IndustryValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                is_tech_fallback=is_tech,
                upside_pct=upside,
                enterprise_value=ev,
                equity_value=equity_v,
                wacc_used=round(inputs.wacc, 4),
                terminal_growth_used=round(inputs.terminal_growth, 4),
                notes=(
                    f"DCF/FCFF: FCF=R${inputs.free_cash_flow:.0f}M, "
                    f"WACC={inputs.wacc:.2%}, g={inputs.terminal_growth:.2%} → "
                    f"EV=R${ev:.0f}M, equity=R${equity_v:.0f}M, "
                    f"fair_value=R${fair_value:.2f}"
                ),
            )

        except ZeroDivisionError:
            pass
        except Exception as exc:
            logger.error("ticker=%s: erro no cálculo DCF industry: %s", ticker, exc)

    # ── Passo 3: Tentar EV/EBITDA ─────────────────────────────────────────────
    ev_ebitda_block = _validate_industry_ev_ebitda_prerequisites(inputs)
    if common_block and not ev_ebitda_block:
        ev_ebitda_block = common_block

    if ev_ebitda_block is None:
        try:
            fair_value, ev, equity_v, multiple_used = _calculate_industry_ev_ebitda(inputs)

            if equity_v < 0:
                return IndustryValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"I-IND-03: equity_value={equity_v:.2f} < 0 via EV/EBITDA → "
                        f"EV={ev:.2f}, net_debt={inputs.net_debt:.2f}."
                    ),
                    status=IndustryValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    is_tech_fallback=is_tech,
                )

            if fair_value <= 0:
                return IndustryValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=f"fair_value EV/EBITDA={fair_value:.2f} ≤ 0 — implausível.",
                    status=IndustryValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    is_tech_fallback=is_tech,
                )

            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            confidence = _confidence_from_quality_industry(inputs.source_quality) * 0.85

            return IndustryValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=IndustryValuationMethod.EV_EBITDA,
                method_used=IndustryValuationMethod.EV_EBITDA,
                confidence=confidence,
                input_quality=inputs.source_quality,
                status=IndustryValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                is_tech_fallback=is_tech,
                upside_pct=upside,
                enterprise_value=ev,
                equity_value=equity_v,
                ev_ebitda_used=multiple_used,
                notes=(
                    f"EV/EBITDA: EBITDA=R${inputs.ebitda:.0f}M × {multiple_used:.1f}× → "
                    f"EV=R${ev:.0f}M, equity=R${equity_v:.0f}M, "
                    f"fair_value=R${fair_value:.2f}. "
                    f"DCF indisponível: {dcf_block}"
                ),
            )

        except ZeroDivisionError:
            pass
        except Exception as exc:
            logger.error("ticker=%s: erro no cálculo EV/EBITDA industry: %s", ticker, exc)

    # ── Passo 4: Sem método disponível — bloquear ─────────────────────────────
    # TECH/FALLBACK: status diferenciado para downstream
    final_status = (
        IndustryValuationStatus.TECH_FALLBACK
        if is_tech
        else IndustryValuationStatus.NEEDS_FINANCIALS
    )

    block_reasons = []
    if common_block:
        block_reasons.append(f"Dados comuns: {common_block}")
    if dcf_block:
        block_reasons.append(f"DCF bloqueado: {dcf_block}")
    if ev_ebitda_block:
        block_reasons.append(f"EV/EBITDA bloqueado: {ev_ebitda_block}")

    combined_reason = (
        " | ".join(block_reasons)
        if block_reasons
        else "Dados insuficientes para qualquer método de valuation industry"
    )

    tech_note = f" TECH/FALLBACK: {ticker} não tem modelo próprio em M016-S04." if is_tech else ""

    logger.warning("ticker=%s: sem método disponível — %s%s", ticker, combined_reason, tech_note)

    return IndustryValuationResult.blocked_result(
        ticker=ticker,
        block_reason=combined_reason + tech_note,
        status=final_status,
        input_quality=inputs.source_quality,
        is_tech_fallback=is_tech,
        notes=f"Nenhum método industry disponível. {combined_reason}{tech_note}",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Diagnóstico batch dos tickers INDUSTRY + TECH_FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def _load_existing_fair_value_industry(ticker: str) -> Optional[float]:
    """Tenta carregar fair_value existente para industry/tech.

    Fontes (por precedência):
      1. INDUSTRY_PRESERVED_FAIR_VALUES — WEGE3=40.16 hardcoded
      2. asset_intelligence_snapshots  — campo fair_value (se valuation_available=1)
      3. None se não encontrar
    """
    if ticker in INDUSTRY_PRESERVED_FAIR_VALUES:
        return INDUSTRY_PRESERVED_FAIR_VALUES[ticker]

    try:
        import sqlite3
        import os
        from pathlib import Path

        db_env = os.environ.get("SCANNER_QUANT_DB")
        db_path = db_env if db_env else "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"
        if not Path(db_path).exists():
            return None

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT fair_value, valuation_available FROM asset_intelligence_snapshots "
            "WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()

        if row and row[0] is not None and row[1]:
            return float(row[0])
    except Exception as exc:
        logger.debug("ticker=%s: falha ao carregar fair_value industry: %s", ticker, exc)

    return None


def _load_market_price_industry(ticker: str) -> Optional[float]:
    """Tenta carregar preço de mercado do banco SQLite."""
    try:
        import sqlite3
        import os
        from pathlib import Path

        db_env = os.environ.get("SCANNER_QUANT_DB")
        db_path = db_env if db_env else "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"
        if not Path(db_path).exists():
            return None

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT close FROM cotahist_daily WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        if row and row[0]:
            conn.close()
            return float(row[0])

        c.execute(
            "SELECT market_price FROM asset_intelligence_snapshots "
            "WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            return float(row[0])
    except Exception as exc:
        logger.debug("ticker=%s: falha ao carregar market_price industry: %s", ticker, exc)

    return None


def _count_ri_documents_industry(ticker: str) -> int:
    """Conta ri_documents para o ticker. Retorna 0 em caso de falha/ausência."""
    try:
        import sqlite3
        import os
        from pathlib import Path

        db_env = os.environ.get("SCANNER_QUANT_DB")
        db_path = db_env if db_env else "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"
        if not Path(db_path).exists():
            return 0

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ri_documents WHERE ticker=?", (ticker,))
        count = c.fetchone()[0]
        conn.close()
        return int(count)
    except Exception as exc:
        logger.debug("ticker=%s: falha ao contar ri_documents industry: %s", ticker, exc)
        return 0


def diagnose_industry_tickers(
    tickers: Optional[list[str]] = None,
    force_recalc: bool = False,
) -> dict[str, dict]:
    """Diagnóstico batch dos tickers INDUSTRY + TECH/FALLBACK.

    Para cada ticker, verifica:
      - ri_docs=0 → NEEDS_DATA (bloqueio absoluto)
      - fair_value existente → PRESERVE_EXISTING (WEGE3=40.16)
      - sem dados financeiros estruturados → NEEDS_FINANCIALS
      - TECH/FALLBACK (VIVT3) → status TECH_FALLBACK quando bloqueado

    Parâmetros
    ----------
    tickers : list[str] | None
        Lista de tickers. Se None, usa ALL_INDUSTRY_TICKERS completo.
    force_recalc : bool
        Se True, ignora preserved values e tenta recalcular com dados disponíveis.
        WEGE3=40.16 só recalculado se force_recalc=True.

    Retorno
    -------
    dict[str, dict]
        Mapeamento ticker → dict com:
          - status: IndustryValuationStatus
          - existing_fair_value: float | None
          - market_price: float | None
          - ri_docs: int
          - source_quality: IndustryInputQuality
          - result: IndustryValuationResult
    """
    target = [t.strip().upper() for t in (tickers or sorted(ALL_INDUSTRY_TICKERS))]
    output: dict[str, dict] = {}

    for ticker in target:
        logger.info("diagnose_industry_tickers: processando %s", ticker)
        is_tech = ticker in TECH_FALLBACK_TICKERS

        ri_docs = _count_ri_documents_industry(ticker)

        if ri_docs == 0:
            result = IndustryValuationResult.blocked_result(
                ticker=ticker,
                block_reason=(
                    f"NEEDS_DATA: ri_docs=0 para {ticker}. "
                    "Sem documentos RI no banco — valuation bloqueado."
                ),
                status=IndustryValuationStatus.NEEDS_DATA,
                input_quality=IndustryInputQuality.ABSENT,
                is_tech_fallback=is_tech,
                notes=f"ri_docs=0 → NEEDS_DATA. {ticker} permanece fora do valuation.",
            )
            output[ticker] = {
                "status": IndustryValuationStatus.NEEDS_DATA,
                "existing_fair_value": None,
                "market_price": _load_market_price_industry(ticker),
                "ri_docs": 0,
                "source_quality": IndustryInputQuality.ABSENT,
                "result": result,
            }
            continue

        existing_fv = _load_existing_fair_value_industry(ticker) if not force_recalc else None
        market_price = _load_market_price_industry(ticker)

        if ticker in INDUSTRY_PRESERVED_FAIR_VALUES:
            quality = IndustryInputQuality.EXCEL_PIPELINE
        elif existing_fv is not None:
            quality = IndustryInputQuality.EXCEL_PIPELINE
        else:
            quality = IndustryInputQuality.ABSENT

        # Subsector por ticker para múltiplo default
        subsector_map = {
            "FLRY3":  "healthcare",
            "HYPE3":  "pharma",
            "KLBN11": "pulp",
            "RADL3":  "pharmacy",
            "RAIL3":  "logistics",
            "RENT3":  "rental",
            "SUZB3":  "pulp",
            "VAMO3":  "rental",
            "WEGE3":  "industrial",
            "VIVT3":  "telecom",
        }

        inputs = IndustryValuationInputs(
            ticker=ticker,
            market_price=market_price,
            source_quality=quality,
            existing_fair_value=existing_fv,
            existing_valuation_date=None,
            subsector=subsector_map.get(ticker),
        )

        result = calculate_industry_valuation(inputs, force_recalc=force_recalc)

        if result.status == IndustryValuationStatus.PRESERVE_EXISTING:
            status = IndustryValuationStatus.PRESERVE_EXISTING
        elif result.blocked:
            status = (
                IndustryValuationStatus.TECH_FALLBACK
                if is_tech
                else IndustryValuationStatus.NEEDS_FINANCIALS
            )
        else:
            status = IndustryValuationStatus.VALUATION_READY

        output[ticker] = {
            "status": status,
            "existing_fair_value": existing_fv,
            "market_price": market_price,
            "ri_docs": ri_docs,
            "source_quality": quality,
            "result": result,
        }

        logger.info(
            "diagnose_industry_tickers: %s → status=%s, fv=%s, blocked=%s, ri_docs=%d",
            ticker, status, existing_fv, result.blocked, ri_docs,
        )

    return output


# ─────────────────────────────────────────────────────────────────────────────
#  Save seguro para resultados industry
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_industry_valuation_table(db_path: str) -> None:
    """Cria a tabela industry_valuation_results se não existir."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS industry_valuation_results (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at           TEXT    DEFAULT (datetime('now')),
            ticker               TEXT    NOT NULL,
            fair_value           REAL,
            upside_pct           REAL,
            valuation_method     TEXT,
            method_used          TEXT,
            confidence           REAL    DEFAULT 0.0,
            input_quality        TEXT,
            valuation_date       TEXT,
            enterprise_value     REAL,
            equity_value         REAL,
            ev_ebitda_used       REAL,
            wacc_used            REAL,
            terminal_growth_used REAL,
            is_tech_fallback     INTEGER DEFAULT 0,
            blocked              INTEGER DEFAULT 1,
            block_reason         TEXT,
            status               TEXT,
            notes                TEXT,
            force_recalc         INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_industry_valuation_result(
    ticker: str,
    result: IndustryValuationResult,
    db_path: Optional[str] = None,
    *,
    write: bool = False,
    force_recalc: bool = False,
    input_quality: Optional[str] = None,
    valuation_date: Optional[str] = None,
) -> bool:
    """Gravação segura de resultado de valuation industry.

    CONTRATO DE SEGURANÇA:
    - write=False por default — não escreve sem parâmetro explícito
    - force_recalc=False por default — preserva fair_value existente
    - WEGE3 (40.16) nunca é sobrescrito sem force_recalc=True
    - Escreve em industry_valuation_results (tabela separada)
    """
    import logging
    from datetime import date
    from pathlib import Path

    log = logging.getLogger(__name__)
    ticker_upper = str(ticker).strip().upper()

    if write and result.fair_value is None:
        log.warning(
            "save_industry_valuation_result: ticker=%s — resultado sem fair_value, write ignorado",
            ticker_upper,
        )
        return False

    if ticker_upper in INDUSTRY_PRESERVED_FAIR_VALUES and not force_recalc:
        preserved_fv = INDUSTRY_PRESERVED_FAIR_VALUES[ticker_upper]
        log.info(
            "save_industry_valuation_result: ticker=%s — preserved fair_value=%.2f protegido "
            "(force_recalc=False). Use force_recalc=True para sobrescrever.",
            ticker_upper, preserved_fv,
        )
        return False

    if not write:
        log.debug(
            "save_industry_valuation_result: ticker=%s — write=False, não gravado",
            ticker_upper,
        )
        return False

    if db_path is None:
        db_path = "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"

    effective_date = valuation_date or date.today().isoformat()

    try:
        _ensure_industry_valuation_table(db_path)
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO industry_valuation_results
                (ticker, fair_value, upside_pct, valuation_method, method_used,
                 confidence, input_quality, valuation_date, enterprise_value,
                 equity_value, ev_ebitda_used, wacc_used, terminal_growth_used,
                 is_tech_fallback, blocked, block_reason, status, notes, force_recalc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker_upper,
                result.fair_value,
                result.upside_pct,
                result.valuation_method,
                result.method_used,
                result.confidence,
                input_quality or result.input_quality,
                effective_date,
                result.enterprise_value,
                result.equity_value,
                result.ev_ebitda_used,
                result.wacc_used,
                result.terminal_growth_used,
                1 if result.is_tech_fallback else 0,
                0,
                None,
                result.status,
                result.notes,
                1 if force_recalc else 0,
            ),
        )
        conn.commit()
        conn.close()

        log.info(
            "save_industry_valuation_result: ticker=%s — gravado fair_value=%.2f, "
            "method=%s, date=%s",
            ticker_upper, result.fair_value, result.method_used, effective_date,
        )
        return True

    except Exception as exc:
        log.error(
            "save_industry_valuation_result: ticker=%s — erro ao gravar: %s",
            ticker_upper, exc,
        )
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "INDUSTRY_TICKERS",
    "TECH_FALLBACK_TICKERS",
    "ALL_INDUSTRY_TICKERS",
    "INDUSTRY_PRESERVED_FAIR_VALUES",
    "DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE",
    "INDUSTRY_EV_EBITDA_BY_SUBSECTOR",
    "IndustryValuationMethod",
    "IndustryInputQuality",
    "IndustryValuationStatus",
    "IndustryValuationInputs",
    "IndustryValuationResult",
    "_validate_industry_shares_and_net_debt",
    "_validate_industry_dcf_prerequisites",
    "_validate_industry_ev_ebitda_prerequisites",
    "calculate_industry_valuation",
    "diagnose_industry_tickers",
    "save_industry_valuation_result",
]
