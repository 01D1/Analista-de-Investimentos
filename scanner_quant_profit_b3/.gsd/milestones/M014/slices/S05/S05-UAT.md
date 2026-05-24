# S05 — UAT

## Critério de Aceitação

**Dado** ticker com valuation no outputs/ fallback (PETR4, BBAS3, ITUB4, WEGE3)  
**Quando** chamada `load_valuation_result(ticker)`  
**Então** retorna ValuationResult com fair_value > 0, valuation_available=True, método preservado

**Dado** ticker sem dados no banco  
**Quando** chamada `load_valuation_result('XXXXXX')`  
**Então** retorna ValuationResult com fair_value=None, valuation_available=False, status=VALUATION_MISSING

**Dado** chamada `save_valuation_result()`  
**Quando** qualquer ticker e ValuationResult  
**Então** retorna False (stub seguro, não usado automaticamente)

**Dado** coexistência com router (S04)  
**Quando** `get_valuation_method('PETR4', 'COMMODITY', 'partial', Provenance('TRACEABLE'))`  
**Então** retorna DCF, blocked=False, confidence=1.0

## Evidências

| Critério | Evidência | Resultado |
|----------|-----------|-----------|
| PETR4 fair_value preservado | load_valuation_result('PETR4') → 81.12 | ✅ PASS |
| Empty ticker None≠0.0 | load_valuation_result('XXXXXX') → None | ✅ PASS |
| save stub False | save_valuation_result(...) → False | ✅ PASS |
| Router PETR4 OK | get_valuation_method(...) → DCF, blocked=False, conf=1.0 | ✅ PASS |
| valuation_connector intacto | connector('PETR4') → 81.12 | ✅ PASS |
| pytest 28/28 | pytest tests/test_valuation_stores.py | ✅ PASS |

**Status:** ✅ UAT PASS — Condições de fechamento atendidas.**