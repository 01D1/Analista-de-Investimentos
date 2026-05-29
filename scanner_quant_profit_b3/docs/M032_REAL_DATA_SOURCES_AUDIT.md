# M032 — Auditoria das Fontes Reais de Dados
**Data:** 2026-05-29

---

## 1. RTD PROFIT.xlsx

| Campo | Valor |
|---|---|
| Caminho | `data/realtime/RTD PROFIT.xlsx` |
| Abas | `Ações`, `Opções` |
| Aba Ações: linhas | 153 |
| Aba Opções: linhas | 54 |
| Colunas principais | Asset, Data, Hora, Último, Abertura, Máximo, Mínimo, Fechamento Anterior, Strike, Variação, Volume, Bid, Ask, RSI, ADX, MACD, Bollinger, Vencimento, Greeks |

### Exemplo — 5 ações (aba Ações):
Dados acessados via `/api/market/actions` (97 ações disponíveis):
- ABCB4, preco=24.51
- PETR4, preco=44.48
- VALE3, preco=98.0 (spot)
- WEGE3, BBAS3, etc.

### Exemplo — opções (aba Opções):
54 linhas incluindo PETR, VALE, ENEV, BBDC.
Dados bid/ask disponíveis para opções no RTD ao vivo.

---

## 2. CSVs de Opções

### `data/realtime/options_historical_opportunities.csv`
| Campo | Valor |
|---|---|
| Existe? | ✅ Sim |
| Total de linhas | 13.939 |
| Colunas | ativo_objeto, ticker_opcao, tipo, strike, vencimento, dte, categoria_vencimento, ultimo_preco, vol_media_5d, vol_media_10d, vol_media_21d, negocios_media_5d, variacao_volume, variacao_preco, moneyness, moneyness_cat, liquidez_score, spot, retorno_5d, retorno_21d, retorno_63d, vol_hist_21d, dist_max, dist_min, vol_relativa, tendencia, cenario, estruturas_sugeridas, score, status, motivo, risco_principal, data_analise, ultima_data_cotahist |
| Underlyings presentes | ENEV3, PETR4, VALE3, BBDC4, BBAS3, ITUB4, WEGE3, GGBR4, etc. |
| Última data_analise | 2026-05-27 |

**Exemplo (10 linhas resumidas):**
```
ENEV3,ENEVR245,PUT,24.5,2026-06-19,23,CURTO,0.62,liquidez=100,score=95.0,CANDIDATA_PROXIMO_PREGAO
ENEV3,ENEVF250,CALL,25.0,2026-06-19,23,CURTO,1.56,liquidez=100,score=95.0,CANDIDATA_PROXIMO_PREGAO
B3SA3,B3SAF167,CALL,16.72,2026-06-19,23,CURTO,0.75,liquidez=100,score=95.0,CANDIDATA_PROXIMO_PREGAO
PETR4,PETRQ455W5,PUT,44.96,2026-05-29,2,INTRA_SEMANA,...
...
```

---

### `data/realtime/options_next_session_watchlist.csv`
| Campo | Valor |
|---|---|
| Existe? | ✅ Sim |
| Total de linhas | 4.440 |
| Colunas | ativo_objeto, ticker_opcao, tipo, strike, vencimento, dte, categoria_vencimento, ultimo_preco, liquidez_score, cenario, estruturas_sugeridas, score, status, motivo |
| Status presente | CANDIDATA_PROXIMO_PREGAO |
| Candidatas próximo pregão | 4.439 |

---

### `data/realtime/options_rtd_symbols.csv`
| Campo | Valor |
|---|---|
| Existe? | ✅ Sim |
| Total de linhas | 81 |
| Colunas | ticker, ativo_objeto, tipo, strike, vencimento, prioridade |
| Status | NA_RTD (disponíveis para monitoramento ao vivo) |

---

### `data/realtime/options_rtd_diagnostic.csv`
| Campo | Valor |
|---|---|
| Existe? | ✅ Sim |
| Total de linhas | 27 |
| Colunas | ativo, spot, limite, total_cand, com_liquidez, oportunidades, na_shortlist, status |
| Ativos com dados | PETR (spot=54.96), VALE (spot=98.0), ENEV, BBDC, etc. |

---

### `data/realtime/options_rtd_watchlist.csv`
| Campo | Valor |
|---|---|
| Existe? | ✅ Sim |
| Total de linhas | 81 |
| Colunas | ticker, ativo_objeto, tipo, strike, vencimento, ultimo_preco, spot, moneyness, adv_volume, negocios_media, prioridade, categoria |
| Observação | Arquivo tem formatação com `;` duplo no header — parsear com cuidado |

---

## 3. Banco de Dados

### `data/database/scanner_quant.db`

**Tabelas confirmadas:**

| Tabela | Linhas | Última Data | Observações |
|---|---|---|---|
| `profit_snapshots` | ? | ? | Snapshots do RTD |
| `realtime_signals` | 9+ | 2026-05-21 | 9 ativos com scores |
| `cotahist_daily` | ? | 2026-05-22 | Histórico diário B3 |
| `asset_intelligence_snapshots` | 50+ | recente | Scores integrados |
| `technical_feature_snapshots` | 50+ | recente | Indicadores técnicos |
| `macro_series` | 146 | 2026-05-29 | Séries BCB (selic, ipca, ptax) |
| `options_greeks_snapshot` | ? | ? | Greeks de opções |

**Séries macro_series disponíveis:**
| Código | Nome | Linhas |
|---|---|---|
| `4389` | selic (% a.a.) | 61 |
| `13522` | ipca_12m | 24 |
| `21620` | ptax | 61 |

**Nota crítica:** Código da Selic no banco é `4389`, não `432`. Bug corrigido em M032.

---

## Lacunas de Dados Documentadas

1. **Selic meta**: estava null por código BCB errado (`432` → `4389`) — **CORRIGIDO**
2. **IPCA mensal**: código `433` não existe no banco — mostra `—`
3. **IGPM**: código `189` não existe no banco — mostra `—`
4. **Bid/Ask opções**: disponível apenas para os ~54 instrumentos no RTD ao vivo
5. **Greeks (Delta, Gamma, etc.)**: disponível apenas para opções do RTD ao vivo
6. **Série histórica OHLCV de ações**: apenas snapshot, não série temporal (COTAHIST ingestado mas série temporal por ativo não exposta)
7. **Sector/Name watchlist**: `sector: null`, `name: null` para muitos ativos — dados não enriquecidos
