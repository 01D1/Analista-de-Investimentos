from src.data_quality.file_manifest import build_file_manifest, calculate_file_checksum, compare_file_manifest


def test_checksum_and_manifest(tmp_path):
    f = tmp_path / "COTAHIST_A2026.TXT"
    f.write_text("abc", encoding="utf-8")
    checksum = calculate_file_checksum(f)
    manifest = build_file_manifest([tmp_path], patterns=["*.TXT"])
    assert len(checksum) == 64
    assert manifest.iloc[0]["checksum"] == checksum


def test_compare_manifest_new_changed_removed(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("a", encoding="utf-8")
    previous = build_file_manifest([tmp_path], ["*.txt"])
    f.write_text("b", encoding="utf-8")
    current = build_file_manifest([tmp_path], ["*.txt"])
    comparison = compare_file_manifest(previous, current)
    assert comparison.iloc[0]["change_type"] == "CHANGED_FILE"
    f.unlink()
    removed = compare_file_manifest(current, build_file_manifest([tmp_path], ["*.txt"]))
    assert removed.iloc[0]["change_type"] == "REMOVED_FILE"

