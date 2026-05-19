"""
test_dashboard_command_center.py
---------------------------------
Testes para o Command Center e funções auxiliares do dashboard — Phase 49.

Cobre:
  - get_data_health() retorna dict com estrutura esperada
  - get_assets_count() retorna dict com chaves 'total' e 'with_hash'
  - get_command_last_runs() retorna dict com chaves de comandos principais
  - get_weekly_reports_list() retorna DataFrame (vazio se diretório ausente)
  - get_paper_trading_summary() retorna DataFrame vazio se tabela ausente
  - get_technical_summary() retorna DataFrame vazio se tabela ausente
  - get_risk_summary() retorna DataFrame vazio se tabela ausente
  - get_options_summary() retorna DataFrame vazio se tabela ausente
  - get_scanner_summary() retorna DataFrame (opportunity_signals se existente)
  - get_integrated_intelligence() retorna DataFrame de thesis se existente
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def patched_db(monkeypatch, tmp_path):
    """Banco SQLite temporário com tabelas básicas para testar o data layer."""
    db_path = tmp_path / "test_dash.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS thesis_versions (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            version_num INTEGER,
            generated_at TEXT,
            input_hash TEXT,
            positioning TEXT,
            confidence TEXT,
            fair_value_brl REAL
        );
        CREATE VIEW IF NOT EXISTS thesis_latest AS
            SELECT * FROM thesis_versions
            WHERE version_num = (
                SELECT MAX(version_num)
                FROM thesis_versions tv2
                WHERE tv2.ticker = thesis_versions.ticker
            );
        CREATE TABLE IF NOT EXISTS opportunity_signals (
            id TEXT PRIMARY KEY,
            ticker TEXT,
            signal_type TEXT,
            conviction_score INTEGER,
            computed_date TEXT
        );
        CREATE TABLE IF NOT EXISTS weekly_pipeline_runs (
            id TEXT PRIMARY KEY,
            status TEXT,
            started_at TEXT,
            finished_at TEXT,
            steps_total INTEGER DEFAULT 0,
            steps_success INTEGER DEFAULT 0,
            steps_warning INTEGER DEFAULT 0,
            steps_failed INTEGER DEFAULT 0,
            report_id TEXT,
            tickers TEXT DEFAULT '[]'
        );
    """)
    # Seed thesis
    conn.execute(
        "INSERT INTO thesis_versions VALUES (?,?,?,?,?,?,?,?)",
        ("id1", "PETR4", 1, "2026-05-18", "hash1", "COMPRAR", "ALTA", 40.0),
    )
    conn.execute(
        "INSERT INTO thesis_versions VALUES (?,?,?,?,?,?,?,?)",
        ("id2", "VALE3", 1, "2026-05-18", "hash2", "NEUTRO", "MEDIA", 55.0),
    )
    conn.execute(
        "INSERT INTO opportunity_signals VALUES (?,?,?,?,?)",
        ("sig1", "PETR4", "DCF_DIVERGENCE", 85, "2026-05-18"),
    )
    conn.execute(
        "INSERT INTO weekly_pipeline_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("run1", "SUCCESS", "2026-05-18 08:00", "2026-05-18 09:00", 10, 9, 1, 0, "report-001", '["PETR4","VALE3"]'),
    )
    conn.commit()
    conn.close()

    import src.reports.quant_dashboard_data as m
    monkeypatch.setattr(m, "_DB_PATH", db_path)
    return db_path


@pytest.fixture
def empty_db(monkeypatch, tmp_path):
    """Banco SQLite temporário completamente vazio."""
    db_path = tmp_path / "empty.db"
    db_path.touch()
    import src.reports.quant_dashboard_data as m
    monkeypatch.setattr(m, "_DB_PATH", db_path)
    return db_path


# ---------------------------------------------------------------------------
# get_data_health
# ---------------------------------------------------------------------------

class TestGetDataHealth:
    def test_returns_dict(self, patched_db):
        from src.reports.quant_dashboard_data import get_data_health
        get_data_health.clear()
        health = get_data_health()
        assert isinstance(health, dict)

    def test_known_table_has_exists_true(self, patched_db):
        from src.reports.quant_dashboard_data import get_data_health
        get_data_health.clear()
        health = get_data_health()
        assert "thesis_versions" in health
        assert health["thesis_versions"]["exists"] is True

    def test_absent_table_has_exists_false(self, patched_db):
        from src.reports.quant_dashboard_data import get_data_health
        get_data_health.clear()
        health = get_data_health()
        assert "financial_dcf" in health
        assert health["financial_dcf"]["exists"] is False
        assert health["financial_dcf"]["status"] == "NOT_RUN"

    def test_table_with_data_has_ok_status(self, patched_db):
        from src.reports.quant_dashboard_data import get_data_health
        get_data_health.clear()
        health = get_data_health()
        assert health["thesis_versions"]["rows"] >= 2
        assert health["thesis_versions"]["status"] == "OK"

    def test_empty_db_all_not_run(self, empty_db):
        from src.reports.quant_dashboard_data import get_data_health
        get_data_health.clear()
        health = get_data_health()
        for v in health.values():
            assert v["status"] in ("NOT_RUN", "SEM_DADOS")


# ---------------------------------------------------------------------------
# get_assets_count
# ---------------------------------------------------------------------------

class TestGetAssetsCount:
    def test_returns_dict_with_keys(self, patched_db):
        from src.reports.quant_dashboard_data import get_assets_count
        get_assets_count.clear()
        result = get_assets_count()
        assert "total" in result
        assert "with_hash" in result

    def test_counts_correct(self, patched_db):
        from src.reports.quant_dashboard_data import get_assets_count
        get_assets_count.clear()
        result = get_assets_count()
        assert result["total"] == 2  # PETR4, VALE3
        assert result["with_hash"] == 2

    def test_empty_db_returns_zeros(self, empty_db):
        from src.reports.quant_dashboard_data import get_assets_count
        get_assets_count.clear()
        result = get_assets_count()
        assert result["total"] == 0
        assert result["with_hash"] == 0


# ---------------------------------------------------------------------------
# get_command_last_runs
# ---------------------------------------------------------------------------

class TestGetCommandLastRuns:
    def test_returns_dict(self, patched_db, monkeypatch):
        from src.reports.quant_dashboard_data import get_command_last_runs

        # Patch editorial to avoid DB calls
        monkeypatch.setattr(
            "src.reports.quant_dashboard_data.get_latest_editorial_review",
            lambda *a, **kw: None,
        )
        result = get_command_last_runs()
        assert isinstance(result, dict)
        assert "weekly_pipeline" in result
        assert "editorial_review" in result

    def test_no_pipeline_returns_not_run(self, empty_db, monkeypatch):
        from src.reports.quant_dashboard_data import get_command_last_runs

        monkeypatch.setattr(
            "src.reports.quant_dashboard_data.get_latest_pipeline_run",
            lambda *a, **kw: None,
        )
        monkeypatch.setattr(
            "src.reports.quant_dashboard_data.get_latest_editorial_review",
            lambda *a, **kw: None,
        )
        get_command_last_runs.clear()
        result = get_command_last_runs()
        assert result["weekly_pipeline"] == "NOT_RUN"
        assert result["editorial_review"] == "NOT_RUN"


# ---------------------------------------------------------------------------
# get_weekly_reports_list
# ---------------------------------------------------------------------------

class TestGetWeeklyReportsList:
    def test_returns_dataframe(self, monkeypatch, tmp_path):
        from src.reports.quant_dashboard_data import get_weekly_reports_list
        import src.reports.quant_dashboard_data as m

        # Create fake reports
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "radar_macro_2026-05-11.md").write_text("# Report")
        (reports_dir / "radar_macro_2026-05-18.md").write_text("# Report")

        monkeypatch.setattr(m, "REPORTS_DIR", reports_dir)
        get_weekly_reports_list.clear()

        result = get_weekly_reports_list()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "arquivo" in result.columns

    def test_empty_dir_returns_empty_df(self, monkeypatch, tmp_path):
        from src.reports.quant_dashboard_data import get_weekly_reports_list
        import src.reports.quant_dashboard_data as m

        empty_dir = tmp_path / "empty_reports"
        empty_dir.mkdir()
        monkeypatch.setattr(m, "REPORTS_DIR", empty_dir)
        get_weekly_reports_list.clear()

        result = get_weekly_reports_list()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_nonexistent_dir_returns_empty_df(self, monkeypatch, tmp_path):
        from src.reports.quant_dashboard_data import get_weekly_reports_list
        import src.reports.quant_dashboard_data as m

        monkeypatch.setattr(m, "REPORTS_DIR", tmp_path / "does_not_exist")
        get_weekly_reports_list.clear()

        result = get_weekly_reports_list()
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# Tabelas ausentes → DataFrame vazio
# ---------------------------------------------------------------------------

class TestMissingTableFallbacks:
    def test_paper_trading_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_paper_trading_summary
        get_paper_trading_summary.clear()
        result = get_paper_trading_summary()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_technical_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_technical_summary
        get_technical_summary.clear()
        result = get_technical_summary()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_risk_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_risk_summary
        get_risk_summary.clear()
        result = get_risk_summary()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_options_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_options_summary
        get_options_summary.clear()
        result = get_options_summary()
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# get_scanner_summary (opportunity_signals)
# ---------------------------------------------------------------------------

class TestGetScannerSummary:
    def test_returns_dataframe_with_data(self, patched_db):
        from src.reports.quant_dashboard_data import get_scanner_summary
        get_scanner_summary.clear()
        result = get_scanner_summary()
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "ticker" in result.columns

    def test_returns_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_scanner_summary
        get_scanner_summary.clear()
        result = get_scanner_summary()
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# get_integrated_intelligence (thesis_latest)
# ---------------------------------------------------------------------------

class TestGetIntegratedIntelligence:
    def test_returns_dataframe_with_tickers(self, patched_db):
        from src.reports.quant_dashboard_data import get_integrated_intelligence
        get_integrated_intelligence.clear()
        result = get_integrated_intelligence()
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "ticker" in result.columns
        tickers = list(result["ticker"])
        assert "PETR4" in tickers

    def test_returns_empty_if_no_table(self, empty_db):
        from src.reports.quant_dashboard_data import get_integrated_intelligence
        get_integrated_intelligence.clear()
        result = get_integrated_intelligence()
        assert isinstance(result, pd.DataFrame)
        assert result.empty
