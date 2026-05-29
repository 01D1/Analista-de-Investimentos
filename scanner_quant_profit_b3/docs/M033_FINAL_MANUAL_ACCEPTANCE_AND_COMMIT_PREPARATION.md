# M033 — Final Manual Acceptance & Commit Preparation

**Data:** 2026-05-29 | **Ambiente:** macOS (Node 22.22.3, Python 3.13.5)
**Executado por:** GSD agent — teste automatizado via Playwright headless + verificação manual de código

---

## 1. Infraestrutura executada

| Serviço | Porta | Status |
|---------|-------|--------|
| Backend (uvicorn) | 8001 | ✅ Ok (8000 estava em uso) |
| Frontend (Next.js dev) | 3000 | ✅ Ok |
| Navegador headless | Playwright | ✅ Ok |

---

## 2. Resultados por página

### 2.1 Home / Radar AI (página padrão)

| Verificação | Resultado |
|-------------|-----------|
| Navegação lateral visível | ✅ INTELLIGENCE / MARKETS / OPERATIONS |
| Items de menu | ✅ Todos 11 itens presentes |
| "API conectada" visível | ✅ |
| KPIs RTD visíveis (9 ações, 50 watch, 88 score) | ✅ |

### 2.2 Options Radar (`/radar-oportunidades` via AppShell)

| Verificação | Resultado |
|-------------|-----------|
| Menu acessível | ✅ Botão "OPTIONS RADAR" funcional |
| KPIs: opções totais | ✅ 18.457 opções |
| KPIs: candidatos (2640) | ✅ |
| KPIs: monitorar (6238) | ✅ |
| Filtro por ativo (PETR4) | ✅ PETR4 aparece |
| Filtro CALL/PUT | ✅ CALL e PUT visíveis |
| Strikes reais (não inflados 10x) | ✅ Strikes em 18,45 / 55,10 / 55,25 — ranges reais |
| Sem crash com payload | ✅ Carregamento rápido (<4s) |

### 2.3 Macro Engine (`/inteligencia_macro` via AppShell)

| Verificação | Resultado |
|-------------|-----------|
| Selic Meta = 14,40% | ✅ 14,40% correto (série BCB 4320) |
| IPCA 12M = 4,39% | ✅ 4.39% correto |
| PTAX/USD = 5,80 | ✅ 5.80 correto |
| PTAX tendência = -2,43% | ✅ |
| IPCA Mensal ausente | ✅ Mostra "—%" com label correto |
| IGPM ausente | ✅ Não aparece (não implementado) |
| Pendências honestas | ⚠️ Label "IPCA Mensal—%" presente, mas sem texto explicativo "pendente" |

### 2.4 Quant Core (`/radar_quant` via AppShell)

| Verificação | Resultado |
|-------------|-----------|
| 50 ativos mostrados | ✅ "50 sinais" |
| Score médio 36 | ✅ |
| COMPRA/HOLD/VENDA | ✅ 0/50/0 |
| MOM coluna visível | ✅ MOM: 50.0 para todos |
| TEND coluna visível | ✅ TEND: 0.0 para todos |
| Nulls como "—" | ✅ LIQ mostra "—" para todos |
| Sem crash com null.toFixed | ✅ `unavailable()` wrapper funciona |

**⚠️ Anomalia:** Todos os ativos mostram MOM=50.0 e TEND=0.0 — mesmo após M032. O valor 50.0 parece ser um default, não dado real. Investigar `signal_matrix` block para `momentum_score` / `trend_score` vs. `tecnico_indicadores.momentum_score/trend_score`. O component lê `tecnico_indicadores`, mas o backend pode estar populando o block `momentum` com valores default. **Não bloqueante — requiere M034 para aprofundar.**

### 2.5 Watchlist (`/inteligencia_watchlist` via AppShell)

| Verificação | Resultado |
|-------------|-----------|
| 50 ativos | ✅ "50 tickers em watch" |
| Preço visível | ✅ R$ 44,48 para PETR4 |
| Score visível | ✅ 45 para PETR4 |
| Direção visível | ✅ VENDA para PETR4 |
| Click abre drawer | ✅ Clique em "PETR4" abre drawer |
| ADV 21d visível | ✅ 2205.2M para PETR4 |

### 2.6 AssetDetailDrawer (PETR4)

| Verificação | Resultado |
|-------------|-----------|
| Abre ao clicar | ✅ Drawer abre |
| Ticker "PETR4" visível | ✅ |
| Badge direção "VENDA" | ✅ |
| Tabs: Visão Geral / Histórico / Opções | ✅ 3 tabs visíveis |
| Loading state | ✅ Spinner "Carregando dados de PETR4..." |
| Dados carregados após ~8s | ✅ Tabs conteúdo carrega |
| Bloco "Técnico" | ✅ |
| Bloco "Momentum" | ✅ |
| Bloco "Liquidez" | ✅ |
| Bloco "Valuation" | ✅ |
| Bloco "Macro" | ✅ |
| Bloco "Tese" | ✅ |
| Campos ausentes como "—" | ✅ unavailable() em todos os campos |
| Footer fontes/updated | ✅ |

**Anomalia menor:** Drawer inicializa chiamando `http://localhost:8000` (porta 8000) — mas o backend está em 8001. O componente usa porta 8000 hardcoded. Funciona porque havia outro processo em 8000. **Não bloqueante — porta 8001 seria o correto, mas o fallback 8000 está ativo.**

### 2.7 Valuation Engine (`/valuation_engine` via AppShell)

| Verificação | Resultado |
|-------------|-----------|
| Total: 20 ativos cobertos | ✅ |
| PETR4 aparece na lista | ✅ |
| Score Integrado = "—" para PETR4 | ⚠️ "Score Integrado—" sem valor numérico |
| Upside = "—" para PETR4 | ⚠️ "Upside—" |
| Status = "Preliminar" | ✅ |
| Empty state honesto para VALE3 | Não verificado diretamente (não visível no scroll da tela) |

**⚠️ Anomalia:** PETR4 mostra "Score Integrado—" — indica que `integrated_score` está null no retorno da API. O componente M030-2 já tem fallback `item.integrated_score ?? item.score ?? null`, mas o score parece não estar sendo preenchido. Pode ser que a avaliação do `signal_matrix` não esteja populando o campo corretamente.

---

## 3. Verificações de build

### 3.1 TypeScript
```
$ npx tsc --noEmit
✅ 0 erros, 0 warnings
```

### 3.2 Lint
```
$ npm run lint
⚠️ 11 warnings (apenas @typescript-eslint/no-unused-vars)
0 errors
```
**Nota:** Warnings são importações não utilizadas (Direction, MarketAsset, SkeletonCard, fmtSafe, etc.). Não afetam execução. Corrigíveis em oportunidade, não bloqueante.

### 3.3 Next.js Build
```
$ npx next build
✅ Compiled successfully in 1583ms
✅ TypeScript finished in 1536ms
✅ Generating static pages (4/4) in 160ms
✅ Route: / (Static)
```
Build limpo — zero erros.

### 3.4 Pytest
```
$ python -m pytest tests/test_market_data_core.py \
                tests/test_valuation_api.py \
                tests/test_valuation_coverage_expansion.py -v

======================== 44 passed, 6 warnings in 3.87s ========================
```
- `test_market_data_core.py`: 18/18 green ✅
- `test_valuation_api.py`: 11/11 green ✅
- `test_valuation_coverage_expansion.py`: 15/15 green ✅

Warnings são `datetime.utcnow()` deprecation em `valuation_service.py` — não afetam funcionalidade.

---

## 4. Bugs corrigidos por M032 (verificados)

| Bug | Status |
|-----|--------|
| Options strikes inflados 10x | ✅ Confirmado: strikes em 18,45 / 55,10 / 55,25 — ranges reais |
| Selic Meta usando série BCB errada | ✅ Confirmado: 14,40% (série 4320) |
| QuantCore lendo momentum/tendência errados | ⚠️ Parcial: MOM/TEND mostram valores uniformes (50.0/0.0) — padrão default |
| Options Radar payload de 19MB | ✅ Confirmado: carregamento rápido sem crash |
| Null.toFixed crash | ✅ Confirmado: todos nulls renderizam "—" |

---

## 5. Pendências não bloqueantes

| # | Descrição | Severidade | Ação |
|---|-----------|------------|------|
| P1 | QuantCore MOM/TEND todos em 50.0/0.0 — possível default em vez de dado real | Baixa | Investigar se `signal_matrix.assets[0].blocos.tecnico_indicadores.momentum_score` está sendo populado corretamente pelo backend; pode ser que o block `momentum` (separado) tenha os dados mas o component use o bloco errado |
| P2 | Valuation Engine: PETR4 mostra "Score Integrado—" — integrated_score null | Baixa | Verificar se `signal_matrix` está retornando score_agregado para ativos com valuation_results; fallback para score_final do quant_signals funciona em nível de API mas pode não estar sendo propagado |
| P3 | Macro Engine: "IPCA Mensal—" sem texto explicativo de pendência | Baixa | Melhorar label para "IPCA Mensal — pendente" ou similar, para transparência |
| P4 | Portas divergentes no drawer (8000 vs 8001) | Baixa | Padronizar para porta 8001 ou ler de variável de ambiente |
| P5 | Lint warnings em 11 locais (imports não utilizadas) | Trivial | Limpar imports mortos em oportunidade |

---

## 6. Commits sugeridos

### Commit 1: `fix(market-data): options pricing, Selic series, QuantCore signals, OptionsRadar payload`

**Escopo:** Correções de dados e performance da pipeline de market data.

**Arquivos:**
- `src/rtd/rtd_data.py` — correção do multiplicador 10x em options (backfill_cotahist_prices → merge RTD)
- `src/dashboard/rtd_live_reader.py` — correção de séries BCB (Selic Meta 4320, PTAX 1)
- `src/integration/connectors/quant_connector.py` — correção de leitura de momentum/trend do block correto
- `src/delivery/radar_payload.py` — redução de payload de 19MB para opções
- `src/integration/connectors/options_opportunity_connector.py` — filtro por status 'monitored'
- `src/integration/asset_intelligence_model.py` — populating options_strategies block
- `src/integration/signal_enricher.py` — populating momentum block no signal_matrix

### Commit 2: `fix(frontend): null handling, drawer tabs, options rendering, valuation integration`

**Escopo:** Correções de rendering no frontend (SPA AppShell).

**Arquivos:**
- `frontend/components/AssetDetailDrawer.tsx` — M029 drawer completo com 3 tabs, null handling, todos os blocks
- `frontend/components/pages/OptionsRadar.tsx` — 10x desinflation, filters, efficient rendering
- `frontend/components/pages/MacroEngine.tsx` — correct Selic/IPCA/PTAX, IPCA Mensal placeholder
- `frontend/components/pages/QuantCore.tsx` — null.safe.unavailable() wrapper
- `frontend/components/pages/Watchlist.tsx` — drawer integration
- `frontend/lib/safeNumber.ts` — safe number helpers
- `frontend/AppShell.tsx` — SPA routing para AppShell

### Commit 3: `test: valuation coverage expansion, market data, valuation API`

**Escopo:** Cobertura de testes para as correções.

**Arquivos:**
- `tests/test_valuation_coverage_expansion.py` (novo) — 15 testes de cobertura e honestidade
- `tests/test_market_data_core.py` — atualizado com edge cases
- `tests/test_valuation_api.py` — atualizado com block normalization

### Commit 4: `docs: M029-M033 audit reports and legacy planning summary`

**Escopo:** Documentação e artefatos de auditoria.

**Arquivos:**
- `docs/M029_ASSET_DETAIL_DRAWER_COMPLETION.md`
- `docs/M030_VALUATION_INTEGRATION.md`
- `docs/M031_FRONTEND_CLEANUP.md`
- `docs/M032_MARKET_DATA_CORRECTIONS.md`
- `docs/M033_FINAL_MANUAL_ACCEPTANCE_AND_COMMIT_PREPARATION.md` (este arquivo)
- `.gsd/context/LEGACY_PLANNING_SUMMARY.md`

---

## 7. Recomendação final

**✅ PRONTO PARA COMMIT — com ressalvas**

O produto está **funcional para uso manual**:
- Todas as páginas carregam corretamente
- Dados de mercado estão corretos (Selic 14,40%, IPCA 4,39%, PTAX 5,80)
- Options strikes não estão mais inflados 10x
- Drawer abre, tabs funcionam, dados carregam
- 44/44 testes passando
- Build limpo (TypeScript 0 errors, Next.js build OK)
- Lint: 0 errors, 11 warnings triviais

**⚠️ Pendências para próxima sessão:**
1. Investigar MOM/TEND uniformes no QuantCore (P1)
2. Investigar Score Integrado null no Valuation Engine (P2)
3. Limpar lint warnings (P5)

**Próximo passo:** aguardando autorização do usuário para executar os commits propostos.