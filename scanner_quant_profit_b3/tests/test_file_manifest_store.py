from src.data_quality.file_manifest import build_file_manifest, compare_file_manifest
from src.data_quality.file_manifest_store import load_latest_file_manifest, save_file_manifest_run


def test_save_file_manifest_run(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("1", encoding="utf-8")
    manifest = build_file_manifest([tmp_path], ["*.txt"])
    db = tmp_path / "manifest.db"
    run_id = save_file_manifest_run(db, manifest, compare_file_manifest(None, manifest))
    latest = load_latest_file_manifest(db)
    assert run_id == 1
    assert latest.iloc[0]["file_name"] == "data.txt"

