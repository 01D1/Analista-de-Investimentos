from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def project_path(path):
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p

def load_config():
    cfg_path = PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
