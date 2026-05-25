"""
src/valuation/models/retail_model.py — Retail Valuation Model (M016-S04)

Modelo de valuation para varejo usando metodologia DCF/EV-EBITDA:
  - DCF/FCFF como método primário (Gordon Growth sobre FCF)
  - EV/EBITDA como método secundário (se EBITDA > 0)
  - Flag DISTRESSED quando EBITDA < 0 ou dados inconsistentes
  - Bloqueio total se dados insuficientes

Grupo RETAIL confirmado (M016-S01/S04):
  AZZA3  — Azzas (varejo moda, fusão Arezzo + Reserva)
  LREN3  — Lojas Renner (varejo moda, porte grande)
  MGLU3  — Magazine Luiza (varejo eletroeletrônicos, e-commerce)
  PCAR3  — GPA/Grupo Pão de Açúcar (alimentar, reestruturação)
  VIVA3  — Vivara (joalheria/varejo premium)

Diagnóstico de fontes (M016-S04):
  AZZA3:  market_price=20.72, fair_value=None, ri_docs=131 → NEEDS_FINANCIALS
  LREN3:  market_price=15.07, fair_value=None, ri_docs=130 → NEEDS_FINANCIALS
  MGLU3:  market_price=6.63,  fair_value=None, ri_docs=129 → NEEDS_FINANCIALS
  PCAR3:  market_price=2.08,  fair_value=None, ri_docs=126 → NEEDS_FINANCIALS
  VIVA3:  market_price=22.19, fair_value=None, ri_docs=132 → NEEDS_FINANCIALS

Regras HARD BLOCK (nunca produz fair_value se violadas):
  R-RETAIL-01: free_cash_flow ausente → DCF/FCFF bloqueado
  R-RETAIL-02: WACC <= terminal_growth → modelo DCF indefinido
  R-RETAIL-03: net_debt ausente → enterprise value indefinido
  R-RETAIL-04: shares_outstanding <= 0 → per-share indefinido
  R-RETAIL-05: ebitda <= 0 → EV/EBITDA múltiplo bloqueado

Flag DISTRESSED:
  - EBITDA < 0 → empresa com prejuízo operacional → EV/EBITDA bloqueado
  - Inconsistência: FCF negativo com EBITDA positivo (possível capital destrutivo)
  - Marcado no campo status como DISTRESSED para downstream processing

Regras de preservação:
  Nenhum valor preservado neste grupo (todos fair_value=None em M016-S04).

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

#: Tickers do grupo RETAIL confirmados pelo SectorNormalizer (M016-S01)
RETAIL_TICKERS: frozenset[str] = frozenset({
    "AZZA3",   # Azzas (moda/lifestyle)
    "LREN3",   # Lojas Renner (moda)
    "MGLU3",   # Magazine Luiza (eletro/e-commerce)
    "PCAR3",   # GPA — Grupo Pão de Açúcar (alimentar)
    "VIVA3",   # Vivara (joalheria premium)
})

#: Fair values existentes a preservar (só podem ser sobrescritos com force_recalc=True)
#: Vazio neste grupo — nenhum fair_value registrado em M016-S04
RETAIL_PRESERVED_FAIR_VALUES: dict[str, float] = {}

#: Múltiplo EV/EBITDA de referência para varejo brasileiro (consenso setorial)
DEFAULT_RETAIL_EV_EBITDA_MULTIPLE: float = 8.0

#: Múltiplos EV/EBITDA por subsector de varejo
RETAIL_EV_EBITDA_BY_SUBSECTOR: dict[str, float] = {
    "fashion":      9.0,   # Moda: LREN3, AZZA3 (branding/margem alta)
    "food":         7.0,   # Alimentar: PCAR3 (margem baixa, giro alto)
    "electronics":  6.5,   # Eletroeletrônicos: MGLU3 (e-commerce, margem apertada)
    "jewelry":     12.0,   # Joalheria premium: VIVA3 (margens altas, ticket médio)
    "premium":     11.0,   # Varejo premium genérico
}


class RetailValuationMethod:
    """Constantes de método para valuation de varejo."""
    DCF_FCFF      = "DCF_FCFF"          # DCF/FCFF (Gordon Growth) — primário
    EV_EBITDA     = "EV_EBITDA"         # Múltiplo EV/EBITDA — secundário
    PRESERVE      = "PRESERVE_EXISTING" # Preservar valor existente
    BLOCKED       = "BLOCKED"           # Sem método disponível


class RetailInputQuality:
    """Qualidade dos inputs de dados."""
    CVM_LIVE       = "CVM_LIVE"          # Dados ao vivo CVM / RI estruturado
    EXCEL_PIPELINE = "EXCEL_PIPELINE"    # Modelo Excel pipeline
    ESTIMATED      = "ESTIMATED"         # Estimativas derivadas
    ABSENT         = "ABSENT"            # Dados ausentes


class RetailValuationStatus:
    """Status do diagnóstico do ticker."""
    VALUATION_READY    = "VALUATION_READY"     # Dados suficientes para calcular
    PRESERVE_EXISTING  = "PRESERVE_EXISTING"   # Valor existente a preservar
    NEEDS_FINANCIALS   = "NEEDS_FINANCIALS"    # EBITDA/FCF ausentes no banco
    NEEDS_DATA         = "NEEDS_DATA"          # ri_docs=0 (bloqueio absoluto)
    DISTRESSED         = "DISTRESSED"          # EBITDA negativo ou inconsistência
    NEEDS_REVIEW       = "NEEDS_REVIEW"        # Dados presentes mas suspeitos


# ─────────────────────────────────────────────────────────────────────────────
#  Dataclasses de inputs e resultado
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RetailValuationInputs:
    """Inputs para valuation de varejo (fashion, food, electronics, etc.).

    Todos os campos opcionais — modelo bloqueia com block_reason se mínimos ausentes.
    Nunca usar valores mockados aqui.

    Campos
    ------
    ticker : str
        Código do ativo B3 (ex: "LREN3", "MGLU3").
    free_cash_flow : float | None
        FCF/FCFF anual — R$ milhões.
        R-RETAIL-01: bloqueia DCF/FCFF se ausente.
    ebitda : float | None
        EBITDA anual — R$ milhões.
        R-RETAIL-05: bloqueia EV/EBITDA se <= 0.
        Negativo → empresa DISTRESSED.
    net_debt : float | None
        Dívida líquida = dívida bruta − caixa — R$ milhões.
        R-RETAIL-03: bloqueia todos os métodos se ausente.
    shares_outstanding : float | None
        Número de ações em circulação — milhões de ações.
        R-RETAIL-04: bloqueia per-share se <= 0.
    wacc : float | None
        Custo médio ponderado de capital (decimal, ex: 0.13 = 13%).
        R-RETAIL-02: bloqueia DCF se None ou <= terminal_growth.
    terminal_growth : float | None
        Taxa de crescimento terminal g (decimal, ex: 0.04 = 4%).
        R-RETAIL-02: bloqueia DCF se WACC <= g.
    ev_ebitda_multiple : float | None
        Múltiplo EV/EBITDA de referência setorial.
        Se None, usa default por subsector ou DEFAULT_RETAIL_EV_EBITDA_MULTIPLE.
    market_price : float | None
        Preço de mercado atual (R$). Usado para calcular upside.
    source_quality : str
        Qualidade dos dados de origem (RetailInputQuality constants).
    existing_fair_value : float | None
        Fair value já registrado (para lógica PRESERVE).
    existing_valuation_date : str | None
        Data do valuation existente (ISO format, ex: "2026-04-16").
    subsector : str | None
        Subsector: "fashion", "food", "electronics", "jewelry", "premium".
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
    source_quality: str = RetailInputQuality.ABSENT
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
            for key, mult in RETAIL_EV_EBITDA_BY_SUBSECTOR.items():
                if key in sub_lower:
                    return mult
        return DEFAULT_RETAIL_EV_EBITDA_MULTIPLE

    @property
    def is_distressed(self) -> bool:
        """True se indicadores de distress (EBITDA negativo)."""
        return self.ebitda is not None and self.ebitda < 0

    @property
    def fcf_per_share(self) -> Optional[float]:
        """FCF por ação (R$)."""
        if (self.free_cash_flow is not None
                and self.shares_outstanding is not None
                and self.shares_outstanding > 0):
            return self.free_cash_flow / self.shares_outstanding
        return None


@dataclass
class RetailValuationResult:
    """Resultado de valuation para varejo.

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
        Status do diagnóstico (RetailValuationStatus constants).
    blocked : bool
        True se o cálculo foi bloqueado por dados insuficientes.
    block_reason : str | None
        Razão do bloqueio.
    distressed : bool
        True se empresa com EBITDA negativo ou indicadores de distress.
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
    input_quality: str = RetailInputQuality.ABSENT
    status: str = RetailValuationStatus.NEEDS_FINANCIALS
    blocked: bool = True
    block_reason: Optional[str] = None
    distressed: bool = False
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
        status: str = RetailValuationStatus.NEEDS_FINANCIALS,
        input_quality: str = RetailInputQuality.ABSENT,
        distressed: bool = False,
        notes: str = "",
    ) -> "RetailValuationResult":
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
            distressed=distressed,
            notes=notes,
        )

    @classmethod
    def preserved_result(
        cls,
        ticker: str,
        fair_value: float,
        market_price: Optional[float] = None,
        valuation_date: Optional[str] = None,
        notes: str = "",
    ) -> "RetailValuationResult":
        """Factory para resultado preservado (não recalculado)."""
        upside = None
        if market_price is not None and market_price > 0 and fair_value > 0:
            upside = round((fair_value / market_price - 1) * 100, 2)
        return cls(
            ticker=ticker,
            fair_value=fair_value,
            valuation_method=RetailValuationMethod.PRESERVE,
            method_used=RetailValuationMethod.PRESERVE,
            confidence=0.9,
            input_quality=RetailInputQuality.EXCEL_PIPELINE,
            status=RetailValuationStatus.PRESERVE_EXISTING,
            blocked=False,
            block_reason=None,
            distressed=False,
            upside_pct=upside,
            valuation_date=valuation_date or date.today().isoformat(),
            notes=notes or "Valor preservado. Use force_recalc=True para recalcular.",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Validações e hard blocks
# ─────────────────────────────────────────────────────────────────────────────

def _validate_retail_shares_and_net_debt(inputs: RetailValuationInputs) -> Optional[str]:
    """Validações comuns a todos os métodos retail.

    Hard blocks:
      R-RETAIL-03: net_debt ausente → EV indefinido
      R-RETAIL-04: shares_outstanding <= 0 → per-share indefinido
    """
    if inputs.net_debt is None:
        return (
            "R-RETAIL-03: net_debt ausente — não é possível calcular equity value. "
            "Forneça dívida líquida."
        )
    if inputs.shares_outstanding is None:
        return "R-RETAIL-04: shares_outstanding ausente — per-share indefinido"
    if inputs.shares_outstanding <= 0:
        return (
            f"R-RETAIL-04: shares_outstanding={inputs.shares_outstanding:.0f} ≤ 0 — inválido"
        )
    return None


def _validate_retail_dcf_prerequisites(inputs: RetailValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para DCF/FCFF retail.

    Hard blocks:
      R-RETAIL-01: free_cash_flow ausente
      R-RETAIL-02: WACC ausente ou WACC <= terminal_growth
    """
    if inputs.free_cash_flow is None:
        return "R-RETAIL-01: free_cash_flow ausente — DCF/FCFF indisponível"

    if inputs.wacc is None:
        return "R-RETAIL-02: wacc ausente — DCF/FCFF indisponível"
    if inputs.wacc <= 0:
        return f"R-RETAIL-02: wacc={inputs.wacc:.4f} ≤ 0 — inválido"

    if inputs.terminal_growth is None:
        return "R-RETAIL-02: terminal_growth ausente — DCF/FCFF indisponível"

    if inputs.wacc <= inputs.terminal_growth:
        return (
            f"R-RETAIL-02: HARD BLOCK — WACC={inputs.wacc:.4f} ≤ terminal_growth={inputs.terminal_growth:.4f}. "
            "Modelo DCF indefinido: divisor (WACC − g) ≤ 0. "
            "Ajuste as premissas."
        )

    if inputs.terminal_growth < -0.10:
        return (
            f"R-RETAIL-02: terminal_growth={inputs.terminal_growth:.4f} < −10% — improvável."
        )
    return None


def _validate_retail_ev_ebitda_prerequisites(inputs: RetailValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para EV/EBITDA retail.

    Hard blocks:
      R-RETAIL-05: EBITDA <= 0 → múltiplo inválido (inclui DISTRESSED)
    """
    if inputs.ebitda is None:
        return "R-RETAIL-05: ebitda ausente — EV/EBITDA indisponível"
    if inputs.ebitda <= 0:
        distressed_note = " Empresa DISTRESSED (prejuízo operacional)." if inputs.ebitda < 0 else ""
        return (
            f"R-RETAIL-05: HARD BLOCK — ebitda={inputs.ebitda:.2f} ≤ 0. "
            "EV/EBITDA múltiplo inválido para EBITDA não-positivo."
            + distressed_note
        )
    multiple = inputs.effective_ev_ebitda_multiple
    if multiple <= 0:
        return f"R-RETAIL-05: ev_ebitda_multiple={multiple:.2f} ≤ 0 — inválido"
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Motores de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_retail_dcf_fcff(inputs: RetailValuationInputs) -> tuple[float, float, float]:
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


def _calculate_retail_ev_ebitda(inputs: RetailValuationInputs) -> tuple[float, float, float, float]:
    """Calcula fair_value via EV/EBITDA."""
    ebitda = inputs.ebitda
    multiple = inputs.effective_ev_ebitda_multiple
    net_debt = inputs.net_debt
    shares = inputs.shares_outstanding

    enterprise_value = round(ebitda * multiple, 2)
    equity_value = round(enterprise_value - net_debt, 2)
    fair_value = round(equity_value / shares, 2)

    return fair_value, enterprise_value, equity_value, multiple


def _confidence_from_quality_retail(source_quality: str) -> float:
    """Deriva confiança a partir da qualidade dos inputs."""
    return {
        RetailInputQuality.CVM_LIVE:       0.90,
        RetailInputQuality.EXCEL_PIPELINE: 0.75,
        RetailInputQuality.ESTIMATED:      0.45,
        RetailInputQuality.ABSENT:         0.00,
    }.get(source_quality, 0.45)


# ─────────────────────────────────────────────────────────────────────────────
#  Motor principal de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def calculate_retail_valuation(
    inputs: RetailValuationInputs,
    force_recalc: bool = False,
) -> RetailValuationResult:
    """Calcula valuation para um ticker de varejo.

    Motor seguro — nunca inventa dados, nunca ignora hard blocks.

    Hierarquia de métodos:
      1. PRESERVE_EXISTING — se existing_fair_value preenchido E force_recalc=False
      2. DCF/FCFF          — se FCF, WACC, g, net_debt, shares disponíveis e WACC > g
      3. EV/EBITDA         — se EBITDA > 0, net_debt, shares disponíveis
      4. BLOCKED           — se nenhum método disponível
         (se EBITDA < 0: status=DISTRESSED em vez de NEEDS_FINANCIALS)

    Parâmetros
    ----------
    inputs : RetailValuationInputs
        Inputs do ticker. Nunca passados mockados.
    force_recalc : bool
        Se True, recalcula mesmo com valor existente. Default: False.

    Retorno
    -------
    RetailValuationResult
        Resultado com fair_value calculado ou blocked=True se dados insuficientes.
    """
    ticker = inputs.ticker
    is_distressed = inputs.is_distressed

    # ── Passo 0: Verificar se deve preservar valor existente ──────────────────
    if not force_recalc and inputs.existing_fair_value is not None:
        logger.info(
            "ticker=%s: fair_value existente=%.2f preservado (force_recalc=False)",
            ticker, inputs.existing_fair_value,
        )
        return RetailValuationResult.preserved_result(
            ticker=ticker,
            fair_value=inputs.existing_fair_value,
            market_price=inputs.market_price,
            valuation_date=inputs.existing_valuation_date,
            notes=(
                f"Valor existente preservado (force_recalc=False). "
                f"fair_value={inputs.existing_fair_value:.2f}, "
                f"source_quality={inputs.source_quality}."
            ),
        )

    # ── Passo 1: Validar shares_outstanding e net_debt ────────────────────────
    common_block = _validate_retail_shares_and_net_debt(inputs)

    # ── Passo 2: Tentar DCF/FCFF ──────────────────────────────────────────────
    dcf_block = _validate_retail_dcf_prerequisites(inputs)
    if common_block and not dcf_block:
        dcf_block = common_block

    if dcf_block is None:
        try:
            fair_value, ev, equity_v = _calculate_retail_dcf_fcff(inputs)

            if equity_v < 0:
                early_status = (
                    RetailValuationStatus.DISTRESSED
                    if is_distressed
                    else RetailValuationStatus.NEEDS_REVIEW
                )
                return RetailValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"R-RETAIL-03: equity_value={equity_v:.2f} < 0 via DCF → "
                        f"EV={ev:.2f}, net_debt={inputs.net_debt:.2f}."
                        + (" Empresa DISTRESSED (EBITDA < 0)." if is_distressed else "")
                    ),
                    status=early_status,
                    input_quality=inputs.source_quality,
                    distressed=is_distressed,
                    notes="Equity value negativo via DCF — revisar premissas.",
                )

            if fair_value <= 0:
                return RetailValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=f"fair_value DCF={fair_value:.2f} ≤ 0 — resultado implausível.",
                    status=RetailValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    distressed=is_distressed,
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

            return RetailValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=RetailValuationMethod.DCF_FCFF,
                method_used=RetailValuationMethod.DCF_FCFF,
                confidence=_confidence_from_quality_retail(inputs.source_quality),
                input_quality=inputs.source_quality,
                status=RetailValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                distressed=is_distressed,
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
            logger.error("ticker=%s: erro no cálculo DCF retail: %s", ticker, exc)

    # ── Passo 3: Tentar EV/EBITDA ─────────────────────────────────────────────
    ev_ebitda_block = _validate_retail_ev_ebitda_prerequisites(inputs)
    if common_block and not ev_ebitda_block:
        ev_ebitda_block = common_block

    if ev_ebitda_block is None:
        try:
            fair_value, ev, equity_v, multiple_used = _calculate_retail_ev_ebitda(inputs)

            if equity_v < 0:
                return RetailValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"R-RETAIL-03: equity_value={equity_v:.2f} < 0 via EV/EBITDA → "
                        f"EV={ev:.2f}, net_debt={inputs.net_debt:.2f}."
                    ),
                    status=RetailValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    distressed=is_distressed,
                )

            if fair_value <= 0:
                return RetailValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=f"fair_value EV/EBITDA={fair_value:.2f} ≤ 0 — implausível.",
                    status=RetailValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    distressed=is_distressed,
                )

            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            confidence = _confidence_from_quality_retail(inputs.source_quality) * 0.85

            return RetailValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=RetailValuationMethod.EV_EBITDA,
                method_used=RetailValuationMethod.EV_EBITDA,
                confidence=confidence,
                input_quality=inputs.source_quality,
                status=RetailValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                distressed=is_distressed,
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
            logger.error("ticker=%s: erro no cálculo EV/EBITDA retail: %s", ticker, exc)

    # ── Passo 4: Sem método disponível — bloquear ─────────────────────────────
    # Status DISTRESSED se EBITDA negativo (empresa em perda operacional)
    final_status = (
        RetailValuationStatus.DISTRESSED
        if is_distressed
        else RetailValuationStatus.NEEDS_FINANCIALS
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
        else "Dados insuficientes para qualquer método de valuation retail"
    )

    distressed_note = (
        f" EBITDA negativo detectado (DISTRESSED: {ticker})."
        if is_distressed else ""
    )

    logger.warning(
        "ticker=%s: sem método disponível — %s%s", ticker, combined_reason, distressed_note
    )

    return RetailValuationResult.blocked_result(
        ticker=ticker,
        block_reason=combined_reason + distressed_note,
        status=final_status,
        input_quality=inputs.source_quality,
        distressed=is_distressed,
        notes=f"Nenhum método retail disponível. {combined_reason}{distressed_note}",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Diagnóstico batch dos tickers RETAIL
# ─────────────────────────────────────────────────────────────────────────────

def _load_existing_fair_value_retail(ticker: str) -> Optional[float]:
    """Tenta carregar fair_value existente para varejo."""
    if ticker in RETAIL_PRESERVED_FAIR_VALUES:
        return RETAIL_PRESERVED_FAIR_VALUES[ticker]

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
        logger.debug("ticker=%s: falha ao carregar fair_value retail: %s", ticker, exc)

    return None


def _load_market_price_retail(ticker: str) -> Optional[float]:
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
        logger.debug("ticker=%s: falha ao carregar market_price retail: %s", ticker, exc)

    return None


def _count_ri_documents_retail(ticker: str) -> int:
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
        logger.debug("ticker=%s: falha ao contar ri_documents retail: %s", ticker, exc)
        return 0


def diagnose_retail_tickers(
    tickers: Optional[list[str]] = None,
    force_recalc: bool = False,
) -> dict[str, dict]:
    """Diagnóstico batch dos tickers RETAIL.

    Para cada ticker do grupo RETAIL, verifica:
      - ri_docs=0 → NEEDS_DATA (bloqueio absoluto)
      - fair_value existente → PRESERVE_EXISTING
      - sem dados financeiros estruturados → NEEDS_FINANCIALS
      - EBITDA negativo → DISTRESSED

    Parâmetros
    ----------
    tickers : list[str] | None
        Lista de tickers. Se None, usa RETAIL_TICKERS completo.
    force_recalc : bool
        Se True, ignora preserved values e tenta recalcular com dados disponíveis.

    Retorno
    -------
    dict[str, dict]
        Mapeamento ticker → dict com:
          - status: RetailValuationStatus
          - existing_fair_value: float | None
          - market_price: float | None
          - ri_docs: int
          - source_quality: RetailInputQuality
          - result: RetailValuationResult
    """
    target = [t.strip().upper() for t in (tickers or sorted(RETAIL_TICKERS))]
    output: dict[str, dict] = {}

    for ticker in target:
        logger.info("diagnose_retail_tickers: processando %s", ticker)

        ri_docs = _count_ri_documents_retail(ticker)

        if ri_docs == 0:
            result = RetailValuationResult.blocked_result(
                ticker=ticker,
                block_reason=(
                    f"NEEDS_DATA: ri_docs=0 para {ticker}. "
                    "Sem documentos RI no banco — valuation bloqueado."
                ),
                status=RetailValuationStatus.NEEDS_DATA,
                input_quality=RetailInputQuality.ABSENT,
                notes=f"ri_docs=0 → NEEDS_DATA. {ticker} permanece fora do valuation.",
            )
            output[ticker] = {
                "status": RetailValuationStatus.NEEDS_DATA,
                "existing_fair_value": None,
                "market_price": _load_market_price_retail(ticker),
                "ri_docs": 0,
                "source_quality": RetailInputQuality.ABSENT,
                "result": result,
            }
            continue

        existing_fv = _load_existing_fair_value_retail(ticker) if not force_recalc else None
        market_price = _load_market_price_retail(ticker)

        if ticker in RETAIL_PRESERVED_FAIR_VALUES:
            quality = RetailInputQuality.EXCEL_PIPELINE
        elif existing_fv is not None:
            quality = RetailInputQuality.EXCEL_PIPELINE
        else:
            quality = RetailInputQuality.ABSENT

        inputs = RetailValuationInputs(
            ticker=ticker,
            market_price=market_price,
            source_quality=quality,
            existing_fair_value=existing_fv,
            existing_valuation_date=None,
        )

        result = calculate_retail_valuation(inputs, force_recalc=force_recalc)

        if result.status == RetailValuationStatus.PRESERVE_EXISTING:
            status = RetailValuationStatus.PRESERVE_EXISTING
        elif result.blocked:
            status = (
                RetailValuationStatus.DISTRESSED
                if inputs.is_distressed
                else RetailValuationStatus.NEEDS_FINANCIALS
            )
        else:
            status = RetailValuationStatus.VALUATION_READY

        output[ticker] = {
            "status": status,
            "existing_fair_value": existing_fv,
            "market_price": market_price,
            "ri_docs": ri_docs,
            "source_quality": quality,
            "result": result,
        }

        logger.info(
            "diagnose_retail_tickers: %s → status=%s, fv=%s, blocked=%s, ri_docs=%d",
            ticker, status, existing_fv, result.blocked, ri_docs,
        )

    return output


# ─────────────────────────────────────────────────────────────────────────────
#  Save seguro para resultados retail
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_retail_valuation_table(db_path: str) -> None:
    """Cria a tabela retail_valuation_results se não existir."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retail_valuation_results (
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
            distressed           INTEGER DEFAULT 0,
            blocked              INTEGER DEFAULT 1,
            block_reason         TEXT,
            status               TEXT,
            notes                TEXT,
            force_recalc         INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_retail_valuation_result(
    ticker: str,
    result: RetailValuationResult,
    db_path: Optional[str] = None,
    *,
    write: bool = False,
    force_recalc: bool = False,
    input_quality: Optional[str] = None,
    valuation_date: Optional[str] = None,
) -> bool:
    """Gravação segura de resultado de valuation retail.

    CONTRATO DE SEGURANÇA:
    - write=False por default — não escreve sem parâmetro explícito
    - force_recalc=False por default — preserva fair_value existente
    - Escreve em retail_valuation_results (tabela separada)
    """
    import logging
    from datetime import date
    from pathlib import Path

    log = logging.getLogger(__name__)
    ticker_upper = str(ticker).strip().upper()

    if write and result.fair_value is None:
        log.warning(
            "save_retail_valuation_result: ticker=%s — resultado sem fair_value, write ignorado",
            ticker_upper,
        )
        return False

    if ticker_upper in RETAIL_PRESERVED_FAIR_VALUES and not force_recalc:
        preserved_fv = RETAIL_PRESERVED_FAIR_VALUES[ticker_upper]
        log.info(
            "save_retail_valuation_result: ticker=%s — preserved fair_value=%.2f protegido.",
            ticker_upper, preserved_fv,
        )
        return False

    if not write:
        log.debug(
            "save_retail_valuation_result: ticker=%s — write=False, não gravado",
            ticker_upper,
        )
        return False

    if db_path is None:
        db_path = "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"

    effective_date = valuation_date or date.today().isoformat()

    try:
        _ensure_retail_valuation_table(db_path)
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO retail_valuation_results
                (ticker, fair_value, upside_pct, valuation_method, method_used,
                 confidence, input_quality, valuation_date, enterprise_value,
                 equity_value, ev_ebitda_used, wacc_used, terminal_growth_used,
                 distressed, blocked, block_reason, status, notes, force_recalc)
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
                1 if result.distressed else 0,
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
            "save_retail_valuation_result: ticker=%s — gravado fair_value=%.2f, "
            "method=%s, date=%s",
            ticker_upper, result.fair_value, result.method_used, effective_date,
        )
        return True

    except Exception as exc:
        log.error(
            "save_retail_valuation_result: ticker=%s — erro ao gravar: %s",
            ticker_upper, exc,
        )
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "RETAIL_TICKERS",
    "RETAIL_PRESERVED_FAIR_VALUES",
    "DEFAULT_RETAIL_EV_EBITDA_MULTIPLE",
    "RETAIL_EV_EBITDA_BY_SUBSECTOR",
    "RetailValuationMethod",
    "RetailInputQuality",
    "RetailValuationStatus",
    "RetailValuationInputs",
    "RetailValuationResult",
    "_validate_retail_shares_and_net_debt",
    "_validate_retail_dcf_prerequisites",
    "_validate_retail_ev_ebitda_prerequisites",
    "calculate_retail_valuation",
    "diagnose_retail_tickers",
    "save_retail_valuation_result",
]
