"""CLI de paper trading/carteira simulada.

Executa apenas simulação. Não envia ordens reais, não altera score e não aplica
estratégia em capital real.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.paper_governance import evaluate_paper_simulation
from src.paper.paper_store import save_paper_simulation_run
from src.paper.simulator import run_paper_simulation
from src.risk.risk_store import load_latest_risk_snapshots
from src.scanners.risk_engine_snapshot import _load_price_history
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


def _load_table(db_path: str | Path, table: str) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, table):
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table}", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _normalize_signals(df: pd.DataFrame, source: str, start: str | None, end: str | None) -> pd.DataFrame:
    if df.empty or "ticker" not in df.columns:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    out = df.copy()
    if "trade_date" not in out.columns:
        out["trade_date"] = start or pd.Timestamp.today().date().isoformat()
    out["trade_date"] = out["trade_date"].astype(str)
    out["ticker"] = out["ticker"].astype(str).str.upper()
    out["signal_source"] = source
    if start:
        out = out[out["trade_date"] >= str(start)]
    if end:
        out = out[out["trade_date"] <= str(end)]
    return out


def load_paper_signals(db_path: str | Path, signal_source: str, start: str | None, end: str | None) -> pd.DataFrame:
    source = signal_source.lower()
    frames = []
    if source in {"integrated", "all"}:
        frames.append(_normalize_signals(_load_table(db_path, "asset_intelligence_snapshots"), "integrated", start, end))
    if source in {"technical", "all"}:
        frames.append(_normalize_signals(_load_table(db_path, "technical_setup_signals"), "technical", start, end))
    if source in {"quant", "all"}:
        frames.append(_normalize_signals(_load_table(db_path, "historical_backtest_results"), "quant", start, end))
    if not frames:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    signals = pd.concat(frames, ignore_index=True)
    if signals.empty:
        return signals
    return signals.sort_values(["trade_date", "ticker"]).drop_duplicates(["trade_date", "ticker", "signal_source"])


def run(
    start: str | None = None,
    end: str | None = None,
    capital: float = 100_000,
    max_positions: int = 5,
    risk_pct: float = 0.005,
    cost_bps: float = 10,
    slippage_bps: float = 5,
    signal_source: str = "integrated",
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
    exit_mode: str = "simple",
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    trailing_stop_pct: float | None = None,
    atr_stop_multiplier: float | None = None,
    daily_loss_limit_pct: float | None = None,
    weekly_loss_limit_pct: float | None = None,
    max_drawdown_pct: float | None = None,
    enable_rebalancing: bool = False,
    rebalance_frequency: str = "WEEKLY",
    use_regime_adjustment: bool = False,
    save_attribution: bool = False,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    signals = load_paper_signals(db, signal_source, start, end)
    tickers = sorted(signals["ticker"].dropna().astype(str).unique().tolist()) if not signals.empty else None
    prices = _load_price_history(db, tickers, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    result = run_paper_simulation(
        signals,
        prices,
        risk_df=risk,
        start_date=start,
        end_date=end,
        capital=capital,
        max_positions=max_positions,
        risk_pct=risk_pct,
        cost_bps=cost_bps,
        slippage_bps=slippage_bps,
        stop_loss_pct=stop_loss_pct if exit_mode == "advanced" else None,
        take_profit_pct=take_profit_pct if exit_mode == "advanced" else None,
        trailing_stop_pct=trailing_stop_pct if exit_mode == "advanced" else None,
        atr_stop_multiplier=atr_stop_multiplier if exit_mode == "advanced" else None,
        daily_loss_limit_pct=daily_loss_limit_pct if exit_mode == "advanced" else None,
        weekly_loss_limit_pct=weekly_loss_limit_pct if exit_mode == "advanced" else None,
        max_drawdown_pct=max_drawdown_pct if exit_mode == "advanced" else None,
        enable_rebalancing=enable_rebalancing,
        rebalance_frequency=rebalance_frequency,
        use_regime_adjustment=use_regime_adjustment,
    )
    summary = result["performance_summary"].copy()
    governance = evaluate_paper_simulation(summary)
    summary["governance_status"] = governance["governance_status"]
    summary["start_date"] = start
    summary["end_date"] = end
    summary["metadata"] = {"signal_source": signal_source, "governance": governance, "dry_run": dry_run, "exit_mode": exit_mode, "enable_rebalancing": enable_rebalancing}
    summary["metadata_json"] = json.dumps(summary["metadata"], ensure_ascii=False)
    saved_run_id = None
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved_run_id = save_paper_simulation_run(
            db,
            summary,
            result["orders_df"],
            result["positions_df"],
            result["equity_curve_df"],
            result.get("exit_events_df"),
            result.get("rebalance_events_df"),
            result.get("pnl_attribution_df") if save_attribution else pd.DataFrame(),
        )
    csv_paths = {}
    if csv:
        csv_paths = {
            "orders": str(_write_csv(result["orders_df"], "paper_orders") or ""),
            "positions": str(_write_csv(result["positions_df"], "paper_positions") or ""),
            "equity": str(_write_csv(result["equity_curve_df"], "paper_equity_curve") or ""),
            "summary": str(_write_csv(pd.DataFrame([summary]), "paper_summary") or ""),
            "exit_events": str(_write_csv(result.get("exit_events_df", pd.DataFrame()), "paper_exit_events") or ""),
            "rebalance_events": str(_write_csv(result.get("rebalance_events_df", pd.DataFrame()), "paper_rebalance_events") or ""),
            "pnl_attribution": str(_write_csv(result.get("pnl_attribution_df", pd.DataFrame()), "paper_pnl_attribution") or ""),
        }
    return {
        "status": summary.get("status", "INSUFFICIENT_DATA"),
        "signals_count": int(len(signals)),
        "orders_count": int(len(result["orders_df"])),
        "trades_count": int(summary.get("trades_count", 0) or 0),
        "capital_final": float(summary.get("capital_final", capital) or capital),
        "governance_status": governance["governance_status"],
        "exit_events_count": int(len(result.get("exit_events_df", pd.DataFrame()))),
        "rebalance_events_count": int(len(result.get("rebalance_events_df", pd.DataFrame()))),
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "result": result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulação de paper trading/carteira simulada.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--capital", type=float, default=100_000)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--risk-pct", type=float, default=0.005)
    parser.add_argument("--cost-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--signal-source", choices=["integrated", "technical", "quant", "all"], default="integrated")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--exit-mode", choices=["simple", "advanced"], default="simple")
    parser.add_argument("--stop-loss-pct", type=float, default=None)
    parser.add_argument("--take-profit-pct", type=float, default=None)
    parser.add_argument("--trailing-stop-pct", type=float, default=None)
    parser.add_argument("--atr-stop-multiplier", type=float, default=None)
    parser.add_argument("--daily-loss-limit-pct", type=float, default=None)
    parser.add_argument("--weekly-loss-limit-pct", type=float, default=None)
    parser.add_argument("--max-drawdown-pct", type=float, default=None)
    parser.add_argument("--enable-rebalancing", action="store_true")
    parser.add_argument("--rebalance-frequency", default="WEEKLY")
    parser.add_argument("--use-regime-adjustment", action="store_true")
    parser.add_argument("--save-attribution", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(
        start=args.start,
        end=args.end,
        capital=args.capital,
        max_positions=args.max_positions,
        risk_pct=args.risk_pct,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        signal_source=args.signal_source,
        save_db=args.save_db,
        csv=args.csv,
        dry_run=args.dry_run,
        exit_mode=args.exit_mode,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        trailing_stop_pct=args.trailing_stop_pct,
        atr_stop_multiplier=args.atr_stop_multiplier,
        daily_loss_limit_pct=args.daily_loss_limit_pct,
        weekly_loss_limit_pct=args.weekly_loss_limit_pct,
        max_drawdown_pct=args.max_drawdown_pct,
        enable_rebalancing=args.enable_rebalancing,
        rebalance_frequency=args.rebalance_frequency,
        use_regime_adjustment=args.use_regime_adjustment,
        save_attribution=args.save_attribution,
    )
    print("PAPER TRADING SIMULATION")
    print(f"Status: {summary['status']}")
    print(f"Sinais carregados: {summary['signals_count']}")
    print(f"Ordens simuladas: {summary['orders_count']}")
    print(f"Trades simulados: {summary['trades_count']}")
    print(f"Capital final simulado: {summary['capital_final']:.2f}")
    print(f"Governança: {summary['governance_status']}")
    print(f"Eventos de saída simulada: {summary.get('exit_events_count', 0)}")
    print(f"Eventos de rebalanceamento simulado: {summary.get('rebalance_events_count', 0)}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    if summary["status"] == "INSUFFICIENT_DATA":
        print("Dados insuficientes para simulação de carteira no período/fonte informados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
