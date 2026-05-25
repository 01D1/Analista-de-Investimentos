# M016 — Sector Normalization and Valuation Model Engine

**Versão:** 1.0.0  
**Data:** 2026-05-25  
**Status:** 🟡 PLANEJADO — aguardando execução  
**Depends on:** M015 ✅ CLOSED (2026-05-24)  
**Predecessor gap:** D097 (SectorNormalizer) — registrado em M015-CLOSED.md

---

## Vision

Implementar o motor real de valuation setorial para os 28 tickers `READY_FOR_MODEL_DESIGN`.
O M016 transforma os dados organizados em M014/M015 em modelos de valuation concretos,
roteados corretamente por setor. Entrega: `fair_value`, `upside_pct`, `valuation_method` e
`confidence` reais — não mocks — para cada ticker elegível.

**Princípio:** valuar apenas o que se pode auditar. Sem dados = sem cálculo.

---

## Contexto Herdado de M015

| Fato | Valor |
|------|-------|
| AI entries | 64/64 |
| RI docs | 3.251 em 28 tickers |
| READY_FOR_MODEL_DESIGN | 28 tickers |
| NEEDS_RI_DOCS | 3 (VALE3, AUAU3, NTCO3) |
| NEEDS_SECTOR | 32 |
| LEGACY_TICKER | PETZ3 (bloqueado, successor=AUAU3) |
| Fair values preservados | PETR4=81,12 · BBAS3=64,84 · ITUB4=73,69 · WEGE3=40,16 |
| Gap crítico | SectorNormalizer — D097 |

### Por que todos os 28 caem em FALLBACK hoje

O router (`src/valuation/router.py`) espera chaves canônicas (`BANK`, `COMMODITY`, etc.).
O banco e o `tickers.yaml` armazenam GICS em lowercase (`financials`, `energy`, etc.).
Sem `SectorNormalizer`, `sector.upper()` nunca bate no `_SECTOR_METHOD_MAP` → todos
recebem `FALLBACK → Relativos` com `confidence=0.5`. **M016-S01 corrige isso antes
de qualquer cálculo.**

---

## Universo de Tickers M016

### 28 READY — distribuição por modelo

| Modelo | Type (yaml) | Tickers | RI Docs |
|--------|-------------|---------|--------:|
| **COSIF/DDM — Bancos** | `bank` | BBAS3, BBDC4, BPAC11, ITUB4, SANB11, BRSR6, ABCB4 | ~750 |
| **DCF — Oil & Gas** | `oil_gas` | PETR4, PRIO3, RECV3 | ~366 |
| **DCF — Industrial** | `industrial` | SUZB3, KLBN11, RAIL3, RENT3, VAMO3, WEGE3 | ~780 |
| **DCF — Healthcare→Industry** | `healthcare` | FLRY3, HYPE3, RADL3 | ~277 |
| **DCF — Retail** | `retail` | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 | ~648 |
| **DCF — Utility** | `utilities` | EGIE3, SBSP3, TAEE11 | ~389 |
| **DCF — Tech/Telecom** | `telecom` | VIVT3 | ~128 |

### Tickers fora de escopo M016

| Status | Tickers | Motivo |
|--------|---------|--------|
| NEEDS_RI_DOCS | VALE3, NTCO3 | 0 docs CVM — router bloqueia |
| NEEDS_RI_DOCS | AUAU3 | Successor ativo, sem RI ainda (prazo CVM) |
| LEGACY_TICKER | PETZ3 | Extinto por fusão 2026-01-02 — **permanentemente bloqueado** |
| NEEDS_SECTOR | 32 tickers | sector=UNKNOWN em AI snapshots |

---

## Mapeamento type → Router Canonical Key

Base para implementação do `SectorNormalizer` (S01):

| type (tickers.yaml) | Router Key | Método Principal | Método Alt |
|---------------------|-----------|-----------------|-----------|
| `bank` | `BANK` | `COSIF/DDM` | `DCF` |
| `holding` (fin.) | `HOLDING` | `NAV` | `DCF` |
| `oil_gas` | `COMMODITY` | `DCF` | `EV/EBITDA` |
| `mining` | `COMMODITY` | `DCF` | `EV/EBITDA` |
| `industrial` | `INDUSTRY` | `DCF` | `EV/EBITDA` |
| `healthcare` | `INDUSTRY` | `DCF` | `EV/EBITDA` |
| `agro` | `INDUSTRY` | `DCF` | `EV/EBITDA` |
| `education` | `INDUSTRY` | `DCF` | `EV/EBITDA` |
| `real_estate` | `HOLDING` | `NAV` | `DCF` |
| `retail` | `RETAIL` | `DCF` | `EV/EBITDA` |
| `utilities` | `UTILITY` | `DCF` | `RAB` |
| `technology` | `TECH` | `DCF` | `SOTP` |
| `telecom` | `TECH` | `DCF` | `SOTP` |
| _(desconhecido)_ | `FALLBACK_MULTIPLES` | `Relativos` | — |

**Fonte primária:** campo `type` do `tickers.yaml`.  
**Fallback secundário:** campo `sector` do banco (GICS), se `type` ausente.  
**Nunca inventar:** se ambos ausentes → `FALLBACK_MULTIPLES` (sem exceção).

---

## Slices — Visão Geral

| # | Slice | Prioridade | Depende | Status |
|---|-------|:-----------:|---------|--------|
| **S01** | SectorNormalizer | **P0 BLOQUEADOR** | — | ⬜ |
| **S02** | Bank Valuation Model (COSIF/DDM) | P1 | S01 | ⬜ |
| **S03** | Commodity / Oil & Gas Model (DCF) | P1 | S01 | ⬜ |
| **S04** | Industry / Retail / Utility / Tech Model (DCF) | P2 | S01 | ⬜ |
| **S05** | Metadata Refresh e Coverage Promotion | P2 | S02–S04 | ⬜ |
| **SXX** | CVM Ingestion VALE3 / NTCO3 / AUAU3 | P3 | — | ⬜ |

> S01 **bloqueia** S02, S03 e S04. SXX é paralelo e não bloqueia nada.

---

## S01 — SectorNormalizer (P0 BLOQUEADOR)

### Objetivo
Criar `src/valuation/sector_normalizer.py` que converte `type` (ou `sector` como fallback)
para a chave canônica do router, alimentado pelo `tickers.yaml` canônico.

### Escopo
- **Criar:** `src/valuation/sector_normalizer.py`
- **Criar:** `src/valuation/tickers_config.py` — loader do `tickers.yaml` (se não existir)
- **Integrar:** `get_valuation_method()` deve aceitar `type` diretamente como parâmetro
  OU o chamador normaliza antes via `SectorNormalizer.normalize(ticker)`
- **Validar:** smoke test com 28 tickers READY — todos devem receber chave ≠ `FALLBACK_MULTIPLES`

### O que NÃO faz
- Não calcula valuation
- Não altera banco
- Não sobrescreve sectores existentes em AI snapshots
- Não cria mocks

### Critérios de Aceite (S01-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `SectorNormalizer.normalize("BBAS3")` → `"BANK"` | `assert result == "BANK"` |
| AC-02 | `SectorNormalizer.normalize("PETR4")` → `"COMMODITY"` | `assert result == "COMMODITY"` |
| AC-03 | `SectorNormalizer.normalize("EGIE3")` → `"UTILITY"` | `assert result == "UTILITY"` |
| AC-04 | `SectorNormalizer.normalize("VIVT3")` → `"TECH"` | `assert result == "TECH"` |
| AC-05 | `SectorNormalizer.normalize("FLRY3")` → `"INDUSTRY"` | `assert result == "INDUSTRY"` |
| AC-06 | ticker desconhecido → `"FALLBACK_MULTIPLES"` (nunca raise) | `assert result == "FALLBACK_MULTIPLES"` |
| AC-07 | `get_valuation_method("BBAS3", normalized_sector)` → `COSIF_DDM`, confidence=1.0 | router smoke test |
| AC-08 | `get_valuation_method("PETR4", normalized_sector)` → `DCF`, confidence=1.0 | router smoke test |
| AC-09 | 28/28 tickers READY → confidence ≥ 1.0 após normalização | loop test |
| AC-10 | PETZ3 → `LEGACY_TICKER` (router não afetado pelo normalizer) | assert blocked=True |
| AC-11 | Nenhum fair_value calculado | 0 writes em asset_intelligence_snapshots |
| AC-12 | Nenhum mock criado | code review |

### Riscos S01

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| tickers.yaml em path diferente no scanner vs 12_PYTHON | Alta | Alto | Detectar via `config/` do projeto; fallback para env `TICKERS_YAML_PATH` |
| Ticker em AI snapshot sem correspondência em tickers.yaml | Média | Médio | Retorna `FALLBACK_MULTIPLES` — nunca raise; log warning |
| BMGB4/BPAN4/PINE4 banks sem RI → normalização OK mas router bloqueia por NEEDS_RI | Baixa | Baixo | Correto comportamento — normalizer ≠ desbloqueador |

---

## S02 — Bank Valuation Model (COSIF/DDM)

### Objetivo
Implementar `src/valuation/models/bank_model.py` com metodologia COSIF/DDM para bancos.
Calcular `fair_value` real a partir de dados fundamentalistas extraídos de RI docs.

### Tickers
BBAS3, BBDC4, BPAC11, ITUB4, SANB11, BRSR6, ABCB4 — **7 tickers, ~750 RI docs**

### Metodologia
```
DDM estágio 2 (Gordon Growth simplificado):
  fair_value = DPA_12m / (Ke - g)
  Ke = Rf + β × ERP + CDS_Brazil
  Rf = Selic (BCB série 432)
  g = crescimento sustentável = ROE × (1 - payout_ratio)

COSIF inputs (extraídos de ITR/DFP):
  - NIM (Net Interest Margin)
  - ROE (COSIF — patrimônio médio)
  - Índice de eficiência
  - Inadimplência (NPL)
  - Carteira de crédito
  - DPA (dividendo por ação)
  - Payout ratio histórico

Validações obrigatórias (D-BANK):
  - Ke > g (evitar divisão por número negativo)
  - fair_value dentro de 0.1x–5.0x market_price
  - ROE rastreável (não imputado)
  - NPL > 0 (banco sem inadimplência = dado suspeito)
```

### Precedência de fair values existentes
- BBAS3=64,84: preservar como referência; **não sobrescrever** sem validação explícita
- ITUB4=73,69: idem
- Tickers sem fair_value anterior: calcular livremente se dados presentes

### Critérios de Aceite (S02-AC)

| # | Critério |
|---|----------|
| AC-01 | `bank_model.calculate("BBAS3", inputs)` retorna `BankValuationResult` com `fair_value` não-None |
| AC-02 | `fair_value` dentro de 0.1× a 5.0× `market_price` |
| AC-03 | `valuation_method = "COSIF/DDM"` |
| AC-04 | `confidence ≥ 0.7` somente se ROE + DPA + Ke rastreáveis |
| AC-05 | BBAS3/ITUB4 existentes **não são sobrescritos** sem flag `force_recalc=True` |
| AC-06 | Nenhum input imputado (dado ausente → `confidence` reduzida, não estimativa) |
| AC-07 | Banco não alterado se qualquer validação falhar |
| AC-08 | `BankValuationResult.input_hash` populado (gate de regeneração) |

### Riscos S02

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Dados COSIF (NIM/ROE) não parseados de RI docs ainda | Alta | Alto | Bloquear cálculo se inputs=None; retornar `confidence=0` com `block_reason=MISSING_COSIF_DATA` |
| Ke < g para banco com ROE alto e crescimento otimista | Média | Alto | Validar antes de calcular; logar e bloquear |
| fair_value calculado 3x+ acima do mercado | Baixa | Médio | Clamping com aviso + `valuation_governance_status=FLAGGED_OUTLIER` |
| Dependência de tabela `b3_financials` inexistente | Alta | Alto | Diagnóstico inicial: se tabela ausente → S02 retorna `MISSING_DATA_SOURCE` |

---

## S03 — Commodity / Oil & Gas Valuation Model (DCF)

### Objetivo
Implementar `src/valuation/models/commodity_model.py` para petróleo & gás.
Aplicar DCF simplificado com premissas de preço do Brent + câmbio PTAX.

### Tickers
PETR4, PRIO3, RECV3 — **3 tickers, ~366 RI docs**

> **VALE3:** não entra em S03. `NEEDS_RI_DOCS` ativo → router bloqueado.
> Quando RI docs forem ingeridos via SXX, VALE3 passa a ser elegível automaticamente.

### Metodologia
```
DCF Oil & Gas (E&P):
  EV = Σ (FCF_t / (1+WACC)^t) + TV
  TV = FCF_n × (1+g) / (WACC - g)

  WACC = Ke × (E/V) + Kd × (D/V) × (1-T)
  Ke = Rf + β_setor × ERP + CDS_Brazil
  Rf = Selic (BCB)
  Kd = custo médio ponderado da dívida (ITR/DFP)
  FCF = EBITDA × (1 - impostos ajustados) - Capex - ΔCapital de Giro

Inputs upstream (RI):
  - Reservas provadas (1P) — barris de óleo equivalente
  - Custo de extração (lifting cost)
  - Capex E&P anual
  - Produção diária
  - Receita em USD (ajuste PTAX)

Premissas macro injetadas (nunca inventadas):
  - Brent (ICE): valor atual ou média 12m
  - PTAX (BCB série 1): date-specific
  - Selic (BCB série 432)
  - CDS Brasil (5Y)

Validações obrigatórias (D-COMMOD):
  - terminal_growth < WACC (P7 — evitar TV explosion)
  - fair_value dentro de 0.1x–5.0x market_price
  - Reservas rastreáveis (fonte: RI doc específico)
  - PTAX rastreável (fonte: BCB série 1)
```

### Critérios de Aceite (S03-AC)

| # | Critério |
|---|----------|
| AC-01 | `commodity_model.calculate("PETR4", inputs)` retorna `CommodityValuationResult` com `fair_value` não-None |
| AC-02 | `terminal_growth < WACC` validado antes de calcular TV |
| AC-03 | `fair_value` dentro de 0.1× a 5.0× `market_price` |
| AC-04 | VALE3 **não** entra em S03 (NEEDS_RI_DOCS) — router bloqueia antes |
| AC-05 | Brent e PTAX rastreáveis (fonte + data de referência registrados) |
| AC-06 | PETR4 fair_value=81,12 **não sobrescrito** sem `force_recalc=True` |
| AC-07 | `valuation_method = "DCF"` e `sector_model = "COMMODITY"` |
| AC-08 | `input_hash` populado para gate de regeneração |

### Riscos S03

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Reservas 1P não extraídas de RI docs | Média | Alto | Fallback para EV/EBITDA se reservas ausentes; flag `COSIF_FALLBACK` |
| Brent e PTAX atualizados exigem API BCB/ICE | Média | Médio | Usar última cotação disponível em banco; bloquear se > 5 dias desatualizado |
| RECV3 pequena produtora — dados incompletos nos ITRs | Alta | Médio | Aceitar EV/EBITDA como alternativa válida para small-cap E&P |
| TV explosion (g ≥ WACC) | Média | Alto | Validação hard-block antes de calcular; log + `FLAGGED_INVALID` |

---

## S04 — Industry / Retail / Utility / Tech Valuation Model (DCF)

### Objetivo
Implementar `src/valuation/models/dcf_model.py` — DCF universal para setores não-financeiros
e não-commodity: industrial, retail, utilities, healthcare, telecom.

### Tickers por grupo

| Grupo | Tickers | RI Docs |
|-------|---------|--------:|
| Industrial | SUZB3, KLBN11, RAIL3, RENT3, VAMO3, WEGE3 | ~780 |
| Healthcare→Industry | FLRY3, HYPE3, RADL3 | ~277 |
| Retail | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 | ~648 |
| Utility | EGIE3, SBSP3, TAEE11 | ~389 |
| Tech/Telecom | VIVT3 | ~128 |
| **Total** | **21 tickers** | **~2.222** |

### Metodologia
```
DCF Universal (IFRS):
  EV = Σ (FCFF_t / (1+WACC)^t) + TV
  TV = FCFF_n × (1+g) / (WACC - g)
  equity_value = EV - dívida_líquida
  fair_value = equity_value / shares_outstanding

  FCFF = EBIT × (1-T) + D&A - Capex - ΔCapital de Giro
  WACC = Ke × (E/V) + Kd × (D/V) × (1-T)

Ajustes setoriais:
  Utility: RAB (Regulatory Asset Base) como sanity check
  Retail: working capital intensivo → projeção detalhada de giro
  Healthcare: margem EBITDA normalizada (excl. PCLD atípico)
  Industrial: Capex de manutenção vs expansão separados
  Telecom: EBITDA - CapEx intensivo (ARPU × base)

Validações:
  - terminal_growth < WACC (hard-block)
  - EBITDA margin > 0 para 3 anos históricos
  - Dívida líquida rastreável (DFP/ITR)
  - Shares outstanding rastreáveis (B3/CVM)
```

### Critérios de Aceite (S04-AC)

| # | Critério |
|---|----------|
| AC-01 | `dcf_model.calculate(ticker, inputs)` retorna resultado para ≥ 1 ticker por grupo |
| AC-02 | `terminal_growth < WACC` validado — bloqueia se violado |
| AC-03 | `fair_value` dentro de 0.1× a 5.0× `market_price` |
| AC-04 | WEGE3 fair_value=40,16 **não sobrescrito** sem `force_recalc=True` |
| AC-05 | `valuation_method = "DCF"` + `sector_model` populado por grupo |
| AC-06 | MGLU3 (deterioração operacional) → `confidence` penalizada se EBITDA negativo |
| AC-07 | Utility: cálculo RAB disponível como métrica de validação cruzada |
| AC-08 | `input_hash` populado para todos os resultados |
| AC-09 | 0 tickers NEEDS_SECTOR entram neste modelo |

### Riscos S04

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| DFP/ITR não parseados → EBITDA/Capex ausentes | Alta | Alto | Retornar `MISSING_FINANCIALS`; não calcular; log ticker |
| MGLU3 / PCAR3 com EBITDA negativo | Alta | Médio | DCF não aplicável; fallback EV/EBITDA relativo + flag `DISTRESSED_TICKER` |
| Shares outstanding desatualizadas | Média | Médio | Usar última DFP disponível; avisar se > 6 meses |
| VIVT3 (telecom): modelo DCF menos preciso sem ARPU detalhado | Média | Baixo | DCF com EV/EBITDA como cross-check; confidence penalizada |

---

## S05 — Metadata Refresh e Coverage Promotion

### Objetivo
Corrigir o gap P2 identificado em M015: `s03_coverage_status = HAS_SECTOR_NO_RI` para
tickers que **já têm** RI docs. Atualizar metadados de cobertura após modelos calculados.

### Evidência do problema
```sql
-- 28 tickers têm ri_docs mas metadata ainda stale de S03
SELECT ticker, s03_coverage_status, ri_docs_count
FROM asset_intelligence_snapshots ai
JOIN (SELECT ticker, COUNT(*) as ri_docs_count FROM ri_documents GROUP BY ticker) ri
  ON ai.ticker = ri.ticker
WHERE ai.s03_coverage_status = 'HAS_SECTOR_NO_RI'
  AND ri.ri_docs_count > 0
-- Esperado: ~28 linhas
```

### Regras de promoção de status

| De | Para | Condição |
|----|------|----------|
| `HAS_SECTOR_NO_RI` | `PARTIAL` | ri_docs_count > 0 |
| `PARTIAL` | `READY` | fair_value calculado + confidence ≥ 0.7 |
| `NEEDS_RI_DOCS` | `PARTIAL` | ri_docs_count > 0 (após SXX) |
| `NEEDS_SECTOR` | sem mudança | sector ainda UNKNOWN → não promover |
| `LEGACY_TICKER` | **sem mudança jamais** | PETZ3 permanece bloqueado |

### Critérios de Aceite (S05-AC)

| # | Critério |
|---|----------|
| AC-01 | `s03_coverage_status` atualizado para ≥ 20 tickers com RI docs |
| AC-02 | PETZ3 permanece `LEGACY_TICKER` após S05 |
| AC-03 | VALE3/NTCO3/AUAU3 permanecem `NEEDS_RI_DOCS` até SXX |
| AC-04 | Tickers com `fair_value` calculado → `READY` |
| AC-05 | Tickers sem financials → `PARTIAL` (não `READY`) |
| AC-06 | 0 tickers NEEDS_SECTOR promovidos sem setor rastreável |
| AC-07 | Banco atualizado apenas com UPDATE controlado (não DELETE/TRUNCATE) |

---

## SXX — CVM Ingestion VALE3 / NTCO3 / AUAU3

### Objetivo
Ingestão de RI docs CVM para os 3 tickers bloqueados por `NEEDS_RI_DOCS`.
**Paralelo a S01–S05 — não bloqueia, não é bloqueado.**

### Restrições
- VALE3: priority=high; sector=materials/mining; `type=mining` → canonical=COMMODITY
- NTCO3: sector=consumer_staples; `type` a confirmar em tickers.yaml
- AUAU3: successor de PETZ3; empresa nova (IPO/fusão 2026-01); prazo CVM ainda correndo
- **AUAU3 só entra em valuation APÓS ri_docs_count > 0 E sector mapeável**

### Critérios de Aceite (SXX-AC)

| # | Critério |
|---|----------|
| AC-01 | VALE3: `ri_docs_count > 0` após SXX |
| AC-02 | NTCO3: `ri_docs_count > 0` após SXX |
| AC-03 | VALE3 passa para `PARTIAL` automaticamente após S05 |
| AC-04 | AUAU3: ingestão só se docs CVM disponíveis; não forçar |
| AC-05 | PETZ3 **não recebe docs** — `LEGACY_TICKER` permanente |

---

## Regras Imutáveis (Invariantes M016)

```
RULE-01  Não sobrescrever fair values existentes sem force_recalc=True explícito
RULE-02  Não calcular valuation para NEEDS_SECTOR, NEEDS_RI_DOCS ou LEGACY_TICKER
RULE-03  PETZ3 permanece LEGACY_TICKER para sempre neste milestone
RULE-04  AUAU3 só entra em valuation após ri_docs_count > 0
RULE-05  VALE3 só entra após SXX concluído
RULE-06  terminal_growth < WACC: hard-block antes de qualquer TV calculation
RULE-07  fair_value só gerado quando todos os inputs críticos rastreáveis
RULE-08  input_hash populado em todo ValuationResult para gate de regeneração
RULE-09  Nenhum mock criado; dados ausentes = bloquear, não imputar
RULE-10  Não alterar opções/OOS/paper/scheduler
RULE-11  Não rodar Playwright/Chromium/browser
RULE-12  S01 deve ser concluída e validada ANTES de qualquer execução de S02/S03/S04
```

---

## Ordem de Execução

```
╔══════════════════════════════════════════════════════╗
║  FASE 1 — BLOQUEADORA (executar antes de tudo)      ║
╠══════════════════════════════════════════════════════╣
║  M016-S01: SectorNormalizer                         ║
║  → Smoke test: 28/28 tickers confidence ≥ 1.0       ║
╚══════════════════════════════════════════════════════╝
            ↓ S01 PASSED
╔══════════════════════════════════════════════════════╗
║  FASE 2 — PARALELO (executar após S01)              ║
╠══════════════════════════════════════════════════════╣
║  M016-S02: Bank Model   ←── 7 tickers               ║
║  M016-S03: Commodity    ←── 3 tickers               ║
║  M016-SXX: CVM Ingestion ←── paralelo, independente ║
╚══════════════════════════════════════════════════════╝
            ↓ S02 + S03 em andamento
╔══════════════════════════════════════════════════════╗
║  FASE 3 — DEPENDENTE (executar após S02/S03 stable) ║
╠══════════════════════════════════════════════════════╣
║  M016-S04: DCF Universal ←── 18 tickers             ║
╚══════════════════════════════════════════════════════╝
            ↓ S02 + S03 + S04 done
╔══════════════════════════════════════════════════════╗
║  FASE 4 — CONSOLIDAÇÃO                              ║
╠══════════════════════════════════════════════════════╣
║  M016-S05: Metadata Refresh + Coverage Promotion    ║
╚══════════════════════════════════════════════════════╝
```

---

## Success Criteria — M016

| Critério | Target |
|----------|--------|
| SectorNormalizer: 28/28 tickers com chave canônica correta | 100% |
| Tickers com fair_value calculado | ≥ 15 / 28 |
| Tickers `READY` após S05 | ≥ 10 |
| Nenhum fair_value anterior sobrescrito | 0 sobrescrições não autorizadas |
| PETZ3 permanece LEGACY_TICKER | 100% |
| VALE3/NTCO3/AUAU3 fora do valuation principal | 100% |
| Validação `terminal_growth < WACC`: 0 violações em produção | 0 explosões de TV |
| `input_hash` populado em todos os resultados | 100% |
| 0 mocks criados | 0 |

---

## Riscos Arquiteturais Transversais

| ID | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|:-------------:|:-------:|-----------|
| R01 | Tabela `b3_financials` inexistente ou vazia | **Alta** | **Alto** | Diagnóstico em S01; SE ausente → todos os modelos retornam `MISSING_DATA_SOURCE`; M016 entrega normalização mas não fair values |
| R02 | RI docs existem mas dados financeiros não parseados | Alta | Alto | Separar "RI ingestion" de "RI parsing"; M016 pode calcular apenas onde parser extraiu valores |
| R03 | WACC não calculável sem Selic/CDS atuais | Média | Alto | Fallback: Selic última série BCB + CDS proxy histórico |
| R04 | Múltiplos tickers com EBITDA negativo (MGLU3, PCAR3, RECV3) | Alta | Médio | Flag `DISTRESSED_TICKER`; retornar EV/EBITDA relativo como fallback |
| R05 | Shares outstanding desatualizadas geram fair value errado | Média | Alto | Validar data da DFP; se > 365 dias → penalizar confidence |
| R06 | `save_valuation_result()` é stub — sem implementação real | **Alta** | **Crítico** | Implementar escritas controladas em S02 antes de calcular qualquer valor |

---

## Dependências Técnicas

### Arquivos existentes relevantes
```
src/valuation/router.py              ← S01 interage (adiciona normalize pre-step)
src/valuation/valuation_inputs.py    ← S02/S03/S04 lêem inputs de aqui
src/valuation/valuation_results.py   ← S02/S03/S04 escrevem via save_valuation_result()
src/valuation/valuation_store.py     ← stub save_valuation_result() — implementar em S02
src/valuation/valuation_coverage.py  ← S05 usa para refresh
12_PYTHON/config/tickers.yaml        ← fonte de type/sector para S01
data/database/scanner_quant.db       ← banco canônico
```

### Novos arquivos a criar em M016
```
src/valuation/sector_normalizer.py          ← S01
src/valuation/tickers_config.py             ← S01 (loader yaml)
src/valuation/models/__init__.py            ← S02
src/valuation/models/bank_model.py          ← S02
src/valuation/models/commodity_model.py     ← S03
src/valuation/models/dcf_model.py           ← S04
src/valuation/models/valuation_engine.py    ← orquestrador (S04 ou S05)
tests/valuation/test_sector_normalizer.py   ← S01
tests/valuation/test_bank_model.py          ← S02
tests/valuation/test_commodity_model.py     ← S03
tests/valuation/test_dcf_model.py           ← S04
```

---

## Decisões Registradas M016

| ID | Decisão |
|----|---------|
| D099 | `SectorNormalizer` usa `type` (yaml) como fonte primária; `sector` GICS como fallback |
| D100 | `type` desconhecido → `FALLBACK_MULTIPLES` (nunca raise, nunca inventar) |
| D101 | fair values existentes (PETR4/BBAS3/ITUB4/WEGE3) preservados; sobrescrita exige `force_recalc=True` |
| D102 | VALE3 aguarda SXX; não forçar ingestion em S03 |
| D103 | PETZ3 = LEGACY_TICKER permanente neste milestone |
| D104 | `b3_financials` ausente = `MISSING_DATA_SOURCE` (não crash, não mock) |
| D105 | `save_valuation_result()` stub deve ser implementado em S02 antes de qualquer write |
| D106 | `input_hash` obrigatório em todo `ValuationResult` (gate anti-regeneração) |
| D107 | `terminal_growth < WACC` = hard-block (P7 — anti-TV explosion) |
| D108 | healthcare + agro + education → `INDUSTRY` canonical key (sem modelo próprio em M016) |

---

## Notas de Execução

1. **Iniciar com S01** — nenhuma outra slice pode produzir resultados corretos sem ela.
2. **Diagnóstico de `b3_financials`** — antes de S02, verificar se a tabela existe no banco.
   Se ausente, S02/S03/S04 entregam apenas o normalizer integrado + stub funcional.
3. **S02 antes de S04** — o `save_valuation_result()` deve ser validado com bancos (menor risco)
   antes de escalar para 21 tickers DCF.
4. **SXX é independente** — pode ser executado por fora, em qualquer ordem, sem bloquear S01–S05.

---

*Roadmap M016 criado em 2026-05-25.*  
*Baseado em: M015-CLOSED.md · M015-S05-READINESS-REPORT.md · M014-ARCHITECTURE.md*  
*Próxima etapa: `/gsd-execute-phase M016-S01`*
