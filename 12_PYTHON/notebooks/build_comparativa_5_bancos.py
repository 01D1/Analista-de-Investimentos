"""
Planilha comparativa 5 bancos brasileiros de grande porte — abr/2026
Cruza as saídas dos 5 modelos individuais (DDM + multiplos + drivers) em um único dashboard.
"""
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.chart import BarChart, ScatterChart, Reference, Series
from openpyxl.chart.label import DataLabelList

BASE = "/sessions/quirky-eager-mayer/mnt/OBSIDIAN/Analista de Investimentos/07_VALUATION/BANCOS_GRANDES"
OUT = f"{BASE}/COMPARATIVA_BANCOS_5.xlsx"

TICKERS = ["ITUB4", "BBAS3", "BBDC4", "SANB11", "BPAC11"]

# Extrai dados dos 5 workbooks
def extrair(ticker):
    wb = openpyxl.load_workbook(f"{BASE}/VALUATION_{ticker}_2026.xlsx", data_only=True)
    c = wb["1.Capa"]; drv = wb["4.Drivers"]; dre = wb["5.DRE_Proj"]; bp = wb["6.BP_Proj"]; m = wb["8.Multiplos"]
    d = {
        "ticker": ticker,
        "preco": c['C7'].value,
        "alvo": c['C8'].value,
        "upside": c['C9'].value,
        "rec": c['C10'].value,
        "rf": c['C25'].value,
        "erp": c['C26'].value,
        "beta": c['C27'].value,
        "ke": c['C28'].value,
        "g": c['C29'].value,
        "payout": c['C30'].value,
        "roe_sus": c['C31'].value,
    }
    # ROE, NIM, carteira, eficiência drivers (cols 3-9 hist 2019-2025, 10-14 proj 2026-2030)
    for col, y in enumerate([2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030], start=3):
        d[f"roe_{y}"] = drv.cell(row=10, column=col).value
        d[f"nim_{y}"] = drv.cell(row=7, column=col).value
        d[f"carteira_{y}"] = drv.cell(row=6, column=col).value
        d[f"ef_{y}"] = drv.cell(row=11, column=col).value
    # LL projetado col 3=2026, 4=2027, 5=2028, 6=2029, 7=2030, 8=Terminal
    for col, y in enumerate([2026,2027,2028,2029,2030,"TV"], start=3):
        d[f"ll_{y}"] = dre.cell(row=18, column=col).value
        d[f"div_{y}"] = dre.cell(row=20, column=col).value
    # Múltiplos históricos médios + implícitos
    d["pl_med"] = m['C16'].value
    d["pvp_med"] = m['C17'].value
    d["pl_impl"] = m['C21'].value
    d["pvp_impl"] = m['C22'].value
    # PL atual (ano 2025 — col 9 na 4.Drivers linha 6 era carteira, PL está na aba 3.Historico)
    hist = wb["3.Historico"]
    # BP linha PL — tentar achar
    for r in range(1, 50):
        a = hist.cell(row=r, column=1).value or hist.cell(row=r, column=2).value
        if a and "PL" in str(a) and "Control" in str(a):
            d["pl_2025"] = hist.cell(row=r, column=9).value
            break
    return d

data = {t: extrair(t) for t in TICKERS}

# === Construir workbook comparativo ===
wb = Workbook()
ws1 = wb.active
ws1.title = "1.Resumo"

FONT = "Arial"
BLUE = Font(name=FONT, color="0000FF")
BLACK = Font(name=FONT, color="000000")
GREEN = Font(name=FONT, color="008000")
BOLD = Font(name=FONT, bold=True)
BOLD_W = Font(name=FONT, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
BAND_FILL = PatternFill("solid", fgColor="E7E6E6")
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")
RIGHT = Alignment(horizontal="right", vertical="center")

FMT_RS = '"R$ "#,##0.00;("R$ "#,##0.00);-'
FMT_BI = '#,##0.0" bi";(#,##0.0" bi");-'
FMT_PCT = "0.0%;(0.0%);-"
FMT_MULT = '0.0"x"'

def header(ws, row, cols, values):
    for c, v in zip(cols, values):
        cell = ws.cell(row=row, column=c, value=v)
        cell.fill = HEADER_FILL
        cell.font = BOLD_W
        cell.alignment = CENTER

# === ABA 1: Resumo Executivo ===
ws1['B2'] = "Comparativa — 5 Bancos Brasileiros de Grande Porte"
ws1['B2'].font = Font(name=FONT, bold=True, size=16, color="1F4E78")
ws1['B3'] = "Data-base: 2025-12-31  |  Valuation: abr/2026  |  Metodologia: DDM Gordon 2 estágios + Múltiplos"
ws1['B3'].font = Font(name=FONT, italic=True, color="555555")

# Tabela principal
ws1['B5'] = "Sumário de Recomendações"
ws1['B5'].font = Font(name=FONT, bold=True, size=12)

header(ws1, 7, range(2, 14), [
    "Ticker", "Empresa", "Preço Atual", "Alvo DDM", "Upside", "Recomendação",
    "Ke", "β", "ROE 2026E", "ROE 2030E", "P/L impl.", "P/VP impl."
])

NOMES = {
    "ITUB4": "Itaú Unibanco",
    "BBAS3": "Banco do Brasil",
    "BBDC4": "Bradesco",
    "SANB11": "Santander BR",
    "BPAC11": "BTG Pactual",
}

for i, t in enumerate(TICKERS):
    row = 8 + i
    d = data[t]
    ws1.cell(row=row, column=2, value=t).font = BOLD
    ws1.cell(row=row, column=3, value=NOMES[t]).font = BLACK
    ws1.cell(row=row, column=4, value=d["preco"]).number_format = FMT_RS
    ws1.cell(row=row, column=5, value=d["alvo"]).number_format = FMT_RS
    ws1.cell(row=row, column=6, value=d["upside"]).number_format = FMT_PCT
    rec_cell = ws1.cell(row=row, column=7, value=d["rec"])
    rec_cell.alignment = CENTER
    if "COMPRA" in d["rec"]:
        rec_cell.fill = PatternFill("solid", fgColor="70AD47")
        rec_cell.font = BOLD_W
    elif "NEUTRO" in d["rec"]:
        rec_cell.fill = PatternFill("solid", fgColor="FFD966")
        rec_cell.font = BOLD
    else:  # VENDA
        rec_cell.fill = PatternFill("solid", fgColor="C00000")
        rec_cell.font = BOLD_W
    ws1.cell(row=row, column=8, value=d["ke"]).number_format = FMT_PCT
    ws1.cell(row=row, column=9, value=d["beta"]).number_format = "0.00"
    ws1.cell(row=row, column=10, value=d["roe_2026"]).number_format = FMT_PCT
    ws1.cell(row=row, column=11, value=d["roe_2030"]).number_format = FMT_PCT
    ws1.cell(row=row, column=12, value=d["pl_impl"]).number_format = FMT_MULT
    ws1.cell(row=row, column=13, value=d["pvp_impl"]).number_format = FMT_MULT
    for c in range(2, 14):
        ws1.cell(row=row, column=c).alignment = CENTER if c != 3 else LEFT

# Larguras
for col, w in zip("ABCDEFGHIJKLMNO", [2, 9, 20, 14, 14, 12, 14, 8, 8, 12, 12, 11, 11, 8, 8]):
    ws1.column_dimensions[col].width = w

# Coloração condicional sobre upside
rule_ups = ColorScaleRule(
    start_type='min', start_color='C00000',
    mid_type='num', mid_value=0, mid_color='FFFFFF',
    end_type='max', end_color='70AD47')
ws1.conditional_formatting.add("F8:F12", rule_ups)

# Notas
ws1['B15'] = "Ranking (por upside decrescente)"
ws1['B15'].font = BOLD
sorted_t = sorted(TICKERS, key=lambda x: -data[x]["upside"])
for i, t in enumerate(sorted_t):
    ws1.cell(row=16+i, column=2, value=f"{i+1}º").font = BOLD
    ws1.cell(row=16+i, column=3, value=t).font = BOLD
    ws1.cell(row=16+i, column=4, value=f"{data[t]['upside']*100:.1f}%  ({data[t]['rec']})")

ws1['B22'] = "Observações-chave"
ws1['B22'].font = BOLD
notas = [
    "• ITUB4 é o melhor posicionado entre os 4 grandes (maior ROE, menor desconto → NEUTRO-).",
    "• BBDC4 tem o maior downside implícito (-48%) — reflete deterioração operacional 2020-2024.",
    "• BPAC11 premium não justificado pelo modelo DDM: ROE alto mas Ke ~18% consome o valor.",
    "• Todos os 4 grandes + BPAC com VENDA ou NEUTRO — setor bancário BR precifica pouca margem.",
    "• Sensibilidade: queda de 100 bps no Rf (Selic cai) altera upsides em média +8 p.p.",
]
for i, n in enumerate(notas):
    ws1.cell(row=23+i, column=2, value=n)

# === ABA 2: DRE & LL Projetado ===
ws2 = wb.create_sheet("2.LL_Projetado")
ws2['B2'] = "Lucro Líquido Projetado (R$ bi) — 2026-2030"
ws2['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

header(ws2, 4, range(2, 9), ["Ticker", "2026E", "2027E", "2028E", "2029E", "2030E", "CAGR 26-30"])
for i, t in enumerate(TICKERS):
    row = 5 + i
    d = data[t]
    ws2.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate([2026, 2027, 2028, 2029, 2030]):
        cell = ws2.cell(row=row, column=3+j, value=d[f"ll_{y}"])
        cell.number_format = FMT_BI
    # CAGR
    cagr_formula = f"=({get_column_letter(7)}{row}/{get_column_letter(3)}{row})^(1/4)-1"
    ws2.cell(row=row, column=8, value=cagr_formula).number_format = FMT_PCT
    ws2.cell(row=row, column=8).font = BLACK

# ROE por ano
ws2['B12'] = "ROE Projetado (%) — 2026-2030"
ws2['B12'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")
header(ws2, 14, range(2, 8), ["Ticker", "2026E", "2027E", "2028E", "2029E", "2030E"])
for i, t in enumerate(TICKERS):
    row = 15 + i
    d = data[t]
    ws2.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate([2026, 2027, 2028, 2029, 2030]):
        cell = ws2.cell(row=row, column=3+j, value=d[f"roe_{y}"])
        cell.number_format = FMT_PCT

# Dividendos projetados
ws2['B22'] = "Dividendos Distribuídos Projetados (R$ bi)"
ws2['B22'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")
header(ws2, 24, range(2, 9), ["Ticker", "2026E", "2027E", "2028E", "2029E", "2030E", "DY 2026E"])
for i, t in enumerate(TICKERS):
    row = 25 + i
    d = data[t]
    ws2.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate([2026, 2027, 2028, 2029, 2030]):
        cell = ws2.cell(row=row, column=3+j, value=d[f"div_{y}"])
        cell.number_format = FMT_BI
    # DY = dividendo 2026 / market cap
    dy_formula = f"=C{row}*1000000000/(('1.Resumo'!D{8+i})*(CASE_ACOES_{t}))"
    # Simpler: apenas reportar
    # market cap = preço × ações
    acoes = {"ITUB4": 9777, "BBAS3": 2860, "BBDC4": 10800, "SANB11": 3890, "BPAC11": 2660}[t]
    mkt_cap = data[t]["preco"] * acoes / 1000  # R$ bi
    dy = data[t]["div_2026"] / mkt_cap if mkt_cap else 0
    ws2.cell(row=row, column=8, value=dy).number_format = FMT_PCT

for col, w in zip("ABCDEFGHI", [2, 9, 12, 12, 12, 12, 12, 12, 2]):
    ws2.column_dimensions[col].width = w

# === ABA 3: Múltiplos ===
ws3 = wb.create_sheet("3.Multiplos")
ws3['B2'] = "Múltiplos — Históricos vs Implícitos no Preço-Alvo"
ws3['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

header(ws3, 4, range(2, 9), ["Ticker", "P/L Médio 7a", "P/L Implícito", "Δ P/L", "P/VP Médio 7a", "P/VP Implícito", "Δ P/VP"])
for i, t in enumerate(TICKERS):
    row = 5 + i
    d = data[t]
    ws3.cell(row=row, column=2, value=t).font = BOLD
    ws3.cell(row=row, column=3, value=d["pl_med"]).number_format = FMT_MULT
    ws3.cell(row=row, column=4, value=d["pl_impl"]).number_format = FMT_MULT
    ws3.cell(row=row, column=5, value=f"=D{row}/C{row}-1").number_format = FMT_PCT
    ws3.cell(row=row, column=6, value=d["pvp_med"]).number_format = FMT_MULT
    ws3.cell(row=row, column=7, value=d["pvp_impl"]).number_format = FMT_MULT
    ws3.cell(row=row, column=8, value=f"=G{row}/F{row}-1").number_format = FMT_PCT

# ROE sustentável vs Ke gap
ws3['B12'] = "ROE sustentável vs Ke — Spread de Geração de Valor"
ws3['B12'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")
header(ws3, 14, range(2, 7), ["Ticker", "ROE Sustent.", "Ke", "Spread (ROE-Ke)", "P/VP Justo (Gordon)"])
for i, t in enumerate(TICKERS):
    row = 15 + i
    d = data[t]
    ws3.cell(row=row, column=2, value=t).font = BOLD
    ws3.cell(row=row, column=3, value=d["roe_sus"]).number_format = FMT_PCT
    ws3.cell(row=row, column=4, value=d["ke"]).number_format = FMT_PCT
    ws3.cell(row=row, column=5, value=f"=C{row}-D{row}").number_format = FMT_PCT
    # P/VP justo Gordon = (ROE-g)/(Ke-g) com g=5%
    ws3.cell(row=row, column=6, value=f"=(C{row}-0.05)/(D{row}-0.05)").number_format = FMT_MULT

# NIM comparativo
ws3['B22'] = "NIM Projetado 2026-2030 (%)"
ws3['B22'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")
header(ws3, 24, range(2, 8), ["Ticker", "2026E", "2027E", "2028E", "2029E", "2030E"])
for i, t in enumerate(TICKERS):
    row = 25 + i
    d = data[t]
    ws3.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate([2026, 2027, 2028, 2029, 2030]):
        cell = ws3.cell(row=row, column=3+j, value=d[f"nim_{y}"])
        cell.number_format = FMT_PCT

for col, w in zip("ABCDEFGH", [2, 9, 14, 14, 12, 14, 14, 12]):
    ws3.column_dimensions[col].width = w

# === ABA 4: Premissas Macro ===
ws4 = wb.create_sheet("4.Premissas")
ws4['B2'] = "Premissas Macro — Comuns aos 5 modelos"
ws4['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

header(ws4, 4, range(2, 9), ["Ticker", "Rf (NTN-B)", "ERP Brasil", "Beta (β)", "Ke (CAPM)", "g Terminal", "Payout Proj"])
for i, t in enumerate(TICKERS):
    row = 5 + i
    d = data[t]
    ws4.cell(row=row, column=2, value=t).font = BOLD
    ws4.cell(row=row, column=3, value=d["rf"]).number_format = FMT_PCT
    ws4.cell(row=row, column=4, value=d["erp"]).number_format = FMT_PCT
    ws4.cell(row=row, column=5, value=d["beta"]).number_format = "0.00"
    ws4.cell(row=row, column=6, value=d["ke"]).number_format = FMT_PCT
    ws4.cell(row=row, column=7, value=d["g"]).number_format = FMT_PCT
    ws4.cell(row=row, column=8, value=d["payout"]).number_format = FMT_PCT

ws4['B12'] = "Fórmula CAPM utilizada"
ws4['B12'].font = BOLD
ws4['B13'] = "Ke = Rf_BR + β · ERP_Brasil"
ws4['B13'].font = Font(name=FONT, italic=True, color="555555")
ws4['B14'] = "⚠ ERP Damodaran Brasil JÁ INCLUI Country Risk Premium — não somar CRP separadamente."
ws4['B14'].font = Font(name=FONT, color="C00000", bold=True)

ws4['B17'] = "Fontes"
ws4['B17'].font = BOLD
fontes = [
    "• Rf: Tesouro Direto, NTN-B 2035 proxy (~11,5% nominal)",
    "• ERP: Damodaran 'Country Risk Premium — Brazil' 2025 (6,0-7,0%)",
    "• Beta: Bloomberg / TC School, 5Y mensal",
    "• g terminal: Inflação BCB Focus (3,5%) + crescimento real 1,5% ≈ 5,0% nominal",
    "• Payout: média histórica 5 anos, ajustada para JCP + recompras quando aplicável",
]
for i, n in enumerate(fontes):
    ws4.cell(row=18+i, column=2, value=n)

for col, w in zip("ABCDEFGH", [2, 9, 13, 13, 10, 13, 13, 13]):
    ws4.column_dimensions[col].width = w

# === ABA 5: Balanço (Carteira & PL) ===
ws5 = wb.create_sheet("5.Balanco")
ws5['B2'] = "Carteira de Crédito — Histórico + Projeção (R$ bi)"
ws5['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

anos = [2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030]
header(ws5, 4, range(2, 15), ["Ticker"] + [str(y) for y in anos])
for i, t in enumerate(TICKERS):
    row = 5 + i
    d = data[t]
    ws5.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate(anos):
        v = d.get(f"carteira_{y}")
        cell = ws5.cell(row=row, column=3+j, value=v)
        cell.number_format = FMT_BI

# Eficiência
ws5['B12'] = "Índice de Eficiência (%) — menor é melhor"
ws5['B12'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")
header(ws5, 14, range(2, 15), ["Ticker"] + [str(y) for y in anos])
for i, t in enumerate(TICKERS):
    row = 15 + i
    d = data[t]
    ws5.cell(row=row, column=2, value=t).font = BOLD
    for j, y in enumerate(anos):
        v = d.get(f"ef_{y}")
        cell = ws5.cell(row=row, column=3+j, value=v)
        if v is not None:
            cell.number_format = FMT_PCT

for col in "ABCDEFGHIJKLMNOP":
    ws5.column_dimensions[col].width = 10
ws5.column_dimensions['A'].width = 2
ws5.column_dimensions['B'].width = 9

# === ABA 6: Ranking & Scorecard ===
ws6 = wb.create_sheet("6.Ranking")
ws6['B2'] = "Scorecard — Ranking de 1 (melhor) a 5 (pior)"
ws6['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

# Rankings
def rank(getter, reverse=True):
    """reverse=True: maior = melhor (rank 1). reverse=False: menor = melhor."""
    vals = [(t, getter(data[t])) for t in TICKERS]
    vals.sort(key=lambda x: x[1], reverse=reverse)
    return {t: i+1 for i, (t, _) in enumerate(vals)}

r_upside = rank(lambda d: d["upside"], reverse=True)
r_roe = rank(lambda d: d["roe_sus"], reverse=True)
r_ke = rank(lambda d: d["ke"], reverse=False)  # menor Ke é melhor
r_pl = rank(lambda d: d["pl_impl"], reverse=False)  # menor P/L é mais barato
r_spread = rank(lambda d: d["roe_sus"] - d["ke"], reverse=True)  # maior spread é melhor

header(ws6, 4, range(2, 9), ["Ticker", "Upside", "ROE Sustent.", "Ke (inv.)", "P/L (barato)", "Spread ROE-Ke", "Score Total"])
for i, t in enumerate(TICKERS):
    row = 5 + i
    ws6.cell(row=row, column=2, value=t).font = BOLD
    ws6.cell(row=row, column=3, value=r_upside[t])
    ws6.cell(row=row, column=4, value=r_roe[t])
    ws6.cell(row=row, column=5, value=r_ke[t])
    ws6.cell(row=row, column=6, value=r_pl[t])
    ws6.cell(row=row, column=7, value=r_spread[t])
    ws6.cell(row=row, column=8, value=f"=SUM(C{row}:G{row})").font = BOLD

# Ranking final (menor score = melhor)
scores = {t: r_upside[t]+r_roe[t]+r_ke[t]+r_pl[t]+r_spread[t] for t in TICKERS}
sorted_scores = sorted(scores.items(), key=lambda x: x[1])

ws6['B12'] = "Ranking final (score agregado — menor = melhor)"
ws6['B12'].font = BOLD
for i, (t, s) in enumerate(sorted_scores):
    ws6.cell(row=13+i, column=2, value=f"{i+1}º").font = BOLD
    ws6.cell(row=13+i, column=3, value=t).font = BOLD
    ws6.cell(row=13+i, column=4, value=f"Score {s}")
    rec = data[t]["rec"]
    ws6.cell(row=13+i, column=5, value=rec)
    ws6.cell(row=13+i, column=6, value=f"Upside {data[t]['upside']*100:+.1f}%")

# Heatmap rankings
rule_rank = ColorScaleRule(
    start_type='num', start_value=1, start_color='70AD47',
    mid_type='num', mid_value=3, mid_color='FFEB84',
    end_type='num', end_value=5, end_color='C00000')
ws6.conditional_formatting.add("C5:G9", rule_rank)

for col, w in zip("ABCDEFGH", [2, 9, 11, 13, 11, 13, 15, 12]):
    ws6.column_dimensions[col].width = w

# === ABA 7: Dashboard com gráfico ===
ws7 = wb.create_sheet("7.Dashboard")
ws7['B2'] = "Dashboard Gráfico"
ws7['B2'].font = Font(name=FONT, bold=True, size=14, color="1F4E78")

# Dados para gráfico (colados para reference)
ws7['B4'] = "Ticker"
ws7['C4'] = "Upside"
ws7['D4'] = "ROE 2026E"
ws7['E4'] = "Ke"
ws7['F4'] = "Spread"
for r in range(2, 7):
    ws7.cell(row=4, column=r).font = BOLD
for i, t in enumerate(TICKERS):
    row = 5 + i
    ws7.cell(row=row, column=2, value=t)
    ws7.cell(row=row, column=3, value=data[t]["upside"]).number_format = FMT_PCT
    ws7.cell(row=row, column=4, value=data[t]["roe_2026"]).number_format = FMT_PCT
    ws7.cell(row=row, column=5, value=data[t]["ke"]).number_format = FMT_PCT
    ws7.cell(row=row, column=6, value=data[t]["roe_sus"] - data[t]["ke"]).number_format = FMT_PCT

# Gráfico barra de Upside
chart1 = BarChart()
chart1.type = "bar"
chart1.style = 11
chart1.title = "Upside / (Downside) por Ticker"
chart1.x_axis.title = "Upside (%)"
chart1.y_axis.title = "Ticker"
d_ref = Reference(ws7, min_col=3, min_row=4, max_col=3, max_row=9)
cats = Reference(ws7, min_col=2, min_row=5, max_row=9)
chart1.add_data(d_ref, titles_from_data=True)
chart1.set_categories(cats)
chart1.height = 10
chart1.width = 18
ws7.add_chart(chart1, "H4")

# Gráfico ROE vs Ke (colunas)
chart2 = BarChart()
chart2.type = "col"
chart2.style = 10
chart2.title = "ROE 2026E vs Ke (Custo de Equity)"
d1 = Reference(ws7, min_col=4, min_row=4, max_col=4, max_row=9)
d2 = Reference(ws7, min_col=5, min_row=4, max_col=5, max_row=9)
chart2.add_data(d1, titles_from_data=True)
chart2.add_data(d2, titles_from_data=True)
chart2.set_categories(cats)
chart2.height = 10
chart2.width = 18
ws7.add_chart(chart2, "H24")

for col, w in zip("ABCDEFG", [2, 9, 12, 12, 10, 12, 2]):
    ws7.column_dimensions[col].width = w

# Salvar
wb.save(OUT)
print(f"✅ Comparativa salva em: {OUT}")
