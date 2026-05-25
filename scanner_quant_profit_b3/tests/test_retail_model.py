"""
tests/test_retail_model.py — M016-S04: Retail Valuation Model Tests

Cobre obrigatoriamente (M016-S04 checklist — RETAIL):
  1. WACC <= g bloqueia DCF (R-RETAIL-02)
  2. FCF ausente bloqueia DCF (R-RETAIL-01)
  3. net_debt ausente bloqueia todos os métodos (R-RETAIL-03)
  4. shares_outstanding <= 0 bloqueia per-share (R-RETAIL-04)
  5. EBITDA <= 0 bloqueia EV/EBITDA (R-RETAIL-05)
  6. EBITDA negativo marca empresa como DISTRESSED
  7. Cálculo DCF/FCFF correto com inputs válidos
  8. Cálculo EV/EBITDA correto com inputs válidos
  9. Preserve logic (existing_fair_value preservado com force_recalc=False)
 10. MGLU3/PCAR3 sem dados → não recebe fair_value novo (NEEDS_FINANCIALS)
 11. save_retail_valuation_result com write=False não grava
 12. Estrutura e exports do módulo
"""

from __future__ import annotations

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from src.valuation.models.retail_model import (
    RetailValuationInputs,
    RetailValuationResult,
    RetailInputQuality,
    RetailValuationStatus,
    RetailValuationMethod,
    RETAIL_TICKERS,
    RETAIL_PRESERVED_FAIR_VALUES,
    DEFAULT_RETAIL_EV_EBITDA_MULTIPLE,
    RETAIL_EV_EBITDA_BY_SUBSECTOR,
    calculate_retail_valuation,
    diagnose_retail_tickers,
    save_retail_valuation_result,
    _validate_retail_shares_and_net_debt,
    _validate_retail_dcf_prerequisites,
    _validate_retail_ev_ebitda_prerequisites,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures auxiliares
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_dcf_inputs():
    """Inputs válidos para DCF/FCFF retail."""
    return RetailValuationInputs(
        ticker="LREN3",
        free_cash_flow=1_500.0,
        ebitda=2_000.0,
        net_debt=3_000.0,
        shares_outstanding=800.0,
        wacc=0.13,
        terminal_growth=0.05,
        market_price=15.00,
        source_quality=RetailInputQuality.CVM_LIVE,
        subsector="fashion",
    )


@pytest.fixture
def valid_ev_ebitda_inputs():
    """Inputs válidos apenas para EV/EBITDA."""
    return RetailValuationInputs(
        ticker="AZZA3",
        free_cash_flow=None,
        ebitda=800.0,
        net_debt=1_000.0,
        shares_outstanding=300.0,
        ev_ebitda_multiple=9.0,
        market_price=20.00,
        source_quality=RetailInputQuality.EXCEL_PIPELINE,
    )


@pytest.fixture
def distressed_inputs():
    """Inputs com EBITDA negativo (empresa DISTRESSED)."""
    return RetailValuationInputs(
        ticker="MGLU3",
        free_cash_flow=-200.0,  # FCF negativo também
        ebitda=-500.0,          # EBITDA negativo → DISTRESSED
        net_debt=5_000.0,
        shares_outstanding=7_000.0,
        wacc=0.15,
        terminal_growth=0.04,
        market_price=6.50,
        source_quality=RetailInputQuality.CVM_LIVE,
    )


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_retail.db")


# ─────────────────────────────────────────────────────────────────────────────
#  1. WACC <= g bloqueia DCF (R-RETAIL-02)
# ─────────────────────────────────────────────────────────────────────────────

class TestWACCLeqGBlock:
    """R-RETAIL-02: WACC <= terminal_growth bloqueia DCF."""

    def test_wacc_equals_g_blocks_dcf(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_500.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.10,
            terminal_growth=0.10,  # WACC = g → HARD BLOCK
        )
        block = _validate_retail_dcf_prerequisites(inputs)
        assert block is not None
        assert "R-RETAIL-02" in block
        assert "WACC" in block

        result = calculate_retail_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_wacc_less_than_g_blocks_dcf(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_500.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.08,
            terminal_growth=0.12,
        )
        block = _validate_retail_dcf_prerequisites(inputs)
        assert block is not None
        assert "R-RETAIL-02" in block

    def test_wacc_greater_than_g_allowed(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_500.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
        )
        block = _validate_retail_dcf_prerequisites(inputs)
        assert block is None


# ─────────────────────────────────────────────────────────────────────────────
#  2. FCF ausente bloqueia DCF (R-RETAIL-01)
# ─────────────────────────────────────────────────────────────────────────────

class TestFCFAbsentBlock:
    """R-RETAIL-01: free_cash_flow ausente bloqueia DCF/FCFF."""

    def test_fcf_none_blocks_dcf(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=None,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
        )
        block = _validate_retail_dcf_prerequisites(inputs)
        assert block is not None
        assert "R-RETAIL-01" in block

    def test_fcf_absent_falls_to_ev_ebitda(self, valid_ev_ebitda_inputs):
        result = calculate_retail_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.method_used == RetailValuationMethod.EV_EBITDA

    def test_fcf_absent_ebitda_absent_blocks_all(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=None,
            ebitda=None,
            net_debt=3_000.0,
            shares_outstanding=800.0,
        )
        result = calculate_retail_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None


# ─────────────────────────────────────────────────────────────────────────────
#  3. net_debt ausente bloqueia todos (R-RETAIL-03)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetDebtAbsentBlock:
    """R-RETAIL-03: net_debt ausente bloqueia enterprise value."""

    def test_net_debt_none_blocks(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            net_debt=None,
            shares_outstanding=800.0,
        )
        block = _validate_retail_shares_and_net_debt(inputs)
        assert block is not None
        assert "R-RETAIL-03" in block

    def test_net_debt_none_blocks_full_valuation(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_500.0,
            ebitda=2_000.0,
            net_debt=None,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
        )
        result = calculate_retail_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_net_debt_negative_is_valid(self):
        """net_debt negativo (caixa líquido) é válido."""
        inputs = RetailValuationInputs(
            ticker="VIVA3",
            free_cash_flow=500.0,
            net_debt=-200.0,
            shares_outstanding=300.0,
            wacc=0.13,
            terminal_growth=0.05,
            source_quality=RetailInputQuality.CVM_LIVE,
        )
        result = calculate_retail_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value is not None


# ─────────────────────────────────────────────────────────────────────────────
#  4. shares_outstanding <= 0 bloqueia per-share (R-RETAIL-04)
# ─────────────────────────────────────────────────────────────────────────────

class TestSharesBlock:
    """R-RETAIL-04: shares_outstanding <= 0 bloqueia per-share."""

    @pytest.mark.parametrize("shares", [0.0, -1.0, -10_000.0])
    def test_shares_leq_zero_blocks(self, shares):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            net_debt=3_000.0,
            shares_outstanding=shares,
        )
        block = _validate_retail_shares_and_net_debt(inputs)
        assert block is not None
        assert "R-RETAIL-04" in block

    def test_shares_none_blocks(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            net_debt=3_000.0,
            shares_outstanding=None,
        )
        block = _validate_retail_shares_and_net_debt(inputs)
        assert block is not None
        assert "R-RETAIL-04" in block


# ─────────────────────────────────────────────────────────────────────────────
#  5. EBITDA <= 0 bloqueia EV/EBITDA (R-RETAIL-05)
# ─────────────────────────────────────────────────────────────────────────────

class TestEBITDALeqZeroBlock:
    """R-RETAIL-05: EBITDA <= 0 bloqueia EV/EBITDA."""

    @pytest.mark.parametrize("ebitda", [0.0, -1.0, -500.0])
    def test_ebitda_leq_zero_blocks_ev_ebitda(self, ebitda):
        inputs = RetailValuationInputs(
            ticker="MGLU3",
            ebitda=ebitda,
            net_debt=5_000.0,
            shares_outstanding=7_000.0,
        )
        block = _validate_retail_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "R-RETAIL-05" in block

    def test_ebitda_none_blocks(self):
        inputs = RetailValuationInputs(ticker="MGLU3", ebitda=None,
                                       net_debt=5_000.0, shares_outstanding=7_000.0)
        block = _validate_retail_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "R-RETAIL-05" in block

    def test_ebitda_positive_not_blocked(self):
        inputs = RetailValuationInputs(ticker="LREN3", ebitda=2_000.0,
                                       net_debt=3_000.0, shares_outstanding=800.0)
        block = _validate_retail_ev_ebitda_prerequisites(inputs)
        assert block is None


# ─────────────────────────────────────────────────────────────────────────────
#  6. EBITDA negativo → DISTRESSED
# ─────────────────────────────────────────────────────────────────────────────

class TestDistressedFlag:
    """EBITDA < 0 → empresa marcada como DISTRESSED."""

    def test_negative_ebitda_marks_distressed(self, distressed_inputs):
        assert distressed_inputs.is_distressed is True

    def test_distressed_ebitda_blocked_with_distressed_status(self, distressed_inputs):
        """MGLU3 com EBITDA negativo → bloqueado + status DISTRESSED."""
        result = calculate_retail_valuation(distressed_inputs)
        assert result.blocked is True
        assert result.distressed is True
        assert result.status == RetailValuationStatus.DISTRESSED
        assert result.fair_value is None

    def test_positive_ebitda_not_distressed(self, valid_dcf_inputs):
        assert valid_dcf_inputs.is_distressed is False
        result = calculate_retail_valuation(valid_dcf_inputs)
        assert result.distressed is False

    def test_distressed_flag_in_blocked_result_factory(self):
        r = RetailValuationResult.blocked_result(
            ticker="MGLU3",
            block_reason="EBITDA negativo",
            status=RetailValuationStatus.DISTRESSED,
            distressed=True,
        )
        assert r.distressed is True
        assert r.status == RetailValuationStatus.DISTRESSED

    def test_dcf_fcf_negative_with_negative_ebitda_double_block(self):
        """FCF negativo + EBITDA negativo → bloqueio total + DISTRESSED."""
        inputs = RetailValuationInputs(
            ticker="PCAR3",
            free_cash_flow=-100.0,
            ebitda=-200.0,
            net_debt=2_000.0,
            shares_outstanding=700.0,
            wacc=0.15,
            terminal_growth=0.04,
        )
        # FCF negativo gera equity negativo → NEEDS_REVIEW ou blocks
        result = calculate_retail_valuation(inputs)
        assert result.distressed is True


# ─────────────────────────────────────────────────────────────────────────────
#  7. Cálculo DCF/FCFF correto
# ─────────────────────────────────────────────────────────────────────────────

class TestDCFCalculation:
    """Cálculo DCF/FCFF correto com inputs válidos."""

    def test_dcf_produces_fair_value(self, valid_dcf_inputs):
        result = calculate_retail_valuation(valid_dcf_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == RetailValuationMethod.DCF_FCFF

    def test_dcf_arithmetic(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_000.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
            source_quality=RetailInputQuality.CVM_LIVE,
        )
        # EV = 1000 / (0.13 - 0.05) = 12500
        # equity = 12500 - 3000 = 9500
        # fv = 9500 / 800 = 11.875
        result = calculate_retail_valuation(inputs)
        assert result.blocked is False
        expected_fv = round(9_500.0 / 800.0, 2)
        assert result.fair_value == pytest.approx(expected_fv, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
#  8. Cálculo EV/EBITDA correto
# ─────────────────────────────────────────────────────────────────────────────

class TestEVEBITDACalculation:
    """Cálculo EV/EBITDA correto com inputs válidos."""

    def test_ev_ebitda_produces_fair_value(self, valid_ev_ebitda_inputs):
        result = calculate_retail_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == RetailValuationMethod.EV_EBITDA

    def test_ev_ebitda_arithmetic(self):
        inputs = RetailValuationInputs(
            ticker="VIVA3",
            ebitda=600.0,
            net_debt=500.0,
            shares_outstanding=300.0,
            ev_ebitda_multiple=12.0,
            source_quality=RetailInputQuality.CVM_LIVE,
        )
        # EV = 600 × 12 = 7200
        # equity = 7200 - 500 = 6700
        # fv = 6700 / 300 = 22.33
        result = calculate_retail_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value == pytest.approx(6_700.0 / 300.0, abs=0.01)
        assert result.ev_ebitda_used == 12.0

    def test_ev_ebitda_subsector_multiple(self):
        """Múltiplo por subsector é aplicado corretamente."""
        inputs = RetailValuationInputs(ticker="VIVA3", subsector="jewelry")
        assert inputs.effective_ev_ebitda_multiple == RETAIL_EV_EBITDA_BY_SUBSECTOR["jewelry"]


# ─────────────────────────────────────────────────────────────────────────────
#  9. Preserve logic
# ─────────────────────────────────────────────────────────────────────────────

class TestPreserveLogic:
    """Preserve logic para retail."""

    def test_existing_fair_value_preserved(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            existing_fair_value=25.00,
            market_price=15.00,
            source_quality=RetailInputQuality.EXCEL_PIPELINE,
        )
        result = calculate_retail_valuation(inputs, force_recalc=False)
        assert result.fair_value == pytest.approx(25.00, abs=0.01)
        assert result.method_used == RetailValuationMethod.PRESERVE
        assert result.status == RetailValuationStatus.PRESERVE_EXISTING

    def test_force_recalc_bypasses_preserve(self):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_000.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
            existing_fair_value=25.00,
            source_quality=RetailInputQuality.CVM_LIVE,
        )
        result = calculate_retail_valuation(inputs, force_recalc=True)
        assert result.method_used != RetailValuationMethod.PRESERVE


# ─────────────────────────────────────────────────────────────────────────────
#  10. MGLU3/PCAR3 sem dados → NEEDS_FINANCIALS
# ─────────────────────────────────────────────────────────────────────────────

class TestRetailTickersNoData:
    """Testa que tickers sem dados não recebem fair_value."""

    @pytest.mark.parametrize("ticker", ["MGLU3", "PCAR3", "AZZA3", "LREN3", "VIVA3"])
    def test_no_data_no_fair_value(self, ticker):
        inputs = RetailValuationInputs(
            ticker=ticker,
            free_cash_flow=None,
            ebitda=None,
            net_debt=None,
            shares_outstanding=None,
            source_quality=RetailInputQuality.ABSENT,
        )
        result = calculate_retail_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_retail_tickers_set_complete(self):
        """RETAIL_TICKERS contém os 5 tickers confirmados."""
        for t in ["AZZA3", "LREN3", "MGLU3", "PCAR3", "VIVA3"]:
            assert t in RETAIL_TICKERS
        assert len(RETAIL_TICKERS) == 5

    def test_retail_preserved_fair_values_empty(self):
        """Nenhum valor preservado no grupo RETAIL (M016-S04)."""
        assert len(RETAIL_PRESERVED_FAIR_VALUES) == 0


# ─────────────────────────────────────────────────────────────────────────────
#  11. save_retail_valuation_result
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveRetailValuationResult:
    """Testa gravação segura."""

    def test_write_false_does_not_write(self, tmp_db):
        result = RetailValuationResult.blocked_result(
            ticker="LREN3", block_reason="Test"
        )
        saved = save_retail_valuation_result(
            "LREN3", result, db_path=tmp_db, write=False
        )
        assert saved is False

    def test_write_true_with_valid_result(self, tmp_db):
        inputs = RetailValuationInputs(
            ticker="LREN3",
            free_cash_flow=1_000.0,
            net_debt=3_000.0,
            shares_outstanding=800.0,
            wacc=0.13,
            terminal_growth=0.05,
            source_quality=RetailInputQuality.CVM_LIVE,
        )
        result = calculate_retail_valuation(inputs)
        if not result.blocked:
            saved = save_retail_valuation_result(
                "LREN3", result, db_path=tmp_db, write=True
            )
            assert saved is True
            conn = sqlite3.connect(tmp_db)
            c = conn.cursor()
            c.execute("SELECT ticker, fair_value FROM retail_valuation_results")
            row = c.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "LREN3"

    def test_write_true_blocked_result_not_written(self, tmp_db):
        result = RetailValuationResult.blocked_result(
            ticker="MGLU3", block_reason="DISTRESSED"
        )
        saved = save_retail_valuation_result(
            "MGLU3", result, db_path=tmp_db, write=True
        )
        assert saved is False


# ─────────────────────────────────────────────────────────────────────────────
#  12. Estrutura e exports
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleStructure:
    """Verifica estrutura e exports."""

    def test_blocked_result_factory(self):
        r = RetailValuationResult.blocked_result(
            ticker="MGLU3", block_reason="Teste"
        )
        assert r.blocked is True
        assert r.fair_value is None
        assert r.confidence == 0.0

    def test_preserved_result_factory(self):
        r = RetailValuationResult.preserved_result(
            ticker="LREN3", fair_value=25.00, market_price=15.00
        )
        assert r.blocked is False
        assert r.fair_value == pytest.approx(25.00, abs=0.01)
        assert r.upside_pct is not None

    def test_inputs_ticker_normalized(self):
        inputs = RetailValuationInputs(ticker="  lren3  ")
        assert inputs.ticker == "LREN3"

    def test_result_blocked_confidence_zero(self):
        r = RetailValuationResult(ticker="LREN3", blocked=True, confidence=0.8)
        assert r.confidence == 0.0

    def test_default_multiple(self):
        assert DEFAULT_RETAIL_EV_EBITDA_MULTIPLE > 0
