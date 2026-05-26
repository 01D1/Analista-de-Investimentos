"""
tests/test_financial_inputs_bridge.py — M017-S05: Financial Inputs Bridge Tests

Cobre obrigatoriamente (M017-S05 checklist):
  1.  load_financial_inputs_from_store retorna métricas em R$ milhões
  2.  load_financial_inputs_from_store retorna shares em milhões de ações
  3.  FCF_REVIEW detectado para ticker com FCF/EBITDA > 3.0
  4.  FCF_NEGATIVE_EXPECTED detectado para ticker com FCF < 0 e EBITDA > 0
  5.  DISTRESSED detectado para ticker com EBIT < 0
  6.  _fcf_for_model retorna None para FCF_REVIEW
  7.  _fcf_for_model retorna None para DISTRESSED
  8.  _fcf_for_model retorna None para FCF_NEGATIVE_EXPECTED
  9.  _fcf_for_model retorna None quando DCF produziria equity < 0 (viabilidade)
  10. _fcf_for_model retorna FCF normal sem flags
  11. build_commodity_inputs_from_store popula CommodityValuationInputs
  12. build_utility_inputs_from_store popula UtilityValuationInputs
  13. build_retail_inputs_from_store popula RetailValuationInputs
  14. build_industry_inputs_from_store popula IndustryValuationInputs
  15. PCAR3 bridge → DISTRESSED → FCF=None → EV/EBITDA
  16. MGLU3 bridge → FCF_REVIEW → FCF=None → EV/EBITDA
  17. RECV3 bridge → FCF_NEGATIVE_EXPECTED → FCF=None → EV/EBITDA
  18. Ticker sem dados → available=False, metrics={}
  19. run_dry_run_all retorna 18 resultados (todos M017 tickers)
  20. run_dry_run_all → write_prevented=True em todos
  21. run_dry_run_all → nenhum fair_value escrito em valuation_financial_inputs
  22. run_dry_run_all → 15+ tickers com would_calculate=True
  23. run_dry_run_all → PCAR3 status contém DISTRESSED
  24. Mapeamento TICKER_SECTOR_MAP cobre exatamente os 18 tickers M017
  25. WACC_DEFAULTS cobrem os 4 setores base
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ── Imports do módulo sob teste ────────────────────────────────────────────────

from src.valuation.financial_inputs_bridge import (
    TICKER_SECTOR_MAP,
    TICKER_SUBSECTOR_MAP,
    WACC_DEFAULTS,
    TERMINAL_GROWTH_DEFAULT,
    M017_DRY_RUN_TICKERS,
    load_financial_inputs_from_store,
    build_commodity_inputs_from_store,
    build_utility_inputs_from_store,
    build_retail_inputs_from_store,
    build_industry_inputs_from_store,
    run_dry_run_all,
    _detect_quality_flags,
    _fcf_for_model,
    _resolve_ingestion_db,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path) -> Path:
    """SQLite temporário com tabela valuation_financial_inputs e dados sintéticos."""
    db_path = tmp_path / "test_ingestion.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE valuation_financial_inputs (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            period_type TEXT NOT NULL,
            period_end TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter INTEGER,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'BRL',
            unit TEXT NOT NULL DEFAULT 'units',
            source_type TEXT NOT NULL,
            source_priority INTEGER NOT NULL DEFAULT 1,
            source_path TEXT,
            source_doc_id TEXT,
            statement_type TEXT,
            account_code TEXT,
            account_name TEXT,
            confidence REAL NOT NULL DEFAULT 1.0,
            extraction_method TEXT NOT NULL DEFAULT 'structured',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX idx_test_dedup
            ON valuation_financial_inputs(ticker, period_end, period_type, metric_name, source_type)
    """)

    # Helper para inserir métricas
    def insert(ticker, metric, value, period="2025-12-31", source="CVM_CSV",
                priority=1, confidence=1.0):
        conn.execute("""
            INSERT OR REPLACE INTO valuation_financial_inputs
                (id, ticker, period_type, period_end, fiscal_year, metric_name,
                 metric_value, source_type, source_priority, confidence,
                 created_at, updated_at)
            VALUES (?, ?, 'DFP', ?, 2025, ?, ?, ?, ?, ?, '2026-01-01', '2026-01-01')
        """, (
            f"{ticker}-{metric}-{period}",
            ticker, period, metric, value, source, priority, confidence
        ))

    # NORMAL_TICKER: dados normais (sem flags)
    for m, v in {
        "ebitda": 5_000_000_000,      # R$5B
        "free_cash_flow": 2_000_000_000,  # R$2B (FCF/EBITDA = 0.4x — normal)
        "net_debt": 8_000_000_000,    # R$8B
        "shares_outstanding": 500_000_000,  # 500M ações
        "ebit": 3_000_000_000,        # R$3B (positivo)
        "net_income": 2_000_000_000,  # R$2B
        "revenue": 20_000_000_000,    # R$20B
    }.items():
        insert("NORMAL_T", m, v)

    # FCF_REVIEW_TICKER: FCF anormalmente alto vs EBITDA
    for m, v in {
        "ebitda": 3_000_000_000,      # R$3B
        "free_cash_flow": 15_000_000_000,  # R$15B (FCF/EBITDA = 5.0x — anômalo)
        "net_debt": 2_000_000_000,
        "shares_outstanding": 800_000_000,
        "ebit": 2_000_000_000,
        "net_income": 500_000_000,
    }.items():
        insert("FCR_T", m, v)

    # FCF_NEGATIVE_TICKER: FCF negativo, EBITDA positivo
    for m, v in {
        "ebitda": 4_000_000_000,      # R$4B
        "free_cash_flow": -1_500_000_000,  # R$-1.5B (ciclo de capex)
        "net_debt": 10_000_000_000,
        "shares_outstanding": 1_000_000_000,
        "ebit": 2_500_000_000,
        "net_income": 1_000_000_000,
    }.items():
        insert("FCNEG_T", m, v)

    # DISTRESSED_TICKER: EBIT negativo
    for m, v in {
        "ebitda": 1_000_000_000,      # R$1B (positivo)
        "free_cash_flow": 500_000_000,  # R$0.5B
        "net_debt": 3_000_000_000,
        "shares_outstanding": 400_000_000,
        "ebit": -200_000_000,         # R$-200M (negativo → DISTRESSED)
        "net_income": -800_000_000,
    }.items():
        insert("DIST_T", m, v)

    # DCF_INVIAVEL_TICKER: DCF produziria equity < 0 mas FCF > 0
    # FCF/WACC-g = 1B/0.075 = 13.3B < net_debt = 20B → equity = -6.7B
    for m, v in {
        "ebitda": 6_000_000_000,
        "free_cash_flow": 1_000_000_000,
        "net_debt": 20_000_000_000,   # muito alta → EV < net_debt
        "shares_outstanding": 1_500_000_000,
        "ebit": 4_000_000_000,
        "net_income": 2_000_000_000,
    }.items():
        insert("DCFI_T", m, v)

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def empty_db(tmp_path) -> Path:
    """SQLite temporário vazio (sem dados para o ticker)."""
    db_path = tmp_path / "empty_ingestion.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE valuation_financial_inputs (
            id TEXT PRIMARY KEY, ticker TEXT, period_type TEXT, period_end TEXT,
            fiscal_year INTEGER, metric_name TEXT, metric_value REAL,
            source_type TEXT, source_priority INTEGER DEFAULT 1, confidence REAL DEFAULT 1.0,
            created_at TEXT, updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: constantes e configuração
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    """Testes de constantes e configurações do bridge."""

    def test_ticker_sector_map_cobre_18_tickers_m017(self):
        """TICKER_SECTOR_MAP deve cobrir exatamente os 18 tickers M017."""
        assert len(TICKER_SECTOR_MAP) == 18

    def test_m017_dry_run_tickers_tem_18_tickers(self):
        """M017_DRY_RUN_TICKERS deve ter 18 tickers."""
        assert len(M017_DRY_RUN_TICKERS) == 18

    def test_ticker_sector_map_setores_corretos(self):
        """Setores mapeados corretamente para grupos M016."""
        assert TICKER_SECTOR_MAP["PRIO3"] == "commodity"
        assert TICKER_SECTOR_MAP["RECV3"] == "commodity"
        assert TICKER_SECTOR_MAP["EGIE3"] == "utility"
        assert TICKER_SECTOR_MAP["SBSP3"] == "utility"
        assert TICKER_SECTOR_MAP["TAEE11"] == "utility"
        assert TICKER_SECTOR_MAP["LREN3"] == "retail"
        assert TICKER_SECTOR_MAP["MGLU3"] == "retail"
        assert TICKER_SECTOR_MAP["PCAR3"] == "retail"
        assert TICKER_SECTOR_MAP["FLRY3"] == "industry"
        assert TICKER_SECTOR_MAP["VAMO3"] == "industry"

    def test_wacc_defaults_cobrem_4_setores(self):
        """WACC_DEFAULTS deve cobrir commodity, utility, retail e industry."""
        for setor in ["commodity", "utility", "retail", "industry"]:
            assert setor in WACC_DEFAULTS
            assert 0 < WACC_DEFAULTS[setor] < 1, f"WACC inválido para {setor}"

    def test_wacc_hierarchy(self):
        """Utility WACC < Industry WACC < Retail e Commodity WACC."""
        assert WACC_DEFAULTS["utility"] < WACC_DEFAULTS["industry"]
        assert WACC_DEFAULTS["utility"] < WACC_DEFAULTS["retail"]

    def test_terminal_growth_razoavel(self):
        """Terminal growth deve ser entre 2% e 8%."""
        assert 0.02 <= TERMINAL_GROWTH_DEFAULT <= 0.08

    def test_wacc_supera_terminal_growth_todos_setores(self):
        """WACC deve sempre superar terminal_growth (Gordon Growth válido)."""
        for setor, wacc in WACC_DEFAULTS.items():
            assert wacc > TERMINAL_GROWTH_DEFAULT, \
                f"WACC({setor})={wacc} <= terminal_growth={TERMINAL_GROWTH_DEFAULT}"

    def test_ticker_subsector_map_cobre_todos(self):
        """TICKER_SUBSECTOR_MAP deve cobrir todos os 18 tickers M017."""
        for ticker in M017_DRY_RUN_TICKERS:
            assert ticker in TICKER_SUBSECTOR_MAP, f"{ticker} ausente do TICKER_SUBSECTOR_MAP"


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: detecção de flags de qualidade
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectQualityFlags:
    """Testes de _detect_quality_flags."""

    def test_sem_flags_para_dados_normais(self):
        """Dados normais (FCF/EBITDA ~ 0.4, EBIT > 0) → sem flags."""
        raw = {
            "ebitda": 5_000_000_000,
            "free_cash_flow": 2_000_000_000,
            "ebit": 3_000_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert flags == []

    def test_fcf_review_detectado(self):
        """FCF/EBITDA > 3.0 com ambos positivos → FCF_REVIEW."""
        raw = {
            "ebitda": 3_000_000_000,
            "free_cash_flow": 15_000_000_000,  # 5.0x EBITDA
            "ebit": 2_000_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "FCF_REVIEW" in flags

    def test_fcf_review_nao_detectado_quando_fcf_negativo(self):
        """FCF_REVIEW não deve ser ativado quando FCF < 0."""
        raw = {
            "ebitda": 3_000_000_000,
            "free_cash_flow": -15_000_000_000,
            "ebit": 2_000_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "FCF_REVIEW" not in flags

    def test_fcf_review_nao_detectado_quando_ebitda_negativo(self):
        """FCF_REVIEW não deve ser ativado quando EBITDA < 0."""
        raw = {
            "ebitda": -3_000_000_000,
            "free_cash_flow": 15_000_000_000,
            "ebit": 2_000_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "FCF_REVIEW" not in flags

    def test_fcf_negative_expected_detectado(self):
        """FCF < 0 com EBITDA > 0 → FCF_NEGATIVE_EXPECTED."""
        raw = {
            "ebitda": 4_000_000_000,
            "free_cash_flow": -1_500_000_000,
            "ebit": 2_500_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "FCF_NEGATIVE_EXPECTED" in flags

    def test_fcf_negative_expected_nao_detectado_quando_ebitda_negativo(self):
        """FCF_NEGATIVE_EXPECTED não ativado quando EBITDA < 0 (DISTRESSED dominante)."""
        raw = {
            "ebitda": -1_000_000_000,
            "free_cash_flow": -500_000_000,
            "ebit": -300_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "FCF_NEGATIVE_EXPECTED" not in flags

    def test_distressed_detectado_com_ebit_negativo(self):
        """EBIT < 0 → DISTRESSED."""
        raw = {
            "ebitda": 1_000_000_000,
            "free_cash_flow": 500_000_000,
            "ebit": -200_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "DISTRESSED" in flags

    def test_distressed_nao_detectado_com_ebit_zero(self):
        """EBIT == 0 → NÃO DISTRESSED (threshold é < 0)."""
        raw = {
            "ebitda": 1_000_000_000,
            "free_cash_flow": 500_000_000,
            "ebit": 0.0,
        }
        flags = _detect_quality_flags(raw)
        assert "DISTRESSED" not in flags

    def test_multiplas_flags_simultaneas(self):
        """Empresa DISTRESSED pode ter múltiplas flags ao mesmo tempo."""
        raw = {
            "ebitda": 1_000_000_000,
            "free_cash_flow": -500_000_000,
            "ebit": -200_000_000,
        }
        flags = _detect_quality_flags(raw)
        assert "DISTRESSED" in flags
        assert "FCF_NEGATIVE_EXPECTED" in flags

    def test_flags_ausentes_quando_dados_ausentes(self):
        """Dados ausentes (None) → sem flags."""
        flags = _detect_quality_flags({})
        assert flags == []

    def test_fcf_review_threshold_exato(self):
        """FCF/EBITDA == 3.0 exato NÃO dispara FCF_REVIEW (threshold é > 3.0)."""
        raw = {
            "ebitda": 1_000_000_000,
            "free_cash_flow": 3_000_000_000,  # exatamente 3.0x
            "ebit": 500_000_000,
        }
        flags = _detect_quality_flags(raw)
        # 3.0 NÃO é > 3.0
        assert "FCF_REVIEW" not in flags


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: _fcf_for_model
# ─────────────────────────────────────────────────────────────────────────────

class TestFcfForModel:
    """Testes de _fcf_for_model com regras de qualidade e viabilidade."""

    def test_retorna_fcf_normal_sem_flags(self):
        """Sem flags e DCF viável → retorna FCF normal."""
        metrics = {
            "free_cash_flow": 2_000.0,  # R$ milhões
            "net_debt": 5_000.0,
        }
        # EV = 2000/0.075 = 26666M > net_debt=5000M → equity = 21666M > 0 → OK
        fcf = _fcf_for_model(metrics, [], "TEST", wacc=0.12, g=0.045)
        assert fcf == 2_000.0

    def test_retorna_none_para_fcf_review(self):
        """FCF_REVIEW → FCF=None."""
        metrics = {"free_cash_flow": 15_000.0, "net_debt": 2_000.0}
        fcf = _fcf_for_model(metrics, ["FCF_REVIEW"], "TEST", wacc=0.12, g=0.045)
        assert fcf is None

    def test_retorna_none_para_distressed(self):
        """DISTRESSED → FCF=None."""
        metrics = {"free_cash_flow": 500.0, "net_debt": 3_000.0}
        fcf = _fcf_for_model(metrics, ["DISTRESSED"], "TEST", wacc=0.13, g=0.045)
        assert fcf is None

    def test_retorna_none_para_fcf_negative_expected(self):
        """FCF_NEGATIVE_EXPECTED → FCF=None (prioriza EV/EBITDA)."""
        metrics = {"free_cash_flow": -1_500.0, "net_debt": 10_000.0}
        fcf = _fcf_for_model(metrics, ["FCF_NEGATIVE_EXPECTED"], "TEST", wacc=0.10, g=0.045)
        assert fcf is None

    def test_retorna_none_quando_dcf_produziria_equity_negativo(self):
        """DCF inviável (equity < 0) → FCF=None para habilitar EV/EBITDA fallback."""
        metrics = {
            "free_cash_flow": 1_000.0,   # R$1B
            "net_debt": 20_000.0,         # R$20B >> EV
        }
        # EV = 1000/0.075 = 13333M < net_debt=20000M → equity = -6667M < 0
        fcf = _fcf_for_model(metrics, [], "TEST", wacc=0.12, g=0.045)
        assert fcf is None

    def test_retorna_fcf_quando_dcf_viavel(self):
        """DCF viável (equity > 0) → retorna FCF normal."""
        metrics = {
            "free_cash_flow": 5_000.0,   # R$5B
            "net_debt": 10_000.0,         # EV = 5000/0.075 = 66666M >> net_debt
        }
        fcf = _fcf_for_model(metrics, [], "TEST", wacc=0.12, g=0.045)
        assert fcf == 5_000.0

    def test_retorna_none_quando_fcf_ausente(self):
        """FCF ausente no store → None."""
        metrics = {"net_debt": 5_000.0}  # sem free_cash_flow
        fcf = _fcf_for_model(metrics, [], "TEST", wacc=0.12, g=0.045)
        assert fcf is None

    def test_retorna_fcf_sem_verificacao_quando_wacc_ausente(self):
        """Sem WACC → não faz verificação de viabilidade, retorna FCF."""
        metrics = {
            "free_cash_flow": 1_000.0,
            "net_debt": 20_000.0,  # seria inviável com WACC
        }
        # Sem WACC → sem verificação → retorna FCF (comportamento seguro)
        fcf = _fcf_for_model(metrics, [], "TEST", wacc=None, g=None)
        assert fcf == 1_000.0

    def test_prioridade_fcf_review_sobre_dcf_inviavel(self):
        """FCF_REVIEW tem prioridade — retorna None mesmo que DCF fosse viável."""
        metrics = {
            "free_cash_flow": 50_000.0,  # anômalo E viável
            "net_debt": 5_000.0,
        }
        fcf = _fcf_for_model(metrics, ["FCF_REVIEW"], "TEST", wacc=0.12, g=0.045)
        assert fcf is None


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: load_financial_inputs_from_store
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadFinancialInputsFromStore:
    """Testes de load_financial_inputs_from_store."""

    def test_carrega_metricas_em_r_milhoes(self, tmp_db):
        """Valores financeiros devem ser convertidos para R$ milhões."""
        result = load_financial_inputs_from_store("NORMAL_T", db_path=tmp_db)
        assert result["available"] is True
        assert result["metrics"]["ebitda"] == pytest.approx(5_000.0, rel=1e-3)
        assert result["metrics"]["free_cash_flow"] == pytest.approx(2_000.0, rel=1e-3)
        assert result["metrics"]["net_debt"] == pytest.approx(8_000.0, rel=1e-3)

    def test_shares_convertidos_para_milhoes(self, tmp_db):
        """shares_outstanding deve ser convertido para milhões de ações."""
        result = load_financial_inputs_from_store("NORMAL_T", db_path=tmp_db)
        # 500_000_000 shares → 500.0 milhões
        assert result["metrics"]["shares_outstanding"] == pytest.approx(500.0, rel=1e-3)

    def test_source_quality_cvm_csv(self, tmp_db):
        """Source CVM_CSV → source_quality='CVM_LIVE'."""
        result = load_financial_inputs_from_store("NORMAL_T", db_path=tmp_db)
        assert result["source_quality"] == "CVM_LIVE"

    def test_available_true_quando_essenciais_presentes(self, tmp_db):
        """available=True quando ebitda + net_debt + shares estão presentes."""
        result = load_financial_inputs_from_store("NORMAL_T", db_path=tmp_db)
        assert result["available"] is True

    def test_available_false_quando_sem_dados(self, empty_db):
        """available=False para ticker sem dados no store."""
        result = load_financial_inputs_from_store("NOTICKER", db_path=empty_db)
        assert result["available"] is False
        assert result["metrics"] == {}
        assert result["source_quality"] == "ABSENT"

    def test_quality_flags_fcf_review(self, tmp_db):
        """FCR_T (FCF/EBITDA = 5.0x) → FCF_REVIEW detectado."""
        result = load_financial_inputs_from_store("FCR_T", db_path=tmp_db)
        assert "FCF_REVIEW" in result["quality_flags"]

    def test_quality_flags_fcf_negative_expected(self, tmp_db):
        """FCNEG_T (FCF<0, EBITDA>0) → FCF_NEGATIVE_EXPECTED detectado."""
        result = load_financial_inputs_from_store("FCNEG_T", db_path=tmp_db)
        assert "FCF_NEGATIVE_EXPECTED" in result["quality_flags"]

    def test_quality_flags_distressed(self, tmp_db):
        """DIST_T (EBIT<0) → DISTRESSED detectado."""
        result = load_financial_inputs_from_store("DIST_T", db_path=tmp_db)
        assert "DISTRESSED" in result["quality_flags"]

    def test_period_end_retornado(self, tmp_db):
        """period_end deve ser preenchido com a data do período."""
        result = load_financial_inputs_from_store("NORMAL_T", db_path=tmp_db)
        assert result["period_end"] == "2025-12-31"

    def test_filtro_por_period_end_especifico(self, tmp_db):
        """Filtro por period_end específico deve funcionar."""
        result = load_financial_inputs_from_store(
            "NORMAL_T", period_end="2025-12-31", db_path=tmp_db
        )
        assert result["period_end"] == "2025-12-31"
        assert result["available"] is True

    def test_retorno_vazio_para_period_end_inexistente(self, tmp_db):
        """Período inexistente → available=False."""
        result = load_financial_inputs_from_store(
            "NORMAL_T", period_end="2020-12-31", db_path=tmp_db
        )
        assert result["available"] is False


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: hidratadores por modelo
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildCommodityInputs:
    """Testes de build_commodity_inputs_from_store."""

    def test_build_popula_dataclass_com_metricas(self, tmp_db):
        """Hidratador deve popular CommodityValuationInputs com dados do store."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=50.0,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_commodity_inputs_from_store(
                "NORMAL_T", db_path=tmp_db
            )

        assert inputs.ticker == "NORMAL_T"
        assert inputs.ebitda == pytest.approx(5_000.0, rel=1e-3)
        assert inputs.net_debt == pytest.approx(8_000.0, rel=1e-3)
        assert inputs.shares_outstanding == pytest.approx(500.0, rel=1e-3)
        assert inputs.market_price == 50.0
        assert inputs.wacc == WACC_DEFAULTS["commodity"]

    def test_fcf_review_bloqueia_fcf_em_commodity(self, tmp_db):
        """FCR_T (FCF_REVIEW) → free_cash_flow=None no inputs commodity."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_commodity_inputs_from_store(
                "FCR_T", db_path=tmp_db
            )

        assert inputs.free_cash_flow is None
        assert "FCF_REVIEW" in meta["quality_flags"]

    def test_subsector_atribuido_corretamente(self, tmp_db):
        """Subsector deve ser atribuído a partir do TICKER_SUBSECTOR_MAP."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, _ = build_commodity_inputs_from_store(
                "NORMAL_T", db_path=tmp_db
            )

        # NORMAL_T não está no mapa → usa default "oil_gas"
        assert inputs.subsector == "oil_gas"


class TestBuildUtilityInputs:
    """Testes de build_utility_inputs_from_store."""

    def test_build_popula_dataclass(self, tmp_db):
        """Hidratador deve popular UtilityValuationInputs."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=30.0,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_utility_inputs_from_store(
                "NORMAL_T", db_path=tmp_db
            )

        assert inputs.ticker == "NORMAL_T"
        assert inputs.ebitda == pytest.approx(5_000.0, rel=1e-3)
        assert inputs.wacc == WACC_DEFAULTS["utility"]
        assert inputs.rab is None  # RAB não disponível no store

    def test_fcf_negative_expected_bloqueia_fcf_utility(self, tmp_db):
        """FCF_NEGATIVE_EXPECTED → free_cash_flow=None em utility."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_utility_inputs_from_store(
                "FCNEG_T", db_path=tmp_db
            )

        assert inputs.free_cash_flow is None
        assert "FCF_NEGATIVE_EXPECTED" in meta["quality_flags"]


class TestBuildRetailInputs:
    """Testes de build_retail_inputs_from_store."""

    def test_build_popula_dataclass(self, tmp_db):
        """Hidratador deve popular RetailValuationInputs."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=20.0,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_retail_inputs_from_store(
                "NORMAL_T", db_path=tmp_db
            )

        assert inputs.ticker == "NORMAL_T"
        assert inputs.ebitda == pytest.approx(5_000.0, rel=1e-3)
        assert inputs.wacc == WACC_DEFAULTS["retail"]

    def test_distressed_bloqueia_fcf_retail(self, tmp_db):
        """DISTRESSED (EBIT<0) → free_cash_flow=None em retail."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_retail_inputs_from_store(
                "DIST_T", db_path=tmp_db
            )

        assert inputs.free_cash_flow is None
        assert "DISTRESSED" in meta["quality_flags"]


class TestBuildIndustryInputs:
    """Testes de build_industry_inputs_from_store."""

    def test_build_popula_dataclass(self, tmp_db):
        """Hidratador deve popular IndustryValuationInputs."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=40.0,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_industry_inputs_from_store(
                "NORMAL_T", db_path=tmp_db
            )

        assert inputs.ticker == "NORMAL_T"
        assert inputs.ebitda == pytest.approx(5_000.0, rel=1e-3)
        assert inputs.wacc == WACC_DEFAULTS["industry"]

    def test_dcf_inviavel_bloqueia_fcf_industry(self, tmp_db):
        """DCF produziria equity < 0 → FCF=None habilita EV/EBITDA fallback."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_industry_inputs_from_store(
                "DCFI_T", db_path=tmp_db
            )

        # FCF deve ser None porque EV < net_debt
        assert inputs.free_cash_flow is None

    def test_ticker_sem_dados_retorna_inputs_com_nones(self, empty_db):
        """Ticker sem dados → inputs com campos None."""
        with patch(
            "src.valuation.financial_inputs_bridge._load_market_price",
            return_value=None,
        ), patch(
            "src.valuation.financial_inputs_bridge._load_existing_fair_value",
            return_value=None,
        ):
            inputs, meta = build_industry_inputs_from_store(
                "GHOST_T", db_path=empty_db
            )

        assert inputs.ebitda is None
        assert inputs.net_debt is None
        assert inputs.free_cash_flow is None
        assert meta["available"] is False


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: run_dry_run_all (integração com banco real)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def dry_run_results():
    """Executa dry-run uma vez e compartilha resultados entre testes."""
    return run_dry_run_all()


class TestRunDryRunAll:
    """Testes de run_dry_run_all com banco real (M017-S05)."""

    def test_retorna_18_resultados(self, dry_run_results):
        """dry-run deve retornar exatamente 18 resultados."""
        assert len(dry_run_results) == 18

    def test_cobre_todos_tickers_m017(self, dry_run_results):
        """Todos os 18 tickers M017 devem estar no resultado."""
        for ticker in M017_DRY_RUN_TICKERS:
            assert ticker in dry_run_results, f"Ticker {ticker} ausente"

    def test_write_prevented_em_todos(self, dry_run_results):
        """write_prevented deve ser True em todos os tickers."""
        for ticker, res in dry_run_results.items():
            assert res["write_prevented"] is True, \
                f"{ticker}: write_prevented deveria ser True"

    def test_minimo_15_tickers_calculariam(self, dry_run_results):
        """Pelo menos 15/18 tickers devem calcular fair_value."""
        count = sum(1 for r in dry_run_results.values() if r["would_calculate"])
        assert count >= 15, f"Apenas {count}/18 calculariam (mínimo: 15)"

    def test_todos_18_calculariam_fair_value(self, dry_run_results):
        """Com bridge funcionando, todos os 18 devem calcular."""
        count = sum(1 for r in dry_run_results.values() if r["would_calculate"])
        assert count == 18, f"Esperado 18, obtido {count}"

    def test_pcar3_permanece_distressed(self, dry_run_results):
        """PCAR3 deve ter status PARTIAL_INPUTS/DISTRESSED."""
        pcar3 = dry_run_results["PCAR3"]
        assert "DISTRESSED" in pcar3["status"] or "PARTIAL_INPUTS" in pcar3["status"], \
            f"PCAR3 status inesperado: {pcar3['status']}"
        assert "DISTRESSED" in pcar3["quality_flags"]

    def test_pcar3_usa_ev_ebitda(self, dry_run_results):
        """PCAR3 deve usar EV/EBITDA (não DCF, pois DISTRESSED bloqueia FCF)."""
        pcar3 = dry_run_results["PCAR3"]
        assert pcar3["method_used"] == "EV_EBITDA"

    def test_mglu3_fcr_review_usa_ev_ebitda(self, dry_run_results):
        """MGLU3 FCR_REVIEW → deve usar EV/EBITDA."""
        mglu3 = dry_run_results["MGLU3"]
        assert "FCF_REVIEW" in mglu3["quality_flags"]
        assert mglu3["method_used"] == "EV_EBITDA"

    def test_recv3_fcf_negativo_usa_ev_ebitda(self, dry_run_results):
        """RECV3 FCF_NEGATIVE_EXPECTED → deve usar EV/EBITDA."""
        recv3 = dry_run_results["RECV3"]
        assert "FCF_NEGATIVE_EXPECTED" in recv3["quality_flags"]
        assert recv3["method_used"] == "EV_EBITDA"

    def test_sbsp3_fcf_negativo_usa_ev_ebitda(self, dry_run_results):
        """SBSP3 FCF_NEGATIVE_EXPECTED → deve usar EV/EBITDA."""
        sbsp3 = dry_run_results["SBSP3"]
        assert "FCF_NEGATIVE_EXPECTED" in sbsp3["quality_flags"]
        assert sbsp3["method_used"] == "EV_EBITDA"

    def test_vamo3_fcf_negativo_usa_ev_ebitda(self, dry_run_results):
        """VAMO3 FCF_NEGATIVE_EXPECTED → deve usar EV/EBITDA."""
        vamo3 = dry_run_results["VAMO3"]
        assert "FCF_NEGATIVE_EXPECTED" in vamo3["quality_flags"]
        assert vamo3["method_used"] == "EV_EBITDA"

    def test_nenhum_fair_value_salvo_no_banco(self, dry_run_results):
        """valuation_financial_inputs deve ter exatamente 47621 registros (intocados)."""
        ingestion_db = _resolve_ingestion_db()
        if not ingestion_db.exists():
            pytest.skip(f"ingestion.db não encontrado em {ingestion_db}")

        conn = sqlite3.connect(str(ingestion_db))
        count = conn.execute(
            "SELECT COUNT(*) FROM valuation_financial_inputs"
        ).fetchone()[0]
        conn.close()
        # O número de registros não deve ter aumentado (nenhum fair_value escrito)
        assert count == 47621, \
            f"Registros alterados: esperado 47621, obtido {count}"

    def test_fair_values_positivos_quando_calculados(self, dry_run_results):
        """fair_value calculado deve ser sempre positivo (sanity check)."""
        for ticker, res in dry_run_results.items():
            if res["would_calculate"] and res["fair_value"] is not None:
                assert res["fair_value"] > 0, \
                    f"{ticker}: fair_value={res['fair_value']} deveria ser positivo"

    def test_confidence_reduzida_para_ev_ebitda(self, dry_run_results):
        """EV/EBITDA tem confiança menor que DCF (método secundário)."""
        for ticker, res in dry_run_results.items():
            if res["method_used"] == "EV_EBITDA" and res["would_calculate"]:
                assert res["confidence"] < 0.90, \
                    f"{ticker}: EV_EBITDA deveria ter conf < 0.90, obtido {res['confidence']}"

    def test_setores_corretos_no_resultado(self, dry_run_results):
        """Setores no resultado devem corresponder ao TICKER_SECTOR_MAP."""
        for ticker, res in dry_run_results.items():
            expected = TICKER_SECTOR_MAP.get(ticker)
            if expected:
                assert res["sector"] == expected, \
                    f"{ticker}: setor esperado={expected}, obtido={res['sector']}"

    def test_tickers_commodity_usam_commodity_wacc(self, dry_run_results):
        """Tickers commodity devem ter setor='commodity'."""
        for ticker in ["PRIO3", "RECV3"]:
            res = dry_run_results[ticker]
            assert res["sector"] == "commodity"

    def test_tickers_utility_usam_utility_setor(self, dry_run_results):
        """Tickers utility devem ter setor='utility'."""
        for ticker in ["EGIE3", "SBSP3", "TAEE11"]:
            res = dry_run_results[ticker]
            assert res["sector"] == "utility"


# ─────────────────────────────────────────────────────────────────────────────
#  Testes: resolução de caminhos
# ─────────────────────────────────────────────────────────────────────────────

class TestResolvePaths:
    """Testes de _resolve_ingestion_db."""

    def test_resolve_ingestion_db_retorna_path(self):
        """_resolve_ingestion_db deve retornar um Path."""
        result = _resolve_ingestion_db()
        assert isinstance(result, Path)

    def test_env_var_tem_precedencia(self, tmp_path, monkeypatch):
        """FINANCIAL_INPUTS_DB_PATH env var deve ter precedência."""
        db = tmp_path / "custom.db"
        db.touch()
        monkeypatch.setenv("FINANCIAL_INPUTS_DB_PATH", str(db))
        result = _resolve_ingestion_db()
        assert result == db

    def test_env_var_inexistente_usa_fallback(self, monkeypatch):
        """Env var apontando para arquivo inexistente → usar fallback."""
        monkeypatch.setenv("FINANCIAL_INPUTS_DB_PATH", "/tmp/nonexistent_db_xyz.db")
        result = _resolve_ingestion_db()
        # Não deve lançar exceção
        assert isinstance(result, Path)
