"""
tests/test_utility_model.py — M016-S04: Utility Valuation Model Tests

Cobre obrigatoriamente (M016-S04 checklist — UTILITY):
  1. WACC <= g bloqueia DCF e RAB-DCF (U-UTIL-02)
  2. FCF ausente bloqueia DCF (U-UTIL-01)
  3. RAB ausente bloqueia RAB-DCF (U-UTIL-06)
  4. net_debt ausente bloqueia todos os métodos (U-UTIL-03)
  5. shares_outstanding <= 0 bloqueia per-share (U-UTIL-04)
  6. EBITDA <= 0 bloqueia EV/EBITDA (U-UTIL-05)
  7. Cálculo DCF/FCFF correto com inputs válidos
  8. Cálculo RAB-DCF correto com inputs válidos
  9. Cálculo EV/EBITDA correto com inputs válidos
 10. preserve logic (existing_fair_value preservado com force_recalc=False)
 11. EGIE3/SBSP3/TAEE11 sem dados → NEEDS_FINANCIALS (não recebe fair_value novo)
 12. save_utility_valuation_result com write=False não grava
 13. Estrutura e exports do módulo
"""

from __future__ import annotations

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from src.valuation.models.utility_model import (
    UtilityValuationInputs,
    UtilityValuationResult,
    UtilityInputQuality,
    UtilityValuationStatus,
    UtilityValuationMethod,
    UTILITY_TICKERS,
    UTILITY_PRESERVED_FAIR_VALUES,
    DEFAULT_UTILITY_EV_EBITDA_MULTIPLE,
    UTILITY_EV_EBITDA_BY_SUBSECTOR,
    calculate_utility_valuation,
    diagnose_utility_tickers,
    save_utility_valuation_result,
    _validate_utility_shares_and_net_debt,
    _validate_utility_dcf_prerequisites,
    _validate_utility_rab_prerequisites,
    _validate_utility_ev_ebitda_prerequisites,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures auxiliares
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_dcf_inputs():
    """Inputs válidos para DCF/FCFF utility."""
    return UtilityValuationInputs(
        ticker="EGIE3",
        free_cash_flow=2_000.0,      # R$ 2 bilhões FCF
        ebitda=3_500.0,
        net_debt=5_000.0,
        shares_outstanding=500.0,    # 500M ações
        wacc=0.10,                   # 10% WACC
        terminal_growth=0.03,        # 3% crescimento terminal
        market_price=32.00,
        source_quality=UtilityInputQuality.CVM_LIVE,
        subsector="generation",
    )


@pytest.fixture
def valid_rab_dcf_inputs():
    """Inputs válidos para RAB-DCF."""
    return UtilityValuationInputs(
        ticker="TAEE11",
        rab=8_000.0,                 # R$ 8 bilhões RAB
        wacc_spread=0.02,            # 2% spread regulatório
        wacc=0.10,
        terminal_growth=0.03,
        net_debt=2_000.0,
        shares_outstanding=200.0,
        market_price=38.00,
        source_quality=UtilityInputQuality.CVM_LIVE,
        subsector="transmission",
    )


@pytest.fixture
def valid_ev_ebitda_inputs():
    """Inputs válidos apenas para EV/EBITDA."""
    return UtilityValuationInputs(
        ticker="SBSP3",
        free_cash_flow=None,
        ebitda=4_000.0,
        net_debt=10_000.0,
        shares_outstanding=700.0,
        ev_ebitda_multiple=9.0,
        market_price=28.00,
        source_quality=UtilityInputQuality.EXCEL_PIPELINE,
        subsector="sanitation",
    )


@pytest.fixture
def tmp_db(tmp_path):
    """Banco de dados temporário para testes de save."""
    return str(tmp_path / "test_utility.db")


# ─────────────────────────────────────────────────────────────────────────────
#  1. WACC <= g bloqueia DCF (U-UTIL-02)
# ─────────────────────────────────────────────────────────────────────────────

class TestWACCLeqGBlock:
    """U-UTIL-02: WACC <= terminal_growth bloqueia DCF."""

    def test_wacc_equals_g_blocks_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.10,  # WACC = g → HARD BLOCK
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        block = _validate_utility_dcf_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-02" in block
        assert "WACC" in block

        result = calculate_utility_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_wacc_less_than_g_blocks_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.08,
            terminal_growth=0.12,  # g > WACC → HARD BLOCK
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        block = _validate_utility_dcf_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-02" in block

        result = calculate_utility_valuation(inputs)
        assert result.blocked is True

    def test_wacc_greater_than_g_not_blocked(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,  # WACC > g → OK
        )
        block = _validate_utility_dcf_prerequisites(inputs)
        assert block is None

    def test_wacc_leq_g_also_blocks_rab_dcf(self):
        """U-UTIL-02: WACC <= g bloqueia RAB-DCF também."""
        inputs = UtilityValuationInputs(
            ticker="TAEE11",
            rab=8_000.0,
            wacc_spread=0.02,
            wacc=0.05,
            terminal_growth=0.05,  # WACC = g → bloqueia RAB-DCF
            net_debt=2_000.0,
            shares_outstanding=200.0,
        )
        block = _validate_utility_rab_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-02" in block


# ─────────────────────────────────────────────────────────────────────────────
#  2. FCF ausente bloqueia DCF (U-UTIL-01)
# ─────────────────────────────────────────────────────────────────────────────

class TestFCFAbsentBlock:
    """U-UTIL-01: free_cash_flow ausente bloqueia DCF/FCFF."""

    def test_fcf_none_blocks_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=None,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
        )
        block = _validate_utility_dcf_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-01" in block
        assert "free_cash_flow" in block.lower()

    def test_fcf_absent_falls_to_ev_ebitda(self, valid_ev_ebitda_inputs):
        """Sem FCF, mas com EBITDA > 0 → usa EV/EBITDA."""
        result = calculate_utility_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.method_used == UtilityValuationMethod.EV_EBITDA

    def test_fcf_absent_and_no_ebitda_blocks_all(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=None,
            ebitda=None,
            net_debt=5_000.0,
            shares_outstanding=500.0,
        )
        result = calculate_utility_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None


# ─────────────────────────────────────────────────────────────────────────────
#  3. RAB ausente bloqueia RAB-DCF (U-UTIL-06)
# ─────────────────────────────────────────────────────────────────────────────

class TestRABAbsentBlock:
    """U-UTIL-06: RAB ausente bloqueia RAB-DCF."""

    def test_rab_none_blocks_rab_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="TAEE11",
            rab=None,
            wacc_spread=0.02,
            wacc=0.10,
            terminal_growth=0.03,
            net_debt=2_000.0,
            shares_outstanding=200.0,
        )
        block = _validate_utility_rab_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-06" in block
        assert "rab" in block.lower()

    def test_rab_zero_blocks_rab_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="TAEE11",
            rab=0.0,
            wacc_spread=0.02,
            wacc=0.10,
            terminal_growth=0.03,
            net_debt=2_000.0,
            shares_outstanding=200.0,
        )
        block = _validate_utility_rab_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-06" in block

    def test_wacc_spread_absent_blocks_rab_dcf(self):
        inputs = UtilityValuationInputs(
            ticker="TAEE11",
            rab=8_000.0,
            wacc_spread=None,  # spread ausente
            wacc=0.10,
            terminal_growth=0.03,
        )
        block = _validate_utility_rab_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-06" in block
        assert "wacc_spread" in block.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  4. net_debt ausente bloqueia todos (U-UTIL-03)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetDebtAbsentBlock:
    """U-UTIL-03: net_debt ausente bloqueia enterprise value."""

    def test_net_debt_none_blocks_common(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            net_debt=None,
            shares_outstanding=500.0,
        )
        block = _validate_utility_shares_and_net_debt(inputs)
        assert block is not None
        assert "U-UTIL-03" in block
        assert "net_debt" in block.lower()

    def test_net_debt_none_blocks_full_valuation(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            ebitda=3_500.0,
            net_debt=None,  # ausente → bloqueia tudo
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
        )
        result = calculate_utility_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_net_debt_negative_is_valid(self):
        """net_debt negativo = caixa líquido → válido."""
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=-500.0,  # caixa líquido (válido)
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs)
        # Deve calcular (net_debt negativo é válido)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0


# ─────────────────────────────────────────────────────────────────────────────
#  5. shares_outstanding <= 0 bloqueia per-share (U-UTIL-04)
# ─────────────────────────────────────────────────────────────────────────────

class TestSharesBlock:
    """U-UTIL-04: shares_outstanding <= 0 bloqueia per-share."""

    @pytest.mark.parametrize("shares", [0.0, -1.0, -1_000.0])
    def test_shares_leq_zero_blocks(self, shares):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            net_debt=5_000.0,
            shares_outstanding=shares,
        )
        block = _validate_utility_shares_and_net_debt(inputs)
        assert block is not None
        assert "U-UTIL-04" in block

    def test_shares_none_blocks(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            net_debt=5_000.0,
            shares_outstanding=None,
        )
        block = _validate_utility_shares_and_net_debt(inputs)
        assert block is not None
        assert "U-UTIL-04" in block

    def test_shares_positive_not_blocked(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            net_debt=5_000.0,
            shares_outstanding=500.0,
        )
        block = _validate_utility_shares_and_net_debt(inputs)
        assert block is None


# ─────────────────────────────────────────────────────────────────────────────
#  6. EBITDA <= 0 bloqueia EV/EBITDA (U-UTIL-05)
# ─────────────────────────────────────────────────────────────────────────────

class TestEBITDALeqZeroBlock:
    """U-UTIL-05: EBITDA <= 0 bloqueia EV/EBITDA."""

    @pytest.mark.parametrize("ebitda", [0.0, -1.0, -5_000.0])
    def test_ebitda_leq_zero_blocks_ev_ebitda(self, ebitda):
        inputs = UtilityValuationInputs(
            ticker="SBSP3",
            ebitda=ebitda,
            net_debt=10_000.0,
            shares_outstanding=700.0,
        )
        block = _validate_utility_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-05" in block
        assert "EBITDA" in block.upper()

    def test_ebitda_none_blocks_ev_ebitda(self):
        inputs = UtilityValuationInputs(ticker="SBSP3", ebitda=None,
                                        net_debt=5_000.0, shares_outstanding=500.0)
        block = _validate_utility_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "U-UTIL-05" in block

    def test_ebitda_positive_not_blocked(self):
        inputs = UtilityValuationInputs(ticker="SBSP3", ebitda=4_000.0,
                                        net_debt=5_000.0, shares_outstanding=500.0)
        block = _validate_utility_ev_ebitda_prerequisites(inputs)
        assert block is None


# ─────────────────────────────────────────────────────────────────────────────
#  7. Cálculo DCF/FCFF correto
# ─────────────────────────────────────────────────────────────────────────────

class TestDCFCalculation:
    """Cálculo DCF/FCFF correto com inputs válidos."""

    def test_dcf_produces_fair_value(self, valid_dcf_inputs):
        result = calculate_utility_valuation(valid_dcf_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == UtilityValuationMethod.DCF_FCFF
        assert result.confidence > 0

    def test_dcf_arithmetic(self):
        """Verifica fórmula: EV = FCF/(WACC-g), equity = EV - net_debt, fv = equity/shares."""
        inputs = UtilityValuationInputs(
            ticker="TEST3",
            free_cash_flow=1_000.0,
            net_debt=5_000.0,
            shares_outstanding=100.0,
            wacc=0.10,
            terminal_growth=0.03,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        # EV = 1000 / (0.10 - 0.03) = 14285.71...
        # equity = 14285.71 - 5000 = 9285.71
        # fv = 9285.71 / 100 = 92.86
        result = calculate_utility_valuation(inputs)
        assert result.blocked is False
        expected_ev = round(1_000.0 / 0.07, 2)
        expected_eq = round(expected_ev - 5_000.0, 2)
        expected_fv = round(expected_eq / 100.0, 2)
        assert result.fair_value == pytest.approx(expected_fv, abs=0.01)
        assert result.enterprise_value == pytest.approx(expected_ev, abs=0.01)

    def test_dcf_upside_calculated(self, valid_dcf_inputs):
        result = calculate_utility_valuation(valid_dcf_inputs)
        if not result.blocked and result.fair_value and valid_dcf_inputs.market_price:
            assert result.upside_pct is not None
            expected_upside = round(
                (result.fair_value / valid_dcf_inputs.market_price - 1) * 100, 2
            )
            assert result.upside_pct == pytest.approx(expected_upside, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
#  8. Cálculo RAB-DCF correto
# ─────────────────────────────────────────────────────────────────────────────

class TestRABDCFCalculation:
    """Cálculo RAB-DCF correto com inputs válidos."""

    def test_rab_dcf_produces_fair_value(self, valid_rab_dcf_inputs):
        result = calculate_utility_valuation(valid_rab_dcf_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == UtilityValuationMethod.RAB_DCF
        assert result.rab_used == valid_rab_dcf_inputs.rab

    def test_rab_dcf_arithmetic(self):
        """Verifica fórmula RAB-DCF simplificada."""
        inputs = UtilityValuationInputs(
            ticker="TEST11",
            rab=10_000.0,
            wacc_spread=0.02,
            wacc=0.10,
            terminal_growth=0.03,
            net_debt=3_000.0,
            shares_outstanding=100.0,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        # EV = 10000 × (0.10 - 0.02) / (0.10 - 0.03) = 10000 × 0.08 / 0.07 = 11428.57
        # equity = 11428.57 - 3000 = 8428.57
        # fv = 8428.57 / 100 = 84.29
        result = calculate_utility_valuation(inputs)
        assert result.blocked is False
        expected_ev = round(10_000.0 * 0.08 / 0.07, 2)
        expected_eq = round(expected_ev - 3_000.0, 2)
        expected_fv = round(expected_eq / 100.0, 2)
        assert result.fair_value == pytest.approx(expected_fv, abs=0.01)

    def test_rab_dcf_preferred_over_dcf_when_both_available(self):
        """RAB-DCF tem prioridade sobre DCF quando ambos disponíveis."""
        inputs = UtilityValuationInputs(
            ticker="TAEE11",
            rab=8_000.0,
            wacc_spread=0.02,
            free_cash_flow=500.0,   # FCF disponível também
            wacc=0.10,
            terminal_growth=0.03,
            net_debt=2_000.0,
            shares_outstanding=200.0,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs)
        assert result.blocked is False
        assert result.method_used == UtilityValuationMethod.RAB_DCF  # RAB-DCF prioritário


# ─────────────────────────────────────────────────────────────────────────────
#  9. Cálculo EV/EBITDA correto
# ─────────────────────────────────────────────────────────────────────────────

class TestEVEBITDACalculation:
    """Cálculo EV/EBITDA correto com inputs válidos."""

    def test_ev_ebitda_produces_fair_value(self, valid_ev_ebitda_inputs):
        result = calculate_utility_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == UtilityValuationMethod.EV_EBITDA
        assert result.ev_ebitda_used == 9.0

    def test_ev_ebitda_arithmetic(self):
        inputs = UtilityValuationInputs(
            ticker="SBSP3",
            ebitda=4_000.0,
            net_debt=10_000.0,
            shares_outstanding=700.0,
            ev_ebitda_multiple=9.0,
            source_quality=UtilityInputQuality.EXCEL_PIPELINE,
        )
        # EV = 4000 × 9 = 36000
        # equity = 36000 - 10000 = 26000
        # fv = 26000 / 700 = 37.14
        result = calculate_utility_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value == pytest.approx(26_000.0 / 700.0, abs=0.01)

    def test_ev_ebitda_default_multiple_by_subsector(self):
        inputs = UtilityValuationInputs(
            ticker="SBSP3",
            ebitda=4_000.0,
            net_debt=10_000.0,
            shares_outstanding=700.0,
            subsector="sanitation",  # → 9.5x
        )
        assert inputs.effective_ev_ebitda_multiple == UTILITY_EV_EBITDA_BY_SUBSECTOR["sanitation"]


# ─────────────────────────────────────────────────────────────────────────────
#  10. Preserve logic
# ─────────────────────────────────────────────────────────────────────────────

class TestPreserveLogic:
    """Testa preserve logic para utility."""

    def test_existing_fair_value_preserved(self):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            existing_fair_value=42.50,  # valor existente
            market_price=32.00,
            source_quality=UtilityInputQuality.EXCEL_PIPELINE,
        )
        result = calculate_utility_valuation(inputs, force_recalc=False)
        assert result.blocked is False
        assert result.fair_value == pytest.approx(42.50, abs=0.01)
        assert result.method_used == UtilityValuationMethod.PRESERVE
        assert result.status == UtilityValuationStatus.PRESERVE_EXISTING

    def test_force_recalc_bypasses_preserve(self):
        """force_recalc=True → recalcula mesmo com existing_fair_value."""
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
            existing_fair_value=42.50,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs, force_recalc=True)
        # Deve recalcular, não preservar
        assert result.method_used != UtilityValuationMethod.PRESERVE

    def test_no_existing_fair_value_no_preserve(self):
        """Sem existing_fair_value → não preserva."""
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
            existing_fair_value=None,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs)
        assert result.method_used != UtilityValuationMethod.PRESERVE


# ─────────────────────────────────────────────────────────────────────────────
#  11. EGIE3/SBSP3/TAEE11 sem dados → NEEDS_FINANCIALS
# ─────────────────────────────────────────────────────────────────────────────

class TestUtilityTickersNoData:
    """Testa que tickers sem dados reais recebem NEEDS_FINANCIALS, não fair_value."""

    @pytest.mark.parametrize("ticker", ["EGIE3", "SBSP3", "TAEE11"])
    def test_no_data_no_fair_value(self, ticker):
        inputs = UtilityValuationInputs(
            ticker=ticker,
            # Sem dados financeiros reais
            free_cash_flow=None,
            ebitda=None,
            net_debt=None,
            shares_outstanding=None,
            source_quality=UtilityInputQuality.ABSENT,
        )
        result = calculate_utility_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_utility_tickers_set_complete(self):
        """UTILITY_TICKERS contém os 3 tickers confirmados."""
        assert "EGIE3" in UTILITY_TICKERS
        assert "SBSP3" in UTILITY_TICKERS
        assert "TAEE11" in UTILITY_TICKERS
        assert len(UTILITY_TICKERS) == 3

    def test_utility_preserved_fair_values_empty(self):
        """Nenhum valor preservado no grupo UTILITY (M016-S04)."""
        assert len(UTILITY_PRESERVED_FAIR_VALUES) == 0


# ─────────────────────────────────────────────────────────────────────────────
#  12. save_utility_valuation_result
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveUtilityValuationResult:
    """Testa gravação segura de resultados utility."""

    def test_write_false_does_not_write(self, tmp_db):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs)
        saved = save_utility_valuation_result(
            "EGIE3", result, db_path=tmp_db, write=False
        )
        assert saved is False
        # Tabela não deve existir (write=False)
        assert not Path(tmp_db).exists() or (
            lambda: (
                sqlite3.connect(tmp_db).execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='utility_valuation_results'"
                ).fetchone() is None
            )
        )()

    def test_write_true_with_valid_result(self, tmp_db):
        inputs = UtilityValuationInputs(
            ticker="EGIE3",
            free_cash_flow=2_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            wacc=0.10,
            terminal_growth=0.03,
            source_quality=UtilityInputQuality.CVM_LIVE,
        )
        result = calculate_utility_valuation(inputs)
        if not result.blocked:
            saved = save_utility_valuation_result(
                "EGIE3", result, db_path=tmp_db, write=True
            )
            assert saved is True
            conn = sqlite3.connect(tmp_db)
            c = conn.cursor()
            c.execute("SELECT ticker, fair_value FROM utility_valuation_results WHERE ticker='EGIE3'")
            row = c.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "EGIE3"
            assert row[1] == pytest.approx(result.fair_value, abs=0.01)

    def test_write_true_blocked_result_not_written(self, tmp_db):
        """Resultado bloqueado (fair_value=None) não deve ser gravado."""
        result = UtilityValuationResult.blocked_result(
            ticker="EGIE3",
            block_reason="Teste",
        )
        saved = save_utility_valuation_result(
            "EGIE3", result, db_path=tmp_db, write=True
        )
        assert saved is False


# ─────────────────────────────────────────────────────────────────────────────
#  13. Estrutura e exports
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleStructure:
    """Verifica estrutura e exports do módulo."""

    def test_blocked_result_factory(self):
        r = UtilityValuationResult.blocked_result(
            ticker="EGIE3",
            block_reason="Test block",
            status=UtilityValuationStatus.NEEDS_FINANCIALS,
        )
        assert r.blocked is True
        assert r.fair_value is None
        assert r.confidence == 0.0
        assert r.ticker == "EGIE3"
        assert r.block_reason == "Test block"

    def test_preserved_result_factory(self):
        r = UtilityValuationResult.preserved_result(
            ticker="EGIE3",
            fair_value=42.50,
            market_price=32.00,
        )
        assert r.blocked is False
        assert r.fair_value == pytest.approx(42.50, abs=0.01)
        assert r.method_used == UtilityValuationMethod.PRESERVE
        assert r.upside_pct is not None

    def test_inputs_ticker_normalized(self):
        inputs = UtilityValuationInputs(ticker="  egie3  ")
        assert inputs.ticker == "EGIE3"

    def test_result_blocked_confidence_zero(self):
        """Resultado bloqueado com confidence > 0 deve ser corrigido para 0."""
        r = UtilityValuationResult(
            ticker="EGIE3",
            blocked=True,
            confidence=0.9,  # inconsistente
        )
        assert r.confidence == 0.0  # corrigido por __post_init__

    def test_default_multiple_utility(self):
        assert DEFAULT_UTILITY_EV_EBITDA_MULTIPLE > 0
        inputs = UtilityValuationInputs(ticker="EGIE3")
        assert inputs.effective_ev_ebitda_multiple == DEFAULT_UTILITY_EV_EBITDA_MULTIPLE

    def test_subsector_multiple_lookup(self):
        inputs = UtilityValuationInputs(ticker="TAEE11", subsector="transmission")
        assert inputs.effective_ev_ebitda_multiple == UTILITY_EV_EBITDA_BY_SUBSECTOR["transmission"]
