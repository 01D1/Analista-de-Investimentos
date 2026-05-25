# M015-S03.5: Corporate Actions / Ticker Alias Patch — Relatório Final

**Data:** 2026-05-24  
**Status:** ✅ CONCLUÍDO  
**Autoriza S04:** Sim  

---

## 1. Data Oficial Confirmada (B3)

| Evento | Data |
|--------|------|
| Fusão Petz + Cobasi concluída | **2026-01-02** |
| AUAU3 início de negociação B3 | **2026-01-05** |
| Crédito das novas ações | 2026-01-07 |
| Pagamento em dinheiro (R$ 0,7109/ação) | até 2026-01-23 |
| Última cotação PETZ3 | 2026-01-02 (cotahist confirma) |

> Fontes: [InforMoney](https://www.infomoney.com.br/mercados/uniao-pet-estreia-na-b3-com-ticker-auau3-apos-conclusao-da-fusao-entre-petz-e-cobasi/), [Exame Invest](https://exame.com/invest/mercados/auau3-fusao-entre-petz-e-cobasi-estreia-hoje-na-b3-o-que-muda/), [SBT News](https://sbtnews.sbt.com.br/noticia/economia/auau-3-fusao-entre-petz-e-cobasi-estreia-nesta-segunda-feira-05-na-b3-o-que-muda), [MixVale](https://www.mixvale.com.br/2026/01/05/fusao-petz-e-cobasi-gera-uniao-pet-que-estreia-codigo-auau3-na-bolsa-brasileira-nesta-segunda/)

---

## 2. O Que Foi Encontrado

| Ticker | Estado antes da S03.5 | Problema |
|--------|----------------------|---------|
| PETZ3 | AI entry com `s03_router_eligible=true`, `coverage_status=HAS_SECTOR_NO_RI` | Errado — ticker extinto, não deve ser roteado |
| AUAU3 | AI entry com `sector=UNKNOWN`, sem marcação de successor | Incompleto — setor errado, predecessor não registrado |

---

## 3. O Que Foi Criado

### 3a. `config/ticker_aliases.yaml` (novo)

Arquivo canônico para corporate actions / aliases de ticker. Contém:
- `legacy_ticker: PETZ3`
- `current_ticker: AUAU3`
- `effective_date: 2026-01-05`
- `use_for_history: PETZ3` / `use_for_current: AUAU3`

Padrão extensível: cada novo corporate action é um bloco no YAML.

### 3b. `src/utils/ticker_aliases.py` (novo)

Interface Python com:
```python
from src.utils.ticker_aliases import is_legacy_ticker, resolve_ticker, LEGACY_TICKERS

is_legacy_ticker("PETZ3")  # → True
resolve_ticker("PETZ3")    # → "AUAU3"
resolve_ticker("VALE3")    # → "VALE3"
LEGACY_TICKERS             # → frozenset({"PETZ3"})
```

---

## 4. O Que Foi Alterado

### Código

| Arquivo | Mudança |
|---------|---------|
| `src/valuation/valuation_coverage.py` | `CoverageStatus.LEGACY_TICKER = "legacy_ticker"` adicionado |
| `src/valuation/router.py` | `"legacy_ticker"` em `_BLOCK_STATUSES`; block_reason específico no corpo |
| `scripts/m015_s03_ai_entry_population.py` | Guard early-exit para `LEGACY_TICKERS`; `skipped_legacy_ticker` em stats |

### Configuração

| Arquivo | Mudança |
|---------|---------|
| `12_PYTHON/config/tickers.yaml` | `event_date` corrigido: `2026-01-05` |
| `12_PYTHON/config/corporate_identity.yaml` | `effective_date=2026-01-05`, `series_break_date=2026-01-05`, `delisted_date=2026-01-02` |

### Banco de dados (scanner_quant.db)

| Ticker | Ação | Campos |
|--------|------|--------|
| PETZ3 (id=460) | UPDATE metadata_json | `s035_legacy_ticker=true`, `s035_coverage_status=legacy_ticker`, `s035_router_eligible=false`, `s035_successor_ticker=AUAU3` |
| AUAU3 (id=432) | UPDATE sector + metadata_json | `sector=consumer_discretionary` (era UNKNOWN), `s035_legacy_predecessor=PETZ3`, `s035_router_eligible=true` |

---

## 5. Impacto na S04 (Coverage Audit)

| Ticker | Antes da S03.5 | Depois da S03.5 |
|--------|---------------|----------------|
| PETZ3 | Aparecia como ativo com HAS_SECTOR_NO_RI | Marcado LEGACY_TICKER — não conta como gap ativo |
| AUAU3 | UNKNOWN sector, predecessor não rastreado | `consumer_discretionary`, `HAS_SECTOR_NO_RI`, predecessor=PETZ3 |

**PETZ3 não deve mais aparecer como NEEDS_CVM_DATA ativo na S04.**  
**AUAU3 é o ticker a monitorar para cobertura futura (RI/CVM).**

---

## 6. Validações

| Validação | Status |
|-----------|--------|
| PETZ3 `legacy_ticker=true` no DB | ✅ |
| PETZ3 `router_eligible=false` no DB | ✅ |
| AUAU3 `sector=consumer_discretionary` | ✅ |
| AUAU3 único (sem duplicatas) | ✅ |
| fair_values BBAS3/ITUB4/PETR4/WEGE3 preservados | ✅ |
| Nenhum valuation calculado | ✅ |
| Nenhum mock criado | ✅ |
| Router bloqueia `coverage_status=legacy_ticker` | ✅ código |

---

## 7. Autorização para S04

✅ **S04 AUTORIZADO** — Coverage Audit Before/After pode ser executado.

```
python scripts/coverage_audit.py
```

---

*Gerado por M015-S03.5 em 2026-05-24*
