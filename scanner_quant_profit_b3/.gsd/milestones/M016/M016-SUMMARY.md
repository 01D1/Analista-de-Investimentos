# M016 — Sector Normalization and Valuation Model Engine

**Data:** 2026-05-25 | **Milestone:** M016 | **Status:** ✅ FECHADO

## One-liner

Motor real de valuation setorial implementado: SectorNormalizer converte GICS/type
para chaves canônicas, 5 modelos setoriais (bank, commodity, utility, retail, industry)
com hard blocks e preserve logic, 9 fair values auditáveis preservados, 514/514 testes
passando, 18 tickers MODEL_AVAILABLE aguardando parsing DFP/ITR para M017.

---

## Resumo por Slice

| Slice | Título | Status | Key Deliverable |
|-------|--------|:------:|-----------------|
| S01 | SectorNormalizer | ✅ | `sector_normalizer.py` + `tickers_config.py`; 28/28 tickers com chave canônica correta (confidence=1.0); gap D097 resolvido |
| S02 | Bank Valuation Model | ✅ | `bank_model.py`: P/BV justificado + DDM/Gordon + diagnose batch; 7 tickers; BBAS3=64.84 e ITUB4=73.69 preservados; Excel pipeline lê BBDC4/BPAC11/BRSR6/ABCB4/SANB11 |
| S03 | Commodity / Oil & Gas Model | ✅ | `commodity_model.py`: DCF/FCFF + EV/EBITDA; PETR4=81.12 preservado; PRIO3/RECV3 NEEDS_FINANCIALS; VALE3 NEEDS_DATA (ri_docs=0) |
| S04 | Utility / Retail / Industry / Tech Model | ✅ | `utility_model.py`, `retail_model.py`, `industry_model.py`; WEGE3=40.16 preservado; 18 tickers NEEDS_FINANCIALS; VIVT3 TECH_FALLBACK; 150 testes novos |
| S05 | Metadata Refresh e Coverage Promotion | ✅ | Diagnose batch 5 modelos; matriz final 32 tickers; 514/514 testes; 9 fair values confirmados; relatório `docs/M016_S05_METADATA_REFRESH_REPORT.md` |

---

## Decisões Registradas (M016)

| ID | Decisão | Status |
|----|---------|:------:|
| D099 | `SectorNormalizer` usa `type` (yaml) como fonte primária; `sector` GICS como fallback | ✅ |
| D100 | `type` desconhecido → `FALLBACK_MULTIPLES` (nunca raise, nunca inventar) | ✅ |
| D101 | Fair values existentes (PETR4/BBAS3/ITUB4/WEGE3) preservados; sobrescrita exige `force_recalc=True` | ✅ |
| D102 | VALE3 aguarda SXX; não forçar ingestion em S03 | ✅ |
| D103 | PETZ3 = LEGACY_TICKER permanente neste milestone | ✅ |
| D104 | `b3_financials` ausente = `MISSING_DATA_SOURCE` (não crash, não mock) | ✅ |
| D105 | `save_valuation_result()` stub implementado com write=False default (safe) | ✅ |
| D106 | `input_hash` obrigatório em todo `ValuationResult` (gate anti-regeneração) | ✅ |
| D107 | `terminal_growth < WACC` = hard-block (P7 — anti-TV explosion) | ✅ |
| D108 | healthcare + agro + education → `INDUSTRY` canonical key | ✅ |
| D109 | VIVT3 = TECH_FALLBACK via industry_model; DCF aplicável quando inputs disponíveis | ✅ |
| D110 | 18 tickers NEEDS_FINANCIALS = corretos; RI docs existem mas DFP/ITR não parseados → M017 | ✅ |

---

## Arquivos Criados / Alterados

| Slice | Arquivo | Ação | Descrição |
|-------|---------|------|-----------|
| S01 | `src/valuation/sector_normalizer.py` | CRIADO | SectorNormalizer; type→canonical; GICS fallback |
| S01 | `src/valuation/tickers_config.py` | CRIADO | Loader do tickers.yaml com cache e path fallback |
| S01 | `src/valuation/router.py` | ALTERADO | _normalize_sector_for_router() integrado |
| S01 | `src/valuation/__init__.py` | ALTERADO | Exports de SectorNormalizer e tickers_config |
| S01 | `tests/test_sector_normalizer.py` | CRIADO | 134 testes em 12 suites |
| S02 | `src/valuation/models/__init__.py` | CRIADO | Pacote models |
| S02 | `src/valuation/models/bank_model.py` | CRIADO | BankValuationInputs/Result; P/BV + DDM; diagnose_bank_tickers() |
| S02 | `tests/test_bank_model.py` | CRIADO | 91 testes |
| S03 | `src/valuation/models/commodity_model.py` | CRIADO | CommodityValuationInputs/Result; DCF/FCFF + EV/EBITDA; diagnose_commodity_tickers() |
| S03 | `tests/test_commodity_model.py` | CRIADO | 71 testes |
| S04 | `src/valuation/models/utility_model.py` | CRIADO | UtilityValuationInputs/Result; RAB-DCF + DCF + EV/EBITDA |
| S04 | `src/valuation/models/retail_model.py` | CRIADO | RetailValuationInputs/Result; DCF + EV/EBITDA + DISTRESSED flag |
| S04 | `src/valuation/models/industry_model.py` | CRIADO | IndustryValuationInputs/Result; DCF + EV/EBITDA; TECH_FALLBACK; diagnose batch |
| S04 | `tests/test_utility_model.py` | CRIADO | 59 testes |
| S04 | `tests/test_retail_model.py` | CRIADO | 59 testes |
| S04 | `tests/test_industry_model.py` | CRIADO | 63 testes |
| S05 | `docs/M016_S05_METADATA_REFRESH_REPORT.md` | CRIADO | Relatório completo S05 com matriz de coverage |
| S05 | `.gsd/milestones/M016/slices/S05/S05-SUMMARY.md` | CRIADO | GSD summary S05 |

---

## Estado do Universo Post-M016

| Status | Count | Tickers |
|--------|------:|--------|
| PRESERVE_EXISTING (fair_value auditável) | 9 | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11, PETR4, WEGE3 |
| MODEL_AVAILABLE_NO_INPUTS (NEEDS_FINANCIALS) | 18 | PRIO3, RECV3, EGIE3, SBSP3, TAEE11, AZZA3, LREN3, MGLU3, PCAR3, VIVA3, FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3 |
| TECH_FALLBACK | 1 | VIVT3 |
| NEEDS_DATA (ri_docs=0) | 1 | VALE3 |
| NEEDS_RI_DOCS | 2 | AUAU3, NTCO3 |
| LEGACY_TICKER (permanente) | 1 | PETZ3 |

---

## Gap Residual para M017

**18 tickers com modelo pronto aguardando parsing DFP/ITR**

Todos os modelos setoriais estão implementados e testados. O único bloqueio para
calcular fair_value nos 18 tickers NEEDS_FINANCIALS é a ausência de dados estruturados:

| Campo Ausente | Impacto |
|--------------|---------|
| `ebitda` | Bloqueia EV/EBITDA em todos os modelos |
| `free_cash_flow` | Bloqueia DCF/FCFF em todos os modelos |
| `net_debt` | Bloqueia enterprise value → equity value |
| `shares_outstanding` | Bloqueia per-share calculation |

**RI docs existem** (17–137 por ticker) mas não foram parseados para tabela estruturada.
Quando M017 implementar o parsing DFP/ITR, os modelos calculam automaticamente
sem alteração de código.

---

*Milestone M016 fechado administrativamente em 2026-05-25.*
*M017 autorizado. Iniciar com: parsing estruturado DFP/ITR.*
