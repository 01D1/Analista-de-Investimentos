"""População histórica de snapshots integrados por ativo."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_engine import calculate_data_quality_score, calculate_integrated_score, classify_integrated_status
from src.integration.asset_intelligence_model import normalize_asset_intelligence_frame
from src.integration.asset_intelligence_store import save_asset_intelligence_snapshot
from src.integration.integrated_governance import evaluate_integrated_governance
from src.quant.historical_loader import load_daily_prices
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame) -> str:
    path = _reports_dir() / f"populated_asset_intelligence_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return str(path)


def _read(con: sqlite3.Connection, table: str) -> pd.DataFrame:
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
        return pd.DataFrame()
    return pd.read_sql_query(f"SELECT * FROM {table}", con)


def _latest_on_or_before(df: pd.DataFrame, date: str, ticker_col: str = "ticker") -> pd.DataFrame:
    if df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.date.astype(str)
    work = work[work["trade_date"] <= str(date)].copy()
    if work.empty:
        return work
    return work.sort_values([ticker_col, "trade_date"]).groupby(ticker_col, as_index=False).tail(1)


def _build_date_snapshot(
    trade_date: str,
    tickers: list[str],
    prices: pd.DataFrame,
    technical_features: pd.DataFrame,
    technical_setups: pd.DataFrame,
    quant: pd.DataFrame,
    regimes: pd.DataFrame,
    options: pd.DataFrame,
    risk: pd.DataFrame,
) -> pd.DataFrame:
    out = pd.DataFrame({"ticker": [str(t).upper() for t in tickers]})
    day_prices = prices[prices["trade_date"].astype(str) == str(trade_date)][["ticker", "close"]].rename(columns={"close": "market_price"})
    out = out.merge(day_prices, on="ticker", how="left")
    if not technical_features.empty:
        tech = _latest_on_or_before(technical_features, trade_date)
        tech_cols = [c for c in ["ticker", "technical_score_final", "technical_status"] if c in tech.columns]
        out = out.merge(tech[tech_cols], on="ticker", how="left") if tech_cols else out
    if not technical_setups.empty:
        setups = _latest_on_or_before(technical_setups, trade_date)
        if not setups.empty:
            setups = setups.sort_values(["ticker", "setup_score", "setup_confidence"], ascending=[True, False, False]).groupby("ticker", as_index=False).first()
            setups = setups.rename(
                columns={
                    "setup_type": "top_technical_setup",
                    "setup_score": "technical_setup_score",
                    "setup_confidence": "technical_setup_confidence",
                    "governance_status": "technical_governance_status",
                    "explanation": "technical_explanation",
                }
            )
            cols = [c for c in ["ticker", "top_technical_setup", "technical_setup_score", "technical_setup_confidence", "technical_governance_status", "technical_explanation"] if c in setups.columns]
            out = out.merge(setups[cols], on="ticker", how="left")
    if not quant.empty:
        q = _latest_on_or_before(quant, trade_date)
        q = q.rename(columns={"score_final": "quant_score", "signal_type": "quant_signal_type", "signal_confidence": "quant_signal_confidence", "explanation": "quant_explanation"})
        cols = [c for c in ["ticker", "quant_score", "quant_signal_type", "quant_signal_confidence", "quant_explanation"] if c in q.columns]
        out = out.merge(q[cols], on="ticker", how="left") if cols else out
    if not regimes.empty and "trade_date" in regimes.columns:
        reg = regimes[regimes["trade_date"].astype(str) <= str(trade_date)].sort_values("trade_date").tail(1)
        if not reg.empty:
            for col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"]:
                if col in reg.columns:
                    out[col] = reg.iloc[0][col]
            out["regime_governance_status"] = "REGIME_RISK_ELEVATED" if str(out.get("risk_regime", pd.Series([""])).iloc[0]).upper() == "RISCO_ELEVADO" else "REGIME_OK"
    if not options.empty:
        opt = options.copy()
        if "underlying" in opt.columns:
            opt["ticker"] = opt["underlying"].astype(str).str.upper()
        date_col = "created_at" if "created_at" in opt.columns else None
        if date_col:
            opt["trade_date"] = pd.to_datetime(opt[date_col], errors="coerce").dt.date.astype(str)
            opt = _latest_on_or_before(opt, trade_date)
        if not opt.empty:
            opt = opt.rename(columns={"structure_type": "best_option_structure_type"})
            cols = [c for c in ["ticker", "best_option_structure_type", "structure_score", "governance_status", "liquidity_score"] if c in opt.columns]
            opt = opt[cols].rename(columns={"structure_score": "option_structure_score", "governance_status": "option_oos_governance_status", "liquidity_score": "option_liquidity_score"})
            out = out.merge(opt, on="ticker", how="left")
    if not risk.empty:
        r = _latest_on_or_before(risk.rename(columns={"parametric_var_95": "var_95", "limiting_factor": "risk_limiting_factor"}), trade_date)
        cols = [c for c in ["ticker", "ensemble_vol", "var_95", "expected_shortfall_95", "recommended_size", "recommended_position_value", "risk_status", "risk_limiting_factor", "explanation"] if c in r.columns]
        r = r[cols].rename(columns={"explanation": "risk_explanation"}) if cols else pd.DataFrame()
        if not r.empty:
            out = out.merge(r, on="ticker", how="left")
    out["trade_date"] = trade_date
    out["valuation_available"] = False
    out["option_available"] = out.get("best_option_structure_type", pd.Series(index=out.index, dtype=object)).notna()
    out["has_recent_event"] = 0
    out["governance_blocked"] = out.apply(lambda r: any("BLOCKED" in str(r.get(c, "")).upper() or "BLOQUEADO" in str(r.get(c, "")).upper() for c in ["technical_governance_status", "quant_governance_status", "option_oos_governance_status", "risk_status"]), axis=1)
    out["data_quality_score"] = out.apply(calculate_data_quality_score, axis=1)
    out["integrated_score"] = out.apply(calculate_integrated_score, axis=1)
    out["integrated_status"] = out.apply(classify_integrated_status, axis=1)
    governance = out.apply(evaluate_integrated_governance, axis=1)
    out["integrated_governance_status"] = [g["integrated_governance_status"] for g in governance]
    out["integrated_confidence"] = [g["confidence_level"] for g in governance]
    out["explanation"] = out.apply(lambda r: f"População histórica integrada em estudo para {r.get('ticker')} em {trade_date}. Não recomendação.", axis=1)
    out["reasons_for"] = "[]"
    out["reasons_against"] = "[]"
    out["required_actions"] = "[]"
    out["metadata_json"] = out.apply(lambda r: json.dumps({"population_history": True, "data_quality_score": r.get("data_quality_score")}, ensure_ascii=False, default=str), axis=1)
    return normalize_asset_intelligence_frame(out)


def run(
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    include_technical: bool = True,
    include_quant: bool = True,
    include_valuation: bool = True,
    include_events: bool = True,
    include_regimes: bool = True,
    include_options: bool = True,
    include_risk: bool = True,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    prices = load_daily_prices(db, tickers=tickers, start_date=start, end_date=end)
    if prices.empty:
        data = pd.DataFrame()
        diagnostics = [prices.attrs.get("mensagem", "Dados insuficientes para população histórica integrada.")]
    else:
        prices["trade_date"] = prices["trade_date"].astype(str)
        ticker_list = [str(t).upper() for t in (tickers or sorted(prices["ticker"].unique().tolist()))]
        with sqlite3.connect(db) as con:
            technical_features = _read(con, "technical_feature_snapshots") if include_technical else pd.DataFrame()
            technical_setups = _read(con, "technical_setup_signals") if include_technical else pd.DataFrame()
            quant = _read(con, "historical_backtest_results") if include_quant else pd.DataFrame()
            regimes = _read(con, "market_regime_daily") if include_regimes else pd.DataFrame()
            options = _read(con, "option_structure_candidates") if include_options else pd.DataFrame()
            risk = _read(con, "risk_snapshots") if include_risk else pd.DataFrame()
        frames = []
        for date in sorted(prices["trade_date"].dropna().unique().tolist()):
            frames.append(_build_date_snapshot(date, ticker_list, prices, technical_features, technical_setups, quant, regimes, options, risk))
        data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        diagnostics = []
    csv_path = _write_csv(data) if csv and not data.empty else ""
    saved = 0
    if save_db and not dry_run and not data.empty:
        init_database(db, verbose=False)
        with sqlite3.connect(db) as con:
            if start and end and tickers:
                allowed = [str(t).upper() for t in tickers]
                con.execute(
                    f"DELETE FROM asset_intelligence_snapshots WHERE trade_date >= ? AND trade_date <= ? AND UPPER(ticker) IN ({','.join(['?'] * len(allowed))})",
                    [start, end, *allowed],
                )
            con.commit()
        saved = save_asset_intelligence_snapshot(db, data)
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "snapshots_count": int(len(data)),
        "saved_snapshots_count": int(saved),
        "tickers_count": int(data["ticker"].nunique()) if not data.empty else 0,
        "active_days_count": int(data["trade_date"].nunique()) if not data.empty else 0,
        "diagnostics": diagnostics,
        "csv_path": csv_path,
        "data": data,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Popula snapshots integrados históricos para estudo, sem recomendação.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--include-technical", action="store_true", default=True)
    parser.add_argument("--include-quant", action="store_true", default=True)
    parser.add_argument("--include-valuation", action="store_true", default=True)
    parser.add_argument("--include-events", action="store_true", default=True)
    parser.add_argument("--include-regimes", action="store_true", default=True)
    parser.add_argument("--include-options", action="store_true", default=True)
    parser.add_argument("--include-risk", action="store_true", default=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("POPULAÇÃO HISTÓRICA INTEGRATED")
    print("Fonte de sinal em estudo: integrated")
    print(f"Snapshots gerados: {summary['snapshots_count']}")
    print(f"Snapshots integrated persistidos: {summary['saved_snapshots_count']}")
    if summary["diagnostics"]:
        print("Diagnóstico: " + " | ".join(summary["diagnostics"]))
    if summary["csv_path"]:
        print(f"CSV: {summary['csv_path']}")
    print("Não recomendação: rotina apenas popula histórico integrado e valida amostra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

