"""
test_ipe_ingestion.py
Tests for CVM IPE ingestion — ING-03.
"""
from __future__ import annotations

import io
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.ingestion.cvm_downloader import classify_event, extract_ipe_pdf_text
from src.ingestion.db import init_db


def test_classify_event_earnings():
    assert classify_event("Resultados") == "earnings"


def test_classify_event_material_fact():
    assert classify_event("Fato Relevante") == "material_fact"


def test_classify_event_meeting():
    assert classify_event("Assembleia") == "meeting"


def test_classify_event_announcement():
    assert classify_event("Comunicado ao Mercado") == "announcement"


def test_classify_event_unknown_returns_other():
    assert classify_event("Alguma Coisa Nova") == "other"


def test_extract_ipe_pdf_text_returns_empty_on_pdfplumber_failure():
    with patch("pdfplumber.open", side_effect=Exception("bad pdf")):
        with patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status = lambda: None
            mock_get.return_value.content = b"fake"
            result = extract_ipe_pdf_text("http://example.com/doc.pdf")
    assert result == ""


def test_extract_ipe_pdf_text_returns_empty_on_request_failure():
    import requests
    with patch("requests.get", side_effect=requests.RequestException("timeout")):
        result = extract_ipe_pdf_text("http://example.com/doc.pdf")
    assert result == ""


def test_ipe_csv_filtered_by_codigo_cvm(tmp_path):
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader(output_dir=tmp_path / "cvm")

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)

    # IPE CSV with two companies; only 001023 (BBAS3) should be stored
    csv_content = (
        "Codigo_CVM;Categoria;Tipo;Especie;Data_Referencia;Link_Download\n"
        "1023;Resultados;ITR;;2024-09-30;\n"
        "9512;Fato Relevante;FRE;;2024-09-30;\n"
    )
    csv_path = tmp_path / "ipe_2024.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    with patch.object(downloader, "download_ipe", return_value=[csv_path]):
        inserted = downloader.parse_and_store_ipe(
            "BBAS3", 2024, conn, extract_pdf=False
        )

    assert inserted == 1
    rows = conn.execute(
        "SELECT * FROM cvm_statements WHERE ticker='BBAS3' AND period_type='IPE'"
    ).fetchall()
    assert len(rows) == 1
    conn.close()


def test_download_ipe_uses_correct_url(tmp_path):
    from src.ingestion.cvm_downloader import CVMDownloader
    downloader = CVMDownloader(output_dir=tmp_path / "cvm_test")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ipe_cia_aberta_2024.csv", "Codigo_CVM;Categoria\n")
    buf.seek(0)

    with patch.object(downloader, "_fetch", return_value=buf.read()) as mock_fetch:
        try:
            downloader.download_ipe(2024)
        except Exception:
            pass
        called_url = mock_fetch.call_args[0][0] if mock_fetch.called else ""
    assert "IPE/DADOS/ipe_cia_aberta_2024.zip" in called_url
