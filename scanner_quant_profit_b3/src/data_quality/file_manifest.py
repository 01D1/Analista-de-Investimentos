"""Manifesto de arquivos com checksums para rastreabilidade."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.data_quality.source_inventory import resolve_path


FILE_MANIFEST_COLUMNS = [
    "file_path",
    "file_name",
    "extension",
    "size_bytes",
    "modified_at",
    "checksum",
    "source_domain",
    "metadata_json",
]

MANIFEST_COMPARISON_COLUMNS = [
    "file_path",
    "file_name",
    "change_type",
    "previous_checksum",
    "current_checksum",
    "previous_size_bytes",
    "current_size_bytes",
    "checksum_changed",
    "size_changed",
    "metadata_json",
]


def calculate_file_checksum(path: str | Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_domain(path: Path) -> str:
    text = str(path).lower()
    if "cotahist" in text or "\\data\\raw" in text or "/data/raw" in text:
        return "B3_COTAHIST"
    if "data\\processed" in text or "data/processed" in text:
        return "PROCESSED_DATA"
    if "qualitative" in text or "cvm" in text:
        return "CVM_IPE"
    if "news_hunter" in text or "calendario" in text:
        return "NEWS_MACRO"
    return "UNKNOWN"


def _iter_files(base_dirs: Iterable[str | Path], patterns: list[str] | None) -> Iterable[Path]:
    pats = patterns or ["**/*"]
    for base in base_dirs:
        root = resolve_path(base) or Path(base)
        if not root.exists():
            continue
        for pat in pats:
            for path in root.glob(pat):
                if path.is_file():
                    yield path


def build_file_manifest(base_dirs: Iterable[str | Path], patterns: list[str] | None = None) -> pd.DataFrame:
    rows = []
    for path in sorted(set(_iter_files(base_dirs, patterns))):
        stat = path.stat()
        rows.append(
            {
                "file_path": str(path.resolve()),
                "file_name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": int(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "checksum": calculate_file_checksum(path),
                "source_domain": _source_domain(path),
                "metadata_json": json.dumps({"parent": str(path.parent)}, ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows, columns=FILE_MANIFEST_COLUMNS)


def compare_file_manifest(previous_df: pd.DataFrame, current_df: pd.DataFrame) -> pd.DataFrame:
    previous = previous_df.copy() if previous_df is not None else pd.DataFrame(columns=FILE_MANIFEST_COLUMNS)
    current = current_df.copy() if current_df is not None else pd.DataFrame(columns=FILE_MANIFEST_COLUMNS)
    if previous.empty and current.empty:
        return pd.DataFrame(columns=MANIFEST_COMPARISON_COLUMNS)
    prev_map = previous.set_index("file_path").to_dict(orient="index") if not previous.empty else {}
    curr_map = current.set_index("file_path").to_dict(orient="index") if not current.empty else {}
    rows = []
    for file_path in sorted(set(prev_map) | set(curr_map)):
        prev = prev_map.get(file_path)
        curr = curr_map.get(file_path)
        if prev is None:
            change = "NEW_FILE"
        elif curr is None:
            change = "REMOVED_FILE"
        else:
            checksum_changed = prev.get("checksum") != curr.get("checksum")
            size_changed = int(prev.get("size_bytes") or 0) != int(curr.get("size_bytes") or 0)
            change = "CHANGED_FILE" if checksum_changed or size_changed else "UNCHANGED"
        rows.append(
            {
                "file_path": file_path,
                "file_name": (curr or prev or {}).get("file_name", Path(file_path).name),
                "change_type": change,
                "previous_checksum": (prev or {}).get("checksum", ""),
                "current_checksum": (curr or {}).get("checksum", ""),
                "previous_size_bytes": int((prev or {}).get("size_bytes") or 0),
                "current_size_bytes": int((curr or {}).get("size_bytes") or 0),
                "checksum_changed": bool(prev and curr and prev.get("checksum") != curr.get("checksum")),
                "size_changed": bool(prev and curr and int(prev.get("size_bytes") or 0) != int(curr.get("size_bytes") or 0)),
                "metadata_json": json.dumps({"previous": prev or {}, "current": curr or {}}, ensure_ascii=False, default=str),
            }
        )
    return pd.DataFrame(rows, columns=MANIFEST_COMPARISON_COLUMNS)

