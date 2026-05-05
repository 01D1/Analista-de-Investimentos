"""Página Valuation Engine — análise fundamentalista."""
import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON" / "pipeline banco completo"

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from streamlit_app import main
main(skip_page_config=True)
