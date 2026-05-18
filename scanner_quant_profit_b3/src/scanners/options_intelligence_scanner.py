"""Scanner inteligente de opções com métricas, estruturas e governança."""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.db.init_db import init_database
from src.options.greeks import (
    black_scholes_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    estimate_implied_volatility,
)
from src.options.options_chain_normalizer import normalize_options_chain, validate_options_chain
from src.options.options_governance import evaluate_option_candidate, evaluate_structure_candidate
from src.options.options_metrics import (
    calculate_breakeven,
    calculate_extrinsic_value,
    calculate_intrinsic_value,
    calculate_moneyness,
    calculate_option_liquidity_score,
    calculate_option_risk_score,
)
from src.options.strategy_ranking import score_option_structure
from src.options.structures import build_bear_put_spread, build_bull_call_spread, build_long_call, build_long_put
from src.utils import load_config, project_path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_options_config() -> dict[str, Any]:
    path = project_path("config/options.yaml")
    if not path.exists():
        return {"scanner": {"risk_free_rate": 0.10}, "governance": {}}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_raw_options(db_path: Path, underlyings: list[str] | None = None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    prefixes = [u[:4].upper() for u in underlyings or []]
    with sqlite3.connect(db_path) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cotahist_daily'").fetchone()
        if not exists:
            return pd.DataFrame()
        where = "option_type IN ('CALL','PUT')"
        params: list[Any] = []
        if prefixes:
            where += " AND substr(ticker, 1, 4) IN (" + ",".join("?" for _ in prefixes) + ")"
            params.extend(prefixes)
        query = f"""
            SELECT *
            FROM cotahist_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM cotahist_daily WHERE option_type IN ('CALL','PUT'))
              AND {where}
        """
        raw = pd.read_sql_query(query, con, params=params)
        if raw.empty:
            return raw
        prices = pd.read_sql_query(
            """
            SELECT ticker AS underlying, close AS underlying_price
            FROM cotahist_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM cotahist_daily)
              AND market_type IN ('010', '10', 10)
            """,
            con,
        )
    if underlyings:
        base_map = {u[:4].upper(): u.upper() for u in underlyings}
        raw["underlying"] = raw["ticker"].str[:4].str.upper().map(base_map)
    else:
        raw["underlying"] = raw["ticker"].str[:4].str.upper()
    if not prices.empty:
        raw = raw.merge(prices, on="underlying", how="left")
    return raw


def enrich_options_chain(chain: pd.DataFrame, risk_free_rate: float = 0.10, historical_volatility: float = 0.30) -> pd.DataFrame:
    if chain is None or chain.empty:
        return chain
    df = chain.copy()
    for idx, row in df.iterrows():
        opt = row.get("option_type")
        S = float(row.get("underlying_price") or 0)
        K = float(row.get("strike") or 0)
        price = float(row.get("last_price") or 0)
        dte = row.get("days_to_maturity")
        T = max(float(dte or 0) / 365.0, 0.0)
        m_pct, m_class = calculate_moneyness(opt, S, K)
        intrinsic = calculate_intrinsic_value(opt, S, K)
        extrinsic = calculate_extrinsic_value(price, intrinsic)
        iv = estimate_implied_volatility(price, S, K, T, risk_free_rate, opt)
        sigma = iv if not math.isnan(iv) else historical_volatility
        df.loc[idx, "moneyness_pct"] = m_pct
        df.loc[idx, "moneyness_class"] = m_class
        df.loc[idx, "intrinsic_value"] = intrinsic
        df.loc[idx, "extrinsic_value"] = extrinsic
        df.loc[idx, "extrinsic_pct"] = (extrinsic / price * 100) if price > 0 else math.nan
        df.loc[idx, "breakeven"] = calculate_breakeven(opt, K, price)
        df.loc[idx, "implied_volatility"] = iv
        df.loc[idx, "historical_volatility"] = historical_volatility
        df.loc[idx, "theoretical_value"] = black_scholes_price(S, K, T, risk_free_rate, sigma, opt)
        df.loc[idx, "delta"] = calculate_delta(S, K, T, risk_free_rate, sigma, opt)
        df.loc[idx, "gamma"] = calculate_gamma(S, K, T, risk_free_rate, sigma)
        df.loc[idx, "theta"] = calculate_theta(S, K, T, risk_free_rate, sigma, opt)
        df.loc[idx, "vega"] = calculate_vega(S, K, T, risk_free_rate, sigma)
        liquidity = calculate_option_liquidity_score(row.get("volume"), row.get("trades"), row.get("financial_volume"), row.get("spread_pct"), row.get("open_interest"))
        risk = calculate_option_risk_score(dte, row.get("spread_pct"), df.loc[idx, "theta"], liquidity, m_class)
        df.loc[idx, "liquidity_score"] = liquidity
        df.loc[idx, "risk_score"] = risk
        df.loc[idx, "opportunity_score"] = max(0, min(100, liquidity * 0.45 + risk * 0.35 + (70 if m_class in {"ATM", "ITM"} else 45) * 0.20))
    return df


def build_candidate_structures(chain: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if chain is None or chain.empty:
        return pd.DataFrame()
    # Gera estruturas mesmo com liquidez fraca; a governança é quem bloqueia.
    liquid = chain[pd.to_numeric(chain.get("liquidity_score"), errors="coerce").fillna(0) >= 0].copy()
    for _, row in liquid.head(50).iterrows():
        if row.get("option_type") == "CALL":
            rows.append(build_long_call(row))
        elif row.get("option_type") == "PUT":
            rows.append(build_long_put(row))
    for (underlying, maturity), group in liquid.groupby(["underlying", "maturity_date"], dropna=False):
        bull = build_bull_call_spread(group, underlying, maturity)
        bear = build_bear_put_spread(group, underlying, maturity)
        if bull:
            rows.append(bull)
        if bear:
            rows.append(bear)
    scored = []
    for structure in rows:
        scored.append(score_option_structure(structure))
    return pd.DataFrame(scored)


def apply_governance(chain: pd.DataFrame, structures: pd.DataFrame, limits: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    chain_out = chain.copy()
    if not chain_out.empty:
        reviews = [evaluate_option_candidate(row, limits) for _, row in chain_out.iterrows()]
        chain_out["governance_status"] = [r["governance_status"] for r in reviews]
        chain_out["governance_reasons"] = [", ".join(r["reasons"]) for r in reviews]
    structures_out = structures.copy()
    if not structures_out.empty:
        reviews = [evaluate_structure_candidate(row, limits) for _, row in structures_out.iterrows()]
        structures_out["governance_status"] = [r["governance_status"] for r in reviews]
        structures_out["governance_reasons"] = [", ".join(r["reasons"]) for r in reviews]
    return chain_out, structures_out


def _write_csvs(chain: pd.DataFrame, structures: pd.DataFrame) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "options": reports / f"options_chain_scored_{stamp}.csv",
        "structures": reports / f"option_structure_candidates_{stamp}.csv",
    }
    chain.to_csv(paths["options"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    structures.to_csv(paths["structures"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def _replace_infinite_values(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        numeric = pd.to_numeric(out[col], errors="coerce")
        mask = numeric.isin([float("inf"), -float("inf")])
        if mask.any():
            out.loc[mask, col] = pd.NA
    return out


def _save_db(db_path: Path, chain: pd.DataFrame, structures: pd.DataFrame, started_at: str, finished_at: str) -> int:
    init_database(db_path, verbose=False)
    captured_at = finished_at
    with sqlite3.connect(db_path) as con:
        if not chain.empty:
            cols = [
                "captured_at",
                "trade_date",
                "option_ticker",
                "underlying",
                "option_type",
                "strike",
                "maturity_date",
                "days_to_maturity",
                "last_price",
                "bid",
                "ask",
                "spread_pct",
                "volume",
                "trades",
                "financial_volume",
                "open_interest",
                "underlying_price",
                "moneyness_pct",
                "moneyness_class",
                "intrinsic_value",
                "extrinsic_value",
                "breakeven",
                "implied_volatility",
                "historical_volatility",
                "delta",
                "gamma",
                "theta",
                "vega",
                "liquidity_score",
                "risk_score",
                "metadata_json",
            ]
            save_chain = _replace_infinite_values(chain)
            save_chain["captured_at"] = captured_at
            save_chain["trade_date"] = captured_at[:10]
            save_chain[[c for c in cols if c in save_chain.columns]].to_sql("options_chain_snapshots", con, if_exists="append", index=False)
        if not structures.empty:
            save_struct = _replace_infinite_values(structures)
            save_struct["created_at"] = captured_at
            cols = [
                "created_at",
                "structure_type",
                "underlying",
                "maturity_date",
                "legs_json",
                "net_debit",
                "net_credit",
                "max_profit",
                "max_loss",
                "breakeven",
                "payoff_ratio",
                "liquidity_score",
                "risk_score",
                "structure_score",
                "candidate_status",
                "explanation",
                "governance_status",
                "metadata_json",
            ]
            save_struct[[c for c in cols if c in save_struct.columns]].to_sql("option_structure_candidates", con, if_exists="append", index=False)
        approved = int(structures.get("governance_status", pd.Series(dtype=str)).astype(str).eq("STRUCTURE_APPROVED_FOR_STUDY").sum()) if not structures.empty else 0
        blocked = int(structures.get("governance_status", pd.Series(dtype=str)).astype(str).str.contains("BLOCKED").sum()) if not structures.empty else 0
        warning = int(structures.get("governance_status", pd.Series(dtype=str)).astype(str).str.contains("OBSERVATION").sum()) if not structures.empty else 0
        cur = con.execute(
            """
            INSERT INTO option_scanner_runs (
                started_at, finished_at, status, options_count, structures_count,
                approved_for_study_count, blocked_count, warning_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (started_at, finished_at, "SUCCESS", len(chain), len(structures), approved, blocked, warning, json.dumps({}, ensure_ascii=False)),
        )
        con.commit()
        return int(cur.lastrowid)


def run(
    *,
    underlyings: list[str] | None = None,
    min_volume: float | None = None,
    min_trades: int | None = None,
    max_spread_pct: float | None = None,
    min_dte: int | None = None,
    max_dte: int | None = None,
    risk_free_rate: float | None = None,
    save_db: bool = False,
    write_csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = _now()
    cfg = load_config()
    ocfg = _load_options_config()
    scanner = ocfg.get("scanner", {})
    limits = ocfg.get("governance", {})
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    underlyings = [u.upper() for u in (underlyings or cfg.get("ativos_base", []))]
    raw = _load_raw_options(db, underlyings)
    chain = normalize_options_chain(raw)
    valid, validation = validate_options_chain(chain)
    valid = enrich_options_chain(valid, risk_free_rate or float(scanner.get("risk_free_rate", 0.10)))
    min_volume = min_volume if min_volume is not None else float(scanner.get("min_volume", 0))
    min_trades = min_trades if min_trades is not None else int(scanner.get("min_trades", 0))
    max_spread_pct = max_spread_pct if max_spread_pct is not None else float(scanner.get("max_spread_pct", 999))
    min_dte = min_dte if min_dte is not None else int(scanner.get("min_dte", 0))
    max_dte = max_dte if max_dte is not None else int(scanner.get("max_dte", 9999))
    filtered = valid[
        (pd.to_numeric(valid["volume"], errors="coerce").fillna(0) >= min_volume)
        & (pd.to_numeric(valid["trades"], errors="coerce").fillna(0) >= min_trades)
        & (pd.to_numeric(valid["spread_pct"], errors="coerce").fillna(999) <= max_spread_pct)
        & (pd.to_numeric(valid["days_to_maturity"], errors="coerce").fillna(-1).between(min_dte, max_dte))
    ].copy()
    structures = build_candidate_structures(filtered)
    chain_gov, structures_gov = apply_governance(filtered, structures, limits)
    finished = _now()
    paths = _write_csvs(chain_gov, structures_gov) if write_csv else {}
    run_id = None if dry_run or not save_db else _save_db(db, chain_gov, structures_gov, started, finished)
    approved = int(structures_gov.get("governance_status", pd.Series(dtype=str)).astype(str).eq("STRUCTURE_APPROVED_FOR_STUDY").sum()) if not structures_gov.empty else 0
    blocked = int(structures_gov.get("governance_status", pd.Series(dtype=str)).astype(str).str.contains("BLOCKED").sum()) if not structures_gov.empty else 0
    insufficient = int(chain_gov.get("governance_status", pd.Series(dtype=str)).astype(str).str.contains("DATA").sum()) if not chain_gov.empty else int(validation["count"].sum() if not validation.empty else 0)
    print("\nOPTIONS INTELLIGENCE SCANNER")
    print(f"Opções analisadas: {len(chain_gov)}")
    print(f"Estruturas geradas: {len(structures_gov)}")
    print(f"Aprovadas para estudo: {approved}")
    print(f"Bloqueadas: {blocked}")
    print(f"DADOS_INSUFICIENTES: {insufficient}")
    if run_id:
        print(f"Run salvo: option_scanner_run_id={run_id}")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {"chain": chain_gov, "structures": structures_gov, "validation": validation, "run_id": run_id, "csv_paths": paths}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scanner inteligente de opções para estudo analítico.")
    parser.add_argument("--underlyings", nargs="*", default=None)
    parser.add_argument("--min-volume", type=float, default=None)
    parser.add_argument("--min-trades", type=int, default=None)
    parser.add_argument("--max-spread-pct", type=float, default=None)
    parser.add_argument("--min-dte", type=int, default=None)
    parser.add_argument("--max-dte", type=int, default=None)
    parser.add_argument("--risk-free-rate", type=float, default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(
        underlyings=args.underlyings,
        min_volume=args.min_volume,
        min_trades=args.min_trades,
        max_spread_pct=args.max_spread_pct,
        min_dte=args.min_dte,
        max_dte=args.max_dte,
        risk_free_rate=args.risk_free_rate,
        save_db=args.save_db,
        write_csv=args.write_csv,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
