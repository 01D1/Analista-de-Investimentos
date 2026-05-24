"""
tests/test_router.py — S04 Universal Sector Router Tests

Cobre:
- todos os 8 setores + fallback (9 casos)
- bloqueio por NEEDS_CVM_DATA
- bloqueio por NEEDS_SECTOR
- bloqueio por provenance não rastreável
- method_suggested ≠ method_used (D084)
- confiança por status de routing
- alternativas por setor
"""

from __future__ import annotations

import pytest

from src.valuation.router import (
    ValuationMethod,
    Provenance,
    RouterDecision,
    get_valuation_method,
    RoutingStatus,
)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _provenance_traceable() -> Provenance:
    return Provenance(source="TRACEABLE")


def _provenance_manual() -> Provenance:
    return Provenance(source="MANUAL")


def _provenance_unknown() -> Provenance:
    return Provenance(source="UNKNOWN")


def _provenance_none() -> Provenance:
    return Provenance(source=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────
#  TEST SUITE 1: 8 Setores + Fallback (9 casos)
# ──────────────────────────────────────────────

class TestSectorRouting:
    """Tabela de routing por setor (Arquitetura, seção 6)."""

    @pytest.mark.parametrize(
        "sector,expected_primary,expected_alternatives",
        [
            ("BANK",        ValuationMethod.COSIF_DDM, [ValuationMethod.DCF]),
            ("INSURANCE",   ValuationMethod.DDM,        [ValuationMethod.EV_EBITDA]),
            ("COMMODITY",   ValuationMethod.DCF,        [ValuationMethod.EV_EBITDA]),
            ("UTILITY",     ValuationMethod.DCF,        [ValuationMethod.RAB]),
            ("INDUSTRY",    ValuationMethod.DCF,        [ValuationMethod.EV_EBITDA]),
            ("RETAIL",      ValuationMethod.DCF,        [ValuationMethod.EV_EBITDA]),
            ("HOLDING",     ValuationMethod.NAV,        [ValuationMethod.DCF]),
            ("TECH",        ValuationMethod.DCF,         [ValuationMethod.SOTP]),
        ],
    )
    def test_sector_primary_method(
        self, sector, expected_primary, expected_alternatives
    ):
        """Cada setor mapeia para método primário correto."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector=sector,
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == expected_primary
        assert not decision.blocked
        assert decision.confidence == 1.0

    @pytest.mark.parametrize(
        "sector,expected_alternatives",
        [
            ("BANK",      [ValuationMethod.DCF]),
            ("INSURANCE", [ValuationMethod.EV_EBITDA]),
            ("COMMODITY", [ValuationMethod.EV_EBITDA]),
            ("UTILITY",   [ValuationMethod.RAB]),
            ("INDUSTRY",  [ValuationMethod.EV_EBITDA]),
            ("RETAIL",    [ValuationMethod.EV_EBITDA]),
            ("HOLDING",   [ValuationMethod.DCF]),
            ("TECH",      [ValuationMethod.SOTP]),
        ],
    )
    def test_sector_alternatives(
        self, sector, expected_alternatives
    ):
        """Alternativas por setor estão corretas."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector=sector,
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_alternatives == expected_alternatives

    def test_fallback_unknown_sector(self):
        """Setor não reconhecido → RELATIVOS (FALLBACK_MULTIPLES)."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="UNKNOWN_SECTOR_XYZ",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == ValuationMethod.RELATIVOS
        assert decision.method_alternatives == []
        assert not decision.blocked
        assert decision.confidence == 0.5  # fallback reduz confiança

    def test_fallback_none_sector(self):
        """Setor None → usa FALLBACK_MULTIPLES."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector=None,
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == ValuationMethod.RELATIVOS
        assert not decision.blocked

    def test_fallback_empty_string_sector(self):
        """Setor string vazia → usa FALLBACK_MULTIPLES."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == ValuationMethod.RELATIVOS
        assert not decision.blocked

    def test_sector_case_insensitive(self):
        """Setores são case-insensitive."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="bank",  # minúsculo
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == ValuationMethod.COSIF_DDM
        assert not decision.blocked

    def test_all_9_sectors_routable(self):
        """Garantia: todos os 8 setores + fallback retornam routing (não blocked)."""
        sectors = ["BANK", "INSURANCE", "COMMODITY", "UTILITY", "INDUSTRY", "RETAIL", "HOLDING", "TECH"]
        blocked = []
        for sector in sectors:
            decision = get_valuation_method(
                ticker="TEST11",
                sector=sector,
                coverage_status="ready",
                provenance=_provenance_traceable(),
            )
            if decision.blocked:
                blocked.append(sector)

        assert blocked == [], f"Sectores bloqueados indevidamente: {blocked}"


# ──────────────────────────────────────────────
#  TEST SUITE 2: Bloqueio por NEEDS_CVM_DATA
# ──────────────────────────────────────────────

class TestNeedsCvmData:
    """NEEDS_CVM_DATA bloqueia routing (D087)."""

    def test_needs_data_blocked(self):
        """needs_data → blocked=True, block_reason preenchido."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked is True
        assert "NEEDS_CVM_DATA" in decision.block_reason
        assert decision.confidence == 0.0
        assert decision.method_suggested == ValuationMethod.UNKNOWN

    def test_needs_data_any_sector_blocked(self):
        """Bloqueio não depende do setor."""
        for sector in ["BANK", "INSURANCE", "COMMODITY", "UTILITY"]:
            decision = get_valuation_method(
                ticker="TICKER",
                sector=sector,
                coverage_status="needs_data",
                provenance=_provenance_traceable(),
            )
            assert decision.blocked, f"{sector} deveria estar bloqueado com needs_data"

    def test_needs_data_preserves_ticker(self):
        """Ticker é preservado mesmo bloqueado."""
        decision = get_valuation_method(
            ticker="BBAS3",
            sector="BANK",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.ticker == "BBAS3"

    def test_needs_data_preserves_sector(self):
        """Setor é preservado mesmo bloqueado."""
        decision = get_valuation_method(
            ticker="ITUB4",
            sector="BANK",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.sector == "BANK"

    def test_needs_data_status_label(self):
        """Coverage status é preservado no retorno."""
        decision = get_valuation_method(
            ticker="BBDC4",
            sector="BANK",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.coverage_status == "needs_data"


# ──────────────────────────────────────────────
#  TEST SUITE 3: Bloqueio por NEEDS_SECTOR
# ──────────────────────────────────────────────

class TestNeedsSector:
    """NEEDS_SECTOR bloqueia routing (D087)."""

    def test_needs_sector_blocked(self):
        """needs_sector → blocked=True, block_reason preenchido."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="BANK",
            coverage_status="needs_sector",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked is True
        assert "NEEDS_SECTOR" in decision.block_reason
        assert decision.confidence == 0.0
        assert decision.method_suggested == ValuationMethod.UNKNOWN

    def test_needs_sector_preserves_ticker(self):
        """Ticker é preservado mesmo bloqueado."""
        decision = get_valuation_method(
            ticker="SUZB3",
            sector="INDUSTRY",
            coverage_status="needs_sector",
            provenance=_provenance_traceable(),
        )

        assert decision.ticker == "SUZB3"


# ──────────────────────────────────────────────
#  TEST SUITE 4: Bloqueio por Provenance
# ──────────────────────────────────────────────

class TestProvenanceBlocking:
    """Provenance.source != TRACEABLE bloqueia routing (D087)."""

    def test_provenance_unknown_blocks(self):
        """source=UNKNOWN → bloqueado."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_unknown(),
        )

        assert decision.blocked is True
        assert "NEEDS_SECTOR" in decision.block_reason
        assert decision.confidence == 0.0

    def test_provenance_manual_blocks(self):
        """source=MANUAL → bloqueado (não é TRACEABLE)."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="BANK",
            coverage_status="ready",
            provenance=_provenance_manual(),
        )

        assert decision.blocked is True
        assert "NEEDS_SECTOR" in decision.block_reason

    def test_provenance_none_blocks(self):
        """source=None → bloqueado."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="INDUSTRY",
            coverage_status="ready",
            provenance=_provenance_none(),
        )

        assert decision.blocked is True

    def test_provenance_traceable_allows(self):
        """source=TRACEABLE → permite routing."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert not decision.blocked
        assert decision.confidence == 1.0

    def test_provenance_blocked_with_ready_coverage(self):
        """Provenance bloqueia mesmo quando coverage_status=ready."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="BANK",
            coverage_status="ready",
            provenance=_provenance_unknown(),
        )

        # Provenance wins: bloqueado apesar de ready
        assert decision.blocked is True
        assert "NEEDS_SECTOR" in decision.block_reason


# ──────────────────────────────────────────────
#  TEST SUITE 5: method_suggested ≠ method_used (D084)
# ──────────────────────────────────────────────

class TestMethodSuggestionVsUsage:
    """RouterDecision.method é method_suggested, não method_used (D084)."""

    def test_decision_has_method_suggested_field(self):
        """RouterDecision expõe method_suggested."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert hasattr(decision, "method_suggested")
        # method_used não deve existir no RouterDecision (é do ValuationResult)
        assert not hasattr(decision, "method_used")

    def test_method_suggested_matches_sector_table(self):
        """method_suggested corresponde à tabela de routing."""
        cases = [
            ("BANK",      ValuationMethod.COSIF_DDM),
            ("COMMODITY", ValuationMethod.DCF),
            ("HOLDING",   ValuationMethod.NAV),
            ("UTILITY",   ValuationMethod.DCF),
        ]
        for sector, expected_method in cases:
            decision = get_valuation_method(
                ticker="TST11",
                sector=sector,
                coverage_status="ready",
                provenance=_provenance_traceable(),
            )
            assert decision.method_suggested == expected_method, (
                f"Sector {sector}: esperado {expected_method},got {decision.method_suggested}"
            )

    def test_blocked_decision_unknown_method(self):
        """Decisão bloqueada → method_suggested=UNKNOWN."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="BANK",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.method_suggested == ValuationMethod.UNKNOWN
        # method_used seria None ou diferente no ValuationResult (S06+)


# ──────────────────────────────────────────────
#  TEST SUITE 6: Confiança e Notas
# ──────────────────────────────────────────────

class TestConfidenceAndNotes:
    """Confiança e notas refletem estado de routing."""

    def test_ready_confidence_is_1(self):
        """coverage_status=ready + TRACEABLE → confidence=1.0."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.confidence == 1.0

    def test_partial_confidence_is_1(self):
        """coverage_status=partial + TRACEABLE → confidence=1.0."""
        decision = get_valuation_method(
            ticker="ITUB4",
            sector="BANK",
            coverage_status="partial",
            provenance=_provenance_traceable(),
        )

        assert decision.confidence == 1.0

    def test_blocked_confidence_is_0(self):
        """blocked=True → confidence=0.0."""
        decision = get_valuation_method(
            ticker="SUZB3",
            sector="INDUSTRY",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked
        assert decision.confidence == 0.0

    def test_fallback_confidence_is_0_5(self):
        """Setor desconhecido → confidence=0.5."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="INVALID_SECTOR",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.confidence == 0.5
        assert "INVALID_SECTOR" in decision.notes

    def test_notes_contains_routing_info(self):
        """Notes contém info de routing."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert len(decision.notes) > 0
        assert "COMMODITY" in decision.notes or "DCF" in decision.notes

    def test_blocked_notes_explains_reason(self):
        """Notas de bloqueio explicam a razão."""
        decision = get_valuation_method(
            ticker="SUZB3",
            sector="INDUSTRY",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert len(decision.notes) > 0
        assert "bloqueado" in decision.notes.lower() or "CVM" in decision.notes

    def test_provenance_source_in_decision(self):
        """provenance_source é propagado para a decisão."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.provenance_source == "TRACEABLE"

    def test_provenance_unknown_in_decision(self):
        """Provenance unknown é propagado na decisão."""
        decision = get_valuation_method(
            ticker="TST11",
            sector="BANK",
            coverage_status="ready",
            provenance=_provenance_unknown(),
        )

        assert decision.provenance_source == "UNKNOWN"
        assert decision.blocked


# ──────────────────────────────────────────────
#  TEST SUITE 7: Ticker Case e Espaços
# ──────────────────────────────────────────────

class TestTickerNormalization:
    """Ticker é normalizado para uppercase sem espaços."""

    def test_ticker_uppercase(self):
        """Ticker em minúsculo é normalizado."""
        decision = get_valuation_method(
            ticker="petr4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.ticker == "PETR4"

    def test_ticker_with_spaces(self):
        """Ticker com espaços é normalizado."""
        decision = get_valuation_method(
            ticker="  ITUB4  ",
            sector="BANK",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.ticker == "ITUB4"

    def test_ticker_lowercase_with_suffix(self):
        """Ticker com sufixo (.SA) é preservado."""
        decision = get_valuation_method(
            ticker="petr4.sa",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.ticker == "PETR4.SA"


# ──────────────────────────────────────────────
#  TEST SUITE 8: Integração com CoverageStatus
# ──────────────────────────────────────────────

class TestCoverageStatusIntegration:
    """Router aceita coverage_status como string (não importa enum)."""

    def test_status_ready(self):
        """ready → routed."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert not decision.blocked
        assert decision.coverage_status == "ready"

    def test_status_partial(self):
        """partial → routed."""
        decision = get_valuation_method(
            ticker="ITUB4",
            sector="BANK",
            coverage_status="partial",
            provenance=_provenance_traceable(),
        )

        assert not decision.blocked
        assert decision.coverage_status == "partial"

    def test_status_none_defaults_to_partial(self):
        """coverage_status=None → assume partial."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status=None,
            provenance=_provenance_traceable(),
        )

        assert not decision.blocked
        assert decision.coverage_status == "partial"

    def test_status_empty_defaults_to_partial(self):
        """coverage_status='' → assume partial."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="",
            provenance=_provenance_traceable(),
        )

        assert not decision.blocked


# ──────────────────────────────────────────────
#  TEST SUITE 9: RouterDecision Dataclass
# ──────────────────────────────────────────────

class TestRouterDecisionDataclass:
    """Verifica estrutura completa do RouterDecision."""

    def test_all_required_fields_present(self):
        """Todos os campos obrigatórios estão presentes."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        # Required fields
        assert decision.ticker
        assert decision.sector
        assert decision.coverage_status
        assert decision.method_suggested is not None
        assert decision.blocked is not None
        assert isinstance(decision.confidence, float)
        assert decision.provenance_source

    def test_blocked_has_block_reason(self):
        """blocked=True → block_reason é str, não None."""
        decision = get_valuation_method(
            ticker="SUZB3",
            sector="INDUSTRY",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked is True
        assert decision.block_reason is not None
        assert len(decision.block_reason) > 0

    def test_not_blocked_has_no_block_reason(self):
        """blocked=False → block_reason é None."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked is False
        assert decision.block_reason is None

    def test_post_init_normalizes_confidence(self):
        """Blocked com confidence>0 é normalizado para 0."""
        # coverage_status=needs_data → blocked + confidence=0
        decision = get_valuation_method(
            ticker="SUZB3",
            sector="INDUSTRY",
            coverage_status="needs_data",
            provenance=_provenance_traceable(),
        )

        assert decision.blocked
        assert decision.confidence == 0.0

    def test_method_alternatives_is_list(self):
        """method_alternatives é list, não tuple."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="COMMODITY",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert isinstance(decision.method_alternatives, list)

    def test_fallback_has_empty_alternatives(self):
        """FALLBACK → alternativas vazias."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="UNKNOWN",
            coverage_status="ready",
            provenance=_provenance_traceable(),
        )

        assert decision.method_alternatives == []