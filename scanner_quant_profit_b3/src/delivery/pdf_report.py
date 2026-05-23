"""PDF report generator for investment thesis output.

CAT-007 (M013-S01): Minimal delivery layer — exists and imports without error.
Actual PDF generation requires full data wiring in subsequent slices.
"""
from __future__ import annotations

import io
import logging
import sys
from contextlib import redirect_stdout
from typing import Any

logger = logging.getLogger(__name__)


def _fpdf_to_bytes(pdf) -> bytes:
    """
    fpdf 1.7.2 writes PDF content to stdout instead of returning it.
    Capture via redirect_stdout to get bytes.
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        pdf.output()
    return buf.getvalue().encode("latin-1")


class ReportGenerator:
    """
    Generates PDF investment thesis reports.

    Minimal implementation (CAT-007): creates valid PDF structure.
    Full data integration (real charts, thesis content, valuation) — future slices.
    """

    def generate(self, ticker: str, detail: dict[str, Any]) -> bytes:
        """
        Generate a PDF report for the given ticker.

        Args:
            ticker: Asset ticker symbol (e.g. 'PETR4').
            detail: Asset detail dict from get_asset_detail().

        Returns:
            PDF bytes.
        """
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # ── Header ─────────────────────────────────────────────────────────
            pdf.set_font("Helvetica", size=16, style="B")
            pdf.cell(0, 10, f"Relatorio de Investimento - {ticker}", ln=True, align="C")
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 6, "Plataforma Quant Profit B3", ln=True, align="C")
            pdf.ln(5)

            # ── Summary block ─────────────────────────────────────────────────
            pdf.set_font("Helvetica", size=11, style="B")
            pdf.cell(0, 8, "Resumo do Ativo", ln=True)

            score = detail.get("integrated_score") or detail.get("score") or "N/A"
            status = detail.get("integrated_status") or detail.get("status") or "N/A"
            upside = detail.get("upside_pct")
            fair_value = detail.get("fair_value") or detail.get("fair_value_brl", 0)
            current_price = detail.get("current_price") or detail.get("market_price")

            fields = [
                ("Ticker", str(ticker)),
                ("Score Integrado", f"{score} / 100" if isinstance(score, (int, float)) else str(score)),
                ("Status", str(status)),
                ("Upside", f"{upside:+.2f}%" if isinstance(upside, (int, float)) else str(upside or "N/A")),
                ("Preco Justo (R$)",
                 f"{fair_value:.2f}" if isinstance(fair_value, (int, float)) and fair_value > 0 else str(fair_value)),
                ("Preco Atual (R$)",
                 f"{current_price:.2f}" if isinstance(current_price, (int, float)) else str(current_price or "N/A")),
            ]
            for label, value in fields:
                pdf.set_font("Helvetica", size=9)
                pdf.cell(50, 6, label, border=0)
                pdf.set_font("Helvetica", "B", size=9)
                pdf.cell(0, 6, value, border=0, ln=True)

            pdf.ln(5)
            pdf.set_font("Helvetica", size=8, style="I")
            pdf.cell(0, 5, "Este relatorio e informativo e nao constitui recomendacao de investimento.", ln=True, align="C")

            return _fpdf_to_bytes(pdf)

        except Exception as exc:
            logger.warning("PDF generation failed for %s: %s — returning placeholder", ticker, exc)
            # Return valid placeholder PDF so the UI doesn't crash
            try:
                from fpdf import FPDF

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", size=12)
                pdf.cell(0, 10, f"PDF indisponivel para {ticker}", ln=True, align="C")
                pdf.set_font("Helvetica", size=9)
                pdf.cell(0, 6, f"Erro: {exc}", ln=True, align="C")
                return _fpdf_to_bytes(pdf)
            except Exception:
                # Last resort: return minimal valid PDF header
                return (
                    b"%PDF-1.4\n"
                    b"1 0 obj<</Type/Catalog>>endobj "
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
                    b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj "
                    b"xref 0 4\n"
                    b"0000000000 65535 f \n"
                    b"0000000009 00000 n \n"
                    b"0000000058 00000 n \n"
                    b"0000000115 00000 n \n"
                    b"trailer<</Size 4/Root 1 0 R>>\n"
                    b"startxref\n"
                    b"210\n"
                    b"%%EOF"
                )


def generate(ticker: str, detail: dict[str, Any]) -> bytes:
    """Convenience wrapper matching the interface expected by pages/inteligencia_ativo.py."""
    return ReportGenerator().generate(ticker, detail)


def generate_pdf_report(ticker: str, detail: dict[str, Any]) -> bytes:
    """Alias for generate()."""
    return generate(ticker, detail)