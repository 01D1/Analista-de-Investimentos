---
title: Projetos Python — Implementados
tags:
  - python
  - projetos
  - índice
aliases:
  - Projetos Python
  - Hub Python
---

# Projetos Python — Implementados

Projetos operacionais da plataforma de inteligência financeira. Cada módulo cobre uma camada distinta do fluxo de análise.

---

## Visão Geral do Ecossistema

```
News Hunter  ──────────────────────────────────────────────────────┐
(notícias, macro, agenda econômica)                                │
                                                                   ▼
Scanner Quant Profit B3 ──► dados em tempo real ──► contexto de mercado
(ações + opções, Profit RTD, B3 COTAHIST)                          │
                                                                   ▼
Pipeline Banco Completo ◄──────────────────────────────────────────┘
(valuation DCF, CVM, macro BCB, output Excel)
```

---

## Projetos

### 1. Scanner Quant Profit + B3
**Caminho:** `scanner_quant_profit_b3/`
**Nota:** [[scanner_quant_profit_b3/README_OBSIDIAN|Scanner Quant — Visão Geral]]

Coleta dados de mercado em tempo real via planilha Profit (RTD Excel) e histórico B3 COTAHIST. Scanneia ações e opções com ranking quantitativo. Grava em SQLite.

| Componente | Descrição |
|---|---|
| `profit_excel_collector.py` | Lê RTD em tempo real da planilha Profit |
| `b3_cotahist_collector.py` | Baixa e processa histórico diário da B3 |
| `realtime_profit_scanner.py` | Scanner contínuo com ranking de ativos |
| `combined_stock_options_scanner.py` | Cruza ações com suas opções |
| `scanner_quant.db` | Banco SQLite com dados históricos |

---

### 2. Pipeline Banco Completo
**Caminho:** `12_PYTHON/pipeline banco completo/`
**Nota:** [[12_PYTHON/pipeline banco completo/README|Pipeline Banco — README]]

Pipeline end-to-end de valuation fundamentalista para bancos brasileiros. Coleta CVM + macro BCB + mercado (yfinance), normaliza, projeta 10 anos e gera Excel com DCF/FCFE.

| Componente | Descrição |
|---|---|
| `coletor_cvm.py` | DFPs/ITRs via API pública CVM |
| `coletor_macro.py` | Selic, IPCA, DI via API BCB/SGS |
| `coletor_mercado.py` | Cotações e beta via yfinance |
| `valuation.py` | DCF, TIR, preço justo ON/PN |
| `escritor_excel.py` | Popula template .xlsx |

Bancos cobertos: BBDC4, BBAS3, ITUB4, SANB11, BPAC11

---

### 3. News Hunter
**Caminho:** `12_PYTHON/news_hunter/`
**Nota:** [[12_PYTHON/news_hunter/README|News Hunter — README]]

Coletor e classificador de notícias financeiras com geração automática de boletim diário. Monitora feeds RSS, classifica por categoria e relevância, envia via Telegram.

| Componente | Descrição |
|---|---|
| `crawler.py` | Coleta RSS e classifica notícias |
| `classificador.py` | Categorização por regras |
| `gerar_boletim.py` | Boletim diário em .md e .txt |
| `telegram_client.py` | Envio automático via Telegram |
| `calendario_economico.py` | Agenda de indicadores econômicos |

---

## Fluxo de Dados Entre Projetos

| De | Para | Dado |
|---|---|---|
| News Hunter | Pipeline Banco | Contexto macro (Selic, FOMC, CPI) |
| News Hunter | Scanner Quant | Alertas de eventos que movem mercado |
| Scanner Quant | Pipeline Banco | Preços e volatilidade em tempo real |
| Pipeline Banco | — | Valuation final em Excel |

---

## Referências

- [[12_PYTHON/MAPA_INTEGRACAO_ECOSISTEMA|Mapa de Integracao do Ecossistema Python]]
- [[12_PYTHON/README|Arquitetura Técnica Python]]
- [[12_PYTHON/PIPELINE|Data Pipeline — Fluxo Padrão]]
- [[10_WORKFLOWS/WORKFLOW_VALUATION_DO_ZERO|Workflow Valuation do Zero]]
- [[13_VALIDATION/REGRAS_DE_ALERTA|Regras de Alerta]]

---

*Última atualização: 2026-05-03*
