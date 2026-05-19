"""
quant_dashboard_data.py
-----------------------
Camada de dados para a Mesa Quant Institucional.

Todas as funções são decoradas com cache condicional (st.cache_data quando
Streamlit disponível, identidade caso contrário). TTL padrão: 300s.

Consultas leves, limite de linhas, tratamento de tabela ausente.
Não faz recomendação financeira. Uso interno de pesquisa e auditoria.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from src.reports.editorial_store import (
    load_latest_editorial_review,
    load_weekly_report_diffs,
)
from src.reports.editorial_workflow import EditorialReview
from src.utils.logger import get_logger

log = get_logger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "reports" / "radar_macro_weekly"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "ingestion.db"


# ---------------------------------------------------------------------------
# Cache helper — funciona com ou sem Streamlit
# ---------------------------------------------------------------------------

def _cache(ttl: int = 300):
    """Decorator fábrica: usa st.cache_data se disponível, senão identidade."""
    try:
        import streamlit as st
        return st.cache_data(ttl=ttl)
    except ImportError:
        def _identity(fn):
            return fn
        return _identity


def _query(sql: str, params: tuple = (), limit: int = 500) -> pd.DataFrame:
    """Executa query no banco local com limite de linhas e tratamento de erro."""
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchmany(limit)
        conn.close()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        log.warning(f"[quant_data] query error: {e}")
        return pd.DataFrame()


def _table_exists(table: str) -> bool:
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name=?",
            (table,),
        )
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Editorial
# ---------------------------------------------------------------------------

@_cache(300)
def get_latest_editorial_review(report_id: Optional[str] = None) -> Optional[EditorialReview]:
    """Retorna a revisão editorial mais recente."""
    try:
        return load_latest_editorial_review(report_id=report_id)
    except Exception as e:
        log.warning(f"[quant_data] erro ao carregar revisão editorial: {e}")
        return None


@_cache(300)
def get_latest_weekly_diff(report_id: Optional[str] = None) -> pd.DataFrame:
    """Retorna o diff semanal mais recente como DataFrame."""
    try:
        return load_weekly_report_diffs(current_report_id=report_id, limit=50)
    except Exception as e:
        log.warning(f"[quant_data] erro ao carregar diff semanal: {e}")
        return pd.DataFrame()


def get_editorial_status_summary(review: Optional[EditorialReview]) -> dict:
    """Retorna resumo do status editorial para exibição no dashboard."""
    if not review:
        return {
            "status": "SEM_REVISAO",
            "label": "Sem revisão editorial",
            "color": "gray",
            "command_hint": "python -m src.scanners.editorial_review --latest-report --create-review --save-db",
        }

    status_map = {
        "DRAFT": ("Rascunho", "gray"),
        "PENDING_REVIEW": ("Revisão humana pendente", "orange"),
        "APPROVED_FOR_INTERNAL_USE": ("Aprovado para uso interno", "blue"),
        "APPROVED_FOR_DISTRIBUTION": ("Aprovado para distribuição", "green"),
        "BLOCKED_DATA_QUALITY": ("Bloqueado — dados insuficientes", "red"),
        "BLOCKED_GOVERNANCE": ("Bloqueado — governança", "red"),
        "REJECTED": ("Rejeitado", "red"),
        "ARCHIVED": ("Arquivado", "gray"),
    }
    label, color = status_map.get(review.status.value, (review.status.value, "gray"))
    return {
        "status": review.status.value,
        "label": label,
        "color": color,
        "report_id": review.report_id,
        "reviewer": review.reviewer,
        "reviewed_at": review.reviewed_at,
        "comments": review.comments,
        "approval_level": review.approval_level,
        "command_hint": None,
    }


@_cache(300)
def get_diff_summary_text(diff_df: pd.DataFrame) -> str:
    """Retorna resumo narrativo do diff para exibição."""
    if diff_df.empty:
        return "Nenhuma comparação semanal disponível."
    try:
        from src.reports.weekly_report_diff import generate_weekly_diff_summary
        return generate_weekly_diff_summary(diff_df)
    except Exception as e:
        return f"Erro ao gerar resumo: {e}"


def get_material_changes(diff_df: pd.DataFrame) -> pd.DataFrame:
    """Filtra apenas as mudanças materiais do diff."""
    if diff_df.empty:
        return pd.DataFrame()
    return diff_df[diff_df["material_change"] == True].copy()  # noqa: E712


# ---------------------------------------------------------------------------
# Pipeline Semanal
# ---------------------------------------------------------------------------

@_cache(300)
def get_latest_pipeline_run() -> Optional[dict]:
    """Retorna o run mais recente do pipeline semanal."""
    try:
        from src.pipeline.weekly_pipeline_store import load_latest_weekly_pipeline_run
        return load_latest_weekly_pipeline_run()
    except Exception as e:
        log.warning(f"[quant_data] erro ao carregar pipeline run: {e}")
        return None


@_cache(300)
def get_pipeline_steps(run_db_id: str) -> pd.DataFrame:
    """Retorna as etapas do run especificado."""
    try:
        from src.pipeline.weekly_pipeline_store import load_weekly_pipeline_steps
        return load_weekly_pipeline_steps(run_db_id)
    except Exception as e:
        log.warning(f"[quant_data] erro ao carregar steps: {e}")
        return pd.DataFrame()


def get_pipeline_run_summary(run: Optional[dict]) -> dict:
    """Retorna resumo do pipeline run para exibição no dashboard."""
    if not run:
        return {
            "status": "SEM_DADOS",
            "label": "Nenhum pipeline executado",
            "color": "gray",
            "command_hint": (
                "python -m src.scanners.run_weekly_pipeline "
                "--start 2026-01-02 --end 2026-04-30 "
                "--tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --reports"
            ),
        }
    status = run.get("status", "UNKNOWN")
    color_map = {"SUCCESS": "green", "COMPLETED_WITH_FAILURES": "orange", "RUNNING": "blue", "UNKNOWN": "gray"}
    label_map = {
        "SUCCESS": "Concluído com sucesso",
        "COMPLETED_WITH_FAILURES": "Concluído com falhas",
        "RUNNING": "Em execução",
        "UNKNOWN": "Desconhecido",
    }
    return {
        "status": status,
        "label": label_map.get(status, status),
        "color": color_map.get(status, "gray"),
        "run_id": run.get("id", ""),
        "started_at": run.get("started_at", ""),
        "finished_at": run.get("finished_at", ""),
        "steps_total": run.get("steps_total", 0),
        "steps_success": run.get("steps_success", 0),
        "steps_warning": run.get("steps_warning", 0),
        "steps_failed": run.get("steps_failed", 0),
        "report_id": run.get("report_id"),
        "command_hint": None,
    }


# ---------------------------------------------------------------------------
# Home / Visão Executiva
# ---------------------------------------------------------------------------

@_cache(120)
def get_data_health() -> dict:
    """Verifica existência e volume das tabelas principais."""
    tables = [
        "thesis_versions", "thesis_latest",
        "financial_dcf", "financial_multiples", "financial_ltm",
        "macro_series", "opportunity_signals", "news_articles",
        "weekly_pipeline_runs", "weekly_pipeline_steps",
        "editorial_reviews", "weekly_report_diffs",
    ]
    health = {}
    for t in tables:
        if _table_exists(t):
            df = _query(f"SELECT COUNT(*) AS n FROM {t}", limit=1)  # noqa
            count = int(df["n"].iloc[0]) if not df.empty else 0
            health[t] = {"exists": True, "rows": count, "status": "OK" if count > 0 else "SEM_DADOS"}
        else:
            health[t] = {"exists": False, "rows": 0, "status": "NOT_RUN"}
    return health


@_cache(300)
def get_assets_count() -> dict:
    """Retorna contagem de ativos com teses geradas."""
    df = _query(
        "SELECT COUNT(DISTINCT ticker) AS n FROM thesis_versions",
        limit=1,
    )
    total = int(df["n"].iloc[0]) if not df.empty else 0

    df2 = _query(
        "SELECT COUNT(DISTINCT ticker) AS n FROM thesis_versions WHERE input_hash IS NOT NULL",
        limit=1,
    )
    with_hash = int(df2["n"].iloc[0]) if not df2.empty else 0

    return {"total": total, "with_hash": with_hash}


@_cache(300)
def get_recent_tickers(limit: int = 20) -> list[str]:
    """Retorna lista de tickers mais recentemente atualizados."""
    df = _query(
        "SELECT DISTINCT ticker FROM thesis_versions ORDER BY generated_at DESC",
        limit=limit,
    )
    return list(df["ticker"]) if not df.empty else []


@_cache(300)
def get_command_last_runs() -> dict[str, str]:
    """Retorna última execução conhecida de cada comando principal."""
    results: dict[str, str] = {}

    # Pipeline
    run = get_latest_pipeline_run()
    if run:
        results["weekly_pipeline"] = run.get("started_at", "—")
    else:
        results["weekly_pipeline"] = "NOT_RUN"

    # Editorial
    review = get_latest_editorial_review()
    if review:
        results["editorial_review"] = review.created_at or "—"
    else:
        results["editorial_review"] = "NOT_RUN"

    return results


@_cache(300)
def get_governance_blockers() -> pd.DataFrame:
    """Retorna ativos ou relatórios com bloqueio de governança."""
    try:
        from src.reports.editorial_store import load_editorial_reviews_by_status
        blocked = []
        for s in ("BLOCKED_DATA_QUALITY", "BLOCKED_GOVERNANCE"):
            try:
                rows = load_editorial_reviews_by_status(s)
                if rows:
                    blocked.extend(rows)
            except Exception:
                pass
        if not blocked:
            return pd.DataFrame()
        return pd.DataFrame([
            {
                "report_id": r.report_id,
                "status": r.status.value,
                "created_at": r.created_at,
                "reviewer": r.reviewer or "—",
            }
            for r in blocked
        ])
    except Exception as e:
        log.warning(f"[quant_data] get_governance_blockers: {e}")
        return pd.DataFrame()


@_cache(300)
def get_weekly_reports_list(limit: int = 20) -> pd.DataFrame:
    """Lista relatórios semanais disponíveis no diretório de output."""
    try:
        files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)[:limit]
        rows = []
        for f in files:
            stat = f.stat()
            rows.append({
                "arquivo": f.name,
                "caminho": str(f),
                "tamanho_kb": round(stat.st_size / 1024, 1),
                "modificado": pd.Timestamp(stat.st_mtime, unit="s").strftime("%Y-%m-%d %H:%M"),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        log.warning(f"[quant_data] get_weekly_reports_list: {e}")
        return pd.DataFrame()


@_cache(300)
def get_paper_trading_summary() -> pd.DataFrame:
    """Retorna runs de paper trading. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["paper_trading_runs", "pt_runs", "backtests"]
    for t in candidates:
        if _table_exists(t):
            return _query(f"SELECT * FROM {t} ORDER BY started_at DESC", limit=50)  # noqa
    return pd.DataFrame()


@_cache(300)
def get_technical_summary() -> pd.DataFrame:
    """Retorna análise técnica. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["technical_signals", "technical_analysis", "quant_signals"]
    for t in candidates:
        if _table_exists(t):
            return _query(f"SELECT * FROM {t} ORDER BY computed_date DESC", limit=200)  # noqa
    return pd.DataFrame()


@_cache(300)
def get_risk_summary() -> pd.DataFrame:
    """Retorna sumário do Risk Engine. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["risk_metrics", "risk_engine_runs", "asset_risk"]
    for t in candidates:
        if _table_exists(t):
            return _query(f"SELECT * FROM {t} ORDER BY computed_date DESC", limit=200)  # noqa
    return pd.DataFrame()


@_cache(300)
def get_options_summary() -> pd.DataFrame:
    """Retorna análise de opções. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["options_signals", "options_analysis", "smart_options"]
    for t in candidates:
        if _table_exists(t):
            return _query(f"SELECT * FROM {t} ORDER BY computed_date DESC", limit=200)  # noqa
    return pd.DataFrame()


@_cache(300)
def get_scanner_summary() -> pd.DataFrame:
    """Retorna sinais do scanner quantitativo. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["opportunity_signals", "scanner_signals", "quant_scanner"]
    for t in candidates:
        if _table_exists(t):
            return _query(f"SELECT * FROM {t} ORDER BY computed_date DESC", limit=200)  # noqa
    return pd.DataFrame()


@_cache(300)
def get_integrated_intelligence() -> pd.DataFrame:
    """Retorna visão integrada por ativo. Retorna DataFrame vazio se tabela ausente."""
    candidates = ["asset_intelligence", "integrated_analysis", "thesis_latest"]
    for t in candidates:
        if _table_exists(t):
            return _query(
                f"SELECT ticker, positioning, confidence, fair_value_brl, generated_at FROM {t} ORDER BY generated_at DESC",  # noqa
                limit=200,
            )
    return pd.DataFrame()
