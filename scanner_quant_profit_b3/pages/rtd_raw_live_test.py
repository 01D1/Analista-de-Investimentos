"""
RTD Raw Live Test — lê diretamente data/realtime/RTD PROFIT.xlsx
SEM cache, SEM score, SEM ranking, SEM camadas intermediárias.
Objetivo: provar que o Python enxerga os dados mudando no Excel.

Inclui:
  - Leitura de TODAS as abas disponíveis
  - Coluna calculada "classe_detectada" para validar classificação automática
  - Não depende da aba "Opções" — opções podem estar na aba "Ações"
"""

import os
import re
import time
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RTD_PATH = ROOT / "data" / "realtime" / "RTD PROFIT.xlsx"
SHORTLIST_PATH = ROOT / "data" / "realtime" / "options_rtd_watchlist.csv"
SYMBOLS_PATH = ROOT / "data" / "realtime" / "options_rtd_symbols.csv"

# ── Ticker classifier (mesma lógica do rtd_live_reader) ─────────────────────
OPTION_SUFFIX_PATTERNS = (
    re.compile(r"^[A-Z]{2,5}F\d{3}$"),
    re.compile(r"^[A-Z]{2,5}W\d{3}$"),
    re.compile(r"^[A-Z]{2,5}D\d{3}$"),
    re.compile(r"^[A-Z]{4,6}F\d{2,4}$"),
    re.compile(r"^[A-Z]{1,4}F\d{2,4}$"),
)
FUTURO_PREFIXES = {"WDO", "DOL", "WIN", "IND", "DI1"}
FUTURO_TOKENS = {"WDOFUT", "DOLFUT", "WINFUT", "DDI1FUT", "DI1FUT", "DOLFUTP", "DOLFWN"}
INDICE_TOKERS = {
    "IBOV",
    "IBOVX100",
    "IBRA",
    "SMLL",
    "IFNC",
    "ICON",
    "IDIV",
    "IFIX",
    "IMOB",
    "UTIL",
    "MATER",
    "IBOVX250",
    "IBRXP",
    "IDIVX100",
}
INDICE_PREFIXES = (
    "IBOV",
    "IND",
    "SMLL",
    "IFIX",
    "IMOB",
    "UTIL",
    "MATER",
    "ICON",
    "IDIV",
)
ACAO_TERMINATIONS = {"3", "4", "5", "6", "11"}


def _load_option_tickers() -> set[str]:
    tickers: set[str] = set()
    for path in [SHORTLIST_PATH, SYMBOLS_PATH]:
        if path.exists():
            try:
                df = pd.read_csv(path, dtype=str)
                df.columns = [c.strip() for c in df.columns]
                tickers.update(
                    str(v).strip()
                    for v in df["ticker"].dropna().tolist()
                    if str(v).strip()
                )
            except Exception:
                pass
    return tickers


def classify_ticker(ticker: str, opt_tickers: set[str]) -> str:
    t = str(ticker or "").strip().upper()
    if t in opt_tickers:
        return "OPCAO"
    for pat in OPTION_SUFFIX_PATTERNS:
        if pat.match(t):
            return "OPCAO"
    if t in FUTURO_TOKENS or any(t.startswith(p) for p in FUTURO_PREFIXES):
        return "FUTURO"
    if t in INDICE_TOKERS or t.startswith(INDICE_PREFIXES):
        return "INDICE"
    if t[-2:] in ("11",) or t[-1:] in ("3", "4", "5", "6"):
        return "ACAO"
    return "OUTRO"


# Colunas principais de interesse ──────────────────────────────────────────
COLS_PRINCIPAIS = [
    "Asset",
    "Data",
    "Hora",
    "Último",
    "Variação",
    "Volume",
    "Negócios",
    "Of. Compra",
    "Of. Venda",
    "VWAP",
    "IFR (RSI)",
    "MACD Histograma",
    "ADX",
]

# ─────────────────────────────────────────────────────────────────────────────
st.title("🔬 RTD Raw Live Test")
st.caption(
    "Lê **diretamente** o RTD PROFIT.xlsx — sem cache, sem score, sem camadas. "
    "Sucesso = você vê os números mudarem após editar o Excel."
)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
col_rb, col_btn = st.columns([3, 1])
with col_rb:
    modo = st.radio(
        "Auto-refresh",
        ["Manual", "5s", "10s"],
        horizontal=True,
        key="rtd_refresh_mode",
    )
with col_btn:
    st.write("")  # espaço vertical
    if st.button("⟳ Ler arquivo agora", type="primary"):
        st.rerun()

# ── Implementação do auto-refresh ─────────────────────────────────────────────
if modo == "5s":
    time.sleep(5)
    st.rerun()
elif modo == "10s":
    time.sleep(10)
    st.rerun()

st.divider()

# ── Meta-informações do arquivo ───────────────────────────────────────────────
st.subheader("📁 Informações do Arquivo")

arquivo_existe = RTD_PATH.exists()

m1, m2, m3 = st.columns(3)
m1.metric("Arquivo existe?", "✅ SIM" if arquivo_existe else "❌ NÃO")
m1.code(str(RTD_PATH))

if arquivo_existe:
    stat = RTD_PATH.stat()
    tamanho_kb = stat.st_size / 1024
    dt_modif = datetime.datetime.fromtimestamp(stat.st_mtime)
    dt_leitura = datetime.datetime.now()

    m2.metric("Tamanho", f"{tamanho_kb:.1f} KB")
    m2.metric("Última modificação", dt_modif.strftime("%d/%m/%Y %H:%M:%S"))

    m3.metric("Leitura Python (agora)", dt_leitura.strftime("%d/%m/%Y %H:%M:%S"))
    delta_seg = (dt_leitura - dt_modif).total_seconds()
    m3.metric("Arquivo tem", f"{delta_seg:.0f}s atrás" if delta_seg >= 0 else "futuro?")
else:
    st.error(
        f"❌ Arquivo **não encontrado** em:\n\n`{RTD_PATH}`\n\n"
        "Verifique se o Profit está rodando e exportando para esse caminho."
    )
    st.stop()

st.divider()

# ── Leitura do Excel ──────────────────────────────────────────────────────────
st.subheader("📊 Leitura do Excel")

t_inicio = time.perf_counter()
try:
    xls = pd.ExcelFile(RTD_PATH, engine="openpyxl")
    abas = xls.sheet_names
    t_leitura = time.perf_counter() - t_inicio

    st.success(
        f"✅ Arquivo lido em **{t_leitura*1000:.0f} ms** · "
        f"Abas encontradas: **{', '.join(abas)}**"
    )

    # Resumo por aba
    resumo = {}
    dfs = {}
    for aba in abas:
        try:
            df_tmp = pd.read_excel(xls, sheet_name=aba, header=0, engine="openpyxl")
            resumo[aba] = {"linhas": len(df_tmp), "colunas": len(df_tmp.columns)}
            dfs[aba] = df_tmp
        except Exception as e:
            resumo[aba] = {"erro": str(e)}

    cols_res = st.columns(len(abas))
    for i, aba in enumerate(abas):
        if "erro" in resumo[aba]:
            cols_res[i].error(f"Aba **{aba}**: {resumo[aba]['erro']}")
        else:
            cols_res[i].metric(f"Aba [{aba}]", f"{resumo[aba]['linhas']} linhas")
            cols_res[i].caption(f"{resumo[aba]['colunas']} colunas")

except Exception as e:
    st.error(f"❌ Erro ao ler o Excel: {e}")
    st.exception(e)
    st.stop()

# ── Classificação automática de todos os tickers ────────────────────────────
st.subheader("🎯 Classificação de Tickers")
opt_tickers = _load_option_tickers()

class_counts: dict[str, int] = {
    "ACAO": 0,
    "OPCAO": 0,
    "FUTURO": 0,
    "INDICE": 0,
    "OUTRO": 0,
}

# Classificar todos os tickers de todas as abas
ticker_class_map: dict[str, str] = {}
for aba, df_aba in dfs.items():
    for val in df_aba.iloc[:, 0].dropna():
        tk = str(val).strip().upper()
        if not tk or tk == "NAN":
            continue
        if tk not in ticker_class_map:
            ticker_class_map[tk] = classify_ticker(tk, opt_tickers)
            class_counts[ticker_class_map[tk]] += 1

col_cl1, col_cl2, col_cl3, col_cl4, col_cl5, col_cl6 = st.columns(6)
for col, label, count in [
    (col_cl1, "Ações", class_counts["ACAO"]),
    (col_cl2, "Opções", class_counts["OPCAO"]),
    (col_cl3, "Futuros", class_counts["FUTURO"]),
    (col_cl4, "Índices", class_counts["INDICE"]),
    (col_cl5, "Outros", class_counts["OUTRO"]),
    (col_cl6, "Total", sum(class_counts.values())),
]:
    cor = (
        "#22D3EE"
        if label == "Ações"
        else (
            "#EAB308"
            if label == "Opções"
            else (
                "#22C55E"
                if label == "Futuros"
                else "#94A3B8" if label != "Total" else "#F1F5F9"
            )
        )
    )
    with col:
        st.metric(label, count)

st.divider()

st.divider()

# ── Seletor de aba ────────────────────────────────────────────────────────────
aba_sel = st.selectbox("Selecionar aba", abas, key="rtd_aba_sel")
df = dfs.get(aba_sel, pd.DataFrame())

if df.empty:
    st.warning(f"Aba **{aba_sel}** está vazia ou não foi carregada.")
    st.stop()

# ── Busca por ticker ──────────────────────────────────────────────────────────
st.subheader("🔍 Busca por Ticker")

ticker_col = None
for candidate in ["Asset", "Ativo", "Ticker", "Symbol", "Código"]:
    if candidate in df.columns:
        ticker_col = candidate
        break

if ticker_col is None:
    st.warning(
        "⚠️ Coluna de ticker não encontrada. "
        f"Colunas disponíveis: `{list(df.columns[:20])}`"
    )
else:
    ticker_input = (
        st.text_input(
            "Digite o ticker (ex: PETR4, PETRF469, WINFUT, VALEF856)",
            key="rtd_ticker_input",
        )
        .strip()
        .upper()
    )

    if ticker_input:
        mask = df[ticker_col].astype(str).str.upper() == ticker_input
        df_encontrado = df[mask]

        if df_encontrado.empty:
            st.error(
                f"❌ Ticker **{ticker_input}** **não encontrado** no arquivo RTD lido.\n\n"
                f"Tickers disponíveis na aba **{aba_sel}** (primeiros 30): "
                f"`{list(df[ticker_col].astype(str).head(30).values)}`"
            )
        else:
            st.success(
                f"✅ Ticker **{ticker_input}** encontrado — {len(df_encontrado)} linha(s)"
            )

            # Campos principais se existirem
            cols_presentes = [c for c in COLS_PRINCIPAIS if c in df_encontrado.columns]
            cols_faltantes = [
                c for c in COLS_PRINCIPAIS if c not in df_encontrado.columns
            ]

            if cols_presentes:
                st.markdown("**Campos principais:**")
                st.dataframe(
                    df_encontrado[cols_presentes].reset_index(drop=True),
                    use_container_width=True,
                )

            if cols_faltantes:
                st.caption(f"Campos não presentes nesta aba: `{cols_faltantes}`")

            st.markdown("**Linha completa (todos os campos):**")
            st.dataframe(df_encontrado.reset_index(drop=True), use_container_width=True)

st.divider()

# ── Tabela bruta completa COM classe_detectada ───────────────────────────────
st.subheader(f"📋 Tabela Bruta — Aba [{aba_sel}] + classe_detectada")
st.caption(f"{len(df)} linhas × {len(df.columns)+1} colunas · exibindo até 300 linhas")

# Adicionar coluna classe_detectada
df_disp = df.copy()
ticker_vals = df_disp.iloc[:, 0].astype(str).str.strip().str.upper()


def _map_class(val):
    if pd.isna(val) or str(val).strip().upper() in ("", "NAN"):
        return "—"
    tk = str(val).strip().upper()
    return ticker_class_map.get(tk, "OUTRO")


df_disp["classe_detectada"] = df_disp.iloc[:, 0].apply(_map_class)

# Color mapping
CLS_COR = {
    "ACAO": "#22D3EE",
    "OPCAO": "#EAB308",
    "FUTURO": "#22C55E",
    "INDICE": "#94A3B8",
    "OUTRO": "#475569",
    "—": "#334155",
}
CLS_BG = {
    "ACAO": "#0C2538",
    "OPCAO": "#1C1408",
    "FUTURO": "#052016",
    "INDICE": "#1A1A1A",
    "OUTRO": "#0F172A",
    "—": "#0F172A",
}

# Reorder: classe_detectada first after ticker
cols_order = ["classe_detectada"] + [
    c for c in df_disp.columns if c != "classe_detectada"
]
df_disp = df_disp[cols_order]


# Apply styling
def _cls_style(val):
    if val not in CLS_COR:
        val = "OUTRO"
    return f"color:{CLS_COR.get(val,'#94A3B8')};font-weight:700;background:{CLS_BG.get(val,'#0F172A')};padding:2px 8px;border-radius:4px;"


n_exibir = min(300, len(df_disp))
st.dataframe(
    df_disp.head(n_exibir),
    use_container_width=True,
    height=500,
    column_config={
        "classe_detectada": st.column_config.TextColumn("classe", width="small")
    },
)
st.markdown(
    """
**Código de cores:** 
<span style="color:#22D3EE;font-weight:700;">ACAO</span> ·
<span style="color:#EAB308;font-weight:700;">OPCAO</span> ·
<span style="color:#22C55E;font-weight:700;">FUTURO</span> ·
<span style="color:#94A3B8;font-weight:700;">INDICE</span> ·
<span style="color:#475569;font-weight:700;">OUTRO</span>
""",
    unsafe_allow_html=True,
)

if len(df) > 300:
    st.caption(f"⚠️ Exibindo 300 de {len(df)} linhas totais.")

# ── Todas as colunas disponíveis ──────────────────────────────────────────────
with st.expander("🗂 Todas as colunas desta aba"):
    for i, col in enumerate(df.columns):
        st.write(f"`[{i}]` {col}")

# ── Diagnóstico final ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🩺 Diagnóstico")

diag_items = []

# Verificar se o arquivo foi modificado há mais de 5 minutos
delta_min = (datetime.datetime.now() - dt_modif).total_seconds() / 60
if delta_min > 5:
    diag_items.append(
        f"⚠️ Arquivo não foi modificado há **{delta_min:.1f} minutos**. "
        "O Profit pode ter parado de atualizar o Excel."
    )
else:
    diag_items.append(
        f"✅ Arquivo atualizado há **{delta_min:.1f} minutos** — Profit parece ativo."
    )

# Verificar coluna Asset / ticker
if ticker_col:
    n_tickers = df[ticker_col].dropna().nunique()
    diag_items.append(
        f"✅ Coluna de ticker: `{ticker_col}` · {n_tickers} ativos únicos na aba **{aba_sel}**"
    )
else:
    diag_items.append(
        "❌ Coluna de ticker **não encontrada** — verifique o nome da coluna no Excel."
    )

# Verificar aba Opções
if "Opções" in dfs:
    df_opc = dfs["Opções"]
    if df_opc.empty or (len(df_opc) <= 1 and len(df_opc.columns) <= 1):
        diag_items.append(
            "⚠️ Aba **Opções** parece vazia (1 linha × 1 coluna). "
            "Se o Profit exporta opções, verifique a configuração do RTD."
        )
    else:
        diag_items.append(
            f"✅ Aba Opções: {len(df_opc)} linhas × {len(df_opc.columns)} colunas"
        )

for item in diag_items:
    st.markdown(item)

st.divider()
st.caption(
    "**Como testar:** (1) anote um valor em **Último** de qualquer ticker; "
    "(2) verifique que o Profit está rodando e o Excel está sendo atualizado; "
    "(3) clique **⟳ Ler arquivo agora** e veja se o valor mudou. "
    "Se não mudou, o Profit pode não estar gravando valores no arquivo (só fórmulas RTD que precisam do Excel aberto)."
)
