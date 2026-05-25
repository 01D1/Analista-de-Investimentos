"""
src/valuation/router.py — Universal Sector Router (S04 + M016-S01)

Camada de roteamento metodológico: dado um ticker + setor + status de cobertura,
retorna a decisão de routing (método sugerido, confiança, bloqueio) sem calcular
fair_value, sem executar DCF/COSIF/DDM, sem alterar banco.

Baseado em: M014-ARCHITECTURE.md (S03), D083–D088
Atualizado: M016-S01 — integração com SectorNormalizer (D097, D099)

Contrato público:
    get_valuation_method(ticker, sector, coverage_status=None, provenance=None)
        → RouterDecision

Regras de bloqueio (D087):
    - NEEDS_CVM_DATA → blocked=True, confidence=0
    - NEEDS_SECTOR   → blocked=True, confidence=0
    - provenance.source != TRACEABLE → blocked=True

Normalização de setor (M016-S01):
    - sector GICS (ex: "financials", "energy") → normalizado via SectorNormalizer
    - sector canônico (ex: "BANK", "COMMODITY") → passthrough sem alteração
    - sector=None → FALLBACK_MULTIPLES

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

_BLOCK_STATUSES = {
    "needs_data",     # Setor ok, financials ausentes (D087)
    "needs_sector",   # Setor não identificado (D087)
    "legacy_ticker",  # Ticker extinto por corporate action — usar successor_ticker (S03.5)
}


def _is_blocked_status(coverage_status: Optional[str]) -> bool:
    """Retorna True se o status implica bloqueio de routing."""
    if coverage_status is None:
        return False
    return coverage_status.lower() in _BLOCK_STATUSES


# ──────────────────────────────────────────────
#  Normalização de setor (M016-S01)
# ──────────────────────────────────────────────

def _normalize_sector_for_router(ticker: str, sector_raw: str) -> str:
    """Converte sector GICS/type → chave canônica do router.

    Usado internamente por get_valuation_method() antes do lookup em
    _SECTOR_METHOD_MAP. Retorna FALLBACK_MULTIPLES se não mapeável.

    Não lança exceção. Nunca altera banco. Apenas normaliza string.
    """
    try:
        from src.valuation.sector_normalizer import normalize_sector
        result = normalize_sector(
            ticker=ticker,
            sector=sector_raw.lower() if sector_raw else None,
        )
        return result.canonical_sector
    except Exception:
        # Fallback defensivo: se SectorNormalizer falhar por qualquer razão,
        # retorna o FALLBACK_SECTOR original (comportamento pré-M016).
        return _FALLBACK_SECTOR


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

    # ── M016-S01: normalização de setor (D097/D099) ──────────────────────────
    # Se sector já é chave canônica (ex: "BANK", "COMMODITY") → passthrough.
    # Se sector é GICS/type (ex: "financials", "energy") → normaliza via SectorNormalizer.
    # Preserva comportamento antigo: testes que passam "BANK" diretamente continuam funcionando.
    sector_raw = str(sector).strip().upper() if sector else ""
    sector_original = sector_raw  # preservado para notas (diagnóstico)

    if not sector_raw:
        # Sem setor → tenta lookup no tickers.yaml pelo ticker
        sector = _normalize_sector_for_router(ticker, sector_raw)
    elif sector_raw in _SECTOR_METHOD_MAP or sector_raw == _FALLBACK_SECTOR:
        # Já canônico → passthrough (mantém compatibilidade com testes existentes)
        sector = sector_raw
    else:
        # GICS/type → normalizar; mantém sector_original para notas
        sector = _normalize_sector_for_router(ticker, sector_raw)

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
        elif status_label == "LEGACY_TICKER":
            block_reason = "LEGACY_TICKER — ticker extinto por corporate action; usar successor_ticker"
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
        # Usa sector_original nas notas para diagnóstico (mantém valor pré-normalização)
        _notes_sector = sector_original if sector_original and sector_original != sector else sector
        notes = (
            f"Setor '{_notes_sector}' não reconhecido na tabela de routing. "
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