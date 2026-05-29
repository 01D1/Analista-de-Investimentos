# M032 — Product Data Visibility & Streamlit Feature Parity Audit
**Data:** 2026-05-29  
**Status:** CONCLUÍDO

---

## 1. Quais dados existem de verdade?

| Fonte | Dados | Qualidade |
|---|---|---|
| RTD PROFIT.xlsx (aba Ações) | 97 ações com OHLCV, indicadores técnicos, bid/ask | ✅ Rico |
| RTD PROFIT.xlsx (aba Opções) | 54 opções ao vivo com Greeks e bid/ask | ✅ Rico |
| options_historical_opportunities.csv | 13.939 opções com score, status, estrutura | ✅ Rico |
| options_next_session_watchlist.csv | 4.440 candidatas próximo pregão | ✅ Rico |
| options_rtd_symbols.csv | 81 opções para monitorar no RTD | ✅ OK |
| scanner_quant.db / realtime_signals | 9 ativos com scores RTD ao vivo | ✅ Existe |
| scanner_quant.db / asset_intelligence_snapshots | 50+ ativos com scores integrados | ✅ Rico |
| scanner_quant.db / technical_feature_snapshots | Indicadores técnicos: momentum_score, trend_score, breakout | ✅ Rico |
| scanner_quant.db / macro_series | Selic(4389), IPCA(13522), PTAX(21620) | ✅ Rico |
| scanner_quant.db / cotahist_daily | Histórico diário B3 (ingestado) | ✅ Ingestado |
| scanner_quant.db / valuation_results | Valuations com fair_value, upside, método | ✅ Rico |

---

## 2. Quais endpoints estão ricos?

| Endpoint | Status | Items |
|---|---|---|
| /api/trading/live | ✅ Rico | 9 ações |
| /api/watchlist | ✅ Rico | 50 tickers |
| /api/quant/signals | ✅ Rico | 50 ativos |
| /api/options/radar | ✅ Rico (após fix) | 18.457 total, 2.640 candidatas |
| /api/futures/live | ✅ Rico | 7 instrumentos |
| /api/valuation/summary | ✅ Rico | 20 valuations |
| /api/calendar/economic | ✅ Rico | 19 grupos/eventos |
| /api/macro/b3 | ✅ Rico (após fix) | Selic 14.4%, IPCA 4.39%, PTAX 5.80 |
| /api/market/actions | ✅ Rico | 97 ações |
| /api/intelligence/unified?ticker=X | ✅ Rico | 9 blocos de intel |

---

## 3. Quais páginas não renderizavam dados?

Todas as páginas compilavam e tinham endpoints funcionais. Os problemas eram bugs de dados:

| Página | Problema | Estado após M032 |
|---|---|---|
| Options Radar | Strikes 10x inflados (24.5→245.0), scores 10x (95→950), payload 19MB travava browser | ✅ Corrigido |
| Quant Core | MOM/TEND pills sempre "—" por field mismatch (momentum_score vs. momentum) | ✅ Corrigido |
| Macro Engine | Selic meta null por código BCB errado (432 vs 4389) | ✅ Corrigido |
| Radar AI | Funcionava mas mostrava Selic "—" no painel macro | ✅ Corrigido |

---

## 4. Quais funcionalidades do Streamlit foram recuperadas?

- ✅ Ações ao vivo com OHLCV, indicadores, score
- ✅ Ranking quant com 50 ativos, momentum, tendência, volatilidade
- ✅ Opções para próximo pregão com strike/preço/score corretos
- ✅ Radar histórico de opções por ativo objeto
- ✅ Selic meta, IPCA 12m, PTAX com valores corretos
- ✅ Regime macro e impacto setorial
- ✅ Calendário econômico com eventos hoje/próximos 7 dias
- ✅ Valuation summary com fair_value, upside, status
- ✅ AssetDetailDrawer com 3 abas: Visão Geral / Histórico / Opções

---

## 5. Onde as opções do próximo pregão aparecem agora?

**Página:** Options Radar (menu "MARKETS → OPTIONS RADAR")  
**Seção:** "Candidatas próximo pregão"  
**Dados:**
- Total real: **2.640 candidatas** (contagem mostrada nos KPIs)
- Top 200 exibidas na tabela (sorted by score desc)
- Cada linha mostra: ticker, tipo, strike, DTE, prêmio, bid/ask, spread, score, status
- Filtros disponíveis: ativo objeto, CALL/PUT, status, score mínimo, só RTD
- Exemplo: ENEV3 ENEVR245 PUT strike=24.5 DTE=23 prêmio=0.62 score=95.0

**Também aparece em:** AssetDetailDrawer aba Opções (via `/api/options/chain/{ticker}`)

---

## 6. O que ainda não aparece e por quê?

| Item | Motivo | Solução |
|---|---|---|
| IPCA mensal | Série BCB 433 não ingestada no banco | Ingestar via BCB API |
| IGPM | Série BCB 189 não ingestada | Ingestar via BCB API |
| Bid/Ask opções (maioria) | Apenas 54 opções no RTD ao vivo têm bid/ask | Ampliar cobertura RTD ou usar outra fonte |
| Greeks (Delta, Gamma) | Apenas opções RTD ao vivo | Idem |
| Série histórica OHLCV por ação | COTAHIST ingestado mas endpoint retorna snapshot, não série | Implementar endpoint série temporal |
| Sector/Name na watchlist | Dados não enriquecidos com cadastro B3 | Ingestar cadastro de ativos |
| Página Futuros dedicada | Não existe página de futuros no Next.js (só AgentRuntime mostra) | Criar página ou integrar ao Trading Desk |
| Fura-Teto/Fura-Chão | Não implementado nos services | Calcular a partir de cotahist_daily |
| Próxima ação quant (proxima_acao) | null para maioria dos ativos — derivação não populada | Implementar lógica de derivação |

---

## 7. Quais correções foram feitas (M032)?

### Correção 1: `_parse_br` bug nas opções
**Arquivo:** `src/services/options_market_service.py`  
**Problema:** `_parse_br("24.5")` → 245.0 porque removia `.` antes de converter  
**Impacto:** Todos os strikes, preços e scores de opções estavam 10x inflados  
**Fix:** Tenta `float(s)` (US format) antes de fallback para formato BR

### Correção 2: Selic meta com código BCB errado
**Arquivo:** `src/services/macro_service.py`  
**Problema:** `BCB_SERIES["selic_meta"] = "432"` mas banco tem código `"4389"`  
**Impacto:** Selic meta null em toda a aplicação  
**Fix:** `"4389"` — agora mostra 14.4%

### Correção 3: Field mismatch QuantSignal TypeScript
**Arquivo:** `frontend/lib/api.ts` + `frontend/components/pages/QuantCore.tsx`  
**Problema:** Interface TypeScript usava `momentum`/`tendencia` (null), API retorna `momentum_score`/`trend_score`  
**Impacto:** Pills MOM/TEND sempre mostravam "—"  
**Fix:** Interface atualizada; QuantCore usa `sig.momentum_score ?? sig.momentum`

### Correção 4: Options radar payload 19MB
**Arquivo:** `src/services/options_market_service.py` + `backend/main.py`  
**Problema:** Retornava todas as 18.457 opções com listas completas → 19MB de JSON  
**Impacto:** Browser travava ao carregar Options Radar  
**Fix:** Limite 200 candidates + 100 monitor + 10 por underlying; totais preservados nos KPIs

---

## 8. Como testar manualmente

### Iniciar backend (raiz do projeto):
```bash
cd "/path/to/scanner_quant_profit_b3"
python3 -m uvicorn backend.main:app --port 8000 --reload
```

### Iniciar frontend:
```bash
cd frontend
npm run dev
# → http://localhost:3000
```

### Validação Options Radar:
1. Abrir http://localhost:3000
2. Menu: MARKETS → OPTIONS RADAR
3. Verificar KPI "2.640" candidatas e "6.238" monitorar
4. Verificar que strike de ENEV3 aparece como ~24.5 (não 245)
5. Filtrar por PETR4 → ver opções PETR
6. Clicar em opção → painel de detalhe abre

### Validação Macro Engine:
1. Menu: MARKETS → MACRO ENGINE
2. Verificar Selic = 14.4%, IPCA = 4.39%, PTAX = 5.80
3. Verificar regime = NEUTRO com 5 impactos setoriais

### Validação Quant Core:
1. Menu: MARKETS → QUANT CORE
2. Verificar 50 ativos no ranking
3. Verificar que pills MOM e TEND mostram números (não "—")

### Validação Watchlist:
1. Menu: INTELLIGENCE → WATCHLIST
2. Verificar 50 ativos com cards, score ring, preço, variação

### Validação AssetDetailDrawer:
1. Clicar em qualquer ticker no Radar AI ou Watchlist
2. Aba Histórico → mostra OHLCV snapshot com indicadores
3. Aba Opções → mostra calls/puts disponíveis
4. Aba Visão Geral → mostra score, macro, blocos de signal matrix

---

## 9. Próximas pendências reais

**P1 — Alta prioridade:**
- [ ] Ingestar série BCB 433 (IPCA mensal) no banco
- [ ] Enriquecer watchlist com sector/name da B3
- [ ] Implementar endpoint série temporal OHLCV (cotahist já está no banco)

**P2 — Média prioridade:**
- [ ] Criar página Futuros dedicada ou integrar ao Trading Desk
- [ ] Popular `proxima_acao` nos sinais quant
- [ ] Ampliar cobertura RTD para mais opções com bid/ask
- [ ] Ingestar IGPM (série 189) e DXY

**P3 — Baixa prioridade / V2:**
- [ ] Implementar Fura-Teto/Fura-Chão nos indicadores quant
- [ ] Série temporal de opções (histórico contínuo, não apenas snapshot)
- [ ] Paginação no frontend para Options Radar (carregar mais sob demanda)

---

## Critério de Sucesso M032

✅ Opções para próximo pregão aparecem no site com strikes/preços corretos  
✅ Options Radar com 2.640 candidatas, filtros funcionais, detalhes ao clicar  
✅ Histórico no drawer (OHLCV snapshot com indicadores)  
✅ Valuation no drawer (fair_value, upside, status)  
✅ Watchlist real com 50 ativos, preços, scores  
✅ Ranking quant com 50 ativos e indicadores MOM/TEND  
✅ Macro com Selic/IPCA/PTAX com dados visíveis  
✅ Calendário com eventos reais por data  
✅ Zero erros TypeScript no build  
✅ Backend responde todos os endpoints sem erro 500
