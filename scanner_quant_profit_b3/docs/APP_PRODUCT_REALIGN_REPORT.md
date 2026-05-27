# APP-REALIGN — Product Reset Report

**Data:** 2026-05-26  
**Status:** Executado

---

## 1. Diagnóstico de Produto — Páginas Anteriores vs. Novo Estado

### Navegação anterior (horizontal, 11 itens flat)

| Arquivo | Título anterior | Classificação | Decisão |
|---|---|---|---|
| `radar_ai.py` | Radar AI | Produto útil — intelligence hub por ativo | ✅ Mantido em Research |
| `inteligencia_ativo.py` | Construtor de Tese | Produto útil — deep-dive por ativo | ✅ Mantido em Research |
| `inteligencia_oportunidades.py` | Matriz de Sinais | Produto útil — cards de oportunidade | ✅ Mantido em Decisão como "Matriz de Sinais" |
| `radar_quant.py` | Núcleo Quantitativo | Técnica demais no subtítulo, útil no conteúdo | ✅ Renomeado "Scanner Quantitativo" |
| `valuation_engine.py` | Valuation Engine | Produto útil com poluição técnica | ✅ Corrigido — referências internas removidas |
| `valuation_coverage.py` | Cobertura de Valuation | Produto útil + técnica | ✅ Mantido em Fundamentos |
| `inteligencia_macro.py` | Macro Motor | Produto útil — charts BCB | ✅ Mantido em Research |
| `performance.py` | Mesa de Convicção | Produto útil — equity curve | ✅ Mantido em Decisão |
| `agendador.py` | Agent Runtime | Técnica demais para nav principal | ⬇️ Rebaixado para Técnico |
| `calendario.py` | Event Scheduler | Produto útil — calendário de eventos | ✅ Mantido em Research |
| `opcoes_monitoramento.py` | Opções Monitor | Produto útil | ✅ Mantido em Decisão |
| `inteligencia_watchlist.py` | (ausente) | Estava fora da navegação | ✅ Adicionado em Research |

### Novas páginas criadas

| Arquivo | Título | Função |
|---|---|---|
| `pages/radar_oportunidades.py` | Radar de Oportunidades | Home operacional — top sinais ranqueados |
| `pages/diagnostico_tecnico.py` | Diagnóstico Técnico | Página técnica — fontes, risco, snapshots |

---

## 2. Nova Navegação (sidebar agrupada)

### Grupo 🎯 Decisão
1. **Radar de Oportunidades** (`radar_oportunidades.py`) — home operacional; top sinais com score, direção, tier, próxima ação
2. **Scanner Quantitativo** (`radar_quant.py`) — scores por ativo com regime de mercado
3. **Opções & Derivativos** (`opcoes_monitoramento.py`) — posições abertas, sinais de saída, lifecycle
4. **Matriz de Sinais** (`inteligencia_oportunidades.py`) — opportunity cards com tier/direction/meta-score
5. **Conviction Desk** (`performance.py`) — equity curve, drawdown, Sharpe, exposure

### Grupo 🔭 Research
6. **Macro → B3** (`inteligencia_macro.py`) — Selic, PTAX, IPCA, CDS, PIB
7. **Radar AI** (`radar_ai.py`) — intelligence integrada por ativo
8. **Construtor de Tese** (`inteligencia_ativo.py`) — deep-dive single asset
9. **Empresas Monitoradas** (`inteligencia_watchlist.py`) — watchlist consolidada
10. **Calendário Econômico** (`calendario.py`) — macro events + earnings

### Grupo 📊 Fundamentos
11. **Valuation Hub** (`valuation_engine.py`) — preços justos + base fundamentalista
12. **Cobertura de Valuation** (`valuation_coverage.py`) — universo de 32 empresas

### Grupo ⚙️ Técnico
13. **Diagnóstico Técnico** (`diagnostico_tecnico.py`) — fontes, risco, snapshots, DB
14. **Pipeline & Agentes** (`agendador.py`) — agent runtime, pipeline graph

---

## 3. Valuation — Mudanças Aplicadas

### Tab order (novo)
1. Visão Geral
2. Base Fundamentalista
3. Qualidade Fundamental *(subiu — é produto)*
4. Contexto Macro *(subiu — é produto)*
5. Simulação dos Modelos *(desceu — mais técnico)*
6. **Valores Preliminares ⚠️** *(último — mais técnico, com disclaimer forte)*

### Referências técnicas removidas
- `Fonte: M015/M016` nos cards de preço justo → `Status: Auditado`
- `ingestion.db · CVM_CSV + B3_MARKET_DATA` → `Fontes: CVM / DFP · B3 Market Data`
- `write=False — nenhum valor foi salvo` → `Simulação validada — nenhum valor salvo`
- `source=M018_CONTROLLED · status=preliminary · approved_fair_value=NULL` → removido
- `asset_intelligence_snapshots não modificada` → removido
- `32 empresas · 9 preços justos preservados · 18 valores preliminares · 7 passaram na checagem · 47.621 registros financeiros` → `32 empresas · 9 preços justos auditados · 18 valores em validação · 7 passaram na checagem automática`

### Disclaimer reforçado na tab de valores preliminares
> "Estes valores são resultados do motor de valuation em processo de validação. Nenhum deles representa recomendação de investimento ou preço justo aprovado. Não utilizar como base de decisão sem validação fundamentalista completa."

---

## 4. Radar de Oportunidades — O que já existe vs. o que falta

### Dados disponíveis hoje
| Campo | Status | Fonte |
|---|---|---|
| Score de Convicção | ✅ Disponível | `asset_intelligence_snapshots.integrated_score` |
| Direção (BUY/WATCH/SELL) | ✅ Disponível | Derivado de `integrated_status` |
| Tier de Convicção | ✅ Disponível | Derivado de `integrated_status` |
| Sinal Técnico | ✅ Disponível | `technical_score_final` |
| Score Quant | ✅ Disponível | `quant_score` |
| Regime Macro | ✅ Disponível | `market_regime_engine.detect_regime()` |
| Tipo de Ativo | ✅ Derivado | Estimado de `signal_type` |
| Próxima Ação | ✅ Derivada | Score + direção + tier |

### Dados faltantes para oportunidade completa
| Campo | Status | O que falta |
|---|---|---|
| Gatilho de Entrada | ⚠️ Em desenvolvimento | Ponto técnico específico (suporte, resistência, evento) |
| Liquidez (ADV) | ⚠️ Em desenvolvimento | Volume diário médio de `cotahist_daily` |
| Assimetria Risco/Retorno | ⚠️ Em desenvolvimento | `expected_value_engine.py` → integração pendente |
| Valuation validado | ⚠️ Em validação | `valuation_results` aprovados = 0 ainda |

---

## 5. Poluição Técnica Removida

### Itens removidos da UI principal
- ❌ `source=M018_CONTROLLED` → movido para diagnóstico
- ❌ `valuation_financial_inputs` → linguagem simplificada
- ❌ `ingestion.db` (path) → substituído por "base financeira"
- ❌ `write=False` → substituído por "modo de simulação"
- ❌ `M015/M016`, `M018-S04` → referências de milestone removidas
- ❌ `asset_intelligence_snapshots não modificada` → removido (auditoria interna)

### Onde estão agora
→ Página **Diagnóstico Técnico** (`diagnostico_tecnico.py`) centraliza:
  - Caminhos de banco
  - Saúde das fontes com `source_name` e `status`
  - Snapshots de risco detalhados com VaR/ES
  - Regime de mercado com todos os campos técnicos
  - Tabela completa de `asset_intelligence_snapshots`

---

## 6. Renderização

### Substituições aplicadas
- `valuation_engine.py` Tab 1: manteve `st.html` com CSS inline completo — funcional
- `radar_quant.py`: manteve panels HTML — funcional
- `inteligencia_oportunidades.py`: cards HTML com CSS inline — funcional
- `diagnostico_tecnico.py`: tabela de ativos via `st.dataframe` (nativo Streamlit)

### Validação de síntaxe
- Todos os 14 arquivos de página compilam sem erro (`python -m py_compile`)

---

## 7. Validações Realizadas

- ✅ `python -m py_compile app.py pages/*.py` — sem erros
- ✅ 0 writes em banco
- ✅ 0 cálculo novo de fair_value
- ✅ 0 mocks criados
- ✅ Nomes de milestones removidos da UI
- ✅ HTML bruto: nenhuma nova ocorrência adicionada (existentes têm CSS inline completo)
- ✅ `inteligencia_watchlist.py` adicionada à navegação (estava ausente)
- ✅ Diagnóstico técnico criado como página isolada

---

## 8. O que ainda falta para sugerir oportunidades completas

1. **Integrar `expected_value_engine.py`** → adicionar assimetria ao `get_opportunities()`
2. **ADV de `cotahist_daily`** → adicionar volume diário médio ao payload de oportunidades
3. **Gatilho de entrada** → definir o que constitui um gatilho (nivel técnico, evento, data)
4. **Aprovar ao menos 1 valuation** → `valuation_results.approved = True` para ter preço justo real
5. **Integrar `institutional_meta_score.py`** com o sinal de assimetria no Radar de Oportunidades
