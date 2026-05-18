"""Explicações dos motivos de bloqueio de hipóteses."""
from __future__ import annotations

import pandas as pd


BLOCK_REASON_PRIORITY = [
    "BLOCKED_BY_COST",
    "BLOCKED_BY_SLIPPAGE",
    "BLOCKED_BY_REGIME",
    "BLOCKED_BY_SIGNAL_SOURCE",
    "BLOCKED_BY_ASSET_CONCENTRATION",
    "BLOCKED_BY_LOW_SAMPLE",
    "BLOCKED_BY_OVERFITTING",
    "BLOCKED_BY_NEGATIVE_RETURN",
    "BLOCKED_BY_DRAWDAWN",
    "MIXED_EVIDENCE",
    "NO_CLEAR_BLOCKER",
]


def explain_hypothesis_blockage(deep_oos_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["hypothesis_id", "primary_block_reason", "secondary_block_reason", "explanation", "required_actions_json", "metadata_json"]
    if deep_oos_df is None or deep_oos_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for hypothesis_id, group in deep_oos_df.groupby("hypothesis_id", dropna=False):
        counts = group["block_reason"].value_counts()
        ordered = sorted(counts.index.tolist(), key=lambda x: BLOCK_REASON_PRIORITY.index(x) if x in BLOCK_REASON_PRIORITY else 99)
        primary = ordered[0] if ordered else "NO_CLEAR_BLOCKER"
        secondary = ordered[1] if len(ordered) > 1 else ""
        positive = float(pd.to_numeric(group["positive_improvement_pct"] if "positive_improvement_pct" in group.columns else pd.Series(0, index=group.index), errors="coerce").fillna(0).mean())
        ret = float(pd.to_numeric(group["mean_return_delta"] if "mean_return_delta" in group.columns else pd.Series(0, index=group.index), errors="coerce").fillna(0).mean())
        frag = float(pd.to_numeric(group["mean_fragility_delta"] if "mean_fragility_delta" in group.columns else pd.Series(0, index=group.index), errors="coerce").fillna(0).mean())
        explanation = (
            f"{hypothesis_id} apresentou {positive:.1%} de melhora média nas células do deep dive. "
            f"O delta médio de retorno foi {ret:.6f} e o delta médio de fragilidade foi {frag:.6f}. "
            f"O bloqueio principal foi {primary}; nova investigação necessária antes de qualquer observação recorrente."
        )
        actions = ["retestar com janelas OOS maiores", "comparar por fonte de sinal", "avaliar sensibilidade a custo e slippage"]
        rows.append(
            {
                "hypothesis_id": hypothesis_id,
                "primary_block_reason": primary,
                "secondary_block_reason": secondary,
                "explanation": explanation,
                "required_actions_json": str(actions),
                "metadata_json": counts.to_json(force_ascii=False),
            }
        )
    return pd.DataFrame(rows, columns=columns)
