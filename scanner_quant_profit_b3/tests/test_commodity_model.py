"""
tests/test_commodity_model.py — M016-S03: Commodity / Oil & Gas Valuation Model Tests

Cobre obrigatoriamente (M016-S03 checklist):
  1. WACC <= g bloqueia DCF (D-COMM-02)
  2. EBITDA <= 0 bloqueia EV/EBITDA (D-COMM-05)
  3. FCF ausente bloqueia DCF (D-COMM-01)
  4. net_debt ausente bloqueia EV (D-COMM-03)
  5. PETR4 preserva fair_value=81.12 existente (force_recalc=False)
  6. VALE3 permanece bloqueada por NEEDS_DATA (ri_docs=0)
  7. PRIO3/RECV3 só calculam com inputs reais (sem dados estruturados → bloqueado)
  8. Router normaliza PETR4/PRIO3/RECV3 para COMMODITY
  9. Cálculo DCF/FCFF correto com inputs válidos
 10. Cálculo EV/EBITDA correto com inputs válidos
 11. save_commodity_valuation_result não sobrescreve PETR4 sem force_recalc
 12. Estrutura e exports do módulo
"""

from __future__ import annotations

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# ── Imports dos módulos sob teste ──────────────────────────────────────────────

from src.valuation.models.commodity_model import (
    CommodityValuationInputs,
    CommodityValuationResult,
    CommodityInputQuality,
    CommodityValuationStatus,
    CommodityValuationMethod,
    COMMODITY_TICKERS,
    OIL_GAS_TICKERS,
    MINING_TICKERS,
    COMMODITY_PRESERVED_FAIR_VALUES,
    DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE,
    DEFAULT_MINING_EV_EBITDA_MULTIPLE,
    calculate_commodity_valuation,
    diagnose_commodity_tickers,
    save_commodity_valuation_result,
    _validate_shares_and_net_debt,
    _validate_dcf_prerequisites,
    _validate_ev_ebitda_prerequisites,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures auxiliares
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_dcf_inputs():
    """Inputs válidos para DCF/FCFF — empresa de petróleo genérica."""
    return CommodityValuationInputs(
        ticker="TEST4",
        free_cash_flow=10_000.0,      # R$ 10 bilhões FCF
        ebitda=18_000.0,              # R$ 18 bilhões EBITDA
        net_debt=20_000.0,            # R$ 20 bilhões dívida líquida
        shares_outstanding=13_000.0,  # 13 bilhões de ações
        wacc=0.12,                    # 12% WACC
        terminal_growth=0.04,         # 4% crescimento terminal
        market_price=35.00,
        source_quality=CommodityInputQuality.CVM_LIVE,
        subsector="oil_gas",
    )


@pytest.fixture
def valid_ev_ebitda_inputs():
    """Inputs válidos apenas para EV/EBITDA (sem FCF/WACC)."""
    return CommodityValuationInputs(
        ticker="TEST4",
        free_cash_flow=None,          # DCF bloqueado
        ebitda=5_000.0,               # R$ 5 bilhões EBITDA positivo
        net_debt=8_000.0,             # R$ 8 bilhões dívida líquida
        shares_outstanding=1_000.0,   # 1 bilhão de ações
        wacc=None,                    # DCF não disponível
        terminal_growth=None,
        ev_ebitda_multiple=5.0,       # múltiplo setorial
        market_price=15.00,
        source_quality=CommodityInputQuality.EXCEL_PIPELINE,
        subsector="oil_gas",
    )


@pytest.fixture
def tmp_db(tmp_path):
    """Banco de dados temporário para testes de save."""
    return str(tmp_path / "test_commodity.db")


# ─────────────────────────────────────────────────────────────────────────────
#  1. WACC <= g bloqueia DCF (D-COMM-02)
# ─────────────────────────────────────────────────────────────────────────────

class TestWACCLeqGBlock:
    """D-COMM-02: WACC <= terminal_growth bloqueia DCF."""

    def test_wacc_equals_g_blocks_dcf(self):
        """WACC = g → DCF bloqueado (divisor = 0)."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.10,
            terminal_growth=0.10,   # WACC = g → HARD BLOCK
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is not None
        assert "D-COMM-02" in block
        assert "WACC" in block

        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_wacc_less_than_g_blocks_dcf(self):
        """WACC < g → DCF bloqueado (divisor negativo → resultado indefinido)."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.08,
            terminal_growth=0.12,   # g > WACC → HARD BLOCK
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is not None
        assert "D-COMM-02" in block

        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_wacc_greater_than_g_not_blocked(self):
        """WACC > g → pré-requisito DCF OK."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,   # WACC > g → OK
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is None

    def test_wacc_none_blocks_dcf(self):
        """WACC ausente → DCF bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=None,
            terminal_growth=0.04,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is not None
        assert "wacc" in block.lower()

    def test_terminal_growth_none_blocks_dcf(self):
        """terminal_growth ausente → DCF bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=None,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is not None
        assert "terminal_growth" in block.lower()


# ─────────────────────────────────────────────────────────────────────────────
#  2. EBITDA <= 0 bloqueia EV/EBITDA (D-COMM-05)
# ─────────────────────────────────────────────────────────────────────────────

class TestEBITDALeqZeroBlock:
    """D-COMM-05: EBITDA <= 0 bloqueia múltiplo EV/EBITDA."""

    @pytest.mark.parametrize("ebitda", [0.0, -1.0, -100_000.0])
    def test_ebitda_leq_zero_blocks_ev_ebitda(self, ebitda):
        """EBITDA <= 0 → EV/EBITDA bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=ebitda,
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        block = _validate_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "D-COMM-05" in block
        assert "EBITDA" in block.upper()

    def test_ebitda_none_blocks_ev_ebitda(self):
        """EBITDA ausente → EV/EBITDA bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=None,
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
        )
        block = _validate_ev_ebitda_prerequisites(inputs)
        assert block is not None
        assert "D-COMM-05" in block

    def test_ebitda_positive_not_blocked(self):
        """EBITDA > 0 → EV/EBITDA não bloqueado por este critério."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=1_000.0,
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
        )
        block = _validate_ev_ebitda_prerequisites(inputs)
        assert block is None

    def test_negative_ebitda_blocked_even_with_fcf(self):
        """Com FCF válido mas EBITDA negativo → EV/EBITDA bloqueado, DCF tentado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=2_000.0,
            ebitda=-500.0,           # EBITDA negativo → bloqueia EV/EBITDA
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        # DCF deve funcionar
        result = calculate_commodity_valuation(inputs)
        # DCF disponível com esses inputs
        if not result.blocked:
            assert result.method_used == CommodityValuationMethod.DCF_FCFF
        # EV/EBITDA deve estar bloqueado
        ev_block = _validate_ev_ebitda_prerequisites(inputs)
        assert ev_block is not None
        assert "D-COMM-05" in ev_block


# ─────────────────────────────────────────────────────────────────────────────
#  3. FCF ausente bloqueia DCF (D-COMM-01)
# ─────────────────────────────────────────────────────────────────────────────

class TestFCFAbsentBlock:
    """D-COMM-01: free_cash_flow ausente bloqueia DCF/FCFF."""

    def test_fcf_none_blocks_dcf(self):
        """FCF ausente → DCF bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=None,
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
        )
        block = _validate_dcf_prerequisites(inputs)
        assert block is not None
        assert "D-COMM-01" in block
        assert "free_cash_flow" in block.lower()

    def test_fcf_absent_falls_to_ev_ebitda(self, valid_ev_ebitda_inputs):
        """Sem FCF, mas com EBITDA > 0 → usa EV/EBITDA."""
        result = calculate_commodity_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.method_used == CommodityValuationMethod.EV_EBITDA

    def test_fcf_absent_and_no_ebitda_blocks_all(self):
        """FCF ausente e EBITDA ausente → ambos métodos bloqueados."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=None,
            ebitda=None,
            net_debt=5_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None


# ─────────────────────────────────────────────────────────────────────────────
#  4. net_debt ausente bloqueia EV (D-COMM-03)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetDebtAbsentBlock:
    """D-COMM-03: net_debt ausente bloqueia enterprise value."""

    def test_net_debt_none_blocks_shares_validation(self):
        """net_debt=None → D-COMM-03 bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            net_debt=None,
            shares_outstanding=1_000.0,
        )
        block = _validate_shares_and_net_debt(inputs)
        assert block is not None
        assert "D-COMM-03" in block
        assert "net_debt" in block.lower()

    def test_net_debt_none_blocks_dcf(self):
        """Sem net_debt → DCF não pode calcular equity value."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=None,              # ausente
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_net_debt_none_blocks_ev_ebitda(self):
        """Sem net_debt → EV/EBITDA não pode calcular equity value."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=5_000.0,
            net_debt=None,              # ausente
            shares_outstanding=1_000.0,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_net_debt_negative_allowed(self):
        """net_debt negativo (posição de caixa) é permitido — não bloqueia."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            net_debt=-2_000.0,          # caixa líquido
            shares_outstanding=1_000.0,
        )
        block = _validate_shares_and_net_debt(inputs)
        # Não deve bloquear por net_debt negativo (empresa com caixa líquido é válida)
        if block:
            assert "D-COMM-03" not in block

    def test_shares_outstanding_none_blocks(self):
        """shares_outstanding=None → D-COMM-04 bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            net_debt=5_000.0,
            shares_outstanding=None,
        )
        block = _validate_shares_and_net_debt(inputs)
        assert block is not None
        assert "D-COMM-04" in block

    def test_shares_outstanding_zero_blocks(self):
        """shares_outstanding=0 → D-COMM-04 bloqueado."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            net_debt=5_000.0,
            shares_outstanding=0.0,
        )
        block = _validate_shares_and_net_debt(inputs)
        assert block is not None
        assert "D-COMM-04" in block


# ─────────────────────────────────────────────────────────────────────────────
#  5. PETR4 preserva fair_value=81.12 existente
# ─────────────────────────────────────────────────────────────────────────────

class TestPETR4PreserveFairValue:
    """PETR4=81.12 deve ser preservado quando existing_fair_value fornecido."""

    def test_petr4_preserved_value_in_dict(self):
        """PETR4=81.12 está no dicionário COMMODITY_PRESERVED_FAIR_VALUES."""
        assert "PETR4" in COMMODITY_PRESERVED_FAIR_VALUES
        assert abs(COMMODITY_PRESERVED_FAIR_VALUES["PETR4"] - 81.12) < 0.01

    def test_petr4_preserves_existing_fv_without_force_recalc(self):
        """Com existing_fair_value=81.12 e force_recalc=False → PRESERVE."""
        inputs = CommodityValuationInputs(
            ticker="PETR4",
            market_price=44.48,
            source_quality=CommodityInputQuality.EXCEL_PIPELINE,
            existing_fair_value=81.12,
        )
        result = calculate_commodity_valuation(inputs, force_recalc=False)
        assert result.blocked is False
        assert abs(result.fair_value - 81.12) < 0.01
        assert result.status == CommodityValuationStatus.PRESERVE_EXISTING
        assert result.method_used == CommodityValuationMethod.PRESERVE

    def test_petr4_upside_calculated_when_market_price_available(self):
        """Upside é calculado corretamente para PETR4 preservado."""
        inputs = CommodityValuationInputs(
            ticker="PETR4",
            market_price=44.48,
            existing_fair_value=81.12,
        )
        result = calculate_commodity_valuation(inputs, force_recalc=False)
        assert result.upside_pct is not None
        expected_upside = round((81.12 / 44.48 - 1) * 100, 2)
        assert abs(result.upside_pct - expected_upside) < 0.5

    def test_force_recalc_bypasses_preserve(self):
        """force_recalc=True ignora existing_fair_value e tenta recalcular."""
        inputs = CommodityValuationInputs(
            ticker="PETR4",
            market_price=44.48,
            source_quality=CommodityInputQuality.EXCEL_PIPELINE,
            existing_fair_value=81.12,
        )
        result = calculate_commodity_valuation(inputs, force_recalc=True)
        # Com force_recalc e sem FCF/EBITDA → deve bloquear (mas não por PRESERVE)
        assert result.method_used != CommodityValuationMethod.PRESERVE
        assert result.status != CommodityValuationStatus.PRESERVE_EXISTING

    def test_any_ticker_preserves_existing_fv(self):
        """Qualquer ticker com existing_fair_value → preservado sem force_recalc."""
        inputs = CommodityValuationInputs(
            ticker="PRIO3",
            market_price=68.40,
            existing_fair_value=90.00,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs, force_recalc=False)
        assert result.blocked is False
        assert abs(result.fair_value - 90.00) < 0.01
        assert result.status == CommodityValuationStatus.PRESERVE_EXISTING


# ─────────────────────────────────────────────────────────────────────────────
#  6. VALE3 bloqueada por NEEDS_DATA (ri_docs=0)
# ─────────────────────────────────────────────────────────────────────────────

class TestVALE3NeedsData:
    """VALE3 permanece bloqueada por NEEDS_DATA enquanto ri_docs=0."""

    def test_vale3_in_commodity_tickers(self):
        """VALE3 está no grupo COMMODITY."""
        assert "VALE3" in COMMODITY_TICKERS
        assert "VALE3" in MINING_TICKERS

    def test_vale3_not_in_oil_gas_group(self):
        """VALE3 não está no grupo OIL_GAS."""
        assert "VALE3" not in OIL_GAS_TICKERS

    def test_diagnose_vale3_returns_needs_data(self):
        """diagnose_commodity_tickers retorna NEEDS_DATA para VALE3 (ri_docs=0)."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=0,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=83.10,
        ):
            diag = diagnose_commodity_tickers(tickers=["VALE3"])
        assert "VALE3" in diag
        info = diag["VALE3"]
        assert info["status"] == CommodityValuationStatus.NEEDS_DATA
        assert info["ri_docs"] == 0
        assert info["result"].blocked is True
        assert "NEEDS_DATA" in info["result"].block_reason

    def test_vale3_result_has_no_fair_value(self):
        """VALE3 com NEEDS_DATA nunca produz fair_value."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=0,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=83.10,
        ):
            diag = diagnose_commodity_tickers(tickers=["VALE3"])
        assert diag["VALE3"]["result"].fair_value is None
        assert diag["VALE3"]["result"].confidence == 0.0

    def test_needs_data_block_contains_ri_docs_info(self):
        """Block reason para NEEDS_DATA menciona ri_docs=0."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=0,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=None,
        ):
            diag = diagnose_commodity_tickers(tickers=["VALE3"])
        block_reason = diag["VALE3"]["result"].block_reason
        assert "ri_docs=0" in block_reason


# ─────────────────────────────────────────────────────────────────────────────
#  7. PRIO3/RECV3 só calculam com inputs reais
# ─────────────────────────────────────────────────────────────────────────────

class TestPRIO3RECV3NeedsFinancials:
    """PRIO3 e RECV3 devem ser bloqueados sem dados financeiros estruturados."""

    @pytest.mark.parametrize("ticker", ["PRIO3", "RECV3"])
    def test_ticker_blocked_without_financial_data(self, ticker):
        """PRIO3/RECV3 sem FCF/EBITDA → NEEDS_FINANCIALS."""
        inputs = CommodityValuationInputs(
            ticker=ticker,
            market_price=68.40 if ticker == "PRIO3" else 12.31,
            source_quality=CommodityInputQuality.ABSENT,
            # Sem FCF, EBITDA, WACC, etc.
        )
        result = calculate_commodity_valuation(inputs, force_recalc=False)
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    @pytest.mark.parametrize("ticker", ["PRIO3", "RECV3"])
    def test_diagnose_returns_needs_financials_without_data(self, ticker):
        """diagnose retorna NEEDS_FINANCIALS para PRIO3/RECV3 sem dados estruturados."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=109 if ticker == "PRIO3" else 126,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            return_value=None,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=68.40 if ticker == "PRIO3" else 12.31,
        ):
            diag = diagnose_commodity_tickers(tickers=[ticker])

        assert ticker in diag
        info = diag[ticker]
        assert info["status"] == CommodityValuationStatus.NEEDS_FINANCIALS
        assert info["result"].blocked is True
        assert info["result"].fair_value is None

    def test_prio3_calculates_when_real_data_provided(self):
        """PRIO3 com inputs reais produz fair_value via DCF."""
        inputs = CommodityValuationInputs(
            ticker="PRIO3",
            free_cash_flow=3_000.0,       # R$ 3 bilhões FCF real
            net_debt=5_000.0,             # R$ 5 bilhões dívida
            shares_outstanding=1_100.0,   # 1.1 bilhão ações
            wacc=0.13,
            terminal_growth=0.04,
            market_price=68.40,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == CommodityValuationMethod.DCF_FCFF

    def test_recv3_calculates_when_real_ebitda_provided(self):
        """RECV3 com EBITDA real produz fair_value via EV/EBITDA."""
        inputs = CommodityValuationInputs(
            ticker="RECV3",
            ebitda=800.0,                # R$ 800 milhões EBITDA
            net_debt=1_200.0,            # R$ 1.2 bilhão dívida
            shares_outstanding=500.0,    # 500 milhões ações
            ev_ebitda_multiple=4.5,
            market_price=12.31,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == CommodityValuationMethod.EV_EBITDA


# ─────────────────────────────────────────────────────────────────────────────
#  8. Router normaliza PETR4/PRIO3/RECV3 para COMMODITY
# ─────────────────────────────────────────────────────────────────────────────

class TestRouterNormalizesCommodity:
    """Router e SectorNormalizer devem rotear PETR4/PRIO3/RECV3 para COMMODITY."""

    @pytest.mark.parametrize("ticker,sector,type_", [
        ("PETR4", "energy", "oil_gas"),
        ("PRIO3", "energy", "oil_gas"),
        ("RECV3", "energy", "oil_gas"),
    ])
    def test_normalizer_maps_oil_gas_to_commodity(self, ticker, sector, type_):
        """SectorNormalizer mapeia energy/oil_gas → COMMODITY."""
        from src.valuation.sector_normalizer import normalize_sector
        result = normalize_sector(ticker=ticker, sector=sector, type=type_)
        assert result.canonical_sector == "COMMODITY"
        assert result.confidence >= 0.8

    @pytest.mark.parametrize("ticker", ["PETR4", "PRIO3", "RECV3"])
    def test_router_routes_commodity_to_dcf(self, ticker):
        """Router roteia COMMODITY → DCF como método primário."""
        from src.valuation.router import get_valuation_method, Provenance, ValuationMethod
        decision = get_valuation_method(
            ticker,
            sector="COMMODITY",
            coverage_status="partial",
            provenance=Provenance(source="TRACEABLE"),
        )
        assert decision.blocked is False
        assert decision.method_suggested == ValuationMethod.DCF

    def test_vale3_materials_also_maps_to_commodity(self):
        """VALE3 (materials/mining) também normaliza para COMMODITY."""
        from src.valuation.sector_normalizer import normalize_sector
        result = normalize_sector(ticker="VALE3", sector="materials", type="mining")
        assert result.canonical_sector == "COMMODITY"

    def test_router_blocks_needs_data_status(self):
        """Router bloqueia COMMODITY com coverage_status=needs_data."""
        from src.valuation.router import get_valuation_method, Provenance
        decision = get_valuation_method(
            "VALE3",
            sector="COMMODITY",
            coverage_status="needs_data",
            provenance=Provenance(source="TRACEABLE"),
        )
        assert decision.blocked is True
        assert "NEEDS_CVM_DATA" in decision.block_reason


# ─────────────────────────────────────────────────────────────────────────────
#  9. Cálculo DCF/FCFF correto com inputs válidos
# ─────────────────────────────────────────────────────────────────────────────

class TestDCFCalculation:
    """Testa o motor DCF/FCFF com inputs válidos."""

    def test_dcf_calculates_fair_value(self, valid_dcf_inputs):
        """DCF produz fair_value com inputs válidos."""
        result = calculate_commodity_valuation(valid_dcf_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == CommodityValuationMethod.DCF_FCFF

    def test_dcf_formula_validation(self, valid_dcf_inputs):
        """Verifica fórmula DCF: FCF / (WACC - g) - net_debt / shares."""
        inputs = valid_dcf_inputs
        # FCF=10000, WACC=0.12, g=0.04, net_debt=20000, shares=13000
        ev = 10_000 / (0.12 - 0.04)   # = 125_000
        equity = ev - 20_000            # = 105_000
        expected_fv = round(equity / 13_000, 2)  # = 8.08

        result = calculate_commodity_valuation(inputs)
        assert abs(result.fair_value - expected_fv) < 0.01
        assert abs(result.enterprise_value - ev) < 0.01
        assert abs(result.equity_value - equity) < 0.01

    def test_dcf_populates_wacc_and_g(self, valid_dcf_inputs):
        """DCF preenche wacc_used e terminal_growth_used no resultado."""
        result = calculate_commodity_valuation(valid_dcf_inputs)
        assert result.wacc_used is not None
        assert abs(result.wacc_used - 0.12) < 0.001
        assert result.terminal_growth_used is not None
        assert abs(result.terminal_growth_used - 0.04) < 0.001

    def test_dcf_upside_calculated(self, valid_dcf_inputs):
        """Upside é calculado corretamente."""
        result = calculate_commodity_valuation(valid_dcf_inputs)
        assert result.upside_pct is not None
        expected = round((result.fair_value / valid_dcf_inputs.market_price - 1) * 100, 2)
        assert abs(result.upside_pct - expected) < 0.1

    def test_dcf_confidence_scales_with_quality(self):
        """Confiança DCF é maior para CVM_LIVE que EXCEL_PIPELINE."""
        base = dict(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
        )
        cvm_result = calculate_commodity_valuation(
            CommodityValuationInputs(**base, source_quality=CommodityInputQuality.CVM_LIVE)
        )
        excel_result = calculate_commodity_valuation(
            CommodityValuationInputs(**base, source_quality=CommodityInputQuality.EXCEL_PIPELINE)
        )
        if not cvm_result.blocked and not excel_result.blocked:
            assert cvm_result.confidence > excel_result.confidence

    def test_dcf_negative_equity_value_blocked(self):
        """equity_value < 0 (net_debt > EV) → NEEDS_REVIEW."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=1_000.0,
            net_debt=50_000.0,    # net_debt >> EV → equity negativo
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.status == CommodityValuationStatus.NEEDS_REVIEW


# ─────────────────────────────────────────────────────────────────────────────
#  10. Cálculo EV/EBITDA correto com inputs válidos
# ─────────────────────────────────────────────────────────────────────────────

class TestEVEBITDACalculation:
    """Testa o motor EV/EBITDA com inputs válidos."""

    def test_ev_ebitda_calculates_fair_value(self, valid_ev_ebitda_inputs):
        """EV/EBITDA produz fair_value com inputs válidos."""
        result = calculate_commodity_valuation(valid_ev_ebitda_inputs)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == CommodityValuationMethod.EV_EBITDA

    def test_ev_ebitda_formula_validation(self, valid_ev_ebitda_inputs):
        """Verifica fórmula EV/EBITDA: EBITDA × múltiplo - net_debt / shares."""
        inputs = valid_ev_ebitda_inputs
        # EBITDA=5000, múltiplo=5.0, net_debt=8000, shares=1000
        ev = 5_000 * 5.0           # = 25_000
        equity = ev - 8_000         # = 17_000
        expected_fv = round(equity / 1_000, 2)  # = 17.00

        result = calculate_commodity_valuation(inputs)
        assert abs(result.fair_value - expected_fv) < 0.01
        assert abs(result.enterprise_value - ev) < 0.01
        assert abs(result.equity_value - equity) < 0.01

    def test_ev_ebitda_populates_multiple_used(self, valid_ev_ebitda_inputs):
        """EV/EBITDA preenche ev_ebitda_used no resultado."""
        result = calculate_commodity_valuation(valid_ev_ebitda_inputs)
        assert result.ev_ebitda_used is not None
        assert abs(result.ev_ebitda_used - 5.0) < 0.01

    def test_ev_ebitda_uses_default_multiple_when_not_provided(self):
        """Múltiplo default de oil_gas é usado quando ev_ebitda_multiple=None."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=3_000.0,
            net_debt=5_000.0,
            shares_outstanding=500.0,
            ev_ebitda_multiple=None,   # usa default
            subsector="oil_gas",
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        if not result.blocked:
            assert abs(result.ev_ebitda_used - DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE) < 0.01

    def test_ev_ebitda_confidence_lower_than_dcf(self):
        """EV/EBITDA tem confiança menor que DCF (método secundário)."""
        # Input com DCF disponível
        dcf_inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=5_000.0,
            ebitda=8_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            wacc=0.12,
            terminal_growth=0.04,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        # Input apenas com EBITDA (sem DCF)
        ev_only_inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=8_000.0,
            net_debt=10_000.0,
            shares_outstanding=1_000.0,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        dcf_result = calculate_commodity_valuation(dcf_inputs)
        ev_result = calculate_commodity_valuation(ev_only_inputs)

        if not dcf_result.blocked and not ev_result.blocked:
            assert dcf_result.confidence > ev_result.confidence

    def test_ev_ebitda_negative_equity_blocked(self):
        """equity_value < 0 (net_debt > EV) → NEEDS_REVIEW."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ebitda=1_000.0,
            net_debt=100_000.0,   # net_debt >> EV
            shares_outstanding=1_000.0,
            ev_ebitda_multiple=4.5,
            source_quality=CommodityInputQuality.CVM_LIVE,
        )
        result = calculate_commodity_valuation(inputs)
        assert result.blocked is True
        assert result.status == CommodityValuationStatus.NEEDS_REVIEW


# ─────────────────────────────────────────────────────────────────────────────
#  11. save_commodity_valuation_result — governança de preservação
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveCommodityValuationResult:
    """Testa save_commodity_valuation_result() com governança de preservação."""

    def _make_result(self, fair_value: float = 50.0, ticker: str = "TEST4") -> CommodityValuationResult:
        return CommodityValuationResult(
            ticker=ticker,
            fair_value=fair_value,
            upside_pct=10.0,
            valuation_method=CommodityValuationMethod.DCF_FCFF,
            method_used=CommodityValuationMethod.DCF_FCFF,
            confidence=0.90,
            input_quality=CommodityInputQuality.CVM_LIVE,
            status=CommodityValuationStatus.VALUATION_READY,
            blocked=False,
            enterprise_value=100_000.0,
            equity_value=80_000.0,
            wacc_used=0.12,
            terminal_growth_used=0.04,
        )

    def test_write_false_returns_false(self):
        """write=False → não grava, retorna False."""
        result = self._make_result()
        saved = save_commodity_valuation_result("TEST4", result, write=False)
        assert saved is False

    def test_petr4_not_overwritten_without_force_recalc(self):
        """PETR4 não deve ser sobrescrito sem force_recalc=True."""
        result = self._make_result(fair_value=99.99, ticker="PETR4")
        saved = save_commodity_valuation_result(
            "PETR4", result, write=True, force_recalc=False
        )
        assert saved is False

    def test_none_fair_value_returns_false(self, tmp_db):
        """fair_value=None com write=True → retorna False (proteção)."""
        result = CommodityValuationResult(
            ticker="TEST4",
            fair_value=None,
            blocked=True,
        )
        saved = save_commodity_valuation_result(
            "TEST4", result, db_path=tmp_db, write=True
        )
        assert saved is False

    def test_non_preserved_ticker_writes_with_write_true(self, tmp_db):
        """Ticker não protegido com write=True grava na tabela."""
        result = self._make_result(fair_value=35.50, ticker="PRIO3")
        saved = save_commodity_valuation_result(
            "PRIO3", result,
            db_path=tmp_db,
            write=True,
            force_recalc=False,
            input_quality="CVM_LIVE",
            valuation_date="2026-05-25",
        )
        assert saved is True

        # Verificar que foi gravado
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute(
            "SELECT ticker, fair_value, method_used FROM commodity_valuation_results WHERE ticker='PRIO3'"
        )
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "PRIO3"
        assert abs(row[1] - 35.50) < 0.01
        assert row[2] == CommodityValuationMethod.DCF_FCFF

    def test_petr4_writes_with_force_recalc(self, tmp_db):
        """PETR4 com force_recalc=True permite escrita."""
        result = self._make_result(fair_value=85.00, ticker="PETR4")
        saved = save_commodity_valuation_result(
            "PETR4", result,
            db_path=tmp_db,
            write=True,
            force_recalc=True,
            valuation_date="2026-05-25",
        )
        assert saved is True

    def test_records_enterprise_equity_in_db(self, tmp_db):
        """enterprise_value e equity_value são registrados no banco."""
        result = self._make_result(fair_value=20.00, ticker="RECV3")
        result.enterprise_value = 15_000.0
        result.equity_value = 12_000.0
        result.wacc_used = 0.12
        result.terminal_growth_used = 0.04

        save_commodity_valuation_result(
            "RECV3", result,
            db_path=tmp_db,
            write=True,
            force_recalc=False,
            valuation_date="2026-05-25",
        )
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute(
            "SELECT enterprise_value, equity_value, wacc_used, terminal_growth_used "
            "FROM commodity_valuation_results WHERE ticker='RECV3'"
        )
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert abs(row[0] - 15_000.0) < 0.01
        assert abs(row[1] - 12_000.0) < 0.01
        assert abs(row[2] - 0.12) < 0.001
        assert abs(row[3] - 0.04) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
#  12. Estrutura e exports do módulo
# ─────────────────────────────────────────────────────────────────────────────

class TestCommodityModelStructure:
    """Verifica estrutura, dataclasses e exports do módulo."""

    def test_commodity_tickers_frozenset(self):
        """COMMODITY_TICKERS contém os 4 tickers corretos."""
        assert isinstance(COMMODITY_TICKERS, frozenset)
        expected = {"PETR4", "PRIO3", "RECV3", "VALE3"}
        assert COMMODITY_TICKERS == expected

    def test_oil_gas_tickers_subset(self):
        """OIL_GAS_TICKERS ⊂ COMMODITY_TICKERS."""
        assert OIL_GAS_TICKERS.issubset(COMMODITY_TICKERS)
        expected = {"PETR4", "PRIO3", "RECV3"}
        assert OIL_GAS_TICKERS == expected

    def test_mining_tickers_subset(self):
        """MINING_TICKERS ⊂ COMMODITY_TICKERS."""
        assert MINING_TICKERS.issubset(COMMODITY_TICKERS)
        assert "VALE3" in MINING_TICKERS

    def test_preserved_fair_values_dict(self):
        """COMMODITY_PRESERVED_FAIR_VALUES tem PETR4=81.12."""
        assert "PETR4" in COMMODITY_PRESERVED_FAIR_VALUES
        assert abs(COMMODITY_PRESERVED_FAIR_VALUES["PETR4"] - 81.12) < 0.01

    def test_default_multiples_positive(self):
        """Múltiplos default são positivos e razoáveis."""
        assert DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE > 0
        assert DEFAULT_MINING_EV_EBITDA_MULTIPLE > 0
        assert DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE <= 20  # razoável para E&P
        assert DEFAULT_MINING_EV_EBITDA_MULTIPLE <= 20

    def test_commodity_valuation_inputs_dataclass(self):
        """CommodityValuationInputs instancia e normaliza ticker."""
        inputs = CommodityValuationInputs(ticker="petr4")
        assert inputs.ticker == "PETR4"  # normalizado para uppercase
        assert inputs.free_cash_flow is None
        assert inputs.source_quality == CommodityInputQuality.ABSENT

    def test_commodity_valuation_result_dataclass(self):
        """CommodityValuationResult instancia com blocked=True por default."""
        result = CommodityValuationResult(ticker="PRIO3")
        assert result.ticker == "PRIO3"
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_blocked_result_factory(self):
        """blocked_result() cria resultado bloqueado correto."""
        result = CommodityValuationResult.blocked_result(
            ticker="TEST4",
            block_reason="Teste",
            status=CommodityValuationStatus.NEEDS_FINANCIALS,
        )
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0
        assert result.block_reason == "Teste"

    def test_preserved_result_factory(self):
        """preserved_result() cria resultado preservado correto."""
        result = CommodityValuationResult.preserved_result(
            ticker="PETR4",
            fair_value=81.12,
            market_price=44.48,
        )
        assert result.blocked is False
        assert abs(result.fair_value - 81.12) < 0.01
        assert result.status == CommodityValuationStatus.PRESERVE_EXISTING
        assert result.upside_pct is not None
        assert result.confidence > 0

    def test_blocked_result_confidence_zero(self):
        """Resultado bloqueado com confiança > 0 → normalizado para 0."""
        result = CommodityValuationResult(
            ticker="TEST4",
            blocked=True,
            confidence=0.8,   # inconsistente com blocked=True
        )
        assert result.confidence == 0.0  # normalizado pelo __post_init__

    def test_effective_ev_ebitda_multiple_explicit(self):
        """effective_ev_ebitda_multiple retorna o valor explícito."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            ev_ebitda_multiple=6.0,
        )
        assert abs(inputs.effective_ev_ebitda_multiple - 6.0) < 0.01

    def test_effective_ev_ebitda_multiple_oil_gas_default(self):
        """effective_ev_ebitda_multiple usa default oil_gas quando nenhum fornecido."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            subsector="oil_gas",
        )
        assert abs(inputs.effective_ev_ebitda_multiple - DEFAULT_OIL_GAS_EV_EBITDA_MULTIPLE) < 0.01

    def test_effective_ev_ebitda_multiple_mining_default(self):
        """effective_ev_ebitda_multiple usa default mining para subsector mining."""
        inputs = CommodityValuationInputs(
            ticker="VALE3",
            subsector="mining",
        )
        assert abs(inputs.effective_ev_ebitda_multiple - DEFAULT_MINING_EV_EBITDA_MULTIPLE) < 0.01

    def test_fcf_per_share_property(self):
        """CommodityValuationInputs.fcf_per_share calcula corretamente."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=10_000.0,
            shares_outstanding=2_000.0,
        )
        assert abs(inputs.fcf_per_share - 5.0) < 0.01

    def test_fcf_per_share_none_when_shares_missing(self):
        """fcf_per_share retorna None quando shares_outstanding=None."""
        inputs = CommodityValuationInputs(
            ticker="TEST4",
            free_cash_flow=10_000.0,
            shares_outstanding=None,
        )
        assert inputs.fcf_per_share is None


# ─────────────────────────────────────────────────────────────────────────────
#  13. Importação via pacotes valuation e models
# ─────────────────────────────────────────────────────────────────────────────

class TestCommodityModelImports:
    """Testa que todos os exports estão disponíveis nos pacotes pai."""

    def test_models_package_imports_commodity(self):
        """src.valuation.models importa commodity_model corretamente."""
        from src.valuation.models import (
            CommodityValuationInputs,
            CommodityValuationResult,
            CommodityInputQuality,
            CommodityValuationStatus,
            CommodityValuationMethod,
            COMMODITY_TICKERS,
            COMMODITY_PRESERVED_FAIR_VALUES,
            calculate_commodity_valuation,
            diagnose_commodity_tickers,
            save_commodity_valuation_result,
        )
        assert CommodityValuationInputs is not None
        assert calculate_commodity_valuation is not None
        assert "PETR4" in COMMODITY_TICKERS

    def test_valuation_package_exports_commodity_model(self):
        """src.valuation exporta commodity_model corretamente."""
        from src.valuation import (
            CommodityValuationInputs,
            CommodityValuationResult,
            CommodityInputQuality,
            CommodityValuationStatus,
            CommodityValuationMethod,
            COMMODITY_TICKERS,
            OIL_GAS_TICKERS,
            MINING_TICKERS,
            COMMODITY_PRESERVED_FAIR_VALUES,
            calculate_commodity_valuation,
            diagnose_commodity_tickers,
            save_commodity_valuation_result,
        )
        assert len(COMMODITY_TICKERS) == 4
        assert len(OIL_GAS_TICKERS) == 3
        assert len(MINING_TICKERS) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  14. diagnose_commodity_tickers — smoke tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDiagnoseCommodityTickers:
    """Smoke tests do diagnóstico batch dos tickers COMMODITY."""

    def test_diagnose_returns_all_4_tickers(self):
        """diagnose_commodity_tickers retorna entrada para todos os 4 tickers."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            side_effect=lambda t: 0 if t == "VALE3" else 100,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            side_effect=lambda t: 81.12 if t == "PETR4" else None,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            side_effect=lambda t: {
                "PETR4": 44.48, "PRIO3": 68.40, "RECV3": 12.31, "VALE3": 83.10
            }.get(t),
        ):
            diag = diagnose_commodity_tickers()

        assert len(diag) == 4
        for ticker in ["PETR4", "PRIO3", "RECV3", "VALE3"]:
            assert ticker in diag

    def test_diagnose_each_result_has_required_keys(self):
        """Cada ticker no diagnóstico tem as chaves obrigatórias."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=0,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            return_value=None,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=None,
        ):
            diag = diagnose_commodity_tickers()

        required_keys = {"status", "existing_fair_value", "market_price", "ri_docs", "source_quality", "result"}
        for ticker, info in diag.items():
            assert required_keys.issubset(info.keys()), (
                f"{ticker} faltando chaves: {required_keys - info.keys()}"
            )

    def test_diagnose_result_is_commodity_valuation_result(self):
        """O campo 'result' é sempre CommodityValuationResult."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=0,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            return_value=None,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=None,
        ):
            diag = diagnose_commodity_tickers()

        for ticker, info in diag.items():
            assert isinstance(info["result"], CommodityValuationResult), (
                f"{ticker}: result não é CommodityValuationResult"
            )

    def test_diagnose_petr4_preserve_when_fair_value_exists(self):
        """diagnose retorna PRESERVE_EXISTING para PETR4 com fair_value=81.12."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=131,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            return_value=81.12,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=44.48,
        ):
            diag = diagnose_commodity_tickers(tickers=["PETR4"])

        assert diag["PETR4"]["status"] == CommodityValuationStatus.PRESERVE_EXISTING
        assert abs(diag["PETR4"]["result"].fair_value - 81.12) < 0.01
        assert diag["PETR4"]["result"].blocked is False

    def test_diagnose_subset_tickers(self):
        """diagnose_commodity_tickers aceita subconjunto de tickers."""
        with patch(
            "src.valuation.models.commodity_model._count_ri_documents",
            return_value=100,
        ), patch(
            "src.valuation.models.commodity_model._load_existing_fair_value_commodity",
            return_value=None,
        ), patch(
            "src.valuation.models.commodity_model._load_market_price_commodity",
            return_value=None,
        ):
            diag = diagnose_commodity_tickers(tickers=["PETR4", "VALE3"])
        assert len(diag) == 2
        assert "PETR4" in diag
        assert "VALE3" in diag
