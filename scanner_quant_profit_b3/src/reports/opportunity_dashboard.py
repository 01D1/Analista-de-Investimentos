"""
Dashboard Multi-Painel — Quant Research Layer.

5 painéis via Streamlit:
  1. Principal     — overview e setups do scanner
  2. Risco         — estado dos limites operacionais
  3. Performance   — curva de capital, métricas, drawdown
  4. Oportunidades — cards detalhados com plano operacional
  5. Diário        — histórico de trades

Uso:
    streamlit run src/reports/opportunity_dashboard.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import (
    load_quant_config,
    run_strategy,
    SETUP_STATUS_LABELS,
)
from src.quant.performance import full_summary, drawdown
from src.quant.risk_engine import RiskEngine
from src.quant.execution_assistant import build_execution_plan
from src.reports.report_generator import rank_assets, rank_options


# ---------------------------------------------------------------------------
# Constantes de estilo
# ---------------------------------------------------------------------------

STATUS_COLOR = {
    "ENTRADA_VALIDADA": "#00b300",
    "AGUARDAR_GATILHO": "#e6a817",
    "INVALIDADO": "#cc3300",
    "EM_ABERTO": "#0066cc",
    "ALVO_1": "#007acc",
    "ALVO_2": "#004080",
    "STOPADO": "#800000",
}
STATUS_ICON = {
    "ENTRADA_VALIDADA": "✅",
    "AGUARDAR_GATILHO": "⏳",
    "INVALIDADO": "❌",
    "EM_ABERTO": "📌",
    "ALVO_1": "🎯",
    "ALVO_2": "🏆",
    "STOPADO": "🛑",
}


# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _load_setups(qcfg_hash: str, min_vol, min_trades, min_dte, max_dte, top) -> pd.DataFrame:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    if not db_path.exists():
        return pd.DataFrame()
    qcfg = load_quant_config()
    con = sqlite3.connect(db_path)
    try:
        return run_strategy(
            con=con, cfg=cfg, qcfg=qcfg,
            account=qcfg.get("capital_inicial", 10_000),
            risk=qcfg.get("risco_por_trade", 0.005),
            min_volume=min_vol, min_trades=min_trades,
            min_dte=min_dte, max_dte=max_dte, top=top,
        )
    finally:
        con.close()


def _load_journal() -> pd.DataFrame:
    j = project_path("data/journal/trade_journal.csv")
    if not j.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(j, sep=";", encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def _load_journal_from_db() -> pd.DataFrame:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    if not db_path.exists():
        return pd.DataFrame()
    try:
        con = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM trade_journal ORDER BY rowid DESC", con)
        con.close()
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Sidebar compartilhada
# ---------------------------------------------------------------------------

def _render_sidebar() -> tuple[dict, float, int, int, int, int, bool]:
    with st.sidebar:
        st.title("⚙️ Parâmetros")
        st.caption("⚠️ Apenas alertas — nenhuma ordem real.")

        qcfg = load_quant_config()

        capital = st.number_input(
            "Capital (R$)", value=float(qcfg.get("capital_inicial", 10_000)),
            min_value=1_000.0, step=1_000.0,
        )
        risk = st.slider(
            "Risco/trade (%)", 0.1, 2.0,
            float(qcfg.get("risco_por_trade", 0.005)) * 100, 0.1,
        ) / 100
        min_vol = st.number_input(
            "Volume mín. opção (R$)",
            value=float(qcfg.get("min_volume_opcao", 100_000)),
            min_value=10_000.0, step=10_000.0,
        )
        min_trades = st.number_input(
            "Negócios mín.", value=int(qcfg.get("min_negocios_opcao", 10)),
            min_value=1, step=1,
        )
        min_dte = st.slider("DTE mínimo", 5, 30, int(qcfg.get("min_dte", 15)))
        max_dte = st.slider("DTE máximo", 20, 90, int(qcfg.get("max_dte", 45)))
        top = st.slider("Máx. resultados", 5, 50, 20)

        qcfg["capital_inicial"] = capital
        qcfg["risco_por_trade"] = risk

        run_btn = st.button("🔄 Atualizar Scanner", use_container_width=True)
        st.divider()

        filter_status = st.multiselect(
            "Filtrar status",
            ["ENTRADA_VALIDADA", "AGUARDAR_GATILHO", "INVALIDADO"],
            default=["ENTRADA_VALIDADA", "AGUARDAR_GATILHO"],
        )

    return qcfg, min_vol, int(min_trades), min_dte, max_dte, top, run_btn, filter_status


# ---------------------------------------------------------------------------
# Painel 1 — Principal
# ---------------------------------------------------------------------------

def _panel_main(df: pd.DataFrame, filter_status: list[str]) -> None:
    st.title("📊 Scanner Quant B3 — CALL_CONTINUIDADE")
    st.caption("Motor de decisão quantitativa. Apenas alertas para decisão manual do operador.")

    if df.empty:
        st.warning("Nenhum setup. Importe o COTAHIST primeiro.")
        st.code("python -m src.collectors.b3_cotahist_collector --year 2026")
        return

    df_f = df[df["status"].isin(filter_status)] if filter_status else df

    n_val = int((df_f["status"] == "ENTRADA_VALIDADA").sum())
    n_agt = int((df_f["status"] == "AGUARDAR_GATILHO").sum())
    avg_score = float(df_f["final_score"].mean()) if not df_f.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Setups", len(df_f))
    c2.metric("✅ Entrada Validada", n_val)
    c3.metric("⏳ Aguardar Gatilho", n_agt)
    c4.metric("Score Médio", f"{avg_score:.1f}")

    st.divider()

    # Rankings rápidos
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("🏆 Top Ativos")
        asset_rank = rank_assets(df)
        if not asset_rank.empty:
            st.dataframe(asset_rank, use_container_width=True, hide_index=True)
    with r2:
        st.subheader("🥇 Top Opções")
        opt_rank = rank_options(df, top=8)
        if not opt_rank.empty:
            show_cols = ["ticker", "underlying", "final_score", "delta", "dte",
                         "moneyness", "option_liquidity_score", "status"]
            sc = [c for c in show_cols if c in opt_rank.columns]
            st.dataframe(opt_rank[sc], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📋 Tabela Completa")
    cols_table = [
        "ticker", "underlying", "option_type", "status", "final_score",
        "preco_opcao", "strike", "dte", "delta", "theta",
        "contratos", "stop", "alvo_1", "alvo_2", "risco_financeiro", "payoff_ratio",
    ]
    existing = [c for c in cols_table if c in df_f.columns]
    st.dataframe(df_f[existing].reset_index(drop=True), use_container_width=True)

    csv_bytes = df_f.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar CSV",
        data=csv_bytes,
        file_name=f"setups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Painel 2 — Risco
# ---------------------------------------------------------------------------

def _panel_risk(df: pd.DataFrame, qcfg: dict) -> None:
    st.title("🛡️ Painel de Risco")
    st.caption("Monitoramento de limites operacionais em tempo real.")

    engine = RiskEngine.from_qcfg(qcfg)
    summary = engine.risk_summary()

    capital = summary["capital"]
    daily_pnl_pct = summary["daily_pnl_pct"]
    weekly_pnl_pct = summary["weekly_pnl_pct"]
    daily_limit = summary["daily_limit_pct"]
    weekly_limit = summary["weekly_limit_pct"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capital", f"R$ {capital:,.2f}")
    c2.metric(
        "P&L Diário",
        f"{daily_pnl_pct:.2f}%",
        delta=f"Limite: {daily_limit:.1f}%",
        delta_color="off",
    )
    c3.metric(
        "P&L Semanal",
        f"{weekly_pnl_pct:.2f}%",
        delta=f"Limite: {weekly_limit:.1f}%",
        delta_color="off",
    )
    c4.metric("Posições Abertas", f"{summary['open_positions']} / {summary['max_open']}")

    st.divider()

    lc1, lc2 = st.columns(2)
    with lc1:
        st.subheader("Limite Diário")
        used_daily = abs(min(0, daily_pnl_pct)) / daily_limit if daily_limit > 0 else 0
        st.progress(min(used_daily, 1.0))
        headroom = summary["daily_headroom"]
        status_daily = "🟢 OK" if used_daily < 0.7 else ("🟡 ATENÇÃO" if used_daily < 1.0 else "🔴 ATINGIDO")
        st.caption(f"{status_daily} — Espaço restante: R$ {headroom:.2f}")

    with lc2:
        st.subheader("Limite Semanal")
        used_weekly = abs(min(0, weekly_pnl_pct)) / weekly_limit if weekly_limit > 0 else 0
        st.progress(min(used_weekly, 1.0))
        headroom_w = summary["weekly_headroom"]
        status_weekly = "🟢 OK" if used_weekly < 0.7 else ("🟡 ATENÇÃO" if used_weekly < 1.0 else "🔴 ATINGIDO")
        st.caption(f"{status_weekly} — Espaço restante: R$ {headroom_w:.2f}")

    st.divider()
    st.subheader("📐 Configuração de Limites")
    risk_cfg_data = {
        "Parâmetro": [
            "Risco por trade", "Teto absoluto/trade",
            "Limite perda diária", "Limite perda semanal",
            "Máx risco por ativo", "Máx trades mesmo vencimento",
            "Máx trades mesmo tipo", "Máx posições abertas",
        ],
        "Valor": [
            f"{qcfg.get('risco_por_trade', 0.005)*100:.2f}%",
            f"R$ {qcfg.get('max_risco_abs_por_trade', 500):.0f}",
            f"{qcfg.get('limite_perda_diaria', 0.02)*100:.1f}%",
            f"{qcfg.get('limite_perda_semanal', 0.04)*100:.1f}%",
            f"{qcfg.get('max_risco_por_ativo', 0.02)*100:.1f}%",
            str(qcfg.get("max_trades_mesmo_vencimento", 2)),
            str(qcfg.get("max_trades_mesmo_tipo", 3)),
            str(qcfg.get("max_posicoes_abertas", 5)),
        ],
    }
    st.dataframe(pd.DataFrame(risk_cfg_data), use_container_width=True, hide_index=True)

    if not df.empty:
        st.divider()
        st.subheader("🔍 Avaliação de Risco por Setup")
        for _, row in df[df.get("status", pd.Series()) == "ENTRADA_VALIDADA"].head(5).iterrows():
            verdict = engine.evaluate(
                underlying=str(row.get("underlying", "")),
                option_type=str(row.get("option_type", "CALL")),
                expiry=str(row.get("expiration_date", "")),
                entry=float(row.get("preco_opcao", 0) or 0),
                stop=float(row.get("stop", 0) or 0),
                contracts=int(row.get("contratos", 0) or 0),
                hist_vol=float(row.get("hist_vol", 0) or 0),
            )
            color = "#00b300" if verdict.approved and not verdict.warnings else (
                "#e6a817" if verdict.approved else "#cc3300"
            )
            st.markdown(
                f"**{verdict.verdict_str}** — `{row.get('ticker', '')}` "
                f"Risco calculado: R$ {verdict.risk_amount:.2f}",
            )
            for w in verdict.warnings:
                st.warning(f"⚠️ {w}")
            for b in verdict.blocks:
                st.error(f"🚫 {b}")


# ---------------------------------------------------------------------------
# Painel 3 — Performance
# ---------------------------------------------------------------------------

def _panel_performance(qcfg: dict) -> None:
    st.title("📈 Painel de Performance")

    journal = _load_journal_from_db()
    if journal.empty:
        journal = _load_journal()

    if journal.empty:
        st.info("Nenhum trade registrado. Execute com --journal para registrar setups.")
        st.caption("Dica: use `python -m src.strategies.call_continuity_strategy --journal` para adicionar trades ao diário.")
        return

    capital = float(qcfg.get("capital_inicial", 10_000))

    ret_col = next((c for c in ["retorno_pct", "return_pct"] if c in journal.columns), None)
    if ret_col is None:
        st.warning("Coluna de retorno não encontrada no diário.")
        return

    pnl = journal[ret_col].dropna().astype(float) * capital / 100
    if len(pnl) == 0:
        st.info("Sem retornos calculados no diário.")
        return

    stats = full_summary(pnl, capital=capital)

    # Métricas principais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Trades", stats.get("total_trades", 0))
    c2.metric("Win Rate", f"{stats.get('win_rate', 0)*100:.1f}%")
    c3.metric("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
    c4.metric("Sharpe", f"{stats.get('sharpe', 0):.3f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Expectancy", f"R$ {stats.get('expectancy', 0):.2f}")
    c6.metric("Payoff Ratio", f"{stats.get('payoff_ratio', 0):.2f}x")
    c7.metric("Max Drawdown", f"{stats.get('max_drawdown', 0)*100:.2f}%")
    c8.metric("Retorno Total", f"{stats.get('total_return_pct', 0):.2f}%")

    st.divider()

    # Curva de capital
    st.subheader("💹 Curva de Capital")
    equity = (1.0 + pnl / capital).cumprod() * capital
    st.line_chart(equity.rename("Patrimônio (R$)"))

    # Drawdown
    st.subheader("📉 Drawdown")
    dd_series, max_dd = drawdown(equity)
    st.area_chart(dd_series.rename("Drawdown"))

    st.divider()

    # Tabela completa de métricas
    st.subheader("📊 Métricas Detalhadas")
    metrics_labels = {
        "total_trades": "Total de Trades",
        "win_rate": "Win Rate",
        "payoff_ratio": "Payoff Ratio",
        "profit_factor": "Profit Factor",
        "expectancy": "Expectancy (R$)",
        "avg_trade": "Trade Médio (R$)",
        "best_trade": "Melhor Trade (R$)",
        "worst_trade": "Pior Trade (R$)",
        "total_pnl": "P&L Total (R$)",
        "total_return_pct": "Retorno Total (%)",
        "avg_win": "Ganho Médio (R$)",
        "avg_loss": "Perda Média (R$)",
        "max_drawdown": "Máx Drawdown",
        "sharpe": "Sharpe Ratio",
        "sortino": "Sortino Ratio",
        "calmar": "Calmar Ratio",
        "final_capital": "Capital Final (R$)",
    }

    rows = []
    for key, label in metrics_labels.items():
        val = stats.get(key)
        if val is None:
            continue
        if key == "win_rate":
            display = f"{val*100:.2f}%"
        elif key == "max_drawdown":
            display = f"{val*100:.2f}%"
        else:
            display = f"{val:.4f}" if isinstance(val, float) else str(val)
        rows.append({"Métrica": label, "Valor": display})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Painel 4 — Oportunidades (cards)
# ---------------------------------------------------------------------------

def _panel_opportunities(df: pd.DataFrame, filter_status: list[str]) -> None:
    st.title("🃏 Painel de Oportunidades")

    if df.empty:
        st.warning("Nenhum setup disponível.")
        return

    df_f = df[df["status"].isin(filter_status)] if filter_status else df

    if df_f.empty:
        st.info("Nenhum setup passa pelos filtros de status selecionados.")
        return

    for _, row in df_f.iterrows():
        status = str(row.get("status", "INVALIDADO"))
        color = STATUS_COLOR.get(status, "#888")
        icon = STATUS_ICON.get(status, "")
        label = SETUP_STATUS_LABELS.get(status, status)

        with st.container():
            st.markdown(
                f"""
                <div style="border-left:5px solid {color}; padding:12px 16px;
                            background:#1e1e2e; border-radius:8px; margin-bottom:12px;">
                  <h4 style="margin:0; color:#fff;">
                    {icon} {row.get('ticker', '')}
                    <span style="color:#aaa; font-size:0.9em;"> ({row.get('underlying', '')}
                    · {row.get('option_type', '')}) </span>
                    <span style="float:right; font-size:1.1em; color:{color};">
                      Score: {row.get('final_score', 0):.1f}
                    </span>
                  </h4>
                  <p style="margin:4px 0; color:{color}; font-weight:bold;">{label}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Entrada", f"R$ {row.get('entrada_planejada', 0):.4f}")
            c2.metric("Stop", f"R$ {row.get('stop', 0):.4f}")
            c3.metric("Alvo 1", f"R$ {row.get('alvo_1', 0):.4f}")
            c4.metric("Alvo 2", f"R$ {row.get('alvo_2', 0):.4f}")
            c5.metric("Risco R$", f"R$ {row.get('risco_financeiro', 0):.2f}")
            c6.metric("Contratos", int(row.get("contratos", 0) or 0))

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("DTE", f"{int(row.get('dte', 0) or 0)} dias")
            sc2.metric("Strike", f"R$ {row.get('strike', 0):.2f}")
            sc3.metric("Moneyness", f"{row.get('moneyness', '?')} ({row.get('moneyness_pct', 0):+.1f}%)")

            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Delta", f"{row.get('delta', 0):.3f}")
            g2.metric("Gamma", f"{row.get('gamma', 0):.5f}")
            g3.metric("Theta/dia", f"{row.get('theta', 0):.4f}")
            g4.metric("Vega", f"{row.get('vega', 0):.4f}")

            # Valuation e Notícias
            upside = row.get("upside_pct")
            preco_alvo = row.get("preco_alvo")
            headline = str(row.get("headline", "") or "")
            headline_date = str(row.get("headline_date", "") or "")

            if upside is not None or headline:
                vn1, vn2 = st.columns([1, 2])
                if upside is not None and preco_alvo is not None:
                    vn1.metric(
                        "📐 Upside DCF",
                        f"{upside:+.1f}%",
                        delta=f"Alvo R$ {preco_alvo:.2f}",
                        delta_color="normal",
                    )
                if headline:
                    hl = (headline[:100] + "…") if len(headline) > 100 else headline
                    date_str = f" _{headline_date}_" if headline_date else ""
                    vn2.markdown(f"**📰 Notícias:** {hl}{date_str}")

            with st.expander("🔍 Plano operacional + scores detalhados"):
                plan = build_execution_plan(row)
                p1, p2 = st.columns(2)
                with p1:
                    st.markdown(f"**Sinal:** {plan.signal_type}  |  **Confiança:** {plan.confidence}")
                    st.markdown(f"**Invalidação:** Ativo abaixo de R$ {plan.invalidation:.2f}")
                    if plan.reasons_for:
                        st.markdown("**✅ Favoráveis:**")
                        for r in plan.reasons_for:
                            st.caption(f"• {r}")
                    if plan.reasons_against:
                        st.markdown("**⚠️ Contrários:**")
                        for r in plan.reasons_against:
                            st.caption(f"• {r}")
                with p2:
                    score_data = {
                        "Componente": ["Tendência", "Momentum", "Volume", "Liquidez Opção", "Moneyness", "DTE"],
                        "Score": [
                            row.get("trend_score", 0),
                            row.get("momentum_score", 0),
                            row.get("volume_score", 0),
                            row.get("option_liquidity_score", 0),
                            row.get("option_moneyness_score", 0),
                            row.get("option_dte_score", 0),
                        ],
                    }
                    st.dataframe(pd.DataFrame(score_data), hide_index=True)


# ---------------------------------------------------------------------------
# Painel 5 — Diário de Trades
# ---------------------------------------------------------------------------

def _panel_journal() -> None:
    st.title("📓 Diário de Trades")

    journal = _load_journal_from_db()
    if journal.empty:
        journal = _load_journal()

    if journal.empty:
        st.info("Diário vazio. Execute com --journal para registrar setups.")
        st.code("python -m src.strategies.call_continuity_strategy --account 50000 --risk 0.01 --journal")
        return

    # Métricas do diário
    n_total = len(journal)
    ret_col = next((c for c in ["retorno_pct", "return_pct"] if c in journal.columns), None)

    if ret_col:
        completed = journal[journal[ret_col].notna() & (journal[ret_col] != "")]
        wins = completed[completed[ret_col].astype(float) > 0]
        losses = completed[completed[ret_col].astype(float) < 0]
        wr = len(wins) / len(completed) * 100 if len(completed) > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", n_total)
        c2.metric("Concluídos", len(completed))
        c3.metric("Win Rate", f"{wr:.1f}%")
        c4.metric("Aguardando", n_total - len(completed))

    st.divider()
    st.dataframe(journal, use_container_width=True)

    csv_bytes = journal.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar Diário",
        data=csv_bytes,
        file_name=f"journal_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------

def run_streamlit_app() -> None:
    st.set_page_config(
        page_title="Scanner Quant B3",
        page_icon="📊",
        layout="wide",
    )

    sidebar_result = _render_sidebar()
    qcfg, min_vol, min_trades, min_dte, max_dte, top, run_btn, filter_status = sidebar_result

    # Carrega/atualiza setups
    cache_key = f"{min_vol}_{min_trades}_{min_dte}_{max_dte}_{top}"
    if "df_results" not in st.session_state or run_btn:
        with st.spinner("Executando scanner..."):
            df = _load_setups(cache_key, min_vol, min_trades, min_dte, max_dte, top)
        st.session_state["df_results"] = df

    df: pd.DataFrame = st.session_state.get("df_results", pd.DataFrame())

    # Navegação por abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Principal",
        "🛡️ Risco",
        "📈 Performance",
        "🃏 Oportunidades",
        "📓 Diário",
    ])

    with tab1:
        _panel_main(df, filter_status)
    with tab2:
        _panel_risk(df, qcfg)
    with tab3:
        _panel_performance(qcfg)
    with tab4:
        _panel_opportunities(df, filter_status)
    with tab5:
        _panel_journal()

    st.caption("Scanner Quant Profit B3 · Quant Research Layer · Apenas alertas para decisão manual.")


# ---------------------------------------------------------------------------
# Modo headless
# ---------------------------------------------------------------------------

def run_headless() -> None:
    print("Streamlit não instalado — executando em modo headless.\n")
    qcfg = load_quant_config()
    cfg = load_config()
    db_path = project_path(cfg["database_path"])

    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        return

    con = sqlite3.connect(db_path)
    try:
        df = run_strategy(
            con=con, cfg=cfg, qcfg=qcfg,
            account=qcfg.get("capital_inicial", 10_000),
            risk=qcfg.get("risco_por_trade", 0.005),
            min_volume=qcfg.get("min_volume_opcao", 100_000),
            min_trades=qcfg.get("min_negocios_opcao", 10),
            min_dte=qcfg.get("min_dte", 15),
            max_dte=qcfg.get("max_dte", 45),
            top=20,
        )
    finally:
        con.close()

    if df.empty:
        print("Nenhum setup encontrado.")
        return

    cols = ["ticker", "underlying", "status", "final_score", "preco_opcao",
            "strike", "dte", "delta", "contratos", "stop", "alvo_1", "alvo_2"]
    print(df[[c for c in cols if c in df.columns]].to_string(index=False))


def main() -> None:
    if _HAS_STREAMLIT:
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", __file__,
             "--server.headless", "true"],
            check=False,
        )
    else:
        run_headless()


if _HAS_STREAMLIT and __name__ != "__main__":
    run_streamlit_app()
elif __name__ == "__main__":
    main()
