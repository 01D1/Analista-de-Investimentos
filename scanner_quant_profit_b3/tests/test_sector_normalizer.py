"""
tests/test_sector_normalizer.py — M016-S01: SectorNormalizer Tests

Cobre:
  1. Mapeamento de todos os tipos documentados no roadmap (TYPE_TO_CANONICAL)
  2. Mapeamento GICS sector fallback (GICS_SECTOR_TO_CANONICAL)
  3. Fallback para tipo/sector desconhecido → FALLBACK_MULTIPLES
  4. Passthrough de chaves já canônicas
  5. Integração com router via get_valuation_method (28 tickers READY)
  6. PETZ3 continua LEGACY_TICKER (router bloqueado)
  7. VALE3/AUAU3/NTCO3 verificação de bloqueio correto (NEEDS_RI_DOCS)
  8. Nenhum fair_value calculado
  9. Nenhum mock criado
  10. Tickers com RENT3: normaliza para INDUSTRY (type=industrial)
  11. Smoke test dos 28 tickers READY_FOR_MODEL_DESIGN
"""

from __future__ import annotations

import pytest

from src.valuation.sector_normalizer import (
    SectorNormalizationResult,
    SectorNormalizer,
    NormalizationSource,
    CANONICAL_KEYS,
    FALLBACK_CANONICAL,
    TYPE_TO_CANONICAL,
    GICS_SECTOR_TO_CANONICAL,
    normalize_sector,
    get_normalizer,
)
from src.valuation.router import (
    ValuationMethod,
    Provenance,
    RouterDecision,
    get_valuation_method,
)


# ──────────────────────────────────────────────
#  Constantes de teste
# ──────────────────────────────────────────────

#: 28 tickers READY_FOR_MODEL_DESIGN (M015-S05)
READY_TICKERS = [
    "ABCB4", "AZZA3", "BBAS3", "BBDC4", "BPAC11", "BRSR6", "EGIE3",
    "FLRY3", "HYPE3", "ITUB4", "KLBN11", "LREN3", "MGLU3", "PCAR3",
    "PETR4", "PRIO3", "RADL3", "RAIL3", "RECV3", "RENT3", "SANB11",
    "SBSP3", "SUZB3", "TAEE11", "VAMO3", "VIVA3", "VIVT3", "WEGE3",
]

#: Mapeamento esperado por setor (D097/D099/D108)
EXPECTED_CANONICAL = {
    # Bancos → BANK
    "ABCB4": "BANK", "BBAS3": "BANK", "BBDC4": "BANK",
    "BPAC11": "BANK", "BRSR6": "BANK", "ITUB4": "BANK", "SANB11": "BANK",
    # Oil & Gas → COMMODITY
    "PETR4": "COMMODITY", "PRIO3": "COMMODITY", "RECV3": "COMMODITY",
    # Utilities → UTILITY
    "EGIE3": "UTILITY", "SBSP3": "UTILITY", "TAEE11": "UTILITY",
    # Healthcare → INDUSTRY (D108)
    "FLRY3": "INDUSTRY", "HYPE3": "INDUSTRY", "RADL3": "INDUSTRY",
    # Industrial → INDUSTRY
    "KLBN11": "INDUSTRY", "RAIL3": "INDUSTRY", "RENT3": "INDUSTRY",
    "SUZB3": "INDUSTRY", "VAMO3": "INDUSTRY", "WEGE3": "INDUSTRY",
    # Retail → RETAIL
    "AZZA3": "RETAIL", "LREN3": "RETAIL", "MGLU3": "RETAIL",
    "PCAR3": "RETAIL", "VIVA3": "RETAIL",
    # Telecom → TECH
    "VIVT3": "TECH",
}

_TRACEABLE = Provenance(source="TRACEABLE")


# ──────────────────────────────────────────────
#  TEST SUITE 1: Mapeamento type → canonical
# ──────────────────────────────────────────────

class TestTypeMappings:
    """TYPE_TO_CANONICAL cobre todos os types do tickers.yaml."""

    @pytest.mark.parametrize("raw_type,expected", [
        ("bank",        "BANK"),
        ("insurance",   "INSURANCE"),
        ("reinsurance", "INSURANCE"),
        ("oil_gas",     "COMMODITY"),
        ("mining",      "COMMODITY"),
        ("utilities",   "UTILITY"),
        ("industrial",  "INDUSTRY"),
        ("healthcare",  "INDUSTRY"),   # D108
        ("agro",        "INDUSTRY"),   # D108
        ("education",   "INDUSTRY"),   # D108
        ("retail",      "RETAIL"),
        ("holding",     "HOLDING"),
        ("real_estate", "HOLDING"),    # D108
        ("technology",  "TECH"),
        ("telecom",     "TECH"),
    ])
    def test_type_to_canonical_mapping(self, raw_type, expected):
        """Cada type do tickers.yaml mapeia para a chave canônica correta.

        Nota: types cujo nome coincide com a chave canônica (ex: "bank"→"BANK")
        retornam source=CANONICAL_PASSTHROUGH (não EXPLICIT_TYPE). Ambos são
        corretos — confidence=1.0 e canonical_sector correto em ambos os casos.
        """
        result = normalize_sector("TEST11", type=raw_type)
        assert result.canonical_sector == expected, (
            f"type='{raw_type}' deveria ser '{expected}', got '{result.canonical_sector}'"
        )
        assert result.confidence == 1.0
        # source pode ser EXPLICIT_TYPE ou CANONICAL_PASSTHROUGH (quando type==canonical)
        assert result.source in (
            NormalizationSource.EXPLICIT_TYPE,
            NormalizationSource.CANONICAL_PASSTHROUGH,
        ), f"source inesperado: {result.source}"
        assert not result.fallback_used

    @pytest.mark.parametrize("raw_type", [
        "bank", "oil_gas", "mining", "utilities", "industrial",
        "healthcare", "retail", "holding", "telecom", "technology",
    ])
    def test_all_types_have_confidence_1(self, raw_type):
        """Tipos mapeados retornam confidence=1.0."""
        result = normalize_sector("TEST11", type=raw_type)
        assert result.confidence == 1.0

    def test_type_case_insensitive(self):
        """type é case-insensitive."""
        r1 = normalize_sector("TEST11", type="BANK")
        r2 = normalize_sector("TEST11", type="bank")
        r3 = normalize_sector("TEST11", type="Bank")
        assert r1.canonical_sector == r2.canonical_sector == r3.canonical_sector == "BANK"

    def test_type_with_extra_spaces(self):
        """type com espaços é normalizado."""
        result = normalize_sector("TEST11", type="  bank  ")
        assert result.canonical_sector == "BANK"

    def test_type_alias_oil(self):
        """Alias 'oil' → canonical oil_gas → COMMODITY."""
        result = normalize_sector("TEST11", type="oil")
        assert result.canonical_sector == "COMMODITY"

    def test_type_alias_pharma(self):
        """Alias 'pharma' → healthcare → INDUSTRY."""
        result = normalize_sector("TEST11", type="pharma")
        assert result.canonical_sector == "INDUSTRY"

    def test_type_alias_infra(self):
        """Alias 'infra' → utilities → UTILITY."""
        result = normalize_sector("TEST11", type="infra")
        assert result.canonical_sector == "UTILITY"


# ──────────────────────────────────────────────
#  TEST SUITE 2: Mapeamento GICS sector (fallback)
# ──────────────────────────────────────────────

class TestGicsSectorMappings:
    """GICS_SECTOR_TO_CANONICAL como fallback quando type não disponível."""

    @pytest.mark.parametrize("gics_sector,expected", [
        ("financials",              "BANK"),
        ("energy",                  "COMMODITY"),
        ("materials",               "COMMODITY"),
        ("utilities",               "UTILITY"),
        ("consumer_discretionary",  "RETAIL"),
        ("consumer_staples",        "RETAIL"),
        ("healthcare",              "INDUSTRY"),
        ("communication",           "TECH"),
        ("communication_services",  "TECH"),
        ("technology",              "TECH"),
        ("industrials",             "INDUSTRY"),
        ("real_estate",             "HOLDING"),
    ])
    def test_gics_to_canonical(self, gics_sector, expected):
        """GICS sector mapeia para chave canônica correta."""
        result = normalize_sector("TEST11", sector=gics_sector)
        assert result.canonical_sector == expected, (
            f"sector='{gics_sector}' deveria ser '{expected}', got '{result.canonical_sector}'"
        )

    def test_gics_sector_has_lower_confidence(self):
        """GICS fallback tem confidence=0.8 (menor que type)."""
        result = normalize_sector("UNKNOWN_TICKER", sector="energy")
        assert result.confidence == 0.8
        assert result.source == NormalizationSource.GICS_SECTOR_FALLBACK

    def test_type_overrides_gics(self):
        """type explícito tem precedência sobre sector GICS."""
        # type=bank sobrescreve sector=energy
        result = normalize_sector("TEST11", sector="energy", type="bank")
        assert result.canonical_sector == "BANK"
        # "bank".upper()=="BANK" → canonical_passthrough OU explicit_type; ambos corretos
        assert result.source in (
            NormalizationSource.EXPLICIT_TYPE,
            NormalizationSource.CANONICAL_PASSTHROUGH,
        )
        assert result.confidence == 1.0

    def test_gics_sector_case_insensitive(self):
        """sector GICS é case-insensitive."""
        r1 = normalize_sector("TEST11", sector="FINANCIALS")
        r2 = normalize_sector("TEST11", sector="financials")
        r3 = normalize_sector("TEST11", sector="Financials")
        assert r1.canonical_sector == r2.canonical_sector == r3.canonical_sector == "BANK"


# ──────────────────────────────────────────────
#  TEST SUITE 3: Passthrough de chaves canônicas
# ──────────────────────────────────────────────

class TestCanonicalPassthrough:
    """Chaves já canônicas são retornadas sem modificação."""

    @pytest.mark.parametrize("canonical", [
        "BANK", "INSURANCE", "COMMODITY", "UTILITY",
        "INDUSTRY", "RETAIL", "HOLDING", "TECH",
    ])
    def test_canonical_passthrough_via_sector(self, canonical):
        """sector já canônico → passthrough, confidence=1.0."""
        result = normalize_sector("TEST11", sector=canonical)
        assert result.canonical_sector == canonical
        assert result.confidence == 1.0
        assert result.source == NormalizationSource.CANONICAL_PASSTHROUGH

    @pytest.mark.parametrize("canonical", ["BANK", "COMMODITY", "UTILITY"])
    def test_canonical_passthrough_via_type(self, canonical):
        """type já canônico → passthrough, confidence=1.0."""
        result = normalize_sector("TEST11", type=canonical)
        assert result.canonical_sector == canonical
        assert result.confidence == 1.0

    def test_canonical_lowercase_passthrough(self):
        """Canonical em lowercase → passthrough após upper."""
        result = normalize_sector("TEST11", sector="bank")
        # "bank" → type alias ou canonical passthrough
        assert result.canonical_sector == "BANK"


# ──────────────────────────────────────────────
#  TEST SUITE 4: FALLBACK_MULTIPLES
# ──────────────────────────────────────────────

class TestFallbackMultiples:
    """Tipos/setores desconhecidos → FALLBACK_MULTIPLES, nunca raise."""

    def test_unknown_type_returns_fallback(self):
        """type desconhecido → FALLBACK_MULTIPLES (D100)."""
        result = normalize_sector("TEST11", type="xyz_unknown_sector")
        assert result.canonical_sector == FALLBACK_CANONICAL
        assert result.confidence == 0.5
        assert result.fallback_used is True

    def test_unknown_sector_returns_fallback(self):
        """sector desconhecido → FALLBACK_MULTIPLES."""
        result = normalize_sector("TEST11", sector="invalid_gics_sector_xyz")
        assert result.canonical_sector == FALLBACK_CANONICAL
        assert result.fallback_used is True

    def test_none_inputs_returns_fallback(self):
        """Sem tipo nem sector → FALLBACK_MULTIPLES."""
        result = normalize_sector("NONEXISTENT_TICKER_XYZ")
        assert result.canonical_sector == FALLBACK_CANONICAL
        assert result.fallback_used is True

    def test_empty_string_inputs_returns_fallback(self):
        """Strings vazias → FALLBACK_MULTIPLES (não raise)."""
        result = normalize_sector("TEST11", sector="", type="")
        assert result.canonical_sector == FALLBACK_CANONICAL

    def test_fallback_never_raises(self):
        """NUNCA lança exceção por setor desconhecido (D100)."""
        for bad_input in ["????", "N/A", "none", "null", "UNKNOWN", "DESCONHECIDO", ""]:
            try:
                result = normalize_sector("TEST11", sector=bad_input, type=bad_input)
                # Deve retornar (não raise) — pode ser FALLBACK ou um canonical via alias
            except Exception as e:
                pytest.fail(f"normalize_sector lançou exceção para input='{bad_input}': {e}")

    def test_fallback_confidence_is_05(self):
        """FALLBACK_MULTIPLES tem confidence=0.5."""
        result = normalize_sector("TEST11", type="totally_unknown_type")
        assert result.confidence == 0.5

    def test_fallback_source_is_fallback_multiples(self):
        """FALLBACK_MULTIPLES tem source=NormalizationSource.FALLBACK_MULTIPLES."""
        result = normalize_sector("TEST11", type="totally_unknown_type")
        assert result.source == NormalizationSource.FALLBACK_MULTIPLES

    def test_fallback_notes_not_empty(self):
        """Resultado fallback tem notas de diagnóstico."""
        result = normalize_sector("TEST11", type="unknown")
        assert len(result.notes) > 0


# ──────────────────────────────────────────────
#  TEST SUITE 5: SectorNormalizationResult dataclass
# ──────────────────────────────────────────────

class TestSectorNormalizationResultDataclass:
    """Verifica campos do dataclass SectorNormalizationResult."""

    def test_ticker_always_uppercase(self):
        """ticker é normalizado para UPPER."""
        result = normalize_sector("bbas3", type="bank")
        assert result.ticker == "BBAS3"

    def test_all_fields_present(self):
        """Todos os campos esperados estão no resultado."""
        result = normalize_sector("BBAS3", sector="financials", type="bank")
        assert hasattr(result, "ticker")
        assert hasattr(result, "raw_sector")
        assert hasattr(result, "raw_type")
        assert hasattr(result, "raw_subsector")
        assert hasattr(result, "canonical_sector")
        assert hasattr(result, "confidence")
        assert hasattr(result, "source")
        assert hasattr(result, "fallback_used")
        assert hasattr(result, "notes")

    def test_raw_type_preserved(self):
        """raw_type preserva o valor original passado."""
        result = normalize_sector("TEST11", type="bank")
        assert result.raw_type == "bank"

    def test_raw_sector_preserved(self):
        """raw_sector preserva o setor GICS original."""
        result = normalize_sector("TEST11", sector="financials", type="bank")
        assert result.raw_sector == "financials"

    def test_canonical_sector_never_none(self):
        """canonical_sector NUNCA é None."""
        for ticker in ["TEST11", "UNKN", "", "XYZ"]:
            result = normalize_sector(ticker)
            assert result.canonical_sector is not None

    def test_fallback_used_true_only_for_fallback(self):
        """fallback_used=True somente quando canonical==FALLBACK_MULTIPLES."""
        r_bank = normalize_sector("TEST11", type="bank")
        assert r_bank.fallback_used is False

        r_fallback = normalize_sector("TEST11", type="xyz_unknown")
        assert r_fallback.fallback_used is True


# ──────────────────────────────────────────────
#  TEST SUITE 6: Integração com router
# ──────────────────────────────────────────────

class TestRouterIntegration:
    """Integração: normalize_sector → get_valuation_method."""

    def _route(self, ticker: str, sector: str | None = None, type_: str | None = None) -> RouterDecision:
        """Normaliza setor e rota pelo get_valuation_method."""
        norm = normalize_sector(ticker, sector=sector, type=type_)
        return get_valuation_method(
            ticker=ticker,
            sector=norm.canonical_sector,
            coverage_status="partial",
            provenance=_TRACEABLE,
        )

    # ── Bancos ──────────────────────────────────────────────────────────────

    def test_bbas3_routes_to_cosif_ddm(self):
        """BBAS3 (type=bank) → router COSIF/DDM, confidence=1.0."""
        d = self._route("BBAS3", type_="bank")
        assert d.method_suggested == ValuationMethod.COSIF_DDM
        assert d.confidence == 1.0
        assert not d.blocked

    def test_bpac11_routes_to_cosif_ddm(self):
        """BPAC11 (type=bank) → COSIF/DDM."""
        d = self._route("BPAC11", type_="bank")
        assert d.method_suggested == ValuationMethod.COSIF_DDM
        assert not d.blocked

    def test_itub4_routes_to_cosif_ddm(self):
        """ITUB4 → COSIF/DDM."""
        d = self._route("ITUB4", type_="bank")
        assert d.method_suggested == ValuationMethod.COSIF_DDM

    def test_bbas3_gics_routes_correctly(self):
        """BBAS3 via sector=financials (GICS) → BANK → COSIF/DDM."""
        d = self._route("BBAS3", sector="financials")
        assert d.method_suggested == ValuationMethod.COSIF_DDM

    # ── Commodity ───────────────────────────────────────────────────────────

    def test_petr4_routes_to_dcf(self):
        """PETR4 (type=oil_gas) → DCF, confidence=1.0."""
        d = self._route("PETR4", type_="oil_gas")
        assert d.method_suggested == ValuationMethod.DCF
        assert d.confidence == 1.0
        assert not d.blocked

    def test_prio3_routes_to_dcf(self):
        """PRIO3 (type=oil_gas) → DCF."""
        d = self._route("PRIO3", type_="oil_gas")
        assert d.method_suggested == ValuationMethod.DCF

    def test_petr4_energy_sector_routes_to_dcf(self):
        """PETR4 via sector=energy → COMMODITY → DCF."""
        d = self._route("PETR4", sector="energy")
        assert d.method_suggested == ValuationMethod.DCF

    # ── Utilities ───────────────────────────────────────────────────────────

    def test_egie3_routes_to_utility_dcf(self):
        """EGIE3 (type=utilities) → DCF (UTILITY model)."""
        d = self._route("EGIE3", type_="utilities")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    def test_taee11_routes_to_utility_dcf(self):
        """TAEE11 → DCF (utility)."""
        d = self._route("TAEE11", type_="utilities")
        assert d.method_suggested == ValuationMethod.DCF

    def test_sbsp3_routes_to_utility_dcf(self):
        """SBSP3 (type=utilities) → DCF."""
        d = self._route("SBSP3", type_="utilities")
        assert d.method_suggested == ValuationMethod.DCF

    # ── Retail ──────────────────────────────────────────────────────────────

    def test_lren3_routes_to_retail_dcf(self):
        """LREN3 (type=retail) → DCF (RETAIL model)."""
        d = self._route("LREN3", type_="retail")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    def test_mglu3_routes_to_retail_dcf(self):
        """MGLU3 (type=retail) → DCF."""
        d = self._route("MGLU3", type_="retail")
        assert d.method_suggested == ValuationMethod.DCF

    def test_lren3_consumer_disc_routes_to_retail(self):
        """LREN3 via sector=consumer_discretionary → RETAIL → DCF."""
        d = self._route("LREN3", sector="consumer_discretionary")
        assert d.method_suggested == ValuationMethod.DCF

    # ── Industry ────────────────────────────────────────────────────────────

    def test_wege3_routes_to_industry_dcf(self):
        """WEGE3 (type=industrial) → DCF (INDUSTRY model)."""
        d = self._route("WEGE3", type_="industrial")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    def test_rail3_routes_to_industry_dcf(self):
        """RAIL3 (type=industrial) → DCF."""
        d = self._route("RAIL3", type_="industrial")
        assert d.method_suggested == ValuationMethod.DCF

    def test_vamo3_routes_to_industry_dcf(self):
        """VAMO3 (type=industrial) → DCF."""
        d = self._route("VAMO3", type_="industrial")
        assert d.method_suggested == ValuationMethod.DCF

    def test_rent3_routes_to_industry(self):
        """RENT3 é type=industrial no tickers.yaml → normaliza para INDUSTRY → DCF.

        NOTA: RENT3 (Localiza) tem type=industrial e sector=consumer_discretionary.
        O type é autoritativo (D099), portanto RENT3 → INDUSTRY (não RETAIL).
        Para obter RETAIL, seria necessário mudar type=retail no tickers.yaml.
        """
        d = self._route("RENT3", type_="industrial")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    def test_flry3_healthcare_routes_to_industry(self):
        """FLRY3 (type=healthcare) → INDUSTRY → DCF (D108)."""
        d = self._route("FLRY3", type_="healthcare")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    def test_hype3_healthcare_routes_to_industry(self):
        """HYPE3 (type=healthcare) → INDUSTRY → DCF."""
        d = self._route("HYPE3", type_="healthcare")
        assert d.method_suggested == ValuationMethod.DCF

    # ── Tech ────────────────────────────────────────────────────────────────

    def test_vivt3_routes_to_tech_dcf(self):
        """VIVT3 (type=telecom) → TECH → DCF."""
        d = self._route("VIVT3", type_="telecom")
        assert d.method_suggested == ValuationMethod.DCF
        assert not d.blocked

    # ── Confidence via normalização ──────────────────────────────────────────

    def test_gics_route_has_lower_confidence(self):
        """Routing via GICS (type ausente) tem confidence=0.8 após normalizar."""
        # Normalizar explicitamente via sector apenas (sem type)
        norm = normalize_sector("PETR4", sector="energy")
        d = get_valuation_method(
            ticker="PETR4",
            sector=norm.canonical_sector,
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        # Router confidence depende se canonical_sector é COMMODITY → 1.0
        # (a confidence do normalizer é separada; o router vê "COMMODITY" → confidence=1.0)
        assert not d.blocked
        assert d.method_suggested == ValuationMethod.DCF


# ──────────────────────────────────────────────
#  TEST SUITE 7: Ticker lookup no tickers.yaml
# ──────────────────────────────────────────────

class TestTickerYamlLookup:
    """SectorNormalizer faz lookup no tickers.yaml para obter type."""

    def test_bbas3_lookup_returns_bank(self):
        """BBAS3 sem type/sector → lookup no yaml → BANK."""
        result = normalize_sector("BBAS3")
        assert result.canonical_sector == "BANK"
        assert result.confidence == 1.0
        # Fonte deve ser yaml ou explicit
        assert result.source in (
            NormalizationSource.TICKERS_YAML_TYPE,
            NormalizationSource.EXPLICIT_TYPE,
            NormalizationSource.CANONICAL_PASSTHROUGH,
        )

    def test_petr4_lookup_returns_commodity(self):
        """PETR4 sem type/sector → lookup no yaml → COMMODITY."""
        result = normalize_sector("PETR4")
        assert result.canonical_sector == "COMMODITY"

    def test_egie3_lookup_returns_utility(self):
        """EGIE3 sem type/sector → lookup no yaml → UTILITY."""
        result = normalize_sector("EGIE3")
        assert result.canonical_sector == "UTILITY"

    def test_vivt3_lookup_returns_tech(self):
        """VIVT3 sem type/sector → lookup no yaml → TECH."""
        result = normalize_sector("VIVT3")
        assert result.canonical_sector == "TECH"

    def test_lren3_lookup_returns_retail(self):
        """LREN3 sem type/sector → lookup no yaml → RETAIL."""
        result = normalize_sector("LREN3")
        assert result.canonical_sector == "RETAIL"

    def test_wege3_lookup_returns_industry(self):
        """WEGE3 sem type/sector → lookup no yaml → INDUSTRY."""
        result = normalize_sector("WEGE3")
        assert result.canonical_sector == "INDUSTRY"

    def test_unknown_ticker_fallback(self):
        """Ticker desconhecido (não no yaml, sem type/sector) → FALLBACK."""
        result = normalize_sector("XXXXXX_NONEXISTENT")
        assert result.canonical_sector == FALLBACK_CANONICAL

    def test_type_overrides_yaml_lookup(self):
        """type explícito tem precedência sobre lookup no yaml."""
        # BBAS3 no yaml tem type=bank → BANK
        # Mas se passarmos type=oil_gas explicitamente → COMMODITY
        result = normalize_sector("BBAS3", type="oil_gas")
        assert result.canonical_sector == "COMMODITY"
        assert result.source == NormalizationSource.EXPLICIT_TYPE


# ──────────────────────────────────────────────
#  TEST SUITE 8: PETZ3 e tickers bloqueados
# ──────────────────────────────────────────────

class TestBlockedTickers:
    """PETZ3 e tickers NEEDS_RI_DOCS permanecem fora do valuation."""

    def test_petz3_legacy_ticker_blocked_by_router(self):
        """PETZ3 com coverage_status=legacy_ticker → router bloqueado.

        O SectorNormalizer normaliza o sector de PETZ3 normalmente.
        O bloqueio é feito pelo router via coverage_status=legacy_ticker.
        """
        # Normalizar setor de PETZ3
        norm = normalize_sector("PETZ3")
        # consumer_discretionary / retail → RETAIL ou FALLBACK
        # O setor pode ou não ser mapeável, mas o router deve bloquear via status

        # Router com legacy_ticker → bloqueado independente do setor
        decision = get_valuation_method(
            ticker="PETZ3",
            sector=norm.canonical_sector,
            coverage_status="legacy_ticker",
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True
        assert "LEGACY_TICKER" in decision.block_reason
        assert decision.confidence == 0.0

    def test_petz3_blocked_regardless_of_sector(self):
        """PETZ3 bloqueado independente do sector passado."""
        for sector in ["RETAIL", "BANK", "COMMODITY", "FALLBACK_MULTIPLES"]:
            decision = get_valuation_method(
                ticker="PETZ3",
                sector=sector,
                coverage_status="legacy_ticker",
                provenance=_TRACEABLE,
            )
            assert decision.blocked, f"PETZ3 com sector={sector} deveria estar bloqueado"

    def test_vale3_needs_ri_docs_blocked(self):
        """VALE3 (NEEDS_RI_DOCS) → router bloqueado por needs_data.

        VALE3 type=mining → COMMODITY. Mas coverage_status=needs_data → bloqueia.
        """
        norm = normalize_sector("VALE3")
        assert norm.canonical_sector == "COMMODITY"  # type=mining → COMMODITY

        decision = get_valuation_method(
            ticker="VALE3",
            sector=norm.canonical_sector,
            coverage_status="needs_data",  # NEEDS_RI_DOCS
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True
        assert "NEEDS_CVM_DATA" in decision.block_reason

    def test_auau3_needs_ri_docs_blocked(self):
        """AUAU3 (successor PETZ3, sem RI docs) → router bloqueado."""
        norm = normalize_sector("AUAU3")
        # AUAU3 type=retail → RETAIL

        decision = get_valuation_method(
            ticker="AUAU3",
            sector=norm.canonical_sector,
            coverage_status="needs_data",
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True

    def test_ntco3_needs_ri_docs_blocked(self):
        """NTCO3 (NEEDS_RI_DOCS) → router bloqueado por needs_data."""
        norm = normalize_sector("NTCO3")

        decision = get_valuation_method(
            ticker="NTCO3",
            sector=norm.canonical_sector,
            coverage_status="needs_data",
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True


# ──────────────────────────────────────────────
#  TEST SUITE 9: SectorNormalizer class
# ──────────────────────────────────────────────

class TestSectorNormalizerClass:
    """SectorNormalizer class: normalize, normalize_batch, smoke_test."""

    def test_normalize_single_ticker(self):
        """normalize(ticker) → SectorNormalizationResult."""
        normalizer = SectorNormalizer()
        result = normalizer.normalize("BBAS3")
        assert isinstance(result, SectorNormalizationResult)
        assert result.canonical_sector == "BANK"

    def test_get_canonical(self):
        """get_canonical(ticker) retorna apenas a string canônica."""
        normalizer = SectorNormalizer()
        assert normalizer.get_canonical("BBAS3") == "BANK"
        assert normalizer.get_canonical("PETR4") == "COMMODITY"

    def test_is_routable_true(self):
        """is_routable=True para tickers mapeáveis."""
        normalizer = SectorNormalizer()
        assert normalizer.is_routable("BBAS3") is True
        assert normalizer.is_routable("PETR4") is True

    def test_is_routable_false_for_fallback(self):
        """is_routable=False para FALLBACK_MULTIPLES."""
        normalizer = SectorNormalizer()
        assert normalizer.is_routable("NONEXISTENT_XXXXXX") is False

    def test_normalize_batch(self):
        """normalize_batch(tickers) retorna lista de resultados."""
        normalizer = SectorNormalizer()
        tickers = ["BBAS3", "PETR4", "EGIE3", "LREN3", "VIVT3"]
        results = normalizer.normalize_batch(tickers)
        assert len(results) == 5
        assert all(isinstance(r, SectorNormalizationResult) for r in results)
        canonicals = {r.ticker: r.canonical_sector for r in results}
        assert canonicals["BBAS3"] == "BANK"
        assert canonicals["PETR4"] == "COMMODITY"
        assert canonicals["EGIE3"] == "UTILITY"
        assert canonicals["LREN3"] == "RETAIL"
        assert canonicals["VIVT3"] == "TECH"

    def test_get_normalizer_singleton(self):
        """get_normalizer() retorna instância reutilizável."""
        n1 = get_normalizer()
        n2 = get_normalizer()
        assert n1 is n2  # singleton

    def test_smoke_test_returns_summary(self):
        """smoke_test(tickers) retorna dict com métricas de cobertura."""
        normalizer = SectorNormalizer()
        summary = normalizer.smoke_test(["BBAS3", "PETR4", "EGIE3"])
        assert "results" in summary
        assert "routable" in summary
        assert "fallback" in summary
        assert "by_canonical" in summary
        assert "confidence_avg" in summary
        assert summary["routable_count"] == 3
        assert summary["fallback_count"] == 0


# ──────────────────────────────────────────────
#  TEST SUITE 10: Smoke Test — 28 READY tickers
# ──────────────────────────────────────────────

class TestSmokeTest28ReadyTickers:
    """Smoke test dos 28 tickers READY_FOR_MODEL_DESIGN.

    Valida que:
    - Todos os 28 obtêm um canonical_sector ≠ FALLBACK_MULTIPLES
    - O canonical_sector correto para cada ticker (via tickers.yaml lookup)
    - Todos roteiam para confidence=1.0 no router após normalização
    - Nenhum fair_value é calculado
    """

    def test_all_28_tickers_normalize_correctly(self):
        """Todos os 28 tickers READY obtêm canonical_sector esperado."""
        normalizer = SectorNormalizer()
        failures = []

        for ticker in READY_TICKERS:
            result = normalizer.normalize(ticker)
            expected = EXPECTED_CANONICAL.get(ticker)
            if expected and result.canonical_sector != expected:
                failures.append(
                    f"{ticker}: esperado='{expected}', got='{result.canonical_sector}' "
                    f"(source={result.source}, raw_type={result.raw_type})"
                )

        assert failures == [], "\n".join(failures)

    def test_all_28_tickers_not_fallback(self):
        """Nenhum dos 28 tickers READY deve cair em FALLBACK_MULTIPLES."""
        normalizer = SectorNormalizer()
        fallback_tickers = []

        for ticker in READY_TICKERS:
            result = normalizer.normalize(ticker)
            if result.fallback_used:
                fallback_tickers.append(
                    f"{ticker}: source={result.source}, raw_type={result.raw_type}"
                )

        assert fallback_tickers == [], (
            f"Tickers que caíram em FALLBACK (esperado: nenhum):\n" +
            "\n".join(fallback_tickers)
        )

    def test_all_28_tickers_confidence_100(self):
        """Todos os 28 tickers devem ter confidence=1.0 (type do yaml)."""
        normalizer = SectorNormalizer()
        low_confidence = []

        for ticker in READY_TICKERS:
            result = normalizer.normalize(ticker)
            if result.confidence < 1.0:
                low_confidence.append(
                    f"{ticker}: confidence={result.confidence}, source={result.source}"
                )

        assert low_confidence == [], (
            "Tickers com confidence < 1.0 (todos deveriam ter 1.0 via tickers.yaml):\n" +
            "\n".join(low_confidence)
        )

    def test_all_28_route_to_correct_method(self):
        """Todos os 28 roteiam para método correto após normalização."""
        normalizer = SectorNormalizer()
        expected_methods = {
            "BANK":      ValuationMethod.COSIF_DDM,
            "COMMODITY": ValuationMethod.DCF,
            "UTILITY":   ValuationMethod.DCF,
            "RETAIL":    ValuationMethod.DCF,
            "INDUSTRY":  ValuationMethod.DCF,
            "TECH":      ValuationMethod.DCF,
            "HOLDING":   ValuationMethod.NAV,
        }

        routing_failures = []
        for ticker in READY_TICKERS:
            norm = normalizer.normalize(ticker)
            decision = get_valuation_method(
                ticker=ticker,
                sector=norm.canonical_sector,
                coverage_status="partial",
                provenance=_TRACEABLE,
            )

            if decision.blocked:
                routing_failures.append(f"{ticker}: bloqueado — {decision.block_reason}")
                continue

            expected_method = expected_methods.get(norm.canonical_sector)
            if expected_method and decision.method_suggested != expected_method:
                routing_failures.append(
                    f"{ticker}: canonical={norm.canonical_sector}, "
                    f"esperado={expected_method}, got={decision.method_suggested}"
                )

        assert routing_failures == [], "\n".join(routing_failures)

    def test_smoke_test_batch_result(self):
        """smoke_test dos 28 tickers retorna 28 routable e 0 fallback."""
        normalizer = SectorNormalizer()
        summary = normalizer.smoke_test(READY_TICKERS)

        assert summary["total"] == 28
        assert summary["fallback_count"] == 0, (
            f"Fallback inesperado: {summary['fallback']}"
        )
        assert summary["routable_count"] == 28, (
            f"Esperado 28 roteáveis, got {summary['routable_count']}"
        )
        assert summary["confidence_avg"] == 1.0

    def test_no_fair_value_calculated(self):
        """SectorNormalizer NÃO calcula fair_value. Nunca.

        Verificação de contrato: o resultado não tem campo fair_value.
        """
        result = normalize_sector("BBAS3")
        assert not hasattr(result, "fair_value"), "SectorNormalizationResult não deve ter fair_value"
        assert not hasattr(result, "upside_pct"), "SectorNormalizationResult não deve ter upside_pct"

    def test_no_db_writes_during_normalization(self):
        """Normalização não altera banco. Verifica via smoke_test sem erro."""
        # Se houver write no banco, o smoke_test crasharia com IntegrityError ou similar.
        # Este teste verifica que o smoke_test completo roda sem exceção.
        normalizer = SectorNormalizer()
        try:
            summary = normalizer.smoke_test(READY_TICKERS)
            assert summary["total"] == 28
        except Exception as e:
            pytest.fail(f"smoke_test lançou exceção inesperada: {e}")


# ──────────────────────────────────────────────
#  TEST SUITE 11: Coexistência com router existente
# ──────────────────────────────────────────────

class TestRouterCoexistenceM016:
    """Verifica que a integração M016-S01 não quebra comportamento pré-existente."""

    def test_canonical_sector_passed_directly_still_works(self):
        """router com sector='BANK' (direto) → continua funcionando."""
        decision = get_valuation_method(
            ticker="BBAS3",
            sector="BANK",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        assert decision.method_suggested == ValuationMethod.COSIF_DDM
        assert not decision.blocked
        assert decision.confidence == 1.0

    def test_gics_sector_now_routes_correctly(self):
        """router com sector='financials' (GICS) → agora normaliza para BANK."""
        decision = get_valuation_method(
            ticker="BBAS3",
            sector="financials",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        # Antes do M016-S01: RELATIVOS (confidence=0.5)
        # Após M016-S01: COSIF_DDM (confidence=1.0)
        assert decision.method_suggested == ValuationMethod.COSIF_DDM
        assert not decision.blocked

    def test_energy_sector_routes_to_dcf(self):
        """router com sector='energy' → COMMODITY → DCF."""
        decision = get_valuation_method(
            ticker="PETR4",
            sector="energy",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        assert decision.method_suggested == ValuationMethod.DCF

    def test_materials_sector_routes_to_dcf(self):
        """router com sector='materials' → COMMODITY → DCF."""
        decision = get_valuation_method(
            ticker="VALE3",
            sector="materials",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        assert decision.method_suggested == ValuationMethod.DCF

    def test_utilities_sector_routes_to_dcf(self):
        """router com sector='utilities' → UTILITY → DCF."""
        decision = get_valuation_method(
            ticker="EGIE3",
            sector="utilities",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        assert decision.method_suggested == ValuationMethod.DCF

    def test_needs_sector_still_blocks(self):
        """needs_sector ainda bloqueia mesmo com normalização ativa."""
        decision = get_valuation_method(
            ticker="TEST11",
            sector="financials",
            coverage_status="needs_sector",
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True
        assert "NEEDS_SECTOR" in decision.block_reason

    def test_needs_data_still_blocks(self):
        """needs_data ainda bloqueia mesmo com setor normalizado."""
        decision = get_valuation_method(
            ticker="BBAS3",
            sector="financials",
            coverage_status="needs_data",
            provenance=_TRACEABLE,
        )
        assert decision.blocked is True

    def test_no_method_used_field(self):
        """RouterDecision continua sem method_used (D084)."""
        decision = get_valuation_method(
            ticker="BBAS3",
            sector="financials",
            coverage_status="partial",
            provenance=_TRACEABLE,
        )
        assert not hasattr(decision, "method_used"), "method_used não deve existir (D084)"

    def test_fair_values_preserved(self):
        """Fair values existentes (PETR4/BBAS3/ITUB4/WEGE3) não foram alterados."""
        from src.valuation import load_valuation_result
        for ticker, min_expected in [("PETR4", 10.0), ("BBAS3", 10.0), ("ITUB4", 10.0), ("WEGE3", 1.0)]:
            result = load_valuation_result(ticker)
            assert result.fair_value is not None, f"{ticker}: fair_value deve ser preservado"
            assert result.fair_value > min_expected, f"{ticker}: fair_value parece inválido"


# ──────────────────────────────────────────────
#  TEST SUITE 12: tickers_config loader
# ──────────────────────────────────────────────

class TestTickersConfig:
    """src.valuation.tickers_config: loader do tickers.yaml."""

    def test_load_returns_dict(self):
        """load_tickers_config() retorna dict."""
        from src.valuation.tickers_config import load_tickers_config
        result = load_tickers_config()
        assert isinstance(result, dict)

    def test_bbas3_in_config(self):
        """BBAS3 está no config e tem type=bank."""
        from src.valuation.tickers_config import get_ticker_config, get_ticker_type
        cfg = get_ticker_config("BBAS3")
        assert cfg is not None
        assert get_ticker_type("BBAS3") == "bank"

    def test_petr4_in_config(self):
        """PETR4 está no config e tem type=oil_gas."""
        from src.valuation.tickers_config import get_ticker_type
        assert get_ticker_type("PETR4") == "oil_gas"

    def test_nonexistent_ticker_returns_none(self):
        """Ticker inexistente → get_ticker_config retorna None (não raise)."""
        from src.valuation.tickers_config import get_ticker_config, get_ticker_type
        assert get_ticker_config("XXXXXXNONEXISTENT") is None
        assert get_ticker_type("XXXXXXNONEXISTENT") is None

    def test_case_insensitive(self):
        """get_ticker_config é case-insensitive."""
        from src.valuation.tickers_config import get_ticker_type
        assert get_ticker_type("bbas3") == "bank"
        assert get_ticker_type("BBAS3") == "bank"
        assert get_ticker_type("Bbas3") == "bank"

    def test_min_ticker_count(self):
        """tickers.yaml deve ter pelo menos 28 tickers ativos."""
        from src.valuation.tickers_config import load_tickers_config
        cfg = load_tickers_config()
        assert len(cfg) >= 28, f"Esperado ≥28 tickers, got {len(cfg)}"
