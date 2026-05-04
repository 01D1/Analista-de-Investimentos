---
title: Índice de Fontes de Dados
tags:
  - fontes
  - dados
  - índice
aliases:
  - Fontes de Dados
  - Data Sources
---

# Índice de Fontes de Dados

Inventário e manual de todas as fontes utilizadas no projeto.

---

## Fontes Brasileiras

| Fonte | Tipo de Dado | Confiabilidade | Parser |
|---|---|---|---|
| [[CVM]] | DFP, ITR, FRE, Formulário de Referência | Alta | `cvm_downloader.py` |
| [[B3]] | Cotações, eventos corporativos, proventos | Alta | — |
| [[RI_Empresas]] | Releases, apresentações, transcrições | Alta | `release_parser.py` |
| [[Banco_Central]] | Taxas (SELIC, câmbio), crédito | Alta | `bacen_sgds.py` |
| [[IBGE]] | PIB, inflação, dados setoriais | Alta | — |
| [[IPEA]] | Dados macro históricos | Alta | — |
| [[ANEEL]] | Regulação elétrica, tarifas | Alta (para utilities) | — |
| [[ANP]] | Dados de petróleo e gás | Alta (para O&G) | — |
| [[Susep]] | Dados de seguros | Alta (para seguradoras) | — |

## Fontes Internacionais

| Fonte | Tipo de Dado | Confiabilidade | Parser |
|---|---|---|---|
| [[SEC_EDGAR]] | 10-K, 10-Q (empresas US) | Alta | — |
| [[Yahoo_Finance]] | Cotações, múltiplos básicos | Média | — |
| [[Alpha_Vantage]] | Cotações, fundamentos via API | Média | — |
| [[FMP]] | Dados financeiros via API | Média-Alta | — |

---

## Como Avaliar uma Nova Fonte

| Critério | Perguntas |
|---|---|
| Tipo de dado | O que está disponível? Com que nível de detalhe? |
| Frequência | Diário, trimestral, anual? |
| Formato | XBRL, JSON, CSV, PDF, HTML? |
| Confiabilidade | É fonte primária ou agrega dados de outras? |
| Limitações | Histórico disponível? Atraso de publicação? |
| Acesso | Gratuito, API paga, scraping necessário? |
| Parser existente | Já temos código para esta fonte? |
| Problemas conhecidos | Qualidade inconsistente em algum período? |

---
*Última atualização: 2026-04-16*
