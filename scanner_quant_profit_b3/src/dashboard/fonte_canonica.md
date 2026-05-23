# Fonte Canônica de Dados — S04.5

**Data:** 2026-05-22
**Status:** DEFINIDO
**Milestone:** M002 S04.5

---

## Matriz de Fontes Canônicas

| Domínio | Fonte Canônica | Tabela/Arquivo | Status |
|---|---|---|---|
| **Valuation (DCF)** | scanner_quant.db | `asset_intelligence_snapshots.fair_value` | ✅ Canônica |
| **Valuation (reference)** | 12_PYTHON/pipeline banco completo | `data/valuation.db` | ℹ️ Referência, não integrada |
| **Preço de mercado** | cotahist_daily | `cotahist_daily.close` (latest) | ✅ Canônica |
| **OHLCV histórico** | cotahist_daily | `cotahist_daily` | ✅ Canônica |
| **Notícias** | 12_PYTHON/news_hunter | `banco.db.noticias` via news_connector.py | ✅ Conectado (0 dias stale) |
| **Macro BCB (Selic/PTAX/IPCA)** | scanner_quant.db | `macro_series` (BCB SGS API) | ✅ Canônica |
| **Risco** | scanner_quant.db | `risk_snapshots` | ✅ Canônica |
| **Opções** | scanner_quant.db | `option_structure_candidates` | ✅ Canônica |
| **Scores técnicos** | scanner_quant.db | `asset_intelligence_snapshots.technical_*` | ✅ Canônica |
| **Scores quantitativo** | scanner_quant.db | `asset_intelligence_snapshots.integrated_score` | ✅ Canônica |
| **CSS / Design tokens** | src/ui/design_tokens.css | 118 CSS vars | ✅ Canônica |

---

## Detalhamento por Domínio

### Valuation (DCF)

**Canônica:** `scanner_quant.db > asset_intelligence_snapshots`
- Campo: `fair_value`
- Upside: `upside_pct`
- Data: `created_at`
- Source label: `"scanner_quant.db"`

**Reference (não integrada):** `12_PYTHON/pipeline banco completo/data/valuation.db`
- 149 tickers cobertos
- Inclui 7 bancos com COSIF-adjusted DCF (`tipo_empresa=bank`)
- Corredores: ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11
- **Use case:** auditoria de valuation, não consumo pelo app

**Divergências conhecidas:**

| Ticker | App (scanner_quant) | Pipeline | Diferença | Motivo |
|---|---|---|---|---|
| PETR4 | R$81.12 (71.2%) | R$98.56 (90.3%) | +21.5% | DCF com premissas diferentes (WACC, crescimento terminal, preços de commodity) |
| ITUB4 | R$73.69 (0%) | R$69.79 (74.1%) | -5.3% | App usa DCF simples; pipeline usa COSIF-adjusted para bancos |
| BBAS3 | R$64.84 (0%) | R$63.68 (211.9%) | -1.8% | Mesma dinâmica ITUB4 — pipeline usa COSIF |
| BBDC4 | null | null (no runs) | — | Sem valuation em nenhum dos dois |
| VALE3 | R$0.0 (null) | R$0.0 (PRELIMINAR) | — | Ambos não têm valuation válido |

**Decisão:** `scanner_quant.db` é canônica para o app Streamlit. Divergências são documentadas e expostas via `valuation_source` + `valuation_timestamp` em `get_asset_detail()`.

---

### Preço de Mercado

**Canônica:** `cotahist_daily.close` (por ticker, latest trade_date)

**Origem do problema:** `asset_intelligence_snapshots.market_price` estava `NULL` porque o engine não popula essa coluna.

**Correção:** `_get_market_price(db, ticker)` em `src/dashboard/data.py` resolve `cotahist_daily.close` para o ticker mais recente.

**Exposição:**
```python
get_asset_detail('PETR4')['market_price']  # → 46.44 (from cotahist_daily)
```

---

### OHLCV Histórico

**Canônica:** `cotahist_daily` (scanner_quant.db)

- ~9.45M registros (fonte: S01.7 audit)
- Colunas: `trade_date`, `ticker`, `open`, `high`, `low`, `close`, `volume`, `trades`, etc.
- Usado por: gráficos, indicadores técnicos, backtests, risco

**Pipeline banco completo:** não tem OHLCV alternativo. A fonte única é `cotahist_daily`.

---

### Notícias

**Canônica:** `12_PYTHON/news_hunter/banco.db.noticias` via `src/dashboard/news_connector.py`

- 1,760 notícias totais (322 coletadas em 2026-05-21)
- **Última coleta:** 2026-05-21T19:06:44 — 0 dias stale ✅
- Status operacional: **FUNCIONAL** (não é stale — execução automática diária via `morning_call_diario.bat`)
- Interface: `get_recent_news(ticker=None, limit=20)`, `get_news_summary(ticker=None, limit=10)`

**Limitações conhecidas:**
- Notícia não tem ticker enriquecido para PETR4 (0 resultados com filtro `ticker='PETR4'`)
- Isso é uma limitação do enriquecimento AI do News Hunter, não do conector

---

### Macro BCB

**Canônica:** `scanner_quant.db > macro_series`

- **Selic (4389):** 14.4% (2026-05-21) ✅
- **PTAX (21620):** 5.80 (2026-05-21) ✅
- **IPCA 12m (13522):** disponível, dados até 2026-04
- **CDS/PIB:** SEM_DADOS_BCB

---

### Risco

**Canônica:** `scanner_quant.db > risk_snapshots`
- 7/7 tickers com `RISK_OK`
- VaR 95%, Expected Shortfall, regime de volatilidade

---

## Arquivos Alterados por S04.5

| Arquivo | Ação | Motivo |
|---|---|---|
| `src/dashboard/data.py` | MODIFICADO | `_get_market_price()` resolve cotahist_daily; `market_price`, `valuation_source`, `valuation_timestamp` adicionados a `get_asset_detail()` |
| `src/dashboard/valuation_connector.py` | CRIADO | Camada de integração para pipeline banco completo sem modificar PYTHONPATH global |
| `src/dashboard/__init__.py` | — | Sem modificação (vazio) |

---

## Status por Tarefa

| # | Tarefa | Status | Resultado |
|---|---|---|---|
| T01 | Auditar pipeline banco completo | ✅ | 149 tickers, 7 bancos, valuation.db em data/ |
| T02 | Resolver PYTHONPATH | ✅ | `valuation_connector.py` criado, graceful fallback |
| T03 | Reconciliar valuation PETR4 | ✅ | Divergência 81.12 vs 98.56 explicada; fonte canônica = scanner_quant.db |
| T04 | Corrigir market_price=None | ✅ | `_get_market_price()` resolve cotahist_daily |
| T05 | Confirmar fonte OHLCV | ✅ | `cotahist_daily` é canônica, sem duplicidade |
| T06 | Operacionalizar News Hunter | ✅ | 0 dias stale, 1760 notícias, connector funcional |
| T07 | Matriz fonte canônica | ✅ | Documento criado |
| T08 | Validações finais | ✅ | 10/10 passes |

---

## Próximos Passos Recomendados

1. **S05 (Navigation):** ✅ Pode avançar — dados reconciliados
2. **S06 (Next.js CSS):** ✅ Pode avançar — design tokens definidos
3. **Enriquecer ticker em notícias:** Investigar por que News Hunter não está extraindo tickers das notícias
4. **IPCA maio/2026:** macro_series tem gap — coletar novo dado
5. **VALE3/BBDC4 fair_value=None:** Investigar por que asset_intelligence_engine não populou valuation para esses tickers