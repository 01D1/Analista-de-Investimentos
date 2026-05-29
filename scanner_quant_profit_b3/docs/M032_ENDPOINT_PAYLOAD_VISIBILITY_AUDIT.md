# M032 — Auditoria de Payload dos Endpoints
**Data:** 2026-05-29

## Classificações
- ✅ **OK E RICO**: dados reais suficientes para renderizar cards/tabelas/drawer
- ⚠️ **OK MAS RASO**: endpoint responde mas dados incompletos ou vazios
- 📦 **OK MAS GIGANTE**: dados ricos mas payload muito grande (antes da correção)
- 🔴 **VAZIO**: endpoint ok mas retorna lista vazia
- 💥 **QUEBRADO**: HTTP error

---

## Endpoints Auditados

### `/api/trading/live`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| API status | ok |
| Items | 9 ações |
| Tamanho | 2KB |
| Campos ricos | ticker, score_final, score_momentum, score_tendencia, score_liquidez, signal_type, captured_at |
| Suficiente para render? | Sim — 9 ações com scores completos |
| Exemplo | `WEGE3: score=88.17, signal_type="FORÇA COM LIQUIDEZ"` |

---

### `/api/watchlist`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Items | 50 tickers |
| Tamanho | 26KB |
| Campos ricos | ticker, price, variacao_pct, score, direction, risk, liquidity, adv_21d, has_options, has_valuation |
| Campos nulos comuns | name, sector (não enriquecidos) |
| Suficiente para render? | Sim — 50 ativos com preços e scores |

---

### `/api/quant/signals`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Items | 50 no ranking |
| Tamanho | 30KB |
| Campos ricos | ticker, score_final, momentum_score, trend_score, direction, gatilho, risco, governance_blocked, volume_21d |
| Campos nulos | momentum (null — alias legado), tendencia (null — alias legado), liquidez (null para maioria) |
| Nota | `momentum_score` e `trend_score` têm valores reais — interface TypeScript corrigida em M032 |

---

### `/api/options/radar` (após fix M032)
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO (antes era 📦 GIGANTE) |
| HTTP | 200 |
| Tamanho | 506KB (era 19MB antes do fix) |
| total | 18.457 opções |
| total_candidates | 2.640 candidatas próximo pregão |
| total_monitor_rtd | 6.238 monitorar RTD |
| candidates_next_session | top 200 (sorted by score desc) |
| monitor_rtd | top 100 |
| Strikes corretos? | ✅ Sim (24.5, não 245.0) |
| Preços corretos? | ✅ Sim (0.62, não 62.0) |
| Scores corretos? | ✅ Sim (95.0, não 950.0) |
| Bug corrigido | `_parse_br` aceitava US decimal format ("24.5") mas convertia para BR ("245") |

---

### `/api/options/radar?underlying=PETR4`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| total | 3.379 opções |
| candidates | 636 |
| Tamanho | ~700KB após fix |

---

### `/api/options/chain/PETR`
| Campo | Valor |
|---|---|
| Status | ⚠️ OK MAS RASO (sem bid/ask) |
| HTTP | 200 |
| Resultado | Retorna opções do CSV histórico sem bid/ask |
| calls | muitas |
| puts | muitas |
| has_live_data | false (opções RTD não filtradas por prefixo PETR sem trailing digit) |
| Observação | Funciona corretamente para CSVs; bid/ask requer RTD com ticker exato |

---

### `/api/options/history/ENEVR245`
| Campo | Valor |
|---|---|
| Status | ⚠️ OK MAS RASO |
| HTTP | 200 |
| Records | 1 registro (apenas snapshot de data_analise) |
| Observação | Não é série temporal — apenas snapshot da última análise |

---

### `/api/market/assets/PETR4/history`
| Campo | Valor |
|---|---|
| Status | ⚠️ OK MAS RASO |
| HTTP | 200 |
| api_status | ok |
| ohlcv | Snapshot único (RTD last data) |
| Indicadores | RSI, ADX, MACD, Bollinger, HiLo disponíveis |
| Série histórica | NÃO — apenas snapshot |
| Observação | Drawer mostra corretamente: "RTD snapshot" com aviso de limitação |

---

### `/api/futures/live`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Items | 5 futuros + 2 índices |
| Dados | DOL, WIN, IND, IBOV, SMLL — com preços e variações |

---

### `/api/valuation/summary`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Items | 20 valuations |
| Tamanho | 28KB |
| Campos | fair_value, current_price, upside_pct, method, status, sanity_check_passed |
| Nota | current_price null para alguns — enriquecimento cotahist pendente |

---

### `/api/valuation/PETR4`
| Campo | Valor |
|---|---|
| Status | ⚠️ OK MAS RASO |
| HTTP | 200 |
| api_status | preliminary |
| fair_value | disponível |
| Observação | Status "preliminary" significa que valuation existe mas não foi aprovado manualmente |

---

### `/api/intelligence/unified?ticker=PETR4`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Tamanho | 15KB |
| Blocos | watchlist ✅, quant_signals ✅, signal_matrix ✅, thesis ✅, macro ✅, valuation ✅, conviction ✅, agent_runtime ✅ |
| Suficiente para drawer? | Sim |

---

### `/api/calendar/economic`
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| Events | 19 grupos de datas |
| Dados | Hoje (2026-05-29): GDP EUA, Inflação BR, etc. |
| Campos | event, country, importance, previous, forecast, actual |

---

### `/api/macro/b3` (após fix M032)
| Campo | Valor |
|---|---|
| Status | ✅ OK E RICO |
| HTTP | 200 |
| selic_meta | 14.4% (era null antes do fix) |
| ipca_12m | 4.39% |
| ptax | 5.8022 |
| regime | NEUTRO |
| sector_impact | 5 setores |
| Bug corrigido | Código BCB selic `432` → `4389` |

---

## Resumo de Classificações

| Classificação | Endpoints |
|---|---|
| ✅ OK E RICO | trading/live, watchlist, quant/signals, futures/live, valuation/summary, calendar/economic, macro/b3, market/actions, intelligence/unified |
| ⚠️ OK MAS RASO | options/chain/*, options/history/*, market/assets/*/history, valuation/{ticker}, valuation/coverage/full, agents/status |
| 🔴 NENHUM | — |
| 💥 QUEBRADO | NENHUM |

---

## Bugs Corrigidos em M032

| Bug | Impacto | Fix |
|---|---|---|
| `_parse_br("24.5")` = 245.0 | Todos os preços/strikes de opções 10x inflados | Tenta `float(s)` antes de BR format |
| BCB code selic `432` em vez de `4389` | `selic_meta: null` na Macro | Corrigido em `BCB_SERIES` |
| `QuantSignal.momentum/tendencia` null | MOM/TEND pills no QuantCore mostravam "—" | Interface atualizada para `momentum_score`/`trend_score` |
| Options radar 19MB payload | Browser travava ao carregar OptionsRadar | Limite 200 candidates + 100 monitor + truncamento by_underlying |
