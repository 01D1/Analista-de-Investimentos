"""Comparacao de fontes de sinal em paper trading."""
from __future__ import annotations

import pandas as pd


def compare_signal_sources(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["signal_source", "mean_return", "mean_drawdown", "win_rate", "profit_factor", "turnover", "trades_count", "positive_periods_pct", "robustness_class", "metadata_json"]
    if results_df is None or results_df.empty or "signal_source" not in results_df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for source, group in results_df.groupby("signal_source", dropna=False):
        ret = pd.to_numeric(group["total_return"], errors="coerce").fillna(0)
        trades = pd.to_numeric(group["trades_count"], errors="coerce").fillna(0)
        mean_ret = float(ret.mean())
        positive_pct = float((ret > 0).mean())
        if len(group) < 2 or trades.sum() < 10:
            klass = "SIGNAL_SOURCE_DADOS_INSUFICIENTES"
        elif mean_ret > 0 and positive_pct >= 0.60:
            klass = "SIGNAL_SOURCE_PROMISSOR"
        elif mean_ret > 0 and positive_pct < 0.40:
            klass = "SIGNAL_SOURCE_OVERFIT_PROVAVEL"
        else:
            klass = "SIGNAL_SOURCE_FRAGIL"
        rows.append(
            {
                "signal_source": source,
                "mean_return": round(mean_ret, 6),
                "mean_drawdown": round(float(pd.to_numeric(group["max_drawdown"], errors="coerce").fillna(0).mean()), 6),
                "win_rate": round(float(pd.to_numeric(group["win_rate"], errors="coerce").fillna(0).mean()), 6),
                "profit_factor": round(float(pd.to_numeric(group["profit_factor"], errors="coerce").fillna(0).mean()), 6),
                "turnover": round(float(pd.to_numeric(group["turnover"], errors="coerce").fillna(0).mean()), 2),
                "trades_count": int(trades.sum()),
                "positive_periods_pct": round(positive_pct, 4),
                "robustness_class": klass,
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=columns)
