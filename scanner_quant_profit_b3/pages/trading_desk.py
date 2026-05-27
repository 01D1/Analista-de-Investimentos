"""
Trading Desk — Tela Operacional em Tempo Real
==============================================
Fontes: RTD PROFIT.xlsx (lido direto) + options_rtd_watchlist.csv

Regras:
  - Sem mocks, sem banco写入
  - Atualização automática configurável
  - Sem valuation, sem CVM, sem pipeline pesado
  - Score, sinal e próxima ação apenas de dados RTD

Tabulação:
  1. Visão Geral     → KPIs + status de conexão + candidatos operacionais
  2. Ações ao Vivo   → 15 colunas: ticker,último,var,vol,neg,bid,ask,spread,vwap,rsi,macd,adx,dir,score,próxima
  3. Opções ao Vivo  → 80 opções da shortlist cruzada com RTD
  4. Futuros ao Vivo → DI1FUT/DOLFUT/WDOFUT/WINFUT
  5. Diagnóstico RTD → arquivo,abas,colunas,tempo,campos vazios,ausentes
"""

from __future__ import annotations

import sys
import time as _time
from pathlib import Path
from datetime import datetime

# ── Path setup (mesma técnica usada em todos os scanners) ──────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Remover contaminação do 12_PYTHON se presente
_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)

# Limpar módulos utils que podem estar cacheados
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
import pandas as pd

from src.dashboard.rtd_live_reader import (
    RTDLiveReader,
    InstrumentPayload,
    InstrumentClass,
    DataStatus,
)
from src.ui.styles import PREMIUM_CSS

# ── Paths ──────────────────────────────────────────────────────────────────────
RTD_PATH = SCANNER_ROOT / "data" / "realtime" / "RTD PROFIT.xlsx"
SHORTLIST_PATH = SCANNER_ROOT / "data" / "realtime" / "options_rtd_watchlist.csv"
SYMBOLS_PATH = SCANNER_ROOT / "data" / "realtime" / "options_rtd_symbols.csv"
HIST_OPP_PATH = SCANNER_ROOT / "data" / "realtime" / "options_historical_opportunities.csv"
WATCHLIST_NEXT_PATH = SCANNER_ROOT / "data" / "realtime" / "options_next_session_watchlist.csv"

# ── Config ─────────────────────────────────────────────────────────────────────
REFRESH_OPTIONS = [5, 10, 30, 60, 0]  # 0 = manual

# Thresholds de liquidez para ações
VOL_ALTA = 50_000_000
VOL_MEDIA = 5_000_000
NEGOCIOS_MIN = 500

# Thresholds técnicos
RSI_SOBREVENDIDO = 33
RSI_SOBRECOMPRADO = 68
ADX_TENDENCIA = 30
BOLL_BASE = 25
BOLL_TOPO = 75

# Thresholds de spread para opções
SPREAD_ALTO_OPCAO = 2.0  # >2% = spread alto
SPREAD_MEDIO_OPCAO = 0.5  # >0.5% = monitorável
VOL_MIN_OPCAO = 100_000  # R$100K ADV mínimo


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* KPI Card */
.td-kpi {
    background: #0F1F35;
    border: 1px solid #1E2D42;
    border-radius: 8px;
    padding: 10px 14px;
    min-width: 110px;
}
.td-kpi-label {
    font-size: 0.58rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.td-kpi-val {
    font-size: 1.3rem;
    font-weight: 800;
    color: #F1F5F9;
    line-height: 1.2;
}
.td-kpi-sub {
    font-size: 0.62rem;
    color: #64748B;
    margin-top: 2px;
}

/* Tabela */
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
    font-size: 0.70rem;
}
.td-table thead th {
    background: #0D1B2A;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.56rem;
    padding: 9px 10px;
    text-align: left;
    border-bottom: 1px solid #1E2D42;
    white-space: nowrap;
}
.td-table tbody tr {
    border-bottom: 1px solid rgba(30,45,66,0.5);
}
.td-table tbody tr:hover { background: rgba(34,211,238,0.04); }
.td-table tbody td {
    padding: 7px 10px;
    color: #CBD5E1;
    vertical-align: middle;
    white-space: nowrap;
}

/* Células */
.td-ticker {
    font-weight: 800;
    font-size: 0.80rem;
    color: #F1F5F9;
}
.td-preco   { color: #F1F5F9; font-weight: 600; }
.td-pos     { color: #22C55E; font-weight: 700; }
.td-neg     { color: #EF4444; font-weight: 700; }
.td-neu     { color: #94A3B8; }
.td-warn    { color: #F97316; }
.td-section {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #475569;
    margin: 14px 0 5px 2px;
}

/* Info/Warn boxes */
.td-info {
    background: #0F1F35;
    border: 1px solid #1E2D42;
    border-left: 3px solid #3B82F6;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.70rem;
    color: #94A3B8;
    margin-top: 6px;
}
.td-warn {
    background: #1C1007;
    border: 1px solid #78350F;
    border-left: 3px solid #F59E0B;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.70rem;
    color: #FCD34D;
    margin-top: 6px;
}
.td-success {
    background: #052e16;
    border: 1px solid #14532d;
    border-left: 3px solid #22C55E;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.70rem;
    color: #86EFAC;
    margin-top: 6px;
}

/* Badge de status */
.badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 99px;
    font-size: 0.60rem;
    font-weight: 700;
    white-space: nowrap;
}
.badge-green   { background:#14532D; color:#22C55E; border:1px solid #166534; }
.badge-yellow  { background:#713F12; color:#EAB308; border:1px solid #854D0E; }
.badge-blue    { background:#1E3A5F; color:#60A5FA; border:1px solid #1E40AF; }
.badge-orange  { background:#431407; color:#F97316; border:1px solid #7C2D12; }
.badge-red     { background:#450A0A; color:#EF4444; border:1px solid #7F1D1D; }
.badge-gray    { background:#1E293B; color:#64748B; border:1px solid #334155; }
.badge-cyan    { background:#083344; color:#22D3EE; border:1px solid #0e7490; }

/* Score bar */
.score-wrap {
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.score-bar {
    width: 56px;
    height: 5px;
    background: #1E293B;
    border-radius: 99px;
    overflow: hidden;
}
.score-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.3s;
}

/* Direção badge */
.dir-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 800;
    background: rgba(255,255,255,0.04);
}

/* Pulsing dot */
.live-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22C55E;
    animation: td-pulse 1.8s ease-in-out infinite;
    box-shadow: 0 0 6px #22C55E;
}
@keyframes td-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.75); }
}

/* Header bar */
.td-header-bar {
    background: linear-gradient(135deg, #0A1628 0%, #0D1B2A 100%);
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
}

/* Overview candidate card */
.cand-card {
    background: #0F1F35;
    border: 1px solid #1E2D42;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
}

/* Diagnostic table */
.diag-ok    { color: #22C55E; }
.diag-warn  { color: #F59E0B; }
.diag-err   { color: #EF4444; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — de src/dashboard/rtd_signals.py
# ─────────────────────────────────────────────────────────────────────────────
from src.dashboard.rtd_signals import (
    _fmt_preco,
    _fmt_vol,
    _fmt_pct,
    _cls_pct,
    _badge,
    _dir_badge,
    _score_html,
    _opcao_status,
    _sinal_acao,
)
from src.dashboard.rtd_signals import (
    VOL_ALTA as _VOL_ALTA,
    VOL_MEDIA as _VOL_MEDIA,
    NEGOCIOS_MIN as _NEGOCIOS_MIN,
    RSI_SOBREVENDIDO,
    RSI_SOBRECOMPRADO,
    ADX_TENDENCIA,
    BOLL_BASE,
    BOLL_TOPO,
    SPREAD_ALTO_OPCAO,
    VOL_MIN_OPCAO,
)
from src.options.rtd_strategy_adapter import (
    run_rtd_strategy_engine,
    classify_market_from_rtd,
    format_strategy_html,
    format_no_strategy_html,
    summarize_rtd_strategies,
    _scenario_label,
)

# Expose module-level constants for rtd_signals (re-export)
VOL_ALTA = _VOL_ALTA
VOL_MEDIA = _VOL_MEDIA
NEGOCIOS_MIN = _NEGOCIOS_MIN


# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=30, show_spinner=False)
def _rtd_all() -> dict[str, InstrumentPayload]:
    return RTDLiveReader(
        rtd_path=RTD_PATH,
        shortlist=SHORTLIST_PATH,
        symbols_path=SYMBOLS_PATH,
    ).read_all()


@st.cache_data(ttl=60, show_spinner=False)
def _shortlist() -> pd.DataFrame:
    if SHORTLIST_PATH.exists():
        return pd.read_csv(SHORTLIST_PATH, dtype=str)
    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def _hist_opportunities() -> pd.DataFrame:
    """Lê options_historical_opportunities.csv (gerado pelo COTAHIST scanner)."""
    if HIST_OPP_PATH.exists():
        try:
            return pd.read_csv(HIST_OPP_PATH, dtype=str)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def _next_session_watchlist() -> pd.DataFrame:
    """Lê options_next_session_watchlist.csv (candidatas/monitorar no próximo pregão)."""
    if WATCHLIST_NEXT_PATH.exists():
        try:
            return pd.read_csv(WATCHLIST_NEXT_PATH, dtype=str)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — Radar Histórico
# ─────────────────────────────────────────────────────────────────────────────

_CENARIO_LABEL: dict[str, str] = {
    "RECUPERACAO_APOS_QUEDA": "↗ Recuperação",
    "CONTINUACAO_ALTA":       "↑ Alta",
    "CONTINUACAO_BAIXA":      "↓ Baixa",
    "PROTECAO_CARTEIRA":      "🛡 Proteção",
    "RENDA_COM_ATIVO":        "💰 Renda",
    "VOLATILIDADE_EM_ALTA":   "⚡ Volatilidade",
    "LATERALIDADE":           "↔ Lateral",
    "SEM_ASSIMETRIA":         "— Sem edge",
}

_CENARIO_BADGE: dict[str, str] = {
    "RECUPERACAO_APOS_QUEDA": "badge-green",
    "CONTINUACAO_ALTA":       "badge-green",
    "CONTINUACAO_BAIXA":      "badge-red",
    "PROTECAO_CARTEIRA":      "badge-blue",
    "RENDA_COM_ATIVO":        "badge-yellow",
    "VOLATILIDADE_EM_ALTA":   "badge-orange",
    "LATERALIDADE":           "badge-gray",
    "SEM_ASSIMETRIA":         "badge-gray",
}

_STATUS_LABEL: dict[str, str] = {
    "CANDIDATA_PROXIMO_PREGAO":   "✅ Candidata",
    "MONITORAR_NO_RTD":           "👁 Monitorar",
    "AGUARDAR_LIQUIDEZ":          "⏳ Aguardar",
    "ESTUDAR":                    "📚 Estudar",
    "DESCARTAR_ILIQUIDA":         "🚫 Ilíquida",
    "DESCARTAR_SEM_ASSIMETRIA":   "🚫 Sem edge",
}

_STATUS_BADGE: dict[str, str] = {
    "CANDIDATA_PROXIMO_PREGAO":   "badge-green",
    "MONITORAR_NO_RTD":           "badge-cyan",
    "AGUARDAR_LIQUIDEZ":          "badge-yellow",
    "ESTUDAR":                    "badge-blue",
    "DESCARTAR_ILIQUIDA":         "badge-red",
    "DESCARTAR_SEM_ASSIMETRIA":   "badge-red",
}

_HORIZONTE_BADGE: dict[str, str] = {
    "CURTO":       "badge-orange",
    "MEDIO":       "badge-yellow",
    "LONGO":       "badge-blue",
    "EXTRA_LONGO": "badge-cyan",
    "EXPIRADO":    "badge-red",
}


def _hist_proxima_acao(status: str, in_rtd: bool, rtd_confirmed: bool) -> tuple[str, str]:
    """Retorna (texto da próxima ação, classe CSS badge)."""
    if status == "CANDIDATA_PROXIMO_PREGAO":
        if rtd_confirmed:
            return "Enviar para motor de estratégias ao vivo", "badge-green"
        if in_rtd:
            return "RTD detectado — confirmar bid/ask", "badge-cyan"
        return "Adicionar ao RTD no próximo pregão", "badge-blue"
    if status == "MONITORAR_NO_RTD":
        if in_rtd:
            return "Monitorar liquidez no RTD", "badge-yellow"
        return "Adicionar ao RTD — monitorar liquidez", "badge-yellow"
    if status == "AGUARDAR_LIQUIDEZ":
        return "Aguardar confirmação técnica", "badge-orange"
    if status == "ESTUDAR":
        return "Aguardar confirmação técnica", "badge-gray"
    if status == "DESCARTAR_ILIQUIDA":
        return "Descartar por iliquidez", "badge-red"
    if status == "DESCARTAR_SEM_ASSIMETRIA":
        return "Descartar por falta de assimetria", "badge-red"
    return "—", "badge-gray"


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None or str(val).strip() in ("", "nan", "NaN", "None"):
            return default
        return float(val)
    except Exception:
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(float(val))
    except Exception:
        return default


def _fmt_score_badge(score: float) -> str:
    if score >= 70:
        cls = "badge-green"
    elif score >= 50:
        cls = "badge-yellow"
    elif score >= 30:
        cls = "badge-orange"
    else:
        cls = "badge-red"
    return f'<span class="badge {cls}">{score:.0f}</span>'


def _fmt_tipo_badge(tipo: str) -> str:
    if tipo.upper() == "CALL":
        return '<span class="badge badge-green">CALL</span>'
    if tipo.upper() == "PUT":
        return '<span class="badge badge-red">PUT</span>'
    return f'<span class="badge badge-gray">{tipo}</span>'


def _fmt_rtd_status(in_rtd: bool, rtd_confirmed: bool) -> str:
    if rtd_confirmed:
        return '<span class="badge badge-green">✓ RTD confirmado</span>'
    if in_rtd:
        return '<span class="badge badge-cyan">No RTD</span>'
    return '<span class="badge badge-gray">Histórico</span>'


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(PREMIUM_CSS + _CSS, unsafe_allow_html=True)

# ── Refresh bar ───────────────────────────────────────────────────────────────
col_hdr1, col_hdr2, col_hdr3 = st.columns([2, 1, 1])
with col_hdr1:
    st.markdown(
        "<div style=\"font-family:'Sora',sans-serif;font-size:1.5rem;"
        'font-weight:900;color:#F1F5F9;letter-spacing:-0.5px;">'
        'TRADE <span style="color:#22D3EE;">DESK</span></div>',
        unsafe_allow_html=True,
    )
with col_hdr2:
    refresh_sec = st.selectbox(
        "🔄 Refresh",
        options=REFRESH_OPTIONS,
        format_func=lambda x: "Manual" if x == 0 else f"{x}s",
        index=1,
        label_visibility="collapsed",
    )
with col_hdr3:
    if st.button("🔄 Atualizar", type="secondary", use_container_width=True):
        st.rerun()

if refresh_sec > 0:
    _time.sleep(refresh_sec)
    st.rerun()

# ── Leitura RTD ───────────────────────────────────────────────────────────────
all_inst = _rtd_all()
shortlist_df = _shortlist()

agora = datetime.now().strftime("%H:%M:%S")
rtd_mtime = (
    datetime.fromtimestamp(RTD_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    if RTD_PATH.exists()
    else "—"
)
rtd_exists = RTD_PATH.exists()

# ── Classificação por classe ─────────────────────────────────────────────────
acoes = {t: p for t, p in all_inst.items() if p.classe == InstrumentClass.ACAO}
futuros = {t: p for t, p in all_inst.items() if p.classe == InstrumentClass.FUTURO}
opcoes = {t: p for t, p in all_inst.items() if p.classe == InstrumentClass.OPCAO}
indices = {t: p for t, p in all_inst.items() if p.classe == InstrumentClass.INDICE}
outros = {t: p for t, p in all_inst.items() if p.classe == InstrumentClass.OUTRO}

# Status counts
ao_vivo = sum(1 for p in all_inst.values() if p.status == DataStatus.AO_VIVO)
sem_preco = sum(1 for p in all_inst.values() if p.status == DataStatus.SEM_PRECO)
sem_bid = sum(1 for p in all_inst.values() if p.status == DataStatus.SEM_BID_ASK)
com_bid = ao_vivo  # AO_VIVO = tem bid+ask

# Shortlist status
rtd_tickers = set(all_inst.keys())
sl_in_rtd = (
    sum(
        1
        for _, r in shortlist_df.iterrows()
        if str(r.get("ticker", "")).strip() in rtd_tickers
    )
    if not shortlist_df.empty
    else 0
)
sl_total = len(shortlist_df) if not shortlist_df.empty else 0

# Candidatos operacionais (ações COMPRA com liquidez)
candidatos = []
for t, p in acoes.items():
    s = _sinal_acao(p)
    if s["dir"] == "COMPRA" and s["prox"] == "Operar agora":
        candidatos.append((t, p, s))

# ── Leitura dados históricos ─────────────────────────────────────────────────
hist_opp_df = _hist_opportunities()
next_sess_df = _next_session_watchlist()

# ── Tabs (7) ──────────────────────────────────────────────────────────────────
(
    tab_overview,
    tab_acao,
    tab_opcao,
    tab_futuro,
    tab_estrategias,
    tab_hist_radar,
    tab_diag,
) = st.tabs(
    [
        "🔭 Visão Geral",
        "📊 Ações ao Vivo",
        "💹 Opções ao Vivo",
        "📈 Futuros ao Vivo",
        "🧠 Estratégias",
        "📡 Radar Histórico",
        "🔍 Diagnóstico RTD",
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
# TAB: VISÃO GERAL
# ═══════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown(
        '<div class="td-section">Painel Executivo RTD</div>', unsafe_allow_html=True
    )

    # Connection status
    col_conn1, col_conn2, col_conn3 = st.columns(3)
    with col_conn1:
        conn_ok = rtd_exists and ao_vivo > 0
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">RTD</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
                <span class="live-dot"></span>
                <span style="font-size:1.0rem;font-weight:800;color:{'#22C55E' if conn_ok else '#EF4444'};">
                    {'CONECTADO' if conn_ok else 'DESCONECTADO'}
                </span>
            </div>
            <div class="td-kpi-sub">{RTD_PATH.name}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    with col_conn2:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Última atualização</div>
            <div style="font-size:1.0rem;font-weight:800;color:#F1F5F9;margin-top:4px;">{agora}</div>
            <div class="td-kpi-sub">idade dos dados: {rtd_mtime[:16]}</div>
        </div>""",
            unsafe_allow_html=True,
        )

    with col_conn3:
        age_min = "?"
        if rtd_exists:
            try:
                age_sec = (
                    datetime.now() - datetime.fromtimestamp(RTD_PATH.stat().st_mtime)
                ).total_seconds()
                age_min = f"{int(age_sec/60)}min"
            except Exception:
                pass
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Idade do arquivo</div>
            <div style="font-size:1.0rem;font-weight:800;color:#94A3B8;margin-top:4px;">{age_min}</div>
            <div class="td-kpi-sub">desde última modificação</div>
        </div>""",
            unsafe_allow_html=True,
        )

    # Instrument counts
    st.markdown(
        '<div class="td-section">Instrumentos por Classe</div>', unsafe_allow_html=True
    )
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
    for col, label, count, cor in [
        (col_t1, "Ações", len(acoes), "#22D3EE"),
        (col_t2, "Opções", len(opcoes), "#EAB308"),
        (col_t3, "Futuros", len(futuros), "#22C55E"),
        (col_t4, "Índices", len(indices), "#94A3B8"),
        (col_t5, "Total", len(all_inst), "#F1F5F9"),
    ]:
        with col:
            st.markdown(
                f"""
            <div class="td-kpi">
                <div class="td-kpi-label">{label}</div>
                <div class="td-kpi-val" style="color:{cor};">{count}</div>
            </div>""",
                unsafe_allow_html=True,
            )

    # Status summary
    st.markdown(
        '<div class="td-section">Status dos Dados</div>', unsafe_allow_html=True
    )
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Ao Vivo</div>
            <div class="td-kpi-val" style="color:#22C55E;">{ao_vivo}</div>
            <div class="td-kpi-sub">com bid/ask</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_s2:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Sem Bid/Ask</div>
            <div class="td-kpi-val" style="color:#F59E0B;">{sem_bid}</div>
            <div class="td-kpi-sub">precisa config</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_s3:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Sem Preço</div>
            <div class="td-kpi-val" style="color:#EF4444;">{sem_preco}</div>
            <div class="td-kpi-sub">sem dados</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_s4:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Shortlist RTD</div>
            <div class="td-kpi-val" style="color:{'#22C55E' if sl_in_rtd > 0 else '#F59E0B'};">{sl_in_rtd}/{sl_total}</div>
            <div class="td-kpi-sub">opções config.</div>
        </div>""",
            unsafe_allow_html=True,
        )

    # Candidatos operacionais
    st.markdown(
        '<div class="td-section">Candidatos Operacionais (Ações COMPRA)</div>',
        unsafe_allow_html=True,
    )
    if not candidatos:
        st.markdown(
            '<div class="td-info">Nenhum candidato operacional no momento. Aguarde gatilhos.</div>',
            unsafe_allow_html=True,
        )
    else:
        for t, p, s in candidatos[:8]:
            var_cls = _cls_pct(p.variacao)
            var_str = _fmt_pct(p.variacao)
            prec_str = _fmt_preco(p.preco)
            rsi_str = f"{p.rsi:.0f}" if p.rsi else "—"
            macd_str = f"{p.macd:.2f}" if p.macd else "—"
            st.markdown(
                f"""
            <div class="cand-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-weight:800;font-size:0.85rem;color:#F1F5F9;">{t}</span>
                        <span style="margin-left:10px;font-size:0.72rem;color:#64748B;">{prec_str}</span>
                        <span class="{var_cls}" style="margin-left:8px;font-weight:700;">{var_str}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.68rem;color:#7DD3FC;">{s['gatilho']}</span>
                        <span style="margin-left:8px;font-size:0.62rem;color:#475569;">RSI {rsi_str} · MACD {macd_str}</span>
                    </div>
                </div>
                <div style="margin-top:4px;font-size:0.60rem;color:#475569;">{s['motivos']}</div>
                {_badge(s['prox'], s['prox_cor'])}
            </div>
            """,
                unsafe_allow_html=True,
            )
        if len(candidatos) > 8:
            st.markdown(
                f'<div style="font-size:0.62rem;color:#475569;">+{len(candidatos)-8} outros candidatos</div>',
                unsafe_allow_html=True,
            )

    # Options overview
    st.markdown(
        '<div class="td-section">Opções — Status da Shortlist</div>',
        unsafe_allow_html=True,
    )
    if shortlist_df.empty:
        st.markdown(
            '<div class="td-warn">Shortlist vazia. Execute: python -m src.scanners.options_rtd_watchlist_builder</div>',
            unsafe_allow_html=True,
        )
    else:
        rtd_set = set(all_inst.keys())
        opt_com_preco = sum(
            1 for _, r in shortlist_df.iterrows() if str(r.get("ticker", "")) in rtd_set
        )
        opt_com_bid = sum(
            1
            for _, r in shortlist_df.iterrows()
            if str(r.get("ticker", "")) in rtd_set
            and all_inst.get(str(r.get("ticker", "")), None) is not None
            and all_inst[str(r.get("ticker", ""))].bid is not None
        )
        opt_com_ask = sum(
            1
            for _, r in shortlist_df.iterrows()
            if str(r.get("ticker", "")) in rtd_set
            and all_inst.get(str(r.get("ticker", "")), None) is not None
            and all_inst[str(r.get("ticker", ""))].ask is not None
        )
        opt_com_bidask = sum(
            1
            for _, r in shortlist_df.iterrows()
            if str(r.get("ticker", "")) in rtd_set
            and all_inst.get(str(r.get("ticker", "")), None) is not None
            and all_inst[str(r.get("ticker", ""))].bid is not None
            and all_inst[str(r.get("ticker", ""))].ask is not None
        )
        opt_monitor = sum(
            1
            for _, r in shortlist_df.iterrows()
            if str(r.get("ticker", "")) in rtd_set
            and all_inst.get(str(r.get("ticker", "")), None) is not None
            and all_inst[str(r.get("ticker", ""))].preco is not None
        )
        opt_cand = sum(
            1
            for _, r in shortlist_df.iterrows()
            if str(r.get("ticker", "")) in rtd_set
            and all_inst.get(str(r.get("ticker", "")), None) is not None
            and all_inst[str(r.get("ticker", ""))].preco is not None
            and all_inst[str(r.get("ticker", ""))].bid is not None
            and all_inst[str(r.get("ticker", ""))].ask is not None
            and all_inst[str(r.get("ticker", ""))].spread_pct is not None
            and all_inst[str(r.get("ticker", ""))].spread_pct <= 2.0
        )

        col_opt1, col_opt2, col_opt3, col_opt4, col_opt5 = st.columns(5)
        for c, lbl, val in [
            (col_opt1, "No RTD", f"{opt_com_preco}/{sl_total}"),
            (col_opt2, "Com Bid", f"{opt_com_bid}"),
            (col_opt3, "Com Ask", f"{opt_com_ask}"),
            (col_opt4, "Monitorável", f"{opt_monitor}"),
            (col_opt5, "Candidatas", f"{opt_cand}"),
        ]:
            with c:
                st.markdown(
                    f"""
                <div class="td-kpi">
                    <div class="td-kpi-label">{lbl}</div>
                    <div class="td-kpi-val">{val}</div>
                </div>""",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: AÇÕES
# ═══════════════════════════════════════════════════════════════════════════
with tab_acao:
    st.markdown(
        '<div class="td-section">Ações ao Vivo — RTD Profit</div>',
        unsafe_allow_html=True,
    )

    if not acoes:
        st.markdown(
            '<div class="td-info">Nenhuma ação no RTD.</div>', unsafe_allow_html=True
        )
    else:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            filtro_dir = st.selectbox(
                "Direção",
                [
                    "Todas",
                    "COMPRA",
                    "OBSERVAR",
                    "NEUTRO",
                    "FRAQUEZA",
                    "EVITAR",
                ],
                key="fd_acao",
            )
        with col_f2:
            filtro_liq = st.selectbox(
                "Liquidez",
                [
                    "Todas",
                    "Alta (≥R$50M)",
                    "Mínima (≥R$5M)",
                ],
                key="fl_acao",
            )
        with col_f3:
            filtro_ord = st.selectbox(
                "Ordenar",
                [
                    "Score ↓",
                    "Variação ↓",
                    "Volume ↓",
                    "Ticker A-Z",
                ],
                key="fo_acao",
            )

        rows = ""
        n = 0
        for ticker, p in acoes.items():
            s = _sinal_acao(p)
            if filtro_dir != "Todas" and s["dir"] != filtro_dir:
                continue
            if filtro_liq == "Alta" and not (p.volume and p.volume >= VOL_ALTA):
                continue
            if filtro_liq == "Mínima" and not (p.volume and p.volume >= VOL_MEDIA):
                continue

            # Sort key
            if filtro_ord == "Ticker A-Z":
                sk = ticker
            elif filtro_ord == "Variação ↓":
                sk = p.variacao or -999
            elif filtro_ord == "Volume ↓":
                sk = p.volume or 0
            else:
                sk = s["score"]

            n += 1
            var_cls = _cls_pct(p.variacao)
            var_str = _fmt_pct(p.variacao)
            prec_str = _fmt_preco(p.preco)
            vol_str = s["vol_lbl"]
            neg_str = f"{p.negocios}" if p.negocios else "—"
            bid_str = _fmt_preco(p.bid)
            ask_str = _fmt_preco(p.ask)
            spr_str = f"{p.spread_pct:.2f}%" if p.spread_pct else "—"
            vwap_str = _fmt_preco(p.vwap)
            rsi_str = f"{p.rsi:.0f}" if p.rsi else "—"
            macd_str = f"{p.macd:.2f}" if p.macd else "—"
            adx_str = f"{p.adx:.0f}" if p.adx else "—"

            rows += f"""
            <tr>
                <td><div class="td-ticker">{ticker}</div>
                    <div style="font-size:0.52rem;color:#475569;max-width:70px;overflow:hidden;text-overflow:ellipsis;">{p.nome[:15]}</div>
                </td>
                <td class="td-preco">{prec_str}</td>
                <td><span class="{var_cls}">{var_str}</span></td>
                <td>{vol_str}</td>
                <td>{neg_str}</td>
                <td>{bid_str}</td>
                <td>{ask_str}</td>
                <td>{spr_str}</td>
                <td>{vwap_str}</td>
                <td>{rsi_str}</td>
                <td>{macd_str}</td>
                <td>{adx_str}</td>
                <td>{_dir_badge(s['dir'])}</td>
                <td>{_score_html(int(s['score']))}</td>
                <td>{_badge(s['prox'], s['prox_cor'])}</td>
            </tr>
            """

        st.markdown(
            f"<div style='margin-bottom:4px;font-size:0.60rem;color:#475569;'>{n} ações</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
        <div class="td-table-wrap">
            <table class="td-table">
                <thead>
                    <tr>
                        <th>Ticker</th><th>Último</th><th>Var%</th>
                        <th>Volume</th><th>Neg.</th>
                        <th>Bid</th><th>Ask</th><th>Spread</th>
                        <th>VWAP</th>
                        <th>RSI</th><th>MACD</th><th>ADX</th>
                        <th>Dir.</th><th>Score</th>
                        <th>Próxima</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: OPÇÕES
# ═══════════════════════════════════════════════════════════════════════════
with tab_opcao:
    st.markdown(
        '<div class="td-section">Opções ao Vivo — Shortlist Cruzada com RTD</div>',
        unsafe_allow_html=True,
    )

    # Aviso se aba Opções vazia
    reader = RTDLiveReader(
        rtd_path=RTD_PATH, shortlist=SHORTLIST_PATH, symbols_path=SYMBOLS_PATH
    )
    summary = reader.summary()
    read_sheets = summary.get("read_sheets", [])

    # Verificar se há opções detectadas na aba Ações
    rtd_all_for_opc = _rtd_all()
    opcoes_from_rtd = {
        t: p for t, p in rtd_all_for_opc.items() if p.classe == InstrumentClass.OPCAO
    }
    shortlist_tickers = (
        set(str(r.get("ticker", "")).strip() for r in shortlist_df.iterrows())
        if not shortlist_df.empty
        else set()
    )

    if "Opções" in read_sheets:
        st.markdown(
            '<div class="td-info">ℹ️ A aba <strong>Opções</strong> foi encontrada, mas também estamos '
            "lendo opções da aba <strong>Ações</strong> (classificação automática por ticker).</div>",
            unsafe_allow_html=True,
        )

    if not opcoes_from_rtd:
        st.markdown(
            '<div class="td-warn">Nenhuma opção detectada no RTD. '
            "O RTD PROFIT.xlsx contém opções? Verifique se o Profit está exportando "
            "opções para a aba <strong>Ações</strong>.</div>",
            unsafe_allow_html=True,
        )
    else:
        rtd_set = set(rtd_all_for_opc.keys())
        shortlist_tickers = (
            set(str(r.get("ticker", "")).strip() for r in shortlist_df.iterrows())
            if not shortlist_df.empty
            else set()
        )

        # ── Seção 1: shortlist cruzada com RTD ───────────────────────────
        if shortlist_df.empty:
            st.markdown(
                '<div class="td-warn">Shortlist vazia. Execute: python -m src.scanners.options_rtd_watchlist_builder --top 80</div>',
                unsafe_allow_html=True,
            )
        else:
            # KPIs de status
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)

            opt_noconf = sl_total - sl_in_rtd
        opt_semperco = 0
        opt_sembidask = 0
        opt_spreadalto = 0
        opt_monitor = 0
        opt_cand = 0

        for _, r in shortlist_df.iterrows():
            tk = str(r.get("ticker", "")).strip()
            if tk not in rtd_set:
                continue
            p = all_inst.get(tk)
            if p is None:
                continue
            sts, _ = _opcao_status(p, dict(r))
            if "Não configurada" in sts:
                opt_noconf += 1
            elif "Sem preço" in sts:
                opt_semperco += 1
            elif "Sem bid/ask" in sts:
                opt_sembidask += 1
            elif "Spread" in sts:
                opt_spreadalto += 1
            elif sts == "Monitorável":
                opt_monitor += 1
            elif sts == "Candidata oper.":
                opt_cand += 1

        with col_k1:
            st.markdown(
                f"""
            <div class="td-kpi">
                <div class="td-kpi-label">Shortlist</div>
                <div class="td-kpi-val" style="color:#22D3EE;">{sl_total}</div>
                <div class="td-kpi-sub">total opções</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with col_k2:
            st.markdown(
                f"""
            <div class="td-kpi">
                <div class="td-kpi-label">No RTD</div>
                <div class="td-kpi-val" style="color:{'#22C55E' if sl_in_rtd > 0 else '#F59E0B'};">{sl_in_rtd}</div>
                <div class="td-kpi-sub">configuradas</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with col_k3:
            st.markdown(
                f"""
            <div class="td-kpi">
                <div class="td-kpi-label">Ausentes</div>
                <div class="td-kpi-val" style="color:#F59E0B;">{opt_noconf}</div>
                <div class="td-kpi-sub">não no RTD</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with col_k4:
            st.markdown(
                f"""
            <div class="td-kpi">
                <div class="td-kpi-label">Candidatas</div>
                <div class="td-kpi-val" style="color:#22C55E;">{opt_cand}</div>
                <div class="td-kpi-sub">operacionais</div>
            </div>""",
                unsafe_allow_html=True,
            )

        # Validação especial
        st.markdown(
            '<div class="td-section">Validação — Opções com Bid/Ask</div>',
            unsafe_allow_html=True,
        )
        val_rows = ""
        val_total_com_preco = val_total_com_bid = val_total_com_ask = 0
        val_total_com_bidask = 0

        for _, r in shortlist_df.iterrows():
            tk = str(r.get("ticker", "")).strip()
            p = all_inst.get(tk)
            in_rtd = tk in rtd_set

            if in_rtd and p:
                val_total_com_preco += 1
                if p.bid:
                    val_total_com_bid += 1
                if p.ask:
                    val_total_com_ask += 1
                if p.bid and p.ask:
                    val_total_com_bidask += 1

            tipo = str(r.get("tipo", ""))
            ativo = str(r.get("ativo_objeto", ""))
            strike = r.get("strike", 0)
            venc = str(r.get("vencimento", ""))[:10]
            spot = r.get("spot", 0)
            mney = r.get("moneyness", 0)
            adv = r.get("adv_volume", 0)
            cat = str(r.get("categoria", ""))

            if in_rtd and p:
                prec_s = _fmt_preco(p.preco)
                bid_s = _fmt_preco(p.bid)
                ask_s = _fmt_preco(p.ask)
                spr_s = f"{p.spread_pct:.2f}%" if p.spread_pct else "—"
                vol_s = _fmt_vol(p.volume)
                neg_s = f"{p.negocios}" if p.negocios else "—"
                sts, cor = _opcao_status(p, dict(r))
            else:
                prec_s = _fmt_preco(r.get("ultimo_preco", 0))
                bid_s = "—"
                ask_s = "—"
                spr_s = "—"
                vol_s = _fmt_vol(adv) if adv else "—"
                neg_s = "—"
                sts, cor = "Não configurada", "gray"

            mney_s = f"{mney*100:.1f}%" if mney else "—"
            spot_s = _fmt_preco(spot) if spot else "—"
            tipo_c = "#22C55E" if tipo == "CALL" else "#EF4444"
            cat_c = "#22C55E" if cat == "OPORTUNIDADE" else "#EAB308"
            dot = "🟢" if in_rtd else "⚪"

            # moneyness emoji
            if mney and abs(mney) <= 0.02:
                mne = "ATM"
            elif mney and mney > 0:
                mne = "ITM"
            elif mney and mney < 0:
                mne = "OTM"
            else:
                mne = "—"

            val_rows += f"""
            <tr>
                <td><div class="td-ticker">{dot} {tk}</div>
                    <div style="font-size:0.52rem;color:#475569;">{ativo}</div>
                </td>
                <td><span style="color:{tipo_c};font-weight:800;font-size:0.68rem;">{tipo}</span></td>
                <td style="color:#F1F5F9;">{strike:.2f}</td>
                <td style="color:#64748B;font-size:0.62rem;">{venc}</td>
                <td>{spot_s}</td>
                <td>{mney_s}</td>
                <td><span style="font-size:0.58rem;color:#64748B;">{mne}</span></td>
                <td class="td-preco">{prec_s}</td>
                <td>{bid_s}</td>
                <td>{ask_s}</td>
                <td>{spr_s}</td>
                <td>{vol_s}</td>
                <td>{neg_s}</td>
                <td><span style="color:{cat_c};font-size:0.58rem;font-weight:700;">{cat[:4]}</span></td>
                <td><span style="color:#64748B;font-size:0.58rem;">{adv/1e6:.1f}M ADV</span></td>
                <td><span style="color:{cor};font-size:0.62rem;font-weight:700;">{sts}</span></td>
            </tr>
            """

        # Summary box
        st.markdown(
            f"""
        <div class="td-info">
            <strong style="color:#22D3EE;">Validação da Shortlist</strong><br>
            Com preço: <strong>{val_total_com_preco}/{sl_total}</strong> &nbsp;|&nbsp;
            Com bid: <strong>{val_total_com_bid}</strong> &nbsp;|&nbsp;
            Com ask: <strong>{val_total_com_ask}</strong> &nbsp;|&nbsp;
            Bid+Ask completo: <strong>{val_total_com_bidask}</strong>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Tabela
        st.markdown(
            f"""
        <div class="td-table-wrap">
            <table class="td-table">
                <thead>
                    <tr>
                        <th>Ticker</th><th>Tipo</th><th>Strike</th>
                        <th>Venc.</th><th>Spot</th><th>Moneyness</th>
                        <th>Posição</th>
                        <th>Preço</th><th>Bid</th><th>Ask</th>
                        <th>Spread</th><th>Volume</th><th>Neg.</th>
                        <th>Cat.</th><th>ADV</th>
                        <th>Status RTD</th>
                    </tr>
                </thead>
                <tbody>{val_rows}</tbody>
            </table>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── Seção 2: opções detectadas no RTD mas fora da shortlist ──
        fora_shortlist = [
            (t, p)
            for t, p in opcoes_from_rtd.items()
            if t not in rtd_set or t not in shortlist_tickers
        ]

        if fora_shortlist:
            st.markdown(
                '<div class="td-section">Opções RTD (fora da shortlist)</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="td-info">ℹ️ {len(fora_shortlist)} opção(ões) detectadas no RTD '
                "por classificação automática de ticker, mas <strong>não estão na shortlist</strong>. "
                "Execute o builder para adicioná-las.</div>",
                unsafe_allow_html=True,
            )
            fs_rows = ""
            for t, p in sorted(fora_shortlist):
                prec_s = _fmt_preco(p.preco)
                bid_s = _fmt_preco(p.bid)
                ask_s = _fmt_preco(p.ask)
                spr_s = f"{p.spread_pct:.2f}%" if p.spread_pct else "—"
                vol_s = _fmt_vol(p.volume)
                sts, cor = _opcao_status(p, None)
                fs_rows += f"""
                <tr>
                    <td><div class="td-ticker">{t}</div>
                        <div style="font-size:0.52rem;color:#475569;">{p.ativo_objeto or t[:4]}</div>
                    </td>
                    <td class="td-preco">{prec_s}</td>
                    <td>{bid_s}</td>
                    <td>{ask_s}</td>
                    <td>{spr_s}</td>
                    <td>{vol_s}</td>
                    <td><span style="color:{cor};font-size:0.62rem;font-weight:700;">{sts}</span></td>
                    <td><span style="color:#64748B;font-size:0.58rem;">{p.aba_origem}</span></td>
                </tr>
                """
            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>Ticker</th><th>Preço</th><th>Bid</th><th>Ask</th>
                            <th>Spread</th><th>Volume</th><th>Status</th><th>Aba Origem</th>
                        </tr>
                    </thead>
                    <tbody>{fs_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if sl_in_rtd == 0:
            st.markdown(
                """
            <div class="td-warn">
                ⚠️ Nenhuma opção da shortlist está no RTD ainda.<br>
                Para adicionar: abra o Profit RTD → aba Opções → cole os tickers de
                <code>data/realtime/options_rtd_symbols.csv</code>
            </div>""",
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: FUTUROS
# ═══════════════════════════════════════════════════════════════════════════
with tab_futuro:
    st.markdown(
        '<div class="td-section">Futuros ao Vivo — RTD Profit</div>',
        unsafe_allow_html=True,
    )

    if not futuros:
        st.markdown(
            '<div class="td-info">Nenhum futuro configurado no RTD.</div>',
            unsafe_allow_html=True,
        )
    else:
        rows_fut = ""
        for ticker, p in futuros.items():
            s = _sinal_acao(p)
            var_cls = _cls_pct(p.variacao)
            var_str = _fmt_pct(p.variacao)
            prec_str = f"{p.preco:.1f}" if p.preco else "—"
            vol_str = s["vol_lbl"]
            neg_str = f"{p.negocios}" if p.negocios else "—"
            bid_str = _fmt_preco(p.bid)
            ask_str = _fmt_preco(p.ask)
            vwap_str = f"{p.vwap:.1f}" if p.vwap else "—"
            rsi_str = f"{p.rsi:.0f}" if p.rsi else "—"
            macd_str = f"{p.macd:.2f}" if p.macd else "—"
            adx_str = f"{p.adx:.0f}" if p.adx else "—"

            rows_fut += f"""
            <tr>
                <td><div class="td-ticker">{ticker}</div></td>
                <td class="td-preco">{prec_str}</td>
                <td><span class="{var_cls}">{var_str}</span></td>
                <td>{vol_str}</td>
                <td>{neg_str}</td>
                <td>{bid_str}</td>
                <td>{ask_str}</td>
                <td>{vwap_str}</td>
                <td>{rsi_str}</td>
                <td>{macd_str}</td>
                <td>{adx_str}</td>
                <td>{_dir_badge(s['dir'])}</td>
                <td>{_score_html(int(s['score']))}</td>
                <td>{_badge(s['prox'], s['prox_cor'])}</td>
            </tr>
            """

        st.markdown(
            f"""
        <div class="td-table-wrap">
            <table class="td-table">
                <thead>
                    <tr>
                        <th>Contrato</th><th>Último</th><th>Var%</th>
                        <th>Volume</th><th>Neg.</th>
                        <th>Bid</th><th>Ask</th>
                        <th>VWAP</th>
                        <th>RSI</th><th>MACD</th><th>ADX</th>
                        <th>Dir.</th><th>Score</th>
                        <th>Próxima</th>
                    </tr>
                </thead>
                <tbody>{rows_fut}</tbody>
            </table>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: ESTRATÉGIAS COM OPÇÕES
# ═══════════════════════════════════════════════════════════════════════════
with tab_estrategias:
    st.markdown(
        '<div class="td-section">Motor de Estratégias — Dados RTD ao Vivo</div>',
        unsafe_allow_html=True,
    )

    if shortlist_df.empty:
        st.markdown(
            '<div class="td-warn">Shortlist vazia. Execute: python -m src.scanners.options_rtd_watchlist_builder --top 80</div>',
            unsafe_allow_html=True,
        )
    else:
        col_cfg1, col_cfg2, col_cfg3 = st.columns([1, 1, 2])
        with col_cfg1:
            top_n = st.number_input(
                "Top estratégias por ativo",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
                key="strat_top_n",
            )
        with col_cfg2:
            status_filter = st.selectbox(
                "Filtrar por status",
                ["Todos", "OPERACIONAL", "ESTUDO"],
                key="strat_status_filter",
            )
        with col_cfg3:
            st.markdown(
                '<div class="td-info" style="margin-top:4px;">'
                + "⚙️ Motor usa dados ao vivo (RTD). "
                + "Apenas opções com bid/ask válido e spread ≤ 3% entram na análise. "
                + "Risco máximo calculado para cada estrutura."
                + "</div>",
                unsafe_allow_html=True,
            )

        with st.spinner("Analisando estruturas..."):
            try:
                from src.options.rtd_strategy_adapter import (
                    run_rtd_strategy_engine,
                    classify_market_from_rtd,
                    format_strategy_html,
                    format_no_strategy_html,
                    summarize_rtd_strategies,
                    _scenario_label,
                )

                strat_results = run_rtd_strategy_engine(
                    all_inst=all_inst,
                    shortlist_df=shortlist_df,
                    top=int(top_n),
                )
            except Exception as _e:
                strat_results = {}
                st.markdown(
                    f'<div class="td-warn">Erro ao rodar motor de estratégias: {_e}</div>',
                    unsafe_allow_html=True,
                )

        summ = (
            summarize_rtd_strategies(strat_results)
            if strat_results
            else {
                "underlyings": 0,
                "com_estrategia": 0,
                "sem_estrategia": 0,
                "operacionais": 0,
                "total_estrategias": 0,
            }
        )
        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        for col_kpi, lbl, val, cor in [
            (col_k1, "Ativos", summ["underlyings"], "#F1F5F9"),
            (col_k2, "Com estratégia", summ["com_estrategia"], "#22C55E"),
            (col_k3, "Sem estratégia", summ["sem_estrategia"], "#F59E0B"),
            (col_k4, "Operacionais", summ["operacionais"], "#22D3EE"),
            (col_k5, "Total struct.", summ["total_estrategias"], "#94A3B8"),
        ]:
            with col_kpi:
                st.markdown(
                    f"""
                <div class="td-kpi">
                    <div class="td-kpi-label">{lbl}</div>
                    <div class="td-kpi-val" style="color:{cor};">{val}</div>
                </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)

        if not strat_results:
            st.markdown(
                '<div class="td-info">Nenhuma estratégia encontrada. '
                + "Verifique se há opções com bid/ask no RTD.</div>",
                unsafe_allow_html=True,
            )
        else:
            for underlying, opportunities in sorted(strat_results.items()):
                stock_pay = all_inst.get(underlying)
                stock_price = (
                    float(stock_pay.preco) if stock_pay and stock_pay.preco else 0.0
                )
                condition = classify_market_from_rtd(stock_pay) if stock_pay else None
                cond_label, cond_emoji = (
                    _scenario_label(condition) if condition else ("—", "⚫")
                )
                stock_var = stock_pay.variacao if stock_pay else None
                var_str = _fmt_pct(stock_var)
                var_cls = _cls_pct(stock_var)
                filtered_opps = [
                    o
                    for o in opportunities
                    if status_filter == "Todos" or o.status == status_filter
                ]
                n_ops = len(filtered_opps)
                n_all = len(opportunities)
                header_color = "#22C55E" if n_ops > 0 else "#475569"
                st.markdown(
                    f"""
                <div style="display:flex;align-items:center;gap:10px;
                     margin-top:14px;margin-bottom:6px;padding-bottom:6px;
                     border-bottom:1px solid #1E2D42;">
                    <span style="font-weight:900;font-size:0.95rem;color:#F1F5F9;">{underlying}</span>
                    <span class="{var_cls}" style="font-size:0.72rem;">{var_str}</span>
                    <span style="font-size:0.68rem;color:#64748B;">R$ {stock_price:.2f}</span>
                    <span style="font-size:0.68rem;color:#94A3B8;">{cond_emoji} {cond_label}</span>
                    <span style="font-size:0.60rem;color:{header_color};margin-left:auto;">
                        {n_ops}/{n_all} estruturas
                    </span>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                if not filtered_opps and not opportunities:
                    st.markdown(
                        format_no_strategy_html(
                            underlying,
                            "Sem estrutura operacional — opções com spread alto ou baixa liquidez.",
                        ),
                        unsafe_allow_html=True,
                    )
                elif not filtered_opps:
                    st.markdown(
                        format_no_strategy_html(
                            underlying,
                            f"Nenhuma estrutura com status '{status_filter}'. "
                            f"({n_all} estruturas com outro status encontradas.)",
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    for opp in filtered_opps:
                        st.markdown(
                            format_strategy_html(opp, stock_price),
                            unsafe_allow_html=True,
                        )

        st.markdown(
            """
        <div style="margin-top:16px;padding:10px 14px;
             background:#070F1A;border:1px solid #1E2D42;border-radius:8px;
             font-size:0.60rem;color:#475569;">
            <strong style="color:#64748B;">LEGENDA —</strong>
            <span style="color:#22C55E;font-weight:700;">OPERACIONAL</span>: score ≥ 60, risco BAIXO/MODERADO &nbsp;|&nbsp;
            <span style="color:#EAB308;font-weight:700;">ESTUDO</span>: score &lt; 60 ou risco ALTO &nbsp;|&nbsp;
            <span style="color:#64748B;font-weight:700;">DESCARTAR</span>: risco não recomendado ou score &lt; 30<br>
            Spread máx. 3% · Bid+Ask obrigatório · Apenas estruturas com risco máximo calculado<br>
            <em>Não é recomendação de investimento. Use como apoio à decisão.</em>
        </div>
        <div style="margin-top:8px;padding:8px 14px;background:#070F1A;
             border:1px solid #1E3A1E;border-radius:6px;font-size:0.58rem;color:#475569;">
            <strong style="color:#22C55E;">&#10003; Auditoria de Sanidade:</strong>
            Compra no ASK &middot; Venda no BID &middot; Vencimentos verificados &middot; Risco máximo calculado &middot; Venda descoberta bloqueada
        </div>
        """,
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: RADAR HISTÓRICO DE OPÇÕES
# ═══════════════════════════════════════════════════════════════════════════
with tab_hist_radar:
    st.markdown(
        '<div class="td-section">Radar Histórico de Opções — COTAHIST B3</div>',
        unsafe_allow_html=True,
    )

    # Disclaimer obrigatório
    st.markdown(
        """
    <div class="td-warn" style="margin-bottom:12px;">
        ⚠️ <strong>Radar histórico não é sinal de entrada imediata.</strong>
        O COTAHIST descobre oportunidades passadas com liquidez histórica.
        O RTD confirma execução no pregão. Aguarde confirmação de bid/ask antes de operar.
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Estado vazio ────────────────────────────────────────────────────────
    if hist_opp_df.empty:
        st.markdown(
            """
        <div class="td-info">
            <strong style="color:#22D3EE;">Nenhuma oportunidade histórica carregada.</strong><br>
            Os arquivos de dados não foram encontrados:<br>
            &nbsp;&nbsp;• <code>data/realtime/options_historical_opportunities.csv</code><br>
            &nbsp;&nbsp;• <code>data/realtime/options_next_session_watchlist.csv</code><br><br>
            Execute o scanner para gerar os dados:<br>
            <code style="color:#22C55E;">python -m src.options.historical_opportunity_scanner</code><br><br>
            Opções disponíveis:<br>
            <code>python -m src.options.historical_opportunity_scanner --ativos PETR4 VALE3</code><br>
            <code>python -m src.options.historical_opportunity_scanner --verbose</code>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        # ── Preparar dados ──────────────────────────────────────────────────
        df = hist_opp_df.copy()

        # Converter colunas numéricas
        for col_num in ["score", "liquidez_score", "vol_media_21d", "negocios_media_5d",
                         "dte", "strike", "ultimo_preco", "moneyness",
                         "retorno_5d", "retorno_21d", "vol_hist_21d"]:
            if col_num in df.columns:
                df[col_num] = df[col_num].apply(_safe_float)

        # RTD crossref — set de tickers no RTD
        rtd_set_all = set(all_inst.keys())

        def _check_rtd(ticker: str) -> tuple[bool, bool]:
            in_rtd = ticker in rtd_set_all
            if not in_rtd:
                return False, False
            p = all_inst.get(ticker)
            rtd_confirmed = (
                p is not None
                and p.bid is not None
                and p.ask is not None
                and p.preco is not None
            )
            return in_rtd, rtd_confirmed

        if "ticker_opcao" in df.columns:
            df["_in_rtd"] = df["ticker_opcao"].apply(lambda t: _check_rtd(str(t))[0])
            df["_rtd_confirmed"] = df["ticker_opcao"].apply(lambda t: _check_rtd(str(t))[1])
        else:
            df["_in_rtd"] = False
            df["_rtd_confirmed"] = False

        # ── KPIs ────────────────────────────────────────────────────────────
        total_opp = len(df)
        n_candidata = (df.get("status", pd.Series(dtype=str)) == "CANDIDATA_PROXIMO_PREGAO").sum()
        n_monitor = (df.get("status", pd.Series(dtype=str)) == "MONITORAR_NO_RTD").sum()
        n_aguardar = (df.get("status", pd.Series(dtype=str)) == "AGUARDAR_LIQUIDEZ").sum()
        n_desc_iliq = (df.get("status", pd.Series(dtype=str)) == "DESCARTAR_ILIQUIDA").sum()
        n_desc_assim = (df.get("status", pd.Series(dtype=str)) == "DESCARTAR_SEM_ASSIMETRIA").sum()
        n_ativos = df["ativo_objeto"].nunique() if "ativo_objeto" in df.columns else 0
        n_no_rtd = df["_in_rtd"].sum()
        n_rtd_confirmed = df["_rtd_confirmed"].sum()

        n_curto = (df.get("categoria_vencimento", pd.Series(dtype=str)) == "CURTO").sum()
        n_medio = (df.get("categoria_vencimento", pd.Series(dtype=str)) == "MEDIO").sum()
        n_longo = (df.get("categoria_vencimento", pd.Series(dtype=str)) == "LONGO").sum()
        n_extra = (df.get("categoria_vencimento", pd.Series(dtype=str)) == "EXTRA_LONGO").sum()

        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        for col_kpi, lbl, val, cor, sub in [
            (col_k1, "Total Oportunidades", total_opp, "#F1F5F9", "histórico COTAHIST"),
            (col_k2, "Candidatas Pregão", n_candidata, "#22C55E", "próxima sessão"),
            (col_k3, "Monitorar RTD", n_monitor, "#22D3EE", "confirmar execução"),
            (col_k4, "Ativos Únicos", n_ativos, "#94A3B8", "monitorados"),
            (col_k5, "No RTD", n_no_rtd, "#EAB308", f"{n_rtd_confirmed} confirmados"),
        ]:
            with col_kpi:
                st.markdown(
                    f"""
                <div class="td-kpi">
                    <div class="td-kpi-label">{lbl}</div>
                    <div class="td-kpi-val" style="color:{cor};">{val}</div>
                    <div class="td-kpi-sub">{sub}</div>
                </div>""",
                    unsafe_allow_html=True,
                )

        col_k6, col_k7, col_k8, col_k9, col_k10 = st.columns(5)
        for col_kpi, lbl, val, cor, sub in [
            (col_k6,  "Aguardando Liq.",   n_aguardar,  "#F97316", "liquidez insuf."),
            (col_k7,  "Descard. Ilíquida", n_desc_iliq, "#EF4444", "sem volume"),
            (col_k8,  "Descard. Sem Edge", n_desc_assim,"#EF4444", "sem assimetria"),
            (col_k9,  "Curto/Médio",       f"{n_curto}/{n_medio}", "#F1F5F9", "0-90 dias"),
            (col_k10, "Longo/Extra",       f"{n_longo}/{n_extra}", "#94A3B8", "90-180+ dias"),
        ]:
            with col_kpi:
                st.markdown(
                    f"""
                <div class="td-kpi">
                    <div class="td-kpi-label">{lbl}</div>
                    <div class="td-kpi-val" style="color:{cor};">{val}</div>
                    <div class="td-kpi-sub">{sub}</div>
                </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)

        # ── Filtros ─────────────────────────────────────────────────────────
        st.markdown('<div class="td-section">Filtros</div>', unsafe_allow_html=True)

        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            ativos_list = ["Todos"] + sorted(df["ativo_objeto"].dropna().unique().tolist()) if "ativo_objeto" in df.columns else ["Todos"]
            flt_ativo = st.selectbox("Ativo Objeto", ativos_list, key="hr_ativo")
        with col_f2:
            cenarios_list = ["Todos"] + sorted(df["cenario"].dropna().unique().tolist()) if "cenario" in df.columns else ["Todos"]
            flt_cenario = st.selectbox("Cenário", cenarios_list, key="hr_cenario")
        with col_f3:
            status_list = ["Todos"] + sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else ["Todos"]
            flt_status = st.selectbox("Status", status_list, key="hr_status")
        with col_f4:
            tipo_list = ["Todos", "CALL", "PUT"]
            flt_tipo = st.selectbox("Tipo CALL/PUT", tipo_list, key="hr_tipo")

        col_f5, col_f6, col_f7, col_f8 = st.columns(4)
        with col_f5:
            horiz_list = ["Todos", "CURTO", "MEDIO", "LONGO", "EXTRA_LONGO"]
            flt_horizonte = st.selectbox("Horizonte", horiz_list, key="hr_horizonte")
        with col_f6:
            vencs_list = ["Todos"] + sorted(df["vencimento"].dropna().unique().tolist()) if "vencimento" in df.columns else ["Todos"]
            flt_venc = st.selectbox("Vencimento", vencs_list, key="hr_venc")
        with col_f7:
            structs_raw = set()
            if "estruturas_sugeridas" in df.columns:
                for v in df["estruturas_sugeridas"].dropna():
                    for s in str(v).split(","):
                        s = s.strip()
                        if s:
                            structs_raw.add(s)
            struct_list = ["Todos"] + sorted(structs_raw)
            flt_struct = st.selectbox("Estrutura", struct_list, key="hr_struct")
        with col_f8:
            flt_score_min = st.slider("Score mínimo", 0, 100, 0, step=5, key="hr_score")

        # ── Aplicar filtros ─────────────────────────────────────────────────
        df_filt = df.copy()
        if flt_ativo != "Todos" and "ativo_objeto" in df_filt.columns:
            df_filt = df_filt[df_filt["ativo_objeto"] == flt_ativo]
        if flt_cenario != "Todos" and "cenario" in df_filt.columns:
            df_filt = df_filt[df_filt["cenario"] == flt_cenario]
        if flt_status != "Todos" and "status" in df_filt.columns:
            df_filt = df_filt[df_filt["status"] == flt_status]
        if flt_tipo != "Todos" and "tipo" in df_filt.columns:
            df_filt = df_filt[df_filt["tipo"].str.upper() == flt_tipo]
        if flt_horizonte != "Todos" and "categoria_vencimento" in df_filt.columns:
            df_filt = df_filt[df_filt["categoria_vencimento"] == flt_horizonte]
        if flt_venc != "Todos" and "vencimento" in df_filt.columns:
            df_filt = df_filt[df_filt["vencimento"] == flt_venc]
        if flt_struct != "Todos" and "estruturas_sugeridas" in df_filt.columns:
            df_filt = df_filt[df_filt["estruturas_sugeridas"].str.contains(flt_struct, na=False)]
        if flt_score_min > 0 and "score" in df_filt.columns:
            df_filt = df_filt[df_filt["score"] >= flt_score_min]

        df_filt = df_filt.sort_values("score", ascending=False).reset_index(drop=True)

        # ── Tabela principal ─────────────────────────────────────────────────
        st.markdown(
            f'<div class="td-section">Oportunidades ({len(df_filt)} de {total_opp})</div>',
            unsafe_allow_html=True,
        )

        if df_filt.empty:
            st.markdown(
                '<div class="td-info">Nenhuma oportunidade para os filtros selecionados.</div>',
                unsafe_allow_html=True,
            )
        else:
            table_rows = ""
            for _, row in df_filt.head(200).iterrows():
                ativo = str(row.get("ativo_objeto", "—"))
                ticker = str(row.get("ticker_opcao", "—"))
                tipo = str(row.get("tipo", "—"))
                strike = _safe_float(row.get("strike"))
                venc = str(row.get("vencimento", "—"))[:10]
                dte = _safe_int(row.get("dte"))
                mney_val = _safe_float(row.get("moneyness"))
                mney_cat = str(row.get("moneyness_cat", "—"))
                cenario = str(row.get("cenario", "—"))
                horizonte = str(row.get("categoria_vencimento", "—"))
                estruturas = str(row.get("estruturas_sugeridas", "—"))[:30]
                score_v = _safe_float(row.get("score"))
                liq = _safe_float(row.get("liquidez_score"))
                vol21 = _safe_float(row.get("vol_media_21d"))
                neg21 = _safe_float(row.get("negocios_media_5d"))
                status_v = str(row.get("status", "—"))
                motivo = str(row.get("motivo", "—"))[:50]
                risco = str(row.get("risco_principal", "—"))[:40]
                in_rtd = bool(row.get("_in_rtd", False))
                rtd_conf = bool(row.get("_rtd_confirmed", False))

                prox_txt, prox_cls = _hist_proxima_acao(status_v, in_rtd, rtd_conf)
                cenario_lbl = _CENARIO_LABEL.get(cenario, cenario[:12])
                cenario_cls = _CENARIO_BADGE.get(cenario, "badge-gray")
                status_lbl = _STATUS_LABEL.get(status_v, status_v[:10])
                status_cls = _STATUS_BADGE.get(status_v, "badge-gray")
                horiz_cls = _HORIZONTE_BADGE.get(horizonte, "badge-gray")
                mney_pct = f"{mney_val*100:.1f}%"
                vol21_fmt = f"R${vol21/1e3:.0f}K" if vol21 >= 1000 else f"R${vol21:.0f}"
                dte_cor = "#22C55E" if dte <= 30 else "#EAB308" if dte <= 90 else "#94A3B8"

                table_rows += f"""
                <tr>
                    <td>
                        <div class="td-ticker" style="font-size:0.72rem;">{ativo}</div>
                    </td>
                    <td>
                        <div style="font-weight:700;font-size:0.68rem;color:#F1F5F9;">{ticker}</div>
                    </td>
                    <td>{_fmt_tipo_badge(tipo)}</td>
                    <td style="color:#F1F5F9;">{strike:.2f}</td>
                    <td style="color:#64748B;font-size:0.60rem;">{venc}</td>
                    <td><span style="color:{dte_cor};font-weight:700;">{dte}d</span></td>
                    <td style="color:#94A3B8;font-size:0.62rem;">{mney_pct} <span style="color:#475569;">({mney_cat})</span></td>
                    <td><span class="badge {cenario_cls}" style="font-size:0.55rem;">{cenario_lbl}</span></td>
                    <td><span class="badge {horiz_cls}" style="font-size:0.55rem;">{horizonte}</span></td>
                    <td style="font-size:0.60rem;color:#7DD3FC;max-width:100px;overflow:hidden;text-overflow:ellipsis;">{estruturas}</td>
                    <td>{_fmt_score_badge(score_v)}</td>
                    <td style="color:#94A3B8;">{liq:.0f}</td>
                    <td style="color:#64748B;font-size:0.62rem;">{vol21_fmt}</td>
                    <td style="color:#64748B;">{neg21:.1f}</td>
                    <td><span class="badge {status_cls}" style="font-size:0.55rem;">{status_lbl}</span></td>
                    <td style="font-size:0.58rem;color:#64748B;max-width:120px;overflow:hidden;text-overflow:ellipsis;" title="{motivo}">{motivo}</td>
                    <td style="font-size:0.58rem;color:#F59E0B;max-width:120px;overflow:hidden;text-overflow:ellipsis;" title="{risco}">{risco[:35]}…</td>
                    <td>{_fmt_rtd_status(in_rtd, rtd_conf)}</td>
                    <td><span class="badge {prox_cls}" style="font-size:0.55rem;white-space:normal;">{prox_txt}</span></td>
                </tr>
                """

            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>Ativo</th><th>Opção</th><th>Tipo</th>
                            <th>Strike</th><th>Venc.</th><th>DTE</th>
                            <th>Moneyness</th><th>Cenário</th><th>Horizonte</th>
                            <th>Estrutura</th><th>Score</th>
                            <th>Liq.</th><th>Vol.21d</th><th>Neg.5d</th>
                            <th>Status</th><th>Motivo</th><th>Risco</th>
                            <th>RTD</th><th>Próxima Ação</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )

            if len(df_filt) > 200:
                st.markdown(
                    f'<div style="font-size:0.60rem;color:#475569;margin-top:4px;">'
                    f"Exibindo 200 de {len(df_filt)} oportunidades. Refine os filtros para ver mais.</div>",
                    unsafe_allow_html=True,
                )

        # ── Bloco: Top ideias para próximo pregão ────────────────────────────
        st.markdown(
            '<div class="td-section">Top Ideias para Próximo Pregão</div>',
            unsafe_allow_html=True,
        )

        df_top = df[
            df.get("status", pd.Series(dtype=str)).isin([
                "CANDIDATA_PROXIMO_PREGAO", "MONITORAR_NO_RTD"
            ])
        ].sort_values("score", ascending=False).head(10)

        if df_top.empty:
            st.markdown(
                '<div class="td-info">Nenhuma candidata para o próximo pregão. '
                "Execute: <code>python -m src.options.historical_opportunity_scanner</code></div>",
                unsafe_allow_html=True,
            )
        else:
            top_rows = ""
            for i, (_, row) in enumerate(df_top.iterrows(), 1):
                ativo = str(row.get("ativo_objeto", "—"))
                ticker = str(row.get("ticker_opcao", "—"))
                tipo = str(row.get("tipo", "—"))
                strike = _safe_float(row.get("strike"))
                venc = str(row.get("vencimento", "—"))[:10]
                dte = _safe_int(row.get("dte"))
                cenario = str(row.get("cenario", "—"))
                horizonte = str(row.get("categoria_vencimento", "—"))
                estruturas = str(row.get("estruturas_sugeridas", "—"))
                motivo = str(row.get("motivo", "—"))
                risco = str(row.get("risco_principal", "—"))
                score_v = _safe_float(row.get("score"))
                status_v = str(row.get("status", "—"))
                in_rtd = bool(row.get("_in_rtd", False))
                rtd_conf = bool(row.get("_rtd_confirmed", False))
                prox_txt, prox_cls = _hist_proxima_acao(status_v, in_rtd, rtd_conf)
                cenario_lbl = _CENARIO_LABEL.get(cenario, cenario[:12])
                cenario_cls = _CENARIO_BADGE.get(cenario, "badge-gray")
                horiz_cls = _HORIZONTE_BADGE.get(horizonte, "badge-gray")
                rank_cor = "#22C55E" if i <= 3 else "#EAB308" if i <= 7 else "#94A3B8"

                top_rows += f"""
                <tr>
                    <td style="color:{rank_cor};font-weight:800;">#{i}</td>
                    <td><div class="td-ticker" style="font-size:0.72rem;">{ativo}</div></td>
                    <td><span style="font-weight:700;color:#F1F5F9;font-size:0.68rem;">{ticker}</span></td>
                    <td>{_fmt_tipo_badge(tipo)}</td>
                    <td style="color:#F1F5F9;">{strike:.2f}</td>
                    <td style="color:#64748B;font-size:0.60rem;">{venc} <span style="color:#EAB308;">({dte}d)</span></td>
                    <td><span class="badge {cenario_cls}" style="font-size:0.55rem;">{cenario_lbl}</span></td>
                    <td><span class="badge {horiz_cls}" style="font-size:0.55rem;">{horizonte}</span></td>
                    <td style="font-size:0.60rem;color:#7DD3FC;">{estruturas[:35]}</td>
                    <td>{_fmt_score_badge(score_v)}</td>
                    <td style="font-size:0.58rem;color:#64748B;max-width:150px;">{motivo[:60]}</td>
                    <td style="font-size:0.58rem;color:#F59E0B;max-width:120px;">{risco[:50]}</td>
                    <td><span class="badge {prox_cls}" style="font-size:0.55rem;">{prox_txt}</span></td>
                </tr>
                """

            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>#</th><th>Ativo</th><th>Opção</th><th>Tipo</th>
                            <th>Strike</th><th>Venc./DTE</th>
                            <th>Cenário</th><th>Horizonte</th><th>Estrutura</th>
                            <th>Score</th><th>Motivo</th><th>Risco</th>
                            <th>Próxima Ação</th>
                        </tr>
                    </thead>
                    <tbody>{top_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Bloco: Longo Prazo / Recuperação ────────────────────────────────
        st.markdown(
            '<div class="td-section">Longo Prazo & Recuperação (90–180+ dias)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <div class="td-info" style="margin-bottom:8px;">
            📅 Oportunidades de longo prazo para <strong>planejamento de posição</strong> — não entrada imediata.
            Aguardar janela operacional e confirmação via RTD.
        </div>
        """,
            unsafe_allow_html=True,
        )

        cenarios_longo = {
            "RECUPERACAO_APOS_QUEDA", "CONTINUACAO_ALTA",
            "PROTECAO_CARTEIRA",
        }
        df_longo = df[
            df.get("categoria_vencimento", pd.Series(dtype=str)).isin(["LONGO", "EXTRA_LONGO"])
            & df.get("cenario", pd.Series(dtype=str)).isin(cenarios_longo)
            & (df.get("status", pd.Series(dtype=str)) != "DESCARTAR_ILIQUIDA")
            & (df.get("status", pd.Series(dtype=str)) != "DESCARTAR_SEM_ASSIMETRIA")
        ].sort_values("score", ascending=False).head(20)

        if df_longo.empty:
            st.markdown(
                '<div class="td-info">Nenhuma oportunidade de longo prazo com assimetria identificada.</div>',
                unsafe_allow_html=True,
            )
        else:
            longo_rows = ""
            for _, row in df_longo.iterrows():
                ativo = str(row.get("ativo_objeto", "—"))
                ticker = str(row.get("ticker_opcao", "—"))
                tipo = str(row.get("tipo", "—"))
                strike = _safe_float(row.get("strike"))
                venc = str(row.get("vencimento", "—"))[:10]
                dte = _safe_int(row.get("dte"))
                cenario = str(row.get("cenario", "—"))
                estruturas = str(row.get("estruturas_sugeridas", "—"))[:40]
                score_v = _safe_float(row.get("score"))
                status_v = str(row.get("status", "—"))
                risco = str(row.get("risco_principal", "—"))[:50]
                cenario_lbl = _CENARIO_LABEL.get(cenario, cenario[:12])
                cenario_cls = _CENARIO_BADGE.get(cenario, "badge-gray")
                horizonte = str(row.get("categoria_vencimento", "—"))
                horiz_cls = _HORIZONTE_BADGE.get(horizonte, "badge-gray")
                in_rtd = bool(row.get("_in_rtd", False))
                rtd_conf = bool(row.get("_rtd_confirmed", False))

                longo_rows += f"""
                <tr>
                    <td><div class="td-ticker" style="font-size:0.72rem;">{ativo}</div></td>
                    <td style="font-weight:700;color:#F1F5F9;font-size:0.68rem;">{ticker}</td>
                    <td>{_fmt_tipo_badge(tipo)}</td>
                    <td style="color:#F1F5F9;">{strike:.2f}</td>
                    <td style="color:#64748B;font-size:0.60rem;">{venc}</td>
                    <td style="color:#EAB308;font-weight:700;">{dte}d</td>
                    <td><span class="badge {cenario_cls}" style="font-size:0.55rem;">{cenario_lbl}</span></td>
                    <td><span class="badge {horiz_cls}" style="font-size:0.55rem;">{horizonte}</span></td>
                    <td style="font-size:0.60rem;color:#7DD3FC;">{estruturas}</td>
                    <td>{_fmt_score_badge(score_v)}</td>
                    <td style="font-size:0.58rem;color:#F59E0B;">{risco}</td>
                    <td>{_fmt_rtd_status(in_rtd, rtd_conf)}</td>
                    <td style="font-size:0.58rem;color:#64748B;">Planejar posição</td>
                </tr>
                """

            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>Ativo</th><th>Opção</th><th>Tipo</th>
                            <th>Strike</th><th>Venc.</th><th>DTE</th>
                            <th>Cenário</th><th>Horizonte</th><th>Estrutura</th>
                            <th>Score</th><th>Risco</th><th>RTD</th><th>Ação</th>
                        </tr>
                    </thead>
                    <tbody>{longo_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Bloco: Resumo por Cenário ────────────────────────────────────────
        st.markdown(
            '<div class="td-section">Resumo por Cenário</div>', unsafe_allow_html=True
        )

        todos_cenarios = [
            "RECUPERACAO_APOS_QUEDA", "CONTINUACAO_ALTA", "CONTINUACAO_BAIXA",
            "PROTECAO_CARTEIRA", "RENDA_COM_ATIVO", "VOLATILIDADE_EM_ALTA",
            "LATERALIDADE", "SEM_ASSIMETRIA",
        ]

        cenario_rows = ""
        for cen in todos_cenarios:
            df_cen = df[df.get("cenario", pd.Series(dtype=str)) == cen]
            if df_cen.empty:
                continue
            n_total_cen = len(df_cen)
            n_cand_cen = (df_cen.get("status", pd.Series(dtype=str)) == "CANDIDATA_PROXIMO_PREGAO").sum()
            n_mon_cen = (df_cen.get("status", pd.Series(dtype=str)) == "MONITORAR_NO_RTD").sum()
            n_desc_cen = (
                df_cen.get("status", pd.Series(dtype=str)).isin([
                    "DESCARTAR_ILIQUIDA", "DESCARTAR_SEM_ASSIMETRIA"
                ])
            ).sum()
            ativos_cen = ", ".join(sorted(df_cen["ativo_objeto"].dropna().unique())[:5])
            score_med = df_cen.get("score", pd.Series(dtype=float)).mean()
            cen_lbl = _CENARIO_LABEL.get(cen, cen[:14])
            cen_cls = _CENARIO_BADGE.get(cen, "badge-gray")
            cand_cor = "#22C55E" if n_cand_cen > 0 else "#475569"
            desc_cor = "#EF4444" if n_desc_cen > 0 else "#475569"

            cenario_rows += f"""
            <tr>
                <td><span class="badge {cen_cls}" style="font-size:0.60rem;">{cen_lbl}</span></td>
                <td style="font-weight:700;color:#F1F5F9;">{n_total_cen}</td>
                <td style="color:{cand_cor};font-weight:700;">{n_cand_cen}</td>
                <td style="color:#22D3EE;">{n_mon_cen}</td>
                <td style="color:{desc_cor};">{n_desc_cen}</td>
                <td style="color:#94A3B8;">{score_med:.0f}</td>
                <td style="font-size:0.60rem;color:#64748B;">{ativos_cen}</td>
            </tr>
            """

        if cenario_rows:
            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>Cenário</th><th>Total</th>
                            <th>Candidatas</th><th>Monitorar</th><th>Descartadas</th>
                            <th>Score Médio</th><th>Ativos</th>
                        </tr>
                    </thead>
                    <tbody>{cenario_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Crossref com aba Estratégias ─────────────────────────────────────
        rtd_confirmed_hist = df[df["_rtd_confirmed"]]["ticker_opcao"].tolist() if not df.empty else []
        if rtd_confirmed_hist:
            st.markdown(
                '<div class="td-section">Ponte RTD → Motor de Estratégias</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
            <div class="td-success">
                ✅ <strong>{len(rtd_confirmed_hist)} opção(ões) históricas encontradas no RTD com bid/ask confirmado:</strong>
                {', '.join(rtd_confirmed_hist[:15])}
                {'…' if len(rtd_confirmed_hist) > 15 else ''}<br>
                <span style="font-size:0.62rem;">
                    Acesse a aba <strong>🧠 Estratégias</strong> para ver estruturas operacionais geradas ao vivo.
                    O motor de estratégias consome bid/ask do RTD — nenhuma ação manual é necessária.
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # ── Footer da aba ────────────────────────────────────────────────────
        ultima_data = str(df.get("ultima_data_cotahist", pd.Series(dtype=str)).dropna().iloc[0]) if "ultima_data_cotahist" in df.columns and not df["ultima_data_cotahist"].dropna().empty else "—"
        data_analise = str(df.get("data_analise", pd.Series(dtype=str)).dropna().iloc[0]) if "data_analise" in df.columns and not df["data_analise"].dropna().empty else "—"
        st.markdown(
            f"""
        <div class="td-info" style="margin-top:14px;">
            📊 <strong>Fonte dos dados:</strong> COTAHIST B3 · Última data no banco: <strong>{ultima_data}</strong> ·
            Análise gerada em: <strong>{data_analise}</strong> ·
            {total_opp} oportunidades · {n_ativos} ativos · {HIST_OPP_PATH.name}<br>
            <span style="font-size:0.60rem;color:#475569;">
                Para atualizar: <code>python -m src.options.historical_opportunity_scanner</code>
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# TAB: DIAGNÓSTICO RTD
# ═══════════════════════════════════════════════════════════════════════════
with tab_diag:
    st.markdown(
        '<div class="td-section">Diagnóstico do RTD — Informações Técnicas</div>',
        unsafe_allow_html=True,
    )

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    sheets_str = ", ".join(read_sheets) if read_sheets else "?"
    sheets_count = len(read_sheets)
    with col_d1:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Arquivo</div>
            <div style="font-size:0.78rem;font-weight:800;color:#F1F5F9;margin-top:4px;">{RTD_PATH.name}</div>
            <div class="td-kpi-sub">{RTD_PATH}</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_d2:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Última modificação</div>
            <div style="font-size:0.78rem;font-weight:800;color:#F1F5F9;margin-top:4px;">{rtd_mtime[:19]}</div>
            <div class="td-kpi-sub">YYYY-MM-DD HH:MM:SS</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_d3:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Abas lidas</div>
            <div class="td-kpi-val" style="color:#22D3EE;">{sheets_count}</div>
            <div class="td-kpi-sub">{sheets_str}</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col_d4:
        st.markdown(
            f"""
        <div class="td-kpi">
            <div class="td-kpi-label">Total instrumentos</div>
            <div class="td-kpi-val">{len(all_inst)}</div>
            <div class="td-kpi-sub">lidos</div>
        </div>""",
            unsafe_allow_html=True,
        )

    # Classificação + origem por aba
    st.markdown(
        '<div class="td-section">Origem por Classe</div>', unsafe_allow_html=True
    )
    diag_origin_rows = ""
    summary = reader.summary()
    by_class = summary.get("by_class", {})
    class_origins = summary.get("class_origins", {})

    for cls_label in ["ACAO", "OPCAO", "FUTURO", "INDICE", "OUTRO"]:
        cls_data = by_class.get(cls_label, {})
        origins = class_origins.get(cls_label, {})
        total_cls = cls_data.get("total", 0)
        ao_cls = cls_data.get("ao_vivo", 0)
        orig_str = (
            "; ".join(f"{aba}={cnt}" for aba, cnt in sorted(origins.items()))
            if origins
            else "—"
        )
        diag_origin_rows += f"""
        <tr>
            <td><span style="font-weight:800;color:#F1F5F9;">{cls_label}</span></td>
            <td>{total_cls}</td>
            <td class="diag-ok">{ao_cls}</td>
            <td style="font-size:0.60rem;color:#64748B;">{orig_str}</td>
        </tr>
        """

    st.markdown(
        f"""
    <div class="td-table-wrap">
        <table class="td-table">
            <thead>
                <tr>
                    <th>Classe</th><th>Total</th><th>AO_VIVO</th><th>Origem (aba=qtd)</th>
                </tr>
            </thead>
            <tbody>{diag_origin_rows}</tbody>
        </table>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Per-class summary
    st.markdown(
        '<div class="td-section">Instrumentos por Classe</div>', unsafe_allow_html=True
    )
    diag_rows = ""
    for label, insts in [
        ("ACAO", list(acoes.values())),
        ("OPCAO", list(opcoes.values())),
        ("FUTURO", list(futuros.values())),
        ("INDICE", list(indices.values())),
        ("OUTRO", list(outros.values())),
    ]:
        total = len(insts)
        ao_v = sum(1 for p in insts if p.status == DataStatus.AO_VIVO)
        sem_pre = sum(1 for p in insts if p.status == DataStatus.SEM_PRECO)
        sem_bid = sum(1 for p in insts if p.status == DataStatus.SEM_BID_ASK)
        # vazios
        campos_vazios = []
        if total > 0:
            for fld in [
                "preco",
                "bid",
                "ask",
                "variacao",
                "volume",
                "negocios",
                "vwap",
                "rsi",
                "macd",
                "adx",
                "boll_b",
            ]:
                cnt_none = sum(1 for p in insts if getattr(p, fld, None) is None)
                if cnt_none == total:
                    campos_vazios.append(f"{fld} (todos)")
        vazios_str = ", ".join(campos_vazios) if campos_vazios else "nenhum"

        diag_rows += f"""
        <tr>
            <td><span style="font-weight:800;color:#F1F5F9;">{label}</span></td>
            <td>{total}</td>
            <td class="diag-ok">{ao_v}</td>
            <td class="diag-warn">{sem_bid}</td>
            <td class="diag-err">{sem_pre}</td>
            <td style="font-size:0.60rem;color:#64748B;">{vazios_str}</td>
        </tr>
        """

    st.markdown(
        f"""
    <div class="td-table-wrap">
        <table class="td-table">
            <thead>
                <tr>
                    <th>Classe</th><th>Total</th>
                    <th>AO_VIVO</th><th>SEM_BID_ASK</th><th>SEM_PRECO</th>
                    <th>Campos vazios em todos</th>
                </tr>
            </thead>
            <tbody>{diag_rows}</tbody>
        </table>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Opções ausentes no RTD
    st.markdown(
        '<div class="td-section">Opções da Shortlist Ausentes no RTD</div>',
        unsafe_allow_html=True,
    )
    if shortlist_df.empty:
        st.markdown(
            '<div class="td-info">Shortlist vazia.</div>', unsafe_allow_html=True
        )
    else:
        ausentes = []
        for _, r in shortlist_df.iterrows():
            tk = str(r.get("ticker", "")).strip()
            if tk not in rtd_set:
                ativo = str(r.get("ativo_objeto", ""))
                tipo = str(r.get("tipo", ""))
                strike = r.get("strike", 0)
                venc = str(r.get("vencimento", ""))[:10]
                ausentes.append((tk, ativo, tipo, strike, venc))

        if not ausentes:
            st.markdown(
                '<div class="td-success">✅ Todas as opções da shortlist estão no RTD.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
            <div class="td-warn">
                ⚠️ {len(ausentes)} opções da shortlist ausentes no RTD.<br>
                Adicione-as manualmente no Profit RTD.
            </div>""",
                unsafe_allow_html=True,
            )
            aus_rows = ""
            for tk, ativo, tipo, strike, venc in ausentes[:20]:
                tipo_c = "#22C55E" if tipo == "CALL" else "#EF4444"
                aus_rows += f"""
                <tr>
                    <td><div class="td-ticker">{tk}</div></td>
                    <td style="color:#64748B;">{ativo}</td>
                    <td><span style="color:{tipo_c};font-weight:700;font-size:0.68rem;">{tipo}</span></td>
                    <td>{strike:.2f}</td>
                    <td style="color:#64748B;font-size:0.60rem;">{venc}</td>
                </tr>
                """
            st.markdown(
                f"""
            <div class="td-table-wrap">
                <table class="td-table">
                    <thead>
                        <tr>
                            <th>Ticker</th><th>Ativo</th><th>Tipo</th>
                            <th>Strike</th><th>Vencimento</th>
                        </tr>
                    </thead>
                    <tbody>{aus_rows}</tbody>
                </table>
            </div>
            """,
                unsafe_allow_html=True,
            )
            if len(ausentes) > 20:
                st.markdown(
                    f'<div style="font-size:0.60rem;color:#64748B;margin-top:4px;">Mostrando 20 de {len(ausentes)} ausentes.</div>',
                    unsafe_allow_html=True,
                )

    # Tabela completa de status por instrumento
    st.markdown(
        '<div class="td-section">Status Completo — {len(all_inst)} Instrumentos</div>'.format(
            len(all_inst)
        ),
        unsafe_allow_html=True,
    )
    full_rows = ""
    for ticker, p in sorted(all_inst.items()):
        st_cor = (
            "#22C55E"
            if p.status == DataStatus.AO_VIVO
            else "#F59E0B" if p.status == DataStatus.SEM_BID_ASK else "#EF4444"
        )
        cls_cor = (
            "#22D3EE"
            if p.classe == InstrumentClass.ACAO
            else (
                "#22C55E"
                if p.classe == InstrumentClass.FUTURO
                else "#EAB308" if p.classe == InstrumentClass.OPCAO else "#94A3B8"
            )
        )
        prec_s = _fmt_preco(p.preco)
        bid_s = _fmt_preco(p.bid)
        ask_s = _fmt_preco(p.ask)
        spr_s = f"{p.spread_pct:.2f}%" if p.spread_pct else "—"
        vol_s = _fmt_vol(p.volume)
        rsi_s = f"{p.rsi:.0f}" if p.rsi else "—"
        macd_s = f"{p.macd:.2f}" if p.macd else "—"
        adx_s = f"{p.adx:.0f}" if p.adx else "—"

        full_rows += f"""
        <tr>
            <td><div class="td-ticker">{ticker}</div></td>
            <td><span style="color:{cls_cor};font-size:0.60rem;font-weight:700;">{p.classe.value}</span></td>
            <td>{prec_s}</td>
            <td>{bid_s}</td>
            <td>{ask_s}</td>
            <td>{spr_s}</td>
            <td>{vol_s}</td>
            <td>{rsi_s}</td>
            <td>{macd_s}</td>
            <td>{adx_s}</td>
            <td><span style="color:{st_cor};font-size:0.60rem;font-weight:700;">{p.status.value}</span></td>
            <td>{p.timestamp[:16]}</td>
        </tr>
        """

    st.markdown(
        f"""
    <div class="td-table-wrap">
        <table class="td-table">
            <thead>
                <tr>
                    <th>Ticker</th><th>Classe</th><th>Preço</th>
                    <th>Bid</th><th>Ask</th><th>Spread</th>
                    <th>Volume</th>
                    <th>RSI</th><th>MACD</th><th>ADX</th>
                    <th>Status</th><th>Timestamp</th>
                </tr>
            </thead>
            <tbody>{full_rows}</tbody>
        </table>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div style="margin-top:24px;padding:10px 0;border-top:1px solid #1E2D42;
font-family:'JetBrains Mono',monospace;font-size:0.56rem;color:#334155;
display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <span>TRADE DESK · {RTD_PATH.name} · {len(all_inst)} instrumentos · {len(acoes)} ações · {len(futuros)} futuros · {len(opcoes)} opções no RTD</span>
    <span>{agora} · refresh: {'auto ' + str(refresh_sec) + 's' if refresh_sec > 0 else 'manual'}</span>
</div>
""",
    unsafe_allow_html=True,
)
