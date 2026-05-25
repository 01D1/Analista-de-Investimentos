"""
tests/test_industry_model.py — M016-S04: Industry / TECH-Fallback Valuation Model Tests

Cobre obrigatoriamente (M016-S04 checklist — INDUSTRY):
  1. WACC <= g bloqueia DCF (I-IND-02)
  2. FCF ausente bloqueia DCF (I-IND-01)
  3. net_debt ausente bloqueia todos os métodos (I-IND-03)
  4. shares_outstanding <= 0 bloqueia per-share (I-IND-04)
  5. EBITDA <= 0 bloqueia EV/EBITDA (I-IND-05)
  6. Preserve logic para WEGE3=40.16
  7. Cálculo DCF/FCFF correto com inputs válidos
  8. Cálculo EV/EBITDA correto com inputs válidos
  9. VIVT3 → TECH_FALLBACK status sem dados estruturados
 10. Tickers sem dados → NEEDS_FINANCIALS (não recebem fair_value)
 11. save_industry_valuation_result: WEGE3 não sobrescrito sem force_recalc
 12. save_industry_valuation_result com write=False não grava
 13. Estrutura e exports do módulo
"""

from __future__ import annotations

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from src.valuation.models.industry_model import (
    IndustryValuationInputs,
    IndustryValuationResult,
    IndustryInputQuality,
    IndustryValuationStatus,
    IndustryValuationMethod,
    INDUSTRY_TICKERS,
    TECH_FALLBACK_TICKERS,
    ALL_INDUSTRY_TICKERS,
    INDUSTRY_PRESERVED_FAIR_VALUES,
    DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE,
    INDUSTRY_EV_EBITDA_BY_SUBSECTOR,
    calculate_industry_valuation,
    diagnose_industry_tickers,
    save_industry_valuation_result,
    _validate_industry_shares_and_net_debt,
    _validate_industry_dcf_prerequisites,
    _validate_industry_ev_ebitda_prerequisites,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures auxiliares
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_dcf_inputs():
    """Inputs válidos para DCF/FCFF — indústria genérica."""
    return IndustryValuationInputs(
        ticker="RENT3",
        free_cash_flow=3_000.0,
        ebitda=5_000.0,
        net_debt=10_000.0,
        shares_outstanding=1_000.0,
        wacc=0.11,
        terminal_growth=0.04,
        market_price=43.00,
        source_quality=IndustryInputQuality.CVM_LIVE,
        subsector="rental",
    )


@pytest.fixture
def valid_ev_ebitda_inputs():
    """Inputs válidos apenas para EV/EBITDA."""
    return IndustryValuationInputs(
        ticker="SUZB3",
        free_cash_flow=None,
        ebitda=10_000.0,
        net_debt=30_000.0,
        shares_outstanding=1_300.0,
        ev_ebitda_multiple=7.0,
        market_price=41.00,
        source_quality=IndustryInputQuality.EXCEL_PIPELINE,
        subsector="pulp",
    )


@pytest.fixture
def wege3_preserved_inputs():
    """Inputs de WEGE3 com fair_value existente=40.16."""
    return IndustryValuationInputs(
        ticker="WEGE3",
        market_price=42.73,
        source_quality=IndustryInputQuality.EXCEL_PIPELINE,
        existing_fair_value=40.16,
        existing_valuation_date="2026-05-22",
    )


@pytest.fixture
def vivt3_no_data_inputs():
    """VIVT3 sem dados estruturados."""
    return IndustryValuationInputs(
        ticker="VIVT3",
        free_cash_flow=None,
        ebitda=None,
        net_debt=None,
        shares_outstanding=None,
        source_quality=IndustryInputQuality.ABSENT,
        subsector="telecom",
    )


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_industry.db")


# ─────────────────────────────────────────────────────────────────────────────
#  1. WACC <= g bloqueia DCF (I-IND-02)
# ─────────────────────────────────────────────────────────────────────────────

class TestWACCLeqGBlock:
    """I-IND-02: WACC <= terminal_growth bloqueia DCF."""

    def test_wacc_equals_g_blocks_dcf(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.10,
            terminal_growth=0.10,  # WACC = g → HARD BLOCK
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is not None
        assert "I-IND-02" in block
        assert "WACC" in block

        result = calculate_industry_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_wacc_less_than_g_blocks_dcf(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.07,
            terminal_growth=0.09,  # g > WACC
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is not None
        assert "I-IND-02" in block

    def test_wacc_greater_than_g_allowed(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.11,
            terminal_growth=0.04,
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is None

    def test_wacc_none_blocks_dcf(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=None,
            terminal_growth=0.04,
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is not None
        assert "wacc" in block.lower()

    def test_terminal_growth_none_blocks_dcf(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.11,
            terminal_growth=None,
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is not None
        assert "terminal_growth" in block.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  2. FCF ausente bloqueia DCF (I-IND-01)
# ─────────────────────────────────────────────────────────────────────────────

class TestFCFAbsentBlock:
    """I-IND-01: free_cash_flow ausente bloqueia DCF/FCFF."""

    def test_fcf_none_blocks_dcf(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=None,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.11,
            terminal_growth=0.04,
        )
        block = _validate_industry_dcf_prerequisites(inputs)
        assert block is not None
        assert "I-IND-01" in block

    def test_fcf_absent_falls_to_ev_ebitda(self, valid_ev_ebitda_inputs):
        result = calculate_industry_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.method_used == IndustryValuationMethod.EV_EBITDA

    def test_fcf_absent_ebitda_absent_blocks_all(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=None,
            ebitda=None,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
        )
        result = calculate_industry_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None


# ─────────────────────────────────────────────────────────────────────────────
#  3. net_debt ausente bloqueia todos (I-IND-03)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetDebtAbsentBlock:
    """I-IND-03: net_debt ausente bloqueia enterprise value."""

    def test_net_debt_none_blocks(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            net_debt=None,
            shares_outstanding=1_000.0,
        )
        block = _validate_industry_shares_and_net_debt(inputs)
        assert block is not None
        assert "I-IND-03" in block

    def test_net_debt_none_blocks_full_valuation(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=3_000.0,
            ebitda=5_000.0,
            net_debt=None,
            shares_outstanding=1_000.0,
            wacc=0.11,
            terminal_growth=0.04,
        )
        result = calculate_industry_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_net_debt_negative_is_valid(self):
        """net_debt negativo (caixa líquido) é válido."""
        inputs = IndustryValuationInputs(
            ticker="WEGE3",
            free_cash_flow=5_000.0,
            net_debt=-2_000.0,  # caixa líquido
            shares_outstanding=4_000.0,
            wacc=0.11,
            terminal_growth=0.04,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        result = calculate_industry_valuation(inputs, force_recalc=True)
        assert result.blocked is False
        assert result.fair_value is not None


# ─────────────────────────────────────────────────────────────────────────────
#  4. shares_outstanding <= 0 bloqueia per-share (I-IND-04)
# ─────────────────────────────────────────────────────────────────────────────

class TestSharesBlock:
    """I-IND-04: shares_outstanding <= 0 bloqueia per-share."""

    @pytest.mark.parametrize("shares", [0.0, -1.0, -10_000.0])
    def test_shares_leq_zero_blocks(self, shares):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            net_debt=10_000.0,
            shares_outstanding=shares,
        )
        block = _validate_industry_shares_and_net_debt(inputs)
        assert block is not None
        assert "I-IND-04" in block

    def test_shares_none_blocks(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            net_debt=10_000.0,
            shares_outstanding=None,
        )
        block = _validate_industry_shares_and_net_debt(inputs)
        assert block is not None
        assert "I-IND-04" in block


# ─────────────────────────────────────────────────────────────────────────────
#  5. EBITDA <= 0 bloqueia EV/EBITDA (I-IND-05)
# ─────────────────────────────────────────────────────────────────────────────

class TestEBITDALeqZeroBlock:
    """I-IND-05: EBITDA <= 0 bloqueia EV/EBITDA."""

    @pytest.mark.parametrize("ebitda", [0.0, -1.0, -1_000.0])
    def test_ebitda_leq_zero_blocks_ev_ebitda(self, ebitda):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            ebitda=ebitda,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
        )
        block = _validate_industry_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "I-IND-05" in block

    def test_ebitda_none_blocks(self):
        inputs = IndustryValuationInputs(ticker="RENT3", ebitda=None,
                                         net_debt=10_000.0, shares_outstanding=1_000.0)
        block = _validate_industry_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "I-IND-05" in block

    def test_ebitda_positive_not_blocked(self):
        inputs = IndustryValuationInputs(ticker="RENT3", ebitda=5_000.0,
                                         net_debt=10_000.0, shares_outstanding=1_000.0)
        block = _validate_industry_ev_ebitda_prerequisites(inputs)
        assert block is None

    def test_negative_ebitda_blocked_even_with_fcf(self):
        """FCF válido + EBITDA negativo → DCF tenta, EV/EBITDA bloqueado."""
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=1_000.0,
            ebitda=-500.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.11,
            terminal_growth=0.04,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        ev_block = _validate_industry_ev_ebitda_prerequisites(inputs)
        assert ev_block is not None
        assert "I-IND-05" in ev_block

        result = calculate_industry_valuation(inputs)
        # DCF deve ser tentado
        if not result.blocked:
            assert result.method_used == IndustryValuationMethod.DCF_FCFF


# ─────────────────────────────────────────────────────────────────────────────
#  6. Preserve logic para WEGE3=40.16
# ─────────────────────────────────────────────────────────────────────────────

class TestWEGE3PreserveLogic:
    """WEGE3=40.16 deve ser preservado com force_recalc=False."""

    def test_wege3_preserved_by_default(self, wege3_preserved_inputs):
        """WEGE3 com existing_fair_value=40.16 → preservado sem force_recalc."""
        result = calculate_industry_valuation(wege3_preserved_inputs, force_recalc=False)
        assert result.blocked is False
        assert result.fair_value == pytest.approx(40.16, abs=0.01)
        assert result.method_used == IndustryValuationMethod.PRESERVE
        assert result.status == IndustryValuationStatus.PRESERVE_EXISTING

    def test_wege3_preserved_fair_value_in_dict(self):
        """INDUSTRY_PRESERVED_FAIR_VALUES contém WEGE3=40.16."""
        assert "WEGE3" in INDUSTRY_PRESERVED_FAIR_VALUES
        assert INDUSTRY_PRESERVED_FAIR_VALUES["WEGE3"] == pytest.approx(40.16, abs=0.01)

    def test_wege3_save_blocked_without_force_recalc(self, tmp_db):
        """Save de WEGE3 sem force_recalc deve retornar False."""
        result = IndustryValuationResult(
            ticker="WEGE3",
            fair_value=42.00,
            blocked=False,
            confidence=0.9,
        )
        saved = save_industry_valuation_result(
            "WEGE3", result, db_path=tmp_db, write=True, force_recalc=False
        )
        assert saved is False

    def test_wege3_save_allowed_with_force_recalc(self, tmp_db):
        """Save de WEGE3 com force_recalc=True deve gravar."""
        result = IndustryValuationResult(
            ticker="WEGE3",
            fair_value=42.00,
            blocked=False,
            confidence=0.9,
            status=IndustryValuationStatus.VALUATION_READY,
            method_used=IndustryValuationMethod.DCF_FCFF,
        )
        saved = save_industry_valuation_result(
            "WEGE3", result, db_path=tmp_db, write=True, force_recalc=True
        )
        assert saved is True
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute("SELECT ticker, fair_value, force_recalc FROM industry_valuation_results "
                  "WHERE ticker='WEGE3'")
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "WEGE3"
        assert row[2] == 1  # force_recalc=True registrado

    def test_wege3_force_recalc_bypasses_preserve(self):
        """force_recalc=True → recalcula WEGE3."""
        inputs = IndustryValuationInputs(
            ticker="WEGE3",
            free_cash_flow=5_000.0,
            net_debt=-2_000.0,
            shares_outstanding=4_000.0,
            wacc=0.11,
            terminal_growth=0.04,
            existing_fair_value=40.16,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        result = calculate_industry_valuation(inputs, force_recalc=True)
        assert result.method_used != IndustryValuationMethod.PRESERVE


# ─────────────────────────────────────────────────────────────────────────────
#  7. Cálculo DCF/FCFF correto
# ─────────────────────────────────────────────────────────────────────────────

class TestDCFCalculation:
    """Cálculo DCF/FCFF correto com inputs válidos."""

    def test_dcf_produces_fair_value(self, valid_dcf_inputs):
        result = calculate_industry_valuation(valid_dcf_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == IndustryValuationMethod.DCF_FCFF

    def test_dcf_arithmetic(self):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=1_000.0,
            net_debt=5_000.0,
            shares_outstanding=200.0,
            wacc=0.11,
            terminal_growth=0.04,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        # EV = 1000 / (0.11 - 0.04) = 14285.71
        # equity = 14285.71 - 5000 = 9285.71
        # fv = 9285.71 / 200 = 46.43
        result = calculate_industry_valuation(inputs)
        assert result.blocked is False
        expected_fv = round(9_285.71 / 200.0, 2)
        assert result.fair_value == pytest.approx(expected_fv, abs=0.10)


# ─────────────────────────────────────────────────────────────────────────────
#  8. Cálculo EV/EBITDA correto
# ─────────────────────────────────────────────────────────────────────────────

class TestEVEBITDACalculation:
    """Cálculo EV/EBITDA correto com inputs válidos."""

    def test_ev_ebitda_produces_fair_value(self, valid_ev_ebitda_inputs):
        result = calculate_industry_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == IndustryValuationMethod.EV_EBITDA

    def test_ev_ebitda_arithmetic(self):
        inputs = IndustryValuationInputs(
            ticker="KLBN11",
            ebitda=4_000.0,
            net_debt=10_000.0,
            shares_outstanding=500.0,
            ev_ebitda_multiple=7.0,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        # EV = 4000 × 7 = 28000
        # equity = 28000 - 10000 = 18000
        # fv = 18000 / 500 = 36.0
        result = calculate_industry_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value == pytest.approx(36.0, abs=0.01)
        assert result.ev_ebitda_used == 7.0

    def test_subsector_multiple(self):
        """Múltiplo por subsector aplicado corretamente."""
        inputs = IndustryValuationInputs(ticker="FLRY3", subsector="healthcare")
        assert inputs.effective_ev_ebitda_multiple == INDUSTRY_EV_EBITDA_BY_SUBSECTOR["healthcare"]

    def test_wege3_industrial_multiple(self):
        inputs = IndustryValuationInputs(ticker="WEGE3", subsector="industrial")
        assert inputs.effective_ev_ebitda_multiple == INDUSTRY_EV_EBITDA_BY_SUBSECTOR["industrial"]


# ─────────────────────────────────────────────────────────────────────────────
#  9. VIVT3 → TECH_FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

class TestVIVT3TechFallback:
    """VIVT3 é TECH/FALLBACK — bloqueado sem dados estruturados."""

    def test_vivt3_in_tech_fallback_tickers(self):
        assert "VIVT3" in TECH_FALLBACK_TICKERS

    def test_vivt3_in_all_industry_tickers(self):
        assert "VIVT3" in ALL_INDUSTRY_TICKERS

    def test_vivt3_is_tech_fallback_property(self, vivt3_no_data_inputs):
        assert vivt3_no_data_inputs.is_tech_fallback is True

    def test_vivt3_without_data_status_tech_fallback(self, vivt3_no_data_inputs):
        """VIVT3 sem dados → status TECH_FALLBACK, não NEEDS_FINANCIALS."""
        result = calculate_industry_valuation(vivt3_no_data_inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.status == IndustryValuationStatus.TECH_FALLBACK
        assert result.is_tech_fallback is True

    def test_vivt3_with_data_calculates_normally(self):
        """VIVT3 com dados reais → calcula via DCF ou EV/EBITDA."""
        inputs = IndustryValuationInputs(
            ticker="VIVT3",
            free_cash_flow=5_000.0,
            net_debt=8_000.0,
            shares_outstanding=1_400.0,
            wacc=0.11,
            terminal_growth=0.03,
            market_price=34.00,
            source_quality=IndustryInputQuality.CVM_LIVE,
            subsector="telecom",
        )
        result = calculate_industry_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.is_tech_fallback is True  # flag mantida mesmo calculando


# ─────────────────────────────────────────────────────────────────────────────
#  10. Tickers sem dados → NEEDS_FINANCIALS
# ─────────────────────────────────────────────────────────────────────────────

class TestIndustryTickersNoData:
    """Testa que tickers sem dados não recebem fair_value."""

    @pytest.mark.parametrize("ticker", [
        "FLRY3", "HYPE3", "KLBN11", "RADL3", "RAIL3",
        "RENT3", "SUZB3", "VAMO3",
    ])
    def test_no_data_no_fair_value(self, ticker):
        inputs = IndustryValuationInputs(
            ticker=ticker,
            free_cash_flow=None,
            ebitda=None,
            net_debt=None,
            shares_outstanding=None,
            source_quality=IndustryInputQuality.ABSENT,
        )
        result = calculate_industry_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0
        assert result.status == IndustryValuationStatus.NEEDS_FINANCIALS

    def test_industry_tickers_set_complete(self):
        for t in ["FLRY3", "HYPE3", "KLBN11", "RADL3", "RAIL3",
                  "RENT3", "SUZB3", "VAMO3", "WEGE3"]:
            assert t in INDUSTRY_TICKERS

    def test_all_industry_tickers_includes_tech_fallback(self):
        assert "VIVT3" in ALL_INDUSTRY_TICKERS
        assert ALL_INDUSTRY_TICKERS == INDUSTRY_TICKERS | TECH_FALLBACK_TICKERS


# ─────────────────────────────────────────────────────────────────────────────
#  11 & 12. save_industry_valuation_result
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveIndustryValuationResult:
    """Testa gravação segura."""

    def test_write_false_does_not_write(self, tmp_db):
        result = IndustryValuationResult.blocked_result(
            ticker="RENT3", block_reason="Test"
        )
        saved = save_industry_valuation_result(
            "RENT3", result, db_path=tmp_db, write=False
        )
        assert saved is False

    def test_write_true_with_valid_result(self, tmp_db):
        inputs = IndustryValuationInputs(
            ticker="RENT3",
            free_cash_flow=1_000.0,
            net_debt=5_000.0,
            shares_outstanding=200.0,
            wacc=0.11,
            terminal_growth=0.04,
            source_quality=IndustryInputQuality.CVM_LIVE,
        )
        result = calculate_industry_valuation(inputs)
        if not result.blocked:
            saved = save_industry_valuation_result(
                "RENT3", result, db_path=tmp_db, write=True
            )
            assert saved is True

    def test_write_true_blocked_result_not_written(self, tmp_db):
        result = IndustryValuationResult.blocked_result(
            ticker="SUZB3", block_reason="Sem dados"
        )
        saved = save_industry_valuation_result(
            "SUZB3", result, db_path=tmp_db, write=True
        )
        assert saved is False


# ─────────────────────────────────────────────────────────────────────────────
#  13. Estrutura e exports
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleStructure:
    """Verifica estrutura e exports."""

    def test_blocked_result_factory(self):
        r = IndustryValuationResult.blocked_result(
            ticker="RENT3", block_reason="Teste"
        )
        assert r.blocked is True
        assert r.fair_value is None
        assert r.confidence == 0.0

    def test_preserved_result_factory(self):
        r = IndustryValuationResult.preserved_result(
            ticker="WEGE3", fair_value=40.16, market_price=42.73
        )
        assert r.blocked is False
        assert r.fair_value == pytest.approx(40.16, abs=0.01)
        assert r.method_used == IndustryValuationMethod.PRESERVE
        assert r.upside_pct is not None  # upside calculado

    def test_inputs_ticker_normalized(self):
        inputs = IndustryValuationInputs(ticker="  wege3  ")
        assert inputs.ticker == "WEGE3"

    def test_result_blocked_confidence_zero(self):
        r = IndustryValuationResult(ticker="RENT3", blocked=True, confidence=0.8)
        assert r.confidence == 0.0

    def test_wege3_upside_negative(self):
        """WEGE3=40.16 com market_price=42.73 → upside negativo (overvalued)."""
        r = IndustryValuationResult.preserved_result(
            ticker="WEGE3", fair_value=40.16, market_price=42.73
        )
        assert r.upside_pct is not None
        assert r.upside_pct < 0  # fair_value < market_price → downside

    def test_default_multiple(self):
        assert DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE > 0
        inputs = IndustryValuationInputs(ticker="RENT3")
        assert inputs.effective_ev_ebitda_multiple == DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE
