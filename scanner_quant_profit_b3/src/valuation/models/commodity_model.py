"""
src/valuation/models/commodity_model.py — Commodity / Oil & Gas Valuation Model (M016-S03)

Modelo de valuation para commodities/oil & gas usando metodologia FCFF:
  - DCF/FCFF como método primário (se FCF, WACC, g, net_debt, shares disponíveis)
  - EV/EBITDA como método secundário (se EBITDA > 0, net_debt, shares disponíveis)
  - Bloqueio total se dados insuficientes para qualquer método

Grupo COMMODITY confirmado (M016-S01/S03):
  PETR4, PRIO3, RECV3 — Oil & Gas (sector=energy, subsector=oil_gas)
  VALE3               — Mineração (sector=materials, subsector=mining)
                        STATUS: permanece bloqueada por NEEDS_DATA (ri_docs=0)

Diagnóstico de fontes (M016-S03):
  PETR4: market_price=44.48, fair_value=81.12 (asset_intelligence_snapshots), ri_docs=131
         → PRESERVE_EXISTING (force_recalc=False por padrão)
  PRIO3: market_price=68.40, fair_value=None, ri_docs=109
         → NEEDS_FINANCIALS (sem EBITDA/FCF estruturado no DB)
  RECV3: market_price=12.31, fair_value=None, ri_docs=126
         → NEEDS_FINANCIALS (sem EBITDA/FCF estruturado no DB)
  VALE3: market_price=83.10, fair_value=None, ri_docs=0
         → NEEDS_DATA (zero RI docs — bloqueio absoluto, não entra no valuation)

Regras HARD BLOCK (nunca produz fair_value se violadas):
  D-COMM-01: free_cash_flow ausente → DCF/FCFF bloqueado
  D-COMM-02: WACC <= terminal_growth → modelo DCF indefinido (divisão por zero/negativo)
  D-COMM-03: net_debt ausente → enterprise value indefinido (bloqueia DCF e EV/EBITDA)
  D-COMM-04: shares_outstanding <= 0 → per-share indefinido
  D-COMM-05: ebitda <= 0 → EV/EBITDA múltiplo bloqueado

Regras de preservação:
  PETR4 = 81.12 → PRESERVE_EXISTING (não sobrescrever sem force_recalc=True)

Fórmulas utilizadas (inputs reais obrigatórios):
  DCF/FCFF simplificado (Gordon Growth sobre FCF):
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

#: Tickers do grupo COMMODITY confirmados pelo SectorNormalizer (M016-S01)
COMMODITY_TICKERS: frozenset[str] = frozenset({
    "PETR4",   # Petrobras PN — oil_gas
    "PRIO3",   # PetroRecôncavo — oil_gas
    "RECV3",   # Receita de Petróleo — oil_gas
    "VALE3",   # Vale — mining (bloqueada por NEEDS_DATA)
})

#: Tickers de Oil & Gas (elegíveis para valuation quando com dados)
OIL_GAS_TICKERS: frozenset[str] = frozenset({"PETR4", "PRIO3", "RECV3"})

#: Tickers de Mineração (elegíveis para valuation quando com dados)
MINING_TICKERS: frozenset[str] = frozenset({"VALE3"})

#: Fair values existentes a preservar (só podem ser sobrescritos com force_recalc=True)
#: PETR4=81.12 vem do campo fair_value em asset_intelligence_snapshots (M016-S03 diagnóstico)
COMMODITY_PRESERVED_FAIR_VALUES: dict[str, float] = {
    "PETR4": 81.12,
}

#: Múltiplo EV/EBITDA de referência para oil & gas brasileiro (consenso setorial)
#: Usado como default quando não fornecido explicitamente
DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE: float = 4.5   # conservador para E&P onshore/offshore

#: Múltiplo EV/EBITDA de referência para mineração
DEFAULT_MINING_EV_EBITDA_MULTIPLE: float = 5.0


class CommodityValuationMethod:
    """Constantes de método para valuation de commodities."""
    DCF_FCFF      = "DCF_FCFF"          # DCF/FCFF (Gordon Growth sobre FCF) — primário
    EV_EBITDA     = "EV_EBITDA"         # Múltiplo EV/EBITDA — secundário
    PRESERVE      = "PRESERVE_EXISTING" # Preservar valor existente
    BLOCKED       = "BLOCKED"           # Sem método disponível


class CommodityInputQuality:
    """Qualidade dos inputs de dados."""
    CVM_LIVE       = "CVM_LIVE"          # Dados ao vivo CVM / RI estruturado
    EXCEL_PIPELINE = "EXCEL_PIPELINE"    # Modelo Excel pipeline
    ESTIMATED      = "ESTIMATED"         # Estimativas derivadas
    ABSENT         = "ABSENT"            # Dados ausentes


class CommodityValuationStatus:
    """Status do diagnóstico do ticker."""
    VALUATION_READY    = "VALUATION_READY"     # Dados suficientes para calcular
    PRESERVE_EXISTING  = "PRESERVE_EXISTING"   # Valor existente a preservar
    NEEDS_FINANCIALS   = "NEEDS_FINANCIALS"    # EBITDA/FCF ausentes no banco
    NEEDS_DATA         = "NEEDS_DATA"          # ri_docs=0 (bloqueio absoluto)
    NEEDS_REVIEW       = "NEEDS_REVIEW"        # Dados presentes mas suspeitos


# ─────────────────────────────────────────────────────────────────────────────
#  Dataclasses de inputs e resultado
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CommodityValuationInputs:
    """Inputs para valuation de commodity/oil & gas.

    Todos os campos opcionais — modelo bloqueia com block_reason se mínimos ausentes.
    Nunca usar valores mockados aqui.

    Campos
    ------
    ticker : str
        Código do ativo B3 (ex: "PETR4", "PRIO3").
    free_cash_flow : float | None
        Fluxo de caixa livre (FCF / FCFF) anual — R$ milhões.
        D-COMM-01: bloqueia DCF/FCFF se ausente.
    ebitda : float | None
        EBITDA anual — R$ milhões.
        D-COMM-05: bloqueia EV/EBITDA se <= 0.
    net_debt : float | None
        Dívida líquida = dívida bruta − caixa — R$ milhões.
        D-COMM-03: bloqueia DCF e EV/EBITDA se ausente.
        Pode ser negativo (posição de caixa líquido).
    shares_outstanding : float | None
        Número de ações em circulação — milhões de ações.
        D-COMM-04: bloqueia per-share se <= 0.
    wacc : float | None
        Custo médio ponderado de capital (decimal, ex: 0.12 = 12%).
        D-COMM-02: bloqueia DCF se None ou <= terminal_growth.
    terminal_growth : float | None
        Taxa de crescimento terminal g (decimal, ex: 0.03 = 3%).
        D-COMM-02: bloqueia DCF se WACC <= g.
    ev_ebitda_multiple : float | None
        Múltiplo EV/EBITDA de referência setorial.
        Se None, usa DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE ou DEFAULT_MINING_EV_EBITDA_MULTIPLE.
    market_price : float | None
        Preço de mercado atual (R$). Usado para calcular upside.
    source_quality : str
        Qualidade dos dados de origem (CommodityInputQuality constants).
    existing_fair_value : float | None
        Fair value já registrado (para lógica PRESERVE).
    existing_valuation_date : str | None
        Data do valuation existente (ISO format, ex: "2026-04-16").
    subsector : str | None
        Subsector: "oil_gas" ou "mining". Usado para default de múltiplo.
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
    source_quality: str = CommodityInputQuality.ABSENT
    existing_fair_value: Optional[float] = None
    existing_valuation_date: Optional[str] = None
    subsector: Optional[str] = None

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker).strip().upper()

    @property
    def effective_ev_ebitda_multiple(self) -> float:
        """Múltiplo EV/EBITDA efetivo — explícito ou default setorial."""
        if self.ev_ebitda_multiple is not None and self.ev_ebitda_multiple > 0:
            return self.ev_ebitda_multiple
        if self.subsector and "mining" in self.subsector.lower():
            return DEFAULT_MINING_EV_EBITDA_MULTIPLE
        return DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE

    @property
    def fcf_per_share(self) -> Optional[float]:
        """FCF por ação (R$)."""
        if (self.free_cash_flow is not None
                and self.shares_outstanding is not None
                and self.shares_outstanding > 0):
            return self.free_cash_flow / self.shares_outstanding
        return None

    @property
    def ebitda_per_share(self) -> Optional[float]:
        """EBITDA por ação (R$)."""
        if (self.ebitda is not None
                and self.shares_outstanding is not None
                and self.shares_outstanding > 0):
            return self.ebitda / self.shares_outstanding
        return None


@dataclass
class CommodityValuationResult:
    """Resultado de valuation para commodity/oil & gas.

    Campos
    ------
    ticker : str
        Código do ativo B3.
    fair_value : float | None
        Preço-alvo calculado (R$). None se bloqueado ou sem dados.
    valuation_method : str | None
        Método principal utilizado (CommodityValuationMethod constants).
    method_used : str | None
        Método que efetivamente produziu o fair_value.
    confidence : float
        Confiança do resultado (0.0 a 1.0). 0.0 se bloqueado.
    input_quality : str
        Qualidade dos inputs utilizados (CommodityInputQuality constants).
    status : str
        Status do diagnóstico (CommodityValuationStatus constants).
    blocked : bool
        True se o cálculo foi bloqueado por dados insuficientes.
    block_reason : str | None
        Razão do bloqueio (se blocked=True).
    upside_pct : float | None
        Upside potencial em relação ao preço de mercado (%).
    valuation_date : str
        Data de referência do valuation (ISO format).
    enterprise_value : float | None
        Enterprise value calculado (R$ milhões).
    equity_value : float | None
        Equity value = EV - net_debt (R$ milhões).
    ev_ebitda_used : float | None
        Múltiplo EV/EBITDA utilizado no cálculo.
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
    input_quality: str = CommodityInputQuality.ABSENT
    status: str = CommodityValuationStatus.NEEDS_FINANCIALS
    blocked: bool = True
    block_reason: Optional[str] = None
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
        # Integridade: bloqueado com confiança > 0 é inconsistente
        if self.blocked and self.confidence > 0:
            self.confidence = 0.0

    @classmethod
    def blocked_result(
        cls,
        ticker: str,
        block_reason: str,
        status: str = CommodityValuationStatus.NEEDS_FINANCIALS,
        input_quality: str = CommodityInputQuality.ABSENT,
        notes: str = "",
    ) -> "CommodityValuationResult":
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
    ) -> "CommodityValuationResult":
        """Factory para resultado preservado (não recalculado)."""
        upside = None
        if market_price is not None and market_price > 0 and fair_value > 0:
            upside = round((fair_value / market_price - 1) * 100, 2)
        return cls(
            ticker=ticker,
            fair_value=fair_value,
            valuation_method=CommodityValuationMethod.PRESERVE,
            method_used=CommodityValuationMethod.PRESERVE,
            confidence=0.9,  # alta confiança em valores preservados
            input_quality=CommodityInputQuality.EXCEL_PIPELINE,
            status=CommodityValuationStatus.PRESERVE_EXISTING,
            blocked=False,
            block_reason=None,
            upside_pct=upside,
            valuation_date=valuation_date or date.today().isoformat(),
            notes=notes or "Valor preservado. Use force_recalc=True para recalcular.",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Validações e hard blocks
# ─────────────────────────────────────────────────────────────────────────────

def _validate_shares_and_net_debt(inputs: CommodityValuationInputs) -> Optional[str]:
    """Validações comuns a DCF e EV/EBITDA.

    Hard blocks:
      D-COMM-03: net_debt ausente → EV → equity indefinido
      D-COMM-04: shares_outstanding <= 0 → per-share indefinido
    """
    # D-COMM-03: net_debt
    if inputs.net_debt is None:
        return (
            "D-COMM-03: net_debt ausente — não é possível calcular equity value "
            "(enterprise_value - net_debt = equity_value). Forneça dívida líquida."
        )

    # D-COMM-04: shares_outstanding
    if inputs.shares_outstanding is None:
        return "D-COMM-04: shares_outstanding ausente — per-share indefinido"
    if inputs.shares_outstanding <= 0:
        return (
            f"D-COMM-04: shares_outstanding={inputs.shares_outstanding:.0f} ≤ 0 — inválido"
        )

    return None  # nenhum bloqueio


def _validate_dcf_prerequisites(inputs: CommodityValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para DCF/FCFF.

    Hard blocks adicionais (além de shares/net_debt):
      D-COMM-01: free_cash_flow ausente
      D-COMM-02: WACC ausente ou WACC <= terminal_growth
    """
    # D-COMM-01: FCF
    if inputs.free_cash_flow is None:
        return "D-COMM-01: free_cash_flow ausente — DCF/FCFF indisponível"

    # D-COMM-02: WACC
    if inputs.wacc is None:
        return "D-COMM-02: wacc ausente — DCF/FCFF indisponível"
    if inputs.wacc <= 0:
        return f"D-COMM-02: wacc={inputs.wacc:.4f} ≤ 0 — inválido"

    if inputs.terminal_growth is None:
        return "D-COMM-02: terminal_growth ausente — DCF/FCFF indisponível"

    # D-COMM-02: WACC <= g → HARD BLOCK (Gordon growth undefined)
    if inputs.wacc <= inputs.terminal_growth:
        return (
            f"D-COMM-02: HARD BLOCK — WACC={inputs.wacc:.4f} ≤ terminal_growth={inputs.terminal_growth:.4f}. "
            "Modelo DCF indefinido: divisor (WACC − g) ≤ 0. "
            "Ajuste as premissas (WACC deve superar o crescimento terminal)."
        )

    # Validação de razoabilidade: terminal_growth negativo é possível (deflação) mas incomum
    if inputs.terminal_growth < -0.10:
        return (
            f"D-COMM-02: terminal_growth={inputs.terminal_growth:.4f} < −10% — improvável. "
            "Verifique as premissas de crescimento."
        )

    return None


def _validate_ev_ebitda_prerequisites(inputs: CommodityValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para EV/EBITDA.

    Hard blocks adicionais (além de shares/net_debt):
      D-COMM-05: EBITDA <= 0 → múltiplo inválido
    """
    if inputs.ebitda is None:
        return "D-COMM-05: ebitda ausente — EV/EBITDA indisponível"
    if inputs.ebitda <= 0:
        return (
            f"D-COMM-05: HARD BLOCK — ebitda={inputs.ebitda:.2f} ≤ 0. "
            "EV/EBITDA múltiplo inválido para EBITDA não-positivo. "
            "Empresa com EBITDA negativo/zero requer método DCF ou está em loss."
        )

    # Múltiplo deve ser positivo
    multiple = inputs.effective_ev_ebitda_multiple
    if multiple <= 0:
        return f"D-COMM-05: ev_ebitda_multiple={multiple:.2f} ≤ 0 — inválido"

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Motores de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_dcf_fcff(inputs: CommodityValuationInputs) -> tuple[float, float, float]:
    """Calcula fair_value via DCF/FCFF (Gordon Growth sobre FCF).

    Fórmula:
      enterprise_value = FCF / (WACC - g)
      equity_value     = enterprise_value - net_debt
      fair_value       = equity_value / shares_outstanding

    Retorna (fair_value, enterprise_value, equity_value).
    Pré-condição: sem hard blocks de DCF, sem bloqueio de shares/net_debt.
    """
    fcf = inputs.free_cash_flow
    wacc = inputs.wacc
    g = inputs.terminal_growth
    net_debt = inputs.net_debt
    shares = inputs.shares_outstanding

    enterprise_value = round(fcf / (wacc - g), 2)
    equity_value = round(enterprise_value - net_debt, 2)
    fair_value = round(equity_value / shares, 2)

    return fair_value, enterprise_value, equity_value


def _calculate_ev_ebitda(inputs: CommodityValuationInputs) -> tuple[float, float, float, float]:
    """Calcula fair_value via EV/EBITDA.

    Fórmula:
      enterprise_value = EBITDA × EV/EBITDA multiple
      equity_value     = enterprise_value - net_debt
      fair_value       = equity_value / shares_outstanding

    Retorna (fair_value, enterprise_value, equity_value, multiple_used).
    Pré-condição: sem hard blocks de EV/EBITDA, sem bloqueio de shares/net_debt.
    """
    ebitda = inputs.ebitda
    multiple = inputs.effective_ev_ebitda_multiple
    net_debt = inputs.net_debt
    shares = inputs.shares_outstanding

    enterprise_value = round(ebitda * multiple, 2)
    equity_value = round(enterprise_value - net_debt, 2)
    fair_value = round(equity_value / shares, 2)

    return fair_value, enterprise_value, equity_value, multiple


def _confidence_from_quality(source_quality: str) -> float:
    """Deriva confiança a partir da qualidade dos inputs."""
    return {
        CommodityInputQuality.CVM_LIVE:       0.90,
        CommodityInputQuality.EXCEL_PIPELINE: 0.75,
        CommodityInputQuality.ESTIMATED:      0.45,
        CommodityInputQuality.ABSENT:         0.00,
    }.get(source_quality, 0.45)


# ─────────────────────────────────────────────────────────────────────────────
#  Motor principal de cálculo
# ─────────────────────────────────────────────────────────────────────────────

def calculate_commodity_valuation(
    inputs: CommodityValuationInputs,
    force_recalc: bool = False,
) -> CommodityValuationResult:
    """Calcula valuation para um ticker de commodity.

    Motor seguro — nunca inventa dados, nunca ignora hard blocks.

    Hierarquia de métodos:
      1. PRESERVE_EXISTING — se existing_fair_value preenchido E force_recalc=False
      2. DCF/FCFF          — se FCF, WACC, g, net_debt, shares disponíveis e WACC > g
      3. EV/EBITDA         — se EBITDA > 0, net_debt, shares disponíveis
      4. BLOCKED           — se nenhum método disponível

    Parâmetros
    ----------
    inputs : CommodityValuationInputs
        Inputs do ticker. Nunca passados mockados.
    force_recalc : bool
        Se True, recalcula mesmo com valor existente. Default: False.

    Retorno
    -------
    CommodityValuationResult
        Resultado com fair_value calculado ou blocked=True se dados insuficientes.
    """
    ticker = inputs.ticker

    # ── Passo 0: Verificar se deve preservar valor existente ──────────────────
    if not force_recalc and inputs.existing_fair_value is not None:
        logger.info(
            "ticker=%s: fair_value existente=%.2f preservado (force_recalc=False)",
            ticker, inputs.existing_fair_value,
        )
        return CommodityValuationResult.preserved_result(
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

    # ── Passo 1: Validar shares_outstanding e net_debt (comum a todos os métodos) ─
    common_block = _validate_shares_and_net_debt(inputs)
    # Não bloqueamos aqui — deixamos os métodos individuais reportar seus bloqueios específicos.
    # Mas se ambos ausentes, ambos métodos falharão: capturamos no final.

    # ── Passo 2: Tentar DCF/FCFF ─────────────────────────────────────────────
    dcf_block = _validate_dcf_prerequisites(inputs)
    if common_block:
        # shares/net_debt ausentes → DCF não pode avançar
        dcf_block = common_block if not dcf_block else dcf_block

    if dcf_block is None:
        try:
            fair_value, ev, equity_v = _calculate_dcf_fcff(inputs)

            # Sanity check: equity value negativo → empresa insolvente → NEEDS_REVIEW
            if equity_v < 0:
                return CommodityValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"D-COMM-03: equity_value={equity_v:.2f} < 0 → empresa insolvente "
                        f"(EV={ev:.2f}, net_debt={inputs.net_debt:.2f}). "
                        "Verifique nível de endividamento."
                    ),
                    status=CommodityValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    notes="Equity value negativo: net_debt excede EV — revisar premissas.",
                )

            # Sanity check: fair_value <= 0
            if fair_value <= 0:
                return CommodityValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"fair_value DCF={fair_value:.2f} ≤ 0 — resultado implausível. "
                        "Verifique FCF, WACC e dívida líquida."
                    ),
                    status=CommodityValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    notes="Fair value não-positivo via DCF — revisar inputs.",
                )

            # Calcular upside
            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            logger.info(
                "ticker=%s: DCF/FCFF — FCF=%.2f, WACC=%.4f, g=%.4f → EV=%.2f, "
                "equity=%.2f, fair_value=%.2f",
                ticker,
                inputs.free_cash_flow, inputs.wacc, inputs.terminal_growth,
                ev, equity_v, fair_value,
            )

            return CommodityValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=CommodityValuationMethod.DCF_FCFF,
                method_used=CommodityValuationMethod.DCF_FCFF,
                confidence=_confidence_from_quality(inputs.source_quality),
                input_quality=inputs.source_quality,
                status=CommodityValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
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
            # WACC == g já bloqueado antes — captura defensiva
            pass
        except Exception as exc:
            logger.error("ticker=%s: erro no cálculo DCF: %s", ticker, exc)

    # ── Passo 3: Tentar EV/EBITDA ────────────────────────────────────────────
    ev_ebitda_block = _validate_ev_ebitda_prerequisites(inputs)
    if common_block:
        ev_ebitda_block = common_block if not ev_ebitda_block else ev_ebitda_block

    if ev_ebitda_block is None:
        try:
            fair_value, ev, equity_v, multiple_used = _calculate_ev_ebitda(inputs)

            # Sanity check: equity value negativo
            if equity_v < 0:
                return CommodityValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"D-COMM-03: equity_value={equity_v:.2f} < 0 (EV/EBITDA) → "
                        f"EV={ev:.2f}, net_debt={inputs.net_debt:.2f}. "
                        "Endividamento excede valor da empresa."
                    ),
                    status=CommodityValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    notes="Equity value negativo via EV/EBITDA — revisar dívida líquida.",
                )

            if fair_value <= 0:
                return CommodityValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"fair_value EV/EBITDA={fair_value:.2f} ≤ 0 — resultado implausível."
                    ),
                    status=CommodityValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    notes="Fair value não-positivo via EV/EBITDA — revisar inputs.",
                )

            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            logger.info(
                "ticker=%s: EV/EBITDA — EBITDA=%.2f × %.2f → EV=%.2f, "
                "equity=%.2f, fair_value=%.2f",
                ticker, inputs.ebitda, multiple_used, ev, equity_v, fair_value,
            )

            # Confiança reduzida para EV/EBITDA (método secundário)
            confidence = _confidence_from_quality(inputs.source_quality) * 0.85

            return CommodityValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=CommodityValuationMethod.EV_EBITDA,
                method_used=CommodityValuationMethod.EV_EBITDA,
                confidence=confidence,
                input_quality=inputs.source_quality,
                status=CommodityValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
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
            logger.error("ticker=%s: erro no cálculo EV/EBITDA: %s", ticker, exc)

    # ── Passo 4: Sem método disponível — bloquear ─────────────────────────────
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
        else "Dados insuficientes para qualquer método de valuation commodity"
    )

    logger.warning("ticker=%s: sem método disponível — %s", ticker, combined_reason)

    return CommodityValuationResult.blocked_result(
        ticker=ticker,
        block_reason=combined_reason,
        status=CommodityValuationStatus.NEEDS_FINANCIALS,
        input_quality=inputs.source_quality,
        notes=f"Nenhum método commodity disponível. {combined_reason}",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Diagnóstico batch dos tickers COMMODITY
# ─────────────────────────────────────────────────────────────────────────────

def _load_existing_fair_value_commodity(ticker: str) -> Optional[float]:
    """Tenta carregar fair_value existente via preserved values + asset_intelligence_snapshots.

    Fontes (por precedência):
      1. COMMODITY_PRESERVED_FAIR_VALUES — PETR4=81.12 hardcoded
      2. asset_intelligence_snapshots    — campo fair_value (se valuation_available=1)
      3. None se não encontrar

    Não lança exceção — retorna None em caso de falha.
    """
    # Fonte 1: fair values preservados explicitamente
    if ticker in COMMODITY_PRESERVED_FAIR_VALUES:
        return COMMODITY_PRESERVED_FAIR_VALUES[ticker]

    # Fonte 2: asset_intelligence_snapshots
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
            """SELECT fair_value, valuation_available
               FROM asset_intelligence_snapshots
               WHERE ticker=?
               ORDER BY id DESC LIMIT 1""",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()

        if row and row[0] is not None and row[1]:
            return float(row[0])
    except Exception as exc:
        logger.debug("ticker=%s: falha ao carregar fair_value do snapshots: %s", ticker, exc)

    return None


def _load_market_price_commodity(ticker: str) -> Optional[float]:
    """Tenta carregar preço de mercado do banco SQLite.

    Fontes: cotahist_daily → asset_intelligence_snapshots.
    Retorna None se não encontrar.
    """
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

        # Tenta cotahist_daily
        c.execute(
            "SELECT close FROM cotahist_daily WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        if row and row[0]:
            conn.close()
            return float(row[0])

        # Tenta asset_intelligence_snapshots
        c.execute(
            "SELECT market_price FROM asset_intelligence_snapshots WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,),
        )
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            return float(row[0])
    except Exception as exc:
        logger.debug("ticker=%s: falha ao carregar market_price: %s", ticker, exc)

    return None


def _count_ri_documents(ticker: str) -> int:
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
        logger.debug("ticker=%s: falha ao contar ri_documents: %s", ticker, exc)
        return 0


def diagnose_commodity_tickers(
    tickers: Optional[list[str]] = None,
    force_recalc: bool = False,
) -> dict[str, dict]:
    """Diagnóstico batch dos tickers COMMODITY.

    Para cada ticker do grupo COMMODITY, verifica:
      - ri_docs=0 → NEEDS_DATA (VALE3: bloqueio absoluto)
      - fair_value existente → PRESERVE_EXISTING (PETR4)
      - sem dados financeiros estruturados → NEEDS_FINANCIALS (PRIO3, RECV3)

    Não calcula fair_value novo — somente diagnostica e preserva existentes.
    Não libera VALE3 enquanto ri_docs=0.

    Parâmetros
    ----------
    tickers : list[str] | None
        Lista de tickers. Se None, usa COMMODITY_TICKERS completo.
    force_recalc : bool
        Se True, ignora preserved values e tenta recalcular com dados disponíveis.
        Uso: apenas para testes ou recalibração explícita.

    Retorno
    -------
    dict[str, dict]
        Mapeamento ticker → dict com:
          - status: CommodityValuationStatus
          - existing_fair_value: float | None
          - market_price: float | None
          - ri_docs: int
          - source_quality: CommodityInputQuality
          - result: CommodityValuationResult
    """
    target = [t.strip().upper() for t in (tickers or sorted(COMMODITY_TICKERS))]
    output: dict[str, dict] = {}

    for ticker in target:
        logger.info("diagnose_commodity_tickers: processando %s", ticker)

        # Contar RI docs
        ri_docs = _count_ri_documents(ticker)

        # ── VALE3 e qualquer ticker sem RI docs → NEEDS_DATA absoluto ────────
        if ri_docs == 0:
            result = CommodityValuationResult.blocked_result(
                ticker=ticker,
                block_reason=(
                    f"NEEDS_DATA: ri_docs=0 para {ticker}. "
                    "Sem documentos RI no banco — valuation bloqueado. "
                    "Execute CVM ingestion para liberar este ticker."
                ),
                status=CommodityValuationStatus.NEEDS_DATA,
                input_quality=CommodityInputQuality.ABSENT,
                notes=f"ri_docs=0 → NEEDS_DATA. {ticker} permanece fora do valuation principal.",
            )
            output[ticker] = {
                "status": CommodityValuationStatus.NEEDS_DATA,
                "existing_fair_value": None,
                "market_price": _load_market_price_commodity(ticker),
                "ri_docs": 0,
                "source_quality": CommodityInputQuality.ABSENT,
                "result": result,
            }
            logger.info(
                "diagnose_commodity_tickers: %s → NEEDS_DATA (ri_docs=0)",
                ticker,
            )
            continue

        # ── Tickers com RI docs — verificar fair_value existente ──────────────
        existing_fv = _load_existing_fair_value_commodity(ticker) if not force_recalc else None
        market_price = _load_market_price_commodity(ticker)

        # Qualidade da fonte
        if ticker in COMMODITY_PRESERVED_FAIR_VALUES:
            quality = CommodityInputQuality.EXCEL_PIPELINE
        elif existing_fv is not None:
            quality = CommodityInputQuality.EXCEL_PIPELINE
        else:
            quality = CommodityInputQuality.ABSENT

        # Construir inputs mínimos para diagnóstico
        inputs = CommodityValuationInputs(
            ticker=ticker,
            market_price=market_price,
            source_quality=quality,
            existing_fair_value=existing_fv,
            existing_valuation_date=None,
        )

        # Calcular resultado (preservar ou bloquear)
        result = calculate_commodity_valuation(inputs, force_recalc=force_recalc)

        # Determinar status
        if result.status == CommodityValuationStatus.PRESERVE_EXISTING:
            status = CommodityValuationStatus.PRESERVE_EXISTING
        elif result.blocked:
            status = CommodityValuationStatus.NEEDS_FINANCIALS
        else:
            status = CommodityValuationStatus.VALUATION_READY

        output[ticker] = {
            "status": status,
            "existing_fair_value": existing_fv,
            "market_price": market_price,
            "ri_docs": ri_docs,
            "source_quality": quality,
            "result": result,
        }

        logger.info(
            "diagnose_commodity_tickers: %s → status=%s, fv=%s, blocked=%s, ri_docs=%d",
            ticker, status, existing_fv, result.blocked, ri_docs,
        )

    return output


# ─────────────────────────────────────────────────────────────────────────────
#  Save seguro para resultados commodity
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_commodity_valuation_table(db_path: str) -> None:
    """Cria a tabela commodity_valuation_results se não existir."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commodity_valuation_results (
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
            blocked              INTEGER DEFAULT 1,
            block_reason         TEXT,
            status               TEXT,
            notes                TEXT,
            force_recalc         INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_commodity_valuation_result(
    ticker: str,
    result: CommodityValuationResult,
    db_path: Optional[str] = None,
    *,
    write: bool = False,
    force_recalc: bool = False,
    input_quality: Optional[str] = None,
    valuation_date: Optional[str] = None,
) -> bool:
    """Gravação segura de resultado de valuation commodity.

    CONTRATO DE SEGURANÇA:
    - write=False por default — não escreve sem parâmetro explícito
    - force_recalc=False por default — preserva fair_value existente
    - PETR4 (81.12) nunca é sobrescrito sem force_recalc=True
    - Escreve em commodity_valuation_results (tabela separada)

    Parâmetros
    ----------
    ticker: str
        Código do ativo B3.
    result: CommodityValuationResult
        Resultado a salvar.
    db_path: str | None
        Caminho do banco. Usa data/database/scanner_quant.db se None.
    write: bool
        Se True, efetua a gravação. Default: False (apenas valida).
    force_recalc: bool
        Se True, permite sobrescrever fair_value existente (incluindo PETR4=81.12).
    input_quality: str | None
        Qualidade dos inputs (para registro de auditoria).
    valuation_date: str | None
        Data de referência (ISO format). Default: hoje.

    Retorno
    -------
    bool
        True se gravado com sucesso. False se write=False, bloqueado ou erro.
    """
    import logging
    from datetime import date
    from pathlib import Path

    log = logging.getLogger(__name__)
    ticker_upper = str(ticker).strip().upper()

    # ── Validação: resultado deve ter fair_value se write=True ──────────────
    if write and result.fair_value is None:
        log.warning(
            "save_commodity_valuation_result: ticker=%s — resultado sem fair_value, write ignorado",
            ticker_upper,
        )
        return False

    # ── Proteção PETR4: não sobrescrever sem force_recalc ───────────────────
    if ticker_upper in COMMODITY_PRESERVED_FAIR_VALUES and not force_recalc:
        preserved_fv = COMMODITY_PRESERVED_FAIR_VALUES[ticker_upper]
        log.info(
            "save_commodity_valuation_result: ticker=%s — preserved fair_value=%.2f protegido "
            "(force_recalc=False). Use force_recalc=True para sobrescrever.",
            ticker_upper,
            preserved_fv,
        )
        return False

    # ── write=False → apenas validação ────────────────────────────────────
    if not write:
        log.debug(
            "save_commodity_valuation_result: ticker=%s — write=False, validado mas não gravado",
            ticker_upper,
        )
        return False

    # ── Escrita no banco ─────────────────────────────────────────────────────
    if db_path is None:
        db_path = "data/database/scanner_quant.db"
        if not Path(db_path).exists():
            db_path = "scanner_quant.db"

    effective_date = valuation_date or date.today().isoformat()

    try:
        _ensure_commodity_valuation_table(db_path)
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO commodity_valuation_results
                (ticker, fair_value, upside_pct, valuation_method, method_used,
                 confidence, input_quality, valuation_date, enterprise_value,
                 equity_value, ev_ebitda_used, wacc_used, terminal_growth_used,
                 blocked, block_reason, status, notes, force_recalc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                0,  # blocked=False (fair_value não é None)
                None,
                result.status,
                result.notes,
                1 if force_recalc else 0,
            ),
        )
        conn.commit()
        conn.close()

        log.info(
            "save_commodity_valuation_result: ticker=%s — gravado fair_value=%.2f, "
            "method=%s, date=%s",
            ticker_upper,
            result.fair_value,
            result.method_used,
            effective_date,
        )
        return True

    except Exception as exc:
        log.error(
            "save_commodity_valuation_result: ticker=%s — erro ao gravar: %s",
            ticker_upper,
            exc,
        )
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Constantes
    "COMMODITY_TICKERS",
    "OIL_GAS_TICKERS",
    "MINING_TICKERS",
    "COMMODITY_PRESERVED_FAIR_VALUES",
    "DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE",
    "DEFAULT_MINING_EV_EBITDA_MULTIPLE",
    # Enumerações de método/qualidade/status
    "CommodityValuationMethod",
    "CommodityInputQuality",
    "CommodityValuationStatus",
    # Dataclasses
    "CommodityValuationInputs",
    "CommodityValuationResult",
    # Validações internas (exportadas para testes)
    "_validate_shares_and_net_debt",
    "_validate_dcf_prerequisites",
    "_validate_ev_ebitda_prerequisites",
    # Motor de cálculo
    "calculate_commodity_valuation",
    # Diagnóstico batch
    "diagnose_commodity_tickers",
    # Save seguro
    "save_commodity_valuation_result",
]
