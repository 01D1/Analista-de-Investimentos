"""Auditoria dos dados de opcoes persistidos no banco."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.data_quality.source_inventory import make_audit_row, table_exists
from src.utils import load_config, project_path


def audit_options_data(db_path: str | Path | None = None) -> dict:
    cfg = load_config()
    path = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    if not path.exists():
        return make_audit_row(source_name="options_chain", source_type="OPTIONS", primary_or_secondary="DERIVED", expected_path_or_url=str(path), status="MISSING", message="Banco principal nao encontrado.")
    try:
        with sqlite3.connect(path) as con:
            if not table_exists(con, "options_chain_snapshots"):
                return make_audit_row(source_name="options_chain", source_type="OPTIONS", primary_or_secondary="DERIVED", expected_path_or_url=str(path), available=True, status="MISSING", message="Tabela options_chain_snapshots ausente.")
            count, latest, underlyings, maturities = con.execute(
                "SELECT COUNT(*), MAX(COALESCE(trade_date, captured_at)), COUNT(DISTINCT underlying), COUNT(DISTINCT maturity_date) FROM options_chain_snapshots"
            ).fetchone()
            count = int(count or 0)
            bidask = int(con.execute("SELECT COUNT(*) FROM options_chain_snapshots WHERE bid IS NOT NULL AND ask IS NOT NULL AND ask >= bid").fetchone()[0] or 0)
            liquid = int(con.execute("SELECT COUNT(*) FROM options_chain_snapshots WHERE COALESCE(volume, 0) > 0 OR COALESCE(trades, 0) > 0").fetchone()[0] or 0)
            underlyings_list = [r[0] for r in con.execute("SELECT DISTINCT underlying FROM options_chain_snapshots WHERE underlying IS NOT NULL LIMIT 200").fetchall()]
            structures = int(con.execute("SELECT COUNT(*) FROM option_structure_candidates").fetchone()[0] or 0) if table_exists(con, "option_structure_candidates") else 0
            scanner_runs = int(con.execute("SELECT COUNT(*) FROM option_scanner_runs").fetchone()[0] or 0) if table_exists(con, "option_scanner_runs") else 0
            backtest_runs = int(con.execute("SELECT COUNT(*) FROM option_structure_backtest_runs").fetchone()[0] or 0) if table_exists(con, "option_structure_backtest_runs") else 0
            wf_runs = int(con.execute("SELECT COUNT(*) FROM option_walk_forward_runs").fetchone()[0] or 0) if table_exists(con, "option_walk_forward_runs") else 0
        bidask_pct = (bidask / count * 100) if count else 0.0
        liquid_pct = (liquid / count * 100) if count else 0.0
        if count == 0:
            coverage = "SEM_DADOS"
            status = "EMPTY"
        elif count < 100 or bidask_pct < 50:
            coverage = "COBERTURA_FRACA"
            status = "WARNING"
        elif count < 1000:
            coverage = "COBERTURA_MEDIA"
            status = "OK"
        else:
            coverage = "COBERTURA_BOA"
            status = "OK"
        return {
            **make_audit_row(
                source_name="options_chain",
                source_type="OPTIONS",
                primary_or_secondary="DERIVED",
                expected_path_or_url=str(path),
                available=True,
                records_count=count,
                latest_date=str(latest or "")[:10],
                tickers_count=int(underlyings or 0),
                coverage_scope="options_snapshots_structures_backtests",
                status=status,
                message=f"{count} snapshots de cadeia; cobertura historica {coverage}.",
                metadata={"underlyings": underlyings_list, "maturities_count": int(maturities or 0), "bid_ask_coverage_pct": bidask_pct, "liquidity_coverage_pct": liquid_pct, "structures_count": structures, "scanner_runs": scanner_runs, "backtest_runs": backtest_runs, "walk_forward_runs": wf_runs},
            ),
            "snapshots_count": count,
            "underlyings_count": int(underlyings or 0),
            "maturities_count": int(maturities or 0),
            "latest_snapshot_date": str(latest or "")[:10],
            "bid_ask_coverage_pct": bidask_pct,
            "liquidity_coverage_pct": liquid_pct,
            "historical_coverage_status": coverage,
        }
    except Exception as exc:
        return make_audit_row(source_name="options_chain", source_type="OPTIONS", primary_or_secondary="DERIVED", expected_path_or_url=str(path), status="ERROR", message=str(exc))

