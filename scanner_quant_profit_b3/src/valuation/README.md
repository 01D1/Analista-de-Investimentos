# `src/valuation/` — Valuation Universal

**Propósito:** Pipeline completo de valuation universal — sector router, valuation inputs, valuation results e stores canônicos. Este pacote é a base para o valuation de todos os tickers da watchlist B3.

---

## Visão Geral

O pacote `src/valuation/` é organizado em 4 módulos principais, implementados em slices do M014:

```
src/valuation/
├── __init__.py
├── README.md              # este arquivo
├── router.py             # S04: sector router universal
├── engine.py             # S06+: valuation engine (DCF/COSIF/DDM/etc.)
├── store.py              # S05: stores canônicos
└── models.py             # tipos compartilhados (ValuationMethod, etc.)
```

---

## O que faz

### 1. `router.py` (S04) — Sector Router

Determina o método de valuation correto para cada ticker baseado em setor e cobertura de dados.

```python
from src.valuation.router import route, RouterDecision, RoutingStatus

decision = route("ITUB4", sector="BANK", coverage_status="READY")
# RouterDecision(ticker="ITUB4", sector="BANK",
#               method_primary=ValuationMethod.COSIF_DDM,
#               routing_status=RoutingStatus.ROUTED,
#               block_reason=None, confidence=0.85,
#               inputs_required=["nim", "roe", "ddm", "cosif_captacao"])
```

**Regras de routing:**

| Coverage Status | Routing Status | Ação |
|-----------------|----------------|------|
| `NEEDS_CVM_DATA` | `BLOCKED` | Ingestion CVM/RI necessária |
| `NEEDS_SECTOR` | `BLOCKED` | Setorização manual necessária |
| `NEEDS_MODEL` | `ROUTED` | Alerta — confidence reduzida |
| `EMPTY` | `UNAVAILABLE` | Sem dados para route |
| `PARTIAL` | `ROUTED` | Alerta — confidence intermediária |
| `READY` | `ROUTED` | Confiança máxima |

### 2. `engine.py` (S06+) — Valuation Engine

Calcula fair value baseado nos inputs do router. Implementação futura — não executa em S03–S05.

```python
from src.valuation.engine import calculate, ValuationInputs

inputs = ValuationInputs(
    ticker="PETR4",
    sector="COMMODITY",
    method=ValuationMethod.DCF,
    financials=financial_data,
    price_data=price_data,
    macro=macro_context,
)
result = calculate(inputs)
```

### 3. `store.py` (S05) — Stores Canônicos

Quatro stores padronizados coexistem com o bridge existente:

```python
from src.valuation.store import ValuationStore, get_default_store

store = get_default_store()

# Ler resultado
result = store.get_result("ITUB4")

# Listar múltiplos
results = store.list_results(["ITUB4", "BBDC4", "PETR4"])

# Salvar novo resultado
store.save_result(result)

# Verificar cobertura
coverage = store.get_coverage("PETR4")
```

### 4. `models.py` — Tipos Compartilhados

```python
from src.valuation.models import (
    ValuationMethod,
    RoutingStatus,
    FinancialData,
    ValuationInputs,
    ValuationResult,
)

# ValuationMethod enum:
#   DCF, COSIF_DDM, DDM, NAV, RAB, EV_EBITDA, RELATIVES, SOTP

# RoutingStatus enum:
#   ROUTED, BLOCKED, UNAVAILABLE
```

---

## O que NÃO faz

- **Não calcula valuation em S03/S04/S05** — S03 é documentação, S04 é routing, S05 é store
- **Não cria mocks de fair value** — fair value vem do engine (S06+)
- **Não substitui o bridge existente** (`valuation_connector.py`) — coexiste
- **Não altera o banco de dados** — stores leem e escrevem em tabelas próprias
- **Não ingere dados CVM** — isso é responsabilidade de `src/context/` e `src/collectors/`
- **Não calcula valuation_method como input** — method é output do engine, não input do router

---

## Proibições Absolutas

```
╔══════════════════════════════════════════════════════════════════════╗
║  PROIBIDO: mock de fair_value, upside_pct ou valuation_method         ║
║  PROIBIDO: inventar preço justo sem dados reais do banco                ║
║  PROIBIDO: valuation_method hardcoded por ticker (use o router)        ║
║  PROIBIDO: sobrescrever fair_value existente sem validation           ║
║  PROIBIDO: substituir valuation_connector.py (M012/M013)               ║
║  PROIBIDO: calcular valuation antes de router + store implementados   ║
╚══════════════════════════════════════════════════════════════════════╝
```

O fluxo correto é: **router decide → engine calcula → store salva → dashboard lê.**

Nunca inverta: não calcule primeiro e depois decida o método.

---

## Regras Arquiteturais

| Regra | Descrição |
|-------|-----------|
| `valuation_method` é output | O engine decide o método final; o router sugere |
| `fundamental_quality_score` é output | Calculado pelo motor fundamentalista, não estimado |
| Fair values existentes preservados | Novos cálculos só substituem se confidence > existing |
| D077–D082 intactas | Valuation reconciliation policy não é modificada |
| Coexistência com bridge | Stores novos coexistcem com `valuation_connector.py` |

---

## Coexistência com M012/M013

```
valuation_store.py (S05 — novo)
  ├── Lê: b3_financials, asset_intelligence, cotahist
  └── Escreve: valuation_results, valuation_inputs, valuation_coverage

valuation_connector.py (M012/M013 — existente)
  └── Lê: outputs/Valuation_*.xlsx (old pipeline)

dashboard
  ├── Lê: valuation_store (S05) para dados novos
  └── Lê: valuation_connector (M012/M013) como fallback
```

---

## Dependências

| Dependência | Módulo | Uso |
|-------------|--------|-----|
| `b3_financials` | `src/integration/` | Dados financeiros |
| `cotahist` | `src/integration/` | Preço histórico |
| `asset_intelligence` | `src/integration/` | Setor, fair_value, market_price |
| `src/fundamentals/` | local | Classification de cobertura |
| `valuation_connector.py` | M012/M013 | Bridge legado (backup) |

---

## Roadmap de Implementação

| Slice | Módulo | Status |
|-------|--------|--------|
| S01 | audit script | ✅ Concluído |
| S02 | classify_coverage | ✅ Concluído |
| S02.5 | universo expansion | ✅ Concluído |
| **S03** | **arquitetura** | **📄 Este documento** |
| S04 | `router.py` | ⏳ Implementar |
| S05 | `store.py` | ⏳ Implementar |
| S06+ | `engine.py` | ⏳ Implementar |

---

## Para quem está implementando S04

O router precisa:
1. Ler coverage do `src/fundamentals/valuation_coverage.py`
2. Aplicar a matriz de routing por setor (ver `M014-ARCHITECTURE.md` seção 6)
3. Retornar `RouterDecision` com `routing_status` e `block_reason`
4. **Não calcular valuation** — só decidir o método e inputs necessários

## Para quem está implementando S05

Os stores precisam:
1. Coexistir com `valuation_connector.py` (não substituí-lo)
2. Preservar fair_values existentes em `asset_intelligence`
3. Usar `ValuationResult` dataclass de `models.py`
4. Ser lidos pelo dashboard sem breaking changes

---

*Implementado como parte do M014: Universal Sector Valuation Engine.*
*Proibido criar mocks ou inventar preço justo neste pacote.*