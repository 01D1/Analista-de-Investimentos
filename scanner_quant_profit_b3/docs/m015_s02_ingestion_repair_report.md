# M015-S02: CVM RI Ingestion / INSERT Repair

**Executado:** 2026-05-25T00:49:32.652737+00:00
**Database:** `/Users/diegocarvalho/Library/CloudStorage/OneDrive-EPEJUD/DIEGO/OBSIDIAN/Analista de Investimentos/scanner_quant_profit_b3/data/database/scanner_quant.db`

---

## a) Diagnóstico do CVM Connector

O conector `src/context/connectors/cvm_connector.py` lê arquivos `cvm_*index.json`
do diretório `12_PYTHON/pipeline banco completo/data/qualitative/processed/<TICKER>/`.

O conector `releases_connector.py` lê `events/<TICKER>/events.json` do mesmo caminho base.

As funções `integrate_cvm_documents()` e `integrate_releases()` existem em
`src/context/qualitative_data.py` e funcionam corretamente, mas **nunca foram**
**invocadas em lote para os tickers HAS_SECTOR_NO_RI**. Essa é a causa raiz.

## b) Causa do INSERT Quebrado

1. **Causa principal:** Nenhum script chamava `integrate_cvm_documents()` /
   `integrate_releases()` para os 26 tickers sem ri_documents.
2. **ABCB4 — Contaminação CVM:** a pasta `processed/ABCB4/cvm_ipe_index.json`
   contém 100 eventos de **COMPANHIA PARANAENSE DE ENERGIA COPEL** (CVM 014311)
   em vez de Banco ABC Brasil (CVM 020958). O pipeline que gerou os índices
   atribuiu um lote de dados de outra empresa à pasta ABCB4. CVM BLOQUEADO.
   Releases da ABCB4 estão corretos (79 eventos com `ticker='ABCB4'`) e foram integrados.
3. **NTCO3, PETZ3, VALE3:** sem diretório `processed/` → sem dados disponíveis.

## c) Tickers Processados

- `ABCB4`: CVM=0 (bloqueado — contaminação Copel) | Releases=17 (fix aplicado após erro de módulo)
- `AZZA3`: CVM=118 | Releases=241
- `BPAC11`: CVM=120 | Releases=220
- `BRSR6`: CVM=0 | Releases=143
- `EGIE3`: CVM=120 | Releases=128
- `FLRY3`: CVM=120 | Releases=88
- `HYPE3`: CVM=120 | Releases=162
- `KLBN11`: CVM=120 | Releases=60
- `LREN3`: CVM=120 | Releases=176
- `MGLU3`: CVM=120 | Releases=248
- `PCAR3`: CVM=120 | Releases=151
- `PRIO3`: CVM=120 | Releases=99
- `RADL3`: CVM=120 | Releases=155
- `RAIL3`: CVM=120 | Releases=119
- `RECV3`: CVM=120 | Releases=84
- `RENT3`: CVM=118 | Releases=136
- `SANB11`: CVM=119 | Releases=100
- `SBSP3`: CVM=120 | Releases=100
- `SUZB3`: CVM=120 | Releases=120
- `TAEE11`: CVM=120 | Releases=156
- `VAMO3`: CVM=0 | Releases=135
- `VIVA3`: CVM=120 | Releases=191
- `VIVT3`: CVM=120 | Releases=35

## d) Documentos Inseridos por Ticker

| Ticker | ANTES | DEPOIS | Delta |
|--------|-------|--------|-------|
| ABCB4 | 0 | 17 | +17 (apenas releases; CVM bloqueado) |
| AZZA3 | 0 | 131 | +131 |
| BBAS3 | 121 | 121 | +0 (já coberto) |
| BBDC4 | 125 | 125 | +0 (já coberto) |
| BPAC11 | 0 | 134 | +134 |
| BRSR6 | 0 | 15 | +15 (apenas releases; CVM=Banese bloqueado) |
| EGIE3 | 0 | 129 | +129 |
| FLRY3 | 0 | 128 | +128 |
| HYPE3 | 0 | 132 | +132 |
| ITUB4 | 125 | 125 | +0 (já coberto) |
| KLBN11 | 0 | 129 | +129 |
| LREN3 | 0 | 130 | +130 |
| MGLU3 | 0 | 129 | +129 |
| NTCO3 | 0 | 0 | +0 (sem dados) |
| PCAR3 | 0 | 126 | +126 |
| PETR4 | 131 | 131 | +0 (já coberto) |
| PETZ3 | 0 | 0 | +0 (sem dados) |
| PRIO3 | 0 | 109 | +109 |
| RADL3 | 0 | 129 | +129 |
| RAIL3 | 0 | 135 | +135 |
| RECV3 | 0 | 126 | +126 |
| RENT3 | 0 | 129 | +129 |
| SANB11 | 0 | 129 | +129 |
| SBSP3 | 0 | 123 | +123 |
| SUZB3 | 0 | 131 | +131 |
| TAEE11 | 0 | 137 | +137 |
| VALE3 | 0 | 0 | +0 (sem dados — manual) |
| VAMO3 | 0 | 17 | +17 (apenas releases; CVM code divergente) |
| VIVA3 | 0 | 132 | +132 |
| VIVT3 | 0 | 128 | +128 |
| WEGE3 | 124 | 124 | +0 (já coberto) |

**Total:** 626 → 3251 (+2625 docs, +23 tickers novos)

## e) Tickers Sem Documentos e Motivo

- `NTCO3`: Sem diretório processed/ e sem events.json
- `PETZ3`: Sem diretório processed/ e sem events.json
- `VALE3`: Sem diretório processed/ e sem events.json

## f) Validações Executadas

| Validação | Resultado |
|-----------|-----------|
| V1 — ri_documents ANTES | 626 docs / 5 tickers |
| V1 — ri_documents DEPOIS | 3251 docs / 28 tickers |
| V1 — Delta | +2625 docs / +23 tickers novos |
| V2 — fair_value BBAS3 preservado | ✓ (64.84) |
| V2 — fair_value ITUB4 preservado | ✓ (73.69) |
| V2 — fair_value PETR4 preservado | ✓ (81.12) |
| V2 — fair_value WEGE3 preservado | ✓ (40.16) |
| V3 — UNKNOWN bloqueado | ✓ (0 violações) |
| V4 — Sem dados fake | ✓ |
| V5 — ABCB4 CVM bloqueado (Copel) | ✓ (releases: 17 docs inseridos) |
| V5 — BRSR6 CVM bloqueado (Banese) | ✓ (releases: 15 docs inseridos) |
| V5 — VAMO3 CVM code divergente | ✓ (releases: 17 docs inseridos; CVM requer revisão) |
| V5 — VALE3 sem docs | ✓ |
| V5 — NTCO3 sem docs | ✓ |
| V5 — PETZ3 sem docs | ✓ |

## g) Autorização S04 — Coverage Audit Before/After Report

**Status:** ✅ **AUTORIZADO**

**Resumo S02:**
- 23 tickers elegíveis processados
- 2625 documentos inseridos no total
- 23 novos tickers com ri_documents
- ABCB4: CVM bloqueado (contaminação Copel), releases integrados (17 docs únicos)
- VALE3 / NTCO3 / PETZ3: sem dados disponíveis (0 inseridos)
- Fair values de BBAS3, ITUB4, PETR4, WEGE3: preservados

---
*Gerado por M015-S02 em 2026-05-25T00:49:32.652737+00:00*