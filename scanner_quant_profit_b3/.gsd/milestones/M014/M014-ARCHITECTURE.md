# M014 — Universal Sector Valuation Architecture

**Versão:** 1.0.0 | **Data:** 2026-05-24 | **Milestone:** M014 | **Status:** Documentada

---

## 1. Visão Geral

Esta arquitetura define o pipeline completo de valuation universal para o scanner quant profit B3.
O objetivo é: dado um ticker, o sistema determina automaticamente o método de valuation correto,
coleta os dados necessários, calcula o fair value e expõe o resultado de forma padronizada — sem
inventar números, sem mocks, sem quebrar o que já funciona.

**Princípio central:** _valuar apenas o que se pode auditar._

---

## 2. Camadas do Pipeline

```
cotahist / ri_documents / asset_intelligence
        │
        ▼
┌──────────────────────────────────────────────┐
│  CAMADA 1: INGESTION CVM/RI                  │
│  ────────────────────────────────────────────│
│  • CVM DFP/ITR/IPE parsers                  │
│  • RI PDF text extraction                    │
│  • B3 Cotahist price history                │
│  • BCB macro series (Selic, PTAX, CDS)      │
│  • Saída: dados financeiros normalizados    │
│    em banco SQLite (b3_financials)          │
│  • Gated by: fundamental_quality_score      │
│    derived from data completeness           │
└──────────────────┬─────────────────────────┘
                   │ dados normalizados em b3_financials
                   ▼
┌──────────────────────────────────────────────┐
│  CAMADA 2: SETORIZAÇÃO                       │
│  ────────────────────────────────────────────│
│  • Source: asset_intelligence.sector         │
│    OU manual override                        │
│  • Canonical sector map:                    │
│    BANK, INSURANCE, COMMODITY, UTILITY,     │
│    INDUSTRY, RETAIL, HOLDING, TECH,         │
│    FALLBACK_MULTIPLES                        │
│  • Rastreável: provenance field em          │
│    asset_intelligence (source, date,         │
│    analyst_override)                         │
│  • NEEDS_SECTOR: tickers sem setor          │
│    rastreável → bloqueia routing            │
└──────────────────┬─────────────────────────┘
                   │ setor confirmado + source=TRACEABLE
                   ▼
┌──────────────────────────────────────────────┐
│  CAMADA 3: SECTOR ROUTER (S04)               │
│  ────────────────────────────────────────────│
│  • Input: ticker, sector, coverage_status    │
│  • Output: routing decision + valuation_     │
│    method recomendado + confidence           │
│  • Tabela de routing:                       │
│  │ Sector           │ Method Primary  │ Alt │ │
│  │ BANK             │ COSIF/DDM       │ DCF │ │
│  │ INSURANCE        │ DDM             │ M.P.│ │
│  │ COMMODITY        │ DCF             │ M.P.│ │
│  │ UTILITY          │ DCF             │ RAB │ │
│  │ INDUSTRY         │ DCF             │ M.P.│ │
│  │ RETAIL           │ DCF             │ EV/ │ │
│  │                   │                 │EBITD│ │
│  │ HOLDING          │ NAV             │ DCF │ │
│  │ TECH             │ DCF             │ SOTP│ │
│  │ FALLBACK_MULTIPLES│ Relativos      │ N/A │ │
│  • RULES:                                   │
│    - NEEDS_CVM_DATA → ROUTE_BLOCKED         │
│    - NEEDS_SECTOR → ROUTE_BLOCKED          │
│    - coverage READY → route direto           │
│    - coverage PARTIAL → route com alerta    │
│    - coverage EMPTY → ROUTE_UNAVAILABLE      │
│  • NÃO calcula valuation — apenas routing   │
└──────────────────┬─────────────────────────┘
                   │ routing_decision + method + inputs dict
                   ▼
┌──────────────────────────────────────────────┐
│  CAMADA 4: VALUATION ENGINE (futuro S06+)   │
│  ────────────────────────────────────────────│
│  • Implementação setorial por método:        │
│    DCF universal, COSIF/DDM, NAV, RAB,     │
│    EV/EBITDA, múltiplos relativos           │
│  • Inputs: financial_data + macro +        │
│    sector_config + router_decision          │
│  • Outputs: fair_value, upside_pct,         │
│    confidence, methodology notes            │
│  • Valuation method: OUTPUT do modelo,      │
│    não input                                  │
│  • fundamental_quality_score: OUTPUT do     │
│    motor fundamentalista, não input          │
│  • Validações:                              │
│    - terminal_growth < WACC                 │
│    - fair_value within 0.1x–5.0x price       │
│    - WACC bounded (Selic + risk premium)    │
└──────────────────┬─────────────────────────┘
                   │ valuation_results
                   ▼
┌──────────────────────────────────────────────┐
│  CAMADA 5: STORES CANÔNICOS (S05)            │
│  ────────────────────────────────────────────│
│  4 stores padronizados:                     │
│  1. valuation_results  — resultados          │
│  2. valuation_inputs   — inputs usados       │
│  3. valuation_coverage — status por ticker   │
│  4. valuation_store    — store de fachada    │
│  • Coexistem com bridge existente em         │
│    src/integration/connectors/               │
│    valuation_connector.py (M012/M013)       │
│  • Dashboard lê via stores — não muda         │
│    connector antigo                           │
│  • fair_values existentes PRESERVADOS        │
└──────────────────────────────────────────────┘
```

---

## 3. Fluxo Completo

```
┌──────────────────────────────────────────────────────────────────────┐
│  FLUXO: cotahist/ri_documents/asset_intelligence → coverage          │
│         → sector → router → valuation inputs/results → dashboard     │
└──────────────────────────────────────────────────────────────────────┘

cotahist/
  └── b3_prices (preço histórico, market_price)
        │
ri_documents/
  └── CVM DFP/ITR/IPE → b3_financials (financial_data)
        │
asset_intelligence/
  └── sector, valuation_flag, fair_value, market_price, upside_pct
        │          valuation_method, fundamental_quality_score
        ▼
valuation_coverage/
  └── classify_coverage(ticker) → READY/PARTIAL/EMPTY/NEEDS_MODEL/NEEDS_DATA
        │
sector_router (S04)
  └── route(ticker, sector, coverage_status) → routing_decision + method
        │
valuation_engine (S06+)
  └── calculate(inputs) → fair_value, upside_pct, confidence
        │
stores canônicos (S05)
  └── valuation_results / valuation_inputs / valuation_coverage / valuation_store
        │
dashboard
  └── valuation_engine page / radar_ai / inteligencia_ativo
        │
valuation_connector.py (M012/M013 — PRESERVADO)
  └── get_valuations_batch → old pipeline outputs/ (backup)
```

---

## 4. Regras Arquiteturais (Constraints)

| # | Regra | Impacto |
|---|-------|---------|
| R1 | Tickers com `coverage = NEEDS_CVM_DATA` **não entram** no valuation engine. Routing é bloqueado. | Garante que não se valua com dados incompletos |
| R2 | Tickers com `coverage = NEEDS_SECTOR` precisam de fonte rastreável (`provenance.source != NULL`). Override manual é permitido com auditoria. | Evita setor genérico que quebra o router |
| R3 | `valuation_method` é **output** do modelo, não input. O router sugere; o engine decide. | Impede que o método seja hardcoded ou inventado |
| R4 | `fundamental_quality_score` é **output** do motor fundamentalista (completude + consistência dos dados). Não é input nem estimativa. | Evita qualidade fictícia |
| R5 | fair_values existentes em `asset_intelligence` são **preservados**. Novos cálculos só substituem se confidence > existing_confidence. | Preserva D077-D082 valuation reconciliation |
| R6 | Decisões D077–D082 de valuation reconciliation permanecem **intactas**. Nenhuma nova arquitetura pode contradizê-las. | Mantém governança de valuation |

---

## 5. Contratos Públicos (Interfaces)

### 5.1 Coverage Contract

```python
@dataclass
class CoverageResult:
    ticker: str
    status: CoverageStatus  # READY / PARTIAL / EMPTY / NEEDS_MODEL / NEEDS_DATA
    has_ai_entry: bool
    has_financials: bool     # b3_financials populated
    has_sector: bool
    has_price: bool
    has_fair_value: bool
    has_method: bool
    has_fqs: bool
    gaps: list[str]          # ["ri_docs", "sector", "method", ...]
```

**Linha de corte:** `NEEDS_CVM_DATA` se `ri_docs = 0` OU `financials incomplete`.
Fonte: `src/fundamentals/valuation_coverage.py`

### 5.2 Router Contract

```python
@dataclass
class RouterDecision:
    ticker: str
    sector: str
    method_primary: ValuationMethod
    method_alternatives: list[ValuationMethod]
    routing_status: RoutingStatus  # ROUTED / BLOCKED / UNAVAILABLE
    block_reason: str | None       # "NEEDS_CVM_DATA" / "NEEDS_SECTOR" / None
    confidence: float               # 0.0–1.0
    inputs_required: list[str]       # ["ebitda", "wacc", "growth_rate", ...]
```

**Fonte:** `src/valuation/router.py` (S04)

### 5.3 Valuation Engine Contract

```python
@dataclass
class ValuationInputs:
    ticker: str
    sector: str
    method: ValuationMethod
    financials: FinancialData       # do b3_financials
    price_data: PriceData          # do cotahist
    macro: MacroContext            # Selic, PTAX, CDS, IPCA
    router_decision: RouterDecision

@dataclass
class ValuationResult:
    ticker: str
    fair_value: float | None       # None se dados insuficientes
    upside_pct: float | None
    method_used: ValuationMethod
    confidence: float              # 0.0–1.0
    fundamental_quality_score: float | None
    validation_warnings: list[str]
    inputs_hash: str               # para cache/regeneração
```

**Fonte:** `src/valuation/engine.py` (S06+)

### 5.4 Store Contract

```python
class ValuationStore(Protocol):
    def get_result(self, ticker: str) -> ValuationResult | None: ...
    def get_coverage(self, ticker: str) -> CoverageResult: ...
    def get_inputs(self, ticker: str) -> ValuationInputs | None: ...
    def save_result(self, result: ValuationResult) -> None: ...
    def list_results(self, tickers: list[str]) -> list[ValuationResult]: ...
```

**Fonte:** `src/valuation/store.py` (S05)

---

## 6. Setores e Métodos

| Setor | Código | Método Primário | Métodos Alternativos | Notas Setoriais |
|-------|--------|-----------------|----------------------|-----------------|
| Bancos | `BANK` | COSIF/DDM | DCF | Usa COSIF NIM/ROE/DDM, NÃO IFRS EBITDA/DCF |
| Seguros | `INSURANCE` | DDM | Múltiplos | Reserve adequacy + combined ratio |
| Commodities | `COMMODITY` | DCF | Múltiplos | Volatilidade de preço como risco explícito |
| Utilidades | `UTILITY` | DCF | RAB | Regulated asset base para elétricas |
| Indústria | `INDUSTRY` | DCF | Múltiplos | Capex cycle management |
| Varejo | `RETAIL` | DCF | EV/EBITDA | Same-store growth + working capital |
| Holdings | `HOLDING` | NAV | DCF | SOTP — valor de participações |
| Tecnologia | `TECH` | DCF | SOTP | Growth + TAM como inputs-chave |
| Fallback | `FALLBACK_MULTIPLES` | Relativos | — | P/L, EV/EBITDA setorial apenas |

---

## 7. Rejeição de Tickers

```
┌─────────────────────────────────────────────────────────┐
│  ROUTING DECISION MATRIX                                │
├────────────────────┬────────────────────────────────────┤
│ NEEDS_CVM_DATA     │ BLOCKED — ri_docs=0 ou financials   │
│                    │ incompletos. Não entra no router.  │
├────────────────────┼────────────────────────────────────┤
│ NEEDS_SECTOR       │ BLOCKED — setor ausente ou          │
│                    │ source != TRACEABLE.                 │
├────────────────────┼────────────────────────────────────┤
│ NEEDS_MODEL        │ ROUTED com alerta — pode rodar mas  │
│                    │ confidence reduzida.                │
├────────────────────┼────────────────────────────────────┤
│ EMPTY              │ ROUTE_UNAVAILABLE — sem AI entry.   │
├────────────────────┼────────────────────────────────────┤
│ READY              │ ROUTED — confiança máxima.           │
├────────────────────┼────────────────────────────────────┤
│ PARTIAL            │ ROUTED — confiança intermediária.   │
└────────────────────┴────────────────────────────────────┘
```

---

## 8. Estados de Cobertura

Baseado em `src/fundamentals/valuation_coverage.py`:

| Status | Definição | Ação |
|--------|-----------|------|
| `READY` | ai_entry + financials + sector + price + fair_value + method + fqs = 7/7 | Valuation engine |
| `PARTIAL` | ai_entry + financials + sector + price = 4/7; faltan method/fqs/fair_value | Valuation com alerta |
| `NEEDS_MODEL` | ai_entry + financials + sector + price + fair_value = 5/7; faltan method ou fqs | Router → engine |
| `NEEDS_DATA` | ri_docs=0 OU financials incompletos OU price missing | Ingestion CVM/RI |
| `EMPTY` | Nenhuma AI entry encontrada | Asset intelligence entry |
| `NEEDS_SECTOR` | Setor ausente OU source=UNKNOWN | Setorização manual |

**S02.5 findings reais:**
- 29 tickers NEEDS_CVM_DATA (gap: ri_docs=0)
- 5 tickers NEEDS_SECTOR
- 0 ELIGIBLE_NOW (universo atual = vazio para valuation)

---

## 9. Preservação de Decisões Existentes

### D077–D082: Valuation Reconciliation Policy (PRESERVADAS)

Esta arquitetura não modifica, substitui ou contorna as decisões D077–D082.
Qualquer novo store, router ou engine deve ser compatível com:

- `valuation_connector.py` lendo de `outputs/Valuation_*.xlsx` (backup)
- fair_values existentes em `asset_intelligence` com `valuation_confidence` > 0
- `valuation_governance_status` em `VALUATION_AVAILABLE` quando existente

### Novos stores (S05) coexistem com bridge existente

```
valuation_store.py (S05)
    │
    ├── reads: b3_financials, asset_intelligence, cotahist
    │
    └── writes: valuation_results, valuation_inputs, valuation_coverage

valuation_connector.py (M012/M013 — EXISTENTE)
    │
    └── reads: outputs/Valuation_*.xlsx (old pipeline)

dashboard
    │
    ├── reads: valuation_store (novo) ← S05
    └── reads: valuation_connector (backup) ← M012/M013
```

---

## 10. Dependências por Slice

```
M014 S01  → audit coverage
M014 S02  → classify_coverage() + matriz operacional
M014 S02.5→ universo expansion (64 tickers, 0 ELIGIBLE_NOW)
M014 S03  → ESTE DOCUMENTO — arquitetura documentada
M014 S04  → sector_router.py (implementação)
M014 S05  → stores canônicos (4 stores)
M014 S06+ → valuation_engine.py (implementação setorial)
```

---

## 11. O Que Esta Arquitetura Proíbe

| Proibição | Razão |
|-----------|-------|
| Mock de preço justo | Viola o princípio "valuar apenas o que se pode auditar" |
| Preço justo inventado | Inverte o fluxo — method deve ser output, não input |
| valuation_method hardcoded por ticker | O router deve decidir; o engine pode override |
| Substituição de fair_value sem validation | Preserva D077–D082 reconciliation policy |
| Alteração de valuation_connector.py (M012/M013) | Bridge existente é backup, não alvo |
| Cálculo de valuation antes de S04+S05 | Stores e router são pré-requisitos |
| Modificação de D077–D082 | Decisões de governança são intocáveis |

---

## 12. Riscos Arquiteturais

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Setor mal atribuído bloqueia routing | Alta | Alta | S02.5 já mapeou 5 NEEDS_SECTOR; S04 valida source |
| D077–D082 conflita com novos stores | Baixa | Crítica | Arquitetura define coexistência, não substituição |
| fundamental_quality_score NULL impede router | Alta | Média | Motor fundamentalista em S06 calcula; interim usa proxy |
| CVM ingestion slow — 29 tickers bloqueados | Alta | Média | S01+S02 auditam; priorização por universo |
| Valuation engine coupling with old outputs/ | Média | Média | Bridge coexist; S05 store novo não escreve em outputs/ |

---

*Documento gerado em S03 do M014. Atualizar após S04 (sector router implementado).*
