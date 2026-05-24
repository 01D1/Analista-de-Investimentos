"""
src/valuation/router.py — Universal Sector Router (S04)

Camada de roteamento metodológico: dado um ticker + setor + status de cobertura,
retorna a decisão de routing (método sugerido, confiança, bloqueio) sem calcular
fair_value, sem executar DCF/COSIF/DDM, sem alterar banco.

Baseado em: M014-ARCHITECTURE.md (S03), D083–D088

Contrato público:
    get_valuation_method(ticker, sector, coverage_status=None, provenance=None)
        → RouterDecision

Regras de bloqueio (D087):
    - NEEDS_CVM_DATA → blocked=True, confidence=0
    - NEEDS_SECTOR   → blocked=True, confidence=0
    - provenance.source != TRACEABLE → blocked=True

Proibido:
    - Calcular fair_value
    - Executar DCF/COSIF/DDM
    - Alterar banco
    - Criar dados mockados
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────────────────────────────
#  ValuationMethod — métodos sugeridos por setor
# ──────────────────────────────────────────────

class ValuationMethod(enum.Enum):
    COSIF_DDM = "COSIF/DDM"
    DDM = "DDM"
    DCF = "DCF"
    NAV = "NAV"
    RAB = "RAB"
    EV_EBITDA = "EV/EBITDA"
    RELATIVOS = "Relativos"
    SOTP = "SOTP"
    UNKNOWN = "UNKNOWN"


# ──────────────────────────────────────────────
#  RoutingStatus — status da decisão de routing
# ──────────────────────────────────────────────

class RoutingStatus(enum.Enum):
    ROUTED = "routed"           # routing disponível
    BLOCKED = "blocked"         # bloqueado por falta de dados/setor
    UNAVAILABLE = "unavailable" # sem AI entry


# ──────────────────────────────────────────────
#  Provenance — fonte rastreável do setor
# ──────────────────────────────────────────────

@dataclass
class Provenance:
    source: str = "UNKNOWN"  # TRACEABLE, MANUAL, UNKNOWN
    date: Optional[str] = None
    analyst_override: bool = False


# ──────────────────────────────────────────────
#  RouterDecision — resultado do router
# ──────────────────────────────────────────────

@dataclass
class RouterDecision:
    ticker: str
    sector: str
    coverage_status: str  # string para não importar CoverageStatus (evita circular)
    method_suggested: ValuationMethod
    blocked: bool
    block_reason: Optional[str] = None
    confidence: float = 0.0
    provenance_source: str = "UNKNOWN"
    notes: str = ""
    method_alternatives: list[ValuationMethod] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Validação de integridade
        if self.blocked and self.confidence > 0:
            # Bloqueado com confiança > 0 é inconsistente — normaliza
            self.confidence = 0.0
        if not self.blocked and self.confidence == 0:
            self.confidence = 0.5  # default para routed sem confiança explícita


# ──────────────────────────────────────────────
#  Tabela de routing por setor (Arquitetura, seção 6)
# ──────────────────────────────────────────────

_SECTOR_METHOD_MAP: dict[str, tuple[ValuationMethod, list[ValuationMethod]]] = {
    "BANK": (ValuationMethod.COSIF_DDM, [ValuationMethod.DCF]),
    "INSURANCE": (ValuationMethod.DDM, [ValuationMethod.EV_EBITDA]),
    "COMMODITY": (ValuationMethod.DCF, [ValuationMethod.EV_EBITDA]),
    "UTILITY": (ValuationMethod.DCF, [ValuationMethod.RAB]),
    "INDUSTRY": (ValuationMethod.DCF, [ValuationMethod.EV_EBITDA]),
    "RETAIL": (ValuationMethod.DCF, [ValuationMethod.EV_EBITDA]),
    "HOLDING": (ValuationMethod.NAV, [ValuationMethod.DCF]),
    "TECH": (ValuationMethod.DCF, [ValuationMethod.SOTP]),
}

_FALLBACK_SECTOR = "FALLBACK_MULTIPLES"


# ──────────────────────────────────────────────
#  Regras de cobertura (D087)
# ──────────────────────────────────────────────

_BLOCK_STATUSES = {"needs_data", "needs_sector"}


def _is_blocked_status(coverage_status: Optional[str]) -> bool:
    """Retorna True se o status implica bloqueio de routing."""
    if coverage_status is None:
        return False
    return coverage_status.lower() in _BLOCK_STATUSES


# ──────────────────────────────────────────────
#  get_valuation_method — ponto de entrada público
# ──────────────────────────────────────────────

def get_valuation_method(
    ticker: str,
    sector: Optional[str] = None,
    coverage_status: Optional[str] = None,
    provenance: Optional[Provenance] = None,
) -> RouterDecision:
    """
    Retorna decisão de routing para um ticker.

    Parâmetros
    ----------
    ticker: str
        Código do ativo B3 (ex: "PETR4", "ITUB4")
    sector: str | None
        Setor do ativo. Se None, assume FALLBACK_MULTIPLES.
    coverage_status: str | None
        Status de cobertura (needs_data, needs_sector, partial, ready, empty).
        Se None, assume PARTIAL (comportamento conservador).
    provenance: Provenance | None
        Fonte rastreável do setor. Se None, cria provenance padrão.

    Retorno
    -------
    RouterDecision
        Decisão de routing com método sugerido, confiança e razão de bloqueio.

    Regras
    ------
    1. coverage_status in {needs_data, needs_sector} → blocked=True, block_reason preenchido
    2. provenance.source != "TRACEABLE" → blocked=True, block_reason="NEEDS_SECTOR"
    3. sector não mapeado → usa FALLBACK_MULTIPLES (Relativos)
    4. method_suggested = método do setor; method_used fica no valuation engine (S06+)
    5. confidence = 1.0 se routed + sector mapeado; 0.0 se blocked; 0.5 se routed + FALLBACK

    Exemplos
    --------
    >>> decision = get_valuation_method("PETR4", "COMMODITY", "partial")
    >>> decision.method_suggested
    <ValuationMethod.DCF: 'DCF'>
    >>> decision.blocked
    False
    """
    ticker = str(ticker).strip().upper()
    sector = str(sector).strip().upper() if sector else _FALLBACK_SECTOR

    # provenance padrão
    if provenance is None:
        provenance = Provenance()

    # ── Regra 1: bloqueio por coverage status (D087) ──
    if coverage_status is not None and _is_blocked_status(coverage_status):
        status_label = (coverage_status or "").upper()
        if status_label == "NEEDS_DATA":
            block_reason = "NEEDS_CVM_DATA — ri_docs=0 ou financials incompletos"
        elif status_label == "NEEDS_SECTOR":
            block_reason = "NEEDS_SECTOR — setor ausente ou source!=TRACEABLE"
        else:
            block_reason = f"COVERAGE_BLOCKED — {coverage_status}"

        return RouterDecision(
            ticker=ticker,
            sector=sector,
            coverage_status=coverage_status or "unknown",
            method_suggested=ValuationMethod.UNKNOWN,
            blocked=True,
            block_reason=block_reason,
            confidence=0.0,
            provenance_source=provenance.source,
            notes="Routing bloqueado por status de cobertura. Aguardar CVM ingestion.",
        )

    # ── Regra 2: bloqueio por provenance não rastreável (D087) ──
    if provenance.source != "TRACEABLE":
        return RouterDecision(
            ticker=ticker,
            sector=sector,
            coverage_status=coverage_status or "unknown",
            method_suggested=ValuationMethod.UNKNOWN,
            blocked=True,
            block_reason="NEEDS_SECTOR — setor sem fonte rastreável (source!=TRACEABLE)",
            confidence=0.0,
            provenance_source=provenance.source,
            notes=(
                f"Setor '{sector}' não rastreável (source={provenance.source}). "
                "Requer override manual com auditoria ou dados de provenance."
            ),
        )

    # ── Regra 3: mapeamento setor → método ──
    primary_method, alternatives = _SECTOR_METHOD_MAP.get(
        sector,
        (None, [])
    )

    # Fallback: setor não reconhecido
    if primary_method is None:
        primary_method = ValuationMethod.RELATIVOS
        alternatives = []
        confidence = 0.5
        notes = (
            f"Setor '{sector}' não reconhecido na tabela de routing. "
            "Usando método RELATIVOS como fallback. Verificar mapeamento setorial."
        )
    else:
        confidence = 1.0
        notes = f"Routing OK — {sector} → {primary_method.value}"

    # Determinar coverage_status real
    actual_status = coverage_status or "partial"

    return RouterDecision(
        ticker=ticker,
        sector=sector,
        coverage_status=actual_status,
        method_suggested=primary_method,
        blocked=False,
        block_reason=None,
        confidence=confidence,
        provenance_source=provenance.source,
        notes=notes,
        method_alternatives=alternatives,
    )


# ──────────────────────────────────────────────
#  Exports
# ──────────────────────────────────────────────

__all__ = [
    "ValuationMethod",
    "RoutingStatus",
    "Provenance",
    "RouterDecision",
    "get_valuation_method",
]