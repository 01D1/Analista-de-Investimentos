"""CLI do Risk Engine institucional.

Gera estimativas analiticas de volatilidade, VaR, Expected Shortfall, sizing
sugerido para estudo e stress tests. Nao executa ordens nem altera ranking.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.db.init_db import init_database
from src.risk.expected_shortfall import calculate_historical_expected_shortfall
from src.risk.position_sizing import calculate_final_position_size
from src.risk.risk_explanations import explain_risk_governance, explain_sizing, explain_var, explain_volatility
from src.risk.risk_governance import evaluate_risk_snapshot
from src.risk.risk_store import (
    save_position_sizing_snapshots,
    save_risk_governance_reviews,
    save_risk_snapshots,
    save_stress_test_results,
    save_var_estimates,
    save_volatility_estimates,
)
from src.risk.stress_testing import run_single_asset_stress
from src.risk.var_models import calculate_historical_var, calculate_modified_var, calculate_parametric_var
from src.risk.volatility_models import calculate_volatility_features
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame, stem: str) -> Path | None:
    if df is None or df.empty:
        return None
    path = _reports_dir() / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _available_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _load_price_history(
    db_path: str | Path,
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    db = Path(db_path)
    columns = ["trade_date", "ticker", "open", "high", "low", "close", "volume", "trades"]
    if not db.exists():
        return pd.DataFrame(columns=columns)
    tables = ["cotahist_daily", "b3_quotes", "market_daily"]
    with sqlite3.connect(db) as con:
        selected = next((table for table in tables if _table_exists(con, table)), None)
        if selected is None:
            return pd.DataFrame(columns=columns)
        available = _available_columns(con, selected)
        required = {"trade_date", "ticker", "close"}
        if not required.issubset(available):
            return pd.DataFrame(columns=columns)
        select_expr = [
            "trade_date",
            "ticker",
            "open" if "open" in available else "close AS open",
            "high" if "high" in available else "close AS high",
            "low" if "low" in available else "close AS low",
            "close",
            "volume" if "volume" in available else "NULL AS volume",
            "trades" if "trades" in available else "NULL AS trades",
        ]
        where = []
        params: list[object] = []
        if tickers:
            allowed = [str(t).upper() for t in tickers]
            where.append(f"UPPER(ticker) IN ({','.join(['?'] * len(allowed))})")
            params.extend(allowed)
        if start:
            where.append("trade_date >= ?")
            params.append(start)
        if end:
            where.append("trade_date <= ?")
            params.append(end)
        sql = f"SELECT {', '.join(select_expr)} FROM {selected}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ticker, trade_date"
        df = pd.read_sql_query(sql, con, params=params)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in ["open", "high", "low", "close", "volume", "trades"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df = df.dropna(subset=["trade_date", "ticker", "close"]).copy()
    return df[columns]


def _latest_financial_volume(history: pd.DataFrame) -> float | None:
    volume = pd.to_numeric(history.get("volume"), errors="coerce")
    close = pd.to_numeric(history.get("close"), errors="coerce")
    if volume.notna().any():
        avg_volume = float(volume.tail(20).mean())
        if avg_volume > 0:
            # Em COTAHIST local o campo volume costuma representar volume financeiro.
            return avg_volume
    avg_close = float(close.tail(20).mean()) if close.notna().any() else np.nan
    return avg_close * 10_000 if pd.notna(avg_close) else None


def _build_for_ticker(
    ticker: str,
    history: pd.DataFrame,
    capital: float,
    risk_pct: float,
    var_limit_pct: float,
    confidence: float,
) -> dict[str, pd.DataFrame]:
    created_at = datetime.utcnow().isoformat(timespec="seconds")
    hist = history.sort_values("trade_date").copy()
    vol_df = calculate_volatility_features(hist).copy()
    vol_df["created_at"] = created_at
    vol_df["metadata_json"] = json.dumps({"source": "risk_engine_snapshot"}, ensure_ascii=False)
    vol_cols = [
        "created_at",
        "trade_date",
        "ticker",
        "vol_5d",
        "vol_10d",
        "vol_20d",
        "vol_60d",
        "vol_252d",
        "vol_ewma",
        "downside_vol",
        "parkinson_vol",
        "garman_klass_vol",
        "atr_vol",
        "ensemble_vol",
        "volatility_regime",
        "metadata_json",
    ]
    latest_vol = vol_df.tail(1)[vol_cols].copy()
    latest = hist.iloc[-1]
    latest_vol_row = vol_df.iloc[-1]
    price = float(latest["close"])
    trade_date = str(latest["trade_date"])
    returns = pd.to_numeric(hist["close"], errors="coerce").pct_change().dropna()
    ensemble_vol = pd.to_numeric(pd.Series([latest_vol_row.get("ensemble_vol")]), errors="coerce").iloc[0]
    atr_pct = pd.to_numeric(pd.Series([latest_vol_row.get("atr_vol")]), errors="coerce").iloc[0]
    atr = float(atr_pct * price) if pd.notna(atr_pct) else None
    avg_financial_volume = _latest_financial_volume(hist)
    stop_price = price - (2 * atr) if atr and atr > 0 else price * 0.95

    sizing = calculate_final_position_size(
        capital=capital,
        risk_pct=risk_pct,
        entry_price=price,
        stop_price=stop_price,
        atr=atr,
        volatility=float(ensemble_vol) if pd.notna(ensemble_vol) else None,
        avg_financial_volume=avg_financial_volume,
        var_limit_pct=var_limit_pct,
        confidence=confidence,
    )
    position_value = float(sizing.get("final_position_value") or 0)
    param_var = calculate_parametric_var(position_value, ensemble_vol, confidence=confidence)
    hist_var = calculate_historical_var(returns, position_value, confidence=confidence)
    mod_var = calculate_modified_var(returns, position_value, confidence=confidence)
    es = calculate_historical_expected_shortfall(returns, position_value, confidence=confidence)

    risk_basis = {
        "ticker": ticker,
        "price": price,
        "position_value": position_value,
        "ensemble_vol": ensemble_vol,
        "volatility_regime": latest_vol_row.get("volatility_regime"),
        "parametric_var_95": param_var.get("parametric_var"),
        "historical_var_95": hist_var.get("historical_var"),
        "expected_shortfall_95": es.get("expected_shortfall"),
        "recommended_size": sizing.get("final_size"),
        "recommended_position_value": position_value,
        "limiting_factor": sizing.get("limiting_factor"),
    }
    governance = evaluate_risk_snapshot(risk_basis)
    risk_basis["risk_status"] = governance["risk_status"]
    risk_basis["explanation"] = " ".join(
        [
            explain_volatility(risk_basis),
            explain_var(risk_basis),
            explain_sizing({**risk_basis, "risk_limiting_factor": sizing.get("limiting_factor")}),
            explain_risk_governance(governance),
        ]
    )
    risk_basis["metadata_json"] = json.dumps(
        {
            "confidence": confidence,
            "var_limit_pct": var_limit_pct,
            "sizing_notes": sizing.get("notes"),
            "var_diagnostics": {
                "parametric": param_var.get("diagnostic_message"),
                "historical": hist_var.get("diagnostic_message"),
                "modified": mod_var.get("diagnostic_message"),
                "expected_shortfall": es.get("diagnostic_message"),
            },
        },
        ensure_ascii=False,
    )
    risk_snapshots = pd.DataFrame([{**{"created_at": created_at, "trade_date": trade_date}, **risk_basis}])

    var_estimates = pd.DataFrame(
        [
            {
                "created_at": created_at,
                "trade_date": trade_date,
                "ticker": ticker,
                "position_value": position_value,
                "confidence": confidence,
                "horizon_days": 1,
                "parametric_var": param_var.get("parametric_var"),
                "historical_var": hist_var.get("historical_var"),
                "modified_var": mod_var.get("modified_var"),
                "expected_shortfall": es.get("expected_shortfall"),
                "metadata_json": risk_basis["metadata_json"],
            }
        ]
    )
    sizing_snapshots = pd.DataFrame(
        [
            {
                "created_at": created_at,
                "trade_date": trade_date,
                "ticker": ticker,
                "capital": capital,
                "risk_pct": risk_pct,
                "entry_price": price,
                "stop_price": stop_price,
                "atr": atr,
                "volatility": ensemble_vol,
                "avg_financial_volume": avg_financial_volume,
                "size_fixed_risk": sizing.get("size_fixed_risk"),
                "size_atr": sizing.get("size_atr"),
                "size_var": sizing.get("size_var"),
                "size_liquidity": sizing.get("size_liquidity"),
                "final_size": sizing.get("final_size"),
                "final_position_value": sizing.get("final_position_value"),
                "limiting_factor": sizing.get("limiting_factor"),
                "estimated_var": sizing.get("estimated_var"),
                "metadata_json": json.dumps({"notes": sizing.get("notes")}, ensure_ascii=False),
            }
        ]
    )
    stress = run_single_asset_stress(position_value)
    stress["created_at"] = created_at
    stress["ticker"] = ticker
    stress["position_value"] = position_value
    stress["metadata_json"] = stress["notes"].map(lambda note: json.dumps({"notes": note}, ensure_ascii=False))
    stress = stress[["created_at", "ticker", "scenario", "position_value", "estimated_loss", "loss_pct", "metadata_json"]]
    governance_df = pd.DataFrame(
        [
            {
                "created_at": created_at,
                "ticker": ticker,
                "risk_status": governance["risk_status"],
                "risk_level": governance["risk_level"],
                "confidence_level": governance["confidence_level"],
                "reasons_for_json": json.dumps(governance["reasons_for_json"], ensure_ascii=False),
                "reasons_against_json": json.dumps(governance["reasons_against_json"], ensure_ascii=False),
                "required_actions_json": json.dumps(governance["required_actions_json"], ensure_ascii=False),
                "metadata_json": json.dumps({"source": "risk_engine_snapshot"}, ensure_ascii=False),
            }
        ]
    )
    return {
        "volatility": latest_vol,
        "risk": risk_snapshots,
        "var": var_estimates,
        "sizing": sizing_snapshots,
        "stress": stress,
        "governance": governance_df,
    }


def run(
    tickers: list[str] | None,
    start: str | None = None,
    end: str | None = None,
    capital: float = 100_000,
    risk_pct: float = 0.005,
    var_limit_pct: float = 0.01,
    confidence: float = 0.95,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    ticker_list = [str(t).upper() for t in (tickers or [])]
    history = _load_price_history(db, ticker_list or None, start, end)
    frames = {key: [] for key in ["volatility", "risk", "var", "sizing", "stress", "governance"]}
    diagnostics = []
    if history.empty:
        diagnostics.append("Dados insuficientes: não foi encontrado histórico diário de preços para os filtros informados.")
    for ticker, group in history.groupby("ticker"):
        if len(group) < 20:
            diagnostics.append(f"{ticker}: dados insuficientes para modelos de risco com amostra mínima.")
            continue
        built = _build_for_ticker(ticker, group, capital, risk_pct, var_limit_pct, confidence)
        for key, df in built.items():
            frames[key].append(df)
    outputs = {key: pd.concat(value, ignore_index=True) if value else pd.DataFrame() for key, value in frames.items()}
    saved = {}
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved = {
            "volatility": save_volatility_estimates(db, outputs["volatility"]),
            "risk": save_risk_snapshots(db, outputs["risk"]),
            "var": save_var_estimates(db, outputs["var"]),
            "sizing": save_position_sizing_snapshots(db, outputs["sizing"]),
            "stress": save_stress_test_results(db, outputs["stress"]),
            "governance": save_risk_governance_reviews(db, outputs["governance"]),
        }
    csv_paths = {}
    if csv:
        csv_paths = {
            "risk": str(_write_csv(outputs["risk"], "risk_snapshots") or ""),
            "volatility": str(_write_csv(outputs["volatility"], "volatility_estimates") or ""),
            "sizing": str(_write_csv(outputs["sizing"], "position_sizing") or ""),
            "stress": str(_write_csv(outputs["stress"], "stress_tests") or ""),
        }
    return {
        "tickers_analyzed": int(outputs["risk"]["ticker"].nunique()) if not outputs["risk"].empty else 0,
        "risk_blocked": int(outputs["risk"]["risk_status"].astype(str).str.contains("BLOCKED", na=False).sum()) if not outputs["risk"].empty else 0,
        "diagnostics": diagnostics,
        "saved": saved,
        "csv_paths": csv_paths,
        "dry_run": dry_run,
        "outputs": outputs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera snapshot analitico de risco, volatilidade, VaR, ES e sizing.")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--capital", type=float, default=100_000)
    parser.add_argument("--risk-pct", type=float, default=0.005)
    parser.add_argument("--var-limit-pct", type=float, default=0.01)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(
        tickers=args.tickers,
        start=args.start,
        end=args.end,
        capital=args.capital,
        risk_pct=args.risk_pct,
        var_limit_pct=args.var_limit_pct,
        confidence=args.confidence,
        save_db=args.save_db,
        csv=args.csv,
        dry_run=args.dry_run,
    )
    print("RISK ENGINE SNAPSHOT")
    print(f"Ativos analisados: {summary['tickers_analyzed']}")
    print(f"Bloqueados por risco: {summary['risk_blocked']}")
    print(f"Dry-run: {summary['dry_run']}")
    if summary["diagnostics"]:
        print("Diagnosticos:")
        for item in summary["diagnostics"]:
            print(f"- {item}")
    if summary["saved"]:
        print(f"Linhas salvas: {summary['saved']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    if summary["tickers_analyzed"] == 0:
        print("Nenhum snapshot de risco foi gerado; verifique a cobertura historica de preços.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
