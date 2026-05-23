from src.paper.rebalance_variants import apply_rebalance_variant, build_rebalance_variants


def test_build_rebalance_variants_contains_expected_ids():
    variants = build_rebalance_variants()

    assert "DISABLE_REBALANCE" in variants["variant_id"].tolist()
    assert "THRESHOLD_REBALANCE_10PCT" in variants["variant_id"].tolist()
    assert variants["variant_type"].eq("rebalance").all()


def test_apply_rebalance_variant_updates_config():
    variants = build_rebalance_variants()
    variant = variants[variants["variant_id"] == "DISABLE_REBALANCE"].iloc[0]

    config = apply_rebalance_variant({"enable_rebalancing": True}, variant)

    assert config["enable_rebalancing"] is False
    assert config["variant_type"] == "rebalance"
