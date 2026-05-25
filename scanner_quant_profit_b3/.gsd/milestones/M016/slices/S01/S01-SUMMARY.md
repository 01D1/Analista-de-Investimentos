# M016-S01 — SectorNormalizer
**Data:** 2026-05-25  
**Status:** ✅ CONCLUÍDA  
**Verdict:** ✅ PASS — 12/12 critérios de aceite

---

## Objetivos Cumpridos

Gap D097 resolvido: todos os 28 tickers `READY_FOR_MODEL_DESIGN` agora roteiam
para o método correto com `confidence=1.0`. Antes da S01: `FALLBACK → Relativos`
com `confidence=0.5` para 28/28 tickers.

---

## Arquivos Criados / Alterados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `src/valuation/sector_normalizer.py` | **CRIADO** | SectorNormalizer, normalize_sector(), SectorNormalizationResult |
| `src/valuation/tickers_config.py` | **CRIADO** | Loader do tickers.yaml com cache e fallback de path |
| `src/valuation/router.py` | **ALTERADO** | _normalize_sector_for_router() + integração antes do _SECTOR_METHOD_MAP lookup |
| `src/valuation/__init__.py` | **ALTERADO** | Exports de SectorNormalizer, normalize_sector, tickers_config |
| `tests/test_sector_normalizer.py` | **CRIADO** | 134 testes em 12 suites |

---

## Mapa Final: type/sector → canonical_sector

### Via `type` (tickers.yaml) — confidence=1.0

| type (yaml) | canonical_sector | Método Router |
|-------------|-----------------|---------------|
| `bank` | `BANK` | `COSIF/DDM` |
| `insurance` | `INSURANCE` | `DDM` |
| `reinsurance` | `INSURANCE` | `DDM` |
| `oil_gas` | `COMMODITY` | `DCF` |
| `mining` | `COMMODITY` | `DCF` |
| `utilities` | `UTILITY` | `DCF` |
| `industrial` | `INDUSTRY` | `DCF` |
| `healthcare` | `INDUSTRY` | `DCF` (D108) |
| `agro` | `INDUSTRY` | `DCF` (D108) |
| `education` | `INDUSTRY` | `DCF` (D108) |
| `retail` | `RETAIL` | `DCF` |
| `holding` | `HOLDING` | `NAV` |
| `real_estate` | `HOLDING` | `NAV` (D108) |
| `technology` | `TECH` | `DCF` |
| `telecom` | `TECH` | `DCF` |

### Via sector GICS (fallback) — confidence=0.8

| sector GICS | canonical_sector |
|-------------|-----------------|
| `financials` | `BANK` |
| `energy` | `COMMODITY` |
| `materials` | `COMMODITY` |
| `utilities` | `UTILITY` |
| `consumer_discretionary` | `RETAIL` |
| `consumer_staples` | `RETAIL` |
| `healthcare` | `INDUSTRY` |
| `communication` | `TECH` |
| `technology` | `TECH` |
| `industrials` | `INDUSTRY` |
| `real_estate` | `HOLDING` |

---

## Smoke Test — 28 Tickers READY

| Ticker | type | canonical | conf | Método Router | Blocked |
|--------|------|-----------|:----:|---------------|:-------:|
| ABCB4 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| AZZA3 | retail | RETAIL | 1.0 | DCF | ✅ No |
| BBAS3 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| BBDC4 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| BPAC11 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| BRSR6 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| EGIE3 | utilities | UTILITY | 1.0 | DCF | ✅ No |
| FLRY3 | healthcare | INDUSTRY | 1.0 | DCF | ✅ No |
| HYPE3 | healthcare | INDUSTRY | 1.0 | DCF | ✅ No |
| ITUB4 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| KLBN11 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |
| LREN3 | retail | RETAIL | 1.0 | DCF | ✅ No |
| MGLU3 | retail | RETAIL | 1.0 | DCF | ✅ No |
| PCAR3 | retail | RETAIL | 1.0 | DCF | ✅ No |
| PETR4 | oil_gas | COMMODITY | 1.0 | DCF | ✅ No |
| PRIO3 | oil_gas | COMMODITY | 1.0 | DCF | ✅ No |
| RADL3 | healthcare | INDUSTRY | 1.0 | DCF | ✅ No |
| RAIL3 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |
| RECV3 | oil_gas | COMMODITY | 1.0 | DCF | ✅ No |
| RENT3 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |
| SANB11 | bank | BANK | 1.0 | COSIF/DDM | ✅ No |
| SBSP3 | utilities | UTILITY | 1.0 | DCF | ✅ No |
| SUZB3 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |
| TAEE11 | utilities | UTILITY | 1.0 | DCF | ✅ No |
| VAMO3 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |
| VIVA3 | retail | RETAIL | 1.0 | DCF | ✅ No |
| VIVT3 | telecom | TECH | 1.0 | DCF | ✅ No |
| WEGE3 | industrial | INDUSTRY | 1.0 | DCF | ✅ No |

**confidence_avg = 1.0 | 28/28 routable | 0/28 fallback | 0/28 blocked**

### Distribuição por canonical_sector

| Sector | Qtd | Tickers |
|--------|----:|---------|
| BANK | 7 | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11 |
| COMMODITY | 3 | PETR4, PRIO3, RECV3 |
| INDUSTRY | 9 | FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3, WEGE3 |
| RETAIL | 5 | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 |
| TECH | 1 | VIVT3 |
| UTILITY | 3 | EGIE3, SBSP3, TAEE11 |

---

## Tickers em FALLBACK (0)

Nenhum dos 28 tickers READY caiu em `FALLBACK_MULTIPLES`.

**Antes da S01:** 28/28 tickers → FALLBACK/Relativos (confidence=0.5)  
**Após a S01:** 0/28 tickers → FALLBACK · 28/28 → chave canônica correta (confidence=1.0)

---

## Validações Executadas

| Validação | Resultado |
|-----------|:---------:|
| 28/28 tickers READY com canonical_sector correto | ✅ |
| 0/28 tickers em FALLBACK_MULTIPLES | ✅ |
| confidence_avg = 1.0 | ✅ |
| PETZ3 continua LEGACY_TICKER (router bloqueado) | ✅ |
| VALE3 tipo=mining → COMMODITY (normaliza, mas needs_data bloqueia router) | ✅ |
| AUAU3 tipo=retail → RETAIL (normaliza, mas needs_data bloqueia router) | ✅ |
| NTCO3 tipo=retail → RETAIL (normaliza, mas needs_data bloqueia router) | ✅ |
| 219/219 testes passando (85 antigos + 134 novos) | ✅ |
| 0 fair_values calculados | ✅ |
| 0 mocks criados | ✅ |
| 0 alterações banco | ✅ |
| 0 alterações opções/OOS/paper/scheduler | ✅ |

**12/12 critérios de aceite do roadmap M016-S01 atendidos.**

---

## Nota Técnica: RENT3

RENT3 (Localiza) tem `type=industrial` no `tickers.yaml` → `canonical=INDUSTRY`.
O campo `sector=consumer_discretionary` seria RETAIL via GICS fallback, mas o `type`
tem precedência (D099). RENT3 é empresa de mobilidade/locação de veículos,
corretamente classificada como industrial no roadmap M016 (bucket "DCF — Industrial").

---

## Autorização para M016-S02

**✅ S01 PASSED — M016-S02 (Bank Valuation Model) AUTORIZADO.**

Pré-condição necessária para S02:
- Verificar existência da tabela `b3_financials` no banco canônico (R01 do roadmap)
- Implementar `save_valuation_result()` (R06 do roadmap) antes de qualquer write

---

*S01 concluída em 2026-05-25.*  
*219 testes passando. 0 regressões. Gap D097 resolvido.*
