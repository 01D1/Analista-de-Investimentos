# M015-S04: Ajuste de Corporate Action — PETZ3 → AUAU3

**Data do ajuste:** 2026-05-24  
**Tipo:** Corporate Action — Merger  
**Evento:** Fusão Petz + Cobasi → União Pet Participações / Grupo Petz-Cobasi  
**Ticker extinto:** PETZ3  
**Ticker successor:** AUAU3  

---

## 1. Contexto

A fusão entre Petz e Cobasi foi confirmada e concluída. O ticker PETZ3 (Petz S.A.) foi
cancelado na B3 e substituído por AUAU3 (União Pet Participações / Grupo Petz-Cobasi).
Este ajuste registra o corporate action no universo de tickers e configurações do pipeline,
sem criar valuation novo e sem alterar fair_values existentes.

## 2. Classificação Adotada

| Campo | Valor |
|-------|-------|
| `PETZ3.status` | `LEGACY_TICKER` |
| `PETZ3.active` | `false` |
| `PETZ3.successor_ticker` | `AUAU3` |
| `AUAU3.active` | `true` |
| `corporate_action_type` | `merger` |
| `data_series_break` | `true` |
| `identity_confidence` | `HIGH` |

## 3. Impacto no Pipeline

| Componente | Ação |
|-----------|------|
| `config/tickers.yaml` | PETZ3 `active=false`, `status=LEGACY_TICKER`; AUAU3 adicionado como ativo |
| `config/corporate_identity.yaml` | Entrada AUAU3 criada (merger); PETZ3 adicionado em `ticker_validations` como `valid=false` |
| `config/cvm_codes.yaml` | PETZ3 mantido como legado; AUAU3 adicionado com `null` (CVM code pendente) |
| Database (`asset_intelligence_snapshots`) | Sem dados de PETZ3 — nenhuma atualização necessária (0 AI entries, 0 docs, 0 cotahist) |
| `ri_documents` | PETZ3: 0 docs (confirmado S02) — nada a mover |
| `cotahist_daily` | PETZ3: 0 registros — nenhuma série histórica a preservar |
| Fair values (BBAS3/ITUB4/PETR4/WEGE3) | **Intocados** |
| Valuation engine | **Não executado** |
| Mock data | **Nenhum criado** |

## 4. Regras de Ingestão a Partir de Agora

- **PETZ3**: não tentar ingestão, não coletar preços, não criar AI entry, não rotear valuation.
- **AUAU3**: usar para todas as coletas futuras — preços (yfinance `AUAU3.SA`), RI/CVM (código pendente), valuation.
- Qualquer referência a `PETZ3` em código deve ser tratada como ticker inválido (mesma lógica de RRRP3/ENAT3 pós-BRAV3).

## 5. Pendências (não bloqueantes para S04/M015)

| Item | Responsável | Prazo |
|------|-------------|-------|
| Confirmar data exata de início de negociação AUAU3 na B3 | Manual | Antes de M016 |
| Obter CVM code de AUAU3 (União Pet Participações) via `cvm_lookup` | Script `src/utils/cvm_lookup.py` | Antes de S02 de M016 |
| Verificar Fato Relevante CVM com data e relação de troca | Manual | Informativo |
| Ajustar `effective_date` e `series_break_date` em `corporate_identity.yaml` | Manual após confirmação | Antes de M016 |

## 6. Validações Realizadas

| Validação | Resultado |
|-----------|-----------|
| PETZ3 em `asset_intelligence_snapshots` | 0 rows — sem dados para alterar |
| PETZ3 em `ri_documents` | 0 docs — sem dados para mover |
| PETZ3 em `cotahist_daily` | 0 registros — sem série histórica |
| `tickers.yaml` atualizado | ✓ — PETZ3 `active=false`; AUAU3 adicionado |
| `corporate_identity.yaml` atualizado | ✓ — merger AUAU3 criado; PETZ3 marcado `valid=false` |
| `cvm_codes.yaml` atualizado | ✓ — PETZ3 mantido como legado; AUAU3 `null` pendente |
| Fair values preservados | ✓ |
| Nenhum valuation calculado | ✓ |
| Nenhum mock criado | ✓ |

---

*Registrado como ajuste de corporate action — M015-S04 — 2026-05-24*
