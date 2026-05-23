"""
Performance & Risk Dashboard — Página Streamlit.

Exibe métricas reais do diário de trades + simulação de backtest.
Integra: TradeJournal · BacktestEngine · RiskEngine · performance analytics.
"""
from __future__ import annotations

import math
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT          = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT.parent / "12_PYTHON"

for _k in list(sys.modules):
    if _k == "src" or _k.startswith("src."):
        del sys.modules[_k]

if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.append(str(PIPELINE_ROOT))

import streamlit as st
import pandas as pd
import numpy as np

from src.ui.styles import PREMIUM_CSS
from src.ui.components import (
    section_title, kpi_card, status_chip, alert_block,
    metric_card, metric_table_row, empty_state,
)
from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import load_quant_config
from src.journal.trade_journal import TradeJournal, JournalTrade
from src.quant.performance import full_summary

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ── Paleta ────────────────────────────────────────────────────────────────────
_BG     = "#080D17"
_BG2    = "#111827"
_GRID   = "#1E2D42"
_GREEN  = "#22C55E"
_RED    = "#EF4444"
_CYAN   = "#22D3EE"
_AMBER  = "#F59E0B"
_TEXT   = "#64748B"
_WHITE  = "#E2E8F0"

_CSS = """
<style>
section.main > div { padding-top: 0.5rem; }

.perf-header {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 60%, #060B14 100%);
    border: 1px solid #1E3A5F; border-radius: 12px;
    padding: 16px 24px 14px; margin-bottom: 18px; position: relative; overflow: hidden;
}
.perf-header::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #7C3AED 0%, #22D3EE 50%, #22C55E 100%);
}
.perf-title { font-size: 1.3rem; font-weight: 900; color: #F1F5F9; margin: 0; }
.perf-sub   { font-size: 0.72rem; color: #334155; margin-top: 4px; }

.kpi-strip  { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
.kpi-card   {
    flex: 1; min-width: 120px; background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 14px 16px; text-align: center; position: relative; overflow: hidden;
}
.kpi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
.kc-green::before  { background: #22C55E; }
.kc-red::before    { background: #EF4444; }
.kc-blue::before   { background: #3B82F6; }
.kc-purple::before { background: #7C3AED; }
.kc-amber::before  { background: #F59E0B; }
.kc-slate::before  { background: #475569; }
.kpi-label { font-size: 0.62rem; color: #334155; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 1.5rem; font-weight: 900; color: #F1F5F9; line-height: 1.15; }
.kpi-sub   { font-size: 0.63rem; color: #475569; margin-top: 2px; }

.sec-title {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #334155; margin: 22px 0 12px;
    display: flex; align-items: center; gap: 8px;
}
.sec-title::after { content:''; flex:1; height:1px; background:#1E2D42; }

.trade-row-win  { border-left: 3px solid #22C55E; }
.trade-row-loss { border-left: 3px solid #EF4444; }
.trade-row-open { border-left: 3px solid #F59E0B; }

.risk-box {
    background: #0D1421; border: 1px solid #1E3A5F;
    border-radius: 10px; padding: 18px; margin-bottom: 14px;
}
.risk-box h4 { color: #94A3B8; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 10px; }

.badge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 0.67rem; font-weight: 800; }
.b-win  { background: #052e16; color: #22C55E; }
.b-loss { background: #1c0909; color: #EF4444; }
.b-open { background: #1c1100; color: #F59E0B; }
.b-be   { background: #1A1A2E; color: #64748B; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
</style>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pnl_color(v: float) -> str:
    return _GREEN if v >= 0 else _RED


def _fmt_pnl(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}R${v:,.2f}"


def _plotly_dark(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=_BG,
        plot_bgcolor=_BG2,
        height=height,
        margin=dict(l=0, r=0, t=24, b=0),
        font=dict(color=_TEXT, size=11),
        legend=dict(bgcolor=_BG2, bordercolor=_GRID, borderwidth=1),
        xaxis=dict(gridcolor=_GRID, zeroline=False),
        yaxis=dict(gridcolor=_GRID, zeroline=False),
    )
    return fig


def _equity_chart(equity: pd.Series) -> go.Figure:
    if equity.empty:
        return go.Figure()

    peak = equity.cummax()
    dd   = equity - peak

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.04,
    )
    # Equity
    fig.add_trace(go.Scatter(
        y=equity.values, mode="lines", name="P&L Acumulado",
        line=dict(color=_CYAN, width=2.2),
        fill="tozeroy", fillcolor="rgba(34,211,238,0.07)",
    ), row=1, col=1)
    fig.add_hline(y=0, line_color=_GRID, line_dash="dash", line_width=1, row=1, col=1)

    # Drawdown
    fig.add_trace(go.Scatter(
        y=dd.values, mode="lines", name="Drawdown",
        line=dict(color=_RED, width=1.4),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.08)",
    ), row=2, col=1)

    fig.update_yaxes(tickprefix="R$", row=1, col=1, gridcolor=_GRID)
    fig.update_yaxes(tickprefix="R$", row=2, col=1, gridcolor=_GRID)
    fig.update_xaxes(title_text="Trade #", row=2, col=1, gridcolor=_GRID)

    return _plotly_dark(fig, height=380)


def _monthly_heatmap(monthly_df: pd.DataFrame) -> go.Figure:
    if monthly_df.empty:
        return go.Figure()

    monthly_df = monthly_df.copy()
    monthly_df["period"] = pd.to_datetime(monthly_df["month"])
    monthly_df["year"]   = monthly_df["period"].dt.year
    monthly_df["month_n"]= monthly_df["period"].dt.month

    pivot = monthly_df.pivot_table(index="year", columns="month_n", values="net_pnl", aggfunc="sum")
    months = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    pivot.columns = [months[m-1] for m in pivot.columns]

    z     = pivot.values.tolist()
    years = [str(y) for y in pivot.index.tolist()]
    cols  = pivot.columns.tolist()

    text  = [[_fmt_pnl(v) if not (v != v) else "" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z, x=cols, y=years,
        text=text, texttemplate="%{text}",
        colorscale=[[0, "#7f1d1d"], [0.5, "#1E2D42"], [1, "#052e16"]],
        showscale=False,
    ))
    fig.update_layout(
        title=dict(text="P&L Mensal (R$)", font=dict(size=12, color=_TEXT)),
        xaxis=dict(side="top"),
    )
    return _plotly_dark(fig, height=220)


def _win_rate_gauge(win_rate: float) -> go.Figure:
    color = _GREEN if win_rate >= 0.5 else (_AMBER if win_rate >= 0.4 else _RED)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=win_rate * 100,
        number=dict(suffix="%", font=dict(size=28, color=color)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=_TEXT),
            bar=dict(color=color, thickness=0.25),
            bgcolor=_BG2,
            bordercolor=_GRID,
            steps=[
                dict(range=[0, 40], color="#1c0909"),
                dict(range=[40, 55], color="#1c1100"),
                dict(range=[55, 100], color="#052e16"),
            ],
            threshold=dict(line=dict(color=_WHITE, width=2), thickness=0.6, value=50),
        ),
        domain=dict(x=[0, 1], y=[0, 1]),
    ))
    fig.update_layout(
        paper_bgcolor=_BG2, margin=dict(l=20, r=20, t=20, b=10), height=200
    )
    return fig


# ── Formulário — novo trade ───────────────────────────────────────────────────

def _form_new_trade(journal: TradeJournal):
    with st.expander("➕ Registrar novo trade", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            underlying  = st.text_input("Ativo (ex: PETR4)", key="jrn_und").upper()
            ticker      = st.text_input("Opção (ex: PETRE51)", key="jrn_tkr").upper()
            option_type = st.selectbox("Tipo", ["CALL", "PUT"], key="jrn_otype")
        with c2:
            entry_price = st.number_input("Preço de entrada (R$)", 0.001, 999.0, 1.0, 0.001, key="jrn_entry", format="%.4f")
            stop_price  = st.number_input("Stop (R$)",  0.001, 999.0, entry_price * 0.70, 0.001, key="jrn_stop", format="%.4f")
            target1     = st.number_input("Alvo 1 (R$)", 0.001, 999.0, entry_price * 1.50, 0.001, key="jrn_t1", format="%.4f")
        with c3:
            contracts   = st.number_input("Contratos", 1, 1000, 1, key="jrn_ctr")
            strategy    = st.selectbox("Estratégia", [
                "CALL_COMPRA", "SPREAD_ALTA", "SPREAD_BAIXA", "CONDOR",
                "BUTTERFLY", "RENDA", "PROTECAO", "OUTRO",
            ], key="jrn_strat")
            score       = st.slider("Score do setup", 0, 100, 60, key="jrn_sc")

        notes = st.text_area("Observações", "", key="jrn_notes")
        direction = st.radio("Direção", ["COMPRA", "VENDA"], horizontal=True, key="jrn_dir")

        if st.button("💾 Salvar trade", type="primary", key="jrn_save"):
            if not underlying or not ticker or entry_price <= 0:
                st.error("Preencha ativo, opção e preço de entrada.")
                return
            trade = JournalTrade(
                underlying=underlying,
                ticker=ticker,
                option_type=option_type,
                direction=direction,
                strategy=strategy,
                entry_price=entry_price,
                stop_price=stop_price,
                target1=target1,
                contracts=contracts,
                score=score,
                notes=notes,
            )
            trade_id = journal.add_trade(trade)
            st.success(f"Trade #{trade_id} registrado — {underlying} · {ticker}")
            st.rerun()


def _form_close_trade(journal: TradeJournal, open_df: pd.DataFrame):
    if open_df.empty:
        return
    with st.expander("✅ Fechar trade aberto", expanded=False):
        trade_options = {
            row["id"]: f"#{row['id']} {row['underlying']} · {row['ticker']} @ R${row['entry_price']:.4f}"
            for _, row in open_df.iterrows()
        }
        sel_id = st.selectbox("Trade", list(trade_options.keys()),
                              format_func=lambda i: trade_options[i], key="close_sel")
        c1, c2 = st.columns(2)
        with c1:
            exit_price = st.number_input("Preço de saída (R$)", 0.0001, 999.0, 1.0, 0.001, key="close_px", format="%.4f")
        with c2:
            exit_reason = st.selectbox("Motivo", ["ALVO1", "ALVO2", "STOP", "TEMPO", "MANUAL"], key="close_reason")
        close_notes = st.text_input("Nota de saída", key="close_notes")

        if st.button("Fechar trade", key="close_btn"):
            result = journal.close_trade(sel_id, exit_price, exit_reason, notes=close_notes)
            pnl = result["net_pnl"]
            if pnl >= 0:
                st.success(f"Trade fechado · P&L {_fmt_pnl(pnl)} · {result['outcome']}")
            else:
                st.error(f"Trade fechado · P&L {_fmt_pnl(pnl)} · {result['outcome']}")
            st.rerun()


# ── Risk Dashboard ────────────────────────────────────────────────────────────

def _risk_section(journal: TradeJournal, capital: float):
    summ = journal.daily_summary()
    perf = journal.performance_summary()

    daily_pnl    = summ["net_pnl"]
    daily_limit  = capital * 0.02
    weekly_limit = capital * 0.04

    pct_daily  = abs(daily_pnl) / daily_limit  if daily_limit  > 0 else 0
    pct_weekly = abs(daily_pnl) / weekly_limit if weekly_limit > 0 else 0

    daily_color  = _GREEN if daily_pnl >= 0 else (_AMBER if pct_daily < 0.7 else _RED)
    weekly_color = _GREEN if daily_pnl >= 0 else (_AMBER if pct_weekly < 0.7 else _RED)

    max_dd = perf.get("max_drawdown", 0) if isinstance(perf, dict) and "max_drawdown" in perf else 0

    st.markdown(f"""
    <div class="risk-box">
      <h4>📊 Exposição de Risco — {summ['date']}</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
        <div>
          <div style="font-size:0.63rem;color:#334155;text-transform:uppercase;letter-spacing:1px">P&L Hoje</div>
          <div style="font-size:1.4rem;font-weight:900;color:{daily_color}">{_fmt_pnl(daily_pnl)}</div>
          <div style="font-size:0.68rem;color:#334155">Limite diário R${daily_limit:,.0f}</div>
          <div style="background:#1E2D42;border-radius:3px;height:3px;margin-top:6px">
            <div style="width:{min(pct_daily*100,100):.0f}%;height:3px;border-radius:3px;background:{daily_color}"></div>
          </div>
        </div>
        <div>
          <div style="font-size:0.63rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Trades Fechados Hoje</div>
          <div style="font-size:1.4rem;font-weight:900;color:#F1F5F9">{summ['total_closed']}</div>
          <div style="font-size:0.68rem;color:#334155">{summ['wins']}W · {summ['losses']}L</div>
        </div>
        <div>
          <div style="font-size:0.63rem;color:#334155;text-transform:uppercase;letter-spacing:1px">Max Drawdown</div>
          <div style="font-size:1.4rem;font-weight:900;color:{_RED if max_dd < -capital*0.05 else _AMBER}">{_fmt_pnl(max_dd)}</div>
          <div style="font-size:0.68rem;color:#334155">histórico</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Layer canonical design tokens beneath performance-specific overrides
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
    st.markdown(_CSS, unsafe_allow_html=True)

    cfg  = load_config()
    qcfg = load_quant_config()

    db_path   = project_path(cfg["database_path"])
    jrn_path  = db_path.parent / "journal.db"
    journal   = TradeJournal(jrn_path)

    # ── Header ──
    st.markdown("""
    <div class="perf-header">
      <div class="perf-title">📈 Performance & Risk</div>
      <div class="perf-sub">Diário de trades · Métricas reais · Gestão de risco</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Configuração de capital ──
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        capital = st.number_input("Capital (R$)", 1_000, 1_000_000, 10_000, 1_000)
        show_section = st.radio("Seção", [
            "📊 Visão Geral",
            "📋 Diário de Trades",
            "📉 Risco",
            "📤 Importar Backtest",
        ], label_visibility="collapsed")

    # ── Dados ──
    open_df   = journal.list_open()
    closed_df = journal.list_closed()
    perf      = journal.performance_summary()
    equity    = journal.equity_series()
    monthly   = journal.monthly_pnl()

    has_data = isinstance(perf, dict) and "total_trades" in perf

    # ════════════════════════════════════════════════════════════════════════
    if show_section == "📊 Visão Geral":
    # ════════════════════════════════════════════════════════════════════════

        if not has_data:
            st.info("Sem trades fechados ainda. Registre operações na aba **Diário de Trades**.")
        else:
            total = perf["total_trades"]
            wr    = perf["win_rate"]
            pnl   = perf["gross_pnl"]
            payoff= perf["payoff"]
            exp   = perf["expectancy"]
            max_dd= perf["max_drawdown"]
            best  = perf["best_trade"]
            worst = perf["worst_trade"]

            pnl_color  = _GREEN if pnl >= 0 else _RED
            wr_color   = _GREEN if wr >= 0.5 else (_AMBER if wr >= 0.4 else _RED)
            dd_color   = _AMBER if abs(max_dd) < capital * 0.10 else _RED

            # KPIs
            st.markdown(f"""
            <div class="kpi-strip">
              <div class="kpi-card kc-blue">
                <div class="kpi-label">Trades</div>
                <div class="kpi-value">{total}</div>
                <div class="kpi-sub">{perf['wins']}W · {perf['losses']}L</div>
              </div>
              <div class="kpi-card {'kc-green' if wr>=0.5 else 'kc-amber'}">
                <div class="kpi-label">Win Rate</div>
                <div class="kpi-value" style="color:{wr_color}">{wr:.1%}</div>
                <div class="kpi-sub">meta ≥ 50%</div>
              </div>
              <div class="kpi-card {'kc-green' if pnl>=0 else 'kc-red'}">
                <div class="kpi-label">P&L Realizado</div>
                <div class="kpi-value" style="color:{pnl_color};font-size:1.2rem">{_fmt_pnl(pnl)}</div>
                <div class="kpi-sub">líquido</div>
              </div>
              <div class="kpi-card kc-purple">
                <div class="kpi-label">Payoff Ratio</div>
                <div class="kpi-value">{payoff:.2f}x</div>
                <div class="kpi-sub">ganho/perda médios</div>
              </div>
              <div class="kpi-card kc-amber">
                <div class="kpi-label">Expectativa/Trade</div>
                <div class="kpi-value" style="color:{'#22C55E' if exp>=0 else '#EF4444'};font-size:1.2rem">{_fmt_pnl(exp)}</div>
                <div class="kpi-sub">esperança matemática</div>
              </div>
              <div class="kpi-card {'kc-amber' if abs(max_dd)<capital*0.1 else 'kc-red'}">
                <div class="kpi-label">Max Drawdown</div>
                <div class="kpi-value" style="color:{dd_color};font-size:1.2rem">{_fmt_pnl(max_dd)}</div>
                <div class="kpi-sub">histórico</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Gráficos
            if HAS_PLOTLY and not equity.empty:
                col_eq, col_wr = st.columns([3, 1])
                with col_eq:
                    st.markdown('<div class="sec-title">📈 Curva de Capital</div>', unsafe_allow_html=True)
                    st.plotly_chart(_equity_chart(equity), use_container_width=True)
                with col_wr:
                    st.markdown('<div class="sec-title">🎯 Win Rate</div>', unsafe_allow_html=True)
                    st.plotly_chart(_win_rate_gauge(wr), use_container_width=True)
                    st.markdown(f"""
                    <div style="text-align:center;margin-top:6px">
                      <div style="font-size:0.68rem;color:#334155">Melhor trade</div>
                      <div style="font-size:1rem;font-weight:800;color:#22C55E">{_fmt_pnl(best)}</div>
                      <div style="font-size:0.68rem;color:#334155;margin-top:8px">Pior trade</div>
                      <div style="font-size:1rem;font-weight:800;color:#EF4444">{_fmt_pnl(worst)}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if HAS_PLOTLY and not monthly.empty:
                st.markdown('<div class="sec-title">📅 P&L Mensal</div>', unsafe_allow_html=True)
                st.plotly_chart(_monthly_heatmap(monthly), use_container_width=True)

        # Posições abertas (sempre visível)
        if not open_df.empty:
            st.markdown(f'<div class="sec-title">⚡ Posições Abertas ({len(open_df)})</div>', unsafe_allow_html=True)
            st.dataframe(open_df, use_container_width=True, height=200)

    # ════════════════════════════════════════════════════════════════════════
    elif show_section == "📋 Diário de Trades":
    # ════════════════════════════════════════════════════════════════════════

        _form_new_trade(journal)
        if not open_df.empty:
            _form_close_trade(journal, open_df)

        st.markdown('<div class="sec-title">📋 Trades Fechados</div>', unsafe_allow_html=True)

        if closed_df.empty:
            st.info("Nenhum trade fechado registrado.")
        else:
            _OUTCOME_BADGE = {
                "WIN":       '<span class="badge b-win">✅ WIN</span>',
                "LOSS":      '<span class="badge b-loss">❌ LOSS</span>',
                "BREAKEVEN": '<span class="badge b-be">➡ BE</span>',
            }

            def _style_row(row):
                styles = [""] * len(row)
                idx = list(row.index)
                if "net_pnl" in idx:
                    v = row["net_pnl"]
                    if isinstance(v, (int, float)):
                        styles[idx.index("net_pnl")] = (
                            "color:#22C55E;font-weight:700" if v >= 0
                            else "color:#EF4444;font-weight:700"
                        )
                if "outcome" in idx:
                    bg = {"WIN": "#052e16", "LOSS": "#1c0909", "BREAKEVEN": "#1A1A2E"}.get(
                        str(row["outcome"]), ""
                    )
                    styles[idx.index("outcome")] = f"background:{bg};font-weight:700"
                return styles

            cols_show = ["id","date_entry","date_exit","underlying","ticker","strategy",
                         "entry_price","exit_price","gross_pnl","net_pnl","exit_reason","outcome","score"]
            cols_ok = [c for c in cols_show if c in closed_df.columns]
            styled = closed_df[cols_ok].style.apply(_style_row, axis=1)
            st.dataframe(styled, use_container_width=True, height=420)

            csv = closed_df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig")
            st.download_button("⬇️ Exportar Diário CSV", csv, "journal_trades.csv", "text/csv")

        # Deletar trade (admin)
        with st.expander("🗑 Remover trade (admin)", expanded=False):
            all_df = journal.all_trades()
            if not all_df.empty:
                del_id = st.number_input("ID do trade para remover", 1, int(all_df["id"].max()), 1, key="del_id")
                if st.button("Remover", key="del_btn"):
                    journal.delete_trade(int(del_id))
                    st.warning(f"Trade #{del_id} removido.")
                    st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    elif show_section == "📉 Risco":
    # ════════════════════════════════════════════════════════════════════════

        _risk_section(journal, capital)

        st.markdown('<div class="sec-title">⚙️ Parâmetros de Risco</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        risco_trade = capital * 0.005
        limite_dia  = capital * 0.02
        limite_sem  = capital * 0.04

        with c1:
            st.metric("Risco por trade",  f"R${risco_trade:,.0f}", "0.5% capital")
            st.metric("Máx risco/trade",  f"R$500",               "teto absoluto")
        with c2:
            st.metric("Limite diário",    f"R${limite_dia:,.0f}", "2% capital")
            st.metric("Limite semanal",   f"R${limite_sem:,.0f}", "4% capital")
        with c3:
            st.metric("Máx posições",     "5",                    "simultâneas")
            st.metric("Máx por ativo",    f"R${capital*0.02:,.0f}", "2% capital")

        st.markdown("""
        <div class="risk-box" style="margin-top:16px">
          <h4>📌 Regras do Sistema</h4>
          <ul style="color:#64748B;font-size:0.82rem;line-height:1.8;margin:0;padding-left:18px">
            <li>Nunca arrisque mais de <strong style="color:#F1F5F9">0.5% do capital</strong> por operação</li>
            <li>Encerre o dia ao atingir <strong style="color:#EF4444">−2% do capital</strong></li>
            <li>Encerre a semana ao atingir <strong style="color:#EF4444">−4% do capital</strong></li>
            <li>Máximo de <strong style="color:#F1F5F9">5 posições simultâneas</strong></li>
            <li>Nunca opere sem stop definido</li>
            <li>Apenas risco definido em setups especulativos</li>
            <li>Reduza 50% da posição no Alvo 1, deixe o restante correr</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    elif show_section == "📤 Importar Backtest":
    # ════════════════════════════════════════════════════════════════════════

        st.markdown('<div class="sec-title">📤 Importar Trades do Backtest</div>', unsafe_allow_html=True)
        st.info(
            "Importa o resultado de uma simulação de backtest para o diário, "
            "permitindo comparar trades simulados com os reais."
        )

        uploaded = st.file_uploader("Arquivo CSV do backtest (separador ;)", type="csv")
        if uploaded:
            try:
                df_bt = pd.read_csv(uploaded, sep=";", decimal=",")
                st.dataframe(df_bt.head(10), use_container_width=True)
                if st.button("📥 Importar para o diário"):
                    n = journal.import_from_backtest(df_bt)
                    st.success(f"{n} trades importados do backtest.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao ler CSV: {e}")


main()
