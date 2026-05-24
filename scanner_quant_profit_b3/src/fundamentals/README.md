# `src/fundamentals/` — Cobertura e Classificação de Ativos

**Propósito:** Classificar o estado de cobertura de dados fundamentalistas por ticker, sem criar mocks, sem calcular valuation, sem alterar o banco.

---

## O que faz

Este pacote fornece:

1. **`valuation_coverage.py`** — Classificador de status de cobertura por ticker
   - Baseado em dados reais lidos do banco (asset_intelligence, b3_financials, cotahist)
   - Retorna `CoverageStatus` enum: `READY`, `PARTIAL`, `EMPTY`, `NEEDS_MODEL`, `NEEDS_DATA`
   - Não calcula fair value, não inventa dados, não modifica banco

2. **`audit_*.py`** — Scripts de auditoria (S01)
   - Geram CSV de cobertura por ticker
   - Usados para diagnóstico operacional

---

## APIs Públicas

### `classify_coverage(ticker: str, db_path: str | Path | None = None) -> CoverageResult`

```python
from src.fundamentals.valuation_coverage import classify_coverage, CoverageStatus

result = classify_coverage("ITUB4")
# CoverageResult(ticker="ITUB4", status=CoverageStatus.READY, 
#                has_ai_entry=True, has_financials=True, ...)
```

### `CoverageStatus` enum

| Membro | Significado |
|--------|-------------|
| `READY` | 7/7 campos presentes — pronto para valuation |
| `PARTIAL` | Dados básicos ok, faltan metadados (method/fqs) |
| `NEEDS_MODEL` | Dados OK, falta valuation_method ou fundamental_quality_score |
| `NEEDS_DATA` | ri_docs=0 ou financials incompletos — ingestion necessária |
| `EMPTY` | Nenhuma AI entry — entrada de dados necessária |

### `CoverageResult` dataclass

```python
@dataclass
class CoverageResult:
    ticker: str
    status: CoverageStatus
    has_ai_entry: bool
    has_financials: bool
    has_sector: bool
    has_price: bool
    has_fair_value: bool
    has_method: bool
    has_fqs: bool
    gaps: list[str]  # ["ri_docs", "sector", "method", ...]
```

---

## O que NÃO faz

- **Não calcula fair value** — coverage é só classificação de estado
- **Não cria mocks** — apenas lê dados reais do banco
- **Não modifica o banco** — leitura only
- **Não implementa valuation model** — isso é responsabilidade de `src/valuation/`
- **Não calcula fundamental_quality_score** — isso é output do valuation engine (S06+)

---

## Proibições Absolutas

```
╔══════════════════════════════════════════════════════════════╗
║  PROIBIDO: mock de coverage status ou dados fundamentalistas  ║
║  PROIBIDO: inventar preenche gaps com valores falsos          ║
║  PROIBIDO: calcular valuation aqui                            ║
╚══════════════════════════════════════════════════════════════╝
```

Cobertura é um diagnostico de audit, não uma promessa de dados. Se `has_financials = False`, o ticker realmente não tem financials no banco. Confie no status.

---

## Dependências

- `src/integration/connectors/valuation_connector.py` — lê asset_intelligence (M012/M013)
- `src/integration/connectors/quant_connector.py` — lê cotahist
- `src/integration/connectors/options_connector.py` — NÃO usado aqui (escopo valuation ≠ opções)

---

## Arquivos

```
src/fundamentals/
├── __init__.py
├── valuation_coverage.py      # classificador + enum + CoverageResult
└── audit_tickers.py          # script de auditoria (S01)
```

---

## Relacionamento com M014 Slices

| Slice | Responsável | Output |
|-------|------------|--------|
| S01 | audit script | `coverage_audit_YYYYMMDD.csv` |
| S02 | classify_coverage | matriz operacional |
| S02.5 | universo expansion | `docs/universe_20260524.csv` |
| S03 | arquitetura (este doc) | `M014-ARCHITECTURE.md` |
| S04 | sector router | `src/valuation/router.py` |

---

*Proibido criar mocks ou inventar preço justo neste pacote.*