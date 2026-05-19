---
title: Dashboard Institucional — Mesa Quant
tags: [dashboard, streamlit, ux, institucional]
---

# Dashboard Institucional — Mesa Quant

## Visão Geral

O Dashboard Institucional é a interface visual da plataforma Radar Macro. Organizado em 12 áreas temáticas com navegação por sidebar, filtros globais e componentes visuais padronizados.

**Não altera modelos, scores, ranking, backtests. Não executa ordens. CVM IN 598.**

---

## Como Iniciar

```bash
python -m streamlit run src/reports/quant_mesa_dashboard.py
```

---

## Estrutura de Navegação

| Ícone | Seção | Finalidade |
|---|---|---|
| 🏠 | Home / Visão Executiva | Status geral, alertas, próxima ação |
| 📡 | Radar de Ativos | Scanner quantitativo, sinais |
| 🧠 | Inteligência Integrada | Tese consolidada por ativo |
| 📈 | Análise Técnica Quant | Sinais técnicos por ativo |
| 📊 | Opções Inteligentes | Estratégias baseadas em opções |
| ⚖️ | Risco & Volatilidade | Risk Engine, VaR, volatilidade |
| 📋 | Paper Trading | Simulação de estratégias (12 subáreas) |
| 🗄️ | Dados & Auditoria | Saúde de fontes, reconciliação |
| ⚙️ | Pipeline Semanal | Status do pipeline end-to-end |
| 📰 | Relatórios Radar Macro | Revisão editorial, diff semanal |
| 🏛️ | Governança | Aprovações, bloqueios, fluxo |
| ⌨️ | Command Center | Referência de todos os comandos |
| 🔧 | Dados Brutos / Debug | Query manual, diagnóstico |

---

## Filtros Globais (Sidebar)

Todos os filtros são armazenados em `st.session_state` e reutilizados nas abas:

| Filtro | Descrição |
|---|---|
| Período | Último mês / 3m / 6m / 12m / YTD |
| Tickers | Lista separada por vírgula |
| Apenas bloqueados | Filtra somente itens em bloqueio de governança |
| Apenas com dados suficientes | Filtra itens com dados completos |

---

## Paleta de Status

| Cor | Status Mapeados |
|---|---|
| 🟢 Verde | OK, APPROVED, PASS, CONFIAVEL, SUCCESS |
| 🔵 Azul | APPROVED_FOR_INTERNAL_USE, RUNNING |
| ⚠️ Amarelo | WARNING, OBSERVATION, DADOS_INSUFICIENTES, PENDING_REVIEW |
| 🔴 Vermelho | BLOCKED, CRITICAL, FAILED, REJECTED, BLOCKED_* |
| ⬜ Cinza | SEM_DADOS, UNKNOWN, NOT_RUN, DRAFT, ARCHIVED |

---

## Componentes UI (`src/reports/ui_components.py`)

| Componente | Uso |
|---|---|
| `metric_card(title, value, subtitle, status)` | Card de KPI com cor de status |
| `status_badge(status)` | Badge HTML inline colorido |
| `governance_badge(status)` | Badge de governança |
| `risk_badge(status)` | Badge de risco |
| `data_quality_badge(status)` | Badge de qualidade de dados |
| `command_box(cmd, description, when, last_run)` | Bloco de comando operacional |
| `empty_state(message, command)` | Estado vazio com comando sugerido |
| `warning_panel(title, message)` | Painel de aviso padronizado |
| `executive_summary_box(text)` | Resumo executivo destacado |
| `dataframe_with_status(df, status_col)` | DataFrame com ícones de status |
| `section_header(title, subtitle)` | Cabeçalho de seção |

---

## Arquitetura de Arquivos

```
src/reports/
├── ui_components.py          ← Componentes visuais padronizados
├── quant_dashboard_data.py   ← Camada de dados (cache, queries seguras)
├── quant_mesa_dashboard.py   ← App Streamlit institucional (entry point)
├── editorial_workflow.py     ← Estado da revisão editorial
├── editorial_store.py        ← Persistência SQLite editorial
├── editorial_checklist.py    ← Checklist de 10 itens
├── weekly_pipeline_report.py ← Relatório do pipeline
└── weekly_report_diff.py     ← Diff semanal
```

---

## Performance

- Todas as funções de dados usam `@st.cache_data(ttl=300)` (5 minutos)
- Queries com limite de linhas (padrão 500)
- Tabelas ausentes retornam `pd.DataFrame()` sem erro
- Fallback para console quando Streamlit não disponível

---

## Limitações Conhecidas

- Seções Análise Técnica, Opções, Risco, Paper Trading mostram dados apenas se as tabelas correspondentes existirem no banco
- Filtro de período não está conectado às queries — é um estado de UI para desenvolvimento futuro
- Download de relatórios .md não implementado no browser (limitação Streamlit)

---

*Fase 49 — Mesa Quant Institucional. Uso interno. CVM IN 598.*
