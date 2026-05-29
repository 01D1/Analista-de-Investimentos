# M032 — Mapa de Paridade Streamlit → Next.js
**Data:** 2026-05-29

## Legenda
- ✅ Existe no Next.js com dado real
- ⚠️ Existe parcialmente / dado incompleto
- ❌ Não migrado ainda
- 🔧 Bug corrigido em M032

---

## 1. Trading Desk (`pages/trading_desk.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| Ações ao vivo (ticker, último, var, vol, neg) | ✅ market_history_service | ✅ /api/market/actions | RadarAI + Watchlist | ✅ 97 ações via /market/actions |
| Score final por ação | ✅ quant_signals_service | ✅ /api/quant/signals | QuantCore | ✅ 50 ativos |
| Sinais RTD (BUY/SELL/HOLD) | ✅ trading_desk_service | ✅ /api/trading/live | RadarAI | ✅ 9 sinais ao vivo |
| Opções ao vivo (bid/ask/spread) | ✅ options_market_service | ✅ /api/options/chain | OptionsRadar (Cadeia) | ⚠️ Só RTD ao vivo tem bid/ask |
| Futuros (DOL, WIN, IND) | ✅ futures_market_service | ✅ /api/futures/live | — (não há página Futuros) | ❌ Não exposto em página dedicada |
| Diagnóstico RTD | ✅ agent_runtime_service | ✅ /api/agents/status | AgentRuntime | ✅ Mostra status RTD |
| Ranking de ações por score | ✅ quant_signals_service | ✅ /api/quant/signals | QuantCore | ✅ Ranking 50 ativos |
| Status arquivo RTD | ✅ agent_runtime_service | ✅ /api/agents/status | AgentRuntime | ✅ Mostra arquivos RTD |

---

## 2. Opções (`pages/opcoes_monitoramento.py`, `pages/radar_oportunidades.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| Shortlist opções | ✅ options_market_service | ✅ /api/options/radar | OptionsRadar | ✅ 200 top candidatas |
| Opções para próximo pregão | ✅ options_market_service | ✅ /api/options/radar | OptionsRadar | ✅ 2.640 candidatas (top 200 mostradas) |
| Status CANDIDATA_PROXIMO_PREGAO | ✅ | ✅ | OptionsRadar | ✅ Badge "PRÓXIMO" |
| Monitorar no RTD | ✅ options_market_service | ✅ /api/options/radar | OptionsRadar | ✅ 6.238 opções (top 100) |
| Strike correto | ✅ (após fix) | ✅ | OptionsRadar | ✅ 24.5 (era 245.0) |
| Preço correto | ✅ (após fix) | ✅ | OptionsRadar | ✅ 0.62 (era 62.0) |
| Score correto | ✅ (após fix) | ✅ | OptionsRadar | ✅ 95.0 (era 950.0) |
| DTE | ✅ | ✅ | OptionsRadar | ✅ |
| Cenário | ✅ | ✅ | OptionsRadar | ✅ |
| Estratégia sugerida | ✅ | ✅ | OptionsRadar | ✅ |
| Bid/Ask | ⚠️ Apenas RTD ao vivo | ⚠️ | OptionsRadar | ⚠️ null para maioria |
| Greeks (Delta/Gamma) | ⚠️ Apenas RTD ao vivo | ⚠️ | OptionsRadar | ⚠️ null para maioria |
| Radar histórico por underlying | ✅ | ✅ /api/options/radar?underlying=PETR4 | OptionsRadar (filtro) | ✅ PETR4: 636 candidatas |

---

## 3. Quant (`pages/radar_quant.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| RSI, MACD, ADX | ✅ quant_signals_service | ✅ /api/market/assets/{ticker}/history | AssetDetailDrawer (Histórico) | ✅ No drawer via RTD snapshot |
| Momentum score | ✅ quant_signals_service | ✅ /api/quant/signals (momentum_score) | QuantCore | ✅ Após fix M032 |
| Trend score | ✅ quant_signals_service | ✅ /api/quant/signals (trend_score) | QuantCore | ✅ Após fix M032 |
| Volume score | ✅ quant_signals_service | ✅ /api/quant/signals | QuantCore | ✅ |
| Breakout score | ✅ quant_signals_service | ✅ /api/quant/signals | QuantCore | ✅ |
| Volatilidade histórica | ✅ | ✅ /api/quant/signals | QuantCore | ✅ |
| Score técnico agregado | ✅ | ✅ /api/quant/signals (score_tecnico) | QuantCore | ✅ |
| Direction (BUY/SELL/HOLD) | ✅ | ✅ /api/quant/signals | QuantCore | ✅ |
| Bloqueios governança | ✅ | ✅ /api/quant/signals (governance_blocked) | QuantCore | ✅ |
| Próxima ação | ✅ | ✅ /api/quant/signals (proxima_acao) | QuantCore | ⚠️ null para maioria |
| Fura-Teto / Fura-Chão | ❌ | ❌ | — | ❌ Não implementado |
| HiLo | ✅ no snapshot RTD | ✅ /api/market/assets/*/history | AssetDetailDrawer | ✅ No drawer |
| VWAP | ✅ | ✅ /api/market/assets/*/history | AssetDetailDrawer | ✅ No drawer |

---

## 4. Macro (`pages/inteligencia_macro.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| Selic meta | ✅ (após fix) | ✅ /api/macro/b3 | MacroEngine | ✅ 14.4% (era null) 🔧 |
| IPCA 12m | ✅ | ✅ /api/macro/b3 | MacroEngine | ✅ 4.39% |
| IPCA mensal | ❌ série `433` não no banco | ❌ | MacroEngine | ⚠️ Mostra "—" |
| PTAX | ✅ | ✅ /api/macro/b3 | MacroEngine | ✅ 5.8022 |
| PTAX tendência | ✅ | ✅ /api/macro/b3 | MacroEngine | ✅ -2.43% |
| Regime macro | ✅ | ✅ /api/macro/b3 | MacroEngine | ✅ NEUTRO |
| Impacto setorial | ✅ | ✅ /api/macro/b3 (sector_impact) | MacroEngine | ✅ 5 setores |
| Leitura B3 | ✅ | ✅ /api/macro/b3 (regime.description) | MacroEngine | ✅ |
| IGPM | ❌ série `189` não no banco | ❌ | MacroEngine | ⚠️ Mostra "—" |
| Séries históricas (gráfico) | ✅ series.selic/ipca_12m/ptax_90d | ✅ /api/macro/b3 | MacroEngine | ✅ |

---

## 5. Calendário (`pages/calendario.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| Eventos hoje | ✅ economic_calendar_service | ✅ /api/calendar/economic | EventScheduler | ✅ |
| Próximos 7 dias | ✅ | ✅ | EventScheduler | ✅ |
| Alto impacto | ✅ | ✅ | EventScheduler | ✅ Badge vermelho |
| País + bandeira | ✅ | ✅ | RadarAI (mini) + EventScheduler | ✅ |
| Anterior/consenso/realizado | ✅ | ✅ | EventScheduler | ⚠️ Pode ser "—" se não disponível |
| Impacto na B3 | ⚠️ estimado pelo service | ⚠️ campo b3_impact | EventScheduler | ⚠️ Não renderizado explicitamente |

---

## 6. Valuation (`pages/valuation_engine.py`, `pages/valuation_coverage.py`)

| Funcionalidade Streamlit | Existe em Service? | Existe em Endpoint? | Next.js Page | Aparece na Tela? |
|---|---|---|---|---|
| Preço justo (fair_value) | ✅ valuation_service | ✅ /api/valuation/summary | ValuationEngine | ✅ |
| Status (preliminary/approved/blocked) | ✅ | ✅ /api/valuation/{ticker} | ValuationEngine + Drawer | ✅ |
| Upside % | ✅ | ✅ | ValuationEngine | ✅ |
| Sanity checks | ✅ | ✅ | ValuationEngine | ✅ |
| Cobertura do universo | ✅ | ✅ /api/valuation/coverage/full | ValuationEngine | ✅ |
| Preço atual (current_price) | ⚠️ enriquecimento cotahist | ⚠️ | ValuationEngine | ⚠️ null para alguns |

---

## Resumo Geral de Paridade

| Categoria | Migrado ✅ | Parcial ⚠️ | Não Migrado ❌ |
|---|---|---|---|
| Trading Desk | 7 | 1 | 1 (página Futuros) |
| Opções | 12 | 3 | 0 |
| Quant | 9 | 1 | 2 (Fura-Teto/Chão) |
| Macro | 6 | 3 | 0 |
| Calendário | 5 | 1 | 0 |
| Valuation | 5 | 1 | 0 |
| **TOTAL** | **44** | **10** | **3** |
