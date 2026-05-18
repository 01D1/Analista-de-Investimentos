"""Mesa Quant em Streamlit para backtest, calibracao e diagnostico."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
except ImportError:  # pragma: no cover - ambiente sem Streamlit
    st = None

from src.reports.quant_dashboard_data import (
    load_asset_intelligence_diffs_for_dashboard,
    load_asset_intelligence_snapshots_for_dashboard,
    load_capacity_summary_for_dashboard,
    load_backtest_results,
    load_backtest_runs,
    load_calibration_assets_for_dashboard,
    load_calibration_runs_for_dashboard,
    load_component_summary_for_dashboard,
    load_daily_routine_runs_for_dashboard,
    load_data_source_audit_results_for_dashboard,
    load_data_source_audit_runs_for_dashboard,
    load_data_source_traceability_for_dashboard,
    load_data_file_manifest_for_dashboard,
    load_data_file_manifest_runs_for_dashboard,
    load_data_reconciliation_results_for_dashboard,
    load_data_reconciliation_runs_for_dashboard,
    load_ingestion_assistant_runs_for_dashboard,
    load_ingestion_assistant_steps_for_dashboard,
    load_ingestion_comparison_for_dashboard,
    load_post_ingestion_validation_for_dashboard,
    load_execution_quality_summary_for_dashboard,
    load_filter_walk_forward_results_for_dashboard,
    load_filter_walk_forward_runs_for_dashboard,
    load_event_context_runs_for_dashboard,
    load_event_context_summary_for_dashboard,
    load_event_coverage_by_regime_for_dashboard,
    load_event_coverage_runs_for_dashboard,
    load_governance_reviews_for_dashboard,
    load_governance_summary_for_dashboard,
    load_latest_backtest_run,
    load_market_events_for_dashboard,
    load_net_summary_for_dashboard,
    load_observability_snapshots_for_dashboard,
    load_option_scanner_runs_for_dashboard,
    load_option_context_summary_for_dashboard,
    load_option_structure_backtest_results_for_dashboard,
    load_option_structure_backtest_runs_for_dashboard,
    load_option_structure_candidates_for_dashboard,
    load_option_walk_forward_results_for_dashboard,
    load_option_walk_forward_runs_for_dashboard,
    load_options_chain_snapshots_for_dashboard,
    load_quality_filter_runs_for_dashboard,
    load_market_regimes_for_dashboard,
    load_regime_backtest_summary_for_dashboard,
    load_retention_cleanup_details_for_dashboard,
    load_retention_cleanup_runs_for_dashboard,
    load_risk_snapshots_for_dashboard,
    load_signal_event_links_for_dashboard,
    load_score_bucket_summary_for_dashboard,
    load_score_distribution_history_for_dashboard,
    load_signal_summary_for_dashboard,
    load_source_health_checks_for_dashboard,
    load_source_sla_snapshots_for_dashboard,
    load_technical_backtest_results_for_dashboard,
    load_technical_backtest_runs_for_dashboard,
    load_technical_dedup_runs_for_dashboard,
    load_technical_features_for_dashboard,
    load_technical_setups_for_dashboard,
    load_technical_threshold_runs_for_dashboard,
    load_technical_walk_forward_results_for_dashboard,
    load_technical_walk_forward_runs_for_dashboard,
    load_volatility_estimates_for_dashboard,
    load_position_sizing_for_dashboard,
    load_paper_equity_curve_for_dashboard,
    load_paper_cost_sensitivity_for_dashboard,
    load_paper_drawdown_periods_for_dashboard,
    load_paper_exit_optimization_results_for_dashboard,
    load_paper_exit_optimization_runs_for_dashboard,
    load_paper_exit_events_for_dashboard,
    load_paper_fragility_by_asset_for_dashboard,
    load_paper_fragility_by_signal_source_for_dashboard,
    load_paper_fragility_runs_for_dashboard,
    load_paper_hypothesis_block_reasons_for_dashboard,
    load_paper_hypothesis_deep_oos_results_for_dashboard,
    load_paper_hypothesis_deep_oos_runs_for_dashboard,
    load_paper_hypothesis_oos_coverage_for_dashboard,
    load_paper_hypothesis_ranking_results_for_dashboard,
    load_paper_hypothesis_ranking_runs_for_dashboard,
    load_paper_hypothesis_oos_results_for_dashboard,
    load_paper_hypothesis_oos_runs_for_dashboard,
    load_signal_coverage_by_source_for_dashboard,
    load_signal_coverage_runs_for_dashboard,
    load_paper_investigation_results_for_dashboard,
    load_paper_investigation_runs_for_dashboard,
    load_paper_orders_for_dashboard,
    load_paper_pnl_attribution_for_dashboard,
    load_paper_positions_for_dashboard,
    load_paper_rebalance_events_for_dashboard,
    load_paper_scenario_validation_results_for_dashboard,
    load_paper_scenario_validation_runs_for_dashboard,
    load_paper_signal_source_comparison_for_dashboard,
    load_paper_simulation_comparisons_for_dashboard,
    load_paper_simulation_runs_for_dashboard,
    load_paper_walk_forward_results_for_dashboard,
    load_paper_walk_forward_runs_for_dashboard,
    load_stress_tests_for_dashboard,
    load_operational_alerts_for_dashboard,
    load_threshold_optimization_runs_for_dashboard,
    load_walk_forward_results_for_dashboard,
    load_walk_forward_runs_for_dashboard,
)
from src.context.coverage_trends import calculate_event_coverage_trend, calculate_regime_coverage_trend
from src.context.routine_observability import summarize_daily_routine_runs
from src.context.source_quality_contracts import evaluate_source_contracts, load_source_quality_contracts
from src.context.source_sla import calculate_source_sla
from src.notifications.alert_analytics import detect_recurring_alerts
from src.utils import load_config, project_path


def _metric_value(value, suffix: str = "", decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, (int, float)):
        return f"{float(value):.{decimals}f}{suffix}"
    return str(value)


def _csv_download(label: str, df: pd.DataFrame, filename: str) -> None:
    if df.empty:
        return
    st.download_button(
        label,
        data=df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def _best_value(df: pd.DataFrame, group_col: str, metric_col: str) -> str:
    if df.empty or group_col not in df.columns or metric_col not in df.columns:
        return "-"
    work = df.dropna(subset=[metric_col])
    if work.empty:
        return "-"
    return str(work.sort_values(metric_col, ascending=False).iloc[0][group_col])


def _overview_text(latest_run: pd.DataFrame, signal_summary: pd.DataFrame, bucket_summary: pd.DataFrame, calibration_runs: pd.DataFrame) -> str:
    if latest_run.empty:
        return "Ainda não há backtest histórico salvo. Rode o comando histórico com --save-db para alimentar a Mesa Quant."

    run = latest_run.iloc[0]
    signals = int(run.get("signals_count") or 0)
    tickers = int(run.get("tickers_count") or 0)
    best_signal = _best_value(signal_summary, "signal_type", "mean_return_10d")
    best_bucket = _best_value(bucket_summary, "score_bucket", "mean_return_10d")
    inflation = False
    if calibration_runs is not None and not calibration_runs.empty:
        inflation = bool(pd.to_numeric(calibration_runs.iloc[0].get("inflation_alert"), errors="coerce") or 0)
    inflation_text = "há alerta recente de inflação de score" if inflation else "não há alerta recente de inflação de score"
    return (
        f"O último backtest analisou {signals:,}".replace(",", ".")
        + f" sinais em {tickers} ativos. O melhor tipo de sinal em D+10 foi {best_signal}. "
        + f"A faixa de score {best_bucket} teve melhor desempenho, e {inflation_text}. "
        + "Use essa leitura como diagnóstico estatístico, não como recomendação operacional."
    )


def _diagnose_calibration(calibration_runs: pd.DataFrame, calibration_assets: pd.DataFrame) -> str:
    if calibration_runs.empty:
        return "Amostra insuficiente: nenhuma rodada de calibração foi encontrada."
    latest = calibration_runs.iloc[0]
    total = float(latest.get("total_assets") or 0)
    high = float(latest.get("count_80_100") or 0)
    inflation = bool(pd.to_numeric(latest.get("inflation_alert"), errors="coerce") or 0)
    if total <= 0:
        return "Amostra insuficiente: a última rodada não possui ativos."
    high_ratio = high / total
    if inflation or high_ratio > 0.4:
        return "Score possivelmente inflado: muitos ativos ficaram na faixa 80_100."
    if not calibration_assets.empty and "divergence_type" in calibration_assets.columns:
        dominant = calibration_assets["divergence_type"].value_counts(normalize=True).iloc[0]
        if dominant > 0.7:
            return "Score concentrado: um tipo de divergência domina a amostra recente."
    return "Score equilibrado na última calibração disponível, sujeito ao tamanho da amostra."


def _component_correlations(backtest_results: pd.DataFrame, calibration_assets: pd.DataFrame) -> pd.DataFrame:
    components = ["score_momentum", "score_tendencia", "score_liquidez", "score_volatilidade", "score_risco"]
    rows = []
    source = backtest_results
    for component in components:
        if component not in source.columns:
            continue
        for ret_col in ["future_return_3d", "future_return_5d", "future_return_10d"]:
            if ret_col not in source.columns:
                continue
            corr = pd.to_numeric(source[component], errors="coerce").corr(pd.to_numeric(source[ret_col], errors="coerce"))
            rows.append({"component": component, "metric": ret_col, "correlation": round(float(corr), 4) if pd.notna(corr) else 0.0})
    if rows:
        return pd.DataFrame(rows)

    # O schema persistido atual não guarda componentes no backtest; usa calibração como diagnóstico descritivo.
    if calibration_assets.empty:
        return pd.DataFrame(columns=["component", "metric", "correlation"])
    for component in components:
        if component in calibration_assets.columns:
            values = pd.to_numeric(calibration_assets[component], errors="coerce")
            scores = pd.to_numeric(calibration_assets.get("score_final"), errors="coerce")
            corr = values.corr(scores)
            rows.append({"component": component, "metric": "score_final", "correlation": round(float(corr), 4) if pd.notna(corr) else 0.0})
    return pd.DataFrame(rows)


def _render_header() -> None:
    st.set_page_config(page_title="Radar Macro - Mesa Quant", layout="wide", initial_sidebar_state="collapsed")
    st.title("Radar Macro — Mesa Quant")
    st.caption("Backtest, calibração, sinais quantitativos e performance histórica")
    st.info("Ferramenta de análise estatística. Não altera o score legado, não muda ranking e não constitui recomendação financeira.")


def _tab_overview(latest_run, signal_summary, bucket_summary, calibration_runs, backtest_results, net_summary) -> None:
    if latest_run.empty:
        st.warning("Nenhum backtest histórico salvo encontrado.")
        st.code("python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db")
        return

    run = latest_run.iloc[0]
    best_signal = _best_value(signal_summary, "signal_type", "mean_return_10d")
    best_bucket = _best_value(bucket_summary, "score_bucket", "mean_return_10d")
    inflation = bool(pd.to_numeric(calibration_runs.iloc[0].get("inflation_alert"), errors="coerce") or 0) if not calibration_runs.empty else False

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de sinais", int(run.get("signals_count") or 0))
    c2.metric("Último run_id", int(run.get("id") or 0))
    c3.metric("Ativos", int(run.get("tickers_count") or 0))
    c4.metric("Inflação de score", "Sim" if inflation else "Não")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Melhor sinal", best_signal)
    c6.metric("Melhor faixa", best_bucket)
    c7.metric("Hit rate D+5", _metric_value(run.get("hit_rate_5d"), decimals=2))
    c8.metric("Retorno médio D+10", _metric_value(run.get("mean_return_10d"), "%"))

    if not net_summary.empty:
        net = net_summary.iloc[0]
        c9, c10, c11, c12 = st.columns(4)
        c9.metric("Retorno bruto D+5", _metric_value(net.get("gross_mean_return_5d"), "%"))
        c10.metric("Retorno líquido D+5", _metric_value(net.get("net_mean_return_5d"), "%"))
        c11.metric("Impacto custos D+5", _metric_value(net.get("cost_impact_5d"), " p.p."))
        c12.metric("Sinais inviáveis", int(net.get("untradeable_signals") or 0))

    st.subheader("Diagnóstico automático")
    st.write(_overview_text(latest_run, signal_summary, bucket_summary, calibration_runs))

    if not backtest_results.empty:
        st.subheader("Amostra recente")
        st.dataframe(backtest_results.head(20), use_container_width=True, hide_index=True)


def _tab_backtest(db_path: Path, runs: pd.DataFrame, signal_summary: pd.DataFrame, bucket_summary: pd.DataFrame, quality_summary: pd.DataFrame) -> None:
    st.subheader("Runs históricos")
    if runs.empty:
        st.warning("Nenhum run histórico salvo.")
        return
    st.dataframe(runs, use_container_width=True, hide_index=True)
    run_ids = pd.to_numeric(runs["id"], errors="coerce").dropna().astype(int).tolist()
    selected = st.selectbox("run_id", run_ids, index=0)
    results = load_backtest_results(db_path, run_id=int(selected))
    return_mode = st.radio("Modo de retorno", ["Bruto", "Líquido"], horizontal=True)
    ret_col = "net_return_5d" if return_mode == "Líquido" and "net_return_5d" in results.columns else "future_return_5d"

    st.subheader("Resultados do run selecionado")
    st.dataframe(results, use_container_width=True, hide_index=True)

    if {"future_return_5d", "net_return_5d"}.issubset(results.columns) and pd.to_numeric(results["net_return_5d"], errors="coerce").notna().any():
        st.subheader("Realismo Operacional")
        cols = [c for c in ["future_return_5d", "net_return_5d", "total_cost_pct", "total_slippage_pct", "liquidity_penalty", "is_tradeable"] if c in results.columns]
        st.dataframe(results[cols].describe().reset_index(), use_container_width=True, hide_index=True)
        st.line_chart(results[["future_return_5d", "net_return_5d"]].reset_index(drop=True))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"Retorno médio D+5 por signal_type ({return_mode.lower()})")
        if not results.empty and ret_col in results.columns:
            st.bar_chart(results.groupby("signal_type")[ret_col].mean(numeric_only=True))
    with c2:
        st.markdown(f"Hit rate D+5 por signal_type ({return_mode.lower()})")
        if not results.empty and ret_col in results.columns:
            st.bar_chart((pd.to_numeric(results[ret_col], errors="coerce") > 0).groupby(results["signal_type"]).mean())

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("Retorno médio D+5 por score_bucket")
        if not bucket_summary.empty:
            st.bar_chart(bucket_summary.set_index("score_bucket")["mean_return_5d"])
    with c4:
        st.markdown("Quantidade de sinais por score_bucket")
        if not bucket_summary.empty:
            st.bar_chart(bucket_summary.set_index("score_bucket")["signals"])

    if not quality_summary.empty:
        st.subheader("Resumo por qualidade de execução")
        st.dataframe(quality_summary, use_container_width=True, hide_index=True)

    if not results.empty:
        st.subheader("Ranking dos melhores sinais históricos")
        sort_col = "net_return_10d" if return_mode == "Líquido" and "net_return_10d" in results.columns else "future_return_10d"
        rank_cols = ["trade_date", "ticker", "score_final", "signal_type", "future_return_5d", "net_return_5d", "future_return_10d", "net_return_10d", "execution_quality", "is_tradeable", "mfe_5d", "mae_5d"]
        ranking = results.sort_values(sort_col, ascending=False)[[c for c in rank_cols if c in results.columns]].head(30)
        st.dataframe(ranking, use_container_width=True, hide_index=True)


def _tab_calibration(calibration_runs: pd.DataFrame, calibration_assets: pd.DataFrame, history: pd.DataFrame) -> None:
    if calibration_runs.empty:
        st.warning("Nenhuma calibração salva encontrada.")
        st.code("python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --save-calibration")
        return

    st.subheader("Histórico de rodadas")
    st.dataframe(calibration_runs, use_container_width=True, hide_index=True)

    if not history.empty:
        line_cols = [c for c in ["mean_score_final", "p90_score_final", "count_80_100", "inflation_alert"] if c in history.columns]
        st.subheader("Evolução da distribuição do score")
        st.line_chart(history.set_index("created_at")[line_cols])

    st.subheader("Ativos da calibração mais recente")
    st.dataframe(calibration_assets, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        if not calibration_assets.empty and {"legacy_score", "score_final"}.issubset(calibration_assets.columns):
            st.markdown("Comparação score legado x score_final")
            st.scatter_chart(calibration_assets, x="legacy_score", y="score_final")
    with c2:
        if not calibration_assets.empty and "divergence_type" in calibration_assets.columns:
            st.markdown("Distribuição de divergências")
            st.bar_chart(calibration_assets["divergence_type"].value_counts())

    st.subheader("Diagnóstico de calibração")
    st.write(_diagnose_calibration(calibration_runs, calibration_assets))


def _tab_asset(results: pd.DataFrame) -> None:
    if results.empty or "ticker" not in results.columns:
        st.warning("Sem resultados históricos por ativo.")
        return
    tickers = sorted(results["ticker"].dropna().unique().tolist())
    ticker = st.selectbox("Ticker", tickers)
    asset = results[results["ticker"] == ticker].sort_values("trade_date")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ocorrências", len(asset))
    c2.metric("Hit D+5", _metric_value((pd.to_numeric(asset["future_return_5d"], errors="coerce") > 0).mean(), decimals=2))
    c3.metric("Melhor D+10", _metric_value(pd.to_numeric(asset["future_return_10d"], errors="coerce").max(), "%"))
    c4.metric("Pior D+10", _metric_value(pd.to_numeric(asset["future_return_10d"], errors="coerce").min(), "%"))

    st.subheader("Score_final ao longo do tempo")
    st.line_chart(asset.set_index("trade_date")["score_final"])

    st.subheader("Retornos futuros")
    ret_cols = [c for c in ["future_return_1d", "future_return_3d", "future_return_5d", "future_return_10d"] if c in asset.columns]
    st.line_chart(asset.set_index("trade_date")[ret_cols])

    st.subheader("Média de retorno por tipo de sinal")
    by_signal = asset.groupby("signal_type")[ret_cols].mean(numeric_only=True).reset_index()
    st.dataframe(by_signal, use_container_width=True, hide_index=True)

    st.subheader("Histórico de sinais")
    st.dataframe(asset, use_container_width=True, hide_index=True)


def _tab_components(results: pd.DataFrame, calibration_assets: pd.DataFrame, component_summary: pd.DataFrame) -> None:
    st.subheader("Resumo dos componentes")
    if component_summary.empty:
        st.warning("Sem componentes persistidos para análise. Rode calibrações com --save-calibration.")
    else:
        st.dataframe(component_summary, use_container_width=True, hide_index=True)
        st.bar_chart(component_summary.set_index("component")["mean"])

    if not calibration_assets.empty and "signal_type" in calibration_assets.columns:
        st.subheader("Média dos componentes por signal_type")
        component_cols = [c for c in ["score_momentum", "score_tendencia", "score_liquidez", "score_volatilidade", "score_risco"] if c in calibration_assets.columns]
        means = calibration_assets.groupby("signal_type")[component_cols].mean(numeric_only=True).reset_index()
        st.dataframe(means, use_container_width=True, hide_index=True)

    corr = _component_correlations(results, calibration_assets)
    st.subheader("Relação dos componentes com retornos ou score_final")
    if corr.empty:
        st.info("A base persistida ainda não permite calcular correlação com retornos por componente.")
    else:
        st.dataframe(corr.sort_values("correlation", ascending=False), use_container_width=True, hide_index=True)
        best = corr.sort_values("correlation", ascending=False).iloc[0]
        st.write(
            f"Na amostra atual, {best['component']} apresentou a maior relação com {best['metric']}. "
            "Essa leitura é diagnóstica e depende do histórico persistido."
        )


def _tab_alerts(
    runs: pd.DataFrame,
    results: pd.DataFrame,
    calibration_runs: pd.DataFrame,
    calibration_assets: pd.DataFrame,
    bucket_summary: pd.DataFrame,
    net_summary: pd.DataFrame,
) -> None:
    alerts = []
    strengths = []
    limitations = []

    if results.empty:
        alerts.append("Sem backtest histórico salvo.")
    elif len(results) < 200:
        alerts.append("Amostra pequena para inferência estatística.")
    else:
        strengths.append("Há histórico suficiente para análises exploratórias iniciais.")

    if calibration_runs.empty:
        alerts.append("Sem histórico de calibração salvo.")
    else:
        latest = calibration_runs.iloc[0]
        if bool(pd.to_numeric(latest.get("inflation_alert"), errors="coerce") or 0):
            alerts.append("Score inflado: alerta recente de excesso de ativos acima de 80.")
        else:
            strengths.append("A última calibração não registrou alerta de inflação.")

    if not bucket_summary.empty and "mean_return_5d" in bucket_summary.columns:
        means = pd.to_numeric(bucket_summary["mean_return_5d"], errors="coerce").dropna().tolist()
        if len(means) >= 3 and not all(b >= a for a, b in zip(means, means[1:])):
            alerts.append("Score sem monotonicidade clara: faixas maiores não performaram sempre melhor em D+5.")

    if not calibration_assets.empty and "divergence_type" in calibration_assets.columns:
        divergent = calibration_assets["divergence_type"].astype(str).str.contains("DIVERGENTE|RIGOROSO|AGRESSIVO", regex=True).mean()
        if divergent > 0.4:
            alerts.append("Divergência elevada entre score legado e score_final.")

    if net_summary is not None and not net_summary.empty:
        net = net_summary.iloc[0]
        gross5 = float(net.get("gross_mean_return_5d") or 0)
        net5 = float(net.get("net_mean_return_5d") or 0)
        untradeable = float(net.get("untradeable_signals") or 0)
        total = float(net.get("signals") or 1)
        if gross5 > 0 and net5 <= 0:
            alerts.append("Estratégia perde vantagem após custos no D+5.")
        if untradeable / total > 0.25:
            alerts.append("Muitos sinais classificados como inviáveis por liquidez.")
        if gross5 - net5 > 0.5:
            alerts.append("Diferença grande entre retorno bruto e líquido.")

    limitations.extend(
        [
            "Backtest diário não captura execução intraday.",
            "Custos, slippage e spread são estimativas, não execução real.",
            "O dashboard não altera pesos nem substitui o score legado.",
        ]
    )

    st.subheader("Diagnóstico Quantitativo Atual")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("Pontos fortes")
        st.write("\n".join(f"- {item}" for item in strengths) if strengths else "- Ainda sem pontos fortes estatísticos suficientes.")
    with c2:
        st.markdown("Alertas")
        st.write("\n".join(f"- {item}" for item in alerts) if alerts else "- Nenhum alerta crítico nas bases carregadas.")

    st.markdown("Limitações")
    st.write("\n".join(f"- {item}" for item in limitations))

    st.markdown("Próximos passos")
    st.write(
        "- Rodar mais calibrações em pregões reais.\n"
        "- Persistir backtests por janelas fora da amostra.\n"
        "- Incluir custos e liquidez operacional antes de qualquer decisão de ranking."
    )

    if net_summary is not None and not net_summary.empty:
        st.subheader("Realismo Operacional")
        st.dataframe(net_summary, use_container_width=True, hide_index=True)


def _tab_walk_forward(wf_runs: pd.DataFrame, wf_results: pd.DataFrame) -> None:
    if wf_runs.empty:
        st.warning("Nenhuma análise walk-forward salva encontrada.")
        st.code(
            "python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 "
            "--train-months 12 --test-months 3 --csv --save-db"
        )
        return

    latest = wf_runs.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Janelas", int(latest.get("windows_count") or 0))
    c2.metric("Janelas positivas", _metric_value(latest.get("positive_windows_pct"), "%"))
    c3.metric("Retorno médio teste", _metric_value(latest.get("mean_test_return"), "%"))
    c4.metric("Overfitting", "Sim" if bool(pd.to_numeric(latest.get("overfitting_alert"), errors="coerce") or 0) else "Não")

    st.subheader("Runs walk-forward")
    st.dataframe(wf_runs, use_container_width=True, hide_index=True)

    st.subheader("Janelas")
    st.dataframe(wf_results, use_container_width=True, hide_index=True)

    c5, c6 = st.columns(2)
    with c5:
        if not wf_results.empty and "test_return_best_signal" in wf_results.columns:
            st.markdown("Retorno no teste do melhor sinal do treino")
            st.bar_chart(wf_results.set_index("window_id")["test_return_best_signal"])
    with c6:
        if not wf_results.empty and "test_return_best_bucket" in wf_results.columns:
            st.markdown("Retorno no teste do melhor bucket do treino")
            st.bar_chart(wf_results.set_index("window_id")["test_return_best_bucket"])

    if not wf_results.empty:
        robust_signal = wf_results["best_train_signal_type"].value_counts().idxmax() if "best_train_signal_type" in wf_results else "-"
        robust_bucket = wf_results["best_train_score_bucket"].value_counts().idxmax() if "best_train_score_bucket" in wf_results else "-"
        overfit_rate = pd.to_numeric(wf_results.get("overfitting_flag"), errors="coerce").mean()
        st.subheader("Diagnóstico fora da amostra")
        st.write(
            f"Sinal mais recorrente nas janelas de treino: {robust_signal}. "
            f"Bucket mais recorrente: {robust_bucket}. "
            f"Percentual de janelas com alerta: {overfit_rate:.1%}. "
            "A leitura é estatística e não altera pesos automaticamente."
        )


def _tab_filters_capacity(
    filter_runs: pd.DataFrame,
    threshold_runs: pd.DataFrame,
    capacity_summary: pd.DataFrame,
    results: pd.DataFrame,
    filter_wf_runs: pd.DataFrame,
    filter_wf_results: pd.DataFrame,
) -> None:
    st.subheader("Filtros de qualidade")
    if filter_runs.empty:
        st.warning("Nenhuma rodada de filtros salva encontrada.")
        st.code(
            "python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 "
            "--net --quality-filter --min-score-final 80 --csv --save-db"
        )
    else:
        latest = filter_runs.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sinais antes", int(latest.get("signals_before") or 0))
        c2.metric("Sinais depois", int(latest.get("signals_after") or 0))
        c3.metric("Removidos", _metric_value(latest.get("removed_pct"), "%"))
        c4.metric("Retorno líquido após", _metric_value(latest.get("mean_net_return_after"), "%"))
        st.dataframe(filter_runs, use_container_width=True, hide_index=True)

    st.subheader("Otimização de thresholds")
    if threshold_runs.empty:
        st.info("Nenhuma otimização de thresholds salva. Os thresholds sugeridos não são aplicados automaticamente.")
        st.code(
            "python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 "
            "--net --optimize-thresholds --csv --save-db"
        )
    else:
        st.dataframe(threshold_runs, use_container_width=True, hide_index=True)

    st.subheader("Capacidade por liquidez")
    if capacity_summary.empty:
        st.info("Sem capacidade persistida. Rode um backtest histórico atualizado com --save-db.")
    else:
        st.dataframe(capacity_summary, use_container_width=True, hide_index=True)
        by_class = capacity_summary[capacity_summary["group"] == "capacity_class"]
        if not by_class.empty:
            st.bar_chart(by_class.set_index("value")["mean_capacity"])

    st.subheader("Distribuição de qualidade dos sinais")
    if not results.empty and "signal_quality" in results.columns and results["signal_quality"].notna().any():
        st.bar_chart(results["signal_quality"].value_counts())
    else:
        st.info("A distribuição de signal_quality aparece após rodar o backtest com --quality-filter.")

    st.subheader("Alertas de filtros e capacidade")
    alerts = []
    if not filter_runs.empty:
        latest = filter_runs.iloc[0]
        before = float(latest.get("signals_before") or 0)
        after = float(latest.get("signals_after") or 0)
        before_net = float(latest.get("mean_net_return_before") or 0)
        after_net = float(latest.get("mean_net_return_after") or 0)
        if after < 100 and before >= 100:
            alerts.append("Filtros deixaram a amostra pequena demais.")
        if after_net <= 0:
            alerts.append("Retorno líquido segue negativo após filtros.")
        if after_net > before_net:
            alerts.append("Filtros melhoraram o retorno líquido médio, mas ainda exigem validação fora da amostra.")
    if not capacity_summary.empty:
        cap_classes = capacity_summary[capacity_summary["group"] == "capacity_class"]
        low = cap_classes[cap_classes["value"].isin(["BAIXA_CAPACIDADE", "INVIAVEL"])]["signals"].sum() if not cap_classes.empty else 0
        total = cap_classes["signals"].sum() if not cap_classes.empty else 0
        if total and low / total > 0.25:
            alerts.append("Capacidade operacional baixa em parcela relevante da amostra.")
    st.write("\n".join(f"- {item}" for item in alerts) if alerts else "- Nenhum alerta específico de filtros/capacidade nas bases carregadas.")

    st.subheader("Walk-forward dos Filtros")
    if filter_wf_runs.empty:
        st.info("Nenhuma validação walk-forward dos filtros foi salva.")
        st.code(
            "python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 "
            "--train-months 1 --test-months 1 --csv --save-db"
        )
    else:
        latest = filter_wf_runs.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Janelas positivas", _metric_value(latest.get("positive_windows_pct"), "%"))
        c2.metric("Retorno teste", _metric_value(latest.get("mean_test_net_return"), "%"))
        c3.metric("Hit rate teste", _metric_value(latest.get("mean_test_hit_rate"), decimals=2))
        c4.metric("Robustez", latest.get("robustness_class") or "-")
        c5, c6 = st.columns(2)
        c5.metric("Sinais médios/teste", _metric_value(latest.get("avg_test_signals"), decimals=1))
        c6.metric("Concentração top 3", _metric_value(latest.get("avg_top_3_concentration_pct"), "%"))
        st.dataframe(filter_wf_runs, use_container_width=True, hide_index=True)
        if not filter_wf_results.empty:
            st.markdown("Resultados por janela")
            st.dataframe(filter_wf_results, use_container_width=True, hide_index=True)
            if "test_mean_net_return" in filter_wf_results.columns:
                st.bar_chart(filter_wf_results.set_index("window_id")["test_mean_net_return"])
        wf_alerts = []
        if bool(pd.to_numeric(latest.get("overfitting_alert"), errors="coerce") or 0):
            wf_alerts.append("Overfitting provável nos filtros.")
        if float(latest.get("mean_test_net_return") or 0) <= 0:
            wf_alerts.append("Retorno líquido fora da amostra ficou negativo ou nulo.")
        if float(latest.get("avg_top_3_concentration_pct") or 0) >= 50:
            wf_alerts.append("Concentração excessiva nos 3 principais ativos.")
        st.write("\n".join(f"- {item}" for item in wf_alerts) if wf_alerts else "- Nenhum alerta forte no walk-forward dos filtros salvo.")


def _tab_governance(governance_reviews: pd.DataFrame, governance_summary: pd.DataFrame) -> None:
    st.subheader("Governança Quant")
    if governance_reviews.empty:
        st.warning("Nenhum governance review salvo.")
        st.code("python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db")
        return

    latest = governance_reviews.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", latest.get("governance_status") or "-")
    c2.metric("Aprovado", "SIM" if bool(pd.to_numeric(latest.get("approved"), errors="coerce") or 0) else "NÃO")
    c3.metric("Risco", latest.get("risk_level") or "-")
    c4.metric("Confiança", latest.get("confidence_level") or "-")

    if not governance_summary.empty:
        st.subheader("Contagem por status")
        st.dataframe(governance_summary, use_container_width=True, hide_index=True)
        st.bar_chart(governance_summary.set_index("governance_status")["reviews"])

    st.subheader("Últimos reviews")
    st.dataframe(governance_reviews, use_container_width=True, hide_index=True)

    st.subheader("Leitura institucional")
    st.write(latest.get("summary_text") or "Sem resumo textual salvo.")
    alerts = []
    if not bool(pd.to_numeric(governance_reviews.get("approved"), errors="coerce").fillna(0).any()):
        alerts.append("Nenhum candidato operacional aprovado.")
    statuses = governance_reviews["governance_status"].astype(str).tolist()
    if any("OVERFITTING" in status for status in statuses):
        alerts.append("Há candidato bloqueado por overfitting.")
    if any("AMOSTRA_INSUFICIENTE" in status for status in statuses):
        alerts.append("Há candidato com amostra insuficiente.")
    if any("CONCENTRACAO_EXCESSIVA" in status for status in statuses):
        alerts.append("Há candidato com concentração excessiva.")
    if any("LIQUIDEZ_INSUFICIENTE" in status for status in statuses):
        alerts.append("Há candidato com liquidez insuficiente.")
    st.subheader("Alertas")
    st.write("\n".join(f"- {item}" for item in alerts) if alerts else "- Nenhum alerta de governança nos reviews salvos.")


def _tab_regimes(regimes: pd.DataFrame, regime_summary: pd.DataFrame, governance_reviews: pd.DataFrame) -> None:
    st.subheader("Regimes de Mercado")
    if regimes.empty:
        st.warning("Nenhum regime salvo.")
        st.code("python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv")
        return
    latest = regimes.sort_values("trade_date").iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime atual", latest.get("primary_regime") or "-")
    c2.metric("Tendência", latest.get("trend_regime") or "-")
    c3.metric("Volatilidade", latest.get("volatility_regime") or "-")
    c4.metric("Liquidez", latest.get("liquidity_regime") or "-")
    st.subheader("Distribuição dos regimes")
    st.bar_chart(regimes["primary_regime"].value_counts())
    st.dataframe(regimes, use_container_width=True, hide_index=True)

    st.subheader("Backtest por regime")
    if regime_summary.empty:
        st.info("Sem resumo por regime salvo. Rode historical_quant_backtest com --with-regimes ou regime_analysis após um backtest com regimes.")
        st.code("python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db")
    else:
        st.dataframe(regime_summary, use_container_width=True, hide_index=True)
        primary = regime_summary[regime_summary["regime_type"] == "primary_regime"]
        if not primary.empty:
            st.bar_chart(primary.set_index("regime_value")["mean_net_return_5d"])

    st.subheader("Governança por regime")
    if governance_reviews.empty or "regime_status" not in governance_reviews.columns or governance_reviews["regime_status"].dropna().empty:
        st.info("Sem review de governança por regime salvo.")
    else:
        cols = [c for c in ["created_at", "candidate_name", "governance_status", "regime_status", "allowed_regimes_json", "blocked_regimes_json"] if c in governance_reviews.columns]
        st.dataframe(governance_reviews[cols].head(20), use_container_width=True, hide_index=True)


def _tab_events(events: pd.DataFrame, event_links: pd.DataFrame, event_runs: pd.DataFrame, event_coverage_runs: pd.DataFrame, event_coverage_by_regime: pd.DataFrame, event_summary: pd.DataFrame, results: pd.DataFrame, governance_reviews: pd.DataFrame) -> None:
    st.subheader("Eventos & Notícias")
    if events.empty:
        st.warning("Nenhum evento importado.")
        st.code("python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Eventos importados", len(events))
    c2.metric("Tickers com evento", events["ticker"].replace("", pd.NA).dropna().nunique() if "ticker" in events.columns else 0)
    c3.metric("Links salvos", len(event_links))
    latest_coverage = event_coverage_runs.iloc[0] if not event_coverage_runs.empty else {}
    c4.metric("Cobertura", latest_coverage.get("coverage_quality", "-") if hasattr(latest_coverage, "get") else "-")

    st.subheader("Controle de cobertura")
    if event_coverage_runs.empty:
        st.info("Pipeline de cobertura ainda não foi executado.")
        st.code("python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv")
    else:
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Fontes", latest_coverage.get("sources") or "-")
        c6.metric("Eventos carregados", int(latest_coverage.get("events_loaded") or 0))
        c7.metric("Após dedupe", int(latest_coverage.get("events_after_dedup") or 0))
        c8.metric("Sinais cobertos", _metric_value(float(latest_coverage.get("signals_with_event_pct") or 0) * 100, "%"))
        st.dataframe(event_coverage_runs, use_container_width=True, hide_index=True)
        if str(latest_coverage.get("coverage_quality") or "").upper() in {"COBERTURA_FRACA", "COBERTURA_INSUFICIENTE"}:
            st.warning("Cobertura insuficiente: conclusões evento x sem evento devem permanecer bloqueadas ou em observação.")

    st.subheader("Rotina de Atualização")
    st.code("python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes")

    st.subheader("Cobertura por regime")
    if event_coverage_by_regime.empty:
        st.info("Sem cobertura por regime salva. Rode a rotina diária com --with-regimes depois de gerar market_regime_daily.")
    else:
        st.dataframe(event_coverage_by_regime, use_container_width=True, hide_index=True)
        weak = event_coverage_by_regime[
            event_coverage_by_regime["coverage_quality"].astype(str).str.upper().isin(["COBERTURA_FRACA", "COBERTURA_INSUFICIENTE"])
        ]
        if not weak.empty:
            st.warning("Há regimes com cobertura fraca ou insuficiente; a governança deve bloquear conclusões fortes nesses ambientes.")
        primary = event_coverage_by_regime[event_coverage_by_regime["regime_type"] == "primary_regime"]
        if not primary.empty:
            st.bar_chart(primary.set_index("regime_value")["signals_with_event_pct"])

    st.subheader("Eventos importados")
    st.dataframe(events, use_container_width=True, hide_index=True)

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("Eventos por tipo")
        if "event_type" in events.columns:
            st.bar_chart(events["event_type"].value_counts())
    with c6:
        st.markdown("Eventos por ticker")
        if "ticker" in events.columns:
            by_ticker = events["ticker"].replace("", pd.NA).dropna().value_counts()
            if not by_ticker.empty:
                st.bar_chart(by_ticker)

    st.subheader("Sinais com evento x sem evento")
    if event_summary.empty:
        st.info("Rode o backtest com --with-events ou event_context_analysis para gerar marcações em sinais.")
        st.code("python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db")
    else:
        st.dataframe(event_summary, use_container_width=True, hide_index=True)
        has_event = event_summary[event_summary["group"] == "has_event"]
        if not has_event.empty:
            st.bar_chart(has_event.set_index("value")["mean_net_return_5d"])
            st.bar_chart(has_event.set_index("value")["hit_rate_5d"])

    st.subheader("Top eventos relacionados a sinais")
    if event_links.empty:
        st.info("Nenhum vínculo evento-sinal salvo.")
    else:
        st.dataframe(event_links.head(100), use_container_width=True, hide_index=True)

    st.subheader("Eventos por regime")
    if not event_summary.empty and "primary_regime" in results.columns:
        regime_rows = event_summary[event_summary["group"] == "primary_regime"]
        if not regime_rows.empty:
            st.dataframe(regime_rows, use_container_width=True, hide_index=True)
    else:
        st.info("A análise por regime aparece após rodar backtest com --with-regimes --with-events.")

    st.subheader("Governança por evento")
    if governance_reviews.empty or "event_status" not in governance_reviews.columns or governance_reviews["event_status"].dropna().empty:
        st.info("Sem review de governança com eventos salvo.")
    else:
        cols = [c for c in ["created_at", "candidate_name", "governance_status", "event_status", "allowed_event_contexts_json", "blocked_event_contexts_json"] if c in governance_reviews.columns]
        st.dataframe(governance_reviews[cols].head(20), use_container_width=True, hide_index=True)


def _tab_options_intelligence(option_runs: pd.DataFrame, option_chain: pd.DataFrame, option_structures: pd.DataFrame, option_backtest_runs: pd.DataFrame, option_backtest_results: pd.DataFrame, option_wf_runs: pd.DataFrame, option_wf_results: pd.DataFrame, option_context_summary: pd.DataFrame) -> None:
    st.subheader("Opções Inteligentes")
    st.info("Aprovada para estudo não é recomendação. Estruturas com dados insuficientes devem ser descartadas.")

    if option_runs.empty and option_chain.empty and option_structures.empty:
        st.warning("Nenhum scanner inteligente de opções salvo.")
        st.code("python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv")
        return

    latest = option_runs.iloc[0] if not option_runs.empty else {}
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Opções analisadas", int(latest.get("options_count") or len(option_chain)) if hasattr(latest, "get") else len(option_chain))
    m2.metric("Estruturas geradas", int(latest.get("structures_count") or len(option_structures)) if hasattr(latest, "get") else len(option_structures))
    m3.metric("Aprovadas p/ estudo", int(latest.get("approved_for_study_count") or 0) if hasattr(latest, "get") else 0)
    m4.metric("Bloqueadas", int(latest.get("blocked_count") or 0) if hasattr(latest, "get") else 0)

    if not option_runs.empty:
        st.subheader("Runs do Scanner")
        st.dataframe(option_runs, use_container_width=True, hide_index=True)

    st.subheader("Filtros")
    underlyings = sorted(option_chain["underlying"].dropna().astype(str).unique().tolist()) if not option_chain.empty and "underlying" in option_chain.columns else []
    maturities = sorted(option_chain["maturity_date"].dropna().astype(str).unique().tolist()) if not option_chain.empty and "maturity_date" in option_chain.columns else []
    structure_types = sorted(option_structures["structure_type"].dropna().astype(str).unique().tolist()) if not option_structures.empty and "structure_type" in option_structures.columns else []
    statuses = sorted(option_structures["governance_status"].dropna().astype(str).unique().tolist()) if not option_structures.empty and "governance_status" in option_structures.columns else []
    c1, c2, c3, c4 = st.columns(4)
    selected_underlying = c1.selectbox("Underlying", ["Todos", *underlyings], index=0)
    selected_maturity = c2.selectbox("Vencimento", ["Todos", *maturities], index=0)
    selected_structure = c3.selectbox("Estrutura", ["Todos", *structure_types], index=0)
    selected_status = c4.selectbox("Status", ["Todos", *statuses], index=0)
    c5, c6 = st.columns(2)
    max_spread = c5.slider("Spread máximo (%)", 0.0, 100.0, 100.0)
    min_liquidity = c6.slider("Liquidez mínima", 0.0, 100.0, 0.0)

    chain_view = option_chain.copy()
    if selected_underlying != "Todos" and not chain_view.empty and "underlying" in chain_view.columns:
        chain_view = chain_view[chain_view["underlying"].astype(str) == selected_underlying]
    if selected_maturity != "Todos" and not chain_view.empty and "maturity_date" in chain_view.columns:
        chain_view = chain_view[chain_view["maturity_date"].astype(str) == selected_maturity]
    if not chain_view.empty and "spread_pct" in chain_view.columns:
        chain_view = chain_view[pd.to_numeric(chain_view["spread_pct"], errors="coerce").fillna(999.0) <= max_spread]
    if not chain_view.empty and "liquidity_score" in chain_view.columns:
        chain_view = chain_view[pd.to_numeric(chain_view["liquidity_score"], errors="coerce").fillna(0.0) >= min_liquidity]

    st.subheader("Cadeia de opções")
    if chain_view.empty:
        st.info("Sem opções após os filtros selecionados.")
    else:
        chain_cols = [
            "option_ticker",
            "underlying",
            "option_type",
            "strike",
            "maturity_date",
            "days_to_maturity",
            "last_price",
            "spread_pct",
            "volume",
            "trades",
            "moneyness_class",
            "liquidity_score",
            "risk_score",
            "delta",
            "theta",
            "vega",
        ]
        st.dataframe(chain_view[[c for c in chain_cols if c in chain_view.columns]], use_container_width=True, hide_index=True)

    structures_view = option_structures.copy()
    if selected_underlying != "Todos" and not structures_view.empty and "underlying" in structures_view.columns:
        structures_view = structures_view[structures_view["underlying"].astype(str) == selected_underlying]
    if selected_maturity != "Todos" and not structures_view.empty and "maturity_date" in structures_view.columns:
        structures_view = structures_view[structures_view["maturity_date"].astype(str) == selected_maturity]
    if selected_structure != "Todos" and not structures_view.empty and "structure_type" in structures_view.columns:
        structures_view = structures_view[structures_view["structure_type"].astype(str) == selected_structure]
    if selected_status != "Todos" and not structures_view.empty and "governance_status" in structures_view.columns:
        structures_view = structures_view[structures_view["governance_status"].astype(str) == selected_status]

    st.subheader("Estruturas candidatas")
    if structures_view.empty:
        st.info("Sem estruturas após os filtros selecionados.")
    else:
        structure_cols = [
            "structure_type",
            "underlying",
            "maturity_date",
            "net_debit",
            "max_loss",
            "max_profit",
            "breakeven",
            "payoff_ratio",
            "liquidity_score",
            "risk_score",
            "structure_score",
            "candidate_status",
            "governance_status",
            "explanation",
        ]
        st.dataframe(structures_view[[c for c in structure_cols if c in structures_view.columns]], use_container_width=True, hide_index=True)
        if "governance_status" in structures_view.columns:
            st.bar_chart(structures_view["governance_status"].value_counts())

    st.subheader("Backtest de Estruturas")
    st.warning("Backtest preliminar de opções depende da qualidade da cadeia histórica, bid/ask e premissas de execução. Não é recomendação.")
    if option_backtest_runs.empty:
        st.info("Nenhum backtest de estruturas salvo.")
        st.code("python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv")
    else:
        latest_bt = option_backtest_runs.iloc[0]
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Status", latest_bt.get("status") or "-")
        b2.metric("Trades", int(latest_bt.get("entries_count") or 0))
        b3.metric("Win rate", _metric_value(latest_bt.get("win_rate"), "%"))
        b4.metric("Ret. líquido médio", _metric_value(latest_bt.get("mean_net_return"), "%"))
        b5, b6, b7 = st.columns(3)
        b5.metric("Profit factor", _metric_value(latest_bt.get("profit_factor")))
        b6.metric("Custo médio", _metric_value(latest_bt.get("avg_cost_drag")))
        b7.metric("Estrutura", latest_bt.get("structure_type") or "-")
        st.dataframe(option_backtest_runs, use_container_width=True, hide_index=True)
        if option_backtest_results.empty:
            st.info("Run salvo sem resultados concluídos ou com dados insuficientes.")
        else:
            st.dataframe(option_backtest_results, use_container_width=True, hide_index=True)
            if "status" in option_backtest_results.columns:
                st.markdown("Motivos/status")
                st.bar_chart(option_backtest_results["status"].value_counts())
            if "structure_type" in option_backtest_results.columns and "net_return" in option_backtest_results.columns:
                st.markdown("Retorno líquido por estrutura")
                by_structure = option_backtest_results.groupby("structure_type")["net_return"].mean(numeric_only=True)
                if not by_structure.empty:
                    st.bar_chart(by_structure)
            if "underlying" in option_backtest_results.columns and "net_return" in option_backtest_results.columns:
                st.markdown("Retorno líquido por ativo-objeto")
                by_underlying = option_backtest_results.groupby("underlying")["net_return"].mean(numeric_only=True)
                if not by_underlying.empty:
                    st.bar_chart(by_underlying)

    st.subheader("Walk-forward de Estruturas")
    if option_wf_runs.empty:
        st.info("Nenhum walk-forward de estruturas de opções salvo.")
        st.code("python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv")
    else:
        latest_wf = option_wf_runs.iloc[0]
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Robustez", latest_wf.get("robustness_class") or "-")
        w2.metric("Governança", latest_wf.get("governance_status") or "-")
        w3.metric("Janelas", int(latest_wf.get("windows_count") or 0))
        w4.metric("Janelas positivas", _metric_value(latest_wf.get("positive_windows_pct"), "%"))
        w5, w6, w7 = st.columns(3)
        w5.metric("Ret. teste", _metric_value(latest_wf.get("mean_test_net_return"), "%"))
        w6.metric("Win teste", _metric_value(latest_wf.get("mean_test_win_rate"), "%"))
        w7.metric("Profit factor", _metric_value(latest_wf.get("mean_test_profit_factor")))
        st.dataframe(option_wf_runs, use_container_width=True, hide_index=True)
        if option_wf_results.empty:
            st.info("Run salvo sem janelas válidas ou com dados insuficientes.")
        else:
            st.dataframe(option_wf_results, use_container_width=True, hide_index=True)
            if "test_mean_net_return" in option_wf_results.columns:
                st.bar_chart(option_wf_results.set_index("window_id")["test_mean_net_return"])
        st.subheader("Estabilidade e Contexto")
        if option_context_summary.empty:
            st.info("Sem resumo de estabilidade por vencimento, moneyness, liquidez, regime ou evento.")
        else:
            st.dataframe(option_context_summary, use_container_width=True, hide_index=True)
            dte = option_context_summary[option_context_summary["context_type"].astype(str) == "dte_bucket"]
            if not dte.empty:
                st.markdown("Estabilidade por vencimento")
                st.bar_chart(dte.set_index("context_value")["mean_net_return"])
            money = option_context_summary[option_context_summary["context_type"].astype(str) == "moneyness_bucket"]
            if not money.empty:
                st.markdown("Estabilidade por moneyness")
                st.bar_chart(money.set_index("context_value")["mean_net_return"])


def _tab_operation(daily_runs: pd.DataFrame, source_health: pd.DataFrame, open_alerts: pd.DataFrame) -> None:
    st.subheader("Operação & Saúde das Fontes")
    if daily_runs.empty:
        st.warning("Nenhuma rotina diária salva.")
        st.code(
            "python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 "
            "--with-regimes --with-event-context --with-governance --save-db --csv"
        )
    else:
        latest = daily_runs.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", latest.get("status") or "-")
        c2.metric("Health", latest.get("health_overall_status") or "-")
        c3.metric("Cobertura eventos", latest.get("event_coverage_quality") or "-")
        c4.metric("Alertas", int(latest.get("alerts_count") or 0))
        c5, c6, c7 = st.columns(3)
        c5.metric("Eventos carregados", int(latest.get("events_loaded") or 0))
        c6.metric("Após dedupe", int(latest.get("events_after_dedup") or 0))
        c7.metric("Sinais cobertos", _metric_value(float(latest.get("signals_covered_pct") or 0) * 100, "%"))
        st.dataframe(daily_runs, use_container_width=True, hide_index=True)

    st.subheader("Saúde das fontes")
    if source_health.empty:
        st.info("Nenhum health check salvo.")
        st.code("python -m src.scanners.source_health_check --save-db --csv")
    else:
        st.dataframe(source_health, use_container_width=True, hide_index=True)
        if "status" in source_health.columns:
            st.bar_chart(source_health["status"].value_counts())
        bad = source_health[source_health["status"].astype(str).str.upper().isin(["ERROR", "MISSING", "STALE", "EMPTY"])]
        if not bad.empty:
            st.warning("Há fontes ausentes, vazias ou desatualizadas. A cobertura de eventos deve ser interpretada com cautela.")

    st.subheader("Alertas abertos")
    if open_alerts.empty:
        st.success("Sem alertas operacionais abertos.")
    else:
        st.dataframe(open_alerts, use_container_width=True, hide_index=True)
        if "severity" in open_alerts.columns:
            st.bar_chart(open_alerts["severity"].value_counts())


def _tab_technical_quant(
    technical_features: pd.DataFrame,
    technical_setups: pd.DataFrame,
    technical_bt_runs: pd.DataFrame,
    technical_bt_results: pd.DataFrame,
    technical_wf_runs: pd.DataFrame,
    technical_wf_results: pd.DataFrame,
    technical_threshold_runs: pd.DataFrame,
    technical_dedup_runs: pd.DataFrame,
) -> None:
    st.subheader("Análise Técnica Quant")
    if technical_features.empty and technical_setups.empty and technical_bt_runs.empty:
        st.warning("Nenhum dado técnico quantitativo salvo.")
        st.code(
            "python -m src.scanners.technical_analysis_scanner --start 2026-01-02 --end 2026-04-30 "
            "--tickers PETR4 VALE3 ITUB4 --save-db --csv --with-backtest"
        )
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ativos analisados", technical_features["ticker"].nunique() if "ticker" in technical_features.columns else 0)
    c2.metric("Setups detectados", len(technical_setups))
    setup_mode = technical_setups["setup_type"].mode().iloc[0] if not technical_setups.empty and "setup_type" in technical_setups.columns else "-"
    c3.metric("Setup mais comum", setup_mode)
    mean_score = pd.to_numeric(technical_features.get("technical_score_final"), errors="coerce").mean() if not technical_features.empty else None
    c4.metric("Score técnico médio", _metric_value(mean_score))

    if not technical_setups.empty:
        st.subheader("Setups técnicos")
        filters = st.columns(4)
        tickers = ["Todos"] + sorted(technical_setups["ticker"].dropna().astype(str).unique().tolist())
        setup_types = ["Todos"] + sorted(technical_setups["setup_type"].dropna().astype(str).unique().tolist())
        statuses = ["Todos"] + sorted(technical_setups["technical_status"].dropna().astype(str).unique().tolist()) if "technical_status" in technical_setups.columns else ["Todos"]
        directions = ["Todos"] + sorted(technical_setups["setup_direction"].dropna().astype(str).unique().tolist()) if "setup_direction" in technical_setups.columns else ["Todos"]
        ticker = filters[0].selectbox("Ticker técnico", tickers)
        setup_type = filters[1].selectbox("Setup", setup_types)
        status = filters[2].selectbox("Status técnico", statuses)
        direction = filters[3].selectbox("Direção", directions)
        view = technical_setups.copy()
        if ticker != "Todos":
            view = view[view["ticker"].astype(str) == ticker]
        if setup_type != "Todos":
            view = view[view["setup_type"].astype(str) == setup_type]
        if status != "Todos" and "technical_status" in view.columns:
            view = view[view["technical_status"].astype(str) == status]
        if direction != "Todos" and "setup_direction" in view.columns:
            view = view[view["setup_direction"].astype(str) == direction]
        cols = [c for c in ["trade_date", "ticker", "setup_type", "setup_score", "setup_confidence", "setup_direction", "technical_status", "governance_status", "explanation"] if c in view.columns]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
        if "governance_status" in technical_setups.columns:
            st.bar_chart(technical_setups["governance_status"].value_counts())

    st.subheader("Features técnicas")
    if technical_features.empty:
        st.info("Sem snapshots de features técnicas.")
    else:
        cols = [c for c in ["trade_date", "ticker", "trend_score", "momentum_score", "volatility_score", "volume_score", "technical_score_final", "technical_status"] if c in technical_features.columns]
        st.dataframe(technical_features[cols].head(500), use_container_width=True, hide_index=True)
        if "technical_status" in technical_features.columns:
            st.bar_chart(technical_features["technical_status"].value_counts())

    st.subheader("Backtest técnico")
    if technical_bt_runs.empty:
        st.info("Nenhum backtest técnico salvo.")
    else:
        st.dataframe(technical_bt_runs, use_container_width=True, hide_index=True)
        if not technical_bt_results.empty:
            st.dataframe(technical_bt_results, use_container_width=True, hide_index=True)
            if "setup_type" in technical_bt_results.columns and "future_return_5d" in technical_bt_results.columns:
                ret = technical_bt_results.assign(future_return_5d=pd.to_numeric(technical_bt_results["future_return_5d"], errors="coerce"))
                st.bar_chart(ret.groupby("setup_type")["future_return_5d"].mean())

    st.subheader("Walk-forward Técnico")
    if technical_wf_runs.empty:
        st.info("Nenhum walk-forward técnico salvo.")
        st.code(
            "python -m src.scanners.technical_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 "
            "--tickers PETR4 VALE3 ITUB4 --train-months 3 --test-months 1 --dedupe --optimize-thresholds --save-db --csv"
        )
    else:
        latest = technical_wf_runs.iloc[0]
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("Robustez", latest.get("robustness_class") or "-")
        w2.metric("Governança OOS", latest.get("governance_status") or "-")
        w3.metric("Janelas positivas", _metric_value(latest.get("positive_windows_pct"), "%"))
        w4.metric("Retorno teste", _metric_value(latest.get("mean_test_return"), "%"))
        st.dataframe(technical_wf_runs, use_container_width=True, hide_index=True)
        if not technical_wf_results.empty:
            st.dataframe(technical_wf_results, use_container_width=True, hide_index=True)
            if "test_mean_return" in technical_wf_results.columns:
                st.bar_chart(technical_wf_results.set_index("window_id")["test_mean_return"])
        if not technical_threshold_runs.empty:
            st.markdown("Thresholds sugeridos para estudo")
            st.dataframe(technical_threshold_runs, use_container_width=True, hide_index=True)
        if not technical_dedup_runs.empty:
            st.markdown("Deduplicação e redundância")
            st.dataframe(technical_dedup_runs, use_container_width=True, hide_index=True)

    st.info("Setups técnicos são padrões a investigar. A aba não executa ordens, não altera score principal e não constitui recomendação.")


def _json_list_text(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return "\n".join(f"- {item}" for item in parsed) or "-"
    except json.JSONDecodeError:
        pass
    return str(value)


def _tab_asset_intelligence(asset_intelligence: pd.DataFrame, asset_diffs: pd.DataFrame) -> None:
    st.subheader("Inteligência Integrada")
    if asset_intelligence.empty:
        st.info(
            "Nenhum snapshot integrado salvo. Rode:\n\n"
            "python -m src.scanners.asset_intelligence_snapshot --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv\n\n"
            "python -m src.scanners.generate_asset_intelligence_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence"
        )
        return

    latest = asset_intelligence.sort_values(["ticker", "created_at"], ascending=[True, False]).groupby("ticker", as_index=False).first()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Ativos", int(latest["ticker"].nunique()) if "ticker" in latest.columns else len(latest))
    c2.metric("Alta convergência", int((latest["integrated_status"] == "ALTA_CONVERGENCIA_ANALITICA").sum()))
    c3.metric("Assimetria", int((latest["integrated_status"] == "ASSIMETRIA_A_INVESTIGAR").sum()))
    c4.metric("Bloqueados", int(latest["integrated_status"].astype(str).str.contains("BLOQUEADO", na=False).sum()))
    c5.metric("Divergência técnica x valuation", int((latest["integrated_status"] == "DIVERGENCIA_TECNICA_VALUATION").sum()))
    c6.metric("Dados insuficientes", int(latest["integrated_status"].astype(str).str.contains("DADOS|SEM_DADOS", na=False).sum()))

    filters = st.columns(5)
    tickers = ["Todos"] + sorted(latest["ticker"].dropna().astype(str).unique().tolist())
    statuses = ["Todos"] + sorted(latest["integrated_status"].dropna().astype(str).unique().tolist())
    govs = ["Todos"] + sorted(latest["integrated_governance_status"].dropna().astype(str).unique().tolist())
    regimes = ["Todos"] + sorted(latest["primary_regime"].dropna().astype(str).unique().tolist()) if "primary_regime" in latest.columns else ["Todos"]
    ticker = filters[0].selectbox("Ticker", tickers, key="asset_intelligence_ticker")
    status = filters[1].selectbox("Status integrado", statuses, key="asset_intelligence_status")
    gov = filters[2].selectbox("Governança", govs, key="asset_intelligence_gov")
    regime = filters[3].selectbox("Regime", regimes, key="asset_intelligence_regime")
    only_valuation = filters[4].checkbox("Com valuation", value=False, key="asset_intelligence_with_valuation")

    view = latest.copy()
    if ticker != "Todos":
        view = view[view["ticker"].astype(str) == ticker]
    if status != "Todos":
        view = view[view["integrated_status"].astype(str) == status]
    if gov != "Todos":
        view = view[view["integrated_governance_status"].astype(str) == gov]
    if regime != "Todos" and "primary_regime" in view.columns:
        view = view[view["primary_regime"].astype(str) == regime]
    if only_valuation and "valuation_available" in view.columns:
        view = view[pd.to_numeric(view["valuation_available"], errors="coerce").fillna(0).astype(bool)]

    cols = [
        "ticker",
        "technical_score_final",
        "quant_score",
        "upside_pct",
        "valuation_available",
        "best_option_structure_type",
        "option_structure_score",
        "ensemble_vol",
        "var_95",
        "risk_status",
        "primary_regime",
        "event_context_type",
        "integrated_score",
        "integrated_status",
        "integrated_governance_status",
        "explanation",
    ]
    st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True, hide_index=True)

    if not view.empty:
        selected = st.selectbox("Painel por ativo", view["ticker"].dropna().astype(str).tolist(), key="asset_intelligence_detail")
        row = view[view["ticker"].astype(str) == selected].iloc[0]
        st.markdown("#### Explicação integrada")
        st.write(row.get("explanation", "-"))
        f1, f2, f3 = st.columns(3)
        f1.markdown("**Razões favoráveis**")
        f1.markdown(_json_list_text(row.get("reasons_for_json")))
        f2.markdown("**Razões contrárias**")
        f2.markdown(_json_list_text(row.get("reasons_against_json")))
        f3.markdown("**Ações necessárias**")
        f3.markdown(_json_list_text(row.get("required_actions_json")))

    _csv_download("Baixar snapshot integrado", view, "asset_intelligence_snapshot.csv")
    st.info("Snapshot integrado é uma leitura analítica auditável. Não altera o ranking principal e não constitui recomendação.")

    st.subheader("Histórico & Mudanças")
    if asset_diffs.empty:
        st.info("Nenhum diff salvo. Rode:")
        st.code("python -m src.scanners.asset_intelligence_diff --latest --save-db --csv")
    else:
        diff_view = asset_diffs.copy()
        diff_filters = st.columns(4)
        diff_tickers = ["Todos"] + sorted(diff_view["ticker"].dropna().astype(str).unique().tolist())
        change_types = ["Todos"] + sorted(diff_view["material_change_type"].dropna().astype(str).unique().tolist())
        diff_ticker = diff_filters[0].selectbox("Ticker diff", diff_tickers, key="asset_intelligence_diff_ticker")
        change_type = diff_filters[1].selectbox("Tipo de mudança", change_types, key="asset_intelligence_diff_type")
        material_only = diff_filters[2].checkbox("Apenas materiais", value=False, key="asset_intelligence_diff_material")
        gov_only = diff_filters[3].checkbox("Mudança de governança", value=False, key="asset_intelligence_diff_gov")
        if diff_ticker != "Todos":
            diff_view = diff_view[diff_view["ticker"].astype(str) == diff_ticker]
        if change_type != "Todos":
            diff_view = diff_view[diff_view["material_change_type"].astype(str) == change_type]
        if material_only:
            diff_view = diff_view[pd.to_numeric(diff_view["material_change"], errors="coerce").fillna(0).astype(bool)]
        if gov_only:
            diff_view = diff_view[pd.to_numeric(diff_view["governance_changed"], errors="coerce").fillna(0).astype(bool)]
        diff_cols = [
            "created_at",
            "ticker",
            "material_change",
            "material_change_type",
            "score_delta",
            "data_quality_delta",
            "status_changed",
            "governance_changed",
            "explanation",
        ]
        st.dataframe(diff_view[[c for c in diff_cols if c in diff_view.columns]], use_container_width=True, hide_index=True)
        _csv_download("Baixar diffs integrados", diff_view, "asset_intelligence_diffs.csv")

    if not asset_intelligence.empty:
        st.markdown("#### Histórico por ativo")
        history_ticker = st.selectbox("Ticker histórico", sorted(asset_intelligence["ticker"].dropna().astype(str).unique().tolist()), key="asset_intelligence_history_ticker")
        hist = asset_intelligence[asset_intelligence["ticker"].astype(str) == history_ticker].copy()
        hist["created_at_dt"] = pd.to_datetime(hist.get("created_at"), errors="coerce")
        hist = hist.sort_values("created_at_dt")
        if len(hist) < 2:
            st.info("Histórico insuficiente: há apenas um snapshot para este ativo.")
        else:
            line_cols = [c for c in ["created_at", "integrated_score", "data_quality_score", "upside_pct"] if c in hist.columns]
            st.dataframe(hist[line_cols], use_container_width=True, hide_index=True)
            chart = hist.set_index("created_at")
            chart_cols = [c for c in ["integrated_score", "data_quality_score", "upside_pct"] if c in chart.columns]
            if chart_cols:
                st.line_chart(chart[chart_cols].apply(pd.to_numeric, errors="coerce"))


def _tab_risk_volatility(
    risk_snapshots: pd.DataFrame,
    volatility_estimates: pd.DataFrame,
    position_sizing: pd.DataFrame,
    stress_tests: pd.DataFrame,
) -> None:
    st.subheader("Risco & Volatilidade")
    if risk_snapshots.empty:
        st.info("Nenhum snapshot de risco salvo. Rode:")
        st.code("python -m src.scanners.risk_engine_snapshot --tickers PETR4 VALE3 ITUB4 --capital 100000 --risk-pct 0.005 --save-db --csv")
        return

    latest = risk_snapshots.sort_values(["ticker", "created_at"], ascending=[True, False]).groupby("ticker", as_index=False).first()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ativos com risco", int(latest["ticker"].nunique()) if "ticker" in latest.columns else len(latest))
    c2.metric("Risco bloqueado", int(latest["risk_status"].astype(str).str.contains("BLOCKED", na=False).sum()) if "risk_status" in latest.columns else 0)
    c3.metric("VaR médio 95%", _metric_value(pd.to_numeric(latest.get("parametric_var_95"), errors="coerce").mean()))
    c4.metric("Vol ensemble média", _metric_value(pd.to_numeric(latest.get("ensemble_vol"), errors="coerce").mean()))

    filters = st.columns(3)
    tickers = ["Todos"] + sorted(latest["ticker"].dropna().astype(str).unique().tolist())
    statuses = ["Todos"] + sorted(latest["risk_status"].dropna().astype(str).unique().tolist()) if "risk_status" in latest.columns else ["Todos"]
    regimes = ["Todos"] + sorted(latest["volatility_regime"].dropna().astype(str).unique().tolist()) if "volatility_regime" in latest.columns else ["Todos"]
    ticker = filters[0].selectbox("Ticker risco", tickers, key="risk_ticker")
    status = filters[1].selectbox("Status risco", statuses, key="risk_status")
    regime = filters[2].selectbox("Regime vol", regimes, key="risk_vol_regime")
    view = latest.copy()
    if ticker != "Todos":
        view = view[view["ticker"].astype(str) == ticker]
    if status != "Todos" and "risk_status" in view.columns:
        view = view[view["risk_status"].astype(str) == status]
    if regime != "Todos" and "volatility_regime" in view.columns:
        view = view[view["volatility_regime"].astype(str) == regime]

    cols = [
        "ticker",
        "trade_date",
        "price",
        "volatility_regime",
        "ensemble_vol",
        "parametric_var_95",
        "historical_var_95",
        "expected_shortfall_95",
        "recommended_size",
        "recommended_position_value",
        "limiting_factor",
        "risk_status",
        "explanation",
    ]
    st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True, hide_index=True)
    _csv_download("Baixar snapshots de risco", view, "risk_snapshots.csv")

    st.markdown("#### Modelos de volatilidade")
    vol_cols = [
        "ticker",
        "trade_date",
        "vol_20d",
        "vol_60d",
        "vol_ewma",
        "downside_vol",
        "parkinson_vol",
        "garman_klass_vol",
        "atr_vol",
        "ensemble_vol",
        "volatility_regime",
    ]
    st.dataframe(volatility_estimates[[c for c in vol_cols if c in volatility_estimates.columns]].head(300), use_container_width=True, hide_index=True)

    st.markdown("#### Sizing sugerido para estudo")
    size_cols = [
        "ticker",
        "trade_date",
        "capital",
        "risk_pct",
        "entry_price",
        "stop_price",
        "size_fixed_risk",
        "size_atr",
        "size_var",
        "size_liquidity",
        "final_size",
        "final_position_value",
        "limiting_factor",
        "estimated_var",
    ]
    st.dataframe(position_sizing[[c for c in size_cols if c in position_sizing.columns]].head(300), use_container_width=True, hide_index=True)

    st.markdown("#### Stress tests")
    st.dataframe(stress_tests.head(300), use_container_width=True, hide_index=True)
    st.info("A aba mede risco estimado e sizing sugerido para estudo. Não aplica tamanho automaticamente e não constitui recomendação financeira.")


def _tab_paper_trading(
    runs: pd.DataFrame,
    orders: pd.DataFrame,
    positions: pd.DataFrame,
    equity_curve: pd.DataFrame,
    exit_events: pd.DataFrame,
    rebalance_events: pd.DataFrame,
    pnl_attribution: pd.DataFrame,
    simulation_comparisons: pd.DataFrame | None = None,
    optimization_runs: pd.DataFrame | None = None,
    optimization_results: pd.DataFrame | None = None,
    walk_forward_runs: pd.DataFrame | None = None,
    walk_forward_results: pd.DataFrame | None = None,
    scenario_runs: pd.DataFrame | None = None,
    scenario_results: pd.DataFrame | None = None,
    cost_sensitivity: pd.DataFrame | None = None,
    signal_source_comparison: pd.DataFrame | None = None,
    fragility_runs: pd.DataFrame | None = None,
    fragility_assets: pd.DataFrame | None = None,
    fragility_sources: pd.DataFrame | None = None,
    drawdown_periods: pd.DataFrame | None = None,
    investigation_runs: pd.DataFrame | None = None,
    investigation_results: pd.DataFrame | None = None,
    hypothesis_oos_runs: pd.DataFrame | None = None,
    hypothesis_oos_results: pd.DataFrame | None = None,
    hypothesis_oos_coverage: pd.DataFrame | None = None,
    signal_coverage_runs: pd.DataFrame | None = None,
    signal_coverage_by_source: pd.DataFrame | None = None,
    hypothesis_ranking_runs: pd.DataFrame | None = None,
    hypothesis_ranking_results: pd.DataFrame | None = None,
    hypothesis_deep_runs: pd.DataFrame | None = None,
    hypothesis_deep_results: pd.DataFrame | None = None,
    hypothesis_block_reasons: pd.DataFrame | None = None,
) -> None:
    st.subheader("Paper Trading")
    if runs.empty:
        st.info("Nenhuma simulação de paper trading salva. Rode:")
        st.code("python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --save-db --csv")
        return
    latest = runs.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Capital inicial", _metric_value(latest.get("capital_initial")))
    c2.metric("Capital final", _metric_value(latest.get("capital_final")))
    c3.metric("Retorno", _metric_value(latest.get("total_return"), suffix="", decimals=4))
    c4.metric("Sharpe", _metric_value(latest.get("sharpe")))
    c5.metric("Max drawdown", _metric_value(latest.get("max_drawdown"), decimals=4))
    c6, c7, c8, c9 = st.columns(4)
    c6.metric("Trades", int(latest.get("trades_count") or 0))
    c7.metric("Win rate", _metric_value(latest.get("win_rate"), decimals=4))
    c8.metric("Profit factor", _metric_value(latest.get("profit_factor")))
    c9.metric("Governança", str(latest.get("governance_status", "-")))

    st.markdown("#### Curva de equity")
    if equity_curve.empty:
        st.info("Curva de equity não encontrada para o run selecionado.")
    else:
        chart = equity_curve.copy()
        chart["trade_date"] = pd.to_datetime(chart["trade_date"], errors="coerce")
        chart = chart.sort_values("trade_date").set_index("trade_date")
        plot_cols = [c for c in ["equity", "exposure", "portfolio_var_95", "portfolio_es_95"] if c in chart.columns]
        if plot_cols:
            st.line_chart(chart[plot_cols].apply(pd.to_numeric, errors="coerce"))
        st.dataframe(equity_curve, use_container_width=True, hide_index=True)

    st.markdown("#### Ordens simuladas")
    st.dataframe(orders, use_container_width=True, hide_index=True)
    st.markdown("#### Posições simuladas")
    st.dataframe(positions, use_container_width=True, hide_index=True)
    st.markdown("#### Eventos de saída")
    if exit_events.empty:
        st.info("Nenhum evento de saída avançada salvo para este run.")
    else:
        st.dataframe(exit_events, use_container_width=True, hide_index=True)
    st.markdown("#### Rebalanceamento simulado")
    if rebalance_events.empty:
        st.info("Nenhum rebalanceamento simulado salvo para este run.")
    else:
        st.dataframe(rebalance_events, use_container_width=True, hide_index=True)
    st.markdown("#### Decomposição de P&L")
    if pnl_attribution.empty:
        st.info("Nenhuma decomposição de P&L salva para este run.")
    else:
        st.dataframe(pnl_attribution, use_container_width=True, hide_index=True)

    st.markdown("#### Robustez das Regras")
    simulation_comparisons = simulation_comparisons if simulation_comparisons is not None else pd.DataFrame()
    optimization_runs = optimization_runs if optimization_runs is not None else pd.DataFrame()
    optimization_results = optimization_results if optimization_results is not None else pd.DataFrame()
    walk_forward_runs = walk_forward_runs if walk_forward_runs is not None else pd.DataFrame()
    walk_forward_results = walk_forward_results if walk_forward_results is not None else pd.DataFrame()
    if walk_forward_runs.empty and simulation_comparisons.empty and optimization_runs.empty:
        st.info("Nenhuma robustez de regras salva. Rode:")
        st.code("python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv")
    else:
        if not walk_forward_runs.empty:
            latest_wf = walk_forward_runs.iloc[0]
            r1, r2, r3, r4, r5 = st.columns(5)
            r1.metric("Robustez", str(latest_wf.get("robustness_class", "-")))
            r2.metric("Governança OOS", str(latest_wf.get("governance_status", "-")))
            r3.metric("Janelas", int(latest_wf.get("windows_count") or 0))
            r4.metric("Janelas positivas", _metric_value(latest_wf.get("positive_windows_pct"), decimals=4))
            r5.metric("Retorno OOS", _metric_value(latest_wf.get("mean_test_return"), decimals=4))
            st.dataframe(walk_forward_runs, use_container_width=True, hide_index=True)
            st.dataframe(walk_forward_results, use_container_width=True, hide_index=True)
        if not optimization_runs.empty:
            st.markdown("##### Parametros de saida em estudo")
            st.dataframe(optimization_runs, use_container_width=True, hide_index=True)
            st.dataframe(optimization_results.head(50), use_container_width=True, hide_index=True)
        if not simulation_comparisons.empty:
            st.markdown("##### Simple vs Advanced")
            st.dataframe(simulation_comparisons, use_container_width=True, hide_index=True)

    st.markdown("#### Validação Multi-Cenário")
    scenario_runs = scenario_runs if scenario_runs is not None else pd.DataFrame()
    scenario_results = scenario_results if scenario_results is not None else pd.DataFrame()
    cost_sensitivity = cost_sensitivity if cost_sensitivity is not None else pd.DataFrame()
    signal_source_comparison = signal_source_comparison if signal_source_comparison is not None else pd.DataFrame()
    if scenario_runs.empty:
        st.info("Nenhuma validação multi-cenário salva. Rode:")
        st.code("python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv")
    else:
        latest_scenario = scenario_runs.iloc[0]
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Governança", str(latest_scenario.get("governance_status", "-")))
        s2.metric("Períodos", int(latest_scenario.get("periods_count") or 0))
        s3.metric("Cenários", int(latest_scenario.get("scenarios_count") or 0))
        s4.metric("Retorno médio", _metric_value(latest_scenario.get("mean_return"), decimals=4))
        s5.metric("Períodos positivos", _metric_value(latest_scenario.get("positive_periods_pct"), decimals=4))
        st.dataframe(scenario_runs, use_container_width=True, hide_index=True)
        st.markdown("##### Resultados por período/cenário")
        st.dataframe(scenario_results, use_container_width=True, hide_index=True)
        st.markdown("##### Sensibilidade a custos")
        st.dataframe(cost_sensitivity, use_container_width=True, hide_index=True)
        st.markdown("##### Comparação por fonte de sinal")
        st.dataframe(signal_source_comparison, use_container_width=True, hide_index=True)

    st.markdown("#### Diagnóstico de Fragilidade")
    fragility_runs = fragility_runs if fragility_runs is not None else pd.DataFrame()
    fragility_assets = fragility_assets if fragility_assets is not None else pd.DataFrame()
    fragility_sources = fragility_sources if fragility_sources is not None else pd.DataFrame()
    drawdown_periods = drawdown_periods if drawdown_periods is not None else pd.DataFrame()
    if fragility_runs.empty:
        st.info("Nenhum diagnóstico de fragilidade salvo. Rode:")
        st.code("python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv")
    else:
        latest_frag = fragility_runs.iloc[0]
        f1, f2, f3, f4, f5 = st.columns(5)
        f1.metric("Fragility score", _metric_value(latest_frag.get("fragility_score")))
        f2.metric("Classe", str(latest_frag.get("fragility_class", "-")))
        f3.metric("Governança", str(latest_frag.get("governance_status", "-")))
        f4.metric("P&L líquido", _metric_value(latest_frag.get("total_net_pnl")))
        f5.metric("Trades", int(latest_frag.get("total_trades") or 0))
        st.markdown("##### Ativos frágeis")
        st.dataframe(fragility_assets, use_container_width=True, hide_index=True)
        st.markdown("##### Fontes de sinal frágeis")
        st.dataframe(fragility_sources, use_container_width=True, hide_index=True)
        st.markdown("##### Drawdowns")
        st.dataframe(drawdown_periods, use_container_width=True, hide_index=True)

    st.markdown("#### Investigações Analíticas")
    investigation_runs = investigation_runs if investigation_runs is not None else pd.DataFrame()
    investigation_results = investigation_results if investigation_results is not None else pd.DataFrame()
    if investigation_runs.empty:
        st.info("Nenhuma investigação analítica salva. Rode:")
        st.code("python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv")
    else:
        latest_inv = investigation_runs.iloc[0]
        i1, i2, i3, i4 = st.columns(4)
        i1.metric("Hipóteses", int(latest_inv.get("hypotheses_count") or 0))
        i2.metric("Melhor hipótese", str(latest_inv.get("best_hypothesis_id", "-")))
        i3.metric("Improvement score", _metric_value(latest_inv.get("best_improvement_score"), decimals=2))
        i4.metric("Com melhora", int(latest_inv.get("improved_count") or 0))
        cols = [
            "hypothesis_id",
            "hypothesis_type",
            "target",
            "simulated_return",
            "simulated_drawdown",
            "simulated_trades",
            "fragility_score_before",
            "fragility_score_after",
            "improvement_score",
            "governance_status",
            "conclusion",
        ]
        st.dataframe(investigation_results[[c for c in cols if c in investigation_results.columns]], use_container_width=True, hide_index=True)

    st.markdown("##### Ranking de Hipóteses")
    hypothesis_ranking_runs = hypothesis_ranking_runs if hypothesis_ranking_runs is not None else pd.DataFrame()
    hypothesis_ranking_results = hypothesis_ranking_results if hypothesis_ranking_results is not None else pd.DataFrame()
    if hypothesis_ranking_runs.empty or hypothesis_ranking_results.empty:
        st.info("Nenhum ranking multi-fonte de hipóteses salvo. Rode:")
        st.code("python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv")
    else:
        latest_rank = hypothesis_ranking_runs.iloc[0]
        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Melhor hipótese", str(latest_rank.get("best_hypothesis_id", "-")))
        r2.metric("Melhor score", _metric_value(latest_rank.get("best_score"), decimals=2))
        r3.metric("Robustas", int(latest_rank.get("robust_count") or 0))
        r4.metric("Promissoras", int(latest_rank.get("promising_count") or 0))
        r5.metric("Rejeitadas", int(latest_rank.get("rejected_count") or 0))
        cols = [
            "hypothesis_id",
            "hypothesis_robustness_score",
            "hypothesis_class",
            "governance_status",
            "source_diversity_score",
            "mean_return_delta",
            "mean_drawdown_delta",
            "mean_fragility_delta",
            "overfitting_flag",
            "cost_sensitivity_flag",
        ]
        st.dataframe(hypothesis_ranking_results[[c for c in cols if c in hypothesis_ranking_results.columns]], use_container_width=True, hide_index=True)

    st.markdown("##### Deep Dive de Hipóteses")
    hypothesis_deep_runs = hypothesis_deep_runs if hypothesis_deep_runs is not None else pd.DataFrame()
    hypothesis_deep_results = hypothesis_deep_results if hypothesis_deep_results is not None else pd.DataFrame()
    hypothesis_block_reasons = hypothesis_block_reasons if hypothesis_block_reasons is not None else pd.DataFrame()
    if hypothesis_deep_runs.empty or hypothesis_deep_results.empty:
        st.info("Nenhum deep dive de hipóteses salvo. Rode:")
        st.code("python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv")
    else:
        latest_deep = hypothesis_deep_runs.iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Hipóteses", int(latest_deep.get("hypotheses_count") or 0))
        d2.metric("Melhor hipótese", str(latest_deep.get("best_hypothesis_id", "-")))
        d3.metric("Aprovadas observação", int(latest_deep.get("approved_count") or 0))
        d4.metric("Bloqueadas", int(latest_deep.get("blocked_count") or 0))
        if not hypothesis_block_reasons.empty:
            reason_cols = ["hypothesis_id", "primary_block_reason", "secondary_block_reason", "explanation", "required_actions_json"]
            st.dataframe(hypothesis_block_reasons[[c for c in reason_cols if c in hypothesis_block_reasons.columns]], use_container_width=True, hide_index=True)
        deep_cols = [
            "hypothesis_id",
            "governance_status",
            "block_reason",
            "signal_source",
            "cost_scenario",
            "slippage_scenario",
            "regime",
            "ticker",
            "positive_improvement_pct",
            "mean_return_delta",
            "mean_drawdown_delta",
            "mean_fragility_delta",
        ]
        st.dataframe(hypothesis_deep_results[[c for c in deep_cols if c in hypothesis_deep_results.columns]], use_container_width=True, hide_index=True)

    st.markdown("##### Validação OOS das Hipóteses")
    hypothesis_oos_runs = hypothesis_oos_runs if hypothesis_oos_runs is not None else pd.DataFrame()
    hypothesis_oos_results = hypothesis_oos_results if hypothesis_oos_results is not None else pd.DataFrame()
    hypothesis_oos_coverage = hypothesis_oos_coverage if hypothesis_oos_coverage is not None else pd.DataFrame()
    if hypothesis_oos_runs.empty:
        st.info("Nenhuma validação OOS de hipótese salva. Rode:")
        st.code("python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --require-source-coverage --min-useful-coverage-pct 0.5 --save-db --csv")
    else:
        latest_oos = hypothesis_oos_runs.iloc[0]
        o1, o2, o3, o4, o5 = st.columns(5)
        o1.metric("Hipótese", str(latest_oos.get("hypothesis_id", "-")))
        o2.metric("Robustez", str(latest_oos.get("robustness_class", "-")))
        o3.metric("Governança", str(latest_oos.get("governance_status", "-")))
        o4.metric("Melhora +", _metric_value(latest_oos.get("positive_improvement_pct"), decimals=4))
        o5.metric("Delta retorno", _metric_value(latest_oos.get("mean_return_delta"), decimals=4))
        st.dataframe(hypothesis_oos_runs, use_container_width=True, hide_index=True)
        st.dataframe(hypothesis_oos_results, use_container_width=True, hide_index=True)
        if not hypothesis_oos_coverage.empty:
            st.markdown("###### Cobertura OOS por janela/cenário")
            c1, c2, c3 = st.columns(3)
            useful = hypothesis_oos_coverage["useful_cell"].astype(bool)
            c1.metric("Células úteis", f"{int(useful.sum())}/{len(hypothesis_oos_coverage)}")
            c2.metric("Fontes úteis", int(hypothesis_oos_coverage.loc[useful, "signal_source"].nunique()))
            c3.metric("Regimes úteis", int(hypothesis_oos_coverage.loc[useful & hypothesis_oos_coverage["regime_filter"].astype(str).ne(""), "regime_filter"].nunique()))
            st.dataframe(hypothesis_oos_coverage, use_container_width=True, hide_index=True)

    st.markdown("#### Cobertura das Fontes de Sinal")
    signal_coverage_runs = signal_coverage_runs if signal_coverage_runs is not None else pd.DataFrame()
    signal_coverage_by_source = signal_coverage_by_source if signal_coverage_by_source is not None else pd.DataFrame()
    if signal_coverage_by_source.empty:
        st.info("Sem validação de cobertura salva para fontes de sinal em estudo. Rode:")
        st.code("python -m src.scanners.signal_coverage_check --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv")
    else:
        latest_cov = signal_coverage_runs.iloc[0] if not signal_coverage_runs.empty else {}
        c1, c2, c3 = st.columns(3)
        c1.metric("Status de cobertura", str(latest_cov.get("coverage_status", "-") if hasattr(latest_cov, "get") else "-"))
        c2.metric("Cobertura útil média", _metric_value(latest_cov.get("useful_cells_pct", 0) if hasattr(latest_cov, "get") else 0, decimals=4))
        c3.metric("Fontes avaliadas", int(signal_coverage_by_source["signal_source"].nunique()) if "signal_source" in signal_coverage_by_source.columns else 0)
        cols = [
            "signal_source",
            "signals_count",
            "tickers_count",
            "active_days_count",
            "regimes_count",
            "coverage_pct",
            "coverage_status",
            "requirements_status",
        ]
        st.dataframe(signal_coverage_by_source[[c for c in cols if c in signal_coverage_by_source.columns]], use_container_width=True, hide_index=True)
        st.caption("Últimas populações technical/integrated são inferidas pela data do último sinal persistido na cobertura. Fonte em estudo; não recomendação.")
        st.code("python -m src.scanners.populate_technical_signals --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --dedupe --save-db --csv")
        st.code("python -m src.scanners.populate_asset_intelligence_history --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv")
    st.markdown("#### Runs")
    st.dataframe(runs, use_container_width=True, hide_index=True)
    _csv_download("Baixar ordens simuladas", orders, "paper_orders.csv")
    _csv_download("Baixar curva de equity", equity_curve, "paper_equity_curve.csv")
    _csv_download("Baixar eventos de saída", exit_events, "paper_exit_events.csv")
    _csv_download("Baixar attribution de P&L", pnl_attribution, "paper_pnl_attribution.csv")
    st.info("Paper trading é simulação. Não executa ordens reais e não constitui recomendação.")


def _tab_data_audit(
    audit_runs: pd.DataFrame,
    audit_results: pd.DataFrame,
    traceability: pd.DataFrame,
    reconciliation_runs: pd.DataFrame | None = None,
    reconciliation_results: pd.DataFrame | None = None,
    manifest_runs: pd.DataFrame | None = None,
    manifest: pd.DataFrame | None = None,
    ingestion_runs: pd.DataFrame | None = None,
    ingestion_steps: pd.DataFrame | None = None,
    ingestion_validation: pd.DataFrame | None = None,
    ingestion_comparison: pd.DataFrame | None = None,
) -> None:
    st.subheader("Auditoria de Dados")
    if audit_runs.empty and audit_results.empty:
        st.info("Nenhuma auditoria de dados salva. Rode:")
        st.code("python -m src.scanners.data_source_audit --save-db --csv")
        st.code("python -m src.scanners.data_source_audit --sources ri --check-ri-online --save-db --csv")
        return

    if not audit_runs.empty:
        latest = audit_runs.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Status geral", latest.get("overall_status", "-"))
        c2.metric("Confiabilidade", _metric_value(latest.get("overall_reliability_score"), decimals=1))
        c3.metric("Fontes", int(latest.get("sources_checked") or 0))
        c4.metric("Warnings", int(latest.get("warning_count") or 0))
        c5.metric("Missing/Erro", int((latest.get("missing_count") or 0) + (latest.get("error_count") or 0)))
        st.dataframe(audit_runs, use_container_width=True, hide_index=True)

    st.markdown("#### Confiabilidade por fonte")
    if audit_results.empty:
        st.warning("Sem resultados detalhados para o ultimo run.")
    else:
        filters = st.columns(4)
        source_types = ["Todos"] + sorted(audit_results["source_type"].dropna().astype(str).unique().tolist())
        statuses = ["Todos"] + sorted(audit_results["status"].dropna().astype(str).unique().tolist())
        origins = ["Todos"] + sorted(audit_results["primary_or_secondary"].dropna().astype(str).unique().tolist())
        source_type = filters[0].selectbox("Tipo", source_types, key="data_audit_source_type")
        status = filters[1].selectbox("Status", statuses, key="data_audit_status")
        origin = filters[2].selectbox("Origem", origins, key="data_audit_origin")
        only_primary = filters[3].checkbox("Apenas primárias", value=False, key="data_audit_primary")
        view = audit_results.copy()
        if source_type != "Todos":
            view = view[view["source_type"].astype(str) == source_type]
        if status != "Todos":
            view = view[view["status"].astype(str) == status]
        if origin != "Todos":
            view = view[view["primary_or_secondary"].astype(str) == origin]
        if only_primary:
            view = view[view["primary_or_secondary"].astype(str).str.upper() == "PRIMARY"]
        cols = [
            "source_name",
            "source_type",
            "primary_or_secondary",
            "status",
            "reliability_score",
            "reliability_class",
            "latest_date",
            "records_count",
            "tickers_count",
            "coverage_scope",
            "message",
        ]
        st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True, hide_index=True)
        if "reliability_score" in view.columns and not view.empty:
            chart = view.set_index("source_name")["reliability_score"].apply(pd.to_numeric, errors="coerce")
            st.bar_chart(chart)
        _csv_download("Baixar auditoria de dados", view, "data_source_audit_results.csv")

    st.markdown("#### Rastreabilidade por ticker/fonte")
    if traceability.empty:
        st.info("Sem registros de rastreabilidade salvos.")
    else:
        st.dataframe(traceability, use_container_width=True, hide_index=True)
        _csv_download("Baixar rastreabilidade", traceability, "data_source_traceability.csv")

    st.markdown("#### Reconciliação de Fontes")
    reconciliation_runs = reconciliation_runs if reconciliation_runs is not None else pd.DataFrame()
    reconciliation_results = reconciliation_results if reconciliation_results is not None else pd.DataFrame()
    if reconciliation_runs.empty and reconciliation_results.empty:
        st.info("Nenhuma reconciliação salva. Rode:")
        st.code("python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv")
    else:
        if not reconciliation_runs.empty:
            last = reconciliation_runs.iloc[0]
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Último status", last.get("status", "-"))
            r2.metric("Issues", int(last.get("issues_count") or 0))
            r3.metric("Fixes sugeridos", int(last.get("fixes_suggested_count") or 0))
            r4.metric("Fixes executados", int(last.get("fixes_executed_count") or 0))
            st.dataframe(reconciliation_runs, use_container_width=True, hide_index=True)
        if not reconciliation_results.empty:
            cols = ["source_domain", "issue_type", "severity", "status", "description", "suggested_command", "executed", "execution_status"]
            st.dataframe(reconciliation_results[[c for c in cols if c in reconciliation_results.columns]], use_container_width=True, hide_index=True)
            _csv_download("Baixar reconciliação", reconciliation_results, "data_reconciliation_results.csv")

    st.markdown("#### Manifesto de Arquivos")
    manifest_runs = manifest_runs if manifest_runs is not None else pd.DataFrame()
    manifest = manifest if manifest is not None else pd.DataFrame()
    if manifest_runs.empty and manifest.empty:
        st.caption("Nenhum manifesto salvo ainda.")
    else:
        if not manifest_runs.empty:
            st.dataframe(manifest_runs, use_container_width=True, hide_index=True)
        if not manifest.empty:
            cols = ["source_domain", "file_name", "extension", "size_bytes", "modified_at", "checksum", "file_path"]
            st.dataframe(manifest[[c for c in cols if c in manifest.columns]], use_container_width=True, hide_index=True)

    st.markdown("#### Assistente de Ingestão")
    ingestion_runs = ingestion_runs if ingestion_runs is not None else pd.DataFrame()
    ingestion_steps = ingestion_steps if ingestion_steps is not None else pd.DataFrame()
    ingestion_validation = ingestion_validation if ingestion_validation is not None else pd.DataFrame()
    ingestion_comparison = ingestion_comparison if ingestion_comparison is not None else pd.DataFrame()
    if ingestion_runs.empty and ingestion_steps.empty:
        st.info("Nenhum run do assistente salvo. Rode:")
        st.code("python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv")
    else:
        if not ingestion_runs.empty:
            last = ingestion_runs.iloc[0]
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Status", last.get("status", "-"))
            a2.metric("Etapas", int(last.get("steps_total") or 0))
            a3.metric("Executadas", int(last.get("steps_executed") or 0))
            a4.metric("Melhorias", int(last.get("improvements_count") or 0))
            st.dataframe(ingestion_runs, use_container_width=True, hide_index=True)
        if not ingestion_steps.empty:
            cols = ["step_order", "source_domain", "step_type", "title", "suggested_command", "risk_level", "status"]
            st.dataframe(ingestion_steps[[c for c in cols if c in ingestion_steps.columns]], use_container_width=True, hide_index=True)
        if not ingestion_validation.empty:
            st.markdown("##### Validação pós-processamento")
            st.dataframe(ingestion_validation, use_container_width=True, hide_index=True)
        if not ingestion_comparison.empty:
            st.markdown("##### Comparação antes/depois")
            st.dataframe(ingestion_comparison, use_container_width=True, hide_index=True)


def _tab_sla_observability(
    source_sla_snapshots: pd.DataFrame,
    observability_snapshots: pd.DataFrame,
    source_health: pd.DataFrame,
    event_coverage_runs: pd.DataFrame,
    event_coverage_by_regime: pd.DataFrame,
    all_alerts: pd.DataFrame,
    daily_runs: pd.DataFrame,
    retention_runs: pd.DataFrame,
    retention_details: pd.DataFrame,
) -> None:
    st.subheader("SLA & Observabilidade")
    if source_sla_snapshots.empty and source_health.empty and observability_snapshots.empty:
        st.warning("Ainda não há histórico suficiente de SLA/observabilidade.")
        st.code("python -m src.scanners.source_health_check --save-db --csv")
        st.code(
            "python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 "
            "--with-regimes --with-event-context --with-governance --save-db --csv"
        )
        st.code("python -m src.scanners.operational_observability --window-days 30 --save-db --csv")
        return

    latest_obs = observability_snapshots.iloc[0] if not observability_snapshots.empty else {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status geral", latest_obs.get("overall_status", "-") if hasattr(latest_obs, "get") else "-")
    c2.metric("Disponibilidade média", _metric_value(latest_obs.get("overall_availability_pct") if hasattr(latest_obs, "get") else None, "%"))
    c3.metric("Fontes críticas", int(latest_obs.get("critical_sources") or 0) if hasattr(latest_obs, "get") else 0)
    c4.metric("Alertas abertos", int(latest_obs.get("open_alerts") or 0) if hasattr(latest_obs, "get") else 0)

    st.subheader("SLA por fonte")
    sla_view = source_sla_snapshots.copy()
    if sla_view.empty and not source_health.empty:
        sla_view = calculate_source_sla(source_health, window_days=30)
    if sla_view.empty:
        st.info("Sem snapshots de SLA por fonte. Rode operational_observability com --save-db.")
    else:
        cols = [
            c
            for c in [
                "created_at",
                "source_name",
                "availability_pct",
                "reliability_class",
                "latest_status",
                "days_since_last_ok",
                "total_checks",
                "avg_age_days",
            ]
            if c in sla_view.columns
        ]
        st.dataframe(sla_view[cols].head(50), use_container_width=True, hide_index=True)
        if "reliability_class" in sla_view.columns:
            st.bar_chart(sla_view["reliability_class"].value_counts())

    st.subheader("Histórico de checks")
    if source_health.empty:
        st.info("Sem health checks salvos.")
    else:
        st.dataframe(source_health, use_container_width=True, hide_index=True)
        if "status" in source_health.columns:
            st.bar_chart(source_health["status"].value_counts())

    st.subheader("Tendência de cobertura de eventos")
    coverage_trend = calculate_event_coverage_trend(event_coverage_runs)
    if coverage_trend.empty:
        st.info("Sem histórico de cobertura de eventos.")
    else:
        st.dataframe(coverage_trend, use_container_width=True, hide_index=True)
        st.line_chart(coverage_trend.set_index("period")[["avg_signals_with_event_pct", "avg_tickers_with_event_pct"]])

    st.subheader("Cobertura por regime")
    regime_trend = calculate_regime_coverage_trend(event_coverage_by_regime)
    if regime_trend.empty:
        st.info("Sem histórico de cobertura por regime.")
    else:
        st.dataframe(regime_trend, use_container_width=True, hide_index=True)
        if "avg_coverage_pct" in regime_trend.columns:
            labels = regime_trend["regime_type"].astype(str) + "=" + regime_trend["regime_value"].astype(str)
            st.bar_chart(regime_trend.assign(regime=labels).set_index("regime")["avg_coverage_pct"])

    st.subheader("Alertas recorrentes")
    recurring = detect_recurring_alerts(all_alerts, min_occurrences=3)
    if recurring.empty:
        st.success("Sem alertas recorrentes na amostra carregada.")
    else:
        st.warning("Há alertas recorrentes que merecem tratamento operacional.")
        st.dataframe(recurring, use_container_width=True, hide_index=True)

    st.subheader("Rotina diária")
    routine_summary = summarize_daily_routine_runs(daily_runs, window_days=30)
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Saúde da rotina", routine_summary.get("routine_health_status") or "-")
    c6.metric("Taxa de sucesso", _metric_value(routine_summary.get("success_rate_pct"), "%"))
    c7.metric("Média de alertas", _metric_value(routine_summary.get("avg_alerts_count"), decimals=1))
    c8.metric("Cobertura média", _metric_value(float(routine_summary.get("avg_signals_covered_pct") or 0) * 100, "%"))
    if daily_runs.empty:
        st.info("Sem execuções da rotina diária.")
    else:
        st.dataframe(daily_runs, use_container_width=True, hide_index=True)

    st.subheader("Snapshots de observabilidade")
    if observability_snapshots.empty:
        st.info("Sem snapshots de observabilidade operacional.")
        st.code("python -m src.scanners.operational_observability --window-days 30 --save-db --csv")
    else:
        st.dataframe(observability_snapshots, use_container_width=True, hide_index=True)

    st.subheader("Retenção")
    if retention_runs.empty:
        st.info("Nenhuma limpeza de retenção registrada.")
        st.code("python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv")
    else:
        latest = retention_runs.iloc[0]
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Modo", "DRY-RUN" if int(latest.get("dry_run") or 0) else "EXECUTE")
        r2.metric("Linhas candidatas", int(latest.get("rows_candidates") or 0))
        r3.metric("Arquivadas", int(latest.get("rows_archived") or 0))
        r4.metric("Deletadas", int(latest.get("rows_deleted") or 0))
        st.dataframe(retention_runs, use_container_width=True, hide_index=True)
        if not retention_details.empty:
            st.dataframe(retention_details, use_container_width=True, hide_index=True)

    st.subheader("Contratos de Qualidade")
    contracts = evaluate_source_contracts(source_health, event_coverage_runs, load_source_quality_contracts())
    if contracts.empty:
        st.info("Nenhum contrato de qualidade avaliado.")
    else:
        st.dataframe(contracts, use_container_width=True, hide_index=True)
        if "contract_status" in contracts.columns:
            st.bar_chart(contracts["contract_status"].value_counts())

    st.subheader("Relatório Semanal")
    reports_dir = project_path("data/reports")
    reports = sorted(reports_dir.glob("weekly_operational_report_*.md")) if reports_dir.exists() else []
    if not reports:
        st.info("Nenhum relatório semanal encontrado.")
        st.code("python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv")
    else:
        latest_report = reports[-1]
        st.write(str(latest_report))
        preview = latest_report.read_text(encoding="utf-8", errors="ignore")[:2000]
        st.markdown(preview)


def _tab_raw(runs, results, calibration_runs, calibration_assets, wf_runs, wf_results, filter_runs, threshold_runs, filter_wf_runs, filter_wf_results, governance_reviews, regimes, regime_summary, events, event_links, event_runs, event_coverage_runs, event_coverage_by_regime, option_runs, option_chain, option_structures, option_backtest_runs, option_backtest_results, option_wf_runs, option_wf_results, option_context_summary, technical_features, technical_setups, technical_bt_runs, technical_bt_results, technical_wf_runs, technical_wf_results, technical_threshold_runs, technical_dedup_runs, daily_runs, source_health, open_alerts, source_sla_snapshots, observability_snapshots, retention_runs, retention_details, asset_intelligence=None, asset_diffs=None, data_audit_runs=None, data_audit_results=None, data_traceability=None, data_reconciliation_runs=None, data_reconciliation_results=None, data_manifest_runs=None, data_manifest=None, ingestion_runs=None, ingestion_steps=None, ingestion_validation=None, ingestion_comparison=None) -> None:
    tables = {
        "historical_backtest_runs": runs,
        "historical_backtest_results": results,
        "score_calibration_runs": calibration_runs,
        "score_calibration_assets": calibration_assets,
        "walk_forward_runs": wf_runs,
        "walk_forward_results": wf_results,
        "quality_filter_runs": filter_runs,
        "threshold_optimization_runs": threshold_runs,
        "filter_walk_forward_runs": filter_wf_runs,
        "filter_walk_forward_results": filter_wf_results,
        "governance_reviews": governance_reviews,
        "market_regime_daily": regimes,
        "regime_backtest_summary": regime_summary,
        "market_events": events,
        "signal_event_links": event_links,
        "event_context_runs": event_runs,
        "event_coverage_runs": event_coverage_runs,
        "event_coverage_by_regime": event_coverage_by_regime,
        "option_scanner_runs": option_runs,
        "options_chain_snapshots": option_chain,
        "option_structure_candidates": option_structures,
        "option_structure_backtest_runs": option_backtest_runs,
        "option_structure_backtest_results": option_backtest_results,
        "option_walk_forward_runs": option_wf_runs,
        "option_walk_forward_results": option_wf_results,
        "option_context_summary": option_context_summary,
        "technical_feature_snapshots": technical_features,
        "technical_setup_signals": technical_setups,
        "technical_backtest_runs": technical_bt_runs,
        "technical_backtest_results": technical_bt_results,
        "technical_walk_forward_runs": technical_wf_runs,
        "technical_walk_forward_results": technical_wf_results,
        "technical_threshold_optimization_runs": technical_threshold_runs,
        "technical_setup_dedup_runs": technical_dedup_runs,
        "daily_routine_runs": daily_runs,
        "source_health_checks": source_health,
        "operational_alerts": open_alerts,
        "source_sla_snapshots": source_sla_snapshots,
        "operational_observability_snapshots": observability_snapshots,
        "retention_cleanup_runs": retention_runs,
        "retention_cleanup_details": retention_details,
        "asset_intelligence_snapshots": asset_intelligence if asset_intelligence is not None else pd.DataFrame(),
        "asset_intelligence_diffs": asset_diffs if asset_diffs is not None else pd.DataFrame(),
        "data_source_audit_runs": data_audit_runs if data_audit_runs is not None else pd.DataFrame(),
        "data_source_audit_results": data_audit_results if data_audit_results is not None else pd.DataFrame(),
        "data_source_traceability": data_traceability if data_traceability is not None else pd.DataFrame(),
        "data_reconciliation_runs": data_reconciliation_runs if data_reconciliation_runs is not None else pd.DataFrame(),
        "data_reconciliation_results": data_reconciliation_results if data_reconciliation_results is not None else pd.DataFrame(),
        "data_file_manifest_runs": data_manifest_runs if data_manifest_runs is not None else pd.DataFrame(),
        "data_file_manifest": data_manifest if data_manifest is not None else pd.DataFrame(),
        "ingestion_assistant_runs": ingestion_runs if ingestion_runs is not None else pd.DataFrame(),
        "ingestion_assistant_steps": ingestion_steps if ingestion_steps is not None else pd.DataFrame(),
        "post_ingestion_validation_results": ingestion_validation if ingestion_validation is not None else pd.DataFrame(),
        "ingestion_reliability_comparison": ingestion_comparison if ingestion_comparison is not None else pd.DataFrame(),
    }
    for name, df in tables.items():
        st.subheader(name)
        st.dataframe(df, use_container_width=True, hide_index=True)
        _csv_download(f"Baixar {name}", df, f"{name}.csv")


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit nao esta instalado.")

    _render_header()
    cfg = load_config()
    db_path = project_path(cfg["database_path"])

    with st.sidebar:
        st.header("Fonte")
        st.write(str(db_path))
        st.caption("Gere dados com --save-calibration e --save-db antes de abrir a mesa.")

    latest_run = load_latest_backtest_run(db_path)
    runs = load_backtest_runs(db_path)
    results = load_backtest_results(db_path, run_id=int(latest_run.iloc[0]["id"])) if not latest_run.empty else load_backtest_results(db_path)
    calibration_runs = load_calibration_runs_for_dashboard(db_path)
    latest_calibration_id = int(calibration_runs.iloc[0]["id"]) if not calibration_runs.empty else None
    calibration_assets = load_calibration_assets_for_dashboard(db_path, run_id=latest_calibration_id)
    history = load_score_distribution_history_for_dashboard(db_path)
    signal_summary = load_signal_summary_for_dashboard(db_path)
    bucket_summary = load_score_bucket_summary_for_dashboard(db_path)
    component_summary = load_component_summary_for_dashboard(db_path)
    net_summary = load_net_summary_for_dashboard(db_path)
    quality_summary = load_execution_quality_summary_for_dashboard(db_path)
    filter_runs = load_quality_filter_runs_for_dashboard(db_path)
    threshold_runs = load_threshold_optimization_runs_for_dashboard(db_path)
    capacity_summary = load_capacity_summary_for_dashboard(db_path)
    filter_wf_runs = load_filter_walk_forward_runs_for_dashboard(db_path)
    latest_filter_wf_id = int(filter_wf_runs.iloc[0]["id"]) if not filter_wf_runs.empty else None
    filter_wf_results = load_filter_walk_forward_results_for_dashboard(db_path, run_id=latest_filter_wf_id)
    governance_reviews = load_governance_reviews_for_dashboard(db_path)
    governance_summary = load_governance_summary_for_dashboard(db_path)
    regimes = load_market_regimes_for_dashboard(db_path)
    regime_summary = load_regime_backtest_summary_for_dashboard(db_path)
    events = load_market_events_for_dashboard(db_path)
    event_links = load_signal_event_links_for_dashboard(db_path)
    event_runs = load_event_context_runs_for_dashboard(db_path)
    event_coverage_runs = load_event_coverage_runs_for_dashboard(db_path)
    latest_event_coverage_id = int(event_coverage_runs.iloc[0]["id"]) if not event_coverage_runs.empty else None
    event_coverage_by_regime = load_event_coverage_by_regime_for_dashboard(db_path, coverage_run_id=latest_event_coverage_id)
    event_summary = load_event_context_summary_for_dashboard(db_path)
    option_runs = load_option_scanner_runs_for_dashboard(db_path)
    option_chain = load_options_chain_snapshots_for_dashboard(db_path)
    option_structures = load_option_structure_candidates_for_dashboard(db_path)
    option_backtest_runs = load_option_structure_backtest_runs_for_dashboard(db_path)
    latest_option_bt_id = int(option_backtest_runs.iloc[0]["id"]) if not option_backtest_runs.empty else None
    option_backtest_results = load_option_structure_backtest_results_for_dashboard(db_path, run_id=latest_option_bt_id)
    option_wf_runs = load_option_walk_forward_runs_for_dashboard(db_path)
    latest_option_wf_id = int(option_wf_runs.iloc[0]["id"]) if not option_wf_runs.empty else None
    option_wf_results = load_option_walk_forward_results_for_dashboard(db_path, run_id=latest_option_wf_id)
    option_context_summary = load_option_context_summary_for_dashboard(db_path, run_id=latest_option_wf_id)
    technical_features = load_technical_features_for_dashboard(db_path)
    technical_setups = load_technical_setups_for_dashboard(db_path)
    technical_bt_runs = load_technical_backtest_runs_for_dashboard(db_path)
    latest_technical_bt_id = int(technical_bt_runs.iloc[0]["id"]) if not technical_bt_runs.empty else None
    technical_bt_results = load_technical_backtest_results_for_dashboard(db_path, run_id=latest_technical_bt_id)
    technical_wf_runs = load_technical_walk_forward_runs_for_dashboard(db_path)
    latest_technical_wf_id = int(technical_wf_runs.iloc[0]["id"]) if not technical_wf_runs.empty else None
    technical_wf_results = load_technical_walk_forward_results_for_dashboard(db_path, run_id=latest_technical_wf_id)
    technical_threshold_runs = load_technical_threshold_runs_for_dashboard(db_path)
    technical_dedup_runs = load_technical_dedup_runs_for_dashboard(db_path)
    asset_intelligence = load_asset_intelligence_snapshots_for_dashboard(db_path)
    asset_diffs = load_asset_intelligence_diffs_for_dashboard(db_path)
    data_audit_runs = load_data_source_audit_runs_for_dashboard(db_path)
    latest_data_audit_id = int(data_audit_runs.iloc[0]["id"]) if not data_audit_runs.empty else None
    data_audit_results = load_data_source_audit_results_for_dashboard(db_path, run_id=latest_data_audit_id)
    data_traceability = load_data_source_traceability_for_dashboard(db_path)
    data_reconciliation_runs = load_data_reconciliation_runs_for_dashboard(db_path)
    latest_reconciliation_id = int(data_reconciliation_runs.iloc[0]["id"]) if not data_reconciliation_runs.empty else None
    data_reconciliation_results = load_data_reconciliation_results_for_dashboard(db_path, run_id=latest_reconciliation_id)
    data_manifest_runs = load_data_file_manifest_runs_for_dashboard(db_path)
    data_manifest = load_data_file_manifest_for_dashboard(db_path)
    ingestion_runs = load_ingestion_assistant_runs_for_dashboard(db_path)
    latest_ingestion_id = int(ingestion_runs.iloc[0]["id"]) if not ingestion_runs.empty else None
    ingestion_steps = load_ingestion_assistant_steps_for_dashboard(db_path, run_id=latest_ingestion_id)
    ingestion_validation = load_post_ingestion_validation_for_dashboard(db_path, run_id=latest_ingestion_id)
    ingestion_comparison = load_ingestion_comparison_for_dashboard(db_path, run_id=latest_ingestion_id)
    risk_snapshots = load_risk_snapshots_for_dashboard(db_path)
    volatility_estimates = load_volatility_estimates_for_dashboard(db_path)
    position_sizing = load_position_sizing_for_dashboard(db_path)
    stress_tests = load_stress_tests_for_dashboard(db_path)
    paper_runs = load_paper_simulation_runs_for_dashboard(db_path)
    latest_paper_id = int(paper_runs.iloc[0]["id"]) if not paper_runs.empty else None
    paper_orders = load_paper_orders_for_dashboard(db_path, run_id=latest_paper_id)
    paper_positions = load_paper_positions_for_dashboard(db_path, run_id=latest_paper_id)
    paper_equity = load_paper_equity_curve_for_dashboard(db_path, run_id=latest_paper_id)
    paper_exit_events = load_paper_exit_events_for_dashboard(db_path, run_id=latest_paper_id)
    paper_rebalance_events = load_paper_rebalance_events_for_dashboard(db_path, run_id=latest_paper_id)
    paper_pnl_attribution = load_paper_pnl_attribution_for_dashboard(db_path, run_id=latest_paper_id)
    paper_comparisons = load_paper_simulation_comparisons_for_dashboard(db_path)
    paper_wf_runs = load_paper_walk_forward_runs_for_dashboard(db_path)
    latest_paper_wf_id = int(paper_wf_runs.iloc[0]["id"]) if not paper_wf_runs.empty else None
    paper_wf_results = load_paper_walk_forward_results_for_dashboard(db_path, run_id=latest_paper_wf_id)
    paper_opt_runs = load_paper_exit_optimization_runs_for_dashboard(db_path)
    latest_paper_opt_id = int(paper_opt_runs.iloc[0]["id"]) if not paper_opt_runs.empty else None
    paper_opt_results = load_paper_exit_optimization_results_for_dashboard(db_path, run_id=latest_paper_opt_id)
    paper_scenario_runs = load_paper_scenario_validation_runs_for_dashboard(db_path)
    latest_paper_scenario_id = int(paper_scenario_runs.iloc[0]["id"]) if not paper_scenario_runs.empty else None
    paper_scenario_results = load_paper_scenario_validation_results_for_dashboard(db_path, run_id=latest_paper_scenario_id)
    paper_cost_sensitivity = load_paper_cost_sensitivity_for_dashboard(db_path, run_id=latest_paper_scenario_id)
    paper_signal_sources = load_paper_signal_source_comparison_for_dashboard(db_path, run_id=latest_paper_scenario_id)
    paper_fragility_runs = load_paper_fragility_runs_for_dashboard(db_path)
    latest_paper_fragility_id = int(paper_fragility_runs.iloc[0]["id"]) if not paper_fragility_runs.empty else None
    paper_fragility_assets = load_paper_fragility_by_asset_for_dashboard(db_path, run_id=latest_paper_fragility_id)
    paper_fragility_sources = load_paper_fragility_by_signal_source_for_dashboard(db_path, run_id=latest_paper_fragility_id)
    paper_drawdown_periods = load_paper_drawdown_periods_for_dashboard(db_path, run_id=latest_paper_fragility_id)
    paper_investigation_runs = load_paper_investigation_runs_for_dashboard(db_path)
    latest_paper_investigation_id = int(paper_investigation_runs.iloc[0]["id"]) if not paper_investigation_runs.empty else None
    paper_investigation_results = load_paper_investigation_results_for_dashboard(db_path, run_id=latest_paper_investigation_id)
    paper_hypothesis_oos_runs = load_paper_hypothesis_oos_runs_for_dashboard(db_path)
    latest_hypothesis_oos_id = int(paper_hypothesis_oos_runs.iloc[0]["id"]) if not paper_hypothesis_oos_runs.empty else None
    paper_hypothesis_oos_results = load_paper_hypothesis_oos_results_for_dashboard(db_path, run_id=latest_hypothesis_oos_id)
    paper_hypothesis_oos_coverage = load_paper_hypothesis_oos_coverage_for_dashboard(db_path, run_id=latest_hypothesis_oos_id)
    hypothesis_ranking_runs = load_paper_hypothesis_ranking_runs_for_dashboard(db_path)
    latest_hypothesis_ranking_id = int(hypothesis_ranking_runs.iloc[0]["id"]) if not hypothesis_ranking_runs.empty else None
    hypothesis_ranking_results = load_paper_hypothesis_ranking_results_for_dashboard(db_path, run_id=latest_hypothesis_ranking_id)
    hypothesis_deep_runs = load_paper_hypothesis_deep_oos_runs_for_dashboard(db_path)
    latest_hypothesis_deep_id = int(hypothesis_deep_runs.iloc[0]["id"]) if not hypothesis_deep_runs.empty else None
    hypothesis_deep_results = load_paper_hypothesis_deep_oos_results_for_dashboard(db_path, run_id=latest_hypothesis_deep_id)
    hypothesis_block_reasons = load_paper_hypothesis_block_reasons_for_dashboard(db_path, run_id=latest_hypothesis_deep_id)
    signal_coverage_runs = load_signal_coverage_runs_for_dashboard(db_path)
    latest_signal_coverage_id = int(signal_coverage_runs.iloc[0]["id"]) if not signal_coverage_runs.empty else None
    signal_coverage_by_source = load_signal_coverage_by_source_for_dashboard(db_path, run_id=latest_signal_coverage_id)
    daily_runs = load_daily_routine_runs_for_dashboard(db_path)
    source_health = load_source_health_checks_for_dashboard(db_path)
    open_alerts = load_operational_alerts_for_dashboard(db_path)
    all_alerts = load_operational_alerts_for_dashboard(db_path, open_only=False)
    source_sla_snapshots = load_source_sla_snapshots_for_dashboard(db_path)
    observability_snapshots = load_observability_snapshots_for_dashboard(db_path)
    retention_runs = load_retention_cleanup_runs_for_dashboard(db_path)
    latest_retention_id = int(retention_runs.iloc[0]["id"]) if not retention_runs.empty else None
    retention_details = load_retention_cleanup_details_for_dashboard(db_path, run_id=latest_retention_id)
    wf_runs = load_walk_forward_runs_for_dashboard(db_path)
    latest_wf_id = int(wf_runs.iloc[0]["id"]) if not wf_runs.empty else None
    wf_results = load_walk_forward_results_for_dashboard(db_path, run_id=latest_wf_id)

    tabs = st.tabs(
        [
            "Visão Geral",
            "Backtest Histórico",
            "Score & Calibração",
            "Sinais por Ativo",
            "Componentes do Score",
            "Walk-forward / Fora da Amostra",
            "Filtros & Capacidade",
            "Regimes de Mercado",
            "Eventos & Notícias",
            "Opções Inteligentes",
            "Análise Técnica Quant",
            "Inteligência Integrada",
            "Risco & Volatilidade",
            "Paper Trading",
            "Auditoria de Dados",
            "Operação & Saúde das Fontes",
            "SLA & Observabilidade",
            "Governança Quant",
            "Alertas e Diagnóstico",
            "Dados Brutos",
        ]
    )

    with tabs[0]:
        _tab_overview(latest_run, signal_summary, bucket_summary, calibration_runs, results, net_summary)
    with tabs[1]:
        _tab_backtest(db_path, runs, signal_summary, bucket_summary, quality_summary)
    with tabs[2]:
        _tab_calibration(calibration_runs, calibration_assets, history)
    with tabs[3]:
        _tab_asset(results)
    with tabs[4]:
        _tab_components(results, calibration_assets, component_summary)
    with tabs[5]:
        _tab_walk_forward(wf_runs, wf_results)
    with tabs[6]:
        _tab_filters_capacity(filter_runs, threshold_runs, capacity_summary, results, filter_wf_runs, filter_wf_results)
    with tabs[7]:
        _tab_regimes(regimes, regime_summary, governance_reviews)
    with tabs[8]:
        _tab_events(events, event_links, event_runs, event_coverage_runs, event_coverage_by_regime, event_summary, results, governance_reviews)
    with tabs[9]:
        _tab_options_intelligence(option_runs, option_chain, option_structures, option_backtest_runs, option_backtest_results, option_wf_runs, option_wf_results, option_context_summary)
    with tabs[10]:
        _tab_technical_quant(technical_features, technical_setups, technical_bt_runs, technical_bt_results, technical_wf_runs, technical_wf_results, technical_threshold_runs, technical_dedup_runs)
    with tabs[11]:
        _tab_asset_intelligence(asset_intelligence, asset_diffs)
    with tabs[12]:
        _tab_risk_volatility(risk_snapshots, volatility_estimates, position_sizing, stress_tests)
    with tabs[13]:
        _tab_paper_trading(
            paper_runs,
            paper_orders,
            paper_positions,
            paper_equity,
            paper_exit_events,
            paper_rebalance_events,
            paper_pnl_attribution,
            paper_comparisons,
            paper_opt_runs,
            paper_opt_results,
            paper_wf_runs,
            paper_wf_results,
            paper_scenario_runs,
            paper_scenario_results,
            paper_cost_sensitivity,
            paper_signal_sources,
            paper_fragility_runs,
            paper_fragility_assets,
            paper_fragility_sources,
            paper_drawdown_periods,
            paper_investigation_runs,
            paper_investigation_results,
            paper_hypothesis_oos_runs,
            paper_hypothesis_oos_results,
            paper_hypothesis_oos_coverage,
            signal_coverage_runs,
            signal_coverage_by_source,
            hypothesis_ranking_runs,
            hypothesis_ranking_results,
            hypothesis_deep_runs,
            hypothesis_deep_results,
            hypothesis_block_reasons,
        )
    with tabs[14]:
        _tab_data_audit(data_audit_runs, data_audit_results, data_traceability, data_reconciliation_runs, data_reconciliation_results, data_manifest_runs, data_manifest, ingestion_runs, ingestion_steps, ingestion_validation, ingestion_comparison)
    with tabs[15]:
        _tab_operation(daily_runs, source_health, open_alerts)
    with tabs[16]:
        _tab_sla_observability(source_sla_snapshots, observability_snapshots, source_health, event_coverage_runs, event_coverage_by_regime, all_alerts, daily_runs, retention_runs, retention_details)
    with tabs[17]:
        _tab_governance(governance_reviews, governance_summary)
    with tabs[18]:
        _tab_alerts(runs, results, calibration_runs, calibration_assets, bucket_summary, net_summary)
    with tabs[19]:
        _tab_raw(runs, results, calibration_runs, calibration_assets, wf_runs, wf_results, filter_runs, threshold_runs, filter_wf_runs, filter_wf_results, governance_reviews, regimes, regime_summary, events, event_links, event_runs, event_coverage_runs, event_coverage_by_regime, option_runs, option_chain, option_structures, option_backtest_runs, option_backtest_results, option_wf_runs, option_wf_results, option_context_summary, technical_features, technical_setups, technical_bt_runs, technical_bt_results, technical_wf_runs, technical_wf_results, technical_threshold_runs, technical_dedup_runs, daily_runs, source_health, open_alerts, source_sla_snapshots, observability_snapshots, retention_runs, retention_details, asset_intelligence, asset_diffs, data_audit_runs, data_audit_results, data_traceability, data_reconciliation_runs, data_reconciliation_results, data_manifest_runs, data_manifest, ingestion_runs, ingestion_steps, ingestion_validation, ingestion_comparison)


if __name__ == "__main__":
    main()
