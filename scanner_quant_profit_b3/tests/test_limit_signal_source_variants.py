from src.paper.limit_signal_source_variants import build_limit_signal_source_variants


def test_build_limit_signal_source_variants_has_required_variants():
    variants = build_limit_signal_source_variants()
    assert len(variants) == 10
    assert "LIMIT_SIGNAL_SOURCE" in set(variants["hypothesis_id"])
    assert "REQUIRE_TWO_SOURCE_CONFIRMATION" in set(variants["variant_id"])

