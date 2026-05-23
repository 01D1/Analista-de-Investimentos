"""Valuation connector — bridge to pipeline banco completo (reference only).

Pipeline banco completo (12_PYTHON/pipeline banco completo/data/valuation.db):
  STATUS: catalogado, não integrado ao PYTHONPATH do app.
  USE CASE: referência para auditoria de valuation, não para consumo pelo app.
  149 tickers cubiertos. Bancos usam COSIF-adjusted DCF (tipo_empresa=bank).

  ┌──────────────────────────────────────────────────────────────┐
  │  Fonte canônica de valuation = scanner_quant.db             │
  │  Pipeline banco completo = referência, não integrado         │
  └──────────────────────────────────────────────────────────────┘

This module provides read-only access to the pipeline valuation.db
without modifying sys.path globally. Imports are lazy to avoid
breaking the app if the external vault is unavailable.

Usage:
    from src.dashboard.valuation_connector import get_pipeline_valuation

    # Returns None if vault unavailable (graceful fallback)
    v = get_pipeline_valuation("PETR4")
    if v:
        print(f"Pipeline: fair_value={v['preco_justo_on']}, source=PIPELINE")
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


# Lazily resolve vault path — avoids import errors when vault is offline
_VAULT_PIPELINE_BASE: Path | None = None


def _resolve_vault_pipeline() -> Path | None:
    """Walk up from this file's location to find the vault containing 12_PYTHON."""
    global _VAULT_PIPELINE_BASE
    if _VAULT_PIPELINE_BASE is not None:
        return _VAULT_PIPELINE_BASE

    candidates = [
        # OneDrive vault
        Path.home() / "Library/CloudStorage/OneDrive-EPEJUD/DIEGO/OBSIDIAN/Analista de Investimentos/12_PYTHON/pipeline banco completo",
        # Fallback: check relative to this file
    ]

    for candidate in candidates:
        db_path = candidate / "data" / "valuation.db"
        if db_path.exists():
            _VAULT_PIPELINE_BASE = candidate
            return candidate

    _VAULT_PIPELINE_BASE = None  # mark resolved even if not found
    return None


def get_pipeline_valuation(ticker: str) -> dict[str, Any] | None:
    """Get latest valuation from pipeline banco completo for a ticker.

    Args:
        ticker: Ticker symbol, e.g. "PETR4", "ITUB4".

    Returns:
        Dict with pipeline fields or None if vault unavailable.
        Fields: ticker, preco_atual, preco_justo_on, preco_justo_pn, upside_on,
                score, recomendacao, tipo_empresa, timestamp, run_id.
        Plus decoded valuation_json as nested dict.
    """
    vault = _resolve_vault_pipeline()
    if vault is None:
        return None

    db_path = vault / "data" / "valuation.db"
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT ticker, preco_atual, preco_justo_on, preco_justo_pn,
                   upside_on, tir_on, score, recomendacao, tipo_empresa,
                   timestamp, run_id, valuation_json
            FROM valuations
            WHERE ticker = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (str(ticker).upper(),),
        ).fetchone()
        conn.close()

        if row is None:
            return None

        result = dict(row)

        # Decode valuation_json if present
        if result.get("valuation_json"):
            try:
                result["valuation_json_decoded"] = json.loads(result["valuation_json"])
            except Exception:
                result["valuation_json_decoded"] = None

        # Convert None strings to proper None
        for key in list(result.keys()):
            if isinstance(result[key], str) and result[key] == "None":
                result[key] = None

        return result

    except Exception:
        return None


def get_pipeline_valuation_summary() -> dict[str, Any]:
    """Get summary of the pipeline valuation database.

    Returns:
        Dict with: count, tickers (list), banks (list), latest_run, status.
        status: "available" | "vault_offline" | "db_missing"
    """
    vault = _resolve_vault_pipeline()
    if vault is None:
        return {"status": "vault_offline", "count": 0, "tickers": [], "banks": [], "latest_run": None}

    db_path = vault / "data" / "valuation.db"
    if not db_path.exists():
        return {"status": "db_missing", "count": 0, "tickers": [], "banks": [], "latest_run": None}

    try:
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM valuations").fetchone()[0]
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM valuations ORDER BY ticker"
        ).fetchall()]
        banks = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM valuations WHERE tipo_empresa = 'bank' ORDER BY ticker"
        ).fetchall()]
        latest = conn.execute(
            "SELECT MAX(timestamp) FROM valuations"
        ).fetchone()[0]
        conn.close()
        return {
            "status": "available",
            "count": count,
            "tickers": tickers,
            "banks": banks,
            "latest_run": latest,
        }
    except Exception:
        return {"status": "error", "count": 0, "tickers": [], "banks": [], "latest_run": None}


def compare_valuation(ticker: str) -> dict[str, Any] | None:
    """Compare valuation between scanner_quant.db and pipeline banco completo.

    Args:
        ticker: Ticker symbol.

    Returns:
        Dict with both valuations and a divergence explanation, or None if
        pipeline is unavailable.

    Known divergences:
      PETR4: scanner_quant=81.12 (upside_pct=71.2%), pipeline=98.56 (upside_on=90.3%)
        → Different DCF assumptions: WACC, terminal growth, FCFF projections.
        → Pipeline 2026-05-19 run used different commodity price assumptions.
        → scanner_quant.db fair_value from build_asset_intelligence_snapshot, 2026-05-22.
      ITUB4: scanner_quant=73.69, pipeline=69.79
        → scanner_quant uses simpler DCF; pipeline uses COSIF-adjusted DCF for banks.
        → Both are valid but use different methodologies.
    """
    from src.dashboard.data import _db_path

    # Get app valuation
    try:
        db = _db_path()
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT ticker, fair_value, upside_pct, integrated_score, created_at
            FROM asset_intelligence_snapshots
            WHERE ticker = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (str(ticker).upper(),),
        ).fetchone()
        conn.close()
        app_val = dict(row) if row else None
    except Exception:
        app_val = None

    # Get pipeline valuation
    pipe_val = get_pipeline_valuation(ticker)
    if pipe_val is None:
        return None

    # Build comparison
    app_fv = app_val.get("fair_value") if app_val else None
    app_upside = app_val.get("upside_pct") if app_val else None
    pipe_fv = pipe_val.get("preco_justo_on")
    pipe_upside = pipe_val.get("upside_on")

    divergence_pct = None
    divergence_note = ""
    if app_fv and pipe_fv and app_fv != 0:
        divergence_pct = round((pipe_fv - app_fv) / app_fv * 100, 1)
        divergence_note = (
            f"Pipeline uses pipeline banco completo DCF (may differ from scanner_quant "
            f"methodology). App uses asset_intelligence_engine output. "
            f"Diferença: {abs(divergence_pct):.1f}%"
        )

    return {
        "ticker": ticker.upper(),
        "app": {
            "fair_value": app_fv,
            "upside_pct": app_upside,
            "integrated_score": app_val.get("integrated_score") if app_val else None,
            "timestamp": app_val.get("created_at") if app_val else None,
            "source": "scanner_quant.db asset_intelligence_snapshots",
        },
        "pipeline": {
            "fair_value": pipe_fv,
            "upside_pct": pipe_upside,
            "score": pipe_val.get("score"),
            "recomendacao": pipe_val.get("recomendacao"),
            "tipo_empresa": pipe_val.get("tipo_empresa"),
            "timestamp": pipe_val.get("timestamp"),
            "source": "12_PYTHON/pipeline banco completo/data/valuation.db",
        },
        "divergence_pct": divergence_pct,
        "divergence_note": divergence_note,
    }