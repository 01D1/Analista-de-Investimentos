import pandas as pd

from src.paper.hypothesis_deep_dive_selection import select_top_hypotheses_for_deep_dive


def test_select_top_hypotheses_includes_observation_and_top_score():
    ranking = pd.DataFrame(
        {
            "hypothesis_id": ["H1", "H2", "H3"],
            "hypothesis_robustness_score": [40, 80, 60],
            "hypothesis_class": ["HYPOTHESIS_OBSERVATION_ONLY", "HYPOTHESIS_FRAGILE", "HYPOTHESIS_INSUFFICIENT_DATA"],
            "data_coverage_penalty": [0, 0, 80],
            "governance_status": ["OBS", "REJ", "LOW"],
        }
    )
    selected = select_top_hypotheses_for_deep_dive(ranking, top_n=2)
    assert selected["hypothesis_id"].tolist() == ["H2", "H1"]
    assert selected.loc[0, "reason_for_selection"] == "top score do ranking multi-fonte"


def test_select_top_hypotheses_allows_manual_without_ranking():
    selected = select_top_hypotheses_for_deep_dive(pd.DataFrame(), top_n=1, manual_hypotheses=["LIMIT_ASSET_WEIGHT"])
    assert selected.loc[0, "hypothesis_id"] == "LIMIT_ASSET_WEIGHT"
