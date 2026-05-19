---
title: Command Center — Mesa Quant
tags: [comandos, operacional, reference]
---

# Command Center — Mesa Quant

Referência completa de todos os comandos operacionais da plataforma.

> Acesse no dashboard: **⌨️ Command Center**

---

## Pipeline & Ingestão

### Pipeline Semanal Completo

**Quando usar:** Todo início de semana ou quando dados novos estão disponíveis.

```bash
python -m src.scanners.run_weekly_pipeline \
    --start 2026-01-02 \
    --end 2026-04-30 \
    --tickers PETR4 VALE3 ITUB4 BBAS3 \
    --save-db \
    --reports
```

**O que faz:** Ingestão (CVM, B3, BCB) → Valuation (DCF, Múltiplos) → Intelligence Layer → Relatório Radar Macro.

---

### Ingestão Simples (sem relatório)

```bash
python -m src.scanners.run_weekly_pipeline \
    --start 2026-01-02 \
    --end 2026-04-30 \
    --tickers PETR4 VALE3 \
    --save-db
```

---

## Editorial

### Criar Revisão Editorial

**Quando usar:** Após pipeline semanal concluído com sucesso.

```bash
python -m src.scanners.editorial_review \
    --latest-report \
    --create-review \
    --save-db
```

---

### Aprovar para Uso Interno

**Quando usar:** Após checklist de 10 itens preenchido.

```bash
python -m src.scanners.editorial_review \
    --latest-report \
    --approve-internal \
    --reviewer SEU_NOME \
    --save-db
```

---

### Aprovar para Distribuição

**Quando usar:** Após aprovação interna e validação final da equipe.

```bash
python -m src.scanners.editorial_review \
    --latest-report \
    --approve-distribution \
    --reviewer SEU_NOME \
    --save-db
```

---

### Aprovar com Override de Dados

**Quando usar:** Bloqueio por `BLOCKED_DATA_QUALITY` quando dados foram validados manualmente.

```bash
python -m src.scanners.editorial_review \
    --latest-report \
    --approve-internal \
    --override-data-warning \
    --reviewer SEU_NOME \
    --save-db
```

---

## Relatórios

### Gerar Relatório do Pipeline

```bash
python -m src.scanners.generate_weekly_pipeline_report
```

### Comparação Semanal (Diff)

**Quando usar:** Após dois relatórios semanais consecutivos gerados.

```bash
python -m src.scanners.compare_weekly_reports --save-db --csv
```

### Gerar Relatório Editorial

```bash
python -m src.scanners.generate_editorial_review_report
```

---

## Dashboard

### Iniciar Mesa Quant

```bash
python -m streamlit run src/reports/quant_mesa_dashboard.py
```

### Iniciar com porta específica

```bash
python -m streamlit run src/reports/quant_mesa_dashboard.py --server.port 8502
```

---

## Testes

### Rodar suíte completa

```bash
python -m pytest -q
```

### Rodar testes de UI

```bash
python -m pytest tests/test_ui_components.py -v
```

### Rodar testes do Command Center / data layer

```bash
python -m pytest tests/test_dashboard_command_center.py -v
```

### Rodar testes do dashboard editorial

```bash
python -m pytest tests/test_dashboard_data.py -v
```

---

## Tabela de Referência Rápida

| Situação | Comando |
|---|---|
| Nenhum dado no banco | `run_weekly_pipeline --save-db --reports` |
| Pipeline executado, sem revisão | `editorial_review --create-review` |
| Revisão criada, sem aprovação | `editorial_review --approve-internal` |
| Bloqueio de dados | `editorial_review --approve-internal --override-data-warning` |
| Aprovado internamente | `editorial_review --approve-distribution` |
| Semana já gerada, comparar | `compare_weekly_reports --save-db --csv` |
| Verificar pipeline | Dashboard → ⚙️ Pipeline Semanal |
| Verificar dados | Dashboard → 🗄️ Dados & Auditoria |

---

*Command Center — Mesa Quant. Uso interno. Não constitui recomendação de investimento. CVM IN 598.*
