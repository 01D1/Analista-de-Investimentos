"""
src/valuation/models/bank_model.py — Bank Valuation Model (M016-S02)

Modelo de valuation para bancos/financials usando metodologia COSIF:
  - P/BV justificado por ROE/Ke (método primário)
  - DDM/Gordon como método secundário (se payout, Ke e g confiáveis)
  - Múltiplos relativos como fallback (somente se dados mínimos existirem)

Arquitetura
-----------
  BankValuationInputs  — dataclass de inputs (real ou ausente)
  BankValuationResult  — dataclass de resultado (calculado ou bloqueado)
  calculate_bank_valuation() — motor de cálculo seguro
  diagnose_bank_tickers()    — diagnóstico batch para 7 tickers BANK

Regras HARD BLOCK (nunca produz fair_value se violadas):
  - Ke <= g         → modelo indefinido (taxa de desconto ≤ crescimento)
  - equity_book_value <= 0  → BVps indefinido
  - net_income ausente ou inconsistente → NI indefinido
  - shares_outstanding <= 0 → per-share indefinido

Regras de preservação:
  - BBAS3 = 64.84 → status PRESERVE_EXISTING (não sobrescrever sem force_recalc)
  - ITUB4 = 73.69 → status PRESERVE_EXISTING (não sobrescrever sem force_recalc)

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

# Grupo BANK canônico (M016-S01)
BANK_TICKERS: frozenset[str] = frozenset({
    "ABCB4", "BBAS3", "BBDC4", "BPAC11", "BRSR6", "ITUB4", "SANB11",
})

# Fair values existentes a preservar (só podem ser sobrescritos com force_recalc=True)
PRESERVED_FAIR_VALUES: dict[str, float] = {
    "BBAS3": 64.84,
    "ITUB4": 73.69,
}


class BankValuationMethod:
    """Constantes de método bancário."""
    PBV_JUSTIFIED  = "P/BV_JUSTIFIED"   # P/BV justificado por ROE/Ke (primário)
    DDM_GORDON     = "DDM_GORDON"        # Dividendo Descontado/Gordon (secundário)
    RELATIVE_PBV   = "RELATIVE_PBV"      # P/BV relativo ao setor (fallback)
    PRESERVE       = "PRESERVE_EXISTING" # Preservar valor existente


class BankInputQuality:
    """Qualidade dos inputs de dados."""
    CVM_LIVE       = "CVM_LIVE"          # Dados ao vivo CVM (melhor)
    EXCEL_PIPELINE = "EXCEL_PIPELINE"    # Modelo Excel pipeline banco completo
    ESTIMATED      = "ESTIMATED"         # Estimativas derivadas (pior)
    ABSENT         = "ABSENT"            # Dados ausentes


class BankValuationStatus:
    """Status do diagnóstico do ticker."""
    VALUATION_READY    = "VALUATION_READY"     # Dados suficientes para calcular
    PRESERVE_EXISTING  = "PRESERVE_EXISTING"   # Valor existente a preservar
    NEEDS_FINANCIALS   = "NEEDS_FINANCIALS"    # Dados financeiros insuficientes
    NEEDS_REVIEW       = "NEEDS_REVIEW"        # Dados presentes mas suspeitos


# ─────────────────────────────────────────────────────────────────────────────
#  Dataclasses de inputs e resultado
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BankValuationInputs:
    """Inputs para valuation de banco/financeiro.

    Todos os campos opcionais — modelo bloqueia se os mínimos ausentes.
    Nunca usar valores mockados aqui.

    Campos
    ------
    ticker : str
        Código do ativo B3 (ex: "BBAS3")
    equity_book_value : float | None
        Patrimônio líquido total (R$ milhões). Bloqueia se ≤ 0.
    net_income : float | None
        Lucro líquido recorrente (R$ milhões). Bloqueia se None.
    roe : float | None
        Return on Equity (decimal, ex: 0.20 = 20%). Derivado de NI/BV se ausente.
    cost_of_equity : float | None
        Custo de capital próprio Ke (decimal, ex: 0.13 = 13%).
        Bloqueia P/BV se ausente ou inválido.
    payout_ratio : float | None
        Taxa de distribuição de dividendos (decimal, ex: 0.40 = 40%).
        Necessário para DDM.
    growth_rate : float | None
        Taxa de crescimento sustentável g (decimal, ex: 0.07 = 7%).
        Bloqueia P/BV e DDM se Ke <= g.
    shares_outstanding : float | None
        Número de ações em circulação (milhões). Bloqueia se ≤ 0.
    market_price : float | None
        Preço de mercado atual (R$). Usado para calcular upside.
    source_quality : str
        Qualidade dos dados de origem (BankInputQuality constants).
    existing_fair_value : float | None
        Fair value já calculado e registrado (para PRESERVE logic).
    existing_valuation_date : str | None
        Data do valuation existente (ISO format, ex: "2026-04-16").
    """

    ticker: str
    equity_book_value: Optional[float] = None
    net_income: Optional[float] = None
    roe: Optional[float] = None
    cost_of_equity: Optional[float] = None
    payout_ratio: Optional[float] = None
    growth_rate: Optional[float] = None
    shares_outstanding: Optional[float] = None
    market_price: Optional[float] = None
    source_quality: str = BankInputQuality.ABSENT
    existing_fair_value: Optional[float] = None
    existing_valuation_date: Optional[str] = None

    def __post_init__(self) -> None:
        self.ticker = str(self.ticker).strip().upper()

    def derive_roe(self) -> Optional[float]:
        """Deriva ROE de NI/BV se não fornecido explicitamente."""
        if self.roe is not None:
            return self.roe
        if (self.net_income is not None and self.equity_book_value is not None
                and self.equity_book_value > 0):
            return self.net_income / self.equity_book_value
        return None

    @property
    def bv_per_share(self) -> Optional[float]:
        """Book value por ação (R$)."""
        if (self.equity_book_value is not None and self.equity_book_value > 0
                and self.shares_outstanding is not None and self.shares_outstanding > 0):
            return self.equity_book_value / self.shares_outstanding
        return None

    @property
    def eps(self) -> Optional[float]:
        """Earnings per share (R$)."""
        if (self.net_income is not None
                and self.shares_outstanding is not None and self.shares_outstanding > 0):
            return self.net_income / self.shares_outstanding
        return None

    @property
    def dps(self) -> Optional[float]:
        """Dividends per share (R$)."""
        if self.eps is not None and self.payout_ratio is not None and self.payout_ratio > 0:
            return self.eps * self.payout_ratio
        return None


@dataclass
class BankValuationResult:
    """Resultado de valuation para banco/financeiro.

    Campos
    ------
    ticker : str
        Código do ativo B3.
    fair_value : float | None
        Preço-alvo calculado (R$). None se bloqueado ou sem dados.
    valuation_method : str | None
        Método principal utilizado (BankValuationMethod constants).
    method_used : str | None
        Método que efetivamente produziu o fair_value (pode ser diferente de method_suggested).
    confidence : float
        Confiança do resultado (0.0 a 1.0). 0.0 se bloqueado.
    input_quality : str
        Qualidade dos inputs utilizados (BankInputQuality constants).
    status : str
        Status do diagnóstico (BankValuationStatus constants).
    blocked : bool
        True se o cálculo foi bloqueado por dados insuficientes.
    block_reason : str | None
        Razão do bloqueio (se blocked=True).
    upside_pct : float | None
        Upside potencial em relação ao preço de mercado (%).
    valuation_date : str
        Data de referência do valuation (ISO format).
    pbv_justified : float | None
        P/BV justificado calculado (ROE/Ke method).
    bv_per_share : float | None
        Book value por ação utilizado no cálculo.
    roe_used : float | None
        ROE utilizado no cálculo.
    ke_used : float | None
        Ke utilizado no cálculo.
    g_used : float | None
        Taxa de crescimento g utilizada.
    notes : str
        Notas de auditoria e diagnóstico.
    """

    ticker: str
    fair_value: Optional[float] = None
    valuation_method: Optional[str] = None
    method_used: Optional[str] = None
    confidence: float = 0.0
    input_quality: str = BankInputQuality.ABSENT
    status: str = BankValuationStatus.NEEDS_FINANCIALS
    blocked: bool = True
    block_reason: Optional[str] = None
    upside_pct: Optional[float] = None
    valuation_date: str = field(default_factory=lambda: date.today().isoformat())
    pbv_justified: Optional[float] = None
    bv_per_share: Optional[float] = None
    roe_used: Optional[float] = None
    ke_used: Optional[float] = None
    g_used: Optional[float] = None
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
        status: str = BankValuationStatus.NEEDS_FINANCIALS,
        input_quality: str = BankInputQuality.ABSENT,
        notes: str = "",
    ) -> "BankValuationResult":
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
    ) -> "BankValuationResult":
        """Factory para resultado preservado (não recalculado)."""
        upside = None
        if market_price is not None and market_price > 0 and fair_value > 0:
            upside = round((fair_value / market_price - 1) * 100, 2)
        return cls(
            ticker=ticker,
            fair_value=fair_value,
            valuation_method=BankValuationMethod.PRESERVE,
            method_used=BankValuationMethod.PRESERVE,
            confidence=0.9,  # high confidence in preserved values
            input_quality=BankInputQuality.EXCEL_PIPELINE,
            status=BankValuationStatus.PRESERVE_EXISTING,
            blocked=False,
            block_reason=None,
            upside_pct=upside,
            valuation_date=valuation_date or date.today().isoformat(),
            notes=notes or f"Valor preservado. force_recalc=True para recalcular.",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Motor de cálculo bancário
# ─────────────────────────────────────────────────────────────────────────────

def _validate_hard_blocks(inputs: BankValuationInputs) -> Optional[str]:
    """Verifica hard blocks. Retorna mensagem de bloqueio ou None se OK.

    Hard blocks (D-BANK-01 a D-BANK-04):
      D-BANK-01: equity_book_value <= 0 → BVps indefinido
      D-BANK-02: net_income ausente ou None → ROE indefinido
      D-BANK-03: shares_outstanding <= 0 → per-share indefinido
      D-BANK-04: Ke <= g → modelo P/BV e DDM indefinidos
    """
    # D-BANK-01: Book value
    if inputs.equity_book_value is None:
        return "D-BANK-01: equity_book_value ausente — BVps indefinido"
    if inputs.equity_book_value <= 0:
        return f"D-BANK-01: equity_book_value={inputs.equity_book_value:.2f} ≤ 0 — BVps indefinido"

    # D-BANK-02: Net income
    if inputs.net_income is None:
        return "D-BANK-02: net_income ausente — não é possível calcular ROE ou EPS"

    # Consistência NI/BV: compara ROE informado com ROE calculado de NI/BV
    # (derive_roe() retorna inputs.roe se explícito — usamos cálculo direto aqui)
    if inputs.roe is not None and inputs.equity_book_value is not None and inputs.equity_book_value > 0:
        roe_computed_from_ni_bv = inputs.net_income / inputs.equity_book_value
        discrepancy = abs(roe_computed_from_ni_bv - inputs.roe)
        if discrepancy > 0.10:  # >10pp discrepancy → dados inconsistentes
            return (
                f"D-BANK-02: Inconsistência NI/BV → ROE(NI/BV)={roe_computed_from_ni_bv:.4f} "
                f"vs ROE informado={inputs.roe:.4f} (discrepância {discrepancy:.4f} > 10pp)"
            )

    # D-BANK-03: Shares outstanding
    if inputs.shares_outstanding is None:
        return "D-BANK-03: shares_outstanding ausente — EPS/BVps indefinido"
    if inputs.shares_outstanding <= 0:
        return f"D-BANK-03: shares_outstanding={inputs.shares_outstanding} ≤ 0 — inválido"

    return None  # nenhum hard block


def _validate_pbv_prerequisites(inputs: BankValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para P/BV justificado.

    Retorna mensagem de bloqueio ou None se OK.
    Pré-requisitos: cost_of_equity, growth_rate, equity_book_value, shares_outstanding.
    Hard block: Ke <= g.
    """
    ke = inputs.cost_of_equity
    g = inputs.growth_rate

    if ke is None:
        return "cost_of_equity (Ke) ausente — P/BV justificado indisponível"
    if ke <= 0:
        return f"cost_of_equity={ke:.4f} ≤ 0 — inválido"
    if g is None:
        return "growth_rate (g) ausente — P/BV justificado indisponível"

    # D-BANK-04: Ke <= g → HARD BLOCK
    if ke <= g:
        return (
            f"D-BANK-04: HARD BLOCK — Ke={ke:.4f} ≤ g={g:.4f}. "
            "Terminal growth ≥ cost of equity: modelo indefinido. "
            "Ajuste as premissas antes de calcular."
        )

    return None


def _validate_ddm_prerequisites(inputs: BankValuationInputs) -> Optional[str]:
    """Verifica pré-requisitos para DDM/Gordon.

    Retorna mensagem de bloqueio ou None se OK.
    """
    if inputs.payout_ratio is None:
        return "payout_ratio ausente — DDM indisponível"
    if inputs.payout_ratio <= 0 or inputs.payout_ratio > 1.5:
        return f"payout_ratio={inputs.payout_ratio:.4f} inválido (esperado 0 < ratio ≤ 1.5)"

    # DDM precisa dos mesmos pré-requisitos do P/BV para Ke e g
    return _validate_pbv_prerequisites(inputs)


def _calculate_pbv_justified(inputs: BankValuationInputs) -> tuple[float, float, float]:
    """Calcula P/BV justificado, BVps e fair_value.

    Fórmula: P/BV justificado = (ROE - g) / (Ke - g)
             fair_value = P/BV justificado × BVps

    Retorna (fair_value, pbv_justified, bv_per_share).
    Pré-condição: sem hard blocks, sem bloqueio de pré-requisitos.
    """
    roe = inputs.derive_roe()
    ke = inputs.cost_of_equity
    g = inputs.growth_rate

    bv_per_share = inputs.bv_per_share  # já validado: > 0

    # P/BV justificado (Gordon-implícito)
    pbv_justified = (roe - g) / (ke - g)

    # Fair value = P/BV justificado × BVps
    # Nota: pbv_justified pode ser negativo se ROE < g — isso é um warning
    fair_value = round(pbv_justified * bv_per_share, 2)

    return fair_value, round(pbv_justified, 4), round(bv_per_share, 2)


def _calculate_ddm_gordon(inputs: BankValuationInputs) -> float:
    """Calcula fair_value via DDM/Gordon.

    Fórmula: fair_value = DPS / (Ke - g)
    Pré-condição: sem hard blocks, sem bloqueio de pré-requisitos.
    """
    dps = inputs.dps  # EPS × payout_ratio
    ke = inputs.cost_of_equity
    g = inputs.growth_rate

    fair_value = round(dps / (ke - g), 2)
    return fair_value


def calculate_bank_valuation(
    inputs: BankValuationInputs,
    force_recalc: bool = False,
) -> BankValuationResult:
    """Calcula valuation para um banco.

    Motor seguro — nunca inventa dados, nunca ignora hard blocks.

    Hierarquia de métodos:
      1. PRESERVE_EXISTING — se valor existente E force_recalc=False
      2. P/BV justificado  — se ROE, Ke, g, BV, shares disponíveis
      3. DDM/Gordon        — se payout_ratio, Ke, g, NI, shares disponíveis
      4. BLOCKED           — se dados insuficientes para qualquer método

    Parâmetros
    ----------
    inputs : BankValuationInputs
        Inputs do banco. Nunca passados mockados.
    force_recalc : bool
        Se True, recalcula mesmo com valor existente. Default: False.

    Retorno
    -------
    BankValuationResult
        Resultado com fair_value calculado ou blocked=True se dados insuficientes.
    """
    ticker = inputs.ticker

    # ── Passo 0: Verificar se deve preservar valor existente ──────────────────
    if not force_recalc and inputs.existing_fair_value is not None:
        logger.info(
            "ticker=%s: fair_value existente=%s preservado (force_recalc=False)",
            ticker, inputs.existing_fair_value
        )
        return BankValuationResult.preserved_result(
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

    # ── Passo 1: Hard blocks — verificação obrigatória antes de qualquer cálculo ─
    hard_block = _validate_hard_blocks(inputs)
    if hard_block:
        logger.warning("ticker=%s: HARD BLOCK — %s", ticker, hard_block)
        return BankValuationResult.blocked_result(
            ticker=ticker,
            block_reason=hard_block,
            status=BankValuationStatus.NEEDS_FINANCIALS,
            input_quality=inputs.source_quality,
            notes=f"Hard block ativado — sem cálculo. {hard_block}",
        )

    # ── Passo 2: Tentar P/BV justificado ────────────────────────────────────────
    pbv_block = _validate_pbv_prerequisites(inputs)
    if pbv_block is None:
        try:
            fair_value, pbv_justified, bv_per_share = _calculate_pbv_justified(inputs)
            roe_used = inputs.derive_roe()

            # Sanity check: pbv_justified negativo → sinal de ROE < g → NEEDS_REVIEW
            if pbv_justified < 0:
                return BankValuationResult.blocked_result(
                    ticker=ticker,
                    block_reason=(
                        f"P/BV justificado={pbv_justified:.4f} < 0: ROE={roe_used:.4f} < g={inputs.growth_rate:.4f}. "
                        "Banco destruindo valor — revisar premissas."
                    ),
                    status=BankValuationStatus.NEEDS_REVIEW,
                    input_quality=inputs.source_quality,
                    notes="P/BV negativo: ROE abaixo do crescimento — modelo sinaliza destruição de valor.",
                )

            # Calcular upside
            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            logger.info(
                "ticker=%s: P/BV justificado=%.4f × BVps=%.2f → fair_value=%.2f",
                ticker, pbv_justified, bv_per_share, fair_value
            )

            return BankValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=BankValuationMethod.PBV_JUSTIFIED,
                method_used=BankValuationMethod.PBV_JUSTIFIED,
                confidence=_confidence_from_quality(inputs.source_quality),
                input_quality=inputs.source_quality,
                status=BankValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                upside_pct=upside,
                pbv_justified=pbv_justified,
                bv_per_share=bv_per_share,
                roe_used=round(roe_used, 4),
                ke_used=round(inputs.cost_of_equity, 4),
                g_used=round(inputs.growth_rate, 4),
                notes=(
                    f"P/BV justificado: ROE={roe_used:.2%}, Ke={inputs.cost_of_equity:.2%}, "
                    f"g={inputs.growth_rate:.2%} → P/BV={pbv_justified:.4f} × BVps=R${bv_per_share:.2f}"
                ),
            )
        except ZeroDivisionError:
            # Ke == g foi bloqueado antes, mas defensive catch
            pass
        except Exception as e:
            logger.error("ticker=%s: erro no cálculo P/BV: %s", ticker, e)

    # ── Passo 3: Tentar DDM/Gordon ───────────────────────────────────────────────
    ddm_block = _validate_ddm_prerequisites(inputs)
    if ddm_block is None:
        try:
            fair_value = _calculate_ddm_gordon(inputs)
            dps = inputs.dps
            upside = None
            if inputs.market_price is not None and inputs.market_price > 0:
                upside = round((fair_value / inputs.market_price - 1) * 100, 2)

            logger.info(
                "ticker=%s: DDM/Gordon DPS=%.2f / (Ke-g) → fair_value=%.2f",
                ticker, dps, fair_value
            )

            return BankValuationResult(
                ticker=ticker,
                fair_value=fair_value,
                valuation_method=BankValuationMethod.DDM_GORDON,
                method_used=BankValuationMethod.DDM_GORDON,
                confidence=_confidence_from_quality(inputs.source_quality) * 0.85,
                input_quality=inputs.source_quality,
                status=BankValuationStatus.VALUATION_READY,
                blocked=False,
                block_reason=None,
                upside_pct=upside,
                ke_used=round(inputs.cost_of_equity, 4),
                g_used=round(inputs.growth_rate, 4),
                notes=(
                    f"DDM/Gordon: DPS=R${dps:.4f}, Ke={inputs.cost_of_equity:.2%}, "
                    f"g={inputs.growth_rate:.2%} → R${fair_value:.2f}. "
                    f"P/BV indisponível: {pbv_block}"
                ),
            )
        except ZeroDivisionError:
            pass
        except Exception as e:
            logger.error("ticker=%s: erro no cálculo DDM: %s", ticker, e)

    # ── Passo 4: Sem método disponível — bloquear ────────────────────────────────
    block_reasons = []
    if pbv_block:
        block_reasons.append(f"P/BV bloqueado: {pbv_block}")
    if ddm_block:
        block_reasons.append(f"DDM bloqueado: {ddm_block}")

    combined_reason = " | ".join(block_reasons) if block_reasons else "Dados insuficientes para qualquer método bancário"

    logger.warning("ticker=%s: sem método disponível — %s", ticker, combined_reason)

    return BankValuationResult.blocked_result(
        ticker=ticker,
        block_reason=combined_reason,
        status=BankValuationStatus.NEEDS_FINANCIALS,
        input_quality=inputs.source_quality,
        notes=f"Nenhum método bancário disponível. {combined_reason}",
    )


def _confidence_from_quality(source_quality: str) -> float:
    """Deriva confiança a partir da qualidade dos inputs."""
    return {
        BankInputQuality.CVM_LIVE:       0.95,
        BankInputQuality.EXCEL_PIPELINE: 0.80,
        BankInputQuality.ESTIMATED:      0.50,
        BankInputQuality.ABSENT:         0.00,
    }.get(source_quality, 0.50)


# ─────────────────────────────────────────────────────────────────────────────
#  Diagnóstico batch dos 7 tickers BANK
# ─────────────────────────────────────────────────────────────────────────────

def _load_existing_fair_value(ticker: str) -> Optional[float]:
    """Tenta carregar fair_value existente via valuation_bridge + registry.

    Fontes (por precedência):
      1. PRESERVED_FAIR_VALUES — valores hardcoded para BBAS3/ITUB4
      2. valuation_bridge (Excel pipeline) — busca arquivos Valuation_TICKER_YYYYMMDD.xlsx
      3. Subdirectório valuations/{TICKER}/Valuation_{TICKER}.xlsx — arquivos canônicos
      4. None se não encontrar

    Não lança exceção — retorna None em caso de falha.
    """
    from pathlib import Path

    # Fonte 1: fair values preservados explicitamente (BBAS3, ITUB4)
    if ticker in PRESERVED_FAIR_VALUES:
        return PRESERVED_FAIR_VALUES[ticker]

    # Localização base dos outputs do pipeline
    outputs_dir = (
        Path(__file__).parent.parent.parent.parent.parent
        / "12_PYTHON" / "pipeline banco completo" / "outputs"
    )

    if not outputs_dir.exists():
        logger.debug("ticker=%s: outputs_dir não encontrado: %s", ticker, outputs_dir)
        return None

    # Fonte 2: Excel bridge — arquivos Valuation_TICKER_*.xlsx com data
    # O bridge ordena alfabeticamente (reverso) e pega o primeiro;
    # arquivos "test_summary" batem antes por ordem alfabética — filtramos datas.
    try:
        import re
        date_pattern = re.compile(rf"Valuation_{re.escape(ticker)}_.*(\d{{8}})\.xlsx$")
        dated_files = [
            f for f in outputs_dir.glob(f"Valuation_{ticker}_*.xlsx")
            if date_pattern.search(f.name)
        ]
        if dated_files:
            # Ordenar por data (YYYYMMDD no nome) — pegar o mais recente
            dated_files_sorted = sorted(
                dated_files,
                key=lambda f: (date_pattern.search(f.name).group(1) if date_pattern.search(f.name) else ""),
                reverse=True,
            )
            best_file = dated_files_sorted[0]
            fv = _extract_fair_value_from_excel(best_file, ticker)
            if fv is not None:
                logger.debug("ticker=%s: fair_value=%.2f carregado de %s", ticker, fv, best_file.name)
                return fv
    except Exception as e:
        logger.debug("ticker=%s: falha ao carregar via dated files: %s", ticker, e)

    # Fonte 3: Subdirectório canônico valuations/{TICKER}/Valuation_{TICKER}.xlsx
    try:
        canonical = outputs_dir / "valuations" / ticker / f"Valuation_{ticker}.xlsx"
        if canonical.exists():
            fv = _extract_fair_value_from_excel(canonical, ticker)
            if fv is not None:
                logger.debug("ticker=%s: fair_value=%.2f carregado de canonical subdir", ticker, fv)
                return fv
    except Exception as e:
        logger.debug("ticker=%s: falha ao carregar via canonical subdir: %s", ticker, e)

    # Fonte 4: bridge genérico (fallback)
    try:
        from src.integration.valuation_bridge import get_valuations_batch
        valuations = get_valuations_batch([ticker], outputs_dir)
        val = valuations.get(ticker) or {}
        if val and val.get("preco_alvo") is not None:
            fv = val["preco_alvo"]
            logger.debug("ticker=%s: fair_value=%.2f carregado via bridge genérico", ticker, fv)
            return float(fv)
    except Exception as e:
        logger.debug("ticker=%s: falha ao carregar via bridge genérico: %s", ticker, e)

    return None


def _extract_fair_value_from_excel(file_path: "Path", ticker: str) -> Optional[float]:
    """Extrai 'Preço Justo' do Dashboard sheet de um Excel de valuation bancário.

    Lê 'Preço Justo por Ação ON' do Dashboard como preço principal.
    Retorna None se não encontrado ou em caso de erro.
    """
    try:
        import pandas as pd
        xl = pd.ExcelFile(str(file_path))

        # Prioridade: Dashboard > Status & Fontes > DRE + DCF
        sheets_priority = ["Dashboard", "Status & Fontes", "DRE + DCF"]
        for sheet in sheets_priority:
            if sheet not in xl.sheet_names:
                continue
            df = xl.parse(sheet, header=None)
            for i, row in df.iterrows():
                for j, val in enumerate(row):
                    if not isinstance(val, str):
                        continue
                    val_lower = val.lower()
                    if any(kw in val_lower for kw in [
                        "preço justo por ação on",
                        "preco justo por acao on",
                        "preço justo principal",
                        "preco justo principal",
                    ]):
                        # Próxima célula à direita
                        for offset in [1, 2]:
                            try:
                                candidate = pd.to_numeric(df.iloc[i, j + offset], errors="coerce")
                                if pd.notna(candidate) and 0 < float(candidate) < 10_000:
                                    return round(float(candidate), 2)
                            except (IndexError, TypeError):
                                pass
    except Exception as e:
        logger.debug("_extract_fair_value_from_excel: %s → %s", file_path, e)
    return None


def _load_market_price(ticker: str) -> Optional[float]:
    """Tenta carregar preço de mercado do banco SQLite.

    Fontes: cotahist_daily → asset_intelligence_snapshots.
    Retorna None se não encontrar.
    """
    try:
        import sqlite3, os
        from pathlib import Path

        db_env = os.environ.get("SCANNER_QUANT_DB")
        db_path = db_env if db_env else "scanner_quant.db"

        if not Path(db_path).exists():
            return None

        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Tenta cotahist_daily
        c.execute(
            "SELECT close FROM cotahist_daily WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
            (ticker,)
        )
        row = c.fetchone()
        if row and row[0]:
            conn.close()
            return float(row[0])

        # Tenta asset_intelligence_snapshots
        c.execute(
            "SELECT market_price FROM asset_intelligence_snapshots WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,)
        )
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            return float(row[0])
    except Exception as e:
        logger.debug("ticker=%s: falha ao carregar market_price: %s", ticker, e)

    return None


def _classify_ticker_status(
    ticker: str,
    existing_fv: Optional[float],
) -> str:
    """Classifica status de disponibilidade de dados para valuation."""
    if existing_fv is not None:
        if ticker in PRESERVED_FAIR_VALUES:
            return BankValuationStatus.PRESERVE_EXISTING
        # Fair value de Excel pipeline
        return BankValuationStatus.PRESERVE_EXISTING
    # Sem nenhum dado
    return BankValuationStatus.NEEDS_FINANCIALS


def diagnose_bank_tickers(
    tickers: Optional[list[str]] = None,
    force_recalc: bool = False,
) -> dict[str, dict]:
    """Diagnóstico batch dos tickers BANK.

    Para cada ticker do grupo BANK, verifica:
      - Se existe fair_value via Excel pipeline ou preserved values
      - Se dados financeiros mínimos estão disponíveis no banco
      - Classifica status: PRESERVE_EXISTING, NEEDS_FINANCIALS, VALUATION_READY

    Não calcula fair_value novo — somente diagnostica e preserva existentes.

    Parâmetros
    ----------
    tickers : list[str] | None
        Lista de tickers. Se None, usa BANK_TICKERS completo.
    force_recalc : bool
        Se True, ignora preserved values e tenta recalcular.
        Uso: apenas para testes ou recalibração explícita.

    Retorno
    -------
    dict[str, dict]
        Mapeamento ticker → dict com:
          - status: BankValuationStatus
          - existing_fair_value: float | None
          - market_price: float | None
          - source_quality: BankInputQuality
          - result: BankValuationResult (com blocked=True se NEEDS_FINANCIALS)
    """
    target = [t.strip().upper() for t in (tickers or list(BANK_TICKERS))]
    output: dict[str, dict] = {}

    for ticker in target:
        logger.info("diagnose_bank_tickers: processando %s", ticker)

        # Carregar fair_value existente
        existing_fv = _load_existing_fair_value(ticker)
        market_price = _load_market_price(ticker)

        # Qualidade da fonte
        if ticker in PRESERVED_FAIR_VALUES:
            quality = BankInputQuality.EXCEL_PIPELINE
        elif existing_fv is not None:
            quality = BankInputQuality.EXCEL_PIPELINE
        else:
            quality = BankInputQuality.ABSENT

        # Classificar status
        status = _classify_ticker_status(ticker, existing_fv)

        # Construir inputs mínimos para diagnóstico
        inputs = BankValuationInputs(
            ticker=ticker,
            market_price=market_price,
            source_quality=quality,
            existing_fair_value=existing_fv if not force_recalc else None,
            existing_valuation_date=None,
        )

        # Calcular resultado (preservar ou bloquear)
        result = calculate_bank_valuation(inputs, force_recalc=force_recalc)

        output[ticker] = {
            "status": status,
            "existing_fair_value": existing_fv,
            "market_price": market_price,
            "source_quality": quality,
            "result": result,
        }

        logger.info(
            "diagnose_bank_tickers: %s → status=%s, fv=%s, blocked=%s",
            ticker, status, existing_fv, result.blocked
        )

    return output


# ─────────────────────────────────────────────────────────────────────────────
#  Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Constantes
    "BANK_TICKERS",
    "PRESERVED_FAIR_VALUES",
    # Enumerações de método/qualidade/status
    "BankValuationMethod",
    "BankInputQuality",
    "BankValuationStatus",
    # Dataclasses
    "BankValuationInputs",
    "BankValuationResult",
    # Motor de cálculo
    "calculate_bank_valuation",
    # Diagnóstico batch
    "diagnose_bank_tickers",
]
