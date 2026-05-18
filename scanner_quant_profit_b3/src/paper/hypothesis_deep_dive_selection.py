"""Seleção de hipóteses prioritárias para deep dive."""
from __future__ import annotations

import pandas as pd


SELECTION_COLUMNS = ["hypothesis_id", "hypothesis_type", "score", "governance_status", "reason_for_selection"]


def select_top_hypotheses_for_deep_dive(
    ranking_df: pd.DataFrame,
    top_n: int = 3,
    manual_hypotheses: list[str] | None = None,
) -> pd.DataFrame:
    """Seleciona hipóteses em estudo para validação OOS profunda."""
    if ranking_df is None or ranking_df.empty:
        rows = [
            {
                "hypothesis_id": str(hyp),
                "hypothesis_type": str(hyp),
                "score": 0.0,
                "governance_status": "MANUAL_SELECTION",
                "reason_for_selection": "seleção manual",
            }
            for hyp in (manual_hypotheses or [])
        ]
        return pd.DataFrame(rows, columns=SELECTION_COLUMNS).head(int(top_n)).reset_index(drop=True)
    df = ranking_df.copy()
    df["hypothesis_id"] = df["hypothesis_id"].astype(str)
    df["score"] = pd.to_numeric(df.get("hypothesis_robustness_score"), errors="coerce").fillna(0)
    if "hypothesis_type" not in df.columns:
        df["hypothesis_type"] = df["hypothesis_id"]
    insufficient = df.get("hypothesis_class", pd.Series("", index=df.index)).astype(str).eq("HYPOTHESIS_INSUFFICIENT_DATA")
    coverage_penalty = pd.to_numeric(df["data_coverage_penalty"] if "data_coverage_penalty" in df.columns else pd.Series(0, index=df.index), errors="coerce").fillna(0)
    candidates = df[~(insufficient & (coverage_penalty >= 50))].copy()

    selected_ids: list[str] = []
    reasons: dict[str, str] = {}
    missing_manual = []
    for hyp in manual_hypotheses or []:
        hyp = str(hyp)
        if hyp in set(df["hypothesis_id"]):
            selected_ids.append(hyp)
            reasons[hyp] = "seleção manual"
        else:
            missing_manual.append(hyp)
    for hyp in candidates.sort_values("score", ascending=False)["hypothesis_id"].tolist():
        if hyp not in selected_ids:
            selected_ids.append(hyp)
            reasons[hyp] = "top score do ranking multi-fonte"
        if len(selected_ids) >= int(top_n):
            break
    observation = candidates[candidates.get("hypothesis_class", pd.Series("", index=candidates.index)).astype(str).isin(["HYPOTHESIS_OBSERVATION_ONLY", "HYPOTHESIS_PROMISING"])]
    for hyp in observation.sort_values("score", ascending=False)["hypothesis_id"].tolist():
        if len(selected_ids) >= int(top_n):
            break
        if hyp not in selected_ids:
            selected_ids.append(hyp)
            reasons[hyp] = "hipótese em observação"
    selected = df[df["hypothesis_id"].isin(selected_ids)].copy()
    if missing_manual:
        selected = pd.concat(
            [
                selected,
                pd.DataFrame(
                    {
                        "hypothesis_id": missing_manual,
                        "hypothesis_type": missing_manual,
                        "score": [0.0] * len(missing_manual),
                        "governance_status": ["MANUAL_SELECTION"] * len(missing_manual),
                    }
                ),
            ],
            ignore_index=True,
        )
        for hyp in missing_manual:
            selected_ids.append(hyp)
            reasons[hyp] = "seleção manual"
    selected["_order"] = selected["hypothesis_id"].map({hyp: i for i, hyp in enumerate(selected_ids)})
    selected = selected.sort_values("_order").head(int(top_n)).copy()
    return pd.DataFrame(
        {
            "hypothesis_id": selected["hypothesis_id"],
            "hypothesis_type": selected["hypothesis_type"],
            "score": selected["score"],
            "governance_status": selected.get("governance_status", ""),
            "reason_for_selection": selected["hypothesis_id"].map(reasons).fillna("top score do ranking multi-fonte"),
        },
        columns=SELECTION_COLUMNS,
    ).reset_index(drop=True)
