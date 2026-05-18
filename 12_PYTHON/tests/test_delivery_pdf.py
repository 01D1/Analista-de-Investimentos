"""
test_delivery_pdf.py
--------------------
Phase 5 - PDF generation tests covering DEL-05.

Covers:
  - generate_from_fixture() retorna bytes nao-vazios comecando com b'%PDF'
  - PDF contem ticker e texto de disclaimer CVM IN 598
  - generate_from_fixture() completa em menos de 30 segundos
"""
from __future__ import annotations

import time


def test_generate_returns_pdf_bytes():
    """DEL-05: ReportGenerator.generate_from_fixture() retorna bytes comecando com b'%PDF'."""
    from src.delivery.pdf_report import ReportGenerator

    rg = ReportGenerator()
    pdf_bytes = rg.generate_from_fixture("PETR4")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF", f"PDF deve comecar com b'%PDF', obteve: {pdf_bytes[:4]}"


def test_pdf_contains_required_strings():
    """DEL-05: PDF contem ticker e texto do disclaimer CVM IN 598."""
    import io

    import pdfplumber

    from src.delivery.pdf_report import ReportGenerator

    pdf_bytes = ReportGenerator().generate_from_fixture("PETR4")
    # fpdf2 usa streams comprimidos (zlib) — pdfplumber e necessario para extrair texto
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = " ".join(page.extract_text() or "" for page in pdf.pages)
    assert "PETR4" in full_text, "PDF deve conter o ticker PETR4"
    assert "CVM" in full_text, "PDF deve conter texto do disclaimer CVM IN 598"


def test_generate_under_30s():
    """DEL-05: Geracao de PDF completa em menos de 30 segundos."""
    from src.delivery.pdf_report import ReportGenerator

    t0 = time.time()
    ReportGenerator().generate_from_fixture("PETR4")
    elapsed = time.time() - t0
    assert elapsed < 30, f"PDF levou {elapsed:.1f}s, limite e 30s"
