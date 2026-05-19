"""
quant_mesa_dashboard.py
-----------------------
Mesa Quant — Dashboard Institucional (Streamlit).

Execução:
    python -m streamlit run src/reports/quant_mesa_dashboard.py

Não altera modelos, scores, ranking, backtests.
Não executa ordens. Não faz recomendação financeira.
Uso interno de pesquisa e auditoria. CVM IN 598.
"""
from __future__ import annotations

import json
from typing import Optional

import pandas as pd

from src.reports.quant_dashboard_data import (
    get_assets_count,
    get_command_last_runs,
    get_data_health,
    get_diff_summary_text,
    get_editorial_status_summary,
    get_governance_blockers,
    get_integrated_intelligence,
    get_latest_editorial_review,
    get_latest_pipeline_run,
    get_latest_weekly_diff,
    get_material_changes,
    get_options_summary,
    get_paper_trading_summary,
    get_pipeline_run_summary,
    get_pipeline_steps,
    get_recent_tickers,
    get_risk_summary,
    get_scanner_summary,
    get_technical_summary,
    get_weekly_reports_list,
)
from src.reports.ui_components import (
    command_box,
    data_quality_badge,
    dataframe_with_status,
    empty_state,
    executive_summary_box,
    governance_badge,
    metric_card,
    risk_badge,
    section_header,
    status_badge,
    warning_panel,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

_DISCLAIMER = (
    "> **Uso interno — pesquisa e auditoria.**  \n"
    "> Não constitui recomendação de investimento (CVM IN 598).  \n"
    "> Revisão humana obrigatória antes de qualquer distribuição."
)

_SECTIONS = [
    "🏠  Home / Visão Executiva",
    "─── Análise ───",
    "📡  Radar de Ativos",
    "🧠  Inteligência Integrada",
    "📈  Análise Técnica Quant",
    "📊  Opções Inteligentes",
    "⚖️   Risco & Volatilidade",
    "📋  Paper Trading",
    "─── Operacional ───",
    "🗄️   Dados & Auditoria",
    "⚙️   Pipeline Semanal",
    "📰  Relatórios Radar Macro",
    "🏛️   Governança",
    "─── Sistema ───",
    "⌨️   Command Center",
    "🔧  Dados Brutos / Debug",
]

# Sections that are navigation headings (separators)
_SEPARATORS = {s for s in _SECTIONS if s.startswith("───")}


# ===========================================================================
# MAIN APP ENTRY POINT
# ===========================================================================

def render_app() -> None:
    """Entry point do dashboard institucional completo."""
    import streamlit as st

    st.set_page_config(
        page_title="Mesa Quant — Radar Macro",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _render_sidebar(st)


def _render_sidebar(st) -> None:
    import streamlit as st  # noqa (re-import for local use)

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/48/000000/combo-chart.png", width=40)
        st.title("Mesa Quant")
        st.caption("Plataforma Institucional · Radar Macro")
        st.divider()

        # Navigation — filter out separators from selectable options
        selectable = [s for s in _SECTIONS if s not in _SEPARATORS]
        section = st.radio(
            "Navegação",
            _SECTIONS,
            index=0,
            label_visibility="collapsed",
        )

        st.divider()
        st.subheader("Filtros Globais")
        period = st.selectbox(
            "Período",
            ["Último mês", "3 meses", "6 meses", "12 meses", "YTD", "Personalizado"],
        )
        tickers_raw = st.text_input(
            "Tickers (vírgula)",
            "PETR4,VALE3,ITUB4,BBAS3",
            help="Ex: PETR4,VALE3,ITUB4",
        )
        show_blocked_only = st.checkbox("Apenas bloqueados")
        show_data_ok_only = st.checkbox("Apenas com dados suficientes")

        st.divider()
        st.caption("Uso interno — CVM IN 598")

    # Store filters in session_state
    tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
    st.session_state["gf_period"] = period
    st.session_state["gf_tickers"] = tickers
    st.session_state["gf_blocked_only"] = show_blocked_only
    st.session_state["gf_data_ok_only"] = show_data_ok_only

    # Route
    if section in _SEPARATORS:
        st.info("Selecione uma seção no menu lateral.")
        return

    routes = {
        "🏠  Home / Visão Executiva": _render_home,
        "📡  Radar de Ativos": _render_radar_ativos,
        "🧠  Inteligência Integrada": _render_inteligencia,
        "📈  Análise Técnica Quant": _render_tecnica,
        "📊  Opções Inteligentes": _render_opcoes,
        "⚖️   Risco & Volatilidade": _render_risco,
        "📋  Paper Trading": _render_paper_trading,
        "🗄️   Dados & Auditoria": _render_dados_auditoria,
        "⚙️   Pipeline Semanal": _render_pipeline,
        "📰  Relatórios Radar Macro": _render_relatorios,
        "🏛️   Governança": _render_governanca,
        "⌨️   Command Center": _render_command_center,
        "🔧  Dados Brutos / Debug": _render_debug,
    }

    fn = routes.get(section)
    if fn:
        fn(st)
    else:
        st.info("Seção em construção.")


# ===========================================================================
# HOME / VISÃO EXECUTIVA
# ===========================================================================

def _render_home(st) -> None:
    section_header("Home — Visão Executiva", "Panorama operacional da semana")
    st.markdown(_DISCLAIMER)
    st.divider()

    # Load data
    run = get_latest_pipeline_run()
    run_summary = get_pipeline_run_summary(run)
    review = get_latest_editorial_review()
    ed_summary = get_editorial_status_summary(review)
    health = get_data_health()
    assets = get_assets_count()
    blockers = get_governance_blockers()
    tickers = get_recent_tickers(10)
    last_runs = get_command_last_runs()

    # ── Cards principais ──────────────────────────────────────────────
    st.subheader("Status da Plataforma")
    cols = st.columns(4)

    with cols[0]:
        metric_card(
            "Pipeline Semanal",
            run_summary["label"],
            subtitle=run_summary.get("started_at", "") or "Nunca executado",
            status=run_summary["status"],
        )
    with cols[1]:
        metric_card(
            "Status Editorial",
            ed_summary["label"],
            subtitle=ed_summary.get("reviewed_at", "") or "Sem revisão",
            status=ed_summary["status"],
        )
    with cols[2]:
        ok_tables = sum(1 for v in health.values() if v["status"] == "OK")
        total_tables = len(health)
        metric_card(
            "Saúde dos Dados",
            f"{ok_tables}/{total_tables}",
            subtitle="tabelas com dados",
            status="OK" if ok_tables == total_tables else ("WARNING" if ok_tables > 0 else "SEM_DADOS"),
        )
    with cols[3]:
        blockers_count = len(blockers)
        metric_card(
            "Bloqueios de Governança",
            str(blockers_count),
            subtitle="relatórios bloqueados",
            status="BLOCKED" if blockers_count > 0 else "OK",
        )

    st.divider()
    cols2 = st.columns(4)
    with cols2[0]:
        metric_card("Ativos Analisados", str(assets["total"]), status="OK" if assets["total"] > 0 else "SEM_DADOS")
    with cols2[1]:
        metric_card("Ativos com Tese", str(assets["with_hash"]), status="OK" if assets["with_hash"] > 0 else "SEM_DADOS")
    with cols2[2]:
        pt_df = get_paper_trading_summary()
        metric_card("Paper Trading", f"{len(pt_df)} runs", status="OK" if not pt_df.empty else "NOT_RUN")
    with cols2[3]:
        rpts = get_weekly_reports_list(5)
        metric_card("Relatórios Semanais", str(len(rpts)), status="OK" if not rpts.empty else "SEM_DADOS")

    # ── Bloqueios ────────────────────────────────────────────────────
    if not blockers.empty:
        st.divider()
        st.subheader("⛔ Alertas Críticos — Bloqueios de Governança")
        dataframe_with_status(blockers, "status")

    # ── Próxima ação sugerida ─────────────────────────────────────────
    st.divider()
    st.subheader("Próxima Ação Sugerida")
    _render_next_action(st, run_summary, ed_summary, health, blockers)

    # ── Tickers recentes ─────────────────────────────────────────────
    if tickers:
        st.divider()
        st.subheader("Ativos Mais Recentes")
        st.write(", ".join(tickers))

    st.divider()
    st.caption("Mesa Quant — Uso interno. Não constitui recomendação de investimento. CVM IN 598.")


def _render_next_action(st, run_summary, ed_summary, health, blockers) -> None:
    from src.reports.editorial_workflow import EditorialStatus

    # Determine action based on platform state
    if run_summary["status"] == "SEM_DADOS":
        executive_summary_box("Nenhum pipeline executado. Rode o pipeline semanal para iniciar a análise.")
        command_box(
            "python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports",
            description="Rodar Pipeline Semanal",
            when_to_use="Todo início de semana ou quando dados novos estão disponíveis",
        )
    elif ed_summary["status"] == "SEM_REVISAO":
        executive_summary_box("Pipeline executado. Crie a revisão editorial do relatório.")
        command_box(
            "python -m src.scanners.editorial_review --latest-report --create-review --save-db",
            description="Criar Revisão Editorial",
            when_to_use="Após pipeline semanal concluído",
        )
    elif ed_summary["status"] == "PENDING_REVIEW":
        executive_summary_box("Revisão editorial pendente. Aprove ou rejeite o relatório.")
        command_box(
            "python -m src.scanners.editorial_review --latest-report --approve-internal --reviewer SEU_NOME --save-db",
            description="Aprovar para Uso Interno",
        )
    elif not blockers.empty:
        executive_summary_box("Existem bloqueios de governança. Investigue e resolva antes de distribuir.")
        command_box(
            "python -m src.scanners.editorial_review --latest-report --approve-internal --override-data-warning --reviewer SEU_NOME --save-db",
            description="Forçar aprovação (com override de dados)",
            when_to_use="Apenas quando bloqueio for por dados insuficientes e você tiver validado manualmente",
        )
    elif ed_summary["status"] == "APPROVED_FOR_INTERNAL_USE":
        executive_summary_box("Relatório aprovado para uso interno. Considere aprovar para distribuição.")
        command_box(
            "python -m src.scanners.editorial_review --latest-report --approve-distribution --reviewer SEU_NOME --save-db",
            description="Aprovar para Distribuição",
        )
    else:
        executive_summary_box("Plataforma em dia. Rode a auditoria de fontes para verificar saúde dos dados.")
        command_box(
            "python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports",
            description="Rodar Novo Pipeline Semanal",
        )


# ===========================================================================
# RADAR DE ATIVOS
# ===========================================================================

def _render_radar_ativos(st) -> None:
    section_header("Radar de Ativos", "Scanner quantitativo — sinais e oportunidades")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_scanner_summary()
    tickers_filter = st.session_state.get("gf_tickers", [])

    if df.empty:
        empty_state(
            "Nenhum sinal de scanner disponível. Rode o scanner quantitativo.",
            command="python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db",
        )
        return

    if tickers_filter and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers_filter)]

    st.subheader("Sinais Identificados")
    st.metric("Total de sinais", len(df))

    if "status" in df.columns:
        dataframe_with_status(df, "status")
    else:
        st.dataframe(df, use_container_width=True)


# ===========================================================================
# INTELIGÊNCIA INTEGRADA
# ===========================================================================

def _render_inteligencia(st) -> None:
    section_header("Inteligência Integrada", "Visão consolidada por ativo — tese + técnica + macro")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_integrated_intelligence()
    tickers_filter = st.session_state.get("gf_tickers", [])
    blocked_only = st.session_state.get("gf_blocked_only", False)

    if df.empty:
        empty_state(
            "Nenhuma tese integrada encontrada. Rode o pipeline para gerar teses por ativo.",
            command="python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports",
        )
        return

    # Apply filters
    if tickers_filter and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers_filter)]

    # Summary cards
    st.subheader("Cards de Status")
    total = len(df)
    cols = st.columns(3)
    with cols[0]:
        metric_card("Ativos Integrados", str(total), status="OK")
    with cols[1]:
        if "positioning" in df.columns:
            buy = (df["positioning"].str.upper() == "COMPRAR").sum()
            metric_card("Posicionamento COMPRAR", str(buy), status="OK" if buy > 0 else "SEM_DADOS")
    with cols[2]:
        if "confidence" in df.columns:
            high = (df["confidence"].str.upper() == "ALTA").sum()
            metric_card("Confiança ALTA", str(high), status="OK" if high > 0 else "SEM_DADOS")

    st.divider()

    # Tabela integrada
    st.subheader("Tabela Integrada")
    if "positioning" in df.columns:
        dataframe_with_status(df, "positioning")
    else:
        st.dataframe(df, use_container_width=True)

    # Painel por ativo
    st.divider()
    st.subheader("Painel por Ativo")
    if "ticker" in df.columns:
        available_tickers = list(df["ticker"].unique())
        selected = st.selectbox("Selecionar ativo", available_tickers)
        if selected:
            row = df[df["ticker"] == selected].iloc[0]
            st.table(pd.Series(row).to_frame("Valor"))

    st.divider()
    st.caption("Teses geradas pela Intelligence Layer. Não constitui recomendação de investimento. CVM IN 598.")


# ===========================================================================
# ANÁLISE TÉCNICA QUANT
# ===========================================================================

def _render_tecnica(st) -> None:
    section_header("Análise Técnica Quant", "Sinais técnicos quantitativos por ativo")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_technical_summary()
    if df.empty:
        empty_state(
            "Nenhuma análise técnica disponível. Rode o módulo de análise técnica.",
            command="python -m src.scanners.run_weekly_pipeline --save-db",
        )
        return

    tickers_filter = st.session_state.get("gf_tickers", [])
    if tickers_filter and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers_filter)]

    st.metric("Sinais técnicos", len(df))
    if "status" in df.columns:
        dataframe_with_status(df, "status")
    else:
        st.dataframe(df, use_container_width=True)


# ===========================================================================
# OPÇÕES INTELIGENTES
# ===========================================================================

def _render_opcoes(st) -> None:
    section_header("Opções Inteligentes", "Estratégias de opções com base em volatilidade implícita e gregas")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_options_summary()
    if df.empty:
        empty_state(
            "Nenhuma análise de opções disponível. Rode o módulo de opções.",
            command="python -m src.scanners.run_weekly_pipeline --save-db",
        )
        return

    tickers_filter = st.session_state.get("gf_tickers", [])
    if tickers_filter and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers_filter)]

    st.metric("Sinais de opções", len(df))
    st.dataframe(df, use_container_width=True)


# ===========================================================================
# RISCO & VOLATILIDADE
# ===========================================================================

def _render_risco(st) -> None:
    section_header("Risco & Volatilidade", "Risk Engine — métricas de risco por ativo e portfólio")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_risk_summary()
    if df.empty:
        empty_state(
            "Nenhuma métrica de risco disponível. Rode o Risk Engine.",
            command="python -m src.scanners.run_weekly_pipeline --save-db",
        )
        return

    tickers_filter = st.session_state.get("gf_tickers", [])
    if tickers_filter and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers_filter)]

    st.metric("Ativos com métricas de risco", len(df))
    if "status" in df.columns:
        dataframe_with_status(df, "status")
    else:
        st.dataframe(df, use_container_width=True)


# ===========================================================================
# PAPER TRADING
# ===========================================================================

def _render_paper_trading(st) -> None:
    section_header("Paper Trading", "Simulação de estratégias — sem ordens reais")
    st.markdown(_DISCLAIMER)
    st.divider()

    df = get_paper_trading_summary()

    tabs = st.tabs([
        "Resumo", "Runs", "Equity Curve", "Ordens", "Posições",
        "Regras de Saída", "Diagnóstico de Custos", "Fragilidade",
        "Hipóteses", "Deep Dive", "Fronteira Custo-Retorno", "Multi-Cenário",
    ])

    # ── Resumo ────────────────────────────────────────────────────────
    with tabs[0]:
        if df.empty:
            empty_state(
                "Nenhum run de paper trading encontrado. Rode o módulo de paper trading.",
                command="python -m src.scanners.run_weekly_pipeline --save-db",
            )
        else:
            cols = st.columns(3)
            with cols[0]:
                metric_card("Runs Executados", str(len(df)), status="OK")
            if "status" in df.columns:
                succ = (df["status"] == "SUCCESS").sum()
                with cols[1]:
                    metric_card("Runs com Sucesso", str(succ), status="OK" if succ > 0 else "WARNING")
                with cols[2]:
                    fail = (df["status"] == "FAILED").sum()
                    metric_card("Runs com Falha", str(fail), status="FAILED" if fail > 0 else "OK")

    # ── Runs ─────────────────────────────────────────────────────────
    with tabs[1]:
        if df.empty:
            empty_state("Nenhum run disponível.")
        else:
            if "status" in df.columns:
                dataframe_with_status(df, "status")
            else:
                st.dataframe(df, use_container_width=True)

    # Remaining tabs: placeholder if no data
    placeholder_tabs = [
        (tabs[2], "Equity Curve", "Gráfico de evolução do capital ao longo dos runs."),
        (tabs[3], "Ordens", "Histórico de ordens simuladas."),
        (tabs[4], "Posições", "Posições abertas e fechadas."),
        (tabs[5], "Regras de Saída", "Stop loss, take profit e trailing stop configurados."),
        (tabs[6], "Diagnóstico de Custos", "Análise de slippage, corretagem e impacto de custos."),
        (tabs[7], "Fragilidade", "Diagnóstico de fragilidade do portfólio."),
        (tabs[8], "Hipóteses", "Hipóteses testadas e resultados de validação."),
        (tabs[9], "Deep Dive", "Análise aprofundada por ativo ou estratégia."),
        (tabs[10], "Fronteira Custo-Retorno", "Fronteira eficiente custo vs. retorno esperado."),
        (tabs[11], "Validação Multi-Cenário", "Resultados sob diferentes cenários macro."),
    ]

    for tab, title, desc in placeholder_tabs:
        with tab:
            if df.empty:
                empty_state(f"{desc} — Sem dados de paper trading.")
            else:
                st.info(f"ℹ️ {desc} — Implemente visualização específica aqui.")


# ===========================================================================
# DADOS & AUDITORIA
# ===========================================================================

def _render_dados_auditoria(st) -> None:
    section_header("Dados & Auditoria", "Saúde de fontes, reconciliação e observabilidade")
    st.markdown(_DISCLAIMER)
    st.divider()

    tabs = st.tabs([
        "Saúde das Fontes", "Auditoria de Dados", "Reconciliação",
        "Assistente de Ingestão", "SLA / Observabilidade",
        "Retenção / Limpeza", "Alertas",
    ])

    health = get_data_health()

    # ── Saúde das Fontes ──────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Saúde das Tabelas Principais")
        rows = [
            {
                "tabela": t,
                "existe": "Sim" if v["exists"] else "Não",
                "registros": v["rows"],
                "status": v["status"],
            }
            for t, v in health.items()
        ]
        df_health = pd.DataFrame(rows)
        dataframe_with_status(df_health, "status")

        st.divider()
        command_box(
            "python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db",
            description="Popular tabelas via pipeline semanal",
            when_to_use="Quando tabelas estão vazias ou desatualizadas",
        )

    # ── Auditoria de Dados ────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Auditoria de Dados")
        st.caption("Valida consistência entre fontes (CVM, B3, BCB).")
        command_box(
            "python -m src.scanners.run_weekly_pipeline --save-db",
            description="Rodar auditoria de fontes",
            when_to_use="Semanalmente antes de gerar relatório",
        )
        empty_state("Resultado de última auditoria não disponível no banco.")

    # ── Reconciliação ─────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Reconciliação de Dados")
        command_box(
            "python -m src.scanners.compare_weekly_reports --save-db --csv",
            description="Reconciliar relatórios semanais",
            when_to_use="Após gerar dois relatórios consecutivos",
        )
        diff_df = get_latest_weekly_diff()
        if not diff_df.empty:
            st.success(f"Diff disponível: {len(diff_df)} registros")
            st.dataframe(diff_df.head(20), use_container_width=True)
        else:
            empty_state("Nenhum diff semanal disponível.")

    # ── Assistente de Ingestão ────────────────────────────────────────
    with tabs[3]:
        st.subheader("Assistente de Ingestão")
        command_box(
            "python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db",
            description="Ingestão completa via pipeline",
            when_to_use="Para popular o banco com dados históricos",
        )
        empty_state("Status de ingestão: use o pipeline semanal para verificar.")

    # ── SLA / Observabilidade ──────────────────────────────────────────
    with tabs[4]:
        st.subheader("SLA e Observabilidade")
        empty_state(
            "Métricas de SLA não disponíveis. Configure monitoramento de execução.",
            command="python -m src.scanners.generate_weekly_pipeline_report",
        )

    # ── Retenção / Limpeza ────────────────────────────────────────────
    with tabs[5]:
        st.subheader("Retenção e Limpeza de Dados")
        st.info("ℹ️ Defina política de retenção para dados históricos (ex: manter últimos 365 dias).")
        empty_state("Nenhuma política de retenção configurada.")

    # ── Alertas ───────────────────────────────────────────────────────
    with tabs[6]:
        st.subheader("Alertas de Dados")
        blockers = get_governance_blockers()
        if not blockers.empty:
            warning_panel("Bloqueios de Governança Ativos", f"{len(blockers)} relatório(s) bloqueado(s)")
            dataframe_with_status(blockers, "status")
        else:
            st.success("✅ Nenhum alerta crítico de dados.")


# ===========================================================================
# PIPELINE SEMANAL (enhanced version of legacy tab)
# ===========================================================================

def _render_pipeline(st) -> None:
    section_header("Pipeline Semanal", "Status do pipeline Radar Macro end-to-end")
    st.markdown(_DISCLAIMER)
    st.divider()

    run = get_latest_pipeline_run()
    summary = get_pipeline_run_summary(run)

    # Status geral
    st.subheader("Status do Pipeline")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("Status", summary["label"], status=summary["status"])
    with col2:
        metric_card("Etapas OK", str(summary.get("steps_success", "—")), status="OK")
    with col3:
        metric_card("Warnings", str(summary.get("steps_warning", "—")), status="WARNING" if summary.get("steps_warning", 0) else "OK")
    with col4:
        fails = summary.get("steps_failed", 0)
        metric_card("Falhas", str(fails), status="FAILED" if fails else "OK")

    if run is None:
        empty_state(
            "Nenhum pipeline executado ainda.",
            command=summary["command_hint"],
        )
        return

    st.divider()

    # Info básica
    tickers = []
    try:
        tickers = json.loads(run.get("tickers", "[]"))
    except Exception:
        pass

    info = {
        "Run DB ID": run.get("id", "—"),
        "Início": run.get("started_at", "—"),
        "Fim": run.get("finished_at", "—"),
        "Tickers": ", ".join(tickers) if tickers else "—",
        "Relatório": run.get("report_id", "—"),
    }
    st.table(pd.Series(info).to_frame("Valor"))

    # Etapas
    st.subheader("Etapas")
    run_db_id = run.get("id", "")
    steps_df = get_pipeline_steps(run_db_id)

    if not steps_df.empty:
        display_cols = [c for c in ["step_order", "step_name", "status", "started_at", "finished_at"] if c in steps_df.columns]
        if "status" in display_cols:
            dataframe_with_status(steps_df[display_cols], "status")
        else:
            st.dataframe(steps_df[display_cols], use_container_width=True)

        failed_df = steps_df[steps_df["status"] == "FAILED"] if "status" in steps_df.columns else pd.DataFrame()
        if not failed_df.empty:
            st.error(f"{len(failed_df)} etapa(s) com falha")
            with st.expander("Ver falhas"):
                for _, row in failed_df.iterrows():
                    st.markdown(f"**{row.get('step_name', '')}**")
                    if row.get("stderr_summary"):
                        st.code(str(row["stderr_summary"])[:400])
    else:
        empty_state("Nenhuma etapa registrada para este run.")

    # Relatório gerado
    if run.get("report_id"):
        st.success(f"Relatório gerado: `{run['report_id']}`")

    # Comandos sugeridos
    st.divider()
    st.subheader("Comandos Sugeridos")
    cmds = [
        ("python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports",
         "Executar pipeline semanal completo",
         "Todo início de semana"),
        ("python -m src.scanners.editorial_review --latest-report --create-review --save-db",
         "Criar revisão editorial",
         "Após pipeline concluído"),
        ("python -m src.scanners.compare_weekly_reports --save-db --csv",
         "Comparação semanal",
         "Após dois relatórios gerados"),
        ("python -m src.scanners.generate_weekly_pipeline_report",
         "Gerar relatório do pipeline",
         "Para diagnóstico"),
    ]
    for cmd, desc, when in cmds:
        command_box(cmd, description=desc, when_to_use=when)
        st.write("")

    st.caption("Pipeline em modo seguro. Nenhuma ordem real. CVM IN 598.")


# ===========================================================================
# RELATÓRIOS RADAR MACRO (enhanced version of legacy tab)
# ===========================================================================

def _render_relatorios(st) -> None:
    section_header("Relatórios Radar Macro", "Revisão editorial e distribuição")
    st.markdown(_DISCLAIMER)
    st.divider()

    tabs = st.tabs([
        "Relatórios Semanais", "Revisão Editorial",
        "Diff Semanal", "Relatórios por Ativo",
        "Relatórios de Auditoria",
    ])

    # ── Relatórios Semanais ───────────────────────────────────────────
    with tabs[0]:
        st.subheader("Relatórios Semanais Disponíveis")
        rpts = get_weekly_reports_list(30)
        if rpts.empty:
            empty_state("Nenhum relatório semanal encontrado no diretório de output.")
        else:
            st.dataframe(rpts, use_container_width=True)

    # ── Revisão Editorial (legacy render, enhanced) ────────────────────
    with tabs[1]:
        render_radar_macro_tab()

    # ── Diff Semanal ─────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Diferenças Semanais")
        review = get_latest_editorial_review()
        diff_df = get_latest_weekly_diff(report_id=review.report_id if review else None)
        if diff_df.empty:
            empty_state(
                "Nenhum diff semanal disponível.",
                command="python -m src.scanners.compare_weekly_reports --save-db --csv",
            )
        else:
            summary_text = get_diff_summary_text(diff_df)
            executive_summary_box(summary_text)
            material_df = get_material_changes(diff_df)
            if not material_df.empty:
                st.subheader("Mudanças Materiais")
                display_cols = [c for c in ["label", "previous_value", "current_value", "delta", "explanation"] if c in material_df.columns]
                st.dataframe(material_df[display_cols], use_container_width=True)
            with st.expander("Ver diff completo"):
                display_cols = [c for c in ["label", "previous_value", "current_value", "delta", "material_change"] if c in diff_df.columns]
                st.dataframe(diff_df[display_cols], use_container_width=True)

    # ── Relatórios por Ativo ─────────────────────────────────────────
    with tabs[3]:
        empty_state(
            "Relatórios individuais por ativo não disponíveis. Gere via Intelligence Layer.",
            command="python -m src.scanners.run_weekly_pipeline --save-db --reports",
        )

    # ── Relatórios de Auditoria ───────────────────────────────────────
    with tabs[4]:
        empty_state(
            "Relatórios de auditoria não disponíveis.",
            command="python -m src.scanners.generate_editorial_review_report",
        )


# ===========================================================================
# GOVERNANÇA
# ===========================================================================

def _render_governanca(st) -> None:
    section_header("Governança", "Status de aprovação e conformidade dos relatórios")
    st.markdown(_DISCLAIMER)
    st.divider()

    review = get_latest_editorial_review()
    ed_summary = get_editorial_status_summary(review)
    blockers = get_governance_blockers()

    # Status atual
    st.subheader("Status de Governança")
    cols = st.columns(3)
    with cols[0]:
        metric_card("Status Editorial", ed_summary["label"], status=ed_summary["status"])
    with cols[1]:
        metric_card("Nível de Aprovação", ed_summary.get("approval_level") or "—", status="OK" if ed_summary.get("approval_level") else "SEM_DADOS")
    with cols[2]:
        metric_card("Revisor", ed_summary.get("reviewer") or "—")

    # Bloqueios
    st.divider()
    st.subheader("Bloqueios Ativos")
    if blockers.empty:
        st.success("✅ Nenhum bloqueio de governança ativo.")
    else:
        warning_panel("Bloqueios de Governança", f"{len(blockers)} relatório(s) com bloqueio")
        dataframe_with_status(blockers, "status")

    # Fluxo de aprovação
    st.divider()
    st.subheader("Fluxo de Aprovação")
    st.markdown("""
    ```
    DRAFT → PENDING_REVIEW → APPROVED_FOR_INTERNAL_USE → APPROVED_FOR_DISTRIBUTION
                ↓                          ↓
        BLOCKED_DATA_QUALITY      BLOCKED_GOVERNANCE
                ↓
          REJECTED / ARCHIVED
    ```
    """)

    # Comandos de governança
    st.divider()
    st.subheader("Comandos de Governança")
    _render_suggested_commands_streamlit(st, review, get_latest_weekly_diff(
        report_id=review.report_id if review else None
    ))

    st.caption("Governança editorial — CVM IN 598. Revisão humana obrigatória.")


# ===========================================================================
# COMMAND CENTER
# ===========================================================================

def _render_command_center(st) -> None:
    section_header("Command Center", "Referência operacional — todos os comandos da plataforma")
    st.markdown(_DISCLAIMER)
    st.divider()

    last_runs = get_command_last_runs()

    commands = [
        {
            "categoria": "Pipeline & Ingestão",
            "nome": "Pipeline Semanal Completo",
            "descricao": "Executa todas as etapas: ingestão, valuation, inteligência, relatório.",
            "quando": "Todo início de semana ou quando dados novos estão disponíveis.",
            "comando": "python -m src.scanners.run_weekly_pipeline --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports",
            "ultimo_run": last_runs.get("weekly_pipeline", "NOT_RUN"),
        },
        {
            "categoria": "Pipeline & Ingestão",
            "nome": "Auditoria de Fontes",
            "descricao": "Verifica saúde das fontes de dados (CVM, B3, BCB).",
            "quando": "Antes de gerar o relatório semanal.",
            "comando": "python -m src.scanners.run_weekly_pipeline --save-db",
            "ultimo_run": "—",
        },
        {
            "categoria": "Editorial",
            "nome": "Criar Revisão Editorial",
            "descricao": "Cria registro de revisão editorial para o relatório mais recente.",
            "quando": "Após pipeline semanal concluído.",
            "comando": "python -m src.scanners.editorial_review --latest-report --create-review --save-db",
            "ultimo_run": last_runs.get("editorial_review", "NOT_RUN"),
        },
        {
            "categoria": "Editorial",
            "nome": "Aprovar para Uso Interno",
            "descricao": "Aprova relatório para uso interno da equipe.",
            "quando": "Após checklist de revisão preenchido.",
            "comando": "python -m src.scanners.editorial_review --latest-report --approve-internal --reviewer SEU_NOME --save-db",
            "ultimo_run": "—",
        },
        {
            "categoria": "Editorial",
            "nome": "Aprovar para Distribuição",
            "descricao": "Aprova relatório para distribuição externa.",
            "quando": "Após aprovação interna e validação final.",
            "comando": "python -m src.scanners.editorial_review --latest-report --approve-distribution --reviewer SEU_NOME --save-db",
            "ultimo_run": "—",
        },
        {
            "categoria": "Relatórios",
            "nome": "Gerar Relatório Radar Macro",
            "descricao": "Gera o relatório semanal Radar Macro em Markdown.",
            "quando": "Após pipeline concluído.",
            "comando": "python -m src.scanners.generate_weekly_pipeline_report",
            "ultimo_run": "—",
        },
        {
            "categoria": "Relatórios",
            "nome": "Comparação Semanal (Diff)",
            "descricao": "Compara relatório atual com o da semana anterior.",
            "quando": "Após dois relatórios consecutivos gerados.",
            "comando": "python -m src.scanners.compare_weekly_reports --save-db --csv",
            "ultimo_run": "—",
        },
        {
            "categoria": "Relatórios",
            "nome": "Gerar Relatório Editorial",
            "descricao": "Gera relatório do processo de revisão editorial.",
            "quando": "Para auditoria e rastreabilidade.",
            "comando": "python -m src.scanners.generate_editorial_review_report",
            "ultimo_run": "—",
        },
        {
            "categoria": "Risk Engine",
            "nome": "Rodar Risk Engine",
            "descricao": "Calcula métricas de risco por ativo (VaR, CVaR, volatilidade).",
            "quando": "Semanalmente ou após mudanças significativas de mercado.",
            "comando": "python -m src.analysis.risk_engine --tickers PETR4 VALE3 ITUB4 --save-db",
            "ultimo_run": "—",
        },
        {
            "categoria": "Paper Trading",
            "nome": "Rodar Paper Trading",
            "descricao": "Executa simulação de estratégias sem ordens reais.",
            "quando": "Para validar novas estratégias antes de considerar implementação.",
            "comando": "python -m src.scanners.run_weekly_pipeline --save-db",
            "ultimo_run": "—",
        },
        {
            "categoria": "Dashboard",
            "nome": "Iniciar Dashboard Institucional",
            "descricao": "Abre a Mesa Quant no navegador.",
            "quando": "Para monitoramento e análise visual.",
            "comando": "python -m streamlit run src/reports/quant_mesa_dashboard.py",
            "ultimo_run": "—",
        },
    ]

    # Group by categoria
    categorias = {}
    for c in commands:
        cat = c["categoria"]
        categorias.setdefault(cat, []).append(c)

    for cat, items in categorias.items():
        with st.expander(f"📂 {cat}", expanded=True):
            for item in items:
                st.markdown(f"**{item['nome']}**")
                st.caption(item["descricao"])
                st.caption(f"Quando usar: {item['quando']}")
                st.code(item["comando"], language="bash")
                ultimo = item["ultimo_run"]
                if ultimo == "NOT_RUN":
                    st.markdown(data_quality_badge("NOT_RUN"), unsafe_allow_html=True)
                else:
                    st.caption(f"Último run: {ultimo}")
                st.divider()

    st.caption("Command Center — Mesa Quant. Uso interno. CVM IN 598.")


# ===========================================================================
# DADOS BRUTOS / DEBUG
# ===========================================================================

def _render_debug(st) -> None:
    section_header("Dados Brutos / Debug", "Acesso direto a tabelas e diagnóstico do banco")
    st.markdown(_DISCLAIMER)
    st.divider()

    health = get_data_health()
    rows = [
        {
            "tabela": t,
            "existe": "✅" if v["exists"] else "❌",
            "registros": v["rows"],
            "status": v["status"],
        }
        for t, v in health.items()
    ]
    df = pd.DataFrame(rows)
    dataframe_with_status(df, "status")

    st.divider()
    st.subheader("Query Manual")
    st.caption("⚠️ Apenas para debug interno. Leitura apenas.")
    table_names = [t for t, v in health.items() if v["exists"]]

    if table_names:
        table = st.selectbox("Tabela", table_names)
        limit = st.slider("Limite de linhas", 5, 100, 20)
        if st.button("Consultar"):
            from src.reports.quant_dashboard_data import _query
            df_result = _query(f"SELECT * FROM {table}", limit=limit)  # noqa
            if df_result.empty:
                empty_state("Nenhum dado nesta tabela.")
            else:
                st.dataframe(df_result, use_container_width=True)
    else:
        empty_state("Nenhuma tabela disponível no banco.")


# ===========================================================================
# BACKWARD-COMPATIBLE LEGACY RENDER FUNCTIONS
# ===========================================================================

def render_radar_macro_tab(report_id: Optional[str] = None) -> None:
    """Renderiza a aba Relatório Radar Macro na Mesa Quant (Streamlit).
    Mantida para compatibilidade com código existente.
    """
    try:
        import streamlit as st
        _render_streamlit(st, report_id)
    except ImportError:
        _render_console(report_id)


def _render_streamlit(st, report_id: Optional[str]) -> None:
    st.markdown("## Relatório Radar Macro — Revisão Editorial")
    st.markdown(_DISCLAIMER)
    st.divider()

    review = get_latest_editorial_review(report_id)
    summary = get_editorial_status_summary(review)
    diff_df = get_latest_weekly_diff(report_id=review.report_id if review else None)
    material_df = get_material_changes(diff_df)

    st.subheader("Status Editorial")
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", summary["label"])
    col2.metric("Aprovação", summary.get("approval_level", "—") or "—")
    col3.metric("Revisor", summary.get("reviewer", "—") or "—")

    if summary.get("comments"):
        st.info(f"Notas: {summary['comments']}")

    if review is None:
        empty_state("Nenhuma revisão editorial encontrada.", command=summary["command_hint"])
        st.stop()

    st.subheader("Checklist de Revisão Humana")
    if review.checklist_json:
        try:
            data = json.loads(review.checklist_json)
            if isinstance(data, list):
                rows = []
                for item in data:
                    resp = "✅ Sim" if item.get("response") is True else ("❌ Não" if item.get("response") is False else "⏳ Pendente")
                    rows.append({
                        "ID": item.get("item_id", ""),
                        "Pergunta": item.get("question", ""),
                        "Resposta": resp,
                        "Bloqueante": "Sim" if item.get("is_blocking") else "Não",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            elif isinstance(data, dict):
                st.json(data)
        except Exception:
            st.code(review.checklist_json)
    else:
        st.warning("Checklist não preenchido.")

    st.subheader("Histórico de Aprovação")
    approval_data = {
        "Relatório ID": review.report_id,
        "Data do Relatório": review.report_date,
        "Status": review.status.value,
        "Nível de Aprovação": review.approval_level,
        "Revisor": review.reviewer or "—",
        "Revisado em": review.reviewed_at or "—",
        "Criado em": review.created_at,
    }
    st.table(pd.DataFrame([approval_data]).T.rename(columns={0: "Valor"}))

    st.subheader("Diferenças Semanais")
    if diff_df.empty:
        empty_state(
            "Nenhum diff semanal disponível.",
            command="python -m src.scanners.compare_weekly_reports --save-db --csv",
        )
    else:
        summary_text = get_diff_summary_text(diff_df)
        executive_summary_box(summary_text)
        if not material_df.empty:
            st.markdown("**Mudanças Materiais:**")
            display_cols = [c for c in ["label", "previous_value", "current_value", "delta", "explanation"] if c in material_df.columns]
            st.dataframe(material_df[display_cols], use_container_width=True)
        with st.expander("Ver diff completo"):
            display_cols = [c for c in ["label", "previous_value", "current_value", "delta", "material_change"] if c in diff_df.columns]
            st.dataframe(diff_df[display_cols], use_container_width=True)

    st.subheader("Comandos Sugeridos")
    _render_suggested_commands_streamlit(st, review, diff_df)

    st.divider()
    st.caption("Uso interno. Não constitui recomendação de investimento. CVM IN 598.")


def _render_suggested_commands_streamlit(st, review, diff_df) -> None:
    if review is None:
        command_box(
            "python -m src.scanners.editorial_review --latest-report --create-review --save-db",
            description="Criar revisão editorial",
        )
        return

    from src.reports.editorial_workflow import EditorialStatus
    cmds = []

    if review.status == EditorialStatus.PENDING_REVIEW:
        cmds.append(("Aprovar para uso interno", "python -m src.scanners.editorial_review --latest-report --approve-internal --reviewer SEU_NOME --save-db"))
    elif review.status == EditorialStatus.APPROVED_FOR_INTERNAL_USE:
        cmds.append(("Aprovar para distribuição", "python -m src.scanners.editorial_review --latest-report --approve-distribution --reviewer SEU_NOME --save-db"))
    elif review.status in (EditorialStatus.BLOCKED_DATA_QUALITY, EditorialStatus.BLOCKED_GOVERNANCE):
        cmds.append(("Forçar aprovação interna (com override)", "python -m src.scanners.editorial_review --latest-report --approve-internal --override-data-warning --reviewer SEU_NOME --save-db"))

    if diff_df.empty:
        cmds.append(("Comparar relatórios semanais", "python -m src.scanners.compare_weekly_reports --save-db --csv"))

    cmds.append(("Gerar relatório editorial", "python -m src.scanners.generate_editorial_review_report"))

    for label, cmd in cmds:
        command_box(cmd, description=label)
        st.write("")


def _render_console(report_id: Optional[str]) -> None:
    print()
    print("=" * 70)
    print("  MESA QUANT — RELATÓRIO RADAR MACRO (REVISÃO EDITORIAL)")
    print("=" * 70)
    print()
    review = get_latest_editorial_review(report_id)
    summary = get_editorial_status_summary(review)
    print(f"  Status Editorial : {summary['label']}")
    if review:
        print(f"  Relatório ID     : {review.report_id}")
        print(f"  Aprovação        : {review.approval_level}")
        print(f"  Revisor          : {review.reviewer or '—'}")
        if review.comments:
            print(f"  Notas            : {review.comments}")
    else:
        print()
        print(f"  [!] {summary['command_hint']}")
    diff_df = get_latest_weekly_diff(report_id=review.report_id if review else None)
    if not diff_df.empty:
        print(f"  DIFF SEMANAL: {get_diff_summary_text(diff_df)}")
    else:
        print("  [!] Sem diff semanal.")
    print("=" * 70)


def render_pipeline_tab(run_db_id: Optional[str] = None) -> None:
    """Renderiza a aba Pipeline Semanal na Mesa Quant (Streamlit).
    Mantida para compatibilidade com código existente.
    """
    try:
        import streamlit as st
        _render_pipeline_streamlit(st, run_db_id)
    except ImportError:
        _render_pipeline_console(run_db_id)


def _render_pipeline_streamlit(st, run_db_id: Optional[str]) -> None:
    _render_pipeline(st)


def _render_pipeline_console(run_db_id: Optional[str]) -> None:
    run = get_latest_pipeline_run()
    summary = get_pipeline_run_summary(run)
    print()
    print("=" * 70)
    print("  MESA QUANT — PIPELINE SEMANAL RADAR MACRO")
    print("=" * 70)
    print(f"  Status : {summary['label']}")
    if run:
        print(f"  Run ID : {run.get('id', '—')}")
        print(f"  Início : {run.get('started_at', '—')}")
        print(f"  Fim    : {run.get('finished_at', '—')}")
    else:
        print(f"  [!] {summary['command_hint']}")
    print("=" * 70)


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    render_app()
