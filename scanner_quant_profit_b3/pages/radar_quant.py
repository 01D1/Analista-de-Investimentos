"""Página Radar Quant — scanner de opções B3."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.options.strategy_dashboard import main
main(skip_page_config=True)
