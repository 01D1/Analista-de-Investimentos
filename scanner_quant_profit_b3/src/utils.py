from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config():
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def project_path(path_str: str) -> Path:
    """Resolve a path relative to the scanner root.

    Special case: paths starting with '12_PYTHON' live under the OBSIDIAN
    root (scanner's parent directory), not under the scanner root itself.
    e.g. '12_PYTHON/pipeline banco completo/outputs' resolves to
         <scanner_parent>/12_PYTHON/pipeline banco completo/outputs
    """
    p = Path(path_str)
    if p.is_absolute():
        return p
    # 12_PYTHON is a sibling at the OBSIDIAN level, not inside the scanner
    if p.parts and p.parts[0] == "12_PYTHON":
        return ROOT.parent / p
    return ROOT / p
