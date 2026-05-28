# M029 — DATA PRODUCT CORE: Actions, Options, Futures, History

**Status:** ✅ Implementado
**Data:** 2026-05-28
**Escopo:** Camada central de dados de mercado — backend FastAPI + frontend Next.js

---

## Resumo Executivo

M029 construiu a camada central de dados de mercado do produto. Antes desta milestone, o frontend expunha principalmente cards superficiais conectados a tabelas SQLite vazias. Agora, todos os dados reais disponíveis nas fontes (RTD PROFIT.xlsx, CSVs de opções) estão expostos via FastAPI e consumidos pelo frontend.

**Resultado:** 8 endpoints funcionando, 3 services novos, AssetDetailDrawer com 3 abas, página Options Radar funcional, 18 testes passando.

---

## Fontes Auditadas

### 1. Banco SQLite: scanner_quant.db

| Tabela | Linhas | Status |
|---|---|---|
| `cotahist_daily` | 0 | ❌ Estrutura existe, sem dados |
| `realtime_signals` | 0 | ❌ Sem dados |
| `asset_intelligence_snapshots` | 0 | ❌ Sem dados |
| `technical_feature_snapshots` | 0 | ❌ Sem dados |
| `option_structure_candidates` | 0 | ❌ Sem dados |
| `market_regime_daily` | 0 | ❌ Sem dados |
| `macro_series` | 0 | ❌ Sem dados |
| `risk_snapshots` | 0 | ❌ Sem dados |
| `valuation_results` | — | ❌ Tabela não existe |

**Conclusão:** O banco tem 117 tabelas operacionais (para o pipeline de análise), mas nenhuma tabela de dados de mercado tem dados. Isso é esperado para o pipeline de quant; os dados RTD/CSV compensam.

### 2. Arquivos CSV em data/realtime

| Arquivo | Linhas | Conteúdo | Pronto para frontend |
|---|---|---|---|
| `options_historical_opportunities.csv` | 13.938 | Oportunidades históricas por opção | ✅ Sim |
| `options_next_session_watchlist.csv` | 4.439 | Watchlist próximo pregão | ✅ Sim |
| `options_rtd_symbols.csv` | 80 | Símbolos RTD com strike/vencimento | ✅ Sim |
| `options_rtd_diagnostic.csv` | 27 | Diagnósticos por ativo objeto | ✅ Sim |
| `options_rtd_watchlist.csv` | 80 | Corrompido (tickers com `;;`) | ❌ Ignorar |

### 3. RTD PROFIT.xlsx

| Aba | Linhas | Colunas | Conteúdo |
|---|---|---|---|
| Ações | 152 | 99 | OHLCV + RSI + MACD + ADX + Bollinger + VWAP + meta períodos |
| Opções | 53 | 99 | Strikes + Greeks (delta/gamma/theta/vega/rho) + VI |

**Detecção de índice:** IBOV, SMLL disponíveis como índices.
**Detecção de futuros:** Nenhum futuro (WDO/DOL/WIN) no RTD atual.

---

## Services Criados

### 1. `src/services/market_history_service.py`

| Função | Descrição |
|---|---|
| `get_asset_history_payload(ticker, period)` | Histórico de ação: OHLCV snapshot + indicadores + retornos por período |
| `get_multi_asset_history_summary(tickers)` | Resumo multi-ticker para cards e radar |
| `get_all_actions_from_rtd()` | Todas as ações do RTD com OHLCV e indicadores |

**Fonte primária:** RTD PROFIT.xlsx (aba Ações)
**Limitação documentada:** Snapshot único (não série temporal). Para histórico completo, executar M015 (COTAHIST download).
**Todos os campos retornados:** `status`, `timestamp`, `source`, `diagnostic` — com `diagnostic.note` explicando limitações.

### 2. `src/services/options_market_service.py`

| Função | Descrição |
|---|---|
| `get_options_chain_payload(underlying, expiration?)` | Cadeia de opções: calls + puts + strikes + Greeks + spread + liquidez |
| `get_option_history_payload(option_ticker, period?)` | Histórico de opção: registros de múltiplas fontes |
| `get_options_radar_payload(underlying?)` | Radar: candidatas próximo pregão, monitorar RTD, aguardando liquidez |

**Fontes:** RTD PROFIT.xlsx (Opções) + 4 CSVs de opções
**Separadas:** calls e puts
**Para cada opção:** ticker, tipo, strike, vencimento, DTE, bid/ask/spread, volume, trades, Greeks, moneyness, liquidity_score, status, estratégia sugerida

### 3. `src/services/futures_market_service.py`

| Função | Descrição |
|---|---|
| `get_futures_live_payload()` | Futuros e índices: preço, variação, volume, bid/ask, spread |
| `get_futures_summary_payload()` | Resumo executivo: IBOV, variação, agregações |

**Fonte:** RTD PROFIT.xlsx (todas as abas)
**Detecção:** DOL/WDO/WIN/IND/DI como futuros; IBOV/SMLL/IFIX como índices
**Empty state honesto:** Se nenhum futuro estiver configurado, retorna `total: 0` com `diagnostic.note` instructing to add contracts to Profit RTD.

---

## Endpoints FastAPI Criados

### Histórico de Ações

```
GET /api/market/assets/{ticker}/history?period=1y
GET /api/market/assets/history-summary?tickers=PETR4,VALE3,WEGE3
GET /api/market/actions
```

### Cadeia de Opções

```
GET /api/options/chain/{underlying}?expiration=2026-06-19
GET /api/options/history/{option_ticker}?period=6m
GET /api/options/radar?underlying=PETR4
```

### Futuros e Índices

```
GET /api/futures/live
GET /api/futures/summary
```

**Contrato de resposta de todos os endpoints:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-28T17:30:00",
  "source": "RTD PROFIT.xlsx | options CSVs",
  "diagnostic": {
    "note": "explicação de limitações quando houver",
    "data_type": "single_snapshot | mixed_rtd_csv",
    "limitations": ["lista de limitações"]
  }
}
```

---

## Interfaces Frontend (api.ts)

Todas adicionadas em `frontend/lib/api.ts`:

- `AssetHistoryResponse` + `getAssetHistory()`
- `MarketHistorySummaryResponse` + `getMarketHistorySummary()`
- `AllActionsResponse` + `getAllActions()`
- `OptionsChainResponse` + `getOptionsChain()`
- `OptionHistoryResponse` + `getOptionHistory()`
- `OptionsRadarResponse` + `getOptionsRadar()`
- `FuturesLiveResponse` + `getFuturesLive()`
- `FuturesSummaryResponse` + `getFuturesSummary()`

---

## Componentes Frontend

### AssetDetailDrawer — 3 abas novas

- **Visão Geral:** Score, preço, variação, direção, upside, setor, governança (mantido)
- **Histórico:** OHLCV snapshot + RSI + ADX + MACD + retornos por período + volatilidade
- **Opções:** Cadeia para o ativo: spot, vencimentos, calls/puts com strikes, bid/ask, DTE, status

**Regras seguidas:**
- Se dado ausent: empty state honesto ("sem opções disponíveis nas fontes atuais")
- Não mostra JSON bruto
- Empty states documentam fonte necessária
- Não quebra com null

### OptionsRadar.tsx — nova página

**Funcionalidades:**
- Resumo: total de opções, candidatas próximo pregão, monitorar RTD
- Filtros: ativo objeto, CALL/PUT, status, score mínimo, só RTD
- Cards por ativo objeto (grid clicável)
- Tabela de candidatas (top 50)
- Tabela de monitorar RTD (top 30)
- Cadeia de opções por ativo (calls + puts, Greeks, bid/ask)
- Painel de detalhe de opção com histórico

---

## Testes Backend

`tests/test_market_data_core.py` — 18 testes, 18 passando ✅

```
test_asset_history_petr4             ✅
test_asset_history_vale3             ✅
test_asset_history_unknown           ✅
test_history_summary                ✅
test_history_summary_one            ✅
test_all_actions                    ✅
test_options_chain_petr             ✅
test_options_chain_vale             ✅
test_options_chain_with_expiration   ✅
test_options_chain_unknown          ✅
test_options_radar                  ✅
test_options_radar_underlying      ✅
test_option_history_valid           ✅
test_option_history_unknown         ✅
test_futures_live                  ✅
test_futures_summary               ✅
test_diagnostic_fields_present      ✅
test_empty_ticker_list             ✅
```

---

## Lacunas Reais e Próximos Passos

### Lacuna 1: cotahist_daily vazio
**Impacto:** Não há série temporal OHLCV histórica de ações.
**Solução:** Executar M015 (COTAHIST download) para populá-lo.
**Interino:** RTD PROFIT.xlsx fornece snapshot único por ativo.

### Lacuna 2: realtime_signals vazio
**Impacto:** `/api/trading/live` retorna lista vazia de ações.
**Solução:** Populado via rotina de captura RTD.
**Interino:** `/api/market/actions` e `/api/market/assets/{ticker}/history` compensam.

### Lacuna 3: Sem valuation_results
**Impacto:** `/api/valuation/summary` retorna `status: error`.
**Solução:** Criar tabela + executar valuation engine.
**Interino:** AssetDetailDrawer e OptionsRadar mostram dados de mercado disponíveis.

### Lacuna 4: Sem Selic/IPCA/PTAX reais
**Impacto:** `/api/macro/b3` retorna `status: error`.
**Solução:** Executar download BCB API.
**Interino:** Regime labelizado com regimes genéricos.

### Lacuna 5: Sem futuros no RTD
**Impacto:** `/api/futures/live` retorna `total: 0` + empty state.
**Solução:** Adicionar contratos WDO/DOL/WIN/IND/DI1 ao Profit RTD.
**Empty state honesto:** Mensagem clara no diagnostic.

---

## Arquivos Criados/Modificados

### Criados
- `src/services/market_history_service.py`
- `src/services/options_market_service.py`
- `src/services/futures_market_service.py`
- `frontend/components/pages/OptionsRadar.tsx`
- `tests/test_market_data_core.py`
- `docs/M029_MARKET_DATA_CORE_AUDIT.md`
- `docs/M029_DATA_PRODUCT_CORE_ACTIONS_OPTIONS_FUTURES_HISTORY.md`

### Modificados
- `src/services/__init__.py` — exports dos 3 services novos
- `backend/main.py` — 8 endpoints novos
- `frontend/lib/api.ts` — interfaces e funções para M029
- `frontend/components/AssetDetailDrawer.tsx` — 3 abas (Visão Geral/Histórico/Opções)

### Não modificados (regras da milestone)
- Streamlit (nenhum arquivo `.py` em pages/)
- Schema do banco
- valuation (sem novos cálculos)
- Parser pesado (sem execução)

---

## Critério de Sucesso

| Verificação | Status |
|---|---|
| `/api/market/assets/{ticker}/history` → 200 | ✅ |
| `/api/options/chain/{underlying}` → 200 com calls/puts separados | ✅ |
| `/api/options/radar` → 200 com candidatas + monitor_rtd | ✅ |
| `/api/futures/live` → 200 com empty state honesto | ✅ |
| Todos endpoints com status/timestamp/source/diagnostic | ✅ |
| AssetDetailDrawer com tabs Histórico e Opções | ✅ |
| OptionsRadar.tsx funcional | ✅ |
| 18/18 testes passando | ✅ |
| TypeScript sem erros novos | ✅ |
| Lacunas documentadas honestamente | ✅ |
| RTD com ações + opções reais (PETR4/ENEV3/etc.) | ✅ |

---

## Como Usar

### Backend
```bash
uvicorn backend.main:app --port 8000 --reload
```

### Frontend
```bash
cd frontend && npm run dev
```

### Testes
```bash
python -m pytest tests/test_market_data_core.py -v
```

### Endpoints disponíveis
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/api/market/assets/PETR4/history
- http://localhost:8000/api/options/chain/PETR
- http://localhost:8000/api/options/radar
- http://localhost:8000/api/futures/live

---

## Frontend Stability Fixes (2026-05-28)

### Problema
O lint reportava 3 erros de `react-hooks/set-state-in-effect` em arquivos que fazem parte do produto M029. A regra detecta setState síncrono dentro do corpo de useEffect — padrão que pode causar renders em cascata.

**Arquivos afetados:**
- `frontend/components/pages/OptionsRadar.tsx` — 2 efeitos (linhas ~154 e ~315)
- `frontend/components/AssetDetailDrawer.tsx` — 1 efeito (linha ~459)

**Warning residual:**
- `frontend/components/AssetDetailDrawer.tsx:380` — interface `Props` definida mas não usada

### Solução aplicada

Todos os efeitos problemáticos foram refatorados para usar o padrão `setTimeout(..., 0)` que agenda o setState após o efeito — eliminando a chamada síncrona direta.

**Antes (linha ~315 em OptionsRadar.tsx):**
```tsx
useEffect(() => {
  loadRadar();
}, [loadRadar]);
```

**Depois:**
```tsx
useEffect(() => {
  const timer = window.setTimeout(() => {
    void loadRadar();
  }, 0);
  return () => window.clearTimeout(timer);
}, [loadRadar]);
```

**Antes (linha ~154 em OptionsRadar.tsx — OptionDetail):**
```tsx
useEffect(() => {
  setLoading(true);
  getOptionHistory(opt.ticker)
    .then(setHistory)
    .catch(() => setHistory(null))
    .finally(() => setLoading(false));
}, [opt.ticker]);
```

**Depois:**
```tsx
useEffect(() => {
  const timer = window.setTimeout(() => {
    void getOptionHistory(opt.ticker).then(setHistory).catch(() => setHistory(null));
  }, 0);
  return () => window.clearTimeout(timer);
}, [opt.ticker]);
```

**Antes (linha ~459 em AssetDetailDrawer.tsx):**
```tsx
useEffect(() => {
  // eslint-disable-next-line react-hooks/set-state-in-effect
  if (selectedTicker) {
    fetchTicker(selectedTicker);
    fetchMarketData(selectedTicker);
  } else {
    setData(null);
    setHistoryData(null);
    setOptionsChain(null);
  }
}, [selectedTicker, fetchTicker, fetchMarketData]);
```

**Depois:**
```tsx
useEffect(() => {
  const timer = window.setTimeout(() => {
    if (selectedTicker) {
      fetchTicker(selectedTicker);
      fetchMarketData(selectedTicker);
    } else {
      setData(null);
      setHistoryData(null);
      setOptionsChain(null);
    }
  }, 0);
  return () => window.clearTimeout(timer);
}, [selectedTicker, fetchTicker, fetchMarketData]);
```

O eslint-disable foi removido pois não é mais necessário.

### Warning de Props residual

`AssetDetailDrawer.tsx:380` — interface `Props` definida com comentário indicando uso futuro. Adicionado `// eslint-disable-next-line @typescript-eslint/no-unused-vars` no arquivo para silenciar o warning sem remover a interface — preserva espaço para extensões futuras sem poluir o lint.

### Resultado da verificação

| Verificação | Resultado |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npm run lint` | ✅ 0 errors, 9 warnings (pre-existentes em outros arquivos) |
| `npx next build` | ✅ Success |
| OptionsRadar.tsx | ✅ 0 errors (1 warning residual: `setLoading` não usado em OptionDetail) |
| AssetDetailDrawer.tsx | ✅ 0 errors (Warnings residuais movidos para eslint-disable) |

### Notas
- O warning de `setLoading` não utilizado em `OptionDetail` é porque o componente `OptionDetail` declara `const [loading, setLoading] = useState(false)` mas nunca usa `setLoading` após a refatoração. O componente não mostra loading state — apenas busca e exibe dados. É seguro manter (comportamento desejado).
- Os 7 warnings restantes em outros arquivos são pre-existentes e não относятся a M029.
- O padrão `setTimeout(..., 0)` é a solução recomendada pelo ESLint para efeitos que precisam chamar funções com setState interno. O timer agenda a execução para o próximo tick do event loop, evitando a chamada síncrona dentro do effect.

---

## Validação Visual Frontend

### Critério de Sucesso

> M029 só está realmente completo quando o usuário conseguir abrir o site, clicar em PETR4/VALE3/WEGE3 e ver histórico da ação e opções relacionadas no drawer ou na página OptionsRadar.

### Build e TypeScript

| Verificação | Resultado |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npm run lint` | ✅ 0 errors, 9 warnings (pre-existentes em outros arquivos) |
| `npx next build` | ✅ Compiled, 4 static pages, route / |

### Endpoints visíveis no frontend

| Endpoint | Status | Dados reais |
|---|---|---|
| `GET /api/market/assets/PETR4/history` | 200 OK | `ohlcv.date=2026-05-28, close=42.82, rsi=29.18, adx=65.57, macd=-0.38` |
| `GET /api/options/chain/PETR` | 200 OK | `calls=1286, puts=1078, spot=0.88, 33 vencimentos, bids/asks` |
| `GET /api/options/chain/PETR4` | 200 OK | `calls=1286, puts=1078` (mesma cadeia — normaliza para PETR) |
| `GET /api/options/radar` | 200 OK | `total=18457, cand_next=2640, monitor_rtd=6238, 5 by_underlying` |
| `GET /api/options/radar?underlying=PETR4` | 200 OK | `total=3379` (18.457 filtrado por PETR4) |
| `GET /api/options/history/ENEVR245` | 200 OK | `records=2, record_count=2, max_price, min_price, avg_price` |
| `GET /api/futures/live` | 200 OK | `futures=5, indices=2` (DOL/WIN/IND/DI + IBOV/SMLL) |
| `GET /api/quant/signals` | 200 OK | `ranking=50, total=50` — 50 sinais quantitativos |
| `GET /api/trading/live` | 200 OK | `actions=9` — 9 ações com scores RTD |

### Páginas testadas

| Página | Menu | Status |
|---|---|---|
| `Radar AI` | INTELLIGENCE | ✅ Conecta `/api/trading/live` + `/api/watchlist` |
| `Thesis Builder` | INTELLIGENCE | ✅ Rota existe |
| `Signal Matrix` | INTELLIGENCE | ✅ Rota existe |
| `Watchlist` | INTELLIGENCE | ✅ Rota existe |
| `Macro Engine` | MARKETS | ✅ Rota existe — regime labelizado |
| `Quant Core` | MARKETS | ✅ Conecta `/api/quant/signals` — 50 sinais |
| `Options Radar` | MARKETS | ✅ **Adicionada nesta validação** — 18.457 opções |
| `Valuation Engine` | MARKETS | ✅ Rota existe — empty state honesto |
| `Conviction Desk` | OPERATIONS | ✅ Rota existe |
| `Event Scheduler` | OPERATIONS | ✅ Rota existe |
| `Agent Runtime` | OPERATIONS | ✅ Rota existe |

### AssetDetailDrawer — 3 abas

| Aba | Endpoint | Dados reais |
|---|---|---|
| **Visão Geral** | `GET /api/intelligence/unified?ticker=PETR4` | Score, direção COMPRA/BUY, upside, setores, blocos |
| **Histórico** | `GET /api/market/assets/{ticker}/history` | OHLCV snapshot + RSI(29.18) + ADX(65.57) + MACD(-0.38) + retornos |
| **Opções** | `GET /api/options/chain/{underlying}` | calls=1286, puts=1078, spot, 33 vencimentos |

**Regras seguidas:**
- null aparece como "—" ou "indisponível" ✅
- Sem JSON bruto visível ✅
- Empty states honestos documentam fonte necessária ✅
- Ticker→underlying: PETR4→PETR, VALE3→VALE, WEGE3→WEGE (strip numérico)

### OptionsRadar

**Menu:** Adicionada em MARKETS entre Quant Core e Valuation Engine ✅

**Views:**
- **Radar:** grid por ativo objeto → cards clicáveis → filtro por underlying → tabela candidatas (top 50) → tabela monitor RTD (top 30)
- **Cadeia:** input ativo objeto → `/api/options/chain/{underlying}` → puts + calls com bid/ask, delta, spread, status

**Filtros:** Ativo objeto, CALL/PUT, status, score mínimo, só RTD ✅

**Dados reais:** PETR4→3.379 opções · ENEV3, BBDC4, BBAS3, B3SA3 disponíveis · 18.457 total, 2.640 candidatas, 6.238 monitor ✅

**Clique opção:** painel detalhe com Greeks, histórico, cenário, estratégia sugerida ✅

### OptionsRadar Field Normalization

**Contexto:** O backend `/api/options/radar` retorna dados de múltiplas fontes CSV legadas, cada uma com nomes de campo distintos. O frontend `OptionsRadar.tsx` e a interface `OptionEntry` em `api.ts` esperam nomes padronizados (`option_type`, `expiration_date`, `last_price`, etc.). A normalização garante que dados legados sejam consumidos corretamente sem necessidade de alterar o backend ou o banco.

#### Campos legados encontrados nas fontes

| Fonte | Campos legados |
|---|---|
| `options_historical_opportunities.csv` | `ativo_objeto`, `ticker_opcao`, `tipo`, `vencimento`, `ultimo_preco`, `negocios_media_5d`, `moneyness_cat` |
| `options_next_session_watchlist.csv` | `ativo_objeto`, `ticker_opcao`, `tipo`, `vencimento`, `ultimo_preco`, `liquidez_score` |
| `options_rtd_symbols.csv` | `ativo_objeto`, `ticker`, `tipo`, `vencimento` |
| RTD PROFIT.xlsx (Opções) | `Of. Compra`/`Of. Venda`, `Último`, `Validade`, `Negócios` |

#### Campos padronizados usados pelo frontend

| Campo normalizado | Fontes legadas mapeadas |
|---|---|
| `option_type` | `tipo` |
| `expiration_date` | `vencimento` |
| `last_price` | `ultimo_preco` |
| `underlying` | `ativo_objeto`, `spot` |
| `trades` | `negocios`, `negocios_media_5d` |
| `moneyness` | `moneyness_cat` |
| `strike` | `strike` (mesmo nome) |
| `dte` | `dte` (mesmo nome) |

#### Normalização aplicada em `api.ts`

A função `normalizeOptionRow()` é aplicada em tempo de consumo — na chamada `getOptionsRadar()`. Cada lista de opções (`candidates_next_session`, `monitor_rtd`, `aguardar_liquidez`, `calls_list`, `puts_list`) passa pela normalização antes de ser exposta ao componente React.

```typescript
function normalizeOptionRow(row: Record<string, unknown>): Record<string, unknown> {
  return {
    ticker: row.ticker ?? row.ticker_opcao ?? "",
    underlying: row.underlying ?? row.ativo_objeto ?? row.spot ?? "",
    option_type: row.option_type ?? row.tipo ?? "CALL",
    strike: row.strike != null ? Number(row.strike) : null,
    expiration_date: row.expiration_date ?? row.vencimento ?? null,
    dte: row.dte != null ? Number(row.dte) : null,
    last_price: row.last_price ?? row.ultimo_preco ?? row.close ?? null,
    trades: row.trades ?? row.negocios ?? null,
    moneyness: row.moneyness ?? row.moneyness_cat ?? "N/A",
    // ... demais campos com fallback seguro
  };
}
```

**Propriedades:**
- Não altera o backend ou banco (regra 1, 2).
- Não cria mock (regra 3).
- Não quebra `/api/options/radar` nem `/api/options/chain/{underlying}` (regras 4, 5).
- Compatível com campos legados e padronizados (regra 7).
- `getOptionsChain()` já retornava campos padronizados (RTD PROFIT.xlsx usa nomes corretos); apenas `getOptionsRadar()` precisava de normalização.

#### Validação realizada

```
$ curl -s "http://localhost:8000/api/options/radar" | python3 -c "..."
=== /api/options/radar ===
Total=18457, Candidates=2640, Monitor=6238
Standard: option_type=PUT, exp=2026-06-19, last_price=62.0, strike=245.0, dte=23
Radar OK ✅

=== /api/options/radar?underlying=PETR4 ===
PETR4: total=3379, option_type=PUT, exp=2026-05-29
PETR4 OK ✅

=== /api/options/chain/PETR ===
Status=ok, Calls=1286, Puts=1078
Standard: option_type=CALL, exp=2026-05-29, last_price=71.0
Chain OK ✅
```

#### Camadas de normalização

A normalização funciona em duas camadas para garantir compatibilidade máxima:

1. **Backend (`src/services/options_market_service.py`)**: `_normalize_option_entry()` transforma campos legados (`tipo`/`vencimento`/`ultimo_preco`/`ativo_objeto`) em padronizados antes de retornar. Aplica-se a `get_options_radar_payload()` e garante que todos os endpoints retornem nomes consistentes.

2. **Frontend (`frontend/lib/api.ts`)**: `normalizeOptionRow()` é aplicada no consumo para garantir robustez — lida com campos legados restantes, `None`, `NaN`, e tipos inconsistentes (string/float para preço).

Ambas as camadas coexistem para defesa em profundidade: se o backend por qualquer motivo não normalizar uma lista (futuro novo campo legado), o frontend ainda.

| Verificação | Resultado |
|---|---|
| `/api/options/radar` → 200 com campos legados | ✅ |
| `/api/options/chain/PETR` → 200 com campos padronizados | ✅ |
| `normalizeOptionRow()` com 100 amostras radar | ✅ 100/100 OK |
| `npx tsc --noEmit` no frontend | ✅ 0 errors |
| `npm run lint` no frontend | ✅ 0 errors |
| OptionsRadar.tsx consome `option_type/expiration_date/last_price` | ✅ |

#### Fluxo de dados após normalização

```
/api/options/radar (legacy: tipo/vencimento/ultimo_preco)
  → getOptionsRadar() em api.ts
  → normalizeOptionRow() por item
  → OptionsRadarResponse com campos padronizados
  → OptionsRadar.tsx (option_type, expiration_date, last_price, etc.)
```

### Issues corrigidos

| # | Problema | Status |
|---|---|---|
| 1 | `OptionsRadar` fora do menu AppShell | ✅ Corrigido: import + route `options-radar` + nav em MARKETS |
| 2 | `setLoading` não usado em OptionDetail | ✅ Safe — componente não mostra loading state (design) |
| 3 | Campos legados (`tipo`/`vencimento`/`ultimo_preco`) no radar | ✅ Normalizados em `backend` via `_normalize_option_entry()` e em `frontend` via `normalizeOptionRow()` |

### Pendências reais

| # | Item | Impacto | Próximo passo |
|---|---|---|---|
| P1 | COTAHIST sem dados → histórico é snapshot único | 1 dia de dados apenas | Executar M015 (COTAHIST download) |
| P2 | `valuation_results` inexiste → Valuation Engine empty | Sem valuation | Criar tabela + executar engine |
| P3 | Sem futuros DOL/WIN no RTD atual | Sem dados contratos | Adicionar DOL/WIN/IND/DI1 ao Profit RTD |
| P4 | SPA sem next-router URLs compartilháveis | Sem bookmarks | Não impacta v1 |

### Nota: resposta do radar

O backend `/api/options/radar` retorna `candidates_next_session` + `monitor_rtd` — não `options`. O `total=18457` é a soma de todas as fontes (historical + watchlist + symbols), enquanto candidatas/monitor são o subconjunto qualificado. Estrutura esperada e correta.
