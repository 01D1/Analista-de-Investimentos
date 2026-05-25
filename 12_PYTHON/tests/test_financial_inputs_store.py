"""
test_financial_inputs_store.py
-------------------------------
Testes do schema canônico e store valuation_financial_inputs (M017-S01).

Cobre:
  T01 - ensure_financial_inputs_schema() cria a tabela
  T02 - ensure_financial_inputs_schema() é idempotente (2× chamada)
  T03 - upsert idempotente (write=True) — mesmo registro 2× → 1 linha
  T04 - upsert atualiza metric_value no conflito (ON CONFLICT DO UPDATE)
  T05 - leitura por ticker — get_financial_inputs()
  T06 - leitura com filtro period_end
  T07 - leitura com filtro period_type
  T08 - latest inputs — get_latest_financial_inputs() retorna período mais recente
  T09 - latest inputs prioriza source_priority menor (CVM > Excel) em empate de período
  T10 - unicidade lógica — duplicata na chave UNIQUE é absorvida (não lança erro)
  T11 - campos de proveniência obrigatórios — ValueError se ausentes
  T12 - write=False (dry-run) não persiste nenhuma linha
  T13 - list_financial_input_coverage() resume cobertura por ticker
  T14 - delete_financial_inputs_for_source() dry-run não remove linhas
  T15 - delete_financial_inputs_for_source() write=True remove linhas
  T16 - store NÃO toca asset_intelligence_snapshots (tabela inexistente permanece inexistente)
  T17 - store NÃO toca valuation_results (tabela inexistente permanece inexistente)
  T18 - ensure_financial_inputs_schema() não altera tabelas pré-existentes (cvm_statements intacta)
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture: banco em memória / tmp_path
# ---------------------------------------------------------------------------

BASE_RECORD: dict = {
    "ticker":           "ITUB4",
    "period_type":      "DFP",
    "period_end":       "2024-12-31",
    "fiscal_year":      2024,
    "metric_name":      "net_revenue",
    "metric_value":     100_000.0,
    "source_type":      "CVM_CSV",
    "source_priority":  1,
    "confidence":       0.95,
    "extraction_method": "structured",
    "source_path":      "/data/raw/cvm/2025/ITUB4_DFP_2025.csv",
    "account_code":     "3.01",
    "account_name":     "Receita de Intermediação Financeira",
    "statement_type":   "DRE",
    "currency":         "BRL",
    "unit":             "thousands",
}


def _init(db_path: Path) -> None:
    """Inicializa ingestion.db e garante schema de financial_inputs."""
    from src.ingestion.db import init_db
    from src.valuation.financial_inputs_store import ensure_financial_inputs_schema

    init_db(db_path)
    ensure_financial_inputs_schema(db_path)


# ---------------------------------------------------------------------------
# T01 — Criação da tabela
# ---------------------------------------------------------------------------

def test_T01_table_created(tmp_path):
    """ensure_financial_inputs_schema() cria valuation_financial_inputs."""
    db = tmp_path / "ingestion.db"
    _init(db)

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    assert "valuation_financial_inputs" in tables, (
        f"Tabela valuation_financial_inputs não encontrada. Tabelas: {tables}"
    )


def test_T01_columns_present(tmp_path):
    """valuation_financial_inputs tem todas as 21 colunas especificadas no schema."""
    db = tmp_path / "ingestion.db"
    _init(db)

    conn = sqlite3.connect(db)
    cols = {row[1] for row in conn.execute(
        "PRAGMA table_info(valuation_financial_inputs)"
    ).fetchall()}
    conn.close()

    expected = {
        "id", "ticker", "period_type", "period_end", "fiscal_year",
        "fiscal_quarter", "metric_name", "metric_value", "currency", "unit",
        "source_type", "source_priority", "source_path", "source_doc_id",
        "statement_type", "account_code", "account_name",
        "confidence", "extraction_method", "created_at", "updated_at",
    }
    missing = expected - cols
    assert not missing, f"Colunas ausentes: {missing}"


def test_T01_pk_is_text(tmp_path):
    """PRIMARY KEY deve ser TEXT (não INTEGER AUTOINCREMENT)."""
    db = tmp_path / "ingestion.db"
    _init(db)

    conn = sqlite3.connect(db)
    cols = conn.execute(
        "PRAGMA table_info(valuation_financial_inputs)"
    ).fetchall()
    conn.close()

    pk_cols = [c for c in cols if c[5] == 1]  # col 5 = pk flag
    assert len(pk_cols) == 1, "Deve haver exatamente 1 coluna PK"
    assert pk_cols[0][2].upper() == "TEXT", f"PK deve ser TEXT, encontrado: {pk_cols[0][2]}"


def test_T01_unique_index_exists(tmp_path):
    """idx_vfi_dedup UNIQUE index existe na tabela."""
    db = tmp_path / "ingestion.db"
    _init(db)

    conn = sqlite3.connect(db)
    indexes = {r[1] for r in conn.execute(
        "SELECT * FROM sqlite_master WHERE type='index'"
    ).fetchall()}
    conn.close()

    assert "idx_vfi_dedup" in indexes, f"idx_vfi_dedup não encontrado. Índices: {indexes}"


def test_T01_performance_indexes_exist(tmp_path):
    """Índices de performance idx_vfi_ticker, idx_vfi_ticker_period, idx_vfi_metric existem."""
    db = tmp_path / "ingestion.db"
    _init(db)

    conn = sqlite3.connect(db)
    indexes = {r[1] for r in conn.execute(
        "SELECT * FROM sqlite_master WHERE type='index'"
    ).fetchall()}
    conn.close()

    for idx in ("idx_vfi_ticker", "idx_vfi_ticker_period", "idx_vfi_metric"):
        assert idx in indexes, f"Índice {idx} não encontrado. Índices: {indexes}"


# ---------------------------------------------------------------------------
# T02 — Idempotência do schema
# ---------------------------------------------------------------------------

def test_T02_schema_idempotent(tmp_path):
    """ensure_financial_inputs_schema() chamado 3× não lança erro e não duplica tabela."""
    db = tmp_path / "ingestion.db"
    from src.ingestion.db import init_db
    from src.valuation.financial_inputs_store import ensure_financial_inputs_schema

    init_db(db)
    ensure_financial_inputs_schema(db)
    ensure_financial_inputs_schema(db)  # segunda chamada
    ensure_financial_inputs_schema(db)  # terceira chamada

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='valuation_financial_inputs'"
    ).fetchone()[0]
    conn.close()

    assert count == 1, f"Esperado 1 tabela, encontrado {count}"


# ---------------------------------------------------------------------------
# T03 — Upsert idempotente
# ---------------------------------------------------------------------------

def test_T03_upsert_idempotent(tmp_path):
    """upsert_financial_input() com write=True inserido 2× → exatamente 1 linha."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)
    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM valuation_financial_inputs WHERE ticker='ITUB4'"
    ).fetchone()[0]
    conn.close()

    assert count == 1, f"Esperado 1 linha (idempotente), encontrado {count}"


# ---------------------------------------------------------------------------
# T04 — Upsert atualiza metric_value no conflito
# ---------------------------------------------------------------------------

def test_T04_upsert_updates_on_conflict(tmp_path):
    """ON CONFLICT DO UPDATE atualiza metric_value — último write vence."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    updated = {**BASE_RECORD, "metric_value": 999_999.0}
    upsert_financial_input(updated, db_path=db, write=True)

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT metric_value FROM valuation_financial_inputs WHERE ticker='ITUB4'"
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == 999_999.0, f"metric_value deveria ser 999999.0, encontrado {row[0]}"


# ---------------------------------------------------------------------------
# T05 — Leitura por ticker
# ---------------------------------------------------------------------------

def test_T05_get_financial_inputs_by_ticker(tmp_path):
    """get_financial_inputs(ticker) retorna todos os registros do ticker."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    # Inserir 2 métricas para ITUB4
    r1 = {**BASE_RECORD, "metric_name": "ebitda", "metric_value": 50_000.0}
    r2 = {**BASE_RECORD, "metric_name": "net_income", "metric_value": 30_000.0}
    upsert_financial_input(r1, db_path=db, write=True)
    upsert_financial_input(r2, db_path=db, write=True)

    # Inserir 1 métrica para outro ticker (não deve aparecer)
    other = {**BASE_RECORD, "ticker": "BBAS3", "metric_name": "net_revenue"}
    upsert_financial_input(other, db_path=db, write=True)

    rows = get_financial_inputs("ITUB4", db_path=db)

    assert len(rows) == 2, f"Esperado 2 linhas para ITUB4, encontrado {len(rows)}"
    tickers = {r["ticker"] for r in rows}
    assert tickers == {"ITUB4"}, f"Ticker inesperado nos resultados: {tickers}"


def test_T05_get_financial_inputs_empty_ticker(tmp_path):
    """get_financial_inputs() retorna lista vazia se ticker não existe."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import get_financial_inputs

    rows = get_financial_inputs("INEXISTENTE", db_path=db)
    assert rows == [], f"Esperado lista vazia, encontrado {rows}"


# ---------------------------------------------------------------------------
# T06 — Filtro por period_end
# ---------------------------------------------------------------------------

def test_T06_filter_by_period_end(tmp_path):
    """get_financial_inputs(period_end=...) filtra corretamente por data."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    r_2023 = {**BASE_RECORD, "period_end": "2023-12-31", "fiscal_year": 2023}
    r_2024 = {**BASE_RECORD, "period_end": "2024-12-31", "fiscal_year": 2024}
    upsert_financial_input(r_2023, db_path=db, write=True)
    upsert_financial_input(r_2024, db_path=db, write=True)

    rows = get_financial_inputs("ITUB4", period_end="2023-12-31", db_path=db)

    assert len(rows) == 1, f"Esperado 1 linha (2023), encontrado {len(rows)}"
    assert rows[0]["period_end"] == "2023-12-31"


# ---------------------------------------------------------------------------
# T07 — Filtro por period_type
# ---------------------------------------------------------------------------

def test_T07_filter_by_period_type(tmp_path):
    """get_financial_inputs(period_type=...) filtra por DFP vs ITR."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    r_dfp = {**BASE_RECORD, "period_type": "DFP"}
    r_itr = {
        **BASE_RECORD,
        "period_type": "ITR",
        "period_end": "2024-09-30",
        "fiscal_quarter": 3,
    }
    upsert_financial_input(r_dfp, db_path=db, write=True)
    upsert_financial_input(r_itr, db_path=db, write=True)

    dfp_rows = get_financial_inputs("ITUB4", period_type="DFP", db_path=db)
    itr_rows = get_financial_inputs("ITUB4", period_type="ITR", db_path=db)

    assert len(dfp_rows) == 1 and dfp_rows[0]["period_type"] == "DFP"
    assert len(itr_rows) == 1 and itr_rows[0]["period_type"] == "ITR"


# ---------------------------------------------------------------------------
# T08 — Latest inputs: retorna período mais recente
# ---------------------------------------------------------------------------

def test_T08_get_latest_returns_most_recent_period(tmp_path):
    """get_latest_financial_inputs() retorna period_end máximo por metric_name."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_latest_financial_inputs

    r_2022 = {**BASE_RECORD, "period_end": "2022-12-31", "fiscal_year": 2022, "metric_value": 1.0}
    r_2023 = {**BASE_RECORD, "period_end": "2023-12-31", "fiscal_year": 2023, "metric_value": 2.0}
    r_2024 = {**BASE_RECORD, "period_end": "2024-12-31", "fiscal_year": 2024, "metric_value": 3.0}

    upsert_financial_input(r_2022, db_path=db, write=True)
    upsert_financial_input(r_2023, db_path=db, write=True)
    upsert_financial_input(r_2024, db_path=db, write=True)

    rows = get_latest_financial_inputs("ITUB4", db_path=db)

    assert len(rows) == 1, f"Esperado 1 linha (net_revenue), encontrado {len(rows)}"
    assert rows[0]["period_end"] == "2024-12-31", f"Esperado 2024-12-31, encontrado {rows[0]['period_end']}"
    assert rows[0]["metric_value"] == 3.0


# ---------------------------------------------------------------------------
# T09 — Latest inputs: prioriza source_priority menor em empate de período
# ---------------------------------------------------------------------------

def test_T09_latest_prioritizes_lower_source_priority(tmp_path):
    """Em empate de period_end, source_priority=1 (CVM) ganha sobre source_priority=2 (Excel)."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_latest_financial_inputs

    cvm_record = {
        **BASE_RECORD,
        "source_type":     "CVM_CSV",
        "source_priority": 1,
        "metric_value":    100.0,
        "confidence":      1.0,
    }
    excel_record = {
        **BASE_RECORD,
        "source_type":     "EXCEL_PIPELINE",
        "source_priority": 2,
        "metric_value":    200.0,
        "confidence":      0.8,
    }

    upsert_financial_input(cvm_record, db_path=db, write=True)
    upsert_financial_input(excel_record, db_path=db, write=True)

    rows = get_latest_financial_inputs("ITUB4", db_path=db)

    assert len(rows) == 1, f"Esperado 1 linha (net_revenue, CVM vence), encontrado {len(rows)}"
    assert rows[0]["source_type"] == "CVM_CSV", (
        f"Esperado CVM_CSV (priority=1), encontrado {rows[0]['source_type']}"
    )
    assert rows[0]["metric_value"] == 100.0


# ---------------------------------------------------------------------------
# T10 — Unicidade lógica
# ---------------------------------------------------------------------------

def test_T10_unique_constraint_absorbed_no_error(tmp_path):
    """Inserir com mesma chave UNIQUE (ticker+period_end+period_type+metric+source) não lança erro."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    # Inserir mesma chave com valores diferentes — deve resultar em 1 linha (upsert)
    upsert_financial_input({**BASE_RECORD, "metric_value": 111.0}, db_path=db, write=True)
    upsert_financial_input({**BASE_RECORD, "metric_value": 222.0}, db_path=db, write=True)
    upsert_financial_input({**BASE_RECORD, "metric_value": 333.0}, db_path=db, write=True)

    rows = get_financial_inputs("ITUB4", db_path=db)
    assert len(rows) == 1, f"Esperado 1 linha (chave duplicada absorvida), encontrado {len(rows)}"
    assert rows[0]["metric_value"] == 333.0, "Último valor deve prevalecer (333.0)"


def test_T10_different_source_type_creates_separate_row(tmp_path):
    """source_type diferente → chave única diferente → 2 linhas distintas."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    cvm = {**BASE_RECORD, "source_type": "CVM_CSV", "source_priority": 1}
    excel = {**BASE_RECORD, "source_type": "EXCEL_PIPELINE", "source_priority": 2}

    upsert_financial_input(cvm, db_path=db, write=True)
    upsert_financial_input(excel, db_path=db, write=True)

    rows = get_financial_inputs("ITUB4", db_path=db)
    assert len(rows) == 2, f"Esperado 2 linhas (fontes distintas), encontrado {len(rows)}"


# ---------------------------------------------------------------------------
# T11 — Campos de proveniência obrigatórios
# ---------------------------------------------------------------------------

def test_T11_missing_required_fields_raises_valueerror(tmp_path):
    """upsert_financial_input() lança ValueError se campos obrigatórios ausentes."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    # Ausente: source_type e source_priority (campos de proveniência)
    incomplete = {
        "ticker":      "ITUB4",
        "period_type": "DFP",
        "period_end":  "2024-12-31",
        "fiscal_year": 2024,
        "metric_name": "net_revenue",
        "metric_value": 100.0,
        # source_type AUSENTE
        # source_priority AUSENTE
    }

    with pytest.raises(ValueError, match="Campos obrigatórios ausentes"):
        upsert_financial_input(incomplete, db_path=db, write=True)


def test_T11_missing_ticker_raises_valueerror(tmp_path):
    """upsert_financial_input() lança ValueError se ticker ausente."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    no_ticker = {k: v for k, v in BASE_RECORD.items() if k != "ticker"}

    with pytest.raises(ValueError, match="Campos obrigatórios ausentes"):
        upsert_financial_input(no_ticker, db_path=db, write=True)


# ---------------------------------------------------------------------------
# T12 — write=False não persiste
# ---------------------------------------------------------------------------

def test_T12_dry_run_does_not_persist(tmp_path):
    """write=False (default) não insere nenhuma linha no banco."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    result = upsert_financial_input(BASE_RECORD, db_path=db)  # write=False por padrão

    assert result["action"] == "dry_run", f"Esperado 'dry_run', encontrado {result['action']}"

    rows = get_financial_inputs("ITUB4", db_path=db)
    assert rows == [], f"Nenhuma linha deve existir após dry-run, encontrado {len(rows)} linhas"


def test_T12_write_true_persists(tmp_path):
    """write=True persiste a linha — resultado action='upserted'."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, get_financial_inputs

    result = upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    assert result["action"] == "upserted", f"Esperado 'upserted', encontrado {result['action']}"
    rows = get_financial_inputs("ITUB4", db_path=db)
    assert len(rows) == 1, f"Esperado 1 linha após write=True, encontrado {len(rows)}"


# ---------------------------------------------------------------------------
# T13 — list_financial_input_coverage
# ---------------------------------------------------------------------------

def test_T13_coverage_summary(tmp_path):
    """list_financial_input_coverage() retorna 1 linha por ticker com resumo correto."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input, list_financial_input_coverage

    records = [
        {**BASE_RECORD, "ticker": "ITUB4", "metric_name": "net_revenue", "metric_value": 100.0, "confidence": 0.9},
        {**BASE_RECORD, "ticker": "ITUB4", "metric_name": "ebitda",      "metric_value": 50.0,  "confidence": 0.8},
        {**BASE_RECORD, "ticker": "BBAS3", "metric_name": "net_revenue", "metric_value": 80.0,  "confidence": 1.0},
    ]
    for r in records:
        upsert_financial_input(r, db_path=db, write=True)

    coverage = list_financial_input_coverage(db_path=db)

    assert len(coverage) == 2, f"Esperado 2 tickers, encontrado {len(coverage)}"

    itub = next((c for c in coverage if c["ticker"] == "ITUB4"), None)
    bbas = next((c for c in coverage if c["ticker"] == "BBAS3"), None)

    assert itub is not None, "ITUB4 não encontrado no coverage"
    assert bbas is not None, "BBAS3 não encontrado no coverage"

    assert itub["total_metrics"] == 2, f"ITUB4 deve ter 2 métricas, encontrado {itub['total_metrics']}"
    assert bbas["total_metrics"] == 1, f"BBAS3 deve ter 1 métrica, encontrado {bbas['total_metrics']}"
    assert itub["latest_period"] == "2024-12-31"
    assert float(itub["min_confidence"]) == pytest.approx(0.8, rel=1e-3)


def test_T13_coverage_empty(tmp_path):
    """list_financial_input_coverage() retorna lista vazia se tabela vazia."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import list_financial_input_coverage

    assert list_financial_input_coverage(db_path=db) == []


# ---------------------------------------------------------------------------
# T14 — delete dry-run não remove linhas
# ---------------------------------------------------------------------------

def test_T14_delete_dry_run_does_not_remove(tmp_path):
    """delete_financial_inputs_for_source() dry-run (write=False) não remove linhas."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import (
        upsert_financial_input, delete_financial_inputs_for_source, get_financial_inputs
    )

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    result = delete_financial_inputs_for_source(
        BASE_RECORD["source_path"], db_path=db  # write=False por padrão
    )

    assert result["action"] == "dry_run"
    assert result["rows_affected"] == 1

    # Linha ainda existe
    rows = get_financial_inputs("ITUB4", db_path=db)
    assert len(rows) == 1, "Linha não deve ter sido removida em dry-run"


# ---------------------------------------------------------------------------
# T15 — delete write=True remove linhas
# ---------------------------------------------------------------------------

def test_T15_delete_write_true_removes_rows(tmp_path):
    """delete_financial_inputs_for_source(write=True) remove linhas corretamente."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import (
        upsert_financial_input, delete_financial_inputs_for_source, get_financial_inputs
    )

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    # Verificar que linha existe
    assert len(get_financial_inputs("ITUB4", db_path=db)) == 1

    result = delete_financial_inputs_for_source(
        BASE_RECORD["source_path"], db_path=db, write=True
    )

    assert result["action"] == "deleted"
    assert result["rows_affected"] == 1

    # Linha foi removida
    rows = get_financial_inputs("ITUB4", db_path=db)
    assert len(rows) == 0, f"Linha deveria ter sido removida, encontrado {len(rows)}"


# ---------------------------------------------------------------------------
# T16 — Não toca asset_intelligence_snapshots
# ---------------------------------------------------------------------------

def test_T16_does_not_create_asset_intelligence_snapshots(tmp_path):
    """Store não cria nem altera a tabela asset_intelligence_snapshots."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    assert "asset_intelligence_snapshots" not in tables, (
        "Store NÃO deve criar asset_intelligence_snapshots"
    )


def test_T16_does_not_write_to_asset_intelligence_snapshots(tmp_path):
    """Store não insere dados em asset_intelligence_snapshots mesmo que ela exista."""
    db = tmp_path / "ingestion.db"
    _init(db)

    # Criar a tabela manualmente (simula ambiente onde ela já existe)
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS asset_intelligence_snapshots (id TEXT, ticker TEXT, data TEXT)"
    )
    conn.commit()
    conn.close()

    from src.valuation.financial_inputs_store import upsert_financial_input
    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM asset_intelligence_snapshots"
    ).fetchone()[0]
    conn.close()

    assert count == 0, f"asset_intelligence_snapshots deve permanecer vazia, encontrado {count} linhas"


# ---------------------------------------------------------------------------
# T17 — Não toca valuation_results
# ---------------------------------------------------------------------------

def test_T17_does_not_create_valuation_results(tmp_path):
    """Store não cria nem altera a tabela valuation_results."""
    db = tmp_path / "ingestion.db"
    _init(db)

    from src.valuation.financial_inputs_store import upsert_financial_input

    upsert_financial_input(BASE_RECORD, db_path=db, write=True)

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    assert "valuation_results" not in tables, (
        "Store NÃO deve criar valuation_results"
    )


def test_T17_does_not_write_to_valuation_results(tmp_path):
    """Store não insere dados em valuation_results mesmo que ela exista."""
    db = tmp_path / "ingestion.db"
    _init(db)

    # Criar a tabela manualmente
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS valuation_results
           (id TEXT, ticker TEXT, fair_value REAL, computed_at TEXT)"""
    )
    conn.commit()
    conn.close()

    from src.valuation.financial_inputs_store import (
        upsert_financial_input, get_latest_financial_inputs, list_financial_input_coverage
    )
    upsert_financial_input(BASE_RECORD, db_path=db, write=True)
    get_latest_financial_inputs("ITUB4", db_path=db)
    list_financial_input_coverage(db_path=db)

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM valuation_results"
    ).fetchone()[0]
    conn.close()

    assert count == 0, f"valuation_results deve permanecer vazia, encontrado {count} linhas"


# ---------------------------------------------------------------------------
# T18 — Não altera tabelas pré-existentes
# ---------------------------------------------------------------------------

def test_T18_does_not_alter_existing_tables(tmp_path):
    """ensure_financial_inputs_schema() não altera cvm_statements pré-existente."""
    db = tmp_path / "ingestion.db"
    from src.ingestion.db import init_db
    init_db(db)

    # Snapshot das colunas de cvm_statements antes
    conn = sqlite3.connect(db)
    cols_before = {row[1] for row in conn.execute(
        "PRAGMA table_info(cvm_statements)"
    ).fetchall()}
    conn.close()

    from src.valuation.financial_inputs_store import ensure_financial_inputs_schema
    ensure_financial_inputs_schema(db)

    conn = sqlite3.connect(db)
    cols_after = {row[1] for row in conn.execute(
        "PRAGMA table_info(cvm_statements)"
    ).fetchall()}
    conn.close()

    assert cols_before == cols_after, (
        f"ensure_financial_inputs_schema() alterou cvm_statements!\n"
        f"Antes: {cols_before}\nDepois: {cols_after}"
    )
