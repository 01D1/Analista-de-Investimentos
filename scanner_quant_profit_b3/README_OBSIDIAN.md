---
title: Scanner Quant Profit + B3
tags:
  - python
  - scanner
  - mercado
  - tempo-real
  - opcoes
  - b3
aliases:
  - Scanner Quant
  - scanner_quant_profit_b3
---

# Scanner Quant Profit + B3

Scanner quantitativo de ações e opções com dados em tempo real via Profit (RTD Excel) e histórico da B3 COTAHIST.

---

## Posição no Ecossistema

Este projeto é a **camada de dados de mercado em tempo real** da plataforma.

```
Este projeto
     │
     ├──► [[12_PYTHON/news_hunter/README|News Hunter]]        ← contexto de notícias
     │
     └──► [[12_PYTHON/pipeline banco completo/README|Pipeline Banco]]  ← dados para valuation
```

Veja o mapa completo em: [[12_PYTHON/Projetos Implementados|Projetos Python — Implementados]]

---

## O que faz

| Módulo | Função |
|---|---|
| `profit_excel_collector.py` | Lê cotações em tempo real da planilha Profit via RTD |
| `b3_cotahist_collector.py` | Baixa e processa histórico diário da B3 |
| `b3_cotahist_downloader.py` | Download do arquivo COTAHIST (ZIP → TXT) |
| `parse_cotahist.py` | Parser do layout B3 para DataFrame |
| `realtime_profit_scanner.py` | Scanner contínuo com ranking de ativos |
| `stock_scanner.py` | Scanner de ações com filtros quantitativos |
| `option_scanner.py` | Scanner de opções com Greeks e liquidez |
| `combined_stock_options_scanner.py` | Cruza ações com opções correspondentes |
| `init_db.py` | Inicializa banco SQLite |

---

## Comandos Rápidos

```powershell
# Instalar dependências e inicializar banco
pip install -r requirements.txt
python -m src.db.init_db

# Scanner em tempo real (top 10 ativos)
python -m src.scanners.realtime_profit_scanner --once --top 10

# Modo demo (fora do pregão)
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo

# Baixar COTAHIST B3
python -m src.collectors.b3_cotahist_collector --year 2026

# Scanner de opções
python -m src.scanners.b3_options_scanner --min-volume 100000 --top 30

# Ranking cruzado ações + opções
python -m src.scanners.combined_stock_options_scanner
```

---

## Arquivos de Dados

| Arquivo | Descrição |
|---|---|
| `data/realtime/RTD PROFIT.xlsx` | Planilha Profit com RTD (manter aberta durante pregão) |
| `data/raw/COTAHIST_A*.ZIP` | Histórico anual B3 (download automático) |
| `data/database/scanner_quant.db` | Banco SQLite com dados processados |
| `data/reports/ranking_*.csv` | Rankings exportados |

---

## Projetos Relacionados

- [[12_PYTHON/Projetos Implementados|Hub — Projetos Python Implementados]]
- [[12_PYTHON/pipeline banco completo/README|Pipeline Banco Completo]] — usa preços de mercado que este projeto coleta
- [[12_PYTHON/news_hunter/README|News Hunter]] — notícias que explicam movimentos captados pelo scanner

---

*Última atualização: 2026-05-03*
