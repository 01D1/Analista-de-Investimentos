"""Mesa Quant em Streamlit para backtest, calibracao e diagnostico."""
from __future__ import annotations

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
    load_capacity_summary_for_dashboard,
    load_backtest_results,
    load_backtest_runs,
    load_calibration_assets_for_dashboard,
    load_calibration_runs_for_dashboard,
    load_component_summary_for_dashboard,
    load_daily_routine_runs_for_dashboard,
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
    load_quality_filter_runs_for_dashboard,
    load_market_regimes_for_dashboard,
    load_regime_backtest_summary_for_dashboard,
    load_retention_cleanup_details_for_dashboard,
    load_retention_cleanup_runs_for_dashboard,
    load_signal_event_links_for_dashboard,
    load_score_bucket_summary_for_dashboard,
    load_score_distribution_history_for_dashboard,
    load_signal_summary_for_dashboard,
    load_source_health_checks_for_dashboard,
    load_source_sla_snapshots_for_dashboard,
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


def _tab_raw(runs, results, calibration_runs, calibration_assets, wf_runs, wf_results, filter_runs, threshold_runs, filter_wf_runs, filter_wf_results, governance_reviews, regimes, regime_summary, events, event_links, event_runs, event_coverage_runs, event_coverage_by_regime, daily_runs, source_health, open_alerts, source_sla_snapshots, observability_snapshots, retention_runs, retention_details) -> None:
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
        "daily_routine_runs": daily_runs,
        "source_health_checks": source_health,
        "operational_alerts": open_alerts,
        "source_sla_snapshots": source_sla_snapshots,
        "operational_observability_snapshots": observability_snapshots,
        "retention_cleanup_runs": retention_runs,
        "retention_cleanup_details": retention_details,
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
        _tab_operation(daily_runs, source_health, open_alerts)
    with tabs[10]:
        _tab_sla_observability(source_sla_snapshots, observability_snapshots, source_health, event_coverage_runs, event_coverage_by_regime, all_alerts, daily_runs, retention_runs, retention_details)
    with tabs[11]:
        _tab_governance(governance_reviews, governance_summary)
    with tabs[12]:
        _tab_alerts(runs, results, calibration_runs, calibration_assets, bucket_summary, net_summary)
    with tabs[13]:
        _tab_raw(runs, results, calibration_runs, calibration_assets, wf_runs, wf_results, filter_runs, threshold_runs, filter_wf_runs, filter_wf_results, governance_reviews, regimes, regime_summary, events, event_links, event_runs, event_coverage_runs, event_coverage_by_regime, daily_runs, source_health, open_alerts, source_sla_snapshots, observability_snapshots, retention_runs, retention_details)


if __name__ == "__main__":
    main()
