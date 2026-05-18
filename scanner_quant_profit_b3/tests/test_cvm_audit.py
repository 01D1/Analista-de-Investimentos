import json

from src.data_quality.cvm_audit import audit_cvm_ipe


def test_cvm_with_synthetic_index(tmp_path):
    folder = tmp_path / "PETR4"
    folder.mkdir()
    (folder / "cvm_ipe_index.json").write_text(json.dumps([{"data": "2026-04-30", "categoria": "Fato Relevante", "link": "https://example.com"}]), encoding="utf-8")
    result = audit_cvm_ipe(tmp_path)
    assert result["docs_count"] == 1
    assert result["status"] == "OK"

