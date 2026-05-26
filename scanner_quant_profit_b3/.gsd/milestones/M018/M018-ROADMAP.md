# M018 — Controlled Fair Value Calculation, Validation and Preserved Value Review

**Versão:** 1.0.0  
**Data:** 2026-05-26  
**Fechado em:** 2026-05-26  
**Status:** ✅ FECHADO  
**Depends on:** M017 ✅ CLOSED (2026-05-26)  
**Predecessor gap:** D124 — 17 tickers READY_TO_CALCULATE + 1 PARTIAL_INPUTS com inputs reais populados, 0 fair_values calculados, 9 fair_values preservados aguardando revalidação

---

## Vision

Calcular fair values reais de forma controlada para os 18 tickers novos e revalidar os 9 fair values
preservados de origem legada. M018 **não substitui** valores existentes automaticamente — todo novo
cálculo passa por sanidade, flags de qualidade e validação explícita antes de ser promovido a oficial.

**Princípio:** calculado ≠ oficial. Todo fair_value tem status rastreável:
`preliminary` → `validated` → `approved`. Nenhum sobrescreve `preserved` sem `force_recalc=True`
explícito e classificação ≥ `REVIEW_PRESERVED`.

> **"Os modelos M016 têm motores. O M017 encheu o tanque. M018 dá a primeira partida — com freio de mão."**

---

## Contexto Herdado de M017

| Fato | Valor |
|------|-------|
| Registros em `valuation_financial_inputs` | 47.621 |
| `financial_inputs_bridge` | Operacional (18/18 dry-run OK) |
| Tickers READY_TO_CALCULATE | 17 |
| Tickers PARTIAL_INPUTS | 1 (PCAR3 — DISTRESSED) |
| Fair values PRESERVE_EXISTING | 9 (origem legada — não alterar sem validação) |
| Fair values novos calculados | **0** (M017 encerrou com write=False) |
| Testes passando (post-M017) | 401/401 |
| Modelos disponíveis | bank, commodity, utility, retail, industry |

### Fair Values Preservados (origem legada)

| Ticker | Setor | Fair Value Preservado | Nota |
|--------|-------|----------------------:|------|
| ABCB4  | Bank  | R$ 210,50 | Banco — modelo DDM/ROE |
| BBAS3  | Bank  | R$ 64,84  | Banco — modelo DDM/ROE |
| BBDC4  | Bank  | R$ 34,63  | Banco — modelo DDM/ROE |
| BPAC11 | Bank  | R$ 8,46   | Banco — modelo DDM/ROE |
| BRSR6  | Bank  | R$ 4,66   | Banco — modelo DDM/ROE |
| ITUB4  | Bank  | R$ 73,69  | Banco — modelo DDM/ROE |
| SANB11 | Bank  | R$ 86,79  | Banco — modelo DDM/ROE |
| PETR4  | Commodity | R$ 81,12 | Petróleo — modelo DCF/EV |
| WEGE3  | Industry  | R$ 40,16 | Industrial — modelo DCF |

> Todos os 9 têm CVM inputs disponíveis em `valuation_financial_inputs`. M018 recalcula em
> modo comparação — **sem sobrescrever** o valor preservado.

### Universo M018 — 18 Tickers Novos

| Modelo | Ticker | Status Inputs | Flag |
|--------|--------|:-------------:|------|
| COMMODITY | PRIO3 | READY | — |
| COMMODITY | RECV3 | READY | qualidade_media |
| UTILITY | EGIE3 | READY | — |
| UTILITY | SBSP3 | READY | qualidade_media |
| UTILITY | TAEE11 | READY | — |
| RETAIL | AZZA3 | READY | — |
| RETAIL | LREN3 | READY | — |
| RETAIL | MGLU3 | READY | distressed_risk |
| RETAIL | PCAR3 | PARTIAL_INPUTS | distressed_confirmed |
| RETAIL | VIVA3 | READY | qualidade_media |
| INDUSTRY | FLRY3 | READY | — |
| INDUSTRY | HYPE3 | READY | — |
| INDUSTRY | KLBN11 | READY | — |
| INDUSTRY | RADL3 | READY | — |
| INDUSTRY | RAIL3 | READY | — |
| INDUSTRY | RENT3 | READY | — |
| INDUSTRY | SUZB3 | READY | — |
| INDUSTRY | VAMO3 | READY | qualidade_media |

---

## Arquitetura de Resultados — Ciclo de Vida do Fair Value

M018 introduz um ciclo de vida explícito para todo fair value calculado:

```
                 ┌─────────────────────────────────────────────────┐
                 │          valuation_results (nova tabela)         │
                 │                                                   │
  Cálculo ──►   │  preliminary_fair_value   (S01/S03)              │
                 │  ├─ sanity_check_passed?  (S04)                  │
                 │  ├─ confidence_score                              │
                 │  └─ flags[ ]                                      │
                 │                                                   │
  Validação ──► │  validated_fair_value     (S04 → humano)          │
                 │  └─ validation_notes                              │
                 │                                                   │
  Aprovação ──► │  approved_fair_value      (explícito)             │
                 │  └─ promoted_at                                   │
                 └─────────────────────────────────────────────────┘

Para PRESERVE_EXISTING (9 tickers):
  preserved_fair_value  (M016 legado — imutável sem force_recalc)
  recalculated_fair_value  (M018-S02 — comparação)
  difference_pct
  classification: KEEP_PRESERVED | REVIEW_PRESERVED | REPLACE_CANDIDATE | INSUFFICIENT_DATA
```

Nenhuma escrita em `asset_intelligence_snapshots` sem status `approved`.

---

## Slices — Visão Geral

| # | Slice | Prioridade | Depende | Status |
|---|-------|:-----------:|---------|--------|
| **S01** | Valuation Result Schema and Safe Writer | **P0 BLOQUEADOR** | — | ✅ |
| **S02** | Preserved Fair Value Review | P1 | S01 | ✅ |
| **S03** | Controlled Calculation Batch for New Tickers | P1 | S01 | ✅ |
| **S04** | Sanity Check and Outlier Detection | P2 | S02 + S03 | ✅ |
| **S05** | Dashboard Integration | P3 | S04 | ✅ |

> S01 **bloqueia tudo**. S02 e S03 são paralelos após S01. S04 consolida ambos. S05 expõe resultados.

---

## S01 — Valuation Result Schema and Safe Writer

### Objetivo

Criar a tabela `valuation_results` no banco `scanner_quant.db` com ciclo de vida explícito:
`preliminary` → `validated` → `approved`. Implementar `ValuationResultsWriter` com proteção
contra sobrescrita de valores preservados.

### Escopo

- **Criar:** migration SQL para `valuation_results` (schema abaixo)
- **Criar:** `src/valuation/valuation_results_store.py` — CRUD com regras de proteção
- **Implementar:** `write_preliminary(ticker, ...)` → bloqueia se `approved_fair_value` existe
- **Implementar:** `write_comparison(ticker, ...)` → modo exclusivo para PRESERVE_EXISTING
- **Implementar:** `promote_to_approved(ticker, force=False)` → exige `sanity_check_passed=True`
- **Garantir:** PRESERVE_EXISTING nunca tem `approved_fair_value` sobrescrito por chamada automática
- **Backup:** snapshot de `scanner_quant.db` antes de qualquer migration

### Schema `valuation_results`

```sql
CREATE TABLE valuation_results (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT NOT NULL,
    valuation_date          DATE NOT NULL,
    -- Valores por ciclo de vida
    preserved_fair_value    REAL,           -- legado M016 (só PRESERVE_EXISTING)
    preliminary_fair_value  REAL,           -- calculado M018, não validado
    recalculated_fair_value REAL,           -- para PRESERVE_EXISTING: cálculo novo em modo comparação
    validated_fair_value    REAL,           -- aprovado humano ou aprovado automaticamente por S04
    approved_fair_value     REAL,           -- promovido a oficial
    -- Contexto de mercado no momento do cálculo
    market_price            REAL,
    upside_pct              REAL,           -- (fair_value / market_price - 1) × 100
    upside_preserved        REAL,           -- upside usando preserved_fair_value
    upside_recalculated     REAL,           -- upside usando recalculated_fair_value
    difference_pct          REAL,           -- (recalc / preserved - 1) × 100 (só PRESERVE_EXISTING)
    -- Metadados do cálculo
    method_used             TEXT NOT NULL,  -- 'DDM' | 'DCF' | 'EV_EBITDA' | 'HYBRID'
    confidence              TEXT NOT NULL,  -- 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT'
    input_quality           TEXT NOT NULL,  -- 'FULL' | 'PARTIAL' | 'DISTRESSED' | 'MANUAL_REVIEW'
    source                  TEXT NOT NULL,  -- 'M018_CONTROLLED' | 'M016_LEGACY'
    -- Classificação para PRESERVE_EXISTING
    preservation_status     TEXT,           -- 'KEEP_PRESERVED' | 'REVIEW_PRESERVED' |
                                            --  'REPLACE_CANDIDATE' | 'INSUFFICIENT_DATA'
    -- Controle de sanidade e flags
    sanity_check_passed     INTEGER,        -- 0 | 1 | NULL (não avaliado)
    block_reason            TEXT,           -- motivo de bloqueio quando sanity=0
    flags                   TEXT,           -- JSON array: ["distressed_risk", "qualidade_media", ...]
    -- Rastreabilidade
    calculated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at             DATETIME,
    calculation_notes       TEXT,
    UNIQUE(ticker, valuation_date, source)
);
```

### Regras de Proteção — `ValuationResultsWriter`

```python
class ValuationResultsWriter:
    PRESERVE_EXISTING = {
        'ABCB4', 'BBAS3', 'BBDC4', 'BPAC11', 'BRSR6',
        'ITUB4', 'SANB11', 'PETR4', 'WEGE3'
    }

    def write_preliminary(self, ticker, fair_value, ...):
        """
        Bloqueia se ticker in PRESERVE_EXISTING — usar write_comparison().
        Bloqueia se approved_fair_value já existe para este ticker/date.
        Persiste como preliminary apenas — nunca altera asset_intelligence_snapshots.
        """

    def write_comparison(self, ticker, recalculated_value, ...):
        """
        Exclusivo para PRESERVE_EXISTING.
        Preserva preserved_fair_value intacto.
        Salva recalculated_fair_value e calcula difference_pct.
        NÃO define approved_fair_value.
        """

    def promote_to_approved(self, ticker, force=False):
        """
        Só executa se sanity_check_passed=True.
        Se ticker in PRESERVE_EXISTING: requer force=True explícito.
        Atualiza approved_fair_value e promoted_at.
        NÃO escreve em asset_intelligence_snapshots — escopo de M019.
        """
```

### Critérios de Aceite (S01-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | Tabela `valuation_results` criada no DB | `SELECT name FROM sqlite_master WHERE type='table'` |
| AC-02 | Constraint `UNIQUE(ticker, valuation_date, source)` ativa | INSERT duplicado → IntegrityError |
| AC-03 | `write_preliminary()` bloqueia chamada para PRESERVE_EXISTING | teste unitário: assert raises |
| AC-04 | `write_comparison()` não altera `preserved_fair_value` existente | teste unitário: valor não muda |
| AC-05 | `promote_to_approved(ticker in PRESERVE_EXISTING, force=False)` → bloqueado | assert raises |
| AC-06 | `promote_to_approved()` bloqueia quando `sanity_check_passed=False` | assert raises |
| AC-07 | `asset_intelligence_snapshots` inalterado após qualquer operação do S01 | diff antes/depois |
| AC-08 | Migration transacional — falha não deixa tabela parcial | rollback test |
| AC-09 | Backup de `scanner_quant.db` criado antes da migration | arquivo de backup presente |
| AC-10 | `PRAGMA integrity_check` passa após migration | output = "ok" |

### Riscos S01

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Schema incompleto — campo necessário para S04 ausente | Média | Médio | Revisar todos os campos de sanidade S04 antes de finalizar DDL |
| `write_comparison()` inadvertidamente sobrescreve `preserved_fair_value` | Baixa | Crítico | Constraint DB + assert no código; teste unitário explícito |
| Conflito de nome de coluna com tabela futura (M019) | Baixa | Baixo | Prefixar colunas de lifecycle com status explícito |

---

## S02 — Preserved Fair Value Review

### Objetivo

Rodar recálculo dos 9 fair values preservados em modo comparação — sem sobrescrever nenhum valor.
Cada ticker recebe `recalculated_fair_value`, `difference_pct`, `upside_preserved`, `upside_recalculated`
e classificação `preservation_status`. Gerar relatório específico dos 9 para revisão humana.

### Escopo

- **Executar:** `financial_inputs_bridge.run(ticker, write=False)` para os 9 PRESERVE_EXISTING
- **Capturar:** `recalculated_fair_value` da bridge sem persistir como `approved`
- **Calcular:** `difference_pct = (recalc / preserved − 1) × 100`
- **Calcular:** `upside_preserved = (preserved / market_price − 1) × 100`
- **Calcular:** `upside_recalculated = (recalc / market_price − 1) × 100`
- **Persistir:** via `write_comparison()` em `valuation_results` (sem `approved_fair_value`)
- **Classificar:** cada ticker com `preservation_status`
- **Gerar:** `docs/M018_S02_PRESERVED_REVIEW.md`

### Critérios de Classificação `preservation_status`

| Classificação | Critério |
|---------------|----------|
| `KEEP_PRESERVED` | `\|difference_pct\|` ≤ 15% **E** `confidence ≥ MEDIUM` |
| `REVIEW_PRESERVED` | `\|difference_pct\|` entre 15–40% **OU** `confidence = LOW` |
| `REPLACE_CANDIDATE` | `\|difference_pct\|` > 40% **E** `confidence ≥ MEDIUM` |
| `INSUFFICIENT_DATA` | Bridge retorna `INSUFFICIENT_INPUTS` ou `confidence = INSUFFICIENT` |

> Classificação é informativa — M018 **não substitui** valor preservado com base nela.
> Promoção requer `force_recalc=True` + validação humana explícita em milestone futuro.

### Critérios de Aceite (S02-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | 9/9 PRESERVE_EXISTING têm linha em `valuation_results` com `source='M018_COMPARISON'` | `SELECT COUNT(*) WHERE source='M018_COMPARISON'` = 9 |
| AC-02 | `preserved_fair_value` idêntico ao valor legado para todos os 9 | comparação com valores hardcoded acima |
| AC-03 | `approved_fair_value` = NULL para todos os 9 após S02 | `SELECT * WHERE approved_fair_value IS NOT NULL` = 0 |
| AC-04 | `difference_pct` calculado e populado | `SELECT * WHERE difference_pct IS NULL AND source='M018_COMPARISON'` = 0 |
| AC-05 | `preservation_status` classificado para todos os 9 | `SELECT * WHERE preservation_status IS NULL` = 0 |
| AC-06 | `market_price` populado com preço real (yfinance/cotahist) | não-NULL, não-zero |
| AC-07 | Relatório `docs/M018_S02_PRESERVED_REVIEW.md` gerado com tabela comparativa | arquivo presente |
| AC-08 | `asset_intelligence_snapshots` inalterado | diff antes/depois |

### Relatório Obrigatório — `M018_S02_PRESERVED_REVIEW.md`

Estrutura:

```markdown
# M018-S02 — Preserved Fair Value Review

## Resumo Executivo
- N tickers KEEP_PRESERVED
- N tickers REVIEW_PRESERVED
- N tickers REPLACE_CANDIDATE
- N tickers INSUFFICIENT_DATA

## Tabela Comparativa
| Ticker | Preservado | Recalculado | Δ% | Preço Atual |
         Upside Pres. | Upside Recalc | Método | Confiança | Status |

## Análise por Ticker
[seção individual por ticker com contexto setorial]

## Recomendações
[lista de ações sugeridas por classificação]
```

### Riscos S02

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Bridge retorna `INSUFFICIENT_INPUTS` para banco ≥ 2 dos 9 | Média | Médio | Classificar como `INSUFFICIENT_DATA`; documentar campo faltante |
| `difference_pct` > 40% para vários bancos (COSIF vs modelo recalibrado) | Alta | Baixo | Esperado — modelos bancários têm sensibilidade a taxa Selic; documentar como `REVIEW_PRESERVED`, não erro |
| `market_price` desatualizado (cotahist vs yfinance lag) | Baixa | Baixo | Usar yfinance como fonte primária; cotahist como fallback |

---

## S03 — Controlled Calculation Batch for New Tickers

### Objetivo

Calcular `preliminary_fair_value` para os 18 novos tickers usando `financial_inputs_bridge`
com `write=False` primeiramente, depois persistir via `write_preliminary()`. Nenhum valor é
promovido a `approved` neste slice — apenas calculado e registrado como preliminar.

### Escopo

- **Executar:** bridge para 17 READY_TO_CALCULATE + PCAR3 (PARTIAL_INPUTS)
- **Persistir:** `write_preliminary()` em `valuation_results` para cada ticker
- **Aplicar:** flags de qualidade conforme universo M018 (distressed_risk, qualidade_media etc.)
- **PCAR3:** calcular via EV/EBITDA only; registrar `input_quality='DISTRESSED'`; block de DCF
- **MGLU3:** registrar `input_quality='DISTRESSED'` se FCF negativo; método EV/EBITDA preferencial
- **RECV3, SBSP3, VAMO3:** registrar `flags=['qualidade_media']`
- **Gerar:** `docs/M018_S03_PRELIMINARY_RESULTS.md` com tabela de resultados por ticker

### Lógica de Execução por Ticker

```python
BATCH_NEW_TICKERS = [
    # Commodity
    'PRIO3', 'RECV3',
    # Utility
    'EGIE3', 'SBSP3', 'TAEE11',
    # Retail
    'AZZA3', 'LREN3', 'MGLU3', 'PCAR3', 'VIVA3',
    # Industry
    'FLRY3', 'HYPE3', 'KLBN11', 'RADL3', 'RAIL3', 'RENT3', 'SUZB3', 'VAMO3',
]

DISTRESSED = {'PCAR3', 'MGLU3'}
QUALITY_FLAGS = {'RECV3': ['qualidade_media'], 'SBSP3': ['qualidade_media'],
                 'VAMO3': ['qualidade_media'], 'VIVA3': ['qualidade_media']}

for ticker in BATCH_NEW_TICKERS:
    # 1. Dry-run (write=False)
    result = bridge.run(ticker, write=False)

    # 2. Aplicar flags de qualidade
    flags = QUALITY_FLAGS.get(ticker, [])
    if ticker in DISTRESSED or result.fcf < 0:
        flags.append('distressed_risk')

    # 3. Persistir como preliminary (nunca como approved)
    writer.write_preliminary(
        ticker=ticker,
        preliminary_fair_value=result.fair_value,
        market_price=result.market_price,
        method_used=result.method,
        confidence=result.confidence,
        input_quality='DISTRESSED' if ticker in DISTRESSED else result.input_quality,
        flags=flags,
        source='M018_CONTROLLED',
    )
    # 4. NÃO chamar promote_to_approved()
```

### Critérios de Aceite (S03-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | ≥ 15 dos 18 tickers têm `preliminary_fair_value` em `valuation_results` | `SELECT COUNT(DISTINCT ticker) WHERE source='M018_CONTROLLED'` ≥ 15 |
| AC-02 | `approved_fair_value` = NULL para todos os 18 após S03 | `SELECT * WHERE approved_fair_value IS NOT NULL AND source='M018_CONTROLLED'` = 0 |
| AC-03 | PCAR3 com `input_quality='DISTRESSED'` e `method_used='EV_EBITDA'` | assert no relatório |
| AC-04 | MGLU3 com `flags` contendo `'distressed_risk'` (se FCF negativo) | assert condicional |
| AC-05 | PRESERVE_EXISTING (9 tickers) não têm linha com `source='M018_CONTROLLED'` | `SELECT * WHERE source='M018_CONTROLLED' AND ticker IN (...)` = 0 |
| AC-06 | `market_price` populado e não-zero para todos os tickers calculados | assert |
| AC-07 | Relatório `docs/M018_S03_PRELIMINARY_RESULTS.md` gerado com tabela por ticker | arquivo presente |
| AC-08 | `asset_intelligence_snapshots` inalterado | diff antes/depois |
| AC-09 | 401+ testes passando | `pytest tests/` |

### Riscos S03

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Bridge falha para ≥ 3 tickers por input insuficiente não detectado em M017 | Média | Médio | Logar como `INSUFFICIENT_DATA`; não bloquear batch |
| VAMO3 com modelo inadequado (industry com dados parciais) | Alta | Baixo | Flag `qualidade_media` + `confidence=LOW`; registrar como preliminary; não promover |
| Fair value negativo ou zero por FCF negativo em distressed | Alta | Baixo | Correto — extrair valor real; flag `distressed_risk`; bloquear auto-promoção em S04 |
| Método de banco (DDM/ROE) inadvertidamente aplicado a non-bank | Baixa | Alto | Bridge já roteia por setor; adicionar assert: `ticker in BANK_TICKERS → method in DDM/ROE` |

---

## S04 — Sanity Check and Outlier Detection

### Objetivo

Validar todos os resultados de S02 e S03. Cada fair value calculado passa por checagem
automática de sanidade. Resultados que falham são bloqueados (`sanity_check_passed=0`
com `block_reason`). Apenas os que passam podem ser promovidos.

### Escopo

- **Executar:** sanity checks em todos os `preliminary_fair_value` e `recalculated_fair_value`
- **Atualizar:** `sanity_check_passed` e `block_reason` em `valuation_results`
- **Gerar:** `docs/M018_S04_SANITY_REPORT.md` com resultado por ticker e classificação final
- **NÃO promover** a `approved_fair_value` — essa decisão é humana (ou M019)

### Regras de Sanidade (obrigatórias)

| ID | Regra | Condição de Falha | Block Reason |
|----|-------|------------------|--------------|
| R01 | Fair value positivo | `fair_value ≤ 0` | `NEGATIVE_OR_ZERO_FV` |
| R02 | Range preço de mercado | `fair_value < 0.1 × market_price` OU `fair_value > 5.0 × market_price` | `FV_OUT_OF_RANGE_0.1X_5X` |
| R03 | Upside razoável | `upside_pct < -80%` OU `upside_pct > 400%` | `UPSIDE_EXTREME` |
| R04 | FCF consistente | FCF negativo + método DCF puro → usar EV/EBITDA | `NEGATIVE_FCF_DCF_METHOD` |
| R05 | Confiança mínima | `confidence = INSUFFICIENT` → não promover | `INSUFFICIENT_CONFIDENCE` |
| R06 | Distressed bloqueado | `input_quality = DISTRESSED` → bloqueia auto-promoção | `DISTRESSED_NO_AUTO_PROMOTE` |
| R07 | Diferença contra preservado | para PRESERVE_EXISTING: `\|difference_pct\| > 40%` → escalar para humano | `LARGE_DEVIATION_FROM_PRESERVED` |
| R08 | Método setorial | banco com método não-DDM/ROE | `WRONG_METHOD_SECTOR_BANK` |
| R09 | Método setorial | commodity com método não-DCF/EV | `WRONG_METHOD_SECTOR_COMMODITY` |
| R10 | Cross-check inputs | `ebitda = None AND fcf = None` → INSUFFICIENT | `MISSING_CRITICAL_INPUTS` |

### Critérios de Aceite (S04-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `sanity_check_passed` populado para todos os tickers S02 + S03 | `SELECT * WHERE sanity_check_passed IS NULL` = 0 |
| AC-02 | Tickers com `block_reason` têm `sanity_check_passed = 0` | assert consistência |
| AC-03 | PCAR3: `DISTRESSED_NO_AUTO_PROMOTE` no `block_reason` | assert |
| AC-04 | Nenhum fair value negativo aprovado | `SELECT * WHERE approved_fair_value ≤ 0` = 0 |
| AC-05 | Nenhum fair value fora do range 0.1×–5.0× promovido automaticamente | assert |
| AC-06 | PRESERVE_EXISTING com `\|difference_pct\| > 40%` marcados como `LARGE_DEVIATION_FROM_PRESERVED` | verificar relatório |
| AC-07 | Relatório `docs/M018_S04_SANITY_REPORT.md` gerado com resultado por ticker | arquivo presente |
| AC-08 | Tabela `sanity_summary` no relatório: N passou / N bloqueado / N distressed / N para revisão humana | seção presente |
| AC-09 | `asset_intelligence_snapshots` inalterado | diff antes/depois |

### Riscos S04

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Muitos tickers fora do range 0.1×–5.0× (premissas setoriais divergentes) | Média | Médio | Investigar por setor; ajustar premissas antes de reprocessar; não relaxar o range |
| `market_price` stale (dados desatualizados) distorce upside | Média | Médio | Usar preço com data ≤ 5 dias; log de age do preço no relatório |
| Sanity check muito restritivo bloqueia todos os RETAIL/DISTRESSED | Alta | Baixo | Correto — distressed são bloqueados por design; documentar |

---

## S05 — Dashboard Integration

### Objetivo

Expor os resultados de M018 no Valuation Hub existente: valores preservados, recalculados,
classificações KEEP/REVIEW/REPLACE, novos preliminares, status de sanidade, flags e confidence.
Nenhum novo cálculo é feito em S05 — apenas leitura e exibição do que já está em `valuation_results`.

### Escopo

- **Adicionar** aba ou seção ao Valuation Hub: "M018 — Review e Cálculo Controlado"
- **Exibir:** tabela de PRESERVE_EXISTING com comparação preservado vs recalculado + `preservation_status`
- **Exibir:** tabela de novos tickers com `preliminary_fair_value`, `confidence`, `flags`, `sanity_check_passed`
- **Exibir:** botão/flag visual diferenciando `preliminary` / `validated` / `approved`
- **Exibir:** `block_reason` para tickers bloqueados (coluna ou tooltip)
- **NÃO** exibir `approved_fair_value` para tickers ainda não promovidos — apenas `preliminary`
- **Garantir:** leitura de `valuation_results`; nenhum write via dashboard

### Estrutura Visual Sugerida

```
┌─────────────────────────────────────────────────────────────────────────┐
│  VALUATION HUB — M018 Review                                            │
├─────────────────────────────────────────────────────────────────────────┤
│  📌 PRESERVE_EXISTING (9 tickers)                                       │
│  ┌──────────┬──────────┬────────────┬──────┬───────────────────────┐   │
│  │ Ticker   │ Preserv. │ Recalc.    │  Δ%  │ Status                │   │
│  ├──────────┼──────────┼────────────┼──────┼───────────────────────┤   │
│  │ ABCB4    │ R$210.50 │ R$ ???.??  │ +X%  │ KEEP_PRESERVED ✅     │   │
│  │ BBAS3    │ R$ 64.84 │ R$ ???.??  │ +X%  │ REVIEW_PRESERVED ⚠️   │   │
│  │ ...      │          │            │      │                       │   │
│  └──────────┴──────────┴────────────┴──────┴───────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  🆕 NOVOS TICKERS — PRELIMINAR (18 tickers)                             │
│  ┌──────────┬──────────┬─────────┬──────────┬────────┬────────────┐    │
│  │ Ticker   │ Prelim.  │ Preço   │  Upside  │ Conf.  │ Flags      │    │
│  ├──────────┼──────────┼─────────┼──────────┼────────┼────────────┤    │
│  │ EGIE3    │ R$ ???   │ R$ ???  │  +??%    │ HIGH   │ —          │    │
│  │ PCAR3    │ R$ ???   │ R$ ???  │  +??%    │ LOW    │ DISTRESSED │    │
│  │ ...      │          │         │          │        │            │    │
│  └──────────┴──────────┴─────────┴──────────┴────────┴────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Critérios de Aceite (S05-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | Seção M018 visível no Valuation Hub | inspeção visual |
| AC-02 | 9 PRESERVE_EXISTING exibidos com preservado + recalculado + `preservation_status` | tabela presente |
| AC-03 | 18 novos tickers exibidos com `preliminary_fair_value`, `confidence`, `flags` | tabela presente |
| AC-04 | Tickers com `sanity_check_passed=0` exibem `block_reason` visível | destaque visual |
| AC-05 | Dashboard não realiza write — apenas read de `valuation_results` | code review |
| AC-06 | `approved_fair_value` NULL exibido como "Pendente" ou equivalente | inspeção visual |
| AC-07 | Tickers PCAR3/MGLU3 com badge visual DISTRESSED | inspeção visual |

### Riscos S05

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Dashboard existente com acoplamento a tabela antiga (sem `valuation_results`) | Média | Médio | Adicionar seção M018 como componente novo; não refatorar existente |
| `preservation_status` com valor inesperado em runtime (enum inconsistente) | Baixa | Baixo | Normalizar para display: `None → 'PENDING'` |

---

## Regras Imutáveis (Invariantes M018)

```
RULE-01  Não sobrescrever fair_values PRESERVE_EXISTING sem force_recalc=True explícito
RULE-02  preliminary_fair_value ≠ approved_fair_value — ciclo de vida obrigatório
RULE-03  Nenhuma escrita em asset_intelligence_snapshots em M018
RULE-04  S02 usa write_comparison() — nunca write_preliminary() para PRESERVE_EXISTING
RULE-05  PCAR3 permanece DISTRESSED — EV/EBITDA apenas; bloquear promoção automática
RULE-06  fair_value negativo → sanity FAIL → não promover (R01)
RULE-07  fair_value fora do range 0.1×–5.0× price → sanity FAIL → não promover (R02)
RULE-08  LLM não calcula — todos os números vêm do Financial Engine (P1 pitfall herdado)
RULE-09  Nenhum mock criado
RULE-10  Não alterar parser (dfp_parser, metric_extractor, cvm_extractor)
RULE-11  Não alterar opções/OOS/paper/scheduler
RULE-12  S01 (schema + writer) deve ser concluída ANTES de S02/S03/S04/S05
RULE-13  S02 e S03 podem rodar em paralelo após S01
RULE-14  S04 só inicia após S02 E S03 concluídas
RULE-15  S05 só inicia após S04 concluída
RULE-16  Backup de scanner_quant.db antes de qualquer migration (S01)
RULE-17  write=False em todos os dry-runs pré-persistência
RULE-18  PETZ3/VALE3/AUAU3/NTCO3 fora de escopo M018
RULE-19  401+ testes M017 devem continuar passando ao final de M018
RULE-20  Promoção para approved exige sanity_check_passed=True — sem exceções automáticas
```

---

## Ordem de Execução

```
╔══════════════════════════════════════════════════════════╗
║  FASE 1 — SCHEMA (bloqueadora)                          ║
╠══════════════════════════════════════════════════════════╣
║  M018-S01: Valuation Result Schema and Safe Writer      ║
║  → CREATE TABLE valuation_results                       ║
║  → ValuationResultsWriter com proteção PRESERVE         ║
║  → Testes unitários de proteção                         ║
╚══════════════════════════════════════════════════════════╝
              ↓ S01 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 2 — CÁLCULO (paralelo após S01)                   ║
╠══════════════════════════════════════════════════════════╣
║  M018-S02: Preserved Fair Value Review (9 tickers)      ║
║  → write_comparison() para PRESERVE_EXISTING            ║
║  → difference_pct + preservation_status                 ║
║                                                         ║
║  M018-S03: Controlled Batch for New Tickers (18)        ║
║  → write_preliminary() para 18 novos                    ║
║  → flags de qualidade e distressed                      ║
╚══════════════════════════════════════════════════════════╝
              ↓ S02 + S03 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 3 — SANIDADE                                      ║
╠══════════════════════════════════════════════════════════╣
║  M018-S04: Sanity Check and Outlier Detection           ║
║  → 10 regras de sanidade por ticker                     ║
║  → sanity_check_passed + block_reason                   ║
║  → Relatório com N passou / N bloqueado                 ║
╚══════════════════════════════════════════════════════════╝
              ↓ S04 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 4 — EXPOSIÇÃO                                     ║
╠══════════════════════════════════════════════════════════╣
║  M018-S05: Dashboard Integration                        ║
║  → Seção M018 no Valuation Hub                          ║
║  → PRESERVE_EXISTING: comparativo + status              ║
║  → Novos: preliminary + flags + sanidade                ║
╚══════════════════════════════════════════════════════════╝
```

---

## Success Criteria — M018

| Critério | Target |
|----------|--------|
| `valuation_results` criada e populada | ≥ 24 linhas (9 comparações + ≥ 15 preliminares) |
| 9 PRESERVE_EXISTING com `recalculated_fair_value` e `preservation_status` | 9/9 — 100% |
| `preserved_fair_value` inalterado para todos os 9 | 9/9 — 0 sobrescrições |
| `approved_fair_value` = NULL para todos após M018 | 100% — promoção é escopo M019 |
| Novos tickers com `preliminary_fair_value` e `sanity_check_passed` | ≥ 15 dos 18 |
| PCAR3 como DISTRESSED com bloqueio de promoção automática | 100% |
| Sanity check executado para 100% dos resultados | 0 linhas com `sanity_check_passed IS NULL` |
| Seção M018 visível e funcional no Valuation Hub | ✅ |
| 0 escritas em `asset_intelligence_snapshots` | 0 |
| 0 mocks criados | 0 |
| 401+ testes M017 continuam passando | ≥ 401/401 |
| Relatórios: S02_PRESERVED_REVIEW + S03_PRELIMINARY_RESULTS + S04_SANITY_REPORT | 3/3 |

---

## Riscos Arquiteturais Transversais

| ID | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|:-------------:|:-------:|-----------|
| R01 | Bridge retorna fair_value muito diferente do preservado para bancos (sensibilidade Selic) | **Alta** | Médio | Classificar como REVIEW_PRESERVED; documentar contexto macro; não é erro |
| R02 | `market_price` desatualizado distorce sanity check | Média | Médio | Usar yfinance com cache ≤ 5 dias; logar data do preço |
| R03 | MGLU3/PCAR3 com fair_value negativo passa pelo batch sem ser flagrado | Média | Alto | R01 do S04 bloqueia negativo; flag `distressed_risk` obrigatória |
| R04 | Método errado aplicado por setor (DCF em banco) | Baixa | Alto | Assert de método × setor em S04 (R08/R09) |
| R05 | `valuation_results` schema incompleto — campo de S04 ausente | Média | Médio | Revisar todos os campos de sanidade antes de finalizar S01 |
| R06 | Dashboard S05 acoplado a schema antigo | Média | Baixo | Adicionar seção nova; não refatorar componentes existentes |

---

## Dependências Técnicas

### Arquivos existentes relevantes

```
data/database/scanner_quant.db                          ← banco canônico (recebe S01 migration)
src/valuation/financial_inputs_bridge.py                ← bridge M017 — motor de cálculo
src/ingestion/financial_inputs_store.py                 ← leitura de valuation_financial_inputs
src/valuation/models/bank_model.py                      ← modelo banco (DDM/ROE)
src/valuation/models/commodity_model.py                 ← modelo commodity (DCF/EV)
src/valuation/models/utility_model.py                   ← modelo utility (DCF)
src/valuation/models/retail_model.py                    ← modelo retail (EV/EBITDA + DCF)
src/valuation/models/industry_model.py                  ← modelo industry (DCF + EV)
docs/M017_S05_DRY_RUN_MATRIX.csv                        ← referência de resultado dry-run M017
```

### Novos arquivos a criar em M018

```
src/valuation/valuation_results_store.py          ← S01 (schema + ValuationResultsWriter)
migrations/002_valuation_results.sql              ← S01 (migration DDL)
tests/test_valuation_results_store.py             ← S01 (proteções PRESERVE_EXISTING)
docs/M018_S02_PRESERVED_REVIEW.md                ← S02 (relatório comparativo 9 tickers)
docs/M018_S03_PRELIMINARY_RESULTS.md             ← S03 (tabela preliminary 18 tickers)
docs/M018_S04_SANITY_REPORT.md                   ← S04 (N passou / N bloqueado / N distressed)
```

---

## Decisões Registradas M018

| ID | Decisão |
|----|---------|
| D124 | `valuation_results` = tabela canônica para outputs de valuation com ciclo de vida explícito |
| D125 | Ciclo de vida: `preliminary` → `validated` → `approved` — nenhuma escrita em `asset_intelligence_snapshots` em M018 |
| D126 | PRESERVE_EXISTING usam `write_comparison()` exclusivo — nunca `write_preliminary()` |
| D127 | Promoção para `approved_fair_value` é escopo de M019, não M018 |
| D128 | PCAR3 permanece DISTRESSED com bloqueio de promoção automática |
| D129 | Sanity check R02 (0.1×–5.0× price) é regra rígida — não relaxar para nenhum ticker |
| D130 | S02 e S03 podem executar em paralelo após S01 — sem dependência entre si |

---

## Notas de Execução

1. **Começar por S01** — schema e writer devem existir antes de qualquer cálculo.
2. **Fazer backup do DB antes da migration S01** — hábito crítico; banco tem 47.621 registros reais.
3. **S02 e S03 são paralelos** — S02 é mais rápido (9 tickers vs 18); rodar juntos ou S02 primeiro.
4. **Esperar PCAR3 negativo ou próximo de zero** — dado real de empresa DISTRESSED; não investigar como erro.
5. **MGLU3** — FCF provavelmente negativo; EV/EBITDA deve ser método preferencial; aceitar como DISTRESSED.
6. **Diferença grande nos bancos (S02) é esperada** — modelos bancários são sensíveis a Selic e ROE base.
   `difference_pct` > 15% para ≥ 3 dos 7 bancos seria normal — classificar como `REVIEW_PRESERVED`.
7. **S04 é rigoroso por design** — é esperado que alguns tickers sejam bloqueados; esse é o ponto.
8. **S05 é read-only** — qualquer tentativa de write no dashboard é bug, não feature.
9. **M019 (não M018) fará a promoção para oficial** — M018 termina com todos os valores como `preliminary`.

---

*Roadmap M018 criado em 2026-05-26. Fechado administrativamente em 2026-05-26.*  
*Baseado em: M017-CLOSED.md · M017-S05 · git commit a91223a · 401/401 testes · dry-run matrix 18/18 tickers.*  
*Ver: M018-CLOSED.md · M018-SUMMARY.md · M018-VALIDATION.md*  
*Próxima etapa: M019 — Fair Value Promotion and Official Approval.*
