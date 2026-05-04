"""
Construtor de planilhas de valuation para bancos grandes brasileiros.
Gera .xlsx com 10 abas: Capa, Premissas, Histórico, DRE Proj, BP Proj,
Drivers, DDM (Gordon 2 estágios), Múltiplos, Sensibilidade, Dashboard.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.chart.label import DataLabelList
from copy import copy

# ============ CORES / STYLES ============
BLUE = Font(name="Arial", color="0000FF", size=10)           # inputs
BLACK = Font(name="Arial", color="000000", size=10)          # formulas
GREEN = Font(name="Arial", color="008000", size=10)          # cross-sheet links
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill("solid", start_color="1F3864")
SUBHEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
SUBHEADER_FILL = PatternFill("solid", start_color="2E75B6")
YELLOW = PatternFill("solid", start_color="FFFF00")          # key assumption
LIGHT_GREY = PatternFill("solid", start_color="F2F2F2")
TOTAL_FILL = PatternFill("solid", start_color="D9E1F2")
NEG_FILL = PatternFill("solid", start_color="FCE4D6")
BOLD = Font(name="Arial", bold=True, size=10)
BOLD_ITALIC = Font(name="Arial", bold=True, italic=True, size=10)
ITALIC = Font(name="Arial", italic=True, color="595959", size=9)

THIN = Side(border_style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

FMT_NUM = '_-* #,##0.0_-;[Red]_-* (#,##0.0)_-;_-* "-"_-;_-@_-'
FMT_NUM0 = '_-* #,##0_-;[Red]_-* (#,##0)_-;_-* "-"_-;_-@_-'
FMT_PCT = '0.0%;[Red](0.0%);"-"'
FMT_MULT = '0.0"x"'
FMT_RS = '"R$ "#,##0.00;[Red]"(R$ "#,##0.00")";"-"'
FMT_YEAR = '0'


def style_header(ws, row, col_start, col_end, title):
    ws.cell(row=row, column=col_start, value=title)
    for c in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="left", vertical="center")


def style_subheader(ws, row, col_start, col_end, title):
    ws.cell(row=row, column=col_start, value=title)
    for c in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = SUBHEADER_FONT
        cell.fill = SUBHEADER_FILL


def set_col_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def put(ws, cell, value, font=None, fmt=None, fill=None, align=None, border=None):
    c = ws[cell]
    c.value = value
    if font: c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if align: c.alignment = align
    if border: c.border = border
    return c


# ============================================================
# DADOS HISTÓRICOS DOS 4 BANCOS (R$ bilhões)
# ============================================================
BANKS = {
    "ITUB4": {
        "nome": "Itaú Unibanco Holding S.A.",
        "cvm": "019348",
        "tipo": "Banco privado — large cap",
        "ticker_b3": "ITUB4",
        "anos": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        # DRE
        "receitas_interm": [193.0, 173.8, 195.7, 283.4, 313.2, 335.3, 387.1],
        "desp_interm":    [-76.0, -73.6, -69.3, -167.8, -188.7, -199.6, -248.2],
        "nii":            [117.1, 100.2, 126.4, 115.6, 124.5, 135.7, 138.9],
        "tarifas":        [39.0, 38.6, 42.0, 46.4, 45.7, 47.1, 47.0],  # 2021 interp
        "pdd":            [-18.3, -24.5, -14.0, -28.1, -31.6, -29.5, -32.6],
        "opex":           [-55.0, -58.0, -62.0, -69.2, -75.8, -79.4, -79.2],  # opex estimado
        "ebt":            [31.2, 5.2, 42.2, 37.5, 39.7, 47.6, 50.2],
        "lucro_liquido":  [27.1, 18.9, 26.8, 29.7, 33.1, 41.1, 44.9],
        # Balanço
        "ativos":         [1637.5, 2019.3, 2069.2, 2323.4, 2543.1, 2854.5, 3066.2],
        "carteira":       [585.8, 714.1, 822.6, 909.4, 910.6, 955.0, 1020.0],  # ajustado (2024/25 pipeline issue)
        "depositos":      [507.1, 809.0, 850.4, 871.4, 951.4, 1054.7, 1114.5],
        "pl":             [136.9, 143.0, 152.9, 168.0, 190.2, 211.1, 204.5],
        # Métricas observadas
        "roe":            [0.198, 0.135, 0.181, 0.185, 0.185, 0.205, 0.216],
        "acoes_mm":       9807,  # 9,8 bi ações totais (ON+PN em tesouraria líquida)
        "preco_atual":    35.50,
        "dividend_yield_hist": 0.065,
        "payout_hist":    0.55,  # 55% típico
        "beta":           0.95,
    },
    "BBAS3": {
        "nome": "Banco do Brasil S.A.",
        "cvm": "001023",
        "tipo": "Banco público federal — large cap",
        "ticker_b3": "BBAS3",
        "anos": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "receitas_interm": [123.1, 98.7, 125.9, 236.5, 265.4, 273.5, 319.5],
        "desp_interm":    [-89.3, -43.2, -66.3, -162.2, -176.7, -169.0, -218.5],
        "nii":            [33.9, 55.4, 59.7, 74.3, 88.7, 104.5, 101.0],
        "tarifas":        [28.0, 27.0, 29.0, 31.5, 33.0, 33.5, 34.0],  # estimado serviços BB
        "pdd":            [-17.0, -14.5, -13.0, -18.0, -27.0, -35.0, -42.0],  # 2020-25 estimado
        "opex":           [-37.0, -39.0, -40.5, -42.0, -44.0, -46.0, -48.5],  # opex estimado incl. pessoal
        "ebt":            [11.1, 11.6, 24.0, 38.3, 41.1, 27.7, 5.6],
        "lucro_liquido":  [16.4, 11.9, 18.3, 27.6, 29.9, 26.4, 13.7],
        "ativos":         [1452.3, 1693.8, 1899.3, 2007.7, 2153.9, 2398.7, 2455.1],
        "carteira":       [579.5, 633.4, 734.3, 832.9, 911.3, 1020.6, 1133.1],
        "depositos":      [485.0, 602.0, 671.3, 753.3, 811.9, 873.7, 897.9],
        "pl":             [107.7, 125.1, 142.8, 159.0, 169.2, 179.6, 189.2],
        "roe":            [0.152, 0.102, 0.137, 0.183, 0.182, 0.151, 0.074],
        "acoes_mm":       5716,
        "preco_atual":    26.80,
        "dividend_yield_hist": 0.095,
        "payout_hist":    0.45,
        "beta":           1.05,
    },
    "BBDC4": {
        "nome": "Banco Bradesco S.A.",
        "cvm": "000906",
        "tipo": "Banco privado — large cap",
        "ticker_b3": "BBDC4",
        "anos": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "receitas_interm": [124.3, 98.4, 125.4, 205.9, 224.5, 213.2, 270.2],
        "desp_interm":    [-58.6, -48.6, -55.1, -131.3, -156.4, -144.3, -193.8],
        "nii":            [65.7, 49.9, 70.3, 74.6, 68.1, 68.9, 76.3],
        "tarifas":        [32.0, 31.0, 33.5, 34.5, 34.8, 35.2, 36.0],
        "pdd":            [-18.0, -24.0, -15.5, -25.0, -36.5, -28.0, -25.0],  # estimado
        "opex":           [-40.5, -44.0, -46.5, -48.0, -50.0, -52.0, -54.0],
        "ebt":            [13.4, 4.1, 32.9, 24.2, 10.2, 16.9, 21.0],
        "lucro_liquido":  [21.0, 15.8, 23.2, 21.0, 14.3, 17.3, 23.7],
        "ativos":         [1378.5, 1604.7, 1675.6, 1799.6, 1927.5, 2069.5, 2330.3],
        "carteira":       [520.0, 540.0, 610.5, 659.7, 625.3, 714.0, 783.8],
        "depositos":      [227.8, 380.0, 575.9, 593.4, 625.8, 648.8, 728.0],
        "pl":             [135.1, 145.6, 149.8, 158.3, 166.3, 168.4, 178.4],
        "roe":            [0.156, 0.113, 0.157, 0.136, 0.088, 0.103, 0.137],
        "acoes_mm":       10704,
        "preco_atual":    15.20,
        "dividend_yield_hist": 0.045,
        "payout_hist":    0.35,
        "beta":           1.10,
    },
    "BPAC11": {
        "nome": "Banco BTG Pactual S.A.",
        "cvm": "022616",
        "tipo": "Banco de investimento — ROE alto, mix fees+NII",
        "ticker_b3": "BPAC11",
        "anos": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "receitas_interm": [11.7, 18.6, 9.9, 22.5, 24.6, 34.7, 28.1],
        "desp_interm":    [-6.9, -12.5, -0.1, -4.7, -2.3, -21.2, -12.0],  # 2025 estimado
        "nii":            [4.8, 6.1, 9.7, 17.9, 22.3, 13.5, 16.1],  # 2025 ajustado (era 28.1 - pipeline issue)
        "tarifas":        [3.5, 4.0, 7.5, 6.5, 7.5, 9.5, 11.0],  # inclui IB + AM + S&T + WM fees (reconciliado com LL real)
        "pdd":            [-0.5, -3.7, -1.5, -2.0, -2.5, -6.5, -4.5],  # custo de crédito estimado
        "opex":           [-1.3, -1.8, -4.6, -8.6, -10.4, -10.6, -10.9],
        "ebt":            [5.1, 5.2, 11.8, 9.6, 11.7, 12.8, 19.3],
        "lucro_liquido":  [4.0, 4.4, 7.2, 7.6, 10.0, 10.7, 16.0],
        "ativos":         [166.3, 244.2, 352.9, 454.1, 495.1, 649.2, 809.3],
        "carteira":       [70.0, 85.0, 93.8, 111.2, 119.8, 155.3, 188.8],  # 2019-2020 estimados
        "depositos":      [45.0, 55.2, 57.9, 87.1, 97.1, 113.8, 201.8],
        "pl":             [21.6, 28.9, 40.6, 44.9, 52.0, 59.7, 73.4],
        "roe":            [0.186, 0.173, 0.207, 0.177, 0.206, 0.192, 0.241],
        "acoes_mm":       2660,  # ~2,66 bi units BPAC11 (após splits)
        "preco_atual":    42.50,  # referência abr/2026
        "dividend_yield_hist": 0.035,
        "payout_hist":    0.45,  # dividendos + JCP + recompras (payout efetivo total ~45-50%)
        "beta":           1.05,  # IB volátil, mas beta maduro ~1.0 pós-IPO (2024-25)
    },
    "SANB11": {
        "nome": "Banco Santander (Brasil) S.A.",
        "cvm": "020532",
        "tipo": "Banco privado (subsidiária do Santander Espanha) — large cap",
        "ticker_b3": "SANB11",
        "anos": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "receitas_interm": [72.8, 62.8, 78.0, 115.2, 128.3, 137.2, 162.5],
        "desp_interm":    [-28.5, -18.3, -26.7, -67.7, -81.4, -80.5, -104.9],
        "nii":            [44.3, 44.4, 51.3, 47.5, 46.9, 56.7, 57.6],
        "tarifas":        [17.5, 17.0, 18.0, 19.5, 20.5, 21.0, 22.0],
        "pdd":            [-14.0, -13.5, -12.0, -14.5, -16.5, -17.5, -17.8],
        "opex":           [-18.0, -19.5, -20.5, -21.5, -22.8, -24.2, -25.5],
        "ebt":            [22.3, 9.7, 24.8, 19.6, 11.9, 19.2, 16.7],
        "lucro_liquido":  [16.4, 13.4, 15.5, 14.3, 9.4, 13.4, 12.8],
        "ativos":         [762.2, 936.2, 931.2, 985.5, 1115.7, 1238.8, 1270.0],
        "carteira":       [370.0, 430.0, 475.0, 510.0, 540.0, 594.8, 615.0],
        "depositos":      [300.0, 370.0, 400.0, 430.0, 470.0, 510.0, 545.0],
        "pl":             [96.7, 105.8, 105.6, 110.2, 114.5, 119.5, 125.2],
        "roe":            [0.170, 0.133, 0.147, 0.132, 0.084, 0.114, 0.104],
        "acoes_mm":       3746,
        "preco_atual":    29.80,
        "dividend_yield_hist": 0.055,
        "payout_hist":    0.50,
        "beta":           1.00,
    },
}


# ============================================================
# CONSTRUÇÃO DO WORKBOOK
# ============================================================
def build_bank_workbook(ticker, data, out_path):
    wb = Workbook()
    # set default font
    # remove default sheet
    wb.remove(wb.active)

    # referências comuns usadas em múltiplas abas
    n_hist = len(data["anos"])
    ativos_hist_last_col = get_column_letter(3 + n_hist - 1)  # col do último ano hist (2025 → 'I')

    # cria abas na ordem
    capa = wb.create_sheet("1.Capa")
    premi = wb.create_sheet("2.Premissas")
    hist = wb.create_sheet("3.Historico")
    drivers = wb.create_sheet("4.Drivers")
    dre_p = wb.create_sheet("5.DRE_Proj")
    bp_p = wb.create_sheet("6.BP_Proj")
    ddm = wb.create_sheet("7.DDM_Valuation")
    mult = wb.create_sheet("8.Multiplos")
    sens = wb.create_sheet("9.Sensibilidade")
    dash = wb.create_sheet("10.Dashboard")

    # ---------------------- 1. CAPA ----------------------
    set_col_widths(capa, [3, 28, 55, 18, 18, 3])
    capa.sheet_view.showGridLines = False
    put(capa, "B2", f"{ticker} — Modelo de Valuation", Font(name="Arial", bold=True, size=22, color="1F3864"))
    put(capa, "B3", data["nome"], Font(name="Arial", italic=True, size=13, color="595959"))
    put(capa, "B4", f"Tipo: {data['tipo']}  |  CVM: {data['cvm']}  |  Data-base: 2025-12-31", ITALIC)
    put(capa, "B6", "Sumário Executivo", Font(name="Arial", bold=True, size=14, color="1F3864"))
    capa.row_dimensions[6].height = 22

    capa["B7"] = "Preço atual (R$)"
    capa["C7"] = data["preco_atual"]; capa["C7"].font = BLUE; capa["C7"].number_format = FMT_RS; capa["C7"].fill = YELLOW
    capa["B8"] = "Preço-alvo DDM (R$/ação)"
    capa["C8"] = "='7.DDM_Valuation'!C35"; capa["C8"].font = GREEN; capa["C8"].number_format = FMT_RS
    capa["B9"] = "Upside / (Downside)"
    capa["C9"] = "=IFERROR(C8/C7-1,0)"; capa["C9"].font = BLACK; capa["C9"].number_format = FMT_PCT
    capa["B10"] = "Recomendação"
    capa["C10"] = '=IF(C9>0.15,"COMPRA",IF(C9>0.05,"NEUTRO +",IF(C9>-0.05,"NEUTRO",IF(C9>-0.15,"NEUTRO -","VENDA"))))'
    capa["C10"].font = Font(name="Arial", bold=True, color="1F3864", size=11)

    capa["B12"] = "Navegação"
    capa["B12"].font = Font(name="Arial", bold=True, size=12, color="1F3864")
    navs = [
        ("2.Premissas", "Inputs macro, CAPM, cenários"),
        ("3.Historico", "DRE e BP 2019-2025"),
        ("4.Drivers", "NIM, crescimento carteira, custo crédito, eficiência"),
        ("5.DRE_Proj", "Projeção 2026-2030 + Terminal"),
        ("6.BP_Proj", "Balanço Patrimonial projetado"),
        ("7.DDM_Valuation", "Modelo Gordon 2 estágios"),
        ("8.Multiplos", "P/L, P/VP, EV/Receita histórico"),
        ("9.Sensibilidade", "Tabela Ke × g terminal"),
        ("10.Dashboard", "KPIs e visualização"),
    ]
    r = 13
    for aba, desc in navs:
        capa.cell(row=r, column=2, value=aba).font = Font(name="Arial", color="1F3864", underline="single", size=10)
        capa.cell(row=r, column=3, value=desc).font = ITALIC
        capa.cell(row=r, column=2).hyperlink = f"#'{aba}'!A1"
        r += 1

    put(capa, "B24", "Premissas-chave (resumo)", Font(name="Arial", bold=True, size=12, color="1F3864"))
    keys = [
        ("Rf — Taxa livre de risco (nominal)", "='2.Premissas'!C7"),
        ("ERP — Prêmio de risco Brasil", "='2.Premissas'!C8"),
        ("Beta alavancado", "='2.Premissas'!C9"),
        ("Ke — Custo de equity (CAPM)", "='2.Premissas'!C11"),
        ("g — Crescimento terminal", "='2.Premissas'!C13"),
        ("Payout projetado", "='2.Premissas'!C19"),
        ("ROE sustentável (steady state)", "='2.Premissas'!C20"),
    ]
    for i, (label, formula) in enumerate(keys):
        capa.cell(row=25+i, column=2, value=label)
        c = capa.cell(row=25+i, column=3, value=formula)
        c.font = GREEN
        c.number_format = FMT_PCT if "g" in label or "ROE" in label or "Payout" in label or "Ke" in label or "Rf" in label or "ERP" in label else FMT_NUM
        if "Beta" in label:
            c.number_format = '0.00'

    put(capa, "B34", "Legenda de cores", Font(name="Arial", bold=True, size=11, color="1F3864"))
    put(capa, "B35", "Input (hardcode)", BLUE)
    put(capa, "B36", "Fórmula / cálculo", BLACK)
    put(capa, "B37", "Link cross-sheet", GREEN)
    put(capa, "B38", "Premissa-chave", Font(name="Arial", size=10)); capa["B38"].fill = YELLOW

    # ---------------------- 2. PREMISSAS ----------------------
    set_col_widths(premi, [3, 42, 16, 16, 16, 16, 16, 3])
    premi.sheet_view.showGridLines = False
    style_header(premi, 2, 2, 7, f"Premissas — {ticker}")

    # Macro / CAPM
    put(premi, "B5", "1. Macroeconomia e Custo de Capital", Font(name="Arial", bold=True, size=12, color="1F3864"))
    put(premi, "B6", "Item"); put(premi, "C6", "Valor"); put(premi, "D6", "Unidade"); put(premi, "E6", "Fonte / Comentário")
    for c in "BCDE": premi[f"{c}6"].font = SUBHEADER_FONT; premi[f"{c}6"].fill = SUBHEADER_FILL

    capm_rows = [
        ("Rf — Selic longa proxy (NTN-B)",  0.1150, FMT_PCT, "Tesouro Direto — IPCA+2035"),
        ("ERP — Equity Risk Premium Brasil", 0.0650, FMT_PCT, "Damodaran 2025 — BR"),
        ("Beta alavancado (5y)",             data["beta"], '0.00', "Regressão IBOV 60m"),
        ("Risco-país (informativo — já embutido no ERP_BR)", 0.0200, FMT_PCT, "EMBI+ Brasil — referência"),
        ("Ke — Custo de Equity (CAPM)",       "=C7+C9*C8", FMT_PCT, "Rf_BR + β·ERP_BR (CRP já embutido)"),
        ("Inflação média projetada",         0.0350, FMT_PCT, "BCB Focus 2026-2030"),
        ("g — Crescimento terminal (nominal)", 0.0500, FMT_PCT, "Inflação + real 1,5%"),
        ("Alíquota IR/CSLL efetiva",         0.3500, FMT_PCT, "CSLL 20% + IR 25% — bancos"),
    ]
    r = 7
    for label, val, fmt, src in capm_rows:
        premi.cell(row=r, column=2, value=label)
        c = premi.cell(row=r, column=3, value=val)
        if isinstance(val, str) and val.startswith("="): c.font = BLACK
        else: c.font = BLUE
        if label.startswith("Ke"): c.font = BLACK; c.fill = YELLOW
        if label.startswith("g "): c.fill = YELLOW
        c.number_format = fmt
        premi.cell(row=r, column=4, value="% a.a." if fmt == FMT_PCT else "×").font = ITALIC
        premi.cell(row=r, column=5, value=src).font = ITALIC
        r += 1

    # Políticas de Capital e Payout
    put(premi, "B16", "2. Política de Capital e Distribuição", Font(name="Arial", bold=True, size=12, color="1F3864"))
    put(premi, "B17", "Item"); put(premi, "C17", "Valor"); put(premi, "D17", "Unidade"); put(premi, "E17", "Comentário")
    for c in "BCDE": premi[f"{c}17"].font = SUBHEADER_FONT; premi[f"{c}17"].fill = SUBHEADER_FILL

    policy = [
        ("Índice de Basileia alvo", 0.145, FMT_PCT, "Req. mínimo 10,5% + buffer"),
        ("Payout ratio projetado", data["payout_hist"], FMT_PCT, "Histórico recente"),
        ("ROE sustentável (steady state)",
         {"ITUB4": 0.170, "BBAS3": 0.150, "BBDC4": 0.140, "SANB11": 0.130, "BPAC11": 0.230}.get(ticker, 0.150),
         FMT_PCT, "Convergência gradual"),
        ("Ações em circulação (milhões)", data["acoes_mm"], FMT_NUM0, "Totais ON+PN / Units"),
    ]
    r = 18
    for label, val, fmt, src in policy:
        premi.cell(row=r, column=2, value=label)
        c = premi.cell(row=r, column=3, value=val)
        c.font = BLUE
        c.number_format = fmt
        if "Payout" in label or "ROE" in label: c.fill = YELLOW
        premi.cell(row=r, column=5, value=src).font = ITALIC
        r += 1

    # Cenário de projeção (anual)
    put(premi, "B23", "3. Cenário de Projeção (2026E–2030E)", Font(name="Arial", bold=True, size=12, color="1F3864"))
    put(premi, "B24", "Driver");
    years_proj = [2026, 2027, 2028, 2029, 2030]
    for i, y in enumerate(years_proj):
        premi.cell(row=24, column=3+i, value=y).font = SUBHEADER_FONT
        premi.cell(row=24, column=3+i).fill = SUBHEADER_FILL
        premi.cell(row=24, column=3+i).alignment = Alignment(horizontal="center")
    premi["B24"].font = SUBHEADER_FONT; premi["B24"].fill = SUBHEADER_FILL

    # cresc carteira, NIM, custo crédito, tarifas yoy, opex yoy
    scen_rows = [
        ("Crescimento da carteira de crédito (YoY)",
         {"BBAS3":  [0.090, 0.090, 0.085, 0.080, 0.075],
          "ITUB4":  [0.075, 0.080, 0.080, 0.075, 0.070],
          "BBDC4":  [0.080, 0.080, 0.075, 0.070, 0.065],
          "SANB11": [0.060, 0.065, 0.065, 0.060, 0.060],
          "BPAC11": [0.160, 0.140, 0.120, 0.110, 0.100]}.get(ticker), FMT_PCT),
        ("NIM — Margem financeira / ativos rentáveis",
         {"ITUB4":  [0.052, 0.052, 0.053, 0.053, 0.053],
          "BBAS3":  [0.044, 0.045, 0.045, 0.046, 0.046],
          "BBDC4":  [0.040, 0.041, 0.041, 0.042, 0.042],
          "SANB11": [0.048, 0.048, 0.048, 0.049, 0.049],
          "BPAC11": [0.050, 0.052, 0.053, 0.054, 0.054]}.get(ticker), FMT_PCT),
        ("Custo do crédito (PDD / carteira)",
         {"ITUB4":  [0.032, 0.030, 0.028, 0.028, 0.028],
          "BBAS3":  [0.035, 0.033, 0.031, 0.030, 0.029],
          "BBDC4":  [0.040, 0.037, 0.034, 0.032, 0.031],
          "SANB11": [0.030, 0.029, 0.029, 0.028, 0.028],
          "BPAC11": [0.025, 0.024, 0.023, 0.023, 0.023]}.get(ticker), FMT_PCT),
        ("Crescimento receitas de serviços (YoY)",
         [0.220, 0.200, 0.180, 0.150, 0.120] if ticker == "BPAC11" else
         [0.070, 0.070, 0.065, 0.060, 0.060], FMT_PCT),
        ("Crescimento OPEX (YoY)",
         [0.080, 0.080, 0.075, 0.070, 0.065] if ticker == "BPAC11" else
         [0.055, 0.055, 0.055, 0.050, 0.050], FMT_PCT),
        ("Índice de Eficiência (OPEX / Receitas)",
         {"ITUB4":  [0.42, 0.41, 0.40, 0.40, 0.40],
          "BBAS3":  [0.45, 0.44, 0.43, 0.43, 0.43],
          "BBDC4":  [0.48, 0.47, 0.46, 0.45, 0.45],
          "SANB11": [0.43, 0.42, 0.42, 0.41, 0.41],
          "BPAC11": [0.55, 0.54, 0.53, 0.52, 0.52]}.get(ticker), FMT_PCT),
    ]
    r = 25
    for label, vals, fmt in scen_rows:
        premi.cell(row=r, column=2, value=label).font = BOLD
        for i, v in enumerate(vals):
            c = premi.cell(row=r, column=3+i, value=v)
            c.font = BLUE
            c.number_format = fmt
        r += 1

    put(premi, "B32", "Notas: valores em R$ bi quando não indicado. Cenário base.", ITALIC)

    # ---------------------- 3. HISTÓRICO ----------------------
    set_col_widths(hist, [3, 42] + [14]*7 + [3])
    hist.sheet_view.showGridLines = False
    style_header(hist, 2, 2, 9, f"Histórico — {ticker} (R$ bilhões)")
    # years headers
    hist.cell(row=4, column=2, value="Linha").font = SUBHEADER_FONT; hist.cell(row=4, column=2).fill = SUBHEADER_FILL
    for i, y in enumerate(data["anos"]):
        c = hist.cell(row=4, column=3+i, value=y)
        c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_YEAR
        c.alignment = Alignment(horizontal="center")

    # DRE
    put(hist, "B6", "DRE", Font(name="Arial", bold=True, color="1F3864", size=11))
    dre_lines = [
        ("Receitas de Intermediação Financeira", "receitas_interm", FMT_NUM),
        ("(-) Despesas de Intermediação Financeira", "desp_interm", FMT_NUM),
        ("Margem Financeira Bruta (NII)", "nii", FMT_NUM),
        ("Receitas de Serviços / Tarifas", "tarifas", FMT_NUM),
        ("(-) PDD / Provisão para créditos", "pdd", FMT_NUM),
        ("(-) Despesas Administrativas (OPEX)", "opex", FMT_NUM),
        ("Lucro Antes de IR (EBT)", "ebt", FMT_NUM),
        ("Lucro Líquido", "lucro_liquido", FMT_NUM),
    ]
    r = 7
    for label, key, fmt in dre_lines:
        hist.cell(row=r, column=2, value=label)
        is_bold = "NII" in label or "Lucro" in label
        if is_bold:
            hist.cell(row=r, column=2).font = BOLD
        for i, v in enumerate(data[key]):
            c = hist.cell(row=r, column=3+i, value=v)
            c.font = BLUE
            c.number_format = fmt
            if is_bold:
                c.fill = TOTAL_FILL
                c.font = Font(name="Arial", color="0000FF", bold=True, size=10)
        r += 1

    # BP
    r += 1
    hist.cell(row=r, column=2, value="Balanço Patrimonial").font = Font(name="Arial", bold=True, color="1F3864", size=11)
    r += 1
    bp_lines = [
        ("Ativo Total", "ativos", FMT_NUM),
        ("Carteira de Crédito", "carteira", FMT_NUM),
        ("Depósitos", "depositos", FMT_NUM),
        ("Patrimônio Líquido", "pl", FMT_NUM),
    ]
    for label, key, fmt in bp_lines:
        hist.cell(row=r, column=2, value=label)
        if "Patrimônio" in label: hist.cell(row=r, column=2).font = BOLD
        for i, v in enumerate(data[key]):
            c = hist.cell(row=r, column=3+i, value=v)
            c.font = BLUE
            c.number_format = fmt
            if "Patrimônio" in label:
                c.fill = TOTAL_FILL
                c.font = Font(name="Arial", color="0000FF", bold=True, size=10)
        r += 1

    # Indicadores
    r += 1
    hist.cell(row=r, column=2, value="Indicadores Calculados").font = Font(name="Arial", bold=True, color="1F3864", size=11)
    r += 1
    # ROE = LL / ((PL_t + PL_t-1)/2); primeiro ano usa só PL do ano
    # ROA = LL / ((At + At-1)/2)
    # NIM = NII / ((At + At-1)/2)
    # Efic = -OPEX / (NII + tarifas)
    # Custo crédito = -PDD / carteira
    # Margem líq = LL / rec. interm
    # Payout (not available in hist - simplified)
    n = len(data["anos"])
    first_col = 3  # C

    # mapear linhas do hist para referência
    # ROE: row_roe -> precisamos da linha do PL (row_pl) e do LL (row_ll)
    # Conforme ordem acima:
    # row 7 = receitas_interm; 8 = desp_interm; 9 = NII; 10 = tarifas; 11 = pdd;
    # 12 = opex; 13 = ebt; 14 = lucro_liquido; 16 = blank (skip line)
    # header "Balanço" at r=16, next r=17 ativos, 18 carteira, 19 depositos, 20 PL

    row_rec = 7; row_nii = 9; row_tarifas = 10; row_pdd = 11; row_opex = 12; row_ll = 14
    row_ativos = 17; row_carteira = 18; row_pl = 20

    ind_specs = [
        ("Margem Líquida (LL / Receitas)", row_ll, row_rec, FMT_PCT, "div"),
        ("NIM (NII / Ativos médios)",       row_nii, row_ativos, FMT_PCT, "nim"),
        ("ROE (LL / PL médio)",             row_ll, row_pl, FMT_PCT, "avg"),
        ("ROA (LL / Ativos médios)",        row_ll, row_ativos, FMT_PCT, "avg"),
        ("Custo do Crédito (-PDD/Carteira)", row_pdd, row_carteira, FMT_PCT, "custo"),
        ("Índice de Eficiência (-OPEX/(NII+Tarifas))", row_opex, None, FMT_PCT, "efic"),
        ("Alavancagem (Ativos/PL)",         row_ativos, row_pl, FMT_MULT, "lev"),
        ("Crescimento Carteira (YoY)",      row_carteira, None, FMT_PCT, "yoy"),
        ("Crescimento LL (YoY)",            row_ll, None, FMT_PCT, "yoy"),
    ]
    for label, row_a, row_b, fmt, kind in ind_specs:
        hist.cell(row=r, column=2, value=label)
        for i in range(n):
            col = get_column_letter(first_col + i)
            prev = get_column_letter(first_col + i - 1) if i > 0 else None
            if kind == "div":
                f = f"=IFERROR({col}{row_a}/{col}{row_b},0)"
            elif kind == "custo":
                # -PDD/Carteira (PDD é negativo) -> -PDD => positivo
                f = f"=IFERROR(-{col}{row_a}/{col}{row_b},0)"
            elif kind == "nim":
                if prev:
                    f = f"=IFERROR({col}{row_nii}/(({col}{row_ativos}+{prev}{row_ativos})/2),0)"
                else:
                    f = f"=IFERROR({col}{row_nii}/{col}{row_ativos},0)"
            elif kind == "avg":
                if prev:
                    f = f"=IFERROR({col}{row_a}/(({col}{row_b}+{prev}{row_b})/2),0)"
                else:
                    f = f"=IFERROR({col}{row_a}/{col}{row_b},0)"
            elif kind == "efic":
                # -opex / (nii + tarifas)
                f = f"=IFERROR(-{col}{row_opex}/({col}{row_nii}+{col}{row_tarifas}),0)"
            elif kind == "lev":
                f = f"=IFERROR({col}{row_a}/{col}{row_b},0)"
            elif kind == "yoy":
                if prev:
                    f = f"=IFERROR({col}{row_a}/{prev}{row_a}-1,0)"
                else:
                    f = "=\"-\""
            c = hist.cell(row=r, column=first_col + i, value=f)
            c.font = BLACK
            c.number_format = fmt
        r += 1

    # ---------------------- 4. DRIVERS ----------------------
    set_col_widths(drivers, [3, 42] + [14]*10 + [3])
    drivers.sheet_view.showGridLines = False
    style_header(drivers, 2, 2, 12, "Drivers — Histórico + Projeção")

    # headers (7 hist + 5 proj)
    drivers.cell(row=4, column=2, value="Driver").font = SUBHEADER_FONT
    drivers.cell(row=4, column=2).fill = SUBHEADER_FILL
    all_years = data["anos"] + [2026, 2027, 2028, 2029, 2030]
    for i, y in enumerate(all_years):
        c = drivers.cell(row=4, column=3+i, value=y)
        c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_YEAR
        c.alignment = Alignment(horizontal="center")
        if y >= 2026:
            c.fill = PatternFill("solid", start_color="1F3864")

    # drivers rows (link histórico + projeção das premissas)
    # Linha 6: Carteira (niveis)
    drivers.cell(row=6, column=2, value="Carteira de Crédito (R$ bi)").font = BOLD
    for i, y in enumerate(data["anos"]):
        col = get_column_letter(3+i)
        f = f"='3.Historico'!{col}{row_carteira}"
        c = drivers.cell(row=6, column=3+i, value=f)
        c.font = GREEN; c.number_format = FMT_NUM
    # projeção carteira: carteira_t = carteira_t-1 * (1 + g)
    for i in range(5):
        col_proj = get_column_letter(3 + len(data["anos"]) + i)
        col_prev = get_column_letter(3 + len(data["anos"]) + i - 1)
        col_prem = get_column_letter(3 + i)  # C-G na premi
        f = f"={col_prev}6*(1+'2.Premissas'!{col_prem}25)"
        c = drivers.cell(row=6, column=3 + len(data["anos"]) + i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM

    # Linha 7: NIM (hist calculado a partir de 3.Historico, proj = premissa)
    drivers.cell(row=7, column=2, value="NIM (%)").font = BOLD
    for i, y in enumerate(data["anos"]):
        col = get_column_letter(3+i); prev = get_column_letter(2+i)
        if i == 0:
            f = f"='3.Historico'!{col}{row_nii}/'3.Historico'!{col}{row_ativos}"
        else:
            f = f"='3.Historico'!{col}{row_nii}/(('3.Historico'!{col}{row_ativos}+'3.Historico'!{prev}{row_ativos})/2)"
        c = drivers.cell(row=7, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT
    for i in range(5):
        col_prem = get_column_letter(3 + i)
        f = f"='2.Premissas'!{col_prem}26"
        c = drivers.cell(row=7, column=3 + len(data["anos"]) + i, value=f)
        c.font = GREEN; c.number_format = FMT_PCT

    # Linha 8: Custo do crédito (% Carteira)
    drivers.cell(row=8, column=2, value="Custo do Crédito (PDD/Carteira)").font = BOLD
    for i, y in enumerate(data["anos"]):
        col = get_column_letter(3+i)
        f = f"=-'3.Historico'!{col}{row_pdd}/'3.Historico'!{col}{row_carteira}"
        c = drivers.cell(row=8, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT
    for i in range(5):
        col_prem = get_column_letter(3 + i)
        f = f"='2.Premissas'!{col_prem}27"
        c = drivers.cell(row=8, column=3 + len(data["anos"]) + i, value=f)
        c.font = GREEN; c.number_format = FMT_PCT

    # Linha 9: Crescimento OPEX
    drivers.cell(row=9, column=2, value="Crescimento OPEX YoY").font = BOLD
    for i in range(1, len(data["anos"])):
        col = get_column_letter(3+i); prev = get_column_letter(2+i)
        f = f"='3.Historico'!{col}{row_opex}/'3.Historico'!{prev}{row_opex}-1"
        c = drivers.cell(row=9, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT
    for i in range(5):
        col_prem = get_column_letter(3 + i)
        f = f"='2.Premissas'!{col_prem}29"
        c = drivers.cell(row=9, column=3 + len(data["anos"]) + i, value=f)
        c.font = GREEN; c.number_format = FMT_PCT

    # Linha 10: ROE
    drivers.cell(row=10, column=2, value="ROE").font = BOLD
    for i, y in enumerate(data["anos"]):
        col = get_column_letter(3+i); prev = get_column_letter(2+i)
        if i == 0:
            f = f"='3.Historico'!{col}{row_ll}/'3.Historico'!{col}{row_pl}"
        else:
            f = f"='3.Historico'!{col}{row_ll}/(('3.Historico'!{col}{row_pl}+'3.Historico'!{prev}{row_pl})/2)"
        c = drivers.cell(row=10, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT
    # ROE projetado = LL proj / PL médio
    # Para 2026 (i=0): PL_prev vem do histórico (3.Historico!I20)
    for i in range(5):
        col_cur = get_column_letter(3+i)
        col_prev = get_column_letter(2+i)
        if i == 0:
            # PL_prev = último ano histórico (2025) em 3.Historico!I20
            f = (f"=IFERROR('5.DRE_Proj'!{col_cur}18/"
                 f"(('6.BP_Proj'!{col_cur}17+'3.Historico'!{ativos_hist_last_col}{row_pl})/2),0)")
        else:
            f = (f"=IFERROR('5.DRE_Proj'!{col_cur}18/"
                 f"(('6.BP_Proj'!{col_cur}17+'6.BP_Proj'!{col_prev}17)/2),0)")
        c = drivers.cell(row=10, column=3 + len(data["anos"]) + i, value=f)
        c.font = GREEN; c.number_format = FMT_PCT

    # Linha 11: Índice de Eficiência
    drivers.cell(row=11, column=2, value="Índice de Eficiência").font = BOLD
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"=-'3.Historico'!{col}{row_opex}/('3.Historico'!{col}{row_nii}+'3.Historico'!{col}{row_tarifas})"
        c = drivers.cell(row=11, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT
    for i in range(5):
        col_prem = get_column_letter(3 + i)
        f = f"='2.Premissas'!{col_prem}30"
        c = drivers.cell(row=11, column=3 + len(data["anos"]) + i, value=f)
        c.font = GREEN; c.number_format = FMT_PCT

    # ---------------------- 5. DRE PROJETADA ----------------------
    set_col_widths(dre_p, [3, 42] + [14]*6 + [3])  # 5 anos + terminal
    dre_p.sheet_view.showGridLines = False
    style_header(dre_p, 2, 2, 9, f"DRE Projetada — {ticker} (R$ bi)")

    dre_p.cell(row=4, column=2, value="Linha").font = SUBHEADER_FONT
    dre_p.cell(row=4, column=2).fill = SUBHEADER_FILL
    proj_years = [2026, 2027, 2028, 2029, 2030, "Terminal"]
    for i, y in enumerate(proj_years):
        c = dre_p.cell(row=4, column=3+i, value=y)
        c.font = SUBHEADER_FONT
        c.fill = PatternFill("solid", start_color="1F3864")
        c.number_format = FMT_YEAR if isinstance(y, int) else '@'
        c.alignment = Alignment(horizontal="center")

    # Linha 6: Ativos rentáveis (≈ Ativo Total do ano anterior + growth)
    # estimamos ativos totais crescem na mesma proporção da carteira
    # Ativos_t = Ativos_t-1 * (1 + g_carteira)
    dre_p.cell(row=6, column=2, value="Ativos Totais médios (R$ bi)").font = ITALIC
    # 2026: (ativos_2025 + ativos_2026)/2, mas usamos link ao BP_Proj depois. Por ora, usar 3.Historico
    # valores de ativos projetados serão calculados direto no BP_Proj
    # aqui usamos =('6.BP_Proj'!col17 + '6.BP_Proj'!col_prev17)/2
    # Para 2026 col_prev = 3.Historico último ano (ativos_hist_last_col já definido no topo)
    for i in range(5):
        col = get_column_letter(3+i)
        prev_col = get_column_letter(2+i) if i > 0 else None
        if i == 0:
            f = f"=('6.BP_Proj'!{col}5+'3.Historico'!{ativos_hist_last_col}{row_ativos})/2"
        else:
            f = f"=('6.BP_Proj'!{col}5+'6.BP_Proj'!{prev_col}5)/2"
        c = dre_p.cell(row=6, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    # Terminal: usa ativos 2030 * (1+g)/(1+g_carteira2030) ≈ estável
    c = dre_p.cell(row=6, column=8, value="=G6*(1+'2.Premissas'!C13)/(1+'2.Premissas'!G25)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 7: NII = Ativos médios × NIM
    dre_p.cell(row=7, column=2, value="Margem Financeira Bruta (NII)").font = BOLD
    for i in range(5):
        col = get_column_letter(3+i); col_prem = get_column_letter(3+i)
        f = f"={col}6*'2.Premissas'!{col_prem}26"
        c = dre_p.cell(row=7, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    # Terminal: usa NIM 2030
    c = dre_p.cell(row=7, column=8, value="=H6*'2.Premissas'!G26")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 8: Receitas de Serviços
    dre_p.cell(row=8, column=2, value="(+) Receitas de Serviços / Tarifas").font = BLACK
    # 2026 = tarifas_2025 * (1 + g_2026)
    tarifas_2025 = f"'3.Historico'!{ativos_hist_last_col}{row_tarifas}"
    for i in range(5):
        col_prem = get_column_letter(3+i)
        if i == 0:
            f = f"={tarifas_2025}*(1+'2.Premissas'!{col_prem}28)"
        else:
            prev_col = get_column_letter(2+i)
            f = f"={prev_col}8*(1+'2.Premissas'!{col_prem}28)"
        c = dre_p.cell(row=8, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    # Terminal: tarifas crescem a g
    c = dre_p.cell(row=8, column=8, value="=G8*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 9: PDD = -Custo_Credito × Carteira_Média (vamos simplificar -> Carteira_t)
    dre_p.cell(row=9, column=2, value="(-) PDD / Custo do Crédito").font = BLACK
    # Carteira projetada está em drivers linha 6, colunas 3+len(anos) até 3+len(anos)+4
    offset_proj = len(data["anos"])  # 7
    for i in range(5):
        col_drv = get_column_letter(3 + offset_proj + i)  # carteira proj em drivers!J..N
        col_prem = get_column_letter(3+i)
        f = f"=-'4.Drivers'!{col_drv}6*'2.Premissas'!{col_prem}27"
        c = dre_p.cell(row=9, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    c = dre_p.cell(row=9, column=8, value="=G9*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 10: Receita Total Operacional (NII + Tarifas - PDD é líquido, mas no gerencial: NII + Tarifas)
    dre_p.cell(row=10, column=2, value="Receita Operacional (NII + Serviços)").font = BOLD_ITALIC
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}7+{col}8"
        c = dre_p.cell(row=10, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM; c.fill = LIGHT_GREY

    # Linha 11: OPEX = - Receita Operacional × Eficiência
    dre_p.cell(row=11, column=2, value="(-) Despesas Administrativas (OPEX)").font = BLACK
    for i in range(5):
        col = get_column_letter(3+i); col_prem = get_column_letter(3+i)
        f = f"=-{col}10*'2.Premissas'!{col_prem}30"
        c = dre_p.cell(row=11, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    c = dre_p.cell(row=11, column=8, value="=-H10*'2.Premissas'!G30")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 13: Resultado Operacional Pré-Impostos = NII + Tarifas + PDD + OPEX
    dre_p.cell(row=13, column=2, value="Resultado Operacional antes de IR").font = BOLD
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}7+{col}8+{col}9+{col}11"
        c = dre_p.cell(row=13, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM; c.fill = TOTAL_FILL
        c.font = Font(name="Arial", bold=True, size=10)

    # Linha 14: Outros resultados (zeramos)
    dre_p.cell(row=14, column=2, value="(+/-) Outras receitas/despesas (não recorrentes)").font = ITALIC
    for i in range(6):
        c = dre_p.cell(row=14, column=3+i, value=0)
        c.font = BLUE; c.number_format = FMT_NUM

    # Linha 15: EBT
    dre_p.cell(row=15, column=2, value="Lucro Antes de IR (EBT)").font = BOLD
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}13+{col}14"
        c = dre_p.cell(row=15, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM; c.fill = LIGHT_GREY

    # Linha 16: IR
    dre_p.cell(row=16, column=2, value="(-) IR/CSLL").font = BLACK
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"=-{col}15*'2.Premissas'!$C$14"
        c = dre_p.cell(row=16, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM

    # Linha 18: Lucro Líquido
    dre_p.cell(row=18, column=2, value="LUCRO LÍQUIDO").font = Font(name="Arial", bold=True, size=11, color="1F3864")
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}15+{col}16"
        c = dre_p.cell(row=18, column=3+i, value=f)
        c.font = Font(name="Arial", bold=True, size=11, color="1F3864")
        c.number_format = FMT_NUM
        c.fill = TOTAL_FILL

    # Linha 20: Dividendos (= LL × Payout)
    dre_p.cell(row=20, column=2, value="Dividendos Distribuídos").font = BOLD_ITALIC
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}18*'2.Premissas'!$C$19"
        c = dre_p.cell(row=20, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM

    # Linha 21: Lucro retido
    dre_p.cell(row=21, column=2, value="Lucro Retido").font = ITALIC
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}18-{col}20"
        c = dre_p.cell(row=21, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM

    # ---------------------- 6. BP PROJETADO ----------------------
    set_col_widths(bp_p, [3, 42] + [14]*6 + [3])
    bp_p.sheet_view.showGridLines = False
    style_header(bp_p, 2, 2, 9, f"Balanço Patrimonial Projetado — {ticker} (R$ bi)")

    bp_p.cell(row=4, column=2, value="Linha").font = SUBHEADER_FONT
    bp_p.cell(row=4, column=2).fill = SUBHEADER_FILL
    for i, y in enumerate(proj_years):
        c = bp_p.cell(row=4, column=3+i, value=y)
        c.font = SUBHEADER_FONT
        c.fill = PatternFill("solid", start_color="1F3864")
        c.number_format = FMT_YEAR if isinstance(y, int) else '@'
        c.alignment = Alignment(horizontal="center")

    # Linha 5: Ativos totais
    bp_p.cell(row=5, column=2, value="Ativo Total").font = BOLD
    # 2026: Ativos_2025 × (1 + g_carteira_2026)
    for i in range(5):
        col_prem = get_column_letter(3+i)
        if i == 0:
            f = f"='3.Historico'!{ativos_hist_last_col}{row_ativos}*(1+'2.Premissas'!{col_prem}25)"
        else:
            prev_col = get_column_letter(2+i)
            f = f"={prev_col}5*(1+'2.Premissas'!{col_prem}25)"
        c = bp_p.cell(row=5, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    # Terminal: cresce a g
    c = bp_p.cell(row=5, column=8, value="=G5*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 6: Carteira de Crédito (= drivers!row6 proj)
    bp_p.cell(row=6, column=2, value="Carteira de Crédito").font = BLACK
    for i in range(5):
        col_drv = get_column_letter(3 + offset_proj + i)
        f = f"='4.Drivers'!{col_drv}6"
        c = bp_p.cell(row=6, column=3+i, value=f)
        c.font = GREEN; c.number_format = FMT_NUM
    c = bp_p.cell(row=6, column=8, value="=G6*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 7: Depósitos
    depositos_2025 = f"'3.Historico'!{ativos_hist_last_col}19"  # row 19
    bp_p.cell(row=7, column=2, value="Depósitos").font = BLACK
    for i in range(5):
        col_prem = get_column_letter(3+i)
        if i == 0:
            f = f"={depositos_2025}*(1+'2.Premissas'!{col_prem}25)"
        else:
            prev_col = get_column_letter(2+i)
            f = f"={prev_col}7*(1+'2.Premissas'!{col_prem}25)"
        c = bp_p.cell(row=7, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM
    c = bp_p.cell(row=7, column=8, value="=G7*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM

    # Linha 17: Patrimônio Líquido
    bp_p.cell(row=17, column=2, value="Patrimônio Líquido").font = Font(name="Arial", bold=True, size=11, color="1F3864")
    pl_2025 = f"'3.Historico'!{ativos_hist_last_col}{row_pl}"
    # PL_t = PL_t-1 + Lucro Retido_t
    for i in range(5):
        col_dre = get_column_letter(3+i)
        if i == 0:
            f = f"={pl_2025}+'5.DRE_Proj'!{col_dre}21"
        else:
            prev_col = get_column_letter(2+i)
            f = f"={prev_col}17+'5.DRE_Proj'!{col_dre}21"
        c = bp_p.cell(row=17, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM; c.fill = TOTAL_FILL
    # Terminal: PL cresce a g (estado estacionário)
    c = bp_p.cell(row=17, column=8, value="=G17*(1+'2.Premissas'!C13)")
    c.font = BLACK; c.number_format = FMT_NUM; c.fill = TOTAL_FILL

    # Linha 19: Alavancagem
    bp_p.cell(row=19, column=2, value="Alavancagem (Ativos / PL)").font = ITALIC
    for i in range(6):
        col = get_column_letter(3+i)
        f = f"={col}5/{col}17"
        c = bp_p.cell(row=19, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_MULT

    # ---------------------- 7. DDM VALUATION ----------------------
    set_col_widths(ddm, [3, 42, 16, 16, 16, 16, 16, 3])
    ddm.sheet_view.showGridLines = False
    style_header(ddm, 2, 2, 8, f"DDM — Modelo de Gordon 2 Estágios ({ticker})")

    # Step 1: Fluxos de dividendos projetados
    put(ddm, "B5", "Estágio 1 — Dividendos explícitos 2026-2030", Font(name="Arial", bold=True, size=12, color="1F3864"))

    put(ddm, "B7", "Ano"); put(ddm, "C7", "Dividendos (R$ bi)"); put(ddm, "D7", "Período"); put(ddm, "E7", "Fator de Desconto"); put(ddm, "F7", "VP Dividendos (R$ bi)")
    for c in "BCDEF": ddm[f"{c}7"].font = SUBHEADER_FONT; ddm[f"{c}7"].fill = SUBHEADER_FILL

    for i, y in enumerate([2026, 2027, 2028, 2029, 2030]):
        r = 8 + i
        put(ddm, f"B{r}", y).number_format = FMT_YEAR
        col_dre = get_column_letter(3+i)
        ddm.cell(row=r, column=3, value=f"='5.DRE_Proj'!{col_dre}20").font = GREEN
        ddm.cell(row=r, column=3).number_format = FMT_NUM
        ddm.cell(row=r, column=4, value=i+1).font = BLACK
        ddm.cell(row=r, column=5, value=f"=1/(1+'2.Premissas'!$C$11)^D{r}").font = BLACK
        ddm.cell(row=r, column=5).number_format = '0.0000'
        ddm.cell(row=r, column=6, value=f"=C{r}*E{r}").font = BLACK
        ddm.cell(row=r, column=6).number_format = FMT_NUM

    # Sum VP Estágio 1
    put(ddm, "B14", "Soma VP Estágio 1").font = BOLD
    ddm["F14"] = "=SUM(F8:F12)"; ddm["F14"].font = BOLD; ddm["F14"].number_format = FMT_NUM; ddm["F14"].fill = TOTAL_FILL

    # Estágio 2 — Terminal Value (Gordon)
    put(ddm, "B17", "Estágio 2 — Valor Terminal (Perpetuidade Gordon)", Font(name="Arial", bold=True, size=12, color="1F3864"))

    put(ddm, "B19", "Dividendo 2031E (D_t+1)"); ddm["C19"] = "=C12*(1+'2.Premissas'!$C$13)"; ddm["C19"].font = BLACK; ddm["C19"].number_format = FMT_NUM
    put(ddm, "B20", "Ke — Custo de Equity"); ddm["C20"] = "='2.Premissas'!$C$11"; ddm["C20"].font = GREEN; ddm["C20"].number_format = FMT_PCT
    put(ddm, "B21", "g — Crescimento terminal"); ddm["C21"] = "='2.Premissas'!$C$13"; ddm["C21"].font = GREEN; ddm["C21"].number_format = FMT_PCT
    put(ddm, "B22", "TV em 2030 (R$ bi)"); ddm["C22"] = "=C19/(C20-C21)"; ddm["C22"].font = BLACK; ddm["C22"].number_format = FMT_NUM; ddm["C22"].fill = TOTAL_FILL
    put(ddm, "B23", "VP do TV (R$ bi)"); ddm["C23"] = "=C22/(1+C20)^5"; ddm["C23"].font = BLACK; ddm["C23"].number_format = FMT_NUM; ddm["C23"].fill = TOTAL_FILL

    # Equity Value
    put(ddm, "B26", "Valor do Equity", Font(name="Arial", bold=True, size=12, color="1F3864"))
    put(ddm, "B28", "Equity Value (R$ bi)"); ddm["C28"] = "=F14+C23"; ddm["C28"].font = Font(name="Arial", bold=True, size=11); ddm["C28"].number_format = FMT_NUM; ddm["C28"].fill = YELLOW
    put(ddm, "B29", "(/) Ações em circulação (mi)"); ddm["C29"] = "='2.Premissas'!$C$21"; ddm["C29"].font = GREEN; ddm["C29"].number_format = FMT_NUM0
    put(ddm, "B30", "Valor por ação (R$)"); ddm["C30"] = "=C28*1000/C29"; ddm["C30"].font = BOLD; ddm["C30"].number_format = FMT_RS

    # Cross-check: via residual income
    put(ddm, "B32", "Checagem cruzada — Preço-alvo", Font(name="Arial", bold=True, size=12, color="1F3864"))
    put(ddm, "B34", "Preço atual (R$)"); ddm["C34"] = f"={data['preco_atual']}"; ddm["C34"].font = BLUE; ddm["C34"].number_format = FMT_RS; ddm["C34"].fill = YELLOW
    put(ddm, "B35", "Preço-alvo DDM (R$)"); ddm["C35"] = "=C30"; ddm["C35"].font = BOLD; ddm["C35"].number_format = FMT_RS; ddm["C35"].fill = TOTAL_FILL
    put(ddm, "B36", "Upside/(Downside)"); ddm["C36"] = "=C35/C34-1"; ddm["C36"].font = BLACK; ddm["C36"].number_format = FMT_PCT
    put(ddm, "B37", "Dividend Yield (prospectivo 2026)"); ddm["C37"] = "=C8/C34/1000*'2.Premissas'!$C$21";
    ddm["C37"].font = BLACK; ddm["C37"].number_format = FMT_PCT

    # Decomposição do valor (Estágio 1 vs Terminal)
    put(ddm, "B39", "Decomposição do Valor")
    put(ddm, "B40", "  % Estágio 1 (dividendos explícitos)"); ddm["C40"] = "=F14/C28"; ddm["C40"].font = BLACK; ddm["C40"].number_format = FMT_PCT
    put(ddm, "B41", "  % Valor Terminal"); ddm["C41"] = "=C23/C28"; ddm["C41"].font = BLACK; ddm["C41"].number_format = FMT_PCT

    # ---------------------- 8. MÚLTIPLOS ----------------------
    set_col_widths(mult, [3, 42] + [14]*7 + [3])
    mult.sheet_view.showGridLines = False
    style_header(mult, 2, 2, 9, f"Múltiplos Históricos e Implícitos — {ticker}")

    mult.cell(row=4, column=2, value="Múltiplo").font = SUBHEADER_FONT
    mult.cell(row=4, column=2).fill = SUBHEADER_FILL
    for i, y in enumerate(data["anos"]):
        c = mult.cell(row=4, column=3+i, value=y)
        c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_YEAR
        c.alignment = Alignment(horizontal="center")

    # Preços históricos aproximados (hardcode — usuário pode substituir)
    preco_hist = {
        "ITUB4":  [25.0, 22.5, 23.0, 28.0, 31.5, 33.8, 35.5],
        "BBAS3":  [22.0, 17.5, 20.0, 35.0, 44.0, 30.5, 26.8],
        "BBDC4":  [26.0, 21.0, 20.5, 15.5, 14.0, 12.8, 15.2],
        "SANB11": [44.0, 32.0, 34.0, 28.5, 26.0, 28.0, 29.8],
        "BPAC11": [20.0, 24.0, 20.0, 23.0, 32.0, 35.5, 42.5],  # units ajustadas por splits
    }
    # Row 6: preço de fechamento
    mult.cell(row=6, column=2, value="Preço médio anual (R$)").font = BLACK
    for i, p in enumerate(preco_hist[ticker]):
        c = mult.cell(row=6, column=3+i, value=p); c.font = BLUE; c.number_format = FMT_RS

    # Row 7: Market Cap = preço × ações
    mult.cell(row=7, column=2, value="Market Cap (R$ bi)").font = BOLD
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"={col}6*'2.Premissas'!$C$21/1000"
        c = mult.cell(row=7, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_NUM

    # Row 9: LPA
    mult.cell(row=9, column=2, value="LPA (R$)").font = BLACK
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"='3.Historico'!{col}{row_ll}*1000/'2.Premissas'!$C$21"
        c = mult.cell(row=9, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_RS

    # Row 10: VPA
    mult.cell(row=10, column=2, value="VPA (R$)").font = BLACK
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"='3.Historico'!{col}{row_pl}*1000/'2.Premissas'!$C$21"
        c = mult.cell(row=10, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_RS

    # Row 12: P/L
    mult.cell(row=12, column=2, value="P/L").font = BOLD
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"=IFERROR({col}6/{col}9,0)"
        c = mult.cell(row=12, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_MULT

    # Row 13: P/VP
    mult.cell(row=13, column=2, value="P/VP").font = BOLD
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"=IFERROR({col}6/{col}10,0)"
        c = mult.cell(row=13, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_MULT

    # Row 14: Dividend Yield
    mult.cell(row=14, column=2, value="Dividend Yield (est.)").font = BLACK
    for i in range(len(data["anos"])):
        col = get_column_letter(3+i)
        f = f"={col}9*'2.Premissas'!$C$19/{col}6"
        c = mult.cell(row=14, column=3+i, value=f)
        c.font = BLACK; c.number_format = FMT_PCT

    # Row 16: média 3Y e 7Y
    mult.cell(row=16, column=2, value="Média P/L 7 anos").font = ITALIC
    mult["C16"] = "=AVERAGE(C12:I12)"; mult["C16"].font = BLACK; mult["C16"].number_format = FMT_MULT
    mult.cell(row=17, column=2, value="Média P/VP 7 anos").font = ITALIC
    mult["C17"] = "=AVERAGE(C13:I13)"; mult["C17"].font = BLACK; mult["C17"].number_format = FMT_MULT

    # Row 19-22: Múltiplos implícitos (preço-alvo)
    mult.cell(row=19, column=2, value="Múltiplos implícitos no preço-alvo (2025)").font = Font(name="Arial", bold=True, color="1F3864", size=11)
    mult.cell(row=20, column=2, value="Preço-alvo DDM").font = BLACK
    mult["C20"] = "='7.DDM_Valuation'!C35"; mult["C20"].font = GREEN; mult["C20"].number_format = FMT_RS
    mult.cell(row=21, column=2, value="P/L implícito (2025)").font = BLACK
    mult["C21"] = "=C20/I9"; mult["C21"].font = BLACK; mult["C21"].number_format = FMT_MULT
    mult.cell(row=22, column=2, value="P/VP implícito (2025)").font = BLACK
    mult["C22"] = "=C20/I10"; mult["C22"].font = BLACK; mult["C22"].number_format = FMT_MULT
    mult.cell(row=23, column=2, value="vs. Média histórica P/L").font = ITALIC
    mult["C23"] = "=C21/C16-1"; mult["C23"].font = BLACK; mult["C23"].number_format = FMT_PCT
    mult.cell(row=24, column=2, value="vs. Média histórica P/VP").font = ITALIC
    mult["C24"] = "=C22/C17-1"; mult["C24"].font = BLACK; mult["C24"].number_format = FMT_PCT

    # ---------------------- 9. SENSIBILIDADE ----------------------
    set_col_widths(sens, [3, 24] + [14]*7 + [3])
    sens.sheet_view.showGridLines = False
    style_header(sens, 2, 2, 9, f"Sensibilidade: Preço-alvo (R$) — Ke × g")

    put(sens, "B5", "Tabela bidirecional: cada célula é o preço-alvo recalculado", ITALIC)
    put(sens, "B6", "Parâmetros atuais:")
    put(sens, "C6", "Ke"); sens["D6"] = "='2.Premissas'!C11"; sens["D6"].font = GREEN; sens["D6"].number_format = FMT_PCT
    put(sens, "E6", "g"); sens["F6"] = "='2.Premissas'!C13"; sens["F6"].font = GREEN; sens["F6"].number_format = FMT_PCT
    put(sens, "G6", "Preço:"); sens["H6"] = "='7.DDM_Valuation'!C35"; sens["H6"].font = GREEN; sens["H6"].number_format = FMT_RS

    # Eixo Y = Ke (12% a 17%), Eixo X = g (3,5% a 6%)
    ke_range = [0.12, 0.13, 0.14, 0.15, 0.16, 0.17]
    g_range = [0.035, 0.04, 0.045, 0.05, 0.055, 0.06]

    put(sens, "B9", "Ke ↓  /  g →").font = BOLD
    for i, g in enumerate(g_range):
        c = sens.cell(row=9, column=3+i, value=g); c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_PCT
    for j, ke in enumerate(ke_range):
        c = sens.cell(row=10+j, column=2, value=ke); c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_PCT

    # Cada célula: (D2026×disc + ... + TV×disc) / shares, onde Ke = $B{row}, g = C${col}
    # Simplificação: usar formula de valor em 2030 + TV do 2031 descontado
    # V = sum_{t=1..5} (D_2025*(1+g_sched)^t)/(1+Ke)^t + [D_2031/(Ke-g)] / (1+Ke)^5
    # PROBLEMA: os dividendos projetados DEPENDEM das premissas. Para uma tabela 2D limpa,
    # assumimos que os dividendos permanecem os calculados em DDM e aplicamos novos Ke/g.
    for j, ke in enumerate(ke_range):
        for i, g in enumerate(g_range):
            # fórmula: sum_{t=1..5} DIV_t / (1+Ke)^t + [DIV_5 * (1+g) / (Ke - g)] / (1+Ke)^5 / shares
            # Ke ref = $B{10+j}; g ref = C${9}...
            ke_ref = f"$B{10+j}"
            g_ref = f"{get_column_letter(3+i)}$9"
            f = (f"=("
                 f"'7.DDM_Valuation'!$C$8/(1+{ke_ref})^1+"
                 f"'7.DDM_Valuation'!$C$9/(1+{ke_ref})^2+"
                 f"'7.DDM_Valuation'!$C$10/(1+{ke_ref})^3+"
                 f"'7.DDM_Valuation'!$C$11/(1+{ke_ref})^4+"
                 f"'7.DDM_Valuation'!$C$12/(1+{ke_ref})^5+"
                 f"('7.DDM_Valuation'!$C$12*(1+{g_ref})/({ke_ref}-{g_ref}))/(1+{ke_ref})^5"
                 f")*1000/'2.Premissas'!$C$21")
            c = sens.cell(row=10+j, column=3+i, value=f)
            c.font = BLACK; c.number_format = FMT_RS

    # Heatmap simples (nota: openpyxl não aplica conditional formatting auto, mas podemos adicionar)
    from openpyxl.formatting.rule import ColorScaleRule
    rule = ColorScaleRule(start_type="min", start_color="F8696B",
                          mid_type="percentile", mid_value=50, mid_color="FFEB84",
                          end_type="max", end_color="63BE7B")
    sens.conditional_formatting.add(f"C10:H{9+len(ke_range)}", rule)

    # ---------------------- 10. DASHBOARD ----------------------
    set_col_widths(dash, [3, 28] + [14]*7 + [3])
    dash.sheet_view.showGridLines = False
    style_header(dash, 2, 2, 9, f"{ticker} — Dashboard de KPIs")

    # KPIs principais
    put(dash, "B5", "Recomendação"); dash["C5"] = "='1.Capa'!C10"; dash["C5"].font = Font(name="Arial", bold=True, size=14, color="1F3864"); dash["C5"].fill = YELLOW
    put(dash, "B6", "Preço atual (R$)"); dash["C6"] = "='1.Capa'!C7"; dash["C6"].font = GREEN; dash["C6"].number_format = FMT_RS
    put(dash, "B7", "Preço-alvo (R$)"); dash["C7"] = "='7.DDM_Valuation'!C35"; dash["C7"].font = GREEN; dash["C7"].number_format = FMT_RS
    put(dash, "B8", "Upside"); dash["C8"] = "=C7/C6-1"; dash["C8"].font = BOLD; dash["C8"].number_format = FMT_PCT

    put(dash, "E5", "Ke"); dash["F5"] = "='2.Premissas'!C11"; dash["F5"].font = GREEN; dash["F5"].number_format = FMT_PCT
    put(dash, "E6", "g terminal"); dash["F6"] = "='2.Premissas'!C13"; dash["F6"].font = GREEN; dash["F6"].number_format = FMT_PCT
    put(dash, "E7", "Payout"); dash["F7"] = "='2.Premissas'!C19"; dash["F7"].font = GREEN; dash["F7"].number_format = FMT_PCT
    put(dash, "E8", "ROE sustentável"); dash["F8"] = "='2.Premissas'!C20"; dash["F8"].font = GREEN; dash["F8"].number_format = FMT_PCT

    # Tabela KPIs históricos + projetados
    put(dash, "B11", "KPI", BOLD)
    all_years_dash = data["anos"] + [2026, 2027, 2028, 2029, 2030]
    for i, y in enumerate(all_years_dash):
        c = dash.cell(row=11, column=3+i, value=y)
        c.font = SUBHEADER_FONT; c.fill = SUBHEADER_FILL; c.number_format = FMT_YEAR
        c.alignment = Alignment(horizontal="center")
        if y >= 2026: c.fill = PatternFill("solid", start_color="1F3864")

    # Row 12: Lucro Líquido
    dash.cell(row=12, column=2, value="Lucro Líquido (R$ bi)").font = BLACK
    for i, y in enumerate(data["anos"]):
        col = get_column_letter(3+i)
        dash.cell(row=12, column=3+i, value=f"='3.Historico'!{col}{row_ll}").font = GREEN
        dash.cell(row=12, column=3+i).number_format = FMT_NUM
    for i in range(5):
        col = get_column_letter(3+i)
        dash.cell(row=12, column=3+len(data["anos"])+i, value=f"='5.DRE_Proj'!{col}18").font = GREEN
        dash.cell(row=12, column=3+len(data["anos"])+i).number_format = FMT_NUM

    # Row 13: ROE
    dash.cell(row=13, column=2, value="ROE").font = BLACK
    # mesma fórmula do histórico drivers!10
    for i in range(len(all_years_dash)):
        col = get_column_letter(3+i)
        dash.cell(row=13, column=3+i, value=f"='4.Drivers'!{col}10").font = GREEN
        dash.cell(row=13, column=3+i).number_format = FMT_PCT

    # Row 14: NIM
    dash.cell(row=14, column=2, value="NIM").font = BLACK
    for i in range(len(all_years_dash)):
        col = get_column_letter(3+i)
        dash.cell(row=14, column=3+i, value=f"='4.Drivers'!{col}7").font = GREEN
        dash.cell(row=14, column=3+i).number_format = FMT_PCT

    # Row 15: Eficiência
    dash.cell(row=15, column=2, value="Índice de Eficiência").font = BLACK
    for i in range(len(all_years_dash)):
        col = get_column_letter(3+i)
        dash.cell(row=15, column=3+i, value=f"='4.Drivers'!{col}11").font = GREEN
        dash.cell(row=15, column=3+i).number_format = FMT_PCT

    # Row 16: Carteira
    dash.cell(row=16, column=2, value="Carteira de Crédito (R$ bi)").font = BLACK
    for i in range(len(all_years_dash)):
        col = get_column_letter(3+i)
        dash.cell(row=16, column=3+i, value=f"='4.Drivers'!{col}6").font = GREEN
        dash.cell(row=16, column=3+i).number_format = FMT_NUM

    # Row 17: Custo do Crédito
    dash.cell(row=17, column=2, value="Custo do Crédito").font = BLACK
    for i in range(len(all_years_dash)):
        col = get_column_letter(3+i)
        dash.cell(row=17, column=3+i, value=f"='4.Drivers'!{col}8").font = GREEN
        dash.cell(row=17, column=3+i).number_format = FMT_PCT

    # === GRÁFICOS ===
    # Gráfico 1: Lucro Líquido 2019-2030
    chart_ll = LineChart()
    chart_ll.title = "Lucro Líquido — Histórico + Projeção (R$ bi)"
    chart_ll.style = 12
    chart_ll.y_axis.title = "R$ bi"
    chart_ll.x_axis.title = "Ano"
    data_ref = Reference(dash, min_col=3, min_row=12, max_col=2+len(all_years_dash), max_row=12)
    cats_ref = Reference(dash, min_col=3, min_row=11, max_col=2+len(all_years_dash), max_row=11)
    chart_ll.add_data(data_ref, titles_from_data=False)
    chart_ll.set_categories(cats_ref)
    chart_ll.series[0].tx = openpyxl_title("Lucro Líquido")
    chart_ll.height = 8; chart_ll.width = 17
    dash.add_chart(chart_ll, "B20")

    # Gráfico 2: ROE + NIM
    chart_roe = LineChart()
    chart_roe.title = "ROE × NIM (%)"
    chart_roe.style = 10
    chart_roe.y_axis.number_format = '0.0%'
    data_ref2 = Reference(dash, min_col=3, min_row=13, max_col=2+len(all_years_dash), max_row=14)
    chart_roe.add_data(data_ref2, titles_from_data=False)
    chart_roe.set_categories(cats_ref)
    chart_roe.series[0].tx = openpyxl_title("ROE")
    chart_roe.series[1].tx = openpyxl_title("NIM")
    chart_roe.height = 8; chart_roe.width = 17
    dash.add_chart(chart_roe, "B38")

    # Gráfico 3: Carteira
    chart_cart = BarChart()
    chart_cart.title = "Carteira de Crédito (R$ bi)"
    chart_cart.style = 11
    data_ref3 = Reference(dash, min_col=3, min_row=16, max_col=2+len(all_years_dash), max_row=16)
    chart_cart.add_data(data_ref3, titles_from_data=False)
    chart_cart.set_categories(cats_ref)
    chart_cart.series[0].tx = openpyxl_title("Carteira")
    chart_cart.height = 8; chart_cart.width = 17
    dash.add_chart(chart_cart, "B56")

    wb.save(out_path)


def openpyxl_title(text):
    """Cria um SeriesLabel para gráfico."""
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.data_source import StrRef
    sl = SeriesLabel()
    sl.v = text
    return sl


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import os
    out_dir = "/sessions/quirky-eager-mayer/mnt/OBSIDIAN/Analista de Investimentos/07_VALUATION/BANCOS_GRANDES"
    os.makedirs(out_dir, exist_ok=True)
    for ticker, data in BANKS.items():
        path = os.path.join(out_dir, f"VALUATION_{ticker}_2026.xlsx")
        build_bank_workbook(ticker, data, path)
        print(f"✅ Gerado: {path}")
