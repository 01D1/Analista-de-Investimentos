---
title: Guia de Uso — Mesa Quant
tags: [guia, dashboard, operacional]
---

# Guia de Uso — Mesa Quant

## Início Rápido

```bash
# Ativar ambiente
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS

# Iniciar dashboard
python -m streamlit run src/reports/quant_mesa_dashboard.py
```

Acesse: `http://localhost:8501`

---

## Fluxo Operacional Semanal

### 1. Rodar Pipeline Semanal

```bash
python -m src.scanners.run_weekly_pipeline \
    --start 2026-01-02 --end 2026-04-30 \
    --tickers PETR4 VALE3 ITUB4 BBAS3 \
    --save-db --reports
```

Navegar para: **⚙️ Pipeline Semanal** → verificar status de cada etapa.

### 2. Verificar Saúde dos Dados

Navegar para: **🗄️ Dados & Auditoria → Saúde das Fontes**

Todas as tabelas principais devem aparecer com status **OK** (verde).

### 3. Criar Revisão Editorial

```bash
python -m src.scanners.editorial_review \
    --latest-report --create-review --save-db
```

### 4. Preencher Checklist e Aprovar

Navegar para: **📰 Relatórios Radar Macro → Revisão Editorial**

Preencher o checklist de 10 itens. Em seguida:

```bash
# Aprovar para uso interno
python -m src.scanners.editorial_review \
    --latest-report --approve-internal \
    --reviewer SEU_NOME --save-db

# Aprovar para distribuição
python -m src.scanners.editorial_review \
    --latest-report --approve-distribution \
    --reviewer SEU_NOME --save-db
```

### 5. Comparar com Semana Anterior

```bash
python -m src.scanners.compare_weekly_reports --save-db --csv
```

Navegar para: **📰 Relatórios Radar Macro → Diff Semanal**

---

## Interpretando a Home

A **Home / Visão Executiva** mostra:

| Card | O que significa |
|---|---|
| Pipeline Semanal | Status do último pipeline executado |
| Status Editorial | Status da revisão editorial mais recente |
| Saúde dos Dados | Proporção de tabelas com dados |
| Bloqueios de Governança | Relatórios com bloqueio ativo |

A seção **Próxima Ação Sugerida** determina automaticamente o que fazer com base no estado atual da plataforma.

---

## Quando cada seção está vazia

| Seção | Condição de vazio | Ação |
|---|---|---|
| Radar de Ativos | Tabela `opportunity_signals` vazia | Rodar pipeline semanal |
| Inteligência Integrada | Tabela `thesis_versions` vazia | Rodar pipeline semanal |
| Análise Técnica | Tabela `technical_signals` ausente | Rodar módulo técnico |
| Opções Inteligentes | Tabela `options_signals` ausente | Rodar módulo de opções |
| Risco & Volatilidade | Tabela `risk_metrics` ausente | Rodar Risk Engine |
| Paper Trading | Tabela `paper_trading_runs` ausente | Rodar paper trading |

---

## Filtros Globais

Os filtros na sidebar afetam as abas que os suportam:

- **Tickers**: filtra tabelas com coluna `ticker`
- **Apenas bloqueados**: exibe somente itens com status BLOCKED_*
- **Apenas com dados suficientes**: oculta itens SEM_DADOS

> Nota: O filtro de **Período** ainda não está conectado às queries — é planejado para fase futura.

---

## Resolução de Bloqueios de Governança

Se aparecerem bloqueios na Home ou em **🏛️ Governança**:

1. Verificar qual relatório está bloqueado (coluna `report_id`)
2. Identificar o tipo de bloqueio (`BLOCKED_DATA_QUALITY` ou `BLOCKED_GOVERNANCE`)
3. Para bloqueio de dados — verificar **🗄️ Dados & Auditoria → Saúde das Fontes**
4. Após correção, usar override:

```bash
python -m src.scanners.editorial_review \
    --latest-report --approve-internal \
    --override-data-warning --reviewer SEU_NOME --save-db
```

---

## Atalhos de Teclado (Streamlit)

| Ação | Atalho |
|---|---|
| Recarregar app | `R` |
| Parar execução | `Esc` |
| Abrir/fechar sidebar | `[` |

---

*Guia de Uso — Mesa Quant Institucional. Uso interno. CVM IN 598.*
