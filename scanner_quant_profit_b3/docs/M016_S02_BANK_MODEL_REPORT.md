# M016-S02 — Bank Valuation Model: Relatório + Errata

**Commit de entrega:** `a36fc73`  
**Data:** 2026-05-25  
**Status:** ✅ FECHADO

---

## Entregáveis

| Arquivo | Descrição |
|---|---|
| `src/valuation/models/__init__.py` | Pacote models |
| `src/valuation/models/bank_model.py` | Motor bancário: P/BV, DDM, hard blocks, diagnóstico |
| `src/valuation/valuation_store.py` | `save_valuation_result()` seguro (write=False, force_recalc=False) |
| `tests/test_bank_model.py` | 61 testes, 280/280 totais passando |

---

## Resumo dos resultados (7 tickers BANK)

| Ticker | Status | fair_value | Fonte |
|---|---|---|---|
| BBAS3 | `PRESERVE_EXISTING` | R$ 64,84 | Excel 2026-04-23 / `PRESERVED_FAIR_VALUES` |
| ITUB4 | `PRESERVE_EXISTING` | R$ 73,69 | Excel 2026-04-23 / `PRESERVED_FAIR_VALUES` |
| BBDC4 | `PRESERVE_EXISTING` | R$ 34,63 | Excel 2026-05-03 (ON) |
| BPAC11 | `PRESERVE_EXISTING` | R$ 8,46 | Excel 2026-04-23 |
| SANB11 | `PRESERVE_EXISTING` | R$ 86,79 | Excel 2026-04-23 |
| BRSR6 | `PRESERVE_EXISTING` | R$ 4,66 | `outputs/valuations/BRSR6/` |
| ABCB4 | `PRESERVE_EXISTING` | R$ 210,50 | `outputs/valuations/ABCB4/` |

---

## ⚠️ ERRATA — Diagnóstico de banco de dados (2026-05-25)

### O que foi reportado

O relatório textual da S02 afirmou que as tabelas do banco estavam com **0 rows** para todos os bancos:

> `asset_intelligence_snapshots`: 0 rows  
> `ri_documents`: 0 rows para BBAS3, ITUB4, BBDC4, BPAC11, BRSR6, ABCB4, SANB11  
> `cotahist_daily`: 0 rows

### O que estava errado

O diagnóstico Python rodou contra `scanner_quant.db` no diretório de trabalho raiz do projeto (`scanner_quant_profit_b3/scanner_quant.db`) — mas o banco canônico real está em **`data/database/scanner_quant.db`**.

A verificação manual confirmou os dados reais:

| Tabela | Rows reais |
|---|---|
| `asset_intelligence_snapshots` | **64** |
| `ri_documents` | **3.251** |
| `cotahist_daily` | **9.508.079** |

**ri_documents por banco (confirmado manualmente):**

| Ticker | ri_documents |
|---|---|
| ABCB4 | 17 |
| BBAS3 | 121 |
| BBDC4 | 125 |
| BPAC11 | 134 |
| BRSR6 | 15 |
| ITUB4 | 125 |
| SANB11 | 129 |

### Impacto nos entregáveis

**Nenhum.** Os entregáveis de código da S02 não são afetados:

- `bank_model.py` e `save_valuation_result()` usam o DB via `SCANNER_QUANT_DB` (env var) ou fallback configurável — **não hardcoded para o path errado**.
- Os 7 fair values foram carregados corretamente **via Excel bridge** (fonte independente do DB).
- O `diagnose_bank_tickers()` já trata a ausência de preço de mercado com `market_price=None` sem falhar.
- Os 280 testes passam sem depender do path específico do DB.

### Consequência para S03

A presença real de dados no DB canônico (`data/database/scanner_quant.db`) é **positiva** para as próximas sprints:

- Os 9,5 M de linhas em `cotahist_daily` fornecem preços de mercado históricos.
- Os 3.251 `ri_documents` (incluindo os dos 7 bancos) confirmam que a ingestão CVM foi executada com sucesso.
- O `asset_intelligence_snapshots` com 64 snapshots indica que o pipeline de inteligência já produziu dados para alguns tickers.

Para S03 (Commodity/Oil & Gas), o diagnóstico de banco deve ser feito apontando explicitamente para `data/database/scanner_quant.db` ou via `SCANNER_QUANT_DB`.

### Ação corretiva

Nenhuma alteração de código ou banco. A errata está registrada aqui.  
Commit `a36fc73` preservado integralmente.

---

*Errata registrada em 2026-05-25 por verificação manual pós-entrega.*
