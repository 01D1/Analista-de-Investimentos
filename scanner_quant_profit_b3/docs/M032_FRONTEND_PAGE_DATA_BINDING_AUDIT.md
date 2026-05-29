# M032 — Auditoria de Data Binding das Páginas Frontend
**Data:** 2026-05-29

## Tabela de Status por Página

| Página | Endpoint | Dados chegam? | Dados renderizam? | Problema | Correção |
|---|---|---|---|---|---|
| Radar AI | /api/trading/live + /api/watchlist + /api/macro/b3 + /api/calendar/economic | ✅ Sim | ✅ Sim (9 ações, 50 watchlist, macro, calendário) | Nenhum | — |
| Watchlist | /api/watchlist | ✅ Sim (50 tickers) | ✅ Sim | sector/name null | Enriquecimento pendente |
| Quant Core | /api/quant/signals | ✅ Sim (50 itens) | ⚠️ Parcial | MOM/TEND pills mostravam "—" | ✅ Corrigido — usa momentum_score/trend_score |
| Options Radar | /api/options/radar | ✅ Sim | ✅ Sim (após fixes) | Strike 10x errado, payload 19MB | ✅ _parse_br fix + limite 200/100 |
| Valuation Engine | /api/valuation/summary | ✅ Sim (20 itens) | ✅ Sim | current_price null para alguns | Enriquecimento cotahist pendente |
| Macro Engine | /api/macro/b3 | ✅ Sim | ✅ Sim (após fix) | selic_meta null | ✅ Código BCB 432→4389 |
| Event Scheduler | /api/calendar/economic | ✅ Sim (19 eventos) | ✅ Sim | — | — |
| Signal Matrix | /api/ai/signal-matrix | ✅ Sim | ✅ Sim | blocos "em integração" para ativos sem dados | Comportamento esperado |
| Thesis Builder | /api/ai/thesis | ✅ Sim | ✅ Sim | — | — |
| Conviction Desk | /api/conviction/positions | ✅ Sim | ✅ Sim | — | — |
| Agent Runtime | /api/agents/status | ✅ Sim | ✅ Sim | — | — |
| AssetDetailDrawer | /api/intelligence/unified?ticker=X | ✅ Sim | ✅ Sim | — | — |

---

## Detalhamento por Página

### 1. Radar AI
**Endpoint:** `/api/trading/live`, `/api/watchlist`, `/api/macro/b3`, `/api/calendar/economic`, `/api/options/strategies`
**Função api.ts:** `getTradingLive()`, `getWatchlist()`, `getMacroB3()`, `getEconomicCalendar()`
**Campos recebidos:** actions (9), watchlist.tickers (50), macro.current_values, calendar.events (19)
**Campos renderizados:** score, signal, ticker, macro KPIs, calendar por data
**Campos ignorados:** nenhum crítico
**Dado real na tela:** ✅ Sim — ações com scores, macro, calendário
**Console errors:** nenhum esperado
**Empty state:** só aparece se `actions.length === 0`

---

### 2. Watchlist
**Endpoint:** `/api/watchlist`
**Função api.ts:** `getWatchlist()`
**Campos recebidos:** tickers[].{ticker, price, variacao_pct, score, direction, risk, liquidity, adv_21d, has_options, has_valuation, next_action}
**Campos renderizados:** todos os acima
**Campos nulos:** name (null), sector (null) → mostra "—" sem travar
**Dado real na tela:** ✅ Sim — 50 ativos com cards, score ring, sparkline
**Clique funciona:** ✅ Abre AssetDetailDrawer via drawerStore

---

### 3. Quant Core
**Endpoint:** `/api/quant/signals`
**Função api.ts:** `getQuantSignals()`
**Campos recebidos:** ranking[].{ticker, score_final, momentum_score, trend_score, liquidez, direction, gatilho, risco, governance_blocked, volume_21d}
**Campos renderizados:** score ring, rank badge, ticker, direction badge, gatilho, momentum/trend/liq pills
**Bug corrigido:** `sig.momentum` era sempre null → agora usa `sig.momentum_score ?? sig.momentum`
**Dado real na tela:** ✅ Sim — 50 ativos com ranking, indicadores MOM/TEND/LIQ agora com valores
**Contagem direction:** buy=0, sell=0, hold=50 (todos bloqueados por governance ou HOLD técnico)

---

### 4. Options Radar
**Endpoint:** `/api/options/radar`
**Função api.ts:** `getOptionsRadar()`
**Campos recebidos:** candidates_next_session[], monitor_rtd[], by_underlying{}, by_status{}, rtd_diagnostic{}
**Campos renderizados:** ticker, tipo, strike, dte, premium, bid/ask, spread, score, status, estruturas_sugeridas
**Bugs corrigidos (M032):**
  - `_parse_br("24.5")` → 245.0: corrigido para 24.5
  - `_parse_br("95.0")` → 950.0: corrigido para 95.0
  - Payload 19MB → 506KB
**Dado real na tela:** ✅ Sim — 200 candidatas próximo pregão mostradas
**View cadeia:** funciona — busca por ativo objeto manual

---

### 5. Valuation Engine
**Endpoint:** `/api/valuation/summary`
**Função api.ts:** `getValuationSummary()`
**Campos recebidos:** valuations[].{ticker, fair_value, status, upside_pct, method, sanity_check_passed}
**Dado real na tela:** ✅ Sim — 20 valuations disponíveis
**current_price:** null para alguns (enriquecimento cotahist pendente, não crítico)

---

### 6. Macro Engine
**Endpoint:** `/api/macro/b3`
**Função api.ts:** `getMacroB3()`
**Campos recebidos:** current_values.{selic_meta, ipca_12m, ptax, ptax_trend_pct}, regime, sector_impact[], series
**Bug corrigido:** selic_meta era null (código BCB errado) → agora mostra 14.4%
**Dado real na tela:** ✅ Sim — Selic 14.4%, IPCA 4.39%, PTAX 5.80, regime NEUTRO, 5 impactos setoriais

---

### 7. Event Scheduler (Calendário)
**Endpoint:** `/api/calendar/economic`
**Função api.ts:** `getEconomicCalendar()`
**Campos recebidos:** events[].{date, events[].{event, country, importance, previous, forecast, actual}}
**Dado real na tela:** ✅ Sim — 19 grupos de eventos com importância colorida

---

### 8. AssetDetailDrawer
**Endpoint:** `/api/intelligence/unified?ticker=X` + `/api/market/assets/{ticker}/history` + `/api/options/chain/{ticker}`
**Tabs disponíveis:** Visão Geral, Histórico, Opções
**Aba Visão Geral:** ✅ Sim — score, preço, variação, setor, governança, blocos técnico/momentum/macro/valuation
**Aba Histórico:** ⚠️ Mostra snapshot do RTD (não série temporal) com aviso claro
**Aba Opções:** ✅ Sim — calls/puts do primeiro vencimento disponíveis
**Clique em ticker abre drawer:** ✅ Via drawerStore

---

## Problemas Não Críticos Documentados

1. **sector/name null na watchlist**: Não enriquecido com dados cadastrais da B3. Mostra "—". Não trava.
2. **Série histórica OHLCV**: Apenas snapshot do RTD, não série temporal. Drawer informa claramente.
3. **Bid/Ask opções**: null para opções fora do RTD. Drawer/OptionsRadar mostra "—" corretamente.
4. **IPCA mensal, IGPM**: Séries não populadas no banco. Mostra "—".
5. **Valuation PETR4**: Status "preliminary" — valuation existe, aguarda aprovação manual.
6. **All directions HOLD**: 50 ativos no quant/signals todos como HOLD por governance_blocked ou score insuficiente.
