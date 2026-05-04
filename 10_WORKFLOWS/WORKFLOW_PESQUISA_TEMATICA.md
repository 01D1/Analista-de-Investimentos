---
title: Workflow — Pesquisa Temática
tags:
  - workflow
  - pesquisa
  - macro
  - setorial
aliases:
  - Pesquisa Temática
status: validado
---

# Workflow: Pesquisa Temática

> [!abstract] Use para investigar temas macro, setoriais ou de evento que impactam múltiplas empresas.

---

## Passo a Passo

### 1. Definir a Pergunta Central
- Qual é a hipótese investigativa?
- O que queremos saber ao final?
- Qual decisão este insight informa?

### 2. Identificar Fontes
- Macro: [[05_DATA_SOURCES/Banco_Central]], [[05_DATA_SOURCES/IBGE]], [[05_DATA_SOURCES/IPEA]]
- Setorial: reguladores (ANEEL, ANP, Susep), B3, CVM
- Empresas: RI, releases, Formulário de Referência

### 3. Levantar Dados
- [ ] Coletar dados quantitativos
- [ ] Coletar evidências qualitativas (discurso de management, notícias, regulação)
- [ ] Anotar data de cada fonte

### 4. Organizar Evidências
- Separar: fatos confirmados / dados ambíguos / rumores
- Criar nota em `08_RESEARCH/Temas_Especiais/` ou `08_RESEARCH/Macroeconomia/`

### 5. Mapear Hipóteses
- Quais hipóteses os dados suportam?
- Quais hipóteses os dados contradizem?
- O que ainda é incerto?

### 6. Testar Coerência
- As evidências são consistentes entre si?
- Há dados contraditórios? O que explica?
- Executar [[11_PROMPTS/PROMPT_AGENTE_REVISAO]] sobre a análise

### 7. Redigir Nota Temática
- Usar [[15_TEMPLATES/TEMPLATE_NOTA_PADRAO]]
- Salvar em `08_RESEARCH/Temas_Especiais/`

### 8. Vincular às Empresas Impactadas
- Quais empresas da cobertura são afetadas?
- Linkar nos arquivos de cada empresa
- Revisar se a tese de alguma empresa precisa atualização

---
*Última atualização: 2026-04-16*
