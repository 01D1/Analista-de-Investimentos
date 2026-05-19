"""Página Radar Quant — scanner de opções B3."""
import sys
from pathlib import Path

PROJECT_ROOT  = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = PROJECT_ROOT.parent / "12_PYTHON"

# Clear cached src so Python re-resolves with scanner root first.
for _k in list(sys.modules):
    if _k == "src" or _k.startswith("src."):
        del sys.modules[_k]

if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.append(str(PIPELINE_ROOT))

import streamlit as st

from src.utils import load_config
from src.options.flow_engine import FlowResult, compute_flow, compute_flow_from_db, flow_html