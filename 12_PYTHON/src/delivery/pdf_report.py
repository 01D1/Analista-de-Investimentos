"""
pdf_report.py
-------------
Gerador de relatorios PDF de investimento - Phase 5 Delivery.

Fluxo: get_asset_detail(ticker) -> ReportGenerator.generate() -> bytes (in-memory)
Uso:
    from src.delivery.pdf_report import ReportGenerator
    pdf_bytes = ReportGenerator().generate(ticker, data)
    # ou para testes sem banco:
    pdf_bytes = ReportGenerator().generate_from_fixture("PETR4")
"""
from __future__ import annotations

from fpdf import FPDF

from src.utils.logger import get_logger

log = get_logger(__name__)

_DISCLAIMER_TEXT = (
    "Este relatorio foi elaborado por analista de valores mobiliarios autonomo, "
    "em conformidade com as disposicoes da Instrucao CVM no 598, de 3 de maio de 2018. "
    "As informacoes e analises contidas neste documento tem carater exclusivamente "
    "informativo e nao constituem oferta de compra ou venda de valores mobiliarios, "
    "tampouco recomendacao de investimento. O analista responsavel certifica que as "
    "opinioes expressas neste relatorio refletem de forma precisa, exclusiva e "
    "independente suas visoes e analises pessoais. Investimentos em valores mobiliarios "
    "envolvem riscos. Rentabilidade passada nao e garantia de rentabilidade futura."
)

# Mapeamento de cor RGB por posicionamento (D-09)
_POSITIONING_COLORS: dict[str, tuple[int, int, int]] = {
    "COMPRAR": (22, 163, 74),
    "MANTER": (202, 138, 4),
    "VENDER": (220, 38, 38),
}


class ReportGenerator(FPDF):
    """Gerador de relatorios PDF de investimento com secoes estruturadas.

    Subclasse de FPDF com header/footer customizados e metodos por secao.
    Uso: instanciar, chamar generate() ou generate_from_fixture().

    T-05-03: generate() e generate_from_fixture() retornam bytes(self.output()) -
    nunca escrevem em disco, sem possibilidade de path traversal (D-17).
    """

    # Ticker atual - definido por _build_pdf() para uso no header
    _ticker: str = ""

    def header(self) -> None:
        """Cabecalho de pagina: titulo da plataforma e ticker."""
        self.set_font("Helvetica", style="B", size=10)
        self.set_text_color(80, 80, 80)
        self.cell(
            0,
            8,
            f"Plataforma Quant B3 - Relatorio de Investimento | {self._ticker}",
            align="C",
        )
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self) -> None:
        """Rodape de pagina: numero de pagina centralizado."""
        self.set_y(-15)
        self.set_font("Helvetica", style="I", size=8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    # ── Secoes privadas ──────────────────────────────────────────────────────────

    def _header_section(self, ticker: str, generated_at: str) -> None:
        """Titulo principal com ticker e data de geracao."""
        self.set_font("Helvetica", style="B", size=14)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, f"Relatorio de Investimento - {ticker}", ln=True, align="L")
        self.set_font("Helvetica", size=10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Gerado em: {generated_at}", ln=True)
        self.ln(4)

    def _thesis_section(self, thesis: dict) -> None:
        """Posicionamento, confianca, rationale e one-liner."""
        positioning = thesis.get("positioning", "-")
        confidence = thesis.get("confidence", "-")
        rationale = thesis.get("rationale", "")
        summary = thesis.get("summary_one_line", "")

        # Titulo da secao
        self.set_font("Helvetica", style="B", size=12)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, "Tese de Investimento", ln=True)

        # Posicionamento com cor
        r, g, b = _POSITIONING_COLORS.get(positioning, (80, 80, 80))
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(r, g, b)
        self.cell(0, 7, f"Posicionamento: {positioning}  |  Confianca: {confidence}", ln=True)

        # Resumo de uma linha
        self.set_font("Helvetica", style="I", size=10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 6, summary)
        self.ln(2)

        # Racional completo
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, rationale)
        self.ln(4)

    def _bull_bear_section(self, thesis: dict) -> None:
        """Cenario otimista e pessimista em blocos de texto."""
        bull = thesis.get("bull_case", "")
        bear = thesis.get("bear_case", "")

        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(22, 163, 74)  # Verde
        self.cell(0, 7, "Cenario Otimista", ln=True)
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, bull)
        self.ln(3)

        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(220, 38, 38)  # Vermelho
        self.cell(0, 7, "Cenario Pessimista", ln=True)
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, bear)
        self.ln(4)

    def _drivers_risks_section(self, drivers: list[dict], risks: list[dict]) -> None:
        """Tabelas de drivers e riscos com titulo/descricao/impacto."""
        # Drivers
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, "Principais Drivers", ln=True)
        self.set_font("Helvetica", size=9)
        self.set_fill_color(230, 240, 255)

        col_w = [55, 110, 25]
        headers = ["Driver", "Descricao", "Impacto"]
        self.set_font("Helvetica", style="B", size=9)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", size=8)
        for d in drivers:
            title = str(d.get("title", ""))[:40]
            desc = str(d.get("description", ""))[:80]
            impact = str(d.get("impact", ""))[:12]
            self.cell(col_w[0], 5, title, border=1)
            self.cell(col_w[1], 5, desc, border=1)
            self.cell(col_w[2], 5, impact, border=1)
            self.ln()
        self.ln(3)

        # Riscos
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, "Principais Riscos", ln=True)
        self.set_font("Helvetica", style="B", size=9)
        self.set_fill_color(255, 235, 235)
        risk_headers = ["Risco", "Descricao", "Severidade"]
        for i, h in enumerate(risk_headers):
            self.cell(col_w[i], 6, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", size=8)
        for r in risks:
            title = str(r.get("title", ""))[:40]
            desc = str(r.get("description", ""))[:80]
            severity = str(r.get("severity", r.get("impact", "")))[:12]
            self.cell(col_w[0], 5, title, border=1)
            self.cell(col_w[1], 5, desc, border=1)
            self.cell(col_w[2], 5, severity, border=1)
            self.ln()
        self.ln(4)

    def _valuation_section(self, dcf: dict, multiples: dict) -> None:
        """Fair value, upside, P/E, EV/EBITDA, PBV e dividend yield."""
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, "Valuation", ln=True)

        def _fmt_brl(v: object) -> str:
            try:
                return f"R$ {float(v):,.2f}"  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return "-"

        def _fmt_pct(v: object) -> str:
            try:
                return f"{float(v):+.1f}%"  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return "-"

        def _fmt_mult(v: object) -> str:
            try:
                return f"{float(v):.1f}x"  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return "-"

        rows = [
            ("Fair Value (DCF)", _fmt_brl(dcf.get("fair_value_brl"))),
            ("Upside", _fmt_pct(dcf.get("upside_pct"))),
            ("P/L", _fmt_mult(multiples.get("pe_ratio"))),
            ("EV/EBITDA", _fmt_mult(multiples.get("ev_ebitda"))),
        ]
        if multiples.get("pbv_ratio") is not None:
            rows.append(("P/VPA", _fmt_mult(multiples.get("pbv_ratio"))))
        if multiples.get("dividend_yield") is not None:
            rows.append(("Dividend Yield", _fmt_pct(multiples.get("dividend_yield"))))

        self.set_font("Helvetica", size=10)
        col_a, col_b = 70, 70
        for label, value in rows:
            self.set_font("Helvetica", style="B", size=10)
            self.cell(col_a, 6, label, border="B")
            self.set_font("Helvetica", size=10)
            self.cell(col_b, 6, value, border="B", ln=True)
        self.ln(4)

    def _financials_section(self, ltm: dict) -> None:
        """LTM financials: receita, EBITDA, lucro liquido, FCF, divida liquida."""
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, "Financeiros (LTM)", ln=True)

        def _fmt_m(v: object) -> str:
            try:
                return f"R$ {float(v) / 1_000_000:.1f}M"  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return "-"

        rows = [
            ("Receita Liquida", _fmt_m(ltm.get("net_revenue"))),
            ("EBITDA", _fmt_m(ltm.get("ebitda"))),
            ("Lucro Liquido", _fmt_m(ltm.get("net_income"))),
            ("FCF", _fmt_m(ltm.get("fcf"))),
            ("Divida Liquida", _fmt_m(ltm.get("net_debt"))),
        ]
        self.set_font("Helvetica", size=10)
        col_a, col_b = 70, 70
        for label, value in rows:
            self.set_font("Helvetica", style="B", size=10)
            self.cell(col_a, 6, label, border="B")
            self.set_font("Helvetica", size=10)
            self.cell(col_b, 6, value, border="B", ln=True)
        self.ln(4)

    def _macro_section(self, macro: dict) -> None:
        """Snapshot das 4 principais series macro (ultimo valor)."""
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, "Contexto Macro", ln=True)

        series_display = [
            ("Selic", "selic", "{:.2f}%"),
            ("IPCA 12m", "ipca_12m", "{:.2f}%"),
            ("PTAX (R$/USD)", "ptax", "R$ {:.4f}"),
            ("CDS Brasil", "cds_brasil", "{:.4f}"),
        ]
        self.set_font("Helvetica", size=10)
        col_a, col_b = 70, 70
        for label, key, fmt in series_display:
            series = macro.get(key, [])
            latest = series[-1]["value"] if series else None
            try:
                value_str = fmt.format(latest) if latest is not None else "-"
            except (TypeError, ValueError):
                value_str = "-"
            self.set_font("Helvetica", style="B", size=10)
            self.cell(col_a, 6, label, border="B")
            self.set_font("Helvetica", size=10)
            self.cell(col_b, 6, value_str, border="B", ln=True)
        self.ln(4)

    def _disclaimer(self) -> None:
        """Disclaimer obrigatorio CVM IN 598 - sempre ao final do relatorio."""
        self.add_page()
        self.set_font("Helvetica", style="B", size=10)
        self.set_text_color(80, 80, 80)
        self.cell(0, 7, "Aviso Legal - CVM IN 598", ln=True)
        self.set_font("Helvetica", style="I", size=8)
        self.set_text_color(107, 114, 128)
        self.multi_cell(0, 5, _DISCLAIMER_TEXT)

    # ── API publica ─────────────────────────────────────────────────────────────

    def generate(self, ticker: str, data: dict) -> bytes:
        """Gera relatorio PDF completo para o ticker com dados fornecidos.

        T-05-03: Retorna bytes(self.output()) - nunca escreve em disco.

        Args:
            ticker: Ticker do ativo (ex: 'PETR4').
            data: Dict com chaves: thesis (dict), dcf (dict), ltm (dict),
                  multiples (dict), macro (dict[str, list[dict]]).

        Returns:
            bytes: Conteudo do PDF (comeca com b'%PDF').
        """
        self._ticker = ticker
        self.add_page()

        thesis = data.get("thesis", {})
        dcf = data.get("dcf", {})
        ltm = data.get("ltm", {})
        multiples = data.get("multiples", {})
        macro = data.get("macro", {})
        generated_at = data.get("generated_at", "-")

        self._header_section(ticker, generated_at)
        self._thesis_section(thesis)
        self._bull_bear_section(thesis)
        self._drivers_risks_section(
            thesis.get("drivers", []),
            thesis.get("risks", []),
        )
        self._valuation_section(dcf, multiples)
        self._financials_section(ltm)
        self._macro_section(macro)
        self._disclaimer()

        log.info(f"[pdf_report] relatorio gerado - ticker={ticker}")
        return bytes(self.output())

    def generate_from_fixture(self, ticker: str) -> bytes:
        """Gera relatorio PDF a partir de dados de fixture minimos (para testes).

        T-05-03: Retorna bytes - nunca escreve em disco.
        Instancia novo ReportGenerator para evitar reuso apos output().
        """
        fixture: dict = {
            "generated_at": "2026-05-18 21:00:00",
            "thesis": {
                "positioning": "COMPRAR",
                "confidence": "ALTA",
                "rationale": (
                    "Empresa com forte geracao de caixa e desconto relevante ao DCF. "
                    "Pre-sal oferece visibilidade de longo prazo."
                ),
                "summary_one_line": "DCF indica upside de 35% com WACC de 11.5%.",
                "bull_case": (
                    "Preco do petroleo acima de USD 80 expande margens EBITDA para 55%+. "
                    "Reducao de divida acelera retorno ao acionista."
                ),
                "bear_case": (
                    "Queda do Brent abaixo de USD 60 comprime FCF. "
                    "Risco regulatorio em distribuidoras de combustivel."
                ),
                "drivers": [
                    {
                        "title": "Pre-sal producao",
                        "description": "Expansao de capacidade com custo extracaocompetitivo",
                        "impact": "HIGH",
                    },
                    {
                        "title": "Reducao de alavancagem",
                        "description": "Divida liquida/EBITDA < 1.5x esperado em 2025",
                        "impact": "MEDIUM",
                    },
                ],
                "risks": [
                    {
                        "title": "Volatilidade do petroleo",
                        "description": "Brent abaixo de USD 60 reduz FCF em 40%",
                        "severity": "HIGH",
                    },
                    {
                        "title": "Interferencia politica",
                        "description": "Historico de subsidios de combustivel pelo governo",
                        "severity": "MEDIUM",
                    },
                ],
                "methodology_disclosure": "DCF + EV/EBITDA setorial",
            },
            "dcf": {
                "fair_value_brl": 45.80,
                "upside_pct": 34.7,
            },
            "ltm": {
                "net_revenue": 580_000_000_000,
                "ebitda": 290_000_000_000,
                "net_income": 124_000_000_000,
                "fcf": 95_000_000_000,
                "net_debt": 230_000_000_000,
            },
            "multiples": {
                "price": 34.00,
                "pe_ratio": 5.8,
                "ev_ebitda": 3.9,
                "pbv_ratio": 1.4,
                "dividend_yield": 8.5,
            },
            "macro": {
                "selic": [{"date": "2026-05-18", "value": 14.75}],
                "ipca_12m": [{"date": "2026-05-18", "value": 4.83}],
                "ptax": [{"date": "2026-05-18", "value": 5.7821}],
                "cds_brasil": [{"date": "2026-05-18", "value": 0.0175}],
                "pib_nominal": [],
            },
        }
        # Instancia novo ReportGenerator para evitar reuso apos output() (Pitfall PATTERNS.md)
        fresh = ReportGenerator()
        return fresh.generate(ticker, fixture)
