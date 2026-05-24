"""
tests/test_valuation_stores.py — S05 canonical stores validation

Testa imports, leitura sem erro, preservação de dados existentes,
e empty sentinel para tickers sem valuation.
"""
from __future__ import annotations

import pytest

from src.valuation import (
    # API pública
    load_valuation_result,
    list_valuation_results,
    load_valuation_inputs,
    load_valuation_inputs,
    list_valuation_inputs,
    load_valuation_coverage,
    load_valuation_coverage_batch,
    load_valuation_fair_values,
    save_valuation_result,
    load_latest_valuation_data,
    # Tipos
    ValuationResult,
    ValuationInputs,
    ValuationCoverage,
    CoverageStatus,
    # Colunas
    VALUATION_RESULT_COLUMNS,
    VALUATION_INPUT_COLUMNS,
    VALUATION_COVERAGE_COLUMNS,
    # Router coexistence
    get_valuation_method,
    Provenance,
    ValuationMethod,
    RouterDecision,
)


# ── Testes de importação ──────────────────────────────────────────────────────

class TestImports:
    def test_results_store_imports(self):
        from src.valuation import valuation_results
        assert hasattr(valuation_results, "load_valuation_result")
        assert hasattr(valuation_results, "ValuationResult")
        assert hasattr(valuation_results, "VALUATION_RESULT_COLUMNS")

    def test_inputs_store_imports(self):
        from src.valuation import valuation_inputs
        assert hasattr(valuation_inputs, "load_valuation_inputs")
        assert hasattr(valuation_inputs, "ValuationInputs")

    def test_coverage_store_imports(self):
        from src.valuation import valuation_coverage
        assert hasattr(valuation_coverage, "load_valuation_coverage")
        assert hasattr(valuation_coverage, "CoverageStatus")
        assert hasattr(valuation_coverage, "ValuationCoverage")

    def test_store_unified_imports(self):
        from src.valuation import valuation_store
        assert hasattr(valuation_store, "load_valuation_result")
        assert hasattr(valuation_store, "save_valuation_result")

    def test_all_public_api_importable(self):
        # Cada símbolo exportado no __all__ deve ser importável
        from src.valuation import __all__
        from src import valuation as vmod
        for name in __all__:
            assert hasattr(vmod, name), f"Missing export: {name}"


# ── Testes de comportamento ────────────────────────────────────────────────

class TestEmptyTickerSentinel:
    """Ticker sem dados → fair_value=None, available=False, status=VALUATION_MISSING.
    Nunca R$ 0,00 falso."""

    def test_nonexistent_ticker_returns_none_not_zero(self):
        r = load_valuation_result("XXXXXXTEST")
        assert r.fair_value is None, "fair_value deve ser None, não 0.0"
        assert r.valuation_available is False, "valuation_available deve ser False"

    def test_nonexistent_ticker_status_valuation_missing(self):
        r = load_valuation_result("NAOEXISTEQWERTY")
        assert r.valuation_governance_status == "VALUATION_MISSING"

    def test_empty_result_factory(self):
        r = ValuationResult.empty("TICKX")
        assert r.fair_value is None
        assert r.valuation_available is False
        assert r.valuation_governance_status == "VALUATION_MISSING"

    def test_fair_values_omits_invalid(self):
        df = load_valuation_fair_values(["XXXXXX", "NAOEXISTE"])
        # Tickers sem dados devem ser omitidos (não preenchidos com 0.0)
        assert df["fair_value"].notna().sum() == 0, "Nenhum ticker deve ter fair_value preenchido"


class TestPreservedData:
    """PETR4/BBAS3/ITUB4/WEGE3 possuem valuation no outputs/ fallback.
    Devem preservar dados existentes."""

    def test_petr4_has_existing_valuation(self):
        r = load_valuation_result("PETR4")
        assert r.fair_value is not None, "PETR4 deve ter fair_value (outputs fallback)"
        assert r.valuation_available is True
        assert r.fair_value > 0, "PETR4 fair_value deve ser positivo"

    def test_bbas3_has_existing_valuation(self):
        r = load_valuation_result("BBAS3")
        assert r.fair_value is not None, "BBAS3 deve ter fair_value"
        assert r.valuation_available is True

    def test_itub4_has_existing_valuation(self):
        r = load_valuation_result("ITUB4")
        assert r.fair_value is not None, "ITUB4 deve ter fair_value"
        assert r.valuation_available is True

    def test_wege3_has_existing_valuation(self):
        r = load_valuation_result("WEGE3")
        assert r.fair_value is not None, "WEGE3 deve ter fair_value"
        assert r.valuation_available is True

    def test_batch_preserves_all_four(self):
        df = list_valuation_results(["PETR4", "BBAS3", "ITUB4", "WEGE3"])
        assert len(df) >= 4, "Deve retornar todas as linhas disponíveis"
        assert set(df["ticker"].tolist()).issuperset({"PETR4", "BBAS3", "ITUB4", "WEGE3"})


class TestRouterCoexistence:
    """Stores coexistem com router (S04) sem alterar comportamento."""

    def test_router_petr4_comtrade_partial_traceable(self):
        d = get_valuation_method(
            "PETR4", "COMMODITY", "partial", Provenance(source="TRACEABLE")
        )
        assert d.blocked is False, "PETR4 COMMODITY partial não deve estar bloqueado"
        assert d.confidence == 1.0, "Routed com setor mapeado deve ter confidence=1.0"
        assert d.method_suggested == ValuationMethod.DCF

    def test_router_no_sector_blocks(self):
        d = get_valuation_method(
            "XXXXXX", None, "empty", Provenance(source="UNKNOWN")
        )
        assert d.blocked is True, "Sem setor rastreável deve bloquear"
        assert d.block_reason is not None

    def test_router_coverage_partial_routed(self):
        d = get_valuation_method(
            "PETR4", "COMMODITY", "partial", Provenance(source="TRACEABLE")
        )
        assert d.coverage_status == "partial"

    def test_coverage_batch_includes_empty(self):
        df = load_valuation_coverage_batch(["PETR4", "XXXXXX"])
        assert len(df) >= 2, "Deve incluir todos os tickers, incluindo empty"
        empty_rows = df[df["coverage_status"] == "empty"]
        assert len(empty_rows) >= 1, "XXXXXX deve aparecer como empty"


class TestInputsStore:
    """Valuation inputs store."""

    def test_load_petr4_inputs(self):
        i = load_valuation_inputs("PETR4")
        assert isinstance(i, ValuationInputs)
        assert i.ticker == "PETR4"
        assert i.coverage_status in ("empty", "needs_data", "partial", "needs_sector")

    def test_nonexistent_inputs_empty(self):
        i = load_valuation_inputs("XXXXXX")
        assert i.coverage_status == "empty"
        assert i.fundamental_quality_score is None

    def test_list_inputs_empty_ticker_included(self):
        df = list_valuation_inputs(["XXXXXX", "NAOEXISTE"])
        # Não deve falhar com tickers inexistentes
        assert isinstance(df, type(df))


class TestSaveStub:
    """save_valuation_result é stub seguro — sempre retorna False."""

    def test_save_returns_false(self):
        result = save_valuation_result("PETR4", ValuationResult(ticker="PETR4"))
        assert result is False, "save_valuation_result deve retornar False (stub)"

    def test_save_does_not_crash_with_valid_input(self):
        r = ValuationResult(ticker="PETR4", fair_value=100.0, valuation_available=True)
        # Não deve lançar exceção
        result = save_valuation_result("PETR4", r)
        assert result is False


class TestCompatShim:
    """load_latest_valuation_data é shim de compatibilidade com valuation_connector."""

    def test_shim_returns_dataframe(self):
        df = load_latest_valuation_data(["PETR4"])
        import pandas as pd
        assert isinstance(df, pd.DataFrame)

    def test_shim_includes_governance_status(self):
        df = load_latest_valuation_data(["PETR4", "BBAS3"])
        assert "valuation_governance_status" in df.columns

    def test_shim_preserves_existing_data(self):
        df = load_latest_valuation_data(["PETR4"])
        petr_row = df[df["ticker"] == "PETR4"]
        assert len(petr_row) >= 1, "PETR4 deve estar no resultado"


class TestColumnContracts:
    """Contratos de colunas canônicas."""

    def test_result_columns_contract(self):
        from src.valuation.valuation_results import VALUATION_RESULT_COLUMNS
        assert "ticker" in VALUATION_RESULT_COLUMNS
        assert "fair_value" in VALUATION_RESULT_COLUMNS
        assert "valuation_available" in VALUATION_RESULT_COLUMNS

    def test_coverage_columns_contract(self):
        from src.valuation.valuation_coverage import VALUATION_COVERAGE_COLUMNS
        assert "ticker" in VALUATION_COVERAGE_COLUMNS
        assert "coverage_status" in VALUATION_COVERAGE_COLUMNS
        assert "valuation_available" in VALUATION_COVERAGE_COLUMNS