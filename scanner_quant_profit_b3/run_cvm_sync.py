#!/usr/bin/env python3
"""
run_cvm_sync.py
---------------
Script de execução para M017-S02.5 — CVM Dataset Sync & Audit.

Configura o PYTHONPATH e delega para src/ingestion/cvm_dataset_sync.py.

Uso:
    cd 12_PYTHON
    python run_cvm_sync.py                     # sync completo
    python run_cvm_sync.py --dry-run           # só contagem, sem salvar CSVs
    python run_cvm_sync.py --years 2024,2025   # anos específicos
    python run_cvm_sync.py --tickers BBAS3,ITUB4,BBDC4  # tickers específicos

Saídas:
    data/raw/cvm/filtered/{TICKER}/{DOC}_{YEAR}_{STMT}.csv
    data/raw/cvm/coverage_audit.json
    docs/M017_S02.5_DATASET_AUDIT.md
"""

import sys
from pathlib import Path

# Garante que src/ está no path mesmo rodando o script diretamente
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.cvm_dataset_sync import main

if __name__ == "__main__":
    main(sys.argv[1:])
