"""
Trading Desk — Tela Única de Decisão em Tempo Real

Fonte: data/realtime/RTD PROFIT.xlsx (RTD Profit, lido direto)
Regras:
  - Sem mocks
  - Sem cálculo de fair value
  - Sem escrita em banco
  - Se dado indisponível → mostra "indisponível" com motivo
  - Sinais gerados apenas de dados reais presentes no RTD
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import re

# ── Path setup ─────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
import pandas as pd

from src.ui.styles import PREMIUM_CSS

# ── Config ─────────────────────────────────────────────────────────────────────
RTD_PATH = SCANNER_ROOT / "data" / "realtime" / "RTD PROFIT.xlsx"
RTD_SHEET = "Planilha1"

# Limiares de liquidez
VOL_ALTA      = 50_000_000   # R$ 50M → alta liquidez
VOL_MEDIA     = 5_000_000    # R$ 5M  → liquidez mínima aceitável
NEGOCIOS_MIN  = 500          # mínimo de negócios para contar como líquido

# Thresholds técnicos
RSI_SOBRECOMPRADO = 68
RSI_SOBREVENDIDO  = 33
STOCH_SOBRECOMPRADO = 75
STOCH_SOBREVENDIDO  = 25
ADX_TENDENCIA  = 30
ADX_FORTE      = 50
BOLL_TOPO      = 75
BOLL_BASE      = 25

# ── Helpers de parse ───────────────────────────────────────────────────────────

def _parse_br(value) -> Optional[float]:
    """Converte '53,00' ou '1.234,56' ou float/int para float. Retorna None se falhar."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            v = float(value)
            return None if (v != v) else v  # NaN check
        except Exception:
            return None
    s = str(value).strip()
    if s in ("-", "", "nan", "None", "NaN"):
        return None
    # Remove R$, %
    s = s.replace("R$", "").replace("%", "").strip()
    # Remove pontuação de milhar e converte vírgula decimal
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _parse_first(value) -> Optional[float]:
    """Extrai o primeiro número de formatos como '25,21 / 23,33' → 25.21"""
    if value is None:
        return None
    s = str(value).strip()
    if s in ("-", "", "nan"):
        return None
    part = s.split("/")[0].strip()
    return _parse_br(part)


def _parse_nelogica(value) -> Optional[float]:
    """Extrai '5,56 / -14,00' → 5.56 (lado positivo = bullish)"""
    return _parse_first(value)


# ── Leitura do RTD ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def _load_rtd() -> tuple[pd.DataFrame, str, str]:
    """
    Retorna (df_normalizado, status, motivo_erro).
    status: "ok" | "erro" | "arquivo_nao_encontrado"
    """
    if not RTD_PATH.exists():
        return pd.DataFrame(), "arquivo_nao_encontrado", f"Arquivo não encontrado: {RTD_PATH}"
    try:
        df = pd.read_excel(RTD_PATH, sheet_name=RTD_SHEET, header=0)
        return df, "ok", ""
    except Exception as e:
        return pd.DataFrame(), "erro", str(e)


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Parseia todas as colunas relevantes para float."""
    col_map = {
        "Asset":                    "ticker",
        "Data":                     "data",
        "Hora":                     "hora",
        "Último":                   "preco",
        "Abertura":                 "abertura",
        "Máximo":                   "maximo",
        "Mínimo":                   "minimo",
        "Fechamento Anterior":      "fech_ant",
        "Variação":                 "variacao_pct",
        "Volume":                   "volume",
        "Negócios":                 "negocios",
        "Of. Compra":               "bid",
        "Of. Venda":                "ask",
        "VWAP":                     "vwap",
        "IFR (RSI)":                "rsi",
        "MACD Histograma":          "macd_hist",
        "ADX":                      "adx",
        "Bollinger b%":             "boll_b",
        "Estocástico Lento":        "stoch",
        "HiLo Activator":           "hilo",
        "Fura-Chão":                "fura_chao",
        "Fura-Teto":                "fura_teto",
        "Volatilidade Histórica":   "vol_hist",
        "Frasson ATR":              "frasson_atr",
        "Bull Power":               "bull_power",
        "Bear Power":               "bear_power",
        "Momentum":                 "momentum",
        "Nelogica - Bottom Finder": "nelogica_bottom",
        "Nelogica - Pullback Finder": "nelogica_pullback",
        "VWAP Semanal":             "vwap_semanal",
        "Nome do Ativo":            "nome",
        "Strike":                   "strike",
        "Vencimento":               "vencimento",
        "Black Scholes":            "black_scholes",
        "Volt. Implícita":          "iv",
        "Delta":                    "delta",
    }

    out = pd.DataFrame()
    for orig, novo in col_map.items():
        if orig in df.columns:
            out[novo] = df[orig]
        else:
            out[novo] = None

    # Parse floats — colunas numéricas simples
    float_cols = [
        "preco", "abertura", "maximo", "minimo", "fech_ant",
        "variacao_pct", "volume", "negocios", "bid", "ask",
        "vwap", "vwap_semanal",
        "rsi", "macd_hist", "adx", "boll_b", "stoch",
        "hilo", "fura_chao", "fura_teto",
        "vol_hist", "bull_power", "bear_power", "momentum", "strike",
    ]
    for col in float_cols:
        if col in out.columns:
            out[col] = out[col].apply(_parse_br)

    # Parse colunas compostas ("X / Y")
    if "frasson_atr" in out.columns:
        out["frasson_atr"] = out["frasson_atr"].apply(_parse_first)
    if "nelogica_bottom" in out.columns:
        out["nelogica_bottom"] = out["nelogica_bottom"].apply(_parse_first)
    if "nelogica_pullback" in out.columns:
        out["nelogica_pullback"] = out["nelogica_pullback"].apply(_parse_first)

    # Filtrar linhas sem ticker
    out = out[out["ticker"].notna() & (out["ticker"].astype(str).str.strip() != "")]
    out["ticker"] = out["ticker"].astype(str).str.strip()

    return out.reset_index(drop=True)


# ── Motor de sinal ─────────────────────────────────────────────────────────────

def _calcular_sinal(row: pd.Series) -> dict:
    """
    Calcula score, direção, gatilho, risco e próxima ação para um ativo.
    Retorna dict com todos os campos necessários para a tabela.
    """
    ticker  = row.get("ticker", "")
    preco   = row.get("preco")
    vol     = row.get("volume")
    neg     = row.get("negocios")
    var     = row.get("variacao_pct")
    rsi     = row.get("rsi")
    macd    = row.get("macd_hist")
    adx     = row.get("adx")
    boll    = row.get("boll_b")
    stoch   = row.get("stoch")
    vwap    = row.get("vwap")
    hilo    = row.get("hilo")
    fura_c  = row.get("fura_chao")
    fura_t  = row.get("fura_teto")
    vh      = row.get("vol_hist")
    bull    = row.get("bull_power")
    bear    = row.get("bear_power")
    mom     = row.get("momentum")
    bid     = row.get("bid")
    ask     = row.get("ask")

    # ── 1. Verificação de dados mínimos ───────────────────────────────────────
    sem_preco = (preco is None or preco <= 0)
    if sem_preco:
        return {
            "score": 0, "direcao": "—", "gatilho": "Sem preço",
            "risco": "—", "proxima_acao": "Sem dados suficientes",
            "acao_cor": "gray", "motivos": "Preço indisponível no RTD",
            "spread_pct": None, "vol_label": "—",
        }

    # ── 2. Liquidez ────────────────────────────────────────────────────────────
    vol_ok  = (vol is not None and vol >= VOL_MEDIA)
    vol_alta = (vol is not None and vol >= VOL_ALTA)
    neg_ok  = (neg is not None and neg >= NEGOCIOS_MIN)
    liquida = vol_ok and neg_ok

    if vol is None:
        vol_label = "s/dado"
    elif vol >= VOL_ALTA:
        vol_label = f"R${vol/1e6:.0f}M 🟢"
    elif vol >= VOL_MEDIA:
        vol_label = f"R${vol/1e6:.1f}M 🟡"
    else:
        vol_label = f"R${vol/1e3:.0f}K 🔴"

    # ── 3. Spread bid/ask ──────────────────────────────────────────────────────
    spread_pct = None
    if bid is not None and ask is not None and bid > 0:
        spread_pct = round((ask - bid) / bid * 100, 2)

    # ── 4. Score técnico ───────────────────────────────────────────────────────
    score = 0
    gatilhos = []
    alertas  = []

    # RSI (peso 25)
    rsi_ok = rsi is not None
    if rsi_ok:
        if rsi <= RSI_SOBREVENDIDO:
            score += 25
            gatilhos.append(f"RSI {rsi:.0f} — sobrevendido")
        elif rsi >= RSI_SOBRECOMPRADO:
            score -= 20
            alertas.append(f"RSI {rsi:.0f} — sobrecomprado")
        elif 38 <= rsi <= 58:
            score += 5  # zona neutra favorável

    # MACD histograma (peso 20)
    macd_ok = macd is not None
    if macd_ok:
        if macd > 0.05:
            score += 20
            gatilhos.append("MACD positivo")
        elif macd > 0:
            score += 10
            gatilhos.append("MACD levemente positivo")
        elif macd < -0.05:
            score -= 20
            alertas.append("MACD negativo")
        else:
            score -= 5

    # Preço vs VWAP (peso 12)
    if vwap is not None and vwap > 0:
        if preco >= vwap * 1.005:
            score += 12
            gatilhos.append("Acima do VWAP")
        elif preco <= vwap * 0.995:
            score -= 8
            alertas.append("Abaixo do VWAP")
        else:
            score += 4  # próximo ao VWAP

    # ADX — força da tendência (peso 10 extra)
    adx_ok = adx is not None
    if adx_ok and adx >= ADX_TENDENCIA:
        if score > 0:
            score += 10  # tendência reforça sinal bullish
        else:
            score -= 10  # tendência reforça sinal bearish

    # Bollinger b% (peso 15)
    boll_ok = boll is not None
    if boll_ok:
        if boll <= BOLL_BASE:
            score += 15
            gatilhos.append(f"Bollinger b% {boll:.0f} — zona de suporte")
        elif boll >= BOLL_TOPO:
            score -= 12
            alertas.append(f"Bollinger b% {boll:.0f} — zona de resistência")
        elif 40 <= boll <= 65:
            score += 5  # zona saudável de tendência

    # Estocástico (peso 10)
    if stoch is not None:
        if stoch <= STOCH_SOBREVENDIDO:
            score += 10
            gatilhos.append(f"Estoch {stoch:.0f} — sobrevendido")
        elif stoch >= STOCH_SOBRECOMPRADO:
            score -= 8
            alertas.append(f"Estoch {stoch:.0f} — sobrecomprado")

    # HiLo Activator (peso 8) — sinal de tendência
    if hilo is not None and preco > 0:
        if preco > hilo:
            score += 8
            gatilhos.append("Acima do HiLo — tendência alta")
        else:
            score -= 8
            alertas.append("Abaixo do HiLo — tendência baixa")

    # Fura-Teto / Fura-Chão — rompimentos (peso 12)
    if fura_t is not None and preco > fura_t:
        score += 12
        gatilhos.append("Rompimento do teto 🔺")
    if fura_c is not None and preco < fura_c:
        score -= 12
        alertas.append("Rompimento do chão 🔻")

    # Bull/Bear Power (peso 8)
    if bull is not None and bear is not None:
        if bull > 0 and bear > 0:
            score += 8
            gatilhos.append("Bull Power positivo")
        elif bull < 0 and bear < 0:
            score -= 8
            alertas.append("Bear Power dominante")

    # Variação intraday (peso 5)
    if var is not None:
        if var >= 1.5:
            score += 5
        elif var <= -1.5:
            score -= 5

    # Clamp score -100..+100
    score = max(-100, min(100, score))

    # ── 5. Direção ─────────────────────────────────────────────────────────────
    # Regras de bloqueio de sinal de venda: sem liquidez ou spread alto → não VENDA
    _pode_vender = liquida and (spread_pct is None or spread_pct < 1.0)

    if score >= 55:
        direcao = "COMPRA"
        direcao_cor = "#22C55E"
    elif score >= 25:
        direcao = "OBSERVAR"
        direcao_cor = "#EAB308"
    elif score >= -20:
        direcao = "NEUTRO"
        direcao_cor = "#94A3B8"
    elif score >= -50:
        # Fraqueza: com liquidez suficiente → VENDA; sem liquidez → FRAQUEZA genérico
        if _pode_vender and sum([
            macd is not None and macd < -0.05,
            vwap is not None and preco < vwap,
            hilo is not None and preco < hilo,
        ]) >= 2:
            direcao = "VENDA"
            direcao_cor = "#EF4444"
        else:
            direcao = "FRAQUEZA"
            direcao_cor = "#F97316"
    else:
        # Score muito negativo → EVITAR (sem short side se liquidez baixa)
        if _pode_vender:
            direcao = "VENDA"
            direcao_cor = "#EF4444"
        else:
            direcao = "EVITAR"
            direcao_cor = "#7F1D1D"

    # Proteção: alta volatilidade histórica + direcao neutra ou fraca
    if vh is not None and vh >= 60 and score < 25 and score > -50 and not _pode_vender:
        direcao = "PROTEÇÃO"
        direcao_cor = "#3B82F6"

    # ── 6. Gatilho principal ───────────────────────────────────────────────────
    if gatilhos:
        gatilho_txt = gatilhos[0]  # mais relevante
    elif alertas:
        gatilho_txt = alertas[0]
    else:
        gatilho_txt = "Sem gatilho claro"

    # ── 7. Risco ───────────────────────────────────────────────────────────────
    if vh is not None:
        if vh >= 60:
            risco_txt = f"Alto ({vh:.0f}% VH)"
        elif vh >= 35:
            risco_txt = f"Médio ({vh:.0f}% VH)"
        else:
            risco_txt = f"Baixo ({vh:.0f}% VH)"
    else:
        risco_txt = "Indisponível"

    # ── 8. Próxima Ação ────────────────────────────────────────────────────────
    # Regras explícitas: precisa de preço + liquidez + sinal técnico + risco + gatilho

    sem_liquidez = not liquida
    sem_tecnicos = (not rsi_ok and not macd_ok and not boll_ok)

    if sem_preco:
        prox_acao = "Sem dados suficientes"
        acao_cor  = "gray"
    elif sem_tecnicos:
        prox_acao = "Sem dados suficientes"
        acao_cor  = "gray"
    elif sem_liquidez:
        prox_acao = "Aguardar liquidez"
        acao_cor  = "orange"
    elif direcao == "COMPRA" and len(gatilhos) >= 2:
        prox_acao = "Operar compra agora"
        acao_cor  = "green"
    elif score >= 30 and liquida:
        prox_acao = "Monitorar compra"
        acao_cor  = "yellow"
    elif direcao == "VENDA" and liquida:
        prox_acao = "Monitorar venda / reduzir exposição"
        acao_cor  = "red"
    elif direcao == "FRAQUEZA":
        prox_acao = "Evitar compra — avaliar saída gradual"
        acao_cor  = "orange"
    elif direcao == "PROTEÇÃO":
        prox_acao = "Avaliar proteção / put"
        acao_cor  = "blue"
    elif direcao == "EVITAR":
        prox_acao = "Evitar — estrutura frágil"
        acao_cor  = "red"
    elif score >= 0:
        prox_acao = "Aguardar gatilho"
        acao_cor  = "blue"
    else:
        prox_acao = "Aguardar definição de direção"
        acao_cor  = "blue"

    motivos_txt = "; ".join(gatilhos + alertas) if (gatilhos or alertas) else "Sem sinais identificados"

    return {
        "score":        score,
        "direcao":      direcao,
        "direcao_cor":  direcao_cor,
        "gatilho":      gatilho_txt,
        "risco":        risco_txt,
        "proxima_acao": prox_acao,
        "acao_cor":     acao_cor,
        "motivos":      motivos_txt,
        "spread_pct":   spread_pct,
        "vol_label":    vol_label,
    }


# ── Cores e badges ─────────────────────────────────────────────────────────────

_ACAO_COLORS = {
    "Operar agora":       ("#14532D", "#22C55E", "#166534"),
    "Monitorar entrada":  ("#713F12", "#EAB308", "#854D0E"),
    "Aguardar gatilho":   ("#1E3A5F", "#60A5FA", "#1E40AF"),
    "Aguardar liquidez":  ("#431407", "#F97316", "#7C2D12"),
    "Evitar":             ("#450A0A", "#EF4444", "#7F1D1D"),
    "Sem dados suficientes": ("#1E293B", "#64748B", "#334155"),
}

def _acao_badge(label: str) -> str:
    bg, fg, border = _ACAO_COLORS.get(label, _ACAO_COLORS["Sem dados suficientes"])
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:99px;'
        f'background:{bg};color:{fg};border:1px solid {border};'
        f'font-size:0.68rem;font-weight:700;white-space:nowrap;">{label}</span>'
    )

def _dir_badge(label: str, cor: str) -> str:
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:rgba(255,255,255,0.05);color:{cor};'
        f'font-size:0.72rem;font-weight:800;">{label}</span>'
    )

def _score_bar(score: int) -> str:
    """Mini barra de score visual -100..+100"""
    clamped = max(-100, min(100, score))
    pct = (clamped + 100) / 2  # 0..100 para CSS width
    if clamped >= 50:
        color = "#22C55E"
    elif clamped >= 20:
        color = "#EAB308"
    elif clamped >= -20:
        color = "#94A3B8"
    else:
        color = "#EF4444"
    return (
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="width:60px;height:6px;background:#1E293B;border-radius:99px;overflow:hidden;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:99px;"></div></div>'
        f'<span style="font-size:0.72rem;color:{color};font-weight:700;">{clamped:+d}</span>'
        f'</div>'
    )


# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.td-header {
    background: linear-gradient(135deg, #0A1628 0%, #0D1B2A 100%);
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 16px;
}
.td-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.4rem;
    font-weight: 900;
    color: #F1F5F9;
    letter-spacing: -0.5px;
}
.td-title span { color: #22D3EE; }
.td-status-ok  { color: #22C55E; font-weight: 700; }
.td-status-err { color: #EF4444; font-weight: 700; }
.td-kpis {
    display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px;
}
.td-kpi {
    background: #0F1F35;
    border: 1px solid #1E2D42;
    border-radius: 8px;
    padding: 8px 14px;
    min-width: 100px;
}
.td-kpi-label { font-size: 0.6rem; color: #475569; text-transform: uppercase; letter-spacing: 1px; }
.td-kpi-val   { font-size: 1.2rem; font-weight: 800; color: #F1F5F9; margin-top: 2px; }
.td-kpi-sub   { font-size: 0.65rem; color: #64748B; margin-top: 1px; }
.td-table-wrap {
    background: #0A1220;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 8px;
}
.td-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
}
.td-table thead th {
    background: #0D1B2A;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.58rem;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #1E2D42;
    white-space: nowrap;
}
.td-table tbody tr {
    border-bottom: 1px solid rgba(30,45,66,0.5);
    transition: background 0.1s;
}
.td-table tbody tr:hover { background: rgba(34,211,238,0.04); }
.td-table tbody td {
    padding: 8px 12px;
    color: #CBD5E1;
    vertical-align: middle;
    white-space: nowrap;
}
.td-ticker {
    font-weight: 800;
    font-size: 0.82rem;
    color: #F1F5F9;
}
.td-preco { color: #F1F5F9; font-weight: 600; }
.td-var-pos { color: #22C55E; font-weight: 700; }
.td-var-neg { color: #EF4444; font-weight: 700; }
.td-var-neu { color: #94A3B8; }
.td-gatilho { color: #7DD3FC; max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.td-risco   { color: #F59E0B; font-size: 0.68rem; }
.td-vazio {
    text-align: center;
    color: #475569;
    padding: 40px !important;
    font-size: 0.85rem;
}
.td-info-box {
    background: #0F1F35;
    border: 1px solid #1E2D42;
    border-left: 3px solid #3B82F6;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.72rem;
    color: #94A3B8;
    margin-top: 6px;
}
.td-warn-box {
    background: #1C1007;
    border: 1px solid #78350F;
    border-left: 3px solid #F59E0B;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.72rem;
    color: #FCD34D;
    margin-top: 6px;
}
.td-section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #475569;
    margin: 16px 0 6px 2px;
}
</style>
"""

# ── Renderização principal ─────────────────────────────────────────────────────

st.markdown(PREMIUM_CSS + _CSS, unsafe_allow_html=True)

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
raw_df, rtd_status, rtd_erro = _load_rtd()

agora = datetime.now().strftime("%H:%M:%S")
data_rtd = "—"
qtd_ativos = 0
qtd_sinais = 0
qtd_operar = 0

df_norm = pd.DataFrame()

if rtd_status == "ok" and not raw_df.empty:
    df_norm = _normalizar(raw_df)
    # Filtra derivativos futuros / índices puros por padrão (mantém IBOVX100 para opções)
    # mas ações são o foco agora
    acao_mask = ~df_norm["ticker"].str.contains("FUT|IBOV$|SMLL$|VXBR|ISEE", regex=True, na=False)
    df_ativos = df_norm[acao_mask].copy()
    qtd_ativos = len(df_ativos)

    # Data do RTD
    if "data" in df_ativos.columns:
        data_val = df_ativos["data"].dropna().iloc[0] if len(df_ativos) > 0 else None
        if data_val is not None:
            try:
                data_rtd = pd.to_datetime(str(data_val)).strftime("%d/%m/%Y")
            except Exception:
                data_rtd = str(data_val)

    # Hora
    if "hora" in df_ativos.columns:
        hora_val = df_ativos["hora"].dropna().iloc[0] if len(df_ativos) > 0 else None
        if hora_val is not None:
            try:
                agora_rtd = str(hora_val)[:8]
                data_rtd = f"{data_rtd} {agora_rtd}"
            except Exception:
                pass

    # Calcular sinais
    sinais = []
    for _, row in df_ativos.iterrows():
        s = _calcular_sinal(row)
        sinais.append({**row.to_dict(), **s})
    df_sinais = pd.DataFrame(sinais)
    qtd_sinais = int((df_sinais["score"] >= 25).sum()) if len(df_sinais) > 0 else 0
    qtd_operar = int((df_sinais["proxima_acao"] == "Operar agora").sum()) if len(df_sinais) > 0 else 0
    qtd_monitorar = int((df_sinais["proxima_acao"] == "Monitorar entrada").sum()) if len(df_sinais) > 0 else 0
else:
    df_ativos  = pd.DataFrame()
    df_sinais  = pd.DataFrame()
    qtd_monitorar = 0

# ── Header HTML ───────────────────────────────────────────────────────────────
status_html = (
    '<span class="td-status-ok">● CONECTADO</span>' if rtd_status == "ok"
    else f'<span class="td-status-err">✕ {rtd_status.upper()}</span>'
)

st.markdown(f"""
<div class="td-header">
    <div class="td-title">TRADING <span>DESK</span></div>
    <div style="font-size:0.7rem;color:#475569;margin-top:2px;font-family:'JetBrains Mono',monospace;">
        RTD Profit · Decisão em Tempo Real · {data_rtd}
    </div>
    <div class="td-kpis">
        <div class="td-kpi">
            <div class="td-kpi-label">RTD Status</div>
            <div style="font-size:0.85rem;margin-top:4px;">{status_html}</div>
            <div class="td-kpi-sub">Última leitura: {agora}</div>
        </div>
        <div class="td-kpi">
            <div class="td-kpi-label">Ativos Lidos</div>
            <div class="td-kpi-val">{qtd_ativos}</div>
            <div class="td-kpi-sub">RTD Profit</div>
        </div>
        <div class="td-kpi">
            <div class="td-kpi-label">Com Sinal</div>
            <div class="td-kpi-val">{qtd_sinais}</div>
            <div class="td-kpi-sub">score ≥ 25</div>
        </div>
        <div class="td-kpi">
            <div class="td-kpi-label">Operar Agora</div>
            <div class="td-kpi-val" style="color:#22C55E;">{qtd_operar}</div>
            <div class="td-kpi-sub">todos os critérios OK</div>
        </div>
        <div class="td-kpi">
            <div class="td-kpi-label">Monitorar</div>
            <div class="td-kpi-val" style="color:#EAB308;">{qtd_monitorar}</div>
            <div class="td-kpi-sub">entrada em formação</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Erro RTD ──────────────────────────────────────────────────────────────────
if rtd_status != "ok":
    st.markdown(f"""
    <div class="td-warn-box">
        ⚠️ <strong>RTD indisponível:</strong> {rtd_erro}<br>
        <span style="color:#94A3B8;">
        Arquivo esperado em: <code>{RTD_PATH}</code><br>
        Abra o Profit, certifique-se que a planilha RTD está aberta e salva nesse caminho.
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Filtros ────────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
with col_f1:
    filtro_acao = st.selectbox(
        "Próxima Ação",
        ["Todas", "Operar agora", "Monitorar entrada", "Aguardar gatilho", "Evitar"],
        key="filtro_acao",
    )
with col_f2:
    filtro_dir = st.selectbox(
        "Direção",
        ["Todas", "COMPRA", "OBSERVAR", "NEUTRO", "FRAQUEZA", "EVITAR"],
        key="filtro_dir",
    )
with col_f3:
    filtro_liq = st.selectbox(
        "Liquidez",
        ["Todas", "Alta (≥R$50M)", "Mínima (≥R$5M)"],
        key="filtro_liq",
    )
with col_f4:
    filtro_ordem = st.selectbox(
        "Ordenar por",
        ["Score (maior)", "Score (menor)", "Variação (maior)", "Volume (maior)"],
        key="filtro_ordem",
    )

# ── Aplicar filtros ────────────────────────────────────────────────────────────
df_view = df_sinais.copy() if len(df_sinais) > 0 else pd.DataFrame()

if len(df_view) > 0:
    if filtro_acao != "Todas":
        df_view = df_view[df_view["proxima_acao"] == filtro_acao]
    if filtro_dir != "Todas":
        df_view = df_view[df_view["direcao"] == filtro_dir]
    if filtro_liq == "Alta (≥R$50M)":
        df_view = df_view[df_view["volume"].fillna(0) >= VOL_ALTA]
    elif filtro_liq == "Mínima (≥R$5M)":
        df_view = df_view[df_view["volume"].fillna(0) >= VOL_MEDIA]

    if filtro_ordem == "Score (maior)":
        df_view = df_view.sort_values("score", ascending=False)
    elif filtro_ordem == "Score (menor)":
        df_view = df_view.sort_values("score", ascending=True)
    elif filtro_ordem == "Variação (maior)":
        df_view = df_view.sort_values("variacao_pct", ascending=False)
    elif filtro_ordem == "Volume (maior)":
        df_view = df_view.sort_values("volume", ascending=False, na_position="last")

# ── Tabela principal ───────────────────────────────────────────────────────────
st.markdown('<div class="td-section-label">Tabela de Decisão</div>', unsafe_allow_html=True)

if df_view.empty:
    st.markdown("""
    <div class="td-table-wrap">
        <table class="td-table">
            <tbody><tr><td class="td-vazio">
                Nenhum ativo corresponde aos filtros selecionados.
            </td></tr></tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
else:
    rows_html = ""
    for _, r in df_view.iterrows():
        ticker  = r.get("ticker", "—")
        preco   = r.get("preco")
        var     = r.get("variacao_pct")
        direcao = r.get("direcao", "—")
        dir_cor = r.get("direcao_cor", "#94A3B8")
        score   = r.get("score", 0)
        gatilho = r.get("gatilho", "—")
        risco   = r.get("risco", "—")
        prox    = r.get("proxima_acao", "—")
        vol_lbl = r.get("vol_label", "—")
        nome    = r.get("nome", "")

        # Preço
        preco_html = f"R$ {preco:.2f}" if preco is not None else "—"

        # Variação
        if var is not None:
            var_cls  = "td-var-pos" if var > 0 else ("td-var-neg" if var < 0 else "td-var-neu")
            sinal_v  = "▲" if var > 0 else ("▼" if var < 0 else "")
            var_html = f'<span class="{var_cls}">{sinal_v} {abs(var):.2f}%</span>'
        else:
            var_html = '<span class="td-var-neu">—</span>'

        rows_html += f"""
        <tr>
            <td><div class="td-ticker">{ticker}</div>
                <div style="font-size:0.58rem;color:#475569;max-width:100px;overflow:hidden;text-overflow:ellipsis;">{str(nome)[:22]}</div>
            </td>
            <td class="td-preco">{preco_html}</td>
            <td>{var_html}</td>
            <td>{vol_lbl}</td>
            <td>{_dir_badge(direcao, dir_cor)}</td>
            <td>{_score_bar(int(score))}</td>
            <td class="td-gatilho">{gatilho}</td>
            <td class="td-risco">{risco}</td>
            <td>{_acao_badge(prox)}</td>
        </tr>
        """

    st.markdown(f"""
    <div class="td-table-wrap">
        <table class="td-table">
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Preço</th>
                    <th>Variação</th>
                    <th>Liquidez</th>
                    <th>Direção</th>
                    <th>Score</th>
                    <th>Gatilho</th>
                    <th>Risco</th>
                    <th>Próxima Ação</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ── Diagnóstico de opções ──────────────────────────────────────────────────────
st.markdown('<div class="td-section-label">Diagnóstico — Opções & Derivativos</div>', unsafe_allow_html=True)

# Verificar opções no RTD
df_opts = df_norm[df_norm["strike"].fillna(0) > 0] if len(df_norm) > 0 else pd.DataFrame()
qtd_futuros = len(df_norm[df_norm["ticker"].str.contains("FUT|WDOFUT|DOLFUT|DDIFUT|DI1FUT|WINFUT", na=False)]) if len(df_norm) > 0 else 0

col_d1, col_d2, col_d3 = st.columns(3)
with col_d1:
    st.markdown("""
    <div class="td-kpi">
        <div class="td-kpi-label">Opções no RTD</div>
        <div class="td-kpi-val" style="color:#F59E0B;">0</div>
        <div class="td-kpi-sub">Nenhuma série configurada ainda</div>
    </div>
    """, unsafe_allow_html=True)
with col_d2:
    st.markdown(f"""
    <div class="td-kpi">
        <div class="td-kpi-label">Futuros no RTD</div>
        <div class="td-kpi-val" style="color:#60A5FA;">{qtd_futuros}</div>
        <div class="td-kpi-sub">WDOFUT, DOLFUT, WINFUT, DI1</div>
    </div>
    """, unsafe_allow_html=True)
with col_d3:
    st.markdown("""
    <div class="td-kpi">
        <div class="td-kpi-label">Cotahist B3</div>
        <div class="td-kpi-val" style="color:#EF4444;">0 linhas</div>
        <div class="td-kpi-sub">Sem histórico de opções ingerido</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="td-info-box">
    <strong style="color:#60A5FA;">ℹ️ Por que não há opções?</strong><br>
    O RTD atual contém 88 ações e contratos futuros. Opções requerem:<br>
    1. <strong>Cotahist B3</strong> ingerida (cotahist_daily está vazia) → para descobrir o universo<br>
    2. <strong>Shortlist RTD</strong> configurada no Profit com os tickers de opção (ex: PETRX35, PETRX40...)<br>
    3. Nenhum dado de Black Scholes, Delta, Gama, Theta está disponível ainda<br><br>
    <strong style="color:#22C55E;">Próximo passo:</strong>
    Execute o coletor B3 COTAHIST para popular a tabela de histórico de opções,
    depois gere a shortlist via <code>src/scanners/options_rtd_watchlist_builder.py</code>.
</div>
""", unsafe_allow_html=True)

# ── Legenda das regras ─────────────────────────────────────────────────────────
with st.expander("📋 Regras de sinal — como a Próxima Ação é calculada"):
    st.markdown("""
    **Fontes usadas:** RTD Profit (`data/realtime/RTD PROFIT.xlsx`) — leitura direta, sem banco.

    | Campo | Fonte RTD | Critério |
    |---|---|---|
    | RSI | `IFR (RSI)` | < 33 = sobrevendido (+25pts) · > 68 = sobrecomprado (-20pts) |
    | MACD | `MACD Histograma` | > 0.05 = bullish (+20pts) · < -0.05 = bearish (-20pts) |
    | VWAP | `VWAP` | Preço > VWAP = confirmação (+12pts) |
    | ADX | `ADX` | > 30 = tendência válida (amplifica sinal ±10pts) |
    | Bollinger | `Bollinger b%` | < 25 = zona de suporte (+15pts) · > 75 = resistência (-12pts) |
    | Estocástico | `Estocástico Lento` | < 25 = sobrevendido (+10pts) · > 75 = sobrecomprado (-8pts) |
    | HiLo | `HiLo Activator` | Preço > HiLo = tendência alta (+8pts) |
    | Fura-Teto/Chão | `Fura-Teto`, `Fura-Chão` | Rompimento ±12pts |
    | Bull/Bear Power | `Bull Power`, `Bear Power` | Ambos positivos = força (+8pts) |
    | Liquidez | `Volume` + `Negócios` | Mínimo: R$5M e 500 negócios |

    **Próxima Ação:**
    - 🟢 **Operar agora**: score ≥ 55 + liquidez OK + ≥ 2 gatilhos confirmados
    - 🟡 **Monitorar entrada**: score 30-54 + liquidez OK
    - 🔵 **Aguardar gatilho**: score 0-29 ou falta de confirmação
    - 🟠 **Aguardar liquidez**: boa técnica mas volume insuficiente
    - 🔴 **Evitar**: score < -30 (múltiplos sinais negativos)
    - ⚪ **Sem dados suficientes**: sem preço ou sem indicadores técnicos
    """)

# ── Rodapé ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:24px;padding:8px 0;border-top:1px solid #1E2D42;
font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:#334155;
display:flex;justify-content:space-between;">
    <span>Trading Desk · RTD Profit · {RTD_PATH.name}</span>
    <span>Atualizado: {agora} · Cache: 30s</span>
</div>
""", unsafe_allow_html=True)
