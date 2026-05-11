"""
test_cvm_ingestion.py
Tests for CVM DFP/ITR ingestion — ING-01, ING-02.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.ingestion.db import init_db, get_connection


def make_test_db(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "ingestion.db"
    init_db(db)
    return sqlite3.connect(db)


def test_get_cvm_code_returns_zero_padded():
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader()
    code = downloader.get_cvm_code("BBAS3")
    assert len(code) == 6
    assert code.isdigit()


def test_write_to_db_inserts_records(tmp_path):
    conn = make_test_db(tmp_path)
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader()
    records = [
        {
            "ticker": "BBAS3",
            "cvm_code": "001023",
            "year": 2024,
            "period_type": "DFP",
            "account_code": "3.01",
            "account_name": "Receita Bruta",
            "normalized_name": None,
            "value": 100000.0,
            "reference_date": "2024-12-31",
        }
    ]
    inserted = downloader.write_to_db(records, conn)
    assert inserted == 1
    row = conn.execute("SELECT * FROM cvm_statements WHERE ticker='BBAS3'").fetchone()
    assert row is not None
    conn.close()


def test_write_to_db_deduplicates(tmp_path):
    conn = make_test_db(tmp_path)
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader()
    record = {
        "ticker": "PETR4",
        "cvm_code": "009512",
        "year": 2024,
        "period_type": "DFP",
        "account_code": "3.01",
        "account_name": "Receita",
        "normalized_name": None,
        "value": 50000.0,
        "reference_date": "2024-12-31",
    }
    downloader.write_to_db([record], conn)
    second = downloader.write_to_db([record], conn)
    assert second == 0
    count = conn.execute("SELECT COUNT(*) FROM cvm_statements WHERE ticker='PETR4'").fetchone()[0]
    assert count == 1
    conn.close()


def test_itr_reconciliation_keeps_ultimo(tmp_path):
    """parse_and_store() for ITR must drop PENULTIMO rows, keep ULTIMO."""
    conn = make_test_db(tmp_path)
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader(output_dir=tmp_path / "cvm")

    # Build fake ITR CSV with both ULTIMO and PENULTIMO rows
    csv_content = (
        "CD_CVM;ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA;MOEDA\n"
        "001023;\xda\x4c\x54\x49\x4d\x4f;2024-09-30;3.01;Receita;100000;UNIDADE;BRL\n"
        "001023;PEN\xda\x4c\x54\x49\x4d\x4f;2024-09-30;3.01;Receita;90000;UNIDADE;BRL\n"
    )
    csv_path = tmp_path / "itr_cia_aberta_2024.csv"
    csv_path.write_bytes(csv_content.encode("latin-1"))

    with patch.object(downloader, "download_itr", return_value=[csv_path]):
        raw_dir = tmp_path / "raw" / "cvm"
        downloader.parse_and_store("BBAS3", 2024, "ITR", conn, raw_dir)

    rows = conn.execute(
        "SELECT value FROM cvm_statements WHERE ticker='BBAS3' AND period_type='ITR'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 100000.0
    conn.close()


def test_raw_csv_saved_to_disk(tmp_path):
    conn = make_test_db(tmp_path)
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader(output_dir=tmp_path / "cvm")

    csv_content = (
        "CD_CVM;ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA;MOEDA\n"
        "001023;\xda\x4c\x54\x49\x4d\x4f;2024-12-31;3.01;Receita;100000;UNIDADE;BRL\n"
    )
    csv_path = tmp_path / "dfp_2024.csv"
    csv_path.write_bytes(csv_content.encode("latin-1"))

    with patch.object(downloader, "download_dfp", return_value=[csv_path]):
        raw_dir = tmp_path / "raw" / "cvm"
        downloader.parse_and_store("BBAS3", 2024, "DFP", conn, raw_dir)

    raw_files = list((raw_dir / "2024").glob("BBAS3_DFP_*.csv"))
    assert len(raw_files) == 1
    conn.close()
