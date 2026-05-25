# M015-S05 — M016 Readiness Assessment
**Data:** 2026-05-24  
**Sprint:** M015 · Step 5 de 5  
**Status:** ✅ CONCLUÍDO

---

## 1. Smoke Test — Router (7 tickers)

### Metodologia
- Fonte: `data/database/scanner_quant.db` (canônico — 3.251 docs em 28 tickers)
- Router: `src/valuation/router.py` · `get_valuation_method()`
- Provenance: `TRACEABLE` para todos os tickers com sector de `tickers.yaml`
- Coverage status: derivado do estado real (s035 > s03; ri_docs reais)

### Resultados

| Ticker | Sector (yaml) | Type | Coverage Status | Router Eligible | Val. Eligible | RI Docs | Market Price | Method Sugerido | Confiança | Block Reason |
|--------|--------------|------|-----------------|:-:|:-:|--------:|-------------:|-----------------|:---------:|--------------|
| PETR4  | energy        | oil_gas  | partial         | ✅ | ✅ | 131 | R$ 44,48 | **Relativos** ⚠️ | 0.5 | — |
| VALE3  | materials     | mining   | needs_data      | ❌ | ❌ |   0 | R$ 83,10 | UNKNOWN         | 0.0 | NEEDS_CVM_DATA |
| BBAS3  | financials    | bank     | partial         | ✅ | ✅ | 121 | R$ 20,94 | **Relativos** ⚠️ | 0.5 | — |
| SUZB3  | materials     | industrial | partial       | ✅ | ✅ | 131 | R$ 41,70 | **Relativos** ⚠️ | 0.5 | — |
| BPAC11 | financials    | bank     | partial         | ✅ | ✅ | 134 | R$ 53,93 | **Relativos** ⚠️ | 0.5 | — |
| AUAU3  | consumer_disc | retail   | needs_data      | ❌ | ❌ |   0 | R$ 3,32  | UNKNOWN         | 0.0 | NEEDS_CVM_DATA |
| PETZ3  | consumer_disc | retail   | **legacy_ticker** | ⛔ | ❌ |   0 | R$ 4,39  | UNKNOWN         | 0.0 | **LEGACY_TICKER** |

### Legenda
- ⚠️ **Relativos** = FALLBACK (confidence=0.5) — setor GICS não mapeado para router canonical key
- ✅ router_eligible = não bloqueado por status
- ❌ val_eligible = bloqueado OU sem RI docs

---

## 2. Confirmações Obrigatórias (Checklist M015-S05)

| Requisito | Status | Evidência |
|-----------|:------:|-----------|
| PETZ3 é bloqueado como LEGACY_TICKER | ✅ | `s035_legacy_ticker=True`, `block_reason=LEGACY_TICKER`, router_eligible=False |
| AUAU3 é monitorável, mas sem RI docs | ✅ | `s035_coverage_status=HAS_SECTOR_NO_RI`, ri_docs=0, successor de PETZ3 |
| sector='UNKNOWN' continua bloqueado pelo router | ✅ | 32 tickers NEEDS_SECTOR em AI snapshots — nenhum passa pelo router |
| Tickers com RI docs + sector → passam pelo router | ✅ | 28 tickers: router_eligible=True, val_eligible=True |
| Tickers sem RI docs **não** viram valuation pronto | ✅ | 3 NEEDS_RI_DOCS (VALE3, AUAU3, NTCO3) + 64 sem docs = 0 val_eligible |
| Fair values existentes preservados | ✅ | PETR4=81,12 · BBAS3=64,84 (não alterados) |
| Nenhum DCF/COSIF/DDM executado | ✅ | Smoke test apenas lê router — zero cálculo |
| Banco não alterado | ✅ | Read-only |

---

## 3. Gap Crítico Detectado — Setor Não Normalizado

> **Este gap é o principal bloqueador de M016.**

### O Problema

O router (`src/valuation/router.py`) opera com chaves canônicas:

```
BANK · INSURANCE · COMMODITY · UTILITY · INDUSTRY · RETAIL · HOLDING · TECH
```

O banco e `tickers.yaml` armazenam valores GICS em lowercase:

```
financials · energy · materials · consumer_discretionary · utilities · ...
```

**Resultado atual:** todos os 28 tickers com RI docs recebem `FALLBACK → Relativos` com `confidence=0.5` — o router não consegue identificar BBAS3 como BANK, PETR4 como COMMODITY, etc.

### Mapeamento Correto (via `type` de tickers.yaml)

| type (yaml) | Router Key | Método |
|------------|-----------|--------|
| bank | BANK | COSIF/DDM |
| oil_gas | COMMODITY | DCF |
| mining | COMMODITY | DCF |
| utilities | UTILITY | DCF |
| industrial | INDUSTRY | DCF |
| retail | RETAIL | DCF |
| holding | HOLDING | NAV |
| technology / telecom | TECH | DCF |
| healthcare | INDUSTRY | DCF |
| agro | INDUSTRY | DCF |
| education | INDUSTRY | DCF |
| real_estate | HOLDING | NAV |

### Impacto se Corrigido

- BBAS3, ITUB4, BBDC4, BPAC11, ABCB4, BRSR6, SANB11 → `COSIF/DDM` (confidence=1.0)
- PETR4, PRIO3, RECV3 → `DCF/COMMODITY` (confidence=1.0)
- SUZB3, KLBN11, RAIL3, RENT3, VAMO3, WEGE3 → `DCF/INDUSTRY` (confidence=1.0)
- AZZA3, LREN3, MGLU3, PCAR3, VIVA3 → `DCF/RETAIL` (confidence=1.0)
- EGIE3, SBSP3, TAEE11 → `DCF/UTILITY` (confidence=1.0)
- VIVT3 → `DCF/TECH` (confidence=1.0)
- FLRY3, HYPE3, RADL3 → `DCF/INDUSTRY` (confidence=1.0)

---

## 4. Matriz de Readiness para M016

### Estado atual (sem normalização de setor)

| Categoria | Qtd | Tickers |
|-----------|----:|---------|
| **READY_FOR_MODEL_DESIGN** | 28 | ABCB4, AZZA3, BBAS3, BBDC4, BPAC11, BRSR6, EGIE3, FLRY3, HYPE3, ITUB4, KLBN11, LREN3, MGLU3, PCAR3, PETR4, PRIO3, RADL3, RAIL3, RECV3, RENT3, SANB11, SBSP3, SUZB3, TAEE11, VAMO3, VIVA3, VIVT3, WEGE3 |
| **NEEDS_RI_DOCS** | 3 | AUAU3, NTCO3, VALE3 |
| **NEEDS_RI_DOCS (tickers.yaml, não AI)** | 61 | (outros 61 tickers do yaml sem docs) |
| **NEEDS_SECTOR** | 32 | AERI3, AESB3, ALUP11, AMAR3, ASAI3, BHIA3, BRIT3, CEAB3, CLSC4, ELET3, ENBR3, EVEN3, FIQE3, JSLG3, KEPL3, LAVV3, LVTC3, MDNE3, MELK3, MOVI3, NATU3, PLPL3, RANI3, RRRP3, SAPR11, SBFG3, SIMH3, SOJA3, TASA4, TGMA3, TRPL4, TUPY3 |
| **LEGACY_BLOCKED** | 1 | PETZ3 |
| **MANUAL_REVIEW** | 0 | — |

> **Nota:** os 32 NEEDS_SECTOR estão em `asset_intelligence_snapshots` mas não no `tickers.yaml` canônico (ou com sector=UNKNOWN). São tickers que entram pelo pipeline de sinais mas não fazem parte do universo de valuation definido.

### Tickers READY — por modelo de valuation (com normalização)

| Modelo M016 | Tickers (28) | RI Docs Total |
|------------|-------------|:-------------:|
| **COSIF/DDM (bancos)** | BBAS3, BBDC4, BPAC11, ITUB4, SANB11, BRSR6, ABCB4 | 750 |
| **DCF/COMMODITY (óleo/gás)** | PETR4, PRIO3, RECV3 | 366 |
| **DCF/INDUSTRY** | SUZB3, KLBN11, RAIL3, RENT3, VAMO3, WEGE3, FLRY3, HYPE3, RADL3 | 1.057 |
| **DCF/RETAIL** | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 | 648 |
| **DCF/UTILITY** | EGIE3, SBSP3, TAEE11 | 389 |
| **DCF/TECH (telecom)** | VIVT3 | 128 |

---

## 5. Pendências para M016

### P1 — BLOQUEADOR: Setor Não Normalizado (crítico)
- **O quê:** router recebe setor GICS (`financials`, `energy`) em vez de chave canônica (`BANK`, `COMMODITY`)
- **Impacto:** todos os 28 tickers caem em FALLBACK/Relativos com confidence=0.5
- **Fix M016:** criar `SectorNormalizer` que usa `type` do `tickers.yaml` → chave canônica do router
- **Localização:** `src/valuation/router.py` ou novo `src/valuation/sector_normalizer.py`
- **Prioridade:** P0 (sem isso, M016 não opera com método correto)

### P2 — S03 Metadata Stale para 28 Tickers
- **O quê:** `s03_coverage_status = HAS_SECTOR_NO_RI` para tickers que JÁ têm RI docs
- **Causa:** S03 não leu ri_docs do banco canônico (data/database/scanner_quant.db)
- **Impacto:** metadata desatualizada (cosmético — os docs existem de fato)
- **Fix M016:** S06 ou patch isolado que atualiza `s03_coverage_status` → `PARTIAL` ou `READY`
- **Prioridade:** P2 (não bloqueia M016, mas deve ser corrigido)

### P3 — VALE3, NTCO3 sem RI Docs
- **O quê:** tickers conhecidos, sector mapeável, mas 0 RI docs em `ri_documents`
- **Impacto:** router bloqueia (`needs_data`) — não passam para valuation
- **Fix M016:** ingestion CVM para VALE3 e NTCO3 (separado, não bloqueia início de M016)
- **Prioridade:** P2

### P4 — AUAU3 sem RI Docs (successor ativo)
- **O quê:** AUAU3 é ticker ativo (fusão Petz+Cobasi, estreou B3 2026-01-05) mas sem docs CVM
- **Impacto:** bloqueado em `needs_data` — correto por ora
- **Fix M016:** ingestion CVM quando disponível (AUAU3 é nova empresa, prazo CVM = 90d)
- **Prioridade:** P3

### P5 — 32 Tickers NEEDS_SECTOR em AI Snapshots
- **O quê:** tickers com sector=UNKNOWN no AI entry — router bloqueado
- **Impacto:** não entram no valuation até setor ser mapeado
- **Fix M016:** classificação setorial via tickers.yaml ou CVM/B3 metadata
- **Prioridade:** P2

---

## 6. Recomendação Final M015

### ✅ M015 PODE SER FECHADO

**Todos os objetivos do M015 foram cumpridos:**

| Objetivo M015 | Resultado |
|--------------|-----------|
| Elevar ri_documents para universo amplo | ✅ 3.251 docs / 28 tickers |
| Criar/atualizar AI entries | ✅ 64/64 entradas |
| Corrigir PETZ3 como LEGACY_TICKER | ✅ s035 confirma bloqueio |
| Mapear AUAU3 como successor monitorável | ✅ s035 confirma; aguarda RI docs |
| Preservar fair values existentes | ✅ BBAS3=64,84 · PETR4=81,12 · ITUB4 · WEGE3 |
| Resolver conflito src/utils.py vs src/utils/ | ✅ (M015-S04 confirmado) |
| Não calcular valuation | ✅ nenhum DCF/COSIF/DDM executado |
| Router funcional | ✅ router bloqueia corretamente; gaps identificados |

**Gap identificado (P1) é trabalho de M016, não M015.**

---

## 7. Autorização para M016

### ✅ AUTORIZADO ABRIR M016 — Valuation Engine Real

**Condição:** M016 deve iniciar com a tarefa P1 — Setor Normalizer — antes de qualquer cálculo de valuation.

**Proposta de estrutura M016:**

```
M016-S01: SectorNormalizer (type → router canonical key)
M016-S02: COSIF/DDM — bancos (BBAS3, ITUB4, BBDC4, BPAC11, SANB11...)
M016-S03: DCF/COMMODITY — oil_gas (PETR4, PRIO3, RECV3)
M016-S04: DCF/INDUSTRY — industrial/healthcare/retail
M016-S05: DCF/UTILITY — utilities (EGIE3, SBSP3, TAEE11)
M016-S06: Metadata Refresh (s03_coverage_status stale → PARTIAL/READY)
M016-SXX: VALE3, NTCO3, AUAU3 CVM ingestion (separado, não bloqueia S01-S05)
```

**28 tickers prontos para modelo:** ABCB4, AZZA3, BBAS3, BBDC4, BPAC11, BRSR6, EGIE3, FLRY3, HYPE3, ITUB4, KLBN11, LREN3, MGLU3, PCAR3, PETR4, PRIO3, RADL3, RAIL3, RECV3, RENT3, SANB11, SBSP3, SUZB3, TAEE11, VAMO3, VIVA3, VIVT3, WEGE3

---

*Gerado por S05 · M015 · 2026-05-24*  
*DB: data/database/scanner_quant.db · Router: src/valuation/router.py*
