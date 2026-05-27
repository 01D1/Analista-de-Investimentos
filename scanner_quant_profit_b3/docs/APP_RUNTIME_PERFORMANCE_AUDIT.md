# APP_RUNTIME_PERFORMANCE_AUDIT.md

**Data:** 2026-05-26  
**Auditoria:** App Runtime + Performance Debug — Streamlit Pages  
**Escopo:** Diagnóstico e correção de gargalos de carregamento em todas as páginas ativas

---

## 1. Bancos Confirmados

| Banco | Localização | Count |
|---|---|---|
| `scanner_quant.db` | `data/database/scanner_quant.db` | — |
| ↳ `asset_intelligence_snapshots` | — | **64 linhas** |
| ↳ `macro_series` | — | **146 linhas** |
| ↳ `market_regime_daily` | — | **81 linhas** |
| ↳ `risk_snapshots` | — | **66 linhas** |
| ↳ `source_health_checks` | — | **28 linhas** |
| ↳ `cotahist_daily` | — | **9.508.079 linhas** ⚠️ |
| `ingestion.db` | `../12_PYTHON/data/ingestion.db` | — |
| ↳ `valuation_financial_inputs` | — | **47.621 linhas** |

> ⚠️ `cotahist_daily` com 9.5M linhas — qualquer `SELECT *` aqui seria catastrófico. Não há acesso direto nas páginas Streamlit (somente via `_get_market_price()` com `LIMIT 1`).

---

## 2. Diagnóstico de Gargalos por Página

### 2.1 Radar AI (`pages/radar_ai.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| Import | OK | — | — |
| Carregamento de dados | **Lento (2–10s)** | `get_watchlist_summary()` sem cache — chamava `_bridge_valuation()` para cada ticker (leitura de Excel) | `@st.cache_data(ttl=300)` em `data.py` |
| Queries SQL | OK | — | — |
| Renderização | OK | — | — |
| **Status final** | ✅ Corrigido | | |

### 2.2 Valuation Engine (`pages/valuation_engine.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| Import | OK | — | — |
| `_load_inputs_kpis()` | **Sem cache** | COUNT/GROUP BY queries a cada render | `@st.cache_data(ttl=300)` |
| `_load_market_prices()` | **Sem cache + SELECT * + Python dedup** | Carregava todas as linhas; Python deduplicava | `@st.cache_data` + SQL `MAX(created_at) GROUP BY` |
| `_load_dry_run_matrix()` | **Sem cache** | CSV lido a cada render | `@st.cache_data(ttl=300)` |
| `_load_preliminary_results()` | **Sem cache** | DB scan a cada render | `@st.cache_data(ttl=300)` |
| `_load_fundamental_quality_rows()` | **Sem cache** | DB scan a cada render | `@st.cache_data(ttl=300)` |
| Métricas-chave (N×M queries) | **Sem cache** | 68 queries individuais (17 tickers × 4 métricas) | Extraído para `_load_key_metrics()` com `@st.cache_data(ttl=300)` |
| **Status final** | ✅ Corrigido | | |

### 2.3 Cobertura de Valuation (`pages/valuation_coverage.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `_load_market_prices()` | **Sem cache + Python dedup** | Mesmo padrão do valuation_engine | `@st.cache_data` + SQL GROUP BY |
| `_load_ingestion_kpis()` | **Sem cache** | COUNT queries a cada render | `@st.cache_data(ttl=300)` |
| `_load_dry_run_matrix()` | **Sem cache** | CSV lido a cada render | `@st.cache_data(ttl=300)` |
| `_load_preliminary_sanity_map()` | **Sem cache** | DB scan a cada render | `@st.cache_data(ttl=300)` |
| `_load_preliminary_fv_map()` | **Sem cache** | DB scan a cada render | `@st.cache_data(ttl=300)` |
| **Status final** | ✅ Corrigido | | |

### 2.4 Núcleo Quantitativo (`pages/radar_quant.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `_load_all()` | **Sem cache** | 5 queries SQL + list_valid_valuations() a cada render | `@st.cache_data(ttl=300)` |
| **Status final** | ✅ Corrigido | | |

### 2.5 Macro Motor (`pages/inteligencia_macro.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `get_macro_panel()` | **Sem cache** | 3 queries + regime query a cada render | `@st.cache_data(ttl=300)` em `data.py` |
| **Status final** | ✅ Corrigido | | |

### 2.6 Matriz de Sinais (`pages/inteligencia_oportunidades.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `get_opportunities()` | **Sem cache** | snapshot DB load + sort a cada render | `@st.cache_data(ttl=300)` em `data.py` |
| **Status final** | ✅ Corrigido | | |

### 2.7 Construtor de Tese (`pages/inteligencia_ativo.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `get_watchlist_summary()` | **Sem cache** | Excel bridge loop | `@st.cache_data(ttl=300)` em `data.py` |
| `get_asset_detail(ticker)` | **Sem cache** | Snapshot + bridge valuation por ticker | `@st.cache_data(ttl=300)` em `data.py` |
| **Status final** | ✅ Corrigido | | |

### 2.8 Opções Monitor (`pages/opcoes_monitoramento.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| Leitura de posições | OK | `get_open_options_positions()` com LIMIT implícito | — |
| **Status final** | ✅ Sem alteração necessária | | |

### 2.9 Mesa de Convicção (`pages/performance.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| Journal DB | OK | Leitura de `journal.db` — tabela pequena | — |
| **Status final** | ✅ Sem alteração necessária | | |

### 2.10 Agent Runtime (`pages/agendador.py`) / Event Scheduler (`pages/calendario.py`)

| Dimensão | Status antes | Gargalo identificado | Correção aplicada |
|---|---|---|---|
| `_load_source_health()` | Carregado no módulo (module-level) | Executa apenas uma vez por sessão | — |
| `_load_calendar_events()` | Carregado no módulo (module-level) | Executa apenas uma vez por sessão | — |
| **Status final** | ✅ Sem alteração necessária | | |

---

## 3. Correções Aplicadas — Resumo

### `src/dashboard/data.py`

```python
# Adicionado @st.cache_data(ttl=300) a:
@st.cache_data(ttl=300, show_spinner=False)
def get_watchlist_summary() -> list[dict]: ...

@st.cache_data(ttl=300, show_spinner=False)
def get_asset_detail(ticker: str) -> dict | None: ...

@st.cache_data(ttl=300, show_spinner=False)
def get_macro_panel() -> dict[str, list[dict]]: ...

@st.cache_data(ttl=300, show_spinner=False)
def get_opportunities() -> list[dict]: ...

@st.cache_data(ttl=120, show_spinner=False)
def get_risk_snapshots(tickers: tuple[str, ...] | None = None) -> list[dict]: ...

@st.cache_data(ttl=120, show_spinner=False)
def get_option_structure_candidates(tickers: tuple[str, ...] | None = None) -> list[dict]: ...
```

> **Nota:** `get_risk_snapshots()` e `get_option_structure_candidates()` passaram a aceitar `tuple` (hashable) em vez de `list` para compatibilidade com o cache.

### `pages/valuation_engine.py`

- `@st.cache_data(ttl=300)` em: `_load_preliminary_results`, `_load_market_prices`, `_load_dry_run_matrix`, `_load_inputs_kpis`, `_load_fundamental_quality_rows`
- Nova função `_load_key_metrics()` com `@st.cache_data(ttl=300)` — extrai o loop de métricas-chave para função cached
- `_load_market_prices()`: query melhorada com `MAX(created_at) GROUP BY ticker` — elimina dedup Python
- Spinner adicionado em `tabs[0]` para feedback visual

### `pages/valuation_coverage.py`

- `@st.cache_data(ttl=300)` em: `_load_market_prices`, `_load_ingestion_kpis`, `_load_dry_run_matrix`, `_load_preliminary_sanity_map`, `_load_preliminary_fv_map`
- `_load_market_prices()`: mesma melhoria de query GROUP BY

### `pages/radar_quant.py`

- `@st.cache_data(ttl=300)` em `_load_all()`

### `pages/radar_ai.py`

- `get_risk_snapshots(tickers=selected)` → `get_risk_snapshots(tickers=tuple(sorted(selected)))` para cache hashable
- Spinner adicionado: `with st.spinner("Carregando inteligência...")`

---

## 4. Validações Finais

```
python -m py_compile app.py pages/*.py src/dashboard/data.py  → ALL OK
Writes em banco → 0 (verificado grep por INSERT/UPDATE/DELETE/commit)
Fair values calculados → 0
Cache decorators → 18 funções no total (6+6+5+1)
```

### Contagem de funções cacheadas

| Arquivo | Funções cacheadas |
|---|---|
| `src/dashboard/data.py` | 6 |
| `pages/valuation_engine.py` | 6 |
| `pages/valuation_coverage.py` | 5 |
| `pages/radar_quant.py` | 1 |
| **Total** | **18** |

---

## 5. Impacto Esperado

| Página | Antes (estimado) | Depois (estimado) |
|---|---|---|
| Radar AI | 3–10s (Excel bridge loop) | < 0.5s (cache warm) |
| Valuation Engine | 2–5s (múltiplas queries) | < 0.3s (cache warm) |
| Cobertura de Valuation | 2–4s (5 DB calls) | < 0.3s (cache warm) |
| Núcleo Quantitativo | 1–3s (5 queries) | < 0.2s (cache warm) |
| Macro Motor | 1–2s (4 queries) | < 0.2s (cache warm) |
| Matriz de Sinais | 1–2s (snapshot load) | < 0.2s (cache warm) |

**Cache TTL:** 300s (5 min) — dados financeiros não mudam a cada render.  
**Primeiro load (cache frio):** Tempo original + inicialização do cache.  
**Reloads seguintes (cache quente):** Praticamente zero para queries e Excel I/O.

---

## 6. Regras Preservadas

- ✅ Nenhum cálculo de fair_value novo
- ✅ Nenhuma escrita no banco
- ✅ Nenhum parser executado
- ✅ Nenhum scheduler executado
- ✅ Nenhum mock criado
- ✅ M019 não iniciado
- ✅ Modelos de valuation não alterados
- ✅ Erros não escondidos com try/except silencioso
- ✅ data/raw/cvm/filtered não acessado em páginas Streamlit
- ✅ Tabelas grandes possuem limitação (LIMIT nas queries)
