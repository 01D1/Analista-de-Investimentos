import pandas as pd

from src.paper.hypothesis_block_explanations import explain_hypothesis_blockage


def test_explain_hypothesis_blockage_prioritizes_cost():
    deep = pd.DataFrame({"hypothesis_id": ["H1", "H1"], "block_reason": ["BLOCKED_BY_COST", "MIXED_EVIDENCE"]})
    out = explain_hypothesis_blockage(deep)
    assert out.loc[0, "primary_block_reason"] == "BLOCKED_BY_COST"
    assert "nova investigação necessária" in out.loc[0, "explanation"]
