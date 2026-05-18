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

_CVM_DISCLAIMER = (
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

# Dados de fixture para testes sem banco de dados (DEL-05)
_FIXTURE: dict = {
    "thesis": {
        "bull_case": "Empresa com forte geracao de caixa e expansao de margem.",
        "bear_case": "Pressao competitiva e desaceleracao macro podem afetar crescimento.",
        "positioning": "COMPRAR",
        "confidence": "ALTA",
        "rationale": "DCF indica desconto de 35% ao preco atual com WACC conservador.",
        "summary_one_line": "DCF sugere forte desconto - upside estrutural.",
        "methodology_disclosure": "DCF FCFF, WACC=12.5%, g=4.0%",
        "fair_value_brl": 48.50,
        "drivers": [
            {
                "title": "Expansao de margem EBITDA",
                "description": "Eficiencias operacionais.",
                "impact": "HIGH",
            },
            {
                "title": "Crescimento de receita",
                "description": "Novos mercados.",
                "impact": "MEDIUM",
            },
        ],
        "risks": [
            {
                "title": "Risco macro",
                "description": "Alta de juros comprime valuation.",
                "severity": "HIGH",
            },
            {
                "title": "Concorrencia",
                "description": "Novos entrantes.",
                "severity": "MEDIUM",
            },
        ],
    },
    "dcf": {"fair_value_brl": 48.50, "upside_pct": 34.7, "wacc": 0.125, "terminal_growth": 0.04},
    "ltm": {
        "net_revenue": 5_200_000_000,
        "ebitda": 1_300_000_000,
        "net_income": 780_000_000,
        "fcf": 650_000_000,
        "net_debt": 2_100_000_000,
    },
    "multiples": {
        "pe_ratio": 12.5,
        "ev_ebitda": 8.2,
        "pbv_ratio": 1.8,
        "dividend_yield": 0.048,
        "price": 36.10,
    },
    "news": [],
    "generated_at": "2026-05-18T14:00:00",
}


class ReportGenerator(FPDF):
    """Gerador de relatorios PDF de investimento com secoes estruturadas.

    Subclasse de FPDF com header/footer customizados e metodos por secao.
    Uso: instanciar, chamar generate() ou generate_from_fixture().

    T-05-03: generate() e generate_from_fixture() retornam bytes(self.output()) -
    nunca escrevem em disco, sem possibilidade de path traversal (D-17).
    """

    # Titulo do documento - definido por generate() para uso no header
    _doc_title: str = ""

    def header(self) -> None:
        """Cabecalho de pagina: titulo do relatorio centralizado com linha separadora."""
        self.set_font("Helvetica", style="B", size=14)
        self.set_text_color(30, 30, 30)
        self.cell(
            0,
            10,
            getattr(self, "_doc_title", "Relatorio"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(30, 58, 95)  # Navy #1E3A5F
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        """Rodape de pagina: numero de pagina centralizado em cinza."""
        self.set_y(-15)
        self.set_font("Helvetica", style="I", size=8)
        self.set_text_color(107, 114, 128)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    # ── Helpers privados ─────────────────────────────────────────────────────────

    def _section_title(self, title: str) -> None:
        """Helper: renderiza titulo de secao em navy 11pt Bold."""
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(30, 58, 95)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    # ── Secoes privadas ──────────────────────────────────────────────────────────

    def _header_section(self, ticker: str, generated_at: str) -> None:
        """Ativo e data de geracao."""
        self.set_font("Helvetica", size=10)
        self.set_text_color(60, 60, 60)
        self.cell(0, 6, f"Ativo: {ticker}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, f"Gerado em: {generated_at}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def _thesis_section(self, thesis: dict) -> None:
        """Posicionamento, confianca, rationale e one-liner."""
        self._section_title("Tese de Investimento")
        positioning = thesis.get("positioning", "-")
        confidence = thesis.get("confidence", "-")
        rationale = thesis.get("rationale", "")
        summary = thesis.get("summary_one_line", "")

        # Posicionamento com cor semantica
        r, g, b = _POSITIONING_COLORS.get(positioning, (80, 80, 80))
        self.set_font("Helvetica", style="B", size=11)
        self.set_text_color(r, g, b)
        self.cell(0, 7, f"Posicionamento: {positioning}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

        self.set_font("Helvetica", size=10)
        self.cell(0, 6, f"Confianca: {confidence}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # Racional completo
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, rationale)
        self.ln(2)

        # Resumo de uma linha em italico
        self.set_font("Helvetica", style="I", size=9)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 5, summary)
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def _bull_bear_section(self, thesis: dict) -> None:
        """Cenario otimista e pessimista em blocos de texto."""
        bull = thesis.get("bull_case", "")
        bear = thesis.get("bear_case", "")

        self._section_title("Cenario Otimista")
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, bull)
        self.ln(4)

        self._section_title("Cenario Pessimista")
        self.set_font("Helvetica", size=10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, bear)
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def _drivers_risks_section(self, drivers: list[dict], risks: list[dict]) -> None:
        """Tabelas de drivers e riscos com titulo/descricao/impacto."""
        # Drivers
        self._section_title("Drivers de Investimento")
        self.set_font("Helvetica", size=9)

        col_w = [55, 110, 25]
        headers = ["Driver", "Descricao", "Impacto"]
        self.set_font("Helvetica", style="B", size=9)
        self.set_fill_color(230, 240, 255)
        for i, h in enumerate(headers):
            self.cell(col_w[i], 6, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", size=8)
        self.set_fill_color(255, 255, 255)
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
        self._section_title("Riscos")
        self.set_font("Helvetica", style="B", size=9)
        self.set_fill_color(255, 235, 235)
        risk_headers = ["Risco", "Descricao", "Severidade"]
        for i, h in enumerate(risk_headers):
            self.cell(col_w[i], 6, h, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", size=8)
        self.set_fill_color(255, 255, 255)
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
        self._section_title("Valuation")

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
        if multiples.get("price") is not None:
            rows.append(("Preco Atual (R$)", _fmt_brl(multiples.get("price"))))

        self.set_font("Helvetica", size=10)
        col_a, col_b = 70, 70
        for label, value in rows:
            self.set_font("Helvetica", style="B", size=10)
            self.cell(col_a, 6, label, border="B")
            self.set_font("Helvetica", size=10)
            self.cell(col_b, 6, value, border="B", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def _financials_section(self, ltm: dict) -> None:
        """LTM financials: receita, EBITDA, lucro liquido, FCF, divida liquida."""
        self._section_title("Destaques Financeiros (LTM)")

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
            self.cell(col_b, 6, value, border="B", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def _macro_section(self, macro: dict) -> None:
        """Snapshot das 4 principais series macro (ultimo valor)."""
        self._section_title("Contexto Macroeconomico")

        series_display = [
            ("Selic (% a.a.)", "selic", "{:.2f}%"),
            ("IPCA 12m (%)", "ipca_12m", "{:.2f}%"),
            ("PTAX (R$/USD)", "ptax", "R$ {:.4f}"),
            ("CDS Brasil (bps)", "cds_brasil", "{:.4f}"),
        ]
        self.set_font("Helvetica", size=10)
        col_a, col_b = 70, 70
        for label, key, fmt in series_display:
            series = macro.get(key, [])
            latest = series[-1].get("value") if series else None
            try:
                value_str = fmt.format(latest) if latest is not None else "-"
            except (TypeError, ValueError):
                value_str = "-"
            self.set_font("Helvetica", style="B", size=10)
            self.cell(col_a, 6, label, border="B")
            self.set_font("Helvetica", size=10)
            self.cell(col_b, 6, value_str, border="B", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

    def _disclaimer(self) -> None:
        """Disclaimer obrigatorio CVM IN 598 - sempre ao final do relatorio."""
        self.add_page()
        self._section_title("Aviso Legal")
        self.set_font("Helvetica", style="I", size=8)
        self.set_text_color(107, 114, 128)  # cinza per UI-SPEC.md
        self.multi_cell(0, 4, _CVM_DISCLAIMER)
        self.set_text_color(0, 0, 0)

    # ── API publica ─────────────────────────────────────────────────────────────

    def generate(self, ticker: str, data: dict) -> bytes:
        """Gera relatorio PDF completo para o ticker com dados fornecidos.

        T-05-03: Retorna bytes(self.output()) - nunca escreve em disco (D-17).

        Args:
            ticker: Ticker do ativo (ex: 'PETR4').
            data: Dict com chaves: thesis (dict), dcf (dict), ltm (dict),
                  multiples (dict), macro (dict[str, list[dict]]).

        Returns:
            bytes: Conteudo do PDF (comeca com b'%PDF').
        """
        thesis = data.get("thesis") or {}
        dcf = data.get("dcf") or {}
        ltm = data.get("ltm") or {}
        multiples = data.get("multiples") or {}
        macro = data.get("macro") or {}
        generated_at = data.get("generated_at", "-")

        self._doc_title = f"Relatorio de Investimento - {ticker}"
        self.set_margins(left=20, top=25, right=20)
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()

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
        self._disclaimer()  # sempre ao final

        log.info(f"[pdf_report] relatorio gerado - ticker={ticker}")
        return bytes(self.output())  # em memoria - D-17: sem escrita em disco

    def generate_from_fixture(self, ticker: str) -> bytes:
        """Gera relatorio PDF a partir de dados de fixture (para testes sem banco).

        T-05-03: Retorna bytes - nunca escreve em disco.
        Instancia novo ReportGenerator para evitar reuso apos output() (Pitfall PATTERNS.md).

        Args:
            ticker: Ticker a ser usado no relatorio (ex: 'PETR4').

        Returns:
            bytes: Conteudo do PDF (comeca com b'%PDF').
        """
        # Cria nova instancia para evitar reuso-apos-output() (Pitfall 4)
        fresh = ReportGenerator()
        return fresh.generate(ticker, _FIXTURE)
