"""
Report Generator — Quant Research Layer.

Gera relatórios estruturados a partir dos dados do scanner:
  - Relatório diário (setups do dia, aprovados e rejeitados)
  - Relatório semanal (sumário de performance, rankings)
  - Ranking de melhores ativos
  - Ranking de melhores opções
  - Histórico de setups

Salva em data/reports/ como CSV e TXT.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils import load_config, project_path
from src.quant.performance import full_summary


# ---------------------------------------------------------------------------
# Helpers de I/O
# ---------------------------------------------------------------------------

def _reports_dir() -> Path:
    p = project_path("data/reports")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save_csv(df: pd.DataFrame, name: str) -> Path:
    path = _reports_dir() / f"{name}_{_stamp()}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _save_txt(content: str, name: str) -> Path:
    path = _reports_dir() / f"{name}_{_stamp()}.txt"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Relatório diário
# ---------------------------------------------------------------------------

def generate_daily_report(
    setups_df: pd.DataFrame,
    journal_df: Optional[pd.DataFrame] = None,
    save: bool = True,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "=" * 72,
        f"  RELATÓRIO DIÁRIO — SCANNER QUANT B3",
        f"  Gerado em: {now}",
        "=" * 72,
    ]

    if setups_df.empty:
        lines.append("\nNenhum setup gerado hoje.")
    else:
        validados = setups_df[setups_df.get("status", pd.Series()) == "ENTRADA_VALIDADA"] if "status" in setups_df else pd.DataFrame()
        aguardar = setups_df[setups_df.get("status", pd.Series()) == "AGUARDAR_GATILHO"] if "status" in setups_df else pd.DataFrame()
        invalidados = setups_df[setups_df.get("status", pd.Series()) == "INVALIDADO"] if "status" in setups_df else pd.DataFrame()

        lines += [
            f"\nTotal de setups analisados: {len(setups_df)}",
            f"  ✅ Entrada Validada:     {len(validados)}",
            f"  ⏳ Aguardar Gatilho:     {len(aguardar)}",
            f"  ❌ Invalidados:          {len(invalidados)}",
        ]

        if not validados.empty:
            lines += ["", "─" * 72, "  SETUPS APROVADOS (ENTRADA_VALIDADA)", "─" * 72]
            for _, row in validados.iterrows():
                score = float(row.get("final_score", 0) or 0)
                ticker = str(row.get("ticker", ""))
                underlying = str(row.get("underlying", ""))
                entry = float(row.get("entrada_planejada", 0) or 0)
                stop = float(row.get("stop", 0) or 0)
                alvo1 = float(row.get("alvo_1", 0) or 0)
                dte = int(row.get("dte", 0) or 0)
                delta = float(row.get("delta", 0) or 0)
                motivo = str(row.get("motivo", ""))
                lines.append(
                    f"  {ticker:10s} ({underlying}) | Score {score:.1f} | DTE {dte}d | "
                    f"Δ {delta:.2f} | E R${entry:.4f} | Stop R${stop:.4f} | T1 R${alvo1:.4f}"
                )
                lines.append(f"    {motivo[:100]}")

        if not aguardar.empty:
            lines += ["", "─" * 72, "  SETUPS EM OBSERVAÇÃO (AGUARDAR_GATILHO)", "─" * 72]
            for _, row in aguardar.iterrows():
                score = float(row.get("final_score", 0) or 0)
                ticker = str(row.get("ticker", ""))
                underlying = str(row.get("underlying", ""))
                entry = float(row.get("entrada_planejada", 0) or 0)
                dte = int(row.get("dte", 0) or 0)
                lines.append(
                    f"  {ticker:10s} ({underlying}) | Score {score:.1f} | DTE {dte}d | E R${entry:.4f}"
                )

    # Performance do diário
    if journal_df is not None and not journal_df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_trades = journal_df[
            journal_df.get("data_sinal", pd.Series("")).str.startswith(today)
        ] if "data_sinal" in journal_df.columns else pd.DataFrame()

        if not today_trades.empty and "retorno_pct" in today_trades.columns:
            pnl_today = today_trades["retorno_pct"].dropna().astype(float)
            lines += [
                "",
                "─" * 72,
                f"  TRADES EXECUTADOS HOJE: {len(today_trades)}",
                f"  Retorno médio: {pnl_today.mean():.2f}%  |  Total: {pnl_today.sum():.2f}%",
                "─" * 72,
            ]

    lines += [
        "",
        "  ⚠️  Sistema de apoio à decisão — não executa ordens reais.",
        "=" * 72,
    ]

    report = "\n".join(lines)
    if save and not setups_df.empty:
        _save_csv(setups_df, "daily_setups")
        _save_txt(report, "daily_report")

    return report


# ---------------------------------------------------------------------------
# Relatório semanal
# ---------------------------------------------------------------------------

def generate_weekly_report(
    journal_df: pd.DataFrame,
    capital: float = 10_000.0,
    save: bool = True,
) -> str:
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%d/%m/%Y")
    lines = [
        "=" * 72,
        f"  RELATÓRIO SEMANAL — SCANNER QUANT B3",
        f"  Semana iniciada em: {week_start}  |  Gerado: {now.strftime('%d/%m/%Y %H:%M')}",
        "=" * 72,
    ]

    if journal_df.empty:
        lines.append("\nNenhum trade no período semanal.")
        return "\n".join(lines)

    # Filtra 7 últimos dias
    if "data_sinal" in journal_df.columns:
        journal_df = journal_df.copy()
        journal_df["_date"] = pd.to_datetime(journal_df["data_sinal"], errors="coerce")
        cutoff = now - timedelta(days=7)
        weekly = journal_df[journal_df["_date"] >= cutoff]
    else:
        weekly = journal_df

    if weekly.empty:
        lines.append("\nNenhum trade nos últimos 7 dias.")
        return "\n".join(lines)

    ret_col = "retorno_pct" if "retorno_pct" in weekly.columns else None
    if ret_col:
        pnl = weekly[ret_col].dropna().astype(float) * capital / 100
        stats = full_summary(pnl, capital=capital) if len(pnl) > 0 else {}
        lines += [
            f"\nTrades na semana: {len(weekly)}",
            f"P&L bruto semanal: R$ {pnl.sum():.2f}  ({pnl.sum()/capital*100:.2f}%)",
            "",
        ]
        if stats:
            lines += [
                f"  Win Rate:       {stats.get('win_rate', 0)*100:.1f}%",
                f"  Payoff Ratio:   {stats.get('payoff_ratio', 0):.2f}x",
                f"  Profit Factor:  {stats.get('profit_factor', 0):.2f}",
                f"  Expectancy:     R$ {stats.get('expectancy', 0):.2f}",
                f"  Melhor trade:   R$ {stats.get('best_trade', 0):.2f}",
                f"  Pior trade:     R$ {stats.get('worst_trade', 0):.2f}",
                f"  Max Drawdown:   {stats.get('max_drawdown', 0)*100:.2f}%",
                f"  Sharpe:         {stats.get('sharpe', 0):.3f}",
            ]

    # Ranking de ativos na semana
    if "ativo" in weekly.columns:
        asset_counts = weekly["ativo"].value_counts().head(5)
        lines += ["", "─" * 50, "  Top 5 Ativos (por frequência de sinal)"]
        for asset, cnt in asset_counts.items():
            lines.append(f"    {asset}: {cnt} setups")

    report = "\n".join(lines)
    if save:
        if not weekly.empty:
            _save_csv(weekly, "weekly_trades")
        _save_txt(report, "weekly_report")

    return report


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def rank_assets(setups_df: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """
    Ranking dos ativos por score médio, frequência e taxa de aprovação.
    """
    if setups_df.empty or "underlying" not in setups_df.columns:
        return pd.DataFrame()

    grp = setups_df.groupby("underlying").agg(
        n_setups=("final_score", "count"),
        avg_score=("final_score", "mean"),
        n_validados=("status", lambda x: (x == "ENTRADA_VALIDADA").sum()),
        avg_delta=("delta", "mean"),
    ).reset_index()

    grp["taxa_aprovacao"] = (grp["n_validados"] / grp["n_setups"] * 100).round(1)
    grp["avg_score"] = grp["avg_score"].round(2)
    grp["avg_delta"] = grp["avg_delta"].round(3)
    grp = grp.sort_values(["taxa_aprovacao", "avg_score"], ascending=False)
    return grp.head(top).reset_index(drop=True)


def rank_options(setups_df: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    """
    Ranking das melhores opções por liquidez, score e moneyness.
    """
    if setups_df.empty:
        return pd.DataFrame()

    cols = ["ticker", "underlying", "option_type", "final_score", "preco_opcao",
            "strike", "dte", "delta", "option_liquidity_score", "moneyness",
            "moneyness_pct", "volume_opcao", "negocios", "status"]
    existing = [c for c in cols if c in setups_df.columns]
    df = setups_df[existing].copy()
    df = df.sort_values("final_score", ascending=False)
    return df.head(top).reset_index(drop=True)


def setup_history_report(
    setups_df: pd.DataFrame,
    save: bool = True,
) -> pd.DataFrame:
    """
    Histórico completo de setups (aprovados e rejeitados) com todas as métricas.
    """
    if setups_df.empty:
        return pd.DataFrame()

    df = setups_df.copy()
    df["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if save:
        _save_csv(df, "setup_history")

    return df


# ---------------------------------------------------------------------------
# Entry point CLI
# ---------------------------------------------------------------------------

def generate_all_reports(
    setups_df: pd.DataFrame,
    capital: float = 10_000.0,
    verbose: bool = True,
) -> None:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])

    journal_df = pd.DataFrame()
    if db_path.exists():
        try:
            con = sqlite3.connect(db_path)
            journal_df = pd.read_sql_query("SELECT * FROM trade_journal", con)
            con.close()
        except Exception:
            pass

    daily = generate_daily_report(setups_df, journal_df, save=True)
    weekly = generate_weekly_report(journal_df, capital=capital, save=True)
    asset_rank = rank_assets(setups_df)
    opt_rank = rank_options(setups_df)
    setup_history_report(setups_df, save=True)

    if verbose:
        print(daily)
        print(weekly)
        print("\n── RANKING DE ATIVOS ──")
        print(asset_rank.to_string(index=False) if not asset_rank.empty else "Sem dados")
        print("\n── RANKING DE OPÇÕES ──")
        print(opt_rank.to_string(index=False) if not opt_rank.empty else "Sem dados")
