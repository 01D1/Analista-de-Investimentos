# App Page Audit Report — M018-App-Audit

**Data:** 2026-05-26  
**Escopo:** Todas as páginas Streamlit em `pages/` e navegação em `app.py`  
**Status:** ✅ Concluído — P0 e P1 corrigidos · P2 registrado

---

## Fase 1 — Inventário de Páginas

### Páginas no menu (app.py `_PAGES`)

| Página | Arquivo | No menu? | Compilou? |
|--------|---------|:--------:|:---------:|
| Radar AI | `pages/radar_ai.py` | ✅ | ✅ |
| Construtor de Tese | `pages/inteligencia_ativo.py` | ✅ | ✅ |
| Matriz de Sinais | `pages/inteligencia_oportunidades.py` | ✅ | ✅ |
| Núcleo Quantitativo | `pages/radar_quant.py` | ✅ | ✅ |
| Valuation Engine | `pages/valuation_engine.py` | ✅ | ✅ |
| Cobertura de Valuation | `pages/valuation_coverage.py` | ✅ | ✅ |
| Macro Motor | `pages/inteligencia_macro.py` | ✅ | ✅ |
| Mesa de Convicção | `pages/performance.py` | ✅ | ✅ |
| Agent Runtime | `pages/agendador.py` | ✅ | ✅ |
| Event Scheduler | `pages/calendario.py` | ✅ | ✅ |
| Opções Monitor | `pages/opcoes_monitoramento.py` | ✅ | ✅ |

### Páginas órfãs (existem em `pages/` mas NÃO estão no menu)

| Arquivo | Status |
|---------|--------|
| `pages/inteligencia_watchlist.py` | Órfão — não registrado em app.py |
| `pages/DEPRECATED/gerador_conteudo.py` | Deprecated — pasta DEPRECATED, não exposto |
| `pages/DEPRECATED/radar_ai_backup.py` | Deprecated — pasta DEPRECATED, não exposto |
| `pages/DEPRECATED/radar_ai_old.py` | Deprecated — pasta DEPRECATED, não exposto |

> `DEPRECATED/` não aparece na navegação — sem ação necessária.  
> `inteligencia_watchlist.py` é órfão ativo — mantido sem remoção por precaução.

---

## Fase 2 — Matriz de Diagnóstico

| Página | Menu | Import OK | Renderiza | Dados reais | JSON bruto | Nomes técnicos | Correção |
|--------|:----:|:---------:|:---------:|:-----------:|:----------:|:--------------:|:--------:|
| `radar_ai.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `inteligencia_ativo.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `inteligencia_oportunidades.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | **F6 sys.path** |
| `radar_quant.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ era | **F4,F8–F11** |
| `valuation_engine.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `valuation_coverage.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | **F7 st.warning** |
| `inteligencia_macro.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | **F5 page-header** |
| `performance.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `agendador.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `calendario.py` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — |
| `opcoes_monitoramento.py` | ✅ | ✅ | ⚠️ crash | ✅ | ❌ | ⚠️ era | **F1,F2,F3** |

---

## Fase 3 — Bugs Encontrados e Correções Aplicadas

### P0 — Críticos (crash em runtime)

#### F1 — `opcoes_monitoramento.py:252` · `pnl_label` NameError
**Problema:** Variável `pnl_label` usada antes de ser definida. A página crashava ao tentar renderizar o KPI de P&L quando havia posições abertas.  
**Correção:** Adicionada linha `pnl_label = f"R$ {total_pnl:+,.2f}"` antes do uso.  
**Arquivo:** `pages/opcoes_monitoramento.py`

#### F2 — `opcoes_monitoramento.py:362,421` · `' '.join(col_widths)` TypeError
**Problema:** `col_widths` é uma lista de floats. `str.join()` rejeita tipos não-string. A página crashava ao tentar renderizar a tabela de posições, emitindo `TypeError: sequence item 0: expected str instance, float found`.  
**Correção:** Substituído por `' '.join(f'{w}fr' for w in col_widths)`, gerando corretamente CSS grid como `0.7fr 1fr 1.5fr ...`.  
**Arquivo:** `pages/opcoes_monitoramento.py`

---

### P1 — Importantes (nomes técnicos / inconsistências de UI)

#### F3 — `opcoes_monitoramento.py` · footer com referências a milestones
**Problema:** Caption final exibia "S07 — Options Monitoring Dashboard · M007 intacto · source: S06 connector" com nomes de slices/milestones visíveis ao usuário.  
**Correção:** Substituído por "Monitoramento de opções · Dados reais do lifecycle · Sem ordens reais executadas".

#### F4 — `radar_quant.py` · subtítulo técnico "S01.5 Data Flow Integration Fix"
**Problema:** O subtítulo da página exibia "S01.5 Data Flow Integration Fix · real data · honest state" — nome interno de slice visível no produto.  
**Correção:** Substituído por "Diagnóstico do pipeline de dados — saúde das fontes, snapshots e risco".

#### F5 — `inteligencia_macro.py` · `st.title()` fora do padrão
**Problema:** Única página usando `st.title("Painel Macroeconômico")` em vez do `page-header` div adotado por todas as demais. Resultado visual inconsistente.  
**Correção:** Substituído por bloco `<div class="page-header">` com título "Macro Motor" e subtítulo descritivo.

#### F6 — `inteligencia_oportunidades.py` · `sys.path.insert(0, _PIPELINE_ROOT)` (colisão de módulos)
**Problema:** Adicionava `12_PYTHON/` em `sys.path[0]`, criando risco de resolver `src.ui.styles` e `src.quant.*` a partir do diretório errado se houver um `src/` em `12_PYTHON`. Todas as demais páginas *removem* o pipeline root.  
**Correção:** Alinhado com o padrão de `radar_ai.py` — remove `_PIPELINE_ROOT` em vez de adicioná-lo.

#### F7 — `valuation_coverage.py` · `st.warning()` fora do padrão
**Problema:** Único uso de `st.warning()` nativo em vez de `alert_block()` do design system da plataforma. Resultado visual inconsistente com as demais páginas.  
**Correção:** Substituído por `st.markdown(alert_block("warn", ...), unsafe_allow_html=True)`.

---

### P2 — Acabamento (labels em inglês / técnicos em seções visíveis)

#### F8–F11 — `radar_quant.py` · labels de seção em inglês/técnico
| Antes | Depois |
|-------|--------|
| "Asset Intelligence Snapshots" | "Inteligência por Ativo" |
| "Source Health Checks" | "Saúde das Fontes de Dados" |
| "Valuation Coverage" | "Cobertura de Valuation" |
| "Market Regime" | "Regime de Mercado" |
| "Risk Snapshots (N ativos)" | "Snapshots de Risco (N ativos)" |
| "Data Availability" | "Disponibilidade de Dados" |
| "VALUATIONS VÁLIDOS (PIPELINE)" | "VALUATIONS VÁLIDOS" |
| "BRIDGE + SQ DB" | "PIPELINE + DB" |
| "SQ DB ONLY (SEM VALUATION)" | "SEM VALUATION" |

---

## Fase 4 — Padrão Visual — Status por Página

| Página | Header/Hero | KPI Cards | Empty State | Dados reais | Sem JSON bruto | Labels PT |
|--------|:-----------:|:---------:|:-----------:|:-----------:|:--------------:|:---------:|
| Radar AI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Construtor de Tese | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Matriz de Sinais | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Núcleo Quantitativo | ✅ (corrigido) | ✅ | ✅ | ✅ | ✅ | ✅ (corrigido) |
| Valuation Engine | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cobertura de Valuation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Macro Motor | ✅ (corrigido) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mesa de Convicção | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agent Runtime | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Event Scheduler | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Opções Monitor | ✅ | ✅ (corrigido) | ✅ | ✅ | ✅ | ✅ (corrigido) |

---

## Fase 5 — Validações Finais

| Verificação | Resultado |
|-------------|-----------|
| `python -m py_compile app.py pages/*.py` | ✅ Todos OK |
| `pnl_label` definido antes do uso | ✅ Confirmado |
| `col_widths` join com `fr` units | ✅ Confirmado — 2 ocorrências corrigidas |
| `sys.path` em `inteligencia_oportunidades.py` | ✅ Alinhado com padrão |
| `st.title()` em `inteligencia_macro.py` | ✅ Substituído |
| Subtítulo técnico em `radar_quant.py` | ✅ Substituído |
| Banco de dados alterado | ✅ 0 arquivos `.db` do scanner_quant alterados |
| `asset_intelligence_snapshots` alterado | ✅ 0 escritas |
| Fair value novo calculado | ✅ 0 cálculos |
| Mocks criados | ✅ 0 |

---

## Arquivos Alterados

| Arquivo | Tipo de alteração |
|---------|-------------------|
| `pages/opcoes_monitoramento.py` | P0: pnl_label bug + col_widths TypeError + footer milestone labels |
| `pages/radar_quant.py` | P1: subtítulo técnico + P2: labels de seção em português |
| `pages/inteligencia_macro.py` | P1: st.title → page-header div |
| `pages/inteligencia_oportunidades.py` | P1: sys.path safety |
| `pages/valuation_coverage.py` | P1: st.warning → alert_block |

---

## Pendências P2 (não corrigidas — próxima etapa)

| Item | Página | Descrição |
|------|--------|-----------|
| Labels EN em opcoes KPIs | `opcoes_monitoramento.py` | "MONITORING", "ALERT", "PNL TOTAL" → português |
| `agendador.py` CSS no módulo | `agendador.py` | `st.markdown(PREMIUM_CSS)` fora de `main()` — redundante mas inofensivo |
| `calendario.py` CSS no módulo | `calendario.py` | Mesmo padrão do agendador |
| docstring técnica | `radar_quant.py:1` | `"""Radar Quant — Diagnostic Dashboard (S01.5)."""` — interno, não visível ao usuário |
| Seção "Market Regime" interna | `radar_quant.py` | Coluna "GOV STATUS" em inglês |
| `inteligencia_watchlist.py` | Órfão | Avaliar remover ou registrar no menu |

---

## Como Abrir o App

```bash
cd "scanner_quant_profit_b3"
streamlit run app.py
```

---

*Relatório gerado em 2026-05-26 · M018-App-Audit*
