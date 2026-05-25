# S01: Data Source Traceability Audit — UAT

**Milestone:** M015
**Written:** 2026-05-24T23:48:16.743Z

## UAT: M015 S01 Data Source Traceability Audit

### Critério 1: CSV gerado com 63 tickers
```bash
wc -l docs/m015_traceability_audit_20260524.csv  # Esperado: 64 linhas (1 header + 63 dados)
```
**Verificado:** ✅ 64 linhas

### Critério 2: README gerado com gap breakdown
```bash
ls -la docs/m015_traceability_audit_README.md  # Esperado: arquivo existe, > 8KB
```
**Verificado:** ✅ 9.746 bytes

### Critério 3: Contagens consistentes
```python
# Cotahist: todos os 63 têm > 0 (market_type='010')
# RI docs: 5 tickers (BBAS3, BBDC4, ITUB4, PETR4, WEGE3)
# AI entries: 7 tickers (BBAS3, BBDC4, ITUB4, PETR4, SUZB3, VALE3, WEGE3)
# Traceability: 63 tickers (base do universo)
```
**Verificado:** ✅ Contagens consistentes com o DB

### Critério 4: Root cause classification
- COTAHIST_NO_AI: 57 tickers
- CVM_CONNECTOR_NOT_EXECUTED: 51 tickers
- AI_METADATA_NOT_POPULATED: 11 tickers
- BDR_UNSUPPORTED: 6 tickers
- CVM_CONNECTOR_PARTIAL_NO_CONTENT: 1 ticker (SUZB3)
**Verificado:** ✅ Root causes classificadas para todos os 63 tickers

### Critério 5: Casos críticos investigados
- VALE3: auditado separadamente (trace=0, cotahist=845, ai=1)
- SUZB3: CVM connector parcial, manifest=84, cotahist=845
- SANB11: BDR, cotahist=845, ai=N
- BPAC11: BDR, cotahist=845, ai=N
**Verificado:** ✅ Todos os 4 casos críticos documentados

### Critério 6: Sem alteração no banco
```bash
# Nenhum INSERT, UPDATE ou DELETE executado
# Apenas SELECT em modo readonly
```
**Verificado:** ✅ Banco não alterado
