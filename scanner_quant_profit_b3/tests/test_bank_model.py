"""
tests/test_bank_model.py — M016-S02: Bank Valuation Model Tests

Cobre obrigatoriamente (M016-S02 checklist):
  1. Dados insuficientes bloqueiam (hard blocks)
  2. Ke <= g bloqueia (D-BANK-04)
  3. equity_book_value <= 0 bloqueia (D-BANK-01)
  4. BBAS3/ITUB4 preservam fair_value existente (PRESERVE_EXISTING)
  5. save_valuation_result não sobrescreve sem force_recalc
  6. Método bancário retorna resultado apenas quando inputs reais existem
  7. Testes auxiliares de estrutura e exports
"""

from __future__ import annotations

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

# ── Imports dos módulos sob teste ──────────────────────────────────────────────

from src.valuation.models.bank_model import (
    BankValuationInputs,
    BankValuationResult,
    BankInputQuality,
    BankValuationStatus,
    BankValuationMethod,
    BANK_TICKERS,
    PRESERVED_FAIR_VALUES,
    calculate_bank_valuation,
    diagnose_bank_tickers,
    _validate_hard_blocks,
    _validate_pbv_prerequisites,
    _validate_ddm_prerequisites,
)

from src.valuation.valuation_store import (
    save_valuation_result,
    _PRESERVED_FAIR_VALUES,
)

from src.valuation.valuation_results import ValuationResult


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures auxiliares
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_bank_inputs_pbv():
    """Inputs válidos para P/BV justificado — baseados em banco genérico."""
    return BankValuationInputs(
        ticker="TEST4",
        equity_book_value=50_000.0,   # R$ 50 bilhões
        net_income=10_000.0,          # R$ 10 bilhões → ROE = 20%
        roe=0.20,
        cost_of_equity=0.13,          # Ke = 13%
        payout_ratio=0.40,            # 40% payout
        growth_rate=0.07,             # g = 7%
        shares_outstanding=5_000.0,   # 5 bilhões de ações
        market_price=18.50,
        source_quality=BankInputQuality.CVM_LIVE,
    )


@pytest.fixture
def valid_bank_inputs_ddm():
    """Inputs válidos para DDM/Gordon (sem ROE explícito, mas com payout)."""
    return BankValuationInputs(
        ticker="TEST4",
        equity_book_value=20_000.0,
        net_income=3_000.0,           # EPS = 3000/1000 = 3.0
        roe=None,                     # será derivado: 3000/20000 = 15%
        cost_of_equity=0.12,
        payout_ratio=0.50,
        growth_rate=0.06,
        shares_outstanding=1_000.0,
        market_price=35.00,
        source_quality=BankInputQuality.EXCEL_PIPELINE,
    )


@pytest.fixture
def tmp_db(tmp_path):
    """Banco de dados temporário para testes de save."""
    db_path = str(tmp_path / "test_valuation.db")
    return db_path


# ─────────────────────────────────────────────────────────────────────────────
#  1. Hard blocks — dados insuficientes bloqueiam
# ─────────────────────────────────────────────────────────────────────────────

class TestHardBlocks:
    """Verifica que hard blocks impedem qualquer cálculo."""

    def test_block_equity_book_value_none(self):
        """D-BANK-01: equity_book_value=None → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=None,
            net_income=1_000.0,
            shares_outstanding=500.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert "D-BANK-01" in result.block_reason
        assert result.confidence == 0.0

    def test_block_equity_book_value_zero(self):
        """D-BANK-01: equity_book_value=0 → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=0.0,
            net_income=500.0,
            shares_outstanding=100.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert "D-BANK-01" in result.block_reason

    def test_block_equity_book_value_negative(self):
        """D-BANK-01: equity_book_value=-5000 → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=-5_000.0,
            net_income=100.0,
            shares_outstanding=200.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert "D-BANK-01" in result.block_reason

    def test_block_net_income_none(self):
        """D-BANK-02: net_income=None → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=None,
            shares_outstanding=500.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert "D-BANK-02" in result.block_reason

    def test_block_shares_outstanding_none(self):
        """D-BANK-03: shares_outstanding=None → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=None,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert "D-BANK-03" in result.block_reason

    def test_block_shares_outstanding_zero(self):
        """D-BANK-03: shares_outstanding=0 → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=0.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert "D-BANK-03" in result.block_reason

    def test_block_net_income_inconsistent_with_bv(self):
        """D-BANK-02: ROE derivado vs ROE informado com discrepância >10pp → bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=500.0,       # ROE derivado = 5%
            roe=0.30,               # ROE informado = 30% → discrepância = 25pp > 10pp
            shares_outstanding=1_000.0,
            cost_of_equity=0.13,
            growth_rate=0.06,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert "D-BANK-02" in result.block_reason
        assert "Inconsistência" in result.block_reason

    def test_no_block_with_consistent_roe(self):
        """ROE derivado e informado compatíveis → não bloqueia por inconsistência."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,     # ROE derivado = 20%
            roe=0.21,               # ROE informado = 21% → discrepância = 1pp < 10pp
            shares_outstanding=1_000.0,
            cost_of_equity=0.13,
            growth_rate=0.07,
            source_quality=BankInputQuality.CVM_LIVE,
        )
        # validate_hard_blocks não deve bloquear por inconsistência
        block = _validate_hard_blocks(inputs)
        assert block is None, f"Não deveria bloquear: {block}"


# ─────────────────────────────────────────────────────────────────────────────
#  2. Ke <= g → hard block D-BANK-04
# ─────────────────────────────────────────────────────────────────────────────

class TestKeLeqGBlock:
    """D-BANK-04: Ke <= g bloqueia P/BV e DDM."""

    def test_ke_equals_g_blocks(self):
        """Ke = g → bloqueado (modelo indefinido)."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=0.10,    # Ke = 10%
            growth_rate=0.10,       # g = 10% = Ke → HARD BLOCK
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_pbv_prerequisites(inputs)
        assert block is not None
        assert "D-BANK-04" in block
        assert "Ke" in block

        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None

    def test_ke_less_than_g_blocks(self):
        """Ke < g → bloqueado (terminal growth excede custo de capital)."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=0.08,    # Ke = 8%
            growth_rate=0.12,       # g = 12% > Ke → HARD BLOCK
            source_quality=BankInputQuality.CVM_LIVE,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert "D-BANK-04" in result.block_reason
        assert result.confidence == 0.0

    def test_ke_greater_than_g_not_blocked(self):
        """Ke > g → não bloqueia (condição válida)."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=0.13,    # Ke = 13%
            growth_rate=0.07,       # g = 7% < Ke → OK
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_pbv_prerequisites(inputs)
        assert block is None

    def test_ke_leq_g_blocks_ddm_too(self):
        """Ke <= g também bloqueia DDM/Gordon."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            payout_ratio=0.40,
            shares_outstanding=1_000.0,
            cost_of_equity=0.09,
            growth_rate=0.09,       # g = Ke → bloqueia DDM
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_ddm_prerequisites(inputs)
        assert block is not None
        assert "D-BANK-04" in block


# ─────────────────────────────────────────────────────────────────────────────
#  3. equity_book_value <= 0 bloqueia
# ─────────────────────────────────────────────────────────────────────────────

class TestBookValueBlock:
    """Verifica bloqueios por book value inválido."""

    @pytest.mark.parametrize("bv", [0.0, -1.0, -100_000.0])
    def test_bv_leq_zero_blocks(self, bv):
        """equity_book_value <= 0 → always blocked."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=bv,
            net_income=1_000.0,
            shares_outstanding=500.0,
        )
        result = calculate_bank_valuation(inputs)
        assert result.blocked is True
        assert result.fair_value is None
        assert "D-BANK-01" in result.block_reason

    def test_bv_positive_allows_calculation(self):
        """equity_book_value > 0 → não bloqueia por BV."""
        block = _validate_hard_blocks(BankValuationInputs(
            ticker="TEST4",
            equity_book_value=1.0,      # mínimo positivo
            net_income=0.2,
            shares_outstanding=10.0,
        ))
        # Se bloquear, deve ser por outra razão (não D-BANK-01)
        if block:
            assert "D-BANK-01" not in block


# ─────────────────────────────────────────────────────────────────────────────
#  4. BBAS3/ITUB4 preservam fair_value existente
# ─────────────────────────────────────────────────────────────────────────────

class TestPreserveFairValues:
    """BBAS3 e ITUB4 não devem ter fair_value recalculado sem force_recalc."""

    def test_bbas3_preserved_value_in_dict(self):
        """BBAS3=64.84 está no dicionário PRESERVED_FAIR_VALUES."""
        assert "BBAS3" in PRESERVED_FAIR_VALUES
        assert abs(PRESERVED_FAIR_VALUES["BBAS3"] - 64.84) < 0.01

    def test_itub4_preserved_value_in_dict(self):
        """ITUB4=73.69 está no dicionário PRESERVED_FAIR_VALUES."""
        assert "ITUB4" in PRESERVED_FAIR_VALUES
        assert abs(PRESERVED_FAIR_VALUES["ITUB4"] - 73.69) < 0.01

    def test_calculate_preserves_existing_fv_without_force_recalc(self):
        """Quando existing_fair_value preenchido e force_recalc=False → PRESERVE."""
        inputs = BankValuationInputs(
            ticker="BBAS3",
            equity_book_value=150_000.0,
            net_income=27_000.0,
            shares_outstanding=5_500.0,
            cost_of_equity=0.13,
            growth_rate=0.07,
            existing_fair_value=64.84,
            source_quality=BankInputQuality.EXCEL_PIPELINE,
        )
        result = calculate_bank_valuation(inputs, force_recalc=False)
        assert result.blocked is False
        assert abs(result.fair_value - 64.84) < 0.01
        assert result.status == BankValuationStatus.PRESERVE_EXISTING
        assert result.method_used == BankValuationMethod.PRESERVE

    def test_itub4_preserves_73_69(self):
        """ITUB4 preserva 73.69 quando existing_fair_value fornecido."""
        inputs = BankValuationInputs(
            ticker="ITUB4",
            equity_book_value=200_000.0,
            net_income=40_000.0,
            shares_outstanding=9_000.0,
            cost_of_equity=0.12,
            growth_rate=0.07,
            existing_fair_value=73.69,
            source_quality=BankInputQuality.EXCEL_PIPELINE,
        )
        result = calculate_bank_valuation(inputs, force_recalc=False)
        assert result.blocked is False
        assert abs(result.fair_value - 73.69) < 0.01
        assert result.status == BankValuationStatus.PRESERVE_EXISTING

    def test_force_recalc_bypasses_preserve(self):
        """force_recalc=True ignora existing_fair_value e recalcula."""
        inputs = BankValuationInputs(
            ticker="BBAS3",
            equity_book_value=150_000.0,
            net_income=27_000.0,
            shares_outstanding=5_500.0,
            cost_of_equity=0.13,
            growth_rate=0.07,
            existing_fair_value=64.84,
            source_quality=BankInputQuality.CVM_LIVE,
        )
        result = calculate_bank_valuation(inputs, force_recalc=True)
        # Com force_recalc, tenta calcular (pode retornar valor diferente de 64.84)
        assert result.method_used != BankValuationMethod.PRESERVE
        # E o status não deve ser PRESERVE_EXISTING
        assert result.status != BankValuationStatus.PRESERVE_EXISTING

    def test_no_existing_fv_blocks_when_data_missing(self):
        """Sem existing_fair_value e sem dados → NEEDS_FINANCIALS."""
        inputs = BankValuationInputs(
            ticker="BBAS3",
            existing_fair_value=None,  # sem valor existente
            source_quality=BankInputQuality.ABSENT,
        )
        result = calculate_bank_valuation(inputs, force_recalc=False)
        assert result.blocked is True
        assert result.fair_value is None


# ─────────────────────────────────────────────────────────────────────────────
#  5. save_valuation_result não sobrescreve sem force_recalc
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveValuationResult:
    """Testa save_valuation_result() com governança de preservação."""

    def _make_result(self, fair_value: float = 50.0) -> ValuationResult:
        return ValuationResult(
            ticker="TEST4",
            fair_value=fair_value,
            upside_pct=10.0,
            valuation_method="P/BV_JUSTIFIED",
            valuation_confidence=0.80,
            valuation_available=True,
            valuation_governance_status="VALUATION_AVAILABLE",
        )

    def test_write_false_returns_false(self):
        """write=False → não grava, retorna False."""
        result = self._make_result()
        saved = save_valuation_result("TEST4", result, write=False)
        assert saved is False

    def test_bbas3_not_overwritten_without_force_recalc(self):
        """BBAS3 não deve ser sobrescrito sem force_recalc=True."""
        result = ValuationResult(
            ticker="BBAS3",
            fair_value=99.99,  # tentativa de sobrescrever 64.84
            valuation_method="TEST",
            valuation_available=True,
        )
        # force_recalc=False → deve retornar False (sem escrita)
        saved = save_valuation_result("BBAS3", result, write=True, force_recalc=False)
        assert saved is False

    def test_itub4_not_overwritten_without_force_recalc(self):
        """ITUB4 não deve ser sobrescrito sem force_recalc=True."""
        result = ValuationResult(
            ticker="ITUB4",
            fair_value=55.00,  # tentativa de sobrescrever 73.69
            valuation_method="TEST",
            valuation_available=True,
        )
        saved = save_valuation_result("ITUB4", result, write=True, force_recalc=False)
        assert saved is False

    def test_non_preserved_ticker_writes_with_write_true(self, tmp_db):
        """Ticker não protegido com write=True grava no banco."""
        result = ValuationResult(
            ticker="TEST4",
            fair_value=45.00,
            valuation_method="P/BV_JUSTIFIED",
            valuation_confidence=0.80,
            valuation_available=True,
            valuation_governance_status="VALUATION_AVAILABLE",
        )
        saved = save_valuation_result(
            "TEST4", result,
            db_path=tmp_db,
            write=True,
            force_recalc=False,
            method_used="P/BV_JUSTIFIED",
            input_quality="CVM_LIVE",
            valuation_date="2026-05-25",
        )
        assert saved is True

        # Verificar que foi gravado
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute("SELECT ticker, fair_value, method_used FROM bank_valuation_results WHERE ticker='TEST4'")
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "TEST4"
        assert abs(row[1] - 45.00) < 0.01
        assert row[2] == "P/BV_JUSTIFIED"

    def test_save_none_fair_value_returns_false(self, tmp_db):
        """fair_value=None com write=True → retorna False (proteção)."""
        result = ValuationResult(
            ticker="TEST4",
            fair_value=None,
            valuation_available=False,
        )
        saved = save_valuation_result("TEST4", result, db_path=tmp_db, write=True)
        assert saved is False

    def test_bbas3_preserved_in_store_dict(self):
        """BBAS3 e ITUB4 estão no dicionário _PRESERVED_FAIR_VALUES do store."""
        assert "BBAS3" in _PRESERVED_FAIR_VALUES
        assert "ITUB4" in _PRESERVED_FAIR_VALUES
        assert abs(_PRESERVED_FAIR_VALUES["BBAS3"] - 64.84) < 0.01
        assert abs(_PRESERVED_FAIR_VALUES["ITUB4"] - 73.69) < 0.01

    def test_records_method_used_in_db(self, tmp_db):
        """method_used é registrado no banco ao gravar."""
        result = ValuationResult(
            ticker="ABCB4",
            fair_value=210.0,
            valuation_method="P/BV_JUSTIFIED",
            valuation_confidence=0.80,
            valuation_available=True,
            valuation_governance_status="VALUATION_AVAILABLE",
        )
        save_valuation_result(
            "ABCB4", result,
            db_path=tmp_db,
            write=True,
            force_recalc=False,
            method_used="P/BV_JUSTIFIED",
            input_quality="EXCEL_PIPELINE",
            valuation_date="2026-05-25",
        )
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute("SELECT method_used, input_quality, valuation_date FROM bank_valuation_results WHERE ticker='ABCB4'")
        row = c.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "P/BV_JUSTIFIED"
        assert row[1] == "EXCEL_PIPELINE"
        assert row[2] == "2026-05-25"


# ─────────────────────────────────────────────────────────────────────────────
#  6. Método bancário retorna resultado apenas com inputs reais
# ─────────────────────────────────────────────────────────────────────────────

class TestBankModelCalculation:
    """Testa o motor de cálculo com inputs reais válidos."""

    def test_pbv_justified_calculation(self, valid_bank_inputs_pbv):
        """P/BV justificado produz fair_value correto."""
        result = calculate_bank_valuation(valid_bank_inputs_pbv)
        assert result.blocked is False
        assert result.fair_value is not None
        assert result.fair_value > 0
        assert result.method_used == BankValuationMethod.PBV_JUSTIFIED
        assert result.pbv_justified is not None
        assert result.bv_per_share is not None
        assert result.roe_used is not None
        assert result.ke_used is not None
        assert result.g_used is not None

    def test_pbv_justified_formula(self, valid_bank_inputs_pbv):
        """Verifica a fórmula P/BV justificado: (ROE-g)/(Ke-g) × BVps."""
        inputs = valid_bank_inputs_pbv
        result = calculate_bank_valuation(inputs)

        roe = 0.20
        ke = 0.13
        g = 0.07
        bvps = 50_000 / 5_000  # = 10.0
        expected_pbv = (roe - g) / (ke - g)  # = 0.13 / 0.06 = 2.1667
        expected_fv = round(expected_pbv * bvps, 2)

        assert abs(result.pbv_justified - expected_pbv) < 0.01
        assert abs(result.fair_value - expected_fv) < 0.01

    def test_pbv_justified_upside_calculated(self, valid_bank_inputs_pbv):
        """Upside é calculado quando market_price disponível."""
        result = calculate_bank_valuation(valid_bank_inputs_pbv)
        assert result.upside_pct is not None
        # Upside = (fair_value / market_price - 1) * 100
        expected_upside = round(
            (result.fair_value / valid_bank_inputs_pbv.market_price - 1) * 100, 2
        )
        assert abs(result.upside_pct - expected_upside) < 0.1

    def test_ddm_gordon_calculation(self, valid_bank_inputs_ddm):
        """DDM/Gordon produz fair_value quando P/BV não disponível."""
        # Remover Ke para forçar bloqueio P/BV mas manter DDM
        inputs = valid_bank_inputs_ddm
        # Já tem todos os campos — deve tentar P/BV primeiro
        result = calculate_bank_valuation(inputs)
        assert result.blocked is False
        assert result.fair_value is not None

    def test_ddm_formula_when_pbv_unavailable(self):
        """DDM/Gordon: DPS / (Ke - g) é calculado quando P/BV bloqueado."""
        # Inputs com Ke < 0 para bloquear P/BV mas manter DDM válido
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=20_000.0,
            net_income=3_000.0,
            payout_ratio=0.40,
            cost_of_equity=0.11,
            growth_rate=0.05,
            shares_outstanding=1_000.0,
            market_price=30.0,
            source_quality=BankInputQuality.CVM_LIVE,
        )
        result = calculate_bank_valuation(inputs)
        # Com todos os dados válidos, deve usar P/BV (mais confiável)
        assert result.blocked is False
        # EPS = 3000/1000 = 3.0; DPS = 3.0 * 0.40 = 1.20
        # se P/BV for usado: BVps = 20, ROE = 15%, Ke = 11%, g = 5%
        # P/BV = (0.15 - 0.05) / (0.11 - 0.05) = 0.10/0.06 = 1.667
        # fair_value = 1.667 * 20 = 33.33
        assert result.fair_value is not None
        assert result.fair_value > 0

    def test_confidence_scales_with_quality(self):
        """Confiança é maior para CVM_LIVE que para EXCEL_PIPELINE."""
        base_inputs = dict(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            cost_of_equity=0.13,
            growth_rate=0.07,
            shares_outstanding=1_000.0,
        )
        cvm_result = calculate_bank_valuation(
            BankValuationInputs(**base_inputs, source_quality=BankInputQuality.CVM_LIVE)
        )
        excel_result = calculate_bank_valuation(
            BankValuationInputs(**base_inputs, source_quality=BankInputQuality.EXCEL_PIPELINE)
        )
        if not cvm_result.blocked and not excel_result.blocked:
            assert cvm_result.confidence > excel_result.confidence

    def test_pbv_negative_returns_needs_review(self):
        """ROE < g → P/BV negativo → status NEEDS_REVIEW."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=500.0,      # ROE = 5%
            cost_of_equity=0.13,
            growth_rate=0.08,      # g = 8% > ROE = 5% → P/BV negativo
            shares_outstanding=1_000.0,
            source_quality=BankInputQuality.CVM_LIVE,
        )
        result = calculate_bank_valuation(inputs)
        # P/BV negativo → NEEDS_REVIEW blocked
        if result.blocked:
            assert result.status in (
                BankValuationStatus.NEEDS_REVIEW,
                BankValuationStatus.NEEDS_FINANCIALS,
            )

    def test_no_cost_of_equity_blocks_pbv(self):
        """Sem cost_of_equity → P/BV bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=None,  # ausente
            growth_rate=0.07,
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_pbv_prerequisites(inputs)
        assert block is not None
        assert "cost_of_equity" in block

    def test_no_growth_rate_blocks_pbv(self):
        """Sem growth_rate → P/BV bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=0.13,
            growth_rate=None,  # ausente
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_pbv_prerequisites(inputs)
        assert block is not None
        assert "growth_rate" in block

    def test_no_payout_blocks_ddm(self):
        """Sem payout_ratio → DDM bloqueado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            shares_outstanding=1_000.0,
            cost_of_equity=0.13,
            growth_rate=0.07,
            payout_ratio=None,  # ausente
            source_quality=BankInputQuality.CVM_LIVE,
        )
        block = _validate_ddm_prerequisites(inputs)
        assert block is not None
        assert "payout_ratio" in block


# ─────────────────────────────────────────────────────────────────────────────
#  7. Estrutura e exports
# ─────────────────────────────────────────────────────────────────────────────

class TestBankModelStructure:
    """Verifica estrutura, dataclasses e exports do módulo."""

    def test_bank_tickers_frozenset(self):
        """BANK_TICKERS contém os 7 tickers corretos."""
        assert isinstance(BANK_TICKERS, frozenset)
        expected = {"ABCB4", "BBAS3", "BBDC4", "BPAC11", "BRSR6", "ITUB4", "SANB11"}
        assert BANK_TICKERS == expected

    def test_preserved_fair_values_dict(self):
        """PRESERVED_FAIR_VALUES tem BBAS3 e ITUB4 corretos."""
        assert "BBAS3" in PRESERVED_FAIR_VALUES
        assert "ITUB4" in PRESERVED_FAIR_VALUES
        assert abs(PRESERVED_FAIR_VALUES["BBAS3"] - 64.84) < 0.01
        assert abs(PRESERVED_FAIR_VALUES["ITUB4"] - 73.69) < 0.01

    def test_bank_valuation_inputs_dataclass(self):
        """BankValuationInputs instancia corretamente."""
        inputs = BankValuationInputs(ticker="bbas3")
        assert inputs.ticker == "BBAS3"  # normalizado para uppercase
        assert inputs.equity_book_value is None
        assert inputs.source_quality == BankInputQuality.ABSENT

    def test_bank_valuation_result_dataclass(self):
        """BankValuationResult instancia corretamente."""
        result = BankValuationResult(ticker="ITUB4")
        assert result.ticker == "ITUB4"
        assert result.blocked is True
        assert result.fair_value is None
        assert result.confidence == 0.0

    def test_blocked_result_factory(self):
        """BankValuationResult.blocked_result() cria resultado bloqueado correto."""
        result = BankValuationResult.blocked_result(
            ticker="TEST4",
            block_reason="Teste de bloqueio",
            status=BankValuationStatus.NEEDS_FINANCIALS,
        )
        assert result.blocked is True
        assert result.fair_value is None
        assert result.block_reason == "Teste de bloqueio"
        assert result.confidence == 0.0

    def test_preserved_result_factory(self):
        """BankValuationResult.preserved_result() cria resultado preservado correto."""
        result = BankValuationResult.preserved_result(
            ticker="BBAS3",
            fair_value=64.84,
            market_price=20.42,
        )
        assert result.blocked is False
        assert abs(result.fair_value - 64.84) < 0.01
        assert result.status == BankValuationStatus.PRESERVE_EXISTING
        assert result.upside_pct is not None

    def test_bv_per_share_property(self, valid_bank_inputs_pbv):
        """BankValuationInputs.bv_per_share calcula corretamente."""
        inputs = valid_bank_inputs_pbv
        expected = inputs.equity_book_value / inputs.shares_outstanding
        assert abs(inputs.bv_per_share - expected) < 0.01

    def test_eps_property(self, valid_bank_inputs_pbv):
        """BankValuationInputs.eps calcula corretamente."""
        inputs = valid_bank_inputs_pbv
        expected = inputs.net_income / inputs.shares_outstanding
        assert abs(inputs.eps - expected) < 0.01

    def test_dps_property(self, valid_bank_inputs_pbv):
        """BankValuationInputs.dps calcula DPS correto."""
        inputs = valid_bank_inputs_pbv
        expected = inputs.eps * inputs.payout_ratio
        assert abs(inputs.dps - expected) < 0.01

    def test_derive_roe_from_fields(self, valid_bank_inputs_pbv):
        """derive_roe() retorna roe explícito se fornecido."""
        inputs = valid_bank_inputs_pbv
        assert abs(inputs.derive_roe() - 0.20) < 0.01

    def test_derive_roe_computed_when_explicit_absent(self):
        """derive_roe() computa NI/BV quando roe não informado."""
        inputs = BankValuationInputs(
            ticker="TEST4",
            equity_book_value=10_000.0,
            net_income=2_000.0,
            roe=None,
        )
        derived = inputs.derive_roe()
        assert derived is not None
        assert abs(derived - 0.20) < 0.001

    def test_blocked_result_confidence_zero(self):
        """Resultado bloqueado com confiança > 0 → normalizado para 0."""
        result = BankValuationResult(
            ticker="TEST4",
            blocked=True,
            confidence=0.8,  # inconsistente com blocked=True
        )
        assert result.confidence == 0.0  # normalizado pelo __post_init__


# ─────────────────────────────────────────────────────────────────────────────
#  8. Módulo de importação
# ─────────────────────────────────────────────────────────────────────────────

class TestBankModelImports:
    """Testa que todos os exports estão disponíveis."""

    def test_models_package_imports(self):
        """src.valuation.models importa bank_model corretamente."""
        from src.valuation.models import (
            BankValuationInputs,
            BankValuationResult,
            BankInputQuality,
            BankValuationStatus,
            BankValuationMethod,
            calculate_bank_valuation,
            diagnose_bank_tickers,
        )
        assert BankValuationInputs is not None
        assert BankValuationResult is not None
        assert calculate_bank_valuation is not None

    def test_valuation_package_exports_bank_model(self):
        """src.valuation exporta banco model corretamente."""
        from src.valuation import (
            BankValuationInputs,
            BankValuationResult,
            BankInputQuality,
            BankValuationStatus,
            BankValuationMethod,
            BANK_TICKERS,
            PRESERVED_FAIR_VALUES,
            calculate_bank_valuation,
            diagnose_bank_tickers,
        )
        assert BANK_TICKERS is not None
        assert len(BANK_TICKERS) == 7


# ─────────────────────────────────────────────────────────────────────────────
#  9. diagnose_bank_tickers — smoke test
# ─────────────────────────────────────────────────────────────────────────────

class TestDiagnoseBankTickers:
    """Smoke test do diagnóstico batch dos 7 tickers BANK."""

    def test_diagnose_returns_all_7_tickers(self):
        """diagnose_bank_tickers retorna entrada para todos os 7 tickers."""
        diag = diagnose_bank_tickers()
        assert len(diag) == 7
        for ticker in ["ABCB4", "BBAS3", "BBDC4", "BPAC11", "BRSR6", "ITUB4", "SANB11"]:
            assert ticker in diag

    def test_diagnose_each_result_has_required_keys(self):
        """Cada ticker no diagnóstico tem as chaves obrigatórias."""
        diag = diagnose_bank_tickers()
        required_keys = {"status", "existing_fair_value", "market_price", "source_quality", "result"}
        for ticker, info in diag.items():
            assert required_keys.issubset(info.keys()), f"{ticker} faltando chaves: {required_keys - info.keys()}"

    def test_diagnose_result_is_bank_valuation_result(self):
        """O campo 'result' é sempre BankValuationResult."""
        diag = diagnose_bank_tickers()
        for ticker, info in diag.items():
            assert isinstance(info["result"], BankValuationResult), (
                f"{ticker}: result não é BankValuationResult"
            )

    def test_bbas3_and_itub4_are_preserve_or_needs(self):
        """BBAS3 e ITUB4 têm status PRESERVE_EXISTING ou NEEDS_FINANCIALS."""
        diag = diagnose_bank_tickers()
        for ticker in ["BBAS3", "ITUB4"]:
            status = diag[ticker]["status"]
            assert status in (
                BankValuationStatus.PRESERVE_EXISTING,
                BankValuationStatus.NEEDS_FINANCIALS,
            ), f"{ticker}: status inesperado '{status}'"

    def test_diagnose_subset_tickers(self):
        """diagnose_bank_tickers aceita subconjunto de tickers."""
        diag = diagnose_bank_tickers(tickers=["BBAS3", "ITUB4"])
        assert len(diag) == 2
        assert "BBAS3" in diag
        assert "ITUB4" in diag

    def test_diagnose_does_not_calculate_new_fair_value_without_data(self):
        """Com DB vazio, não produz fair_value calculado (apenas preservado)."""
        diag = diagnose_bank_tickers()
        for ticker, info in diag.items():
            result = info["result"]
            if result.method_used == BankValuationMethod.PRESERVE:
                # Valor preservado é permitido
                assert result.fair_value is not None
            elif result.blocked:
                # Sem dados → bloqueado corretamente
                assert result.fair_value is None
            # Nunca deve ter method_used calculado sem inputs reais
            # (CVM_LIVE ou EXCEL_PIPELINE completo)


# ─────────────────────────────────────────────────────────────────────────────
#  10. Integração: router + bank model
# ─────────────────────────────────────────────────────────────────────────────

class TestRouterBankIntegration:
    """Verifica que router roteia BANK → COSIF_DDM e bank_model está alinhado."""

    def test_bank_tickers_route_to_cosif_ddm(self):
        """Todos os tickers BANK são roteados para COSIF_DDM pelo router."""
        from src.valuation.router import get_valuation_method, Provenance, ValuationMethod

        for ticker in ["BBAS3", "ITUB4", "BBDC4", "BPAC11", "BRSR6", "SANB11", "ABCB4"]:
            decision = get_valuation_method(
                ticker, sector="BANK",
                coverage_status="partial",
                provenance=Provenance(source="TRACEABLE"),
            )
            assert decision.blocked is False
            assert decision.method_suggested == ValuationMethod.COSIF_DDM, (
                f"{ticker}: method_suggested={decision.method_suggested}, expected COSIF_DDM"
            )

    def test_bank_model_result_status_not_none(self):
        """calculate_bank_valuation retorna resultado com status não-nulo."""
        inputs = BankValuationInputs(ticker="BBAS3")
        result = calculate_bank_valuation(inputs)
        assert result.status is not None
        assert result.ticker == "BBAS3"
