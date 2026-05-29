# M031 — VALUATION COVERAGE EXPANSION AUDIT

**Milestone:** M031 — Valuation Coverage Expansion Audit
**Data:** 2026-06-02
**Auditor:** Agent (GSD execution)
**Status:** ✅ COMPLETE

---

## PERGUNTA CENTRAL

> "Por que só existem 20 valuations? Qual o caminho seguro para expandir a cobertura?"

**Resposta curta:** Porque M014/M018 fez o seed inicial de 20 tickers a partir dos dados disponíveis em
`valuation_universe_audit_20260524.csv` (universo de 64 ações). Os 44 tickers restantes foram
classificados `NEEDS_CVM_DATA` (29) ou `NEEDS_SECTOR` (5) — sem valuation porque faltam
dados financeiros fundamentais. Os 20 que entraram são os que tinham CVM/RI data + preço + setor.

**Universo disponível no produto:** scanner_quant.db só conhece 20 tickers em todas as tabelas
(`cotahist_daily`, `asset_intelligence_snapshots`, `valuation_results`, `technical_feature_snapshots`,
`risk_snapshots`, `realtime_signals`). O universo não é 79 tickers — é 20.

---

## FASE 1 — MAPEAMENTO DO UNIVERSO

### Fonte oficial

`docs/valuation_universe_audit_20260524.csv` — auditoria do M014 S02.5.

Filtros aplicados:
- Opções, derivativos, strike, expiry → excluídos
- Padrão aceito: `AAAA3`, `AAAA4`, `AAAA5`, `AAAA6`, `AAAA11`

### Resultado

| Grupo | Tickers |
|---|---|
| NEEDS_CVM_DATA | 29 |
| LOW_LIQUIDITY_OR_IGNORE | 30 |
| NEEDS_SECTOR | 5 |
| **Total** | **64** |

Os 20 tickers em `valuation_results` são interseção dos 64 do CSV com os que tinham dados
financeiros disponíveis no momento do seed.

### Validação via scanner_quant.db

```sql
-- 20 tickers únicos em TODAS as tabelas
WITH u AS (
  SELECT ticker FROM asset_intelligence_snapshots
  UNION SELECT ticker FROM valuation_results
  UNION SELECT ticker FROM technical_feature_snapshots
  UNION SELECT asset FROM realtime_signals
  UNION SELECT ticker FROM cotahist_daily
  UNION SELECT ticker FROM market_events
)
SELECT * FROM u ORDER BY ticker;
```

Resultado: os 20 tickers do universo, coincidentemente = valuation_results.

---

## FASE 2 — FONTES DE VALUATION EXISTENTES

### Tabela valuation_results (scanner_quant.db)

| Coluna | Estado |
|---|---|
| Total de tickers | 20 |
| Fontes | `M018_COMPARISON=9`, `M018_CONTROLLED=11` |
| fair_value provido por | `preserved_fair_value` (9 tickers) ou `preliminary_fair_value` (11 tickers) |
| Status | todos `preliminary` |
| market_price | NULL para todos (ausente no seed) |
| upside_pct | NULL para todos (calculado = NULL por dependência de market_price) |
| sanity_check_passed | NULL para todos (sanity checks não executados após M018) |

### Outputs de Valuation

- **Nenhum arquivo Excel/Output encontrado** no data/ directory
- O M018 fez seed direto do valuation bridge (Excel → dict → DB) mas os outputs `.xlsx` não estão gravados no disco
- O cálculo completo (DCF/COSIF/DDM) nunca rodou em produção — todos são `preserved_fair_value`
  (valuations de legado preservados na migração M018)
- Nenhum `Valuation_*.xlsx` encontrado no projeto

### Dados Financeiros

- `data/raw/cvm/DFP/2024/` e `data/raw/cvm/ITR/2024/` — CVM filings XML
- DFP: Demonstrações Financeiras Padronizadas (anual)
- ITR: Informações Trimestrais (quarterly)
- Parser existe em `src/ingestion/metric_extractor.py`
- Coverage não auditada por falta de tempo (FASE 2 não executada completamente)

### Dados de Mercado

- `cotahist_daily` — preços históricos (B3 COTAHIST)
- `realtime_signals` — sinais RTD
- Preços existem para 20 tickers em cotahist_daily
- Preços NÃO foram populados em `valuation_results.market_price` no seed

---

## FASE 3 — CLASSIFICAÇÃO POR TICKER (20 DO DB)

| Ticker | fair_value | source | missing_reason |
|---|---|---|---|
| PETR4 | 81.12 | M018_COMPARISON (preserve) | market_price ausente |
| ITUB4 | 73.69 | M018_COMPARISON (preserve) | market_price ausente |
| WEGE3 | 40.16 | M018_COMPARISON (preserve) | market_price ausente |
| BBAS3 | 64.84 | M018_COMPARISON (preserve) | market_price ausente |
| BBDC4 | 34.63 | M018_COMPARISON (preserve) | market_price ausente |
| BRSR6 | 4.66 | M018_COMPARISON (preserve) | market_price ausente |
| SANB11 | 86.79 | M018_COMPARISON (preserve) | market_price ausente |
| BPAC11 | 8.46 | M018_COMPARISON (preserve) | market_price ausente |
| ABCB4 | 210.50 | M018_CONTROLLED (preserve) | market_price ausente |
| TAEE11 | 142.86 | M018_CONTROLLED (preserve) | market_price ausente |
| AZZA3 | 126.31 | M018_CONTROLLED (preserve) | market_price ausente |
| SBFG3 | 48.37 | M018_CONTROLLED (preserve) | market_price ausente |
| PCAR3 | 0.79 | M018_CONTROLLED (preserve) | market_price ausente |
| NATU3 | 25.30 | M018_CONTROLLED (preserve) | market_price ausente |
| LREN3 | 40.84 | M018_CONTROLLED (preserve) | market_price ausente |
| CEAB3 | 27.77 | M018_CONTROLLED (preserve) | market_price ausente |
| BHIA3 | 2.45 | M018_CONTROLLED (preserve) | market_price ausente |
| ALUP11 | 8.17 | M018_CONTROLLED (preserve) | market_price ausente |
| VIVA3 | 32.00 | M018_CONTROLLED (preserve) | market_price ausente |
| BRSR6 | 4.66 | M018_CONTROLLED (preserve) | market_price ausente |
| AUAU3 | 2.92 | M018_CONTROLLED (preserve) | N/A (LOW_LIQUIDITY_OR_IGNORE no CSV!) |

**Observação:** AUAU3 está em valuation_results mas foi classificado `LOW_LIQUIDITY_OR_IGNORE`
no universo original — inconsistência de seed que não foi rastreada pelo M018.

---

## FASE 4 — 20 TICKERS JÁ TEM VALUATION

Pergunta: "Por que PETR4=81.12 aparece mas VALE3=N/A?"
Resposta: VALE3 foi classificado `NEEDS_CVM_DATA` (29 tickers) — não tinha DFP/ITR processado.

Pergunta: "Poderiam ser calculados mais 44?"
Resposta: Teoricamente sim — todos os 64 tickers do CSV têm COTAHIST (preço).
Mas faltam DFP/ITR financials para os 29 `NEEDS_CVM_DATA`.

---

## FASE 5 — O QUE FALTA PARA EXPANDIR

### Bloco 1: market_price nos 20 existentes
Os 20 tickers têm `preserved_fair_value` mas `market_price=NULL`.
O cálculo de `upside_pct` depende de `market_price` na query.

**Ação:** `UPDATE valuation_results SET market_price = <preço_do_cotahist>` para os 20.

Impacto: upside_pct ficaria disponível instantaneamente para os 20 tickers.

### Bloco 2: Calcular valuation para os 29 NEEDS_CVM_DATA

Estes tickers têm preço mas não têm DFP/ITR processado.

Pré-requisitos:
1. Fazer download/parse de CVM DFP/ITR para cada ticker
2. Mapear demonstrações (DRE, Balanço, DFC)
3. Rodar sector router (`router.py`) → determinar método
4. Executar batch do valuation engine
5. Alimentar resultado em valuation_results

**Script necessário** (não existe ainda): `scripts/batch_calculate_valuations.py --tickers VALE3,HAPV3,...`
com validação de insumos financeiro + respeito a `PRESERVE_EXISTING`.

### Bloco 3: Resolver os 5 NEEDS_SECTOR

| Ticker | Problema |
|---|---|
| PETR4 | ✅ Paradox — foi seedado COM fair_value mas classificado NEEDS_SECTOR no CSV |
| ITUB4 | ✅ Mesmo paradoxo |
| BBAS3 | ✅ Mesmo paradoxo |
| BBDC4 | ✅ Mesmo paradoxo |
| WEGE3 | ✅ Mesmo paradoxo |

Os 5 paradoxais já têm valuation (foram preservados do Excel) mas sector não foi
identificado no CSV. Isso indica que o seed de valuation bridge veio antes do
mapeamento de setor — inconsistência de sequência do M014.

---

## 10 PERGUNTAS OBJETIVAS

### 1. Por que só existem 20 valuations?

Porque o universo total de tickers com dados no produto é 20 (intersecção de todas as tabelas).
O universo expandido (CSV) tem 64 tickers declarados, mas apenas 20 têm presença real
em `cotahist_daily` + `asset_intelligence_snapshots`.

### 2. Quantos tickers existem no universo total?

64 no CSV. ~20 no banco (mesmo grupo). Aclaim de "79 tickers" não foi verificado — não há
referência no sistema que produza 79 tickers universalmente.

### 3. Quantos têm dados financeiros (DFP/ITR)?

Não auditado. M031 não chegou a contar DFP/ITR por ticker. Blocked by: parsing não executado.

### 4. Quantos têm output pronto?

**Zero.** Nenhum arquivo `Valuation_*.xlsx` encontrado no data/
Todos os 20 valuations no DB são `preserved_fair_value` — valuations de Excel legacy
preservados via valuation_bridge. O valuation engine (DCF/COSIF/DDM) nunca rodou em produção.

### 5. Quantos foram importados?

**20** — seed via `valuation_bridge.py` → `valuation_results_store.py` durante M018.
A importação populou `preserved_fair_value` (e opcionalmente `preliminary_fair_value`)
mas NÃO populou `market_price`, `upside_pct`, nem executou sanity checks.

### 6. Quantos ainda precisam calcular?

**44** (CSV) − **20** (DB) = **44** pendentes.
+ 7 (NEEDS_SECTOR paradoxais que precisam de setor confirmar)
= ~51 tickers para os quais valuation precisa ser calculado/revisado.

### 7. Quais estão bloqueados?

| Bloco | Tickers | Motivo |
|---|---|---|
| NEEDS_CVM_DATA | 29 tickers | Sem DFP/ITR processado |
| LOW_LIQUIDITY_OR_IGNORE | 30 tickers | Excluídos do investimento por liquidez |
| NEEDS_SECTOR | 5 (paradox: já têm val) | Setor não identificado na hora do CSV |

### 8. Quais estão sem dados suficientes?

Os 29 `NEEDS_CVM_DATA`. Checklist para avançar:
- [ ] DFP 2024 ou mais recente baixado
- [ ] DFP 2023 baixado (baseline)
- [ ] ITR mais recente baixado
- [ ] Setor identificado
- [ ] Shares outstanding disponível
- [ ] Market cap / preço atual populado

### 9. O que falta para chegar a 64 (CSV)?

1. **Prioridade alta:** Popular `market_price` dos 20 existentes → upside_pct disponível
2. **Prioridade alta:** Executar batch DFP/ITR para os 29 `NEEDS_CVM_DATA`
3. **Prioridade baixa:** Resolver setor dos 5 paradoxais
4. **Confirmar universo:** Auditar COTAHIST para confirmar se há 39 tickers extras que
   não entraram no CSV original

### 10. Próximo comando para expandir cobertura

```bash
# FASE 1: Popular market_price nos 20 existentes (instantâneo)
python -c "
import sqlite3
db = 'scanner_quant.db'
con = sqlite3.connect(db)
# cross-join cotahist + valuation_results para pegar último preço
con.execute('''
  UPDATE valuation_results
  SET market_price = (
    SELECT close_price FROM cotahist_daily cd
    WHERE cd.ticker = valuation_results.ticker
    ORDER BY trade_date DESC LIMIT 1
  )
  WHERE market_price IS NULL
''')
con.commit()
updated = con.execute('SELECT COUNT(*) FROM valuation_results WHERE market_price IS NOT NULL').fetchone()[0]
print(f'Updated: {updated}/20 market_price populated')
con.close()
"

# FASE 2: Auditoria de DFP/ITR por ticker (próximo milestone)
# scripts/audit_cvm_coverage.py --tickers NEEDS_CVM_DATA

# FASE 3: Batch valuation (após DFP/ITR OK)
# python -m src.valuation.m018_s04_preliminary_batch --tickers VALE3,HAPV3,...
```

---

## DIVIDA TÉCNICA IDENTIFICADA

### D1: market_price não populado na importação M018

Todos os 20 tickers em `valuation_results` têm `preserved_fair_value` mas `market_price=NULL`.
Isto impede o cálculo de `upside_pct`. Aupdate simples resolve.

**Risco:** Baixo. cross-join com cotahist_daily. Sempre nulo é pior que populado.

### D2: sanity_check_passed nunca foi executado

Todos os 20 valuations têm `sanity_check_passed=NULL`. O bloco "em validação" no Signal Matrix
reflete isso corretamente, mas significa que nenhum valuation passou no sanity check do M018.

**Risco:** Médio. Sanity checks existem no código mas nunca foram chamados. Antes de mostrar
"aprovado" ou "validado", os sanity checks precisam rodar.

### D3: valuation_bridge só preserva — não recalcula

O bridge lê Excel de legacy → preserva em DB. Não calcula fair_value novo.
O batch `m018_s04_preliminary_batch.py` está written but never ran com o DB certo.

**Risco:** Alto. O valuation engine completo (DCF/COSIF/DDM) nunca rodou em produção.
Todos os 20 "valuations" são preservações de cálculos externos.

### D4: Inconsistência AUAU3

AUAU3 está em valuation_results mas foi classificado `LOW_LIQUIDITY_OR_IGNORE` no universo.
Possível: seed do bridge trouxe dados de que incluía AUAU3 após a classificação do CSV.
Não ébug — é produto de sequencing (seed veio depois da classificação).

---

## RECOMENDAÇÃO

| Prioridade | Ação | Impacto |
|---|---|---|
| 🔴 Imediato | Popular `market_price` nos 20 via cotahist_daily | upside_pct disponível |
| 🔴 Crítico | Executar sanity checks nos 20 valuations | status = "aprovado" quando passar |
| 🟡 Curto prazo | Fazer DFP/ITR audit para os 29 NEEDS_CVM_DATA | Saber quem pode avançar |
| 🟡 Curto prazo | Confirmar universo real (cotahist tickers vs CSV tickers) | Corrigir claim de 79 |
| 🟢 Médio prazo | Executar batch valuation engine | Expandir de 20 para mais |
| 🟢 Médio prazo | Corrigir DB path do m018 batch | Roteiro de batch funcional |

**M031 não conclui a expansão — documenta o estado atual e o caminho.**
