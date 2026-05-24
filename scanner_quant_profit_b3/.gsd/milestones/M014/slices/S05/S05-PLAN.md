# S05: Stores Canônicos de Valuation

**Goal:** Implementar 4 stores canônicos (results/inputs/coverage/store) com interface pública tipada, coexistência com valuation_connector.py, sem valuation pesado, sem mocks.

**Demo:** `from src.valuation import load_valuation_result; r = load_valuation_result('PETR4'); print(r.fair_value)` → 81.12

## Must-Haves

- [x] `valuation_results.py` — store de fair_value, upside, método, confiança
- [x] `valuation_inputs.py` — store de setor, subsector, scores, coverage
- [x] `valuation_coverage.py` — store de status de cobertura por ticker
- [x] `valuation_store.py` — interface unificada + save stub + compat shim
- [x] `src/valuation/__init__.py` — re-export completo
- [x] `tests/test_valuation_stores.py` — 28+ testes unitários
- [x] py_compile + import validation
- [x] valuation_connector.py não quebrado
- [x] Router (S04) coexiste

## Verification

- py_compile src/valuation/*.py → OK
- import stores → OK
- pytest 28/28 → PASSED
- PETR4=81.12 preservado → OK
- Empty ticker None≠0.0 → OK
- valuation_connector intacto → OK
- app.py/pages import → OK

## Tasks

- [x] **T01: Criar valuation_results.py**
  - ValuationResult dataclass
  - load_valuation_result(ticker) → ValuationResult
  - list_valuation_results(tickers) → pd.DataFrame
  - load_valuation_fair_values(tickers) → pd.DataFrame
  - asset_intelligence_snapshots como fonte primária
  - outputs/ fallback transitório

- [x] **T02: Criar valuation_inputs.py**
  - ValuationInputs dataclass
  - load_valuation_inputs(ticker) → ValuationInputs
  - list_valuation_inputs(tickers) → pd.DataFrame
  - CoverageStatus inferido

- [x] **T03: Criar valuation_coverage.py**
  - CoverageStatus enum (READY/PARTIAL/NEEDS_DATA/NEEDS_SECTOR/EMPTY)
  - ValuationCoverage dataclass
  - load_valuation_coverage(ticker) → ValuationCoverage
  - load_valuation_coverage_batch(tickers) → pd.DataFrame
  - ri_docs_count via ri_documents

- [x] **T04: Criar valuation_store.py**
  - Interface unificada das 3 funções
  - save_valuation_result() stub (sempre False)
  - load_latest_valuation_data() shim compat M012/M013

- [x] **T05: Criar testes e validar**
  - tests/test_valuation_stores.py (28+ casos)
  - py_compile + import validation
  - app/pages import validation
  - valuation_connector regression check