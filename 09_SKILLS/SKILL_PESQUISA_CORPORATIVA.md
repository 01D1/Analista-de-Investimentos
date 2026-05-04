---
title: "Skill: Pesquisa Corporativa Profunda"
tags:
  - skill
  - pesquisa
  - empresa
aliases:
  - Pesquisa Corporativa
status: validado
---

# Skill: Pesquisa Corporativa Profunda

## Objetivo

Levantar um retrato completo de uma empresa, suficiente para fundamentar qualquer análise financeira, tese de investimento ou cobertura contínua.

---

## Quando Usar

- Ao iniciar cobertura de nova empresa
- Ao revisar tese após mudança relevante de negócio
- Ao comparar empresa com peers
- Antes de construir modelo financeiro

---

## Entradas Necessárias

- Ticker / nome da empresa
- Acesso a: [[05_DATA_SOURCES/CVM]], [[05_DATA_SOURCES/RI_Empresas]]
- Documentos: Formulário de Referência, DFP mais recente, apresentações institucionais

---

## Processo

### 1. Identidade da Empresa

- [ ] Razão social, ticker, CNPJ, setor B3
- [ ] Fundação, histórico de constituição
- [ ] Listagem e estrutura de ações (ON, PN, Unit)
- [ ] Controle acionário e grupo econômico

### 2. Modelo de Negócio

- [ ] O que a empresa faz? Como ganha dinheiro?
- [ ] Segmentos operacionais
- [ ] Mix de receita por produto / serviço / canal
- [ ] Geografias de atuação

### 3. Drivers de Receita

- [ ] Quais são os 3–5 drivers principais de crescimento?
- [ ] Pricing power: a empresa tem poder de precificar?
- [ ] Demanda: cíclica, defensiva, secular?
- [ ] Sazonalidade

### 4. Estrutura de Custos

- [ ] Principais linhas de custo
- [ ] Custos fixos vs variáveis
- [ ] Margem bruta e dinâmica de EBITDA
- [ ] Alavancagem operacional

### 5. Vantagens Competitivas

- [ ] Quais são os moats?
- [ ] Escalabilidade do modelo
- [ ] Barreiras de entrada
- [ ] Network effects / switching costs

### 6. Riscos Estruturais

- [ ] Regulatório
- [ ] Competitivo
- [ ] Macroeconômico
- [ ] Operacional
- [ ] De gestão / governança

### 7. Governança

- [ ] Estrutura de controle (controlador, free float)
- [ ] Conselho: independência, composição
- [ ] Histórico de capital allocation
- [ ] Relacionamento com minoritários
- [ ] Remuneração variável da gestão

### 8. Estratégia e Guidance

- [ ] Plano estratégico atual
- [ ] Guidance divulgado (crescimento, margem, capex)
- [ ] Histórico de entrega vs guidance

### 9. M&A e Eventos Corporativos

- [ ] Aquisições históricas relevantes
- [ ] Desinvestimentos
- [ ] Incorporações, cisões, reorganizações

### 10. Lacunas Identificadas

- [ ] O que ainda não sabemos?
- [ ] Quais hipóteses precisam ser testadas?

---

## Saídas Esperadas

- Nota preenchida: [[15_TEMPLATES/TEMPLATE_COBERTURA_EMPRESA]]
- Tags: `#empresa/[TICKER]`, `#status/em-andamento`
- Links criados para setor correspondente em [[04_SECTORS]]

---

## Erros Comuns

> [!warning] Armadilhas frequentes

- Confundir receita bruta com receita líquida ao comparar empresas
- Ignorar segmentos menores que impactam a tese (ex: um segmento que cresce ou deteriora rápido)
- Aceitar o "modelo de negócio" conforme a empresa descreve, sem questionar
- Não separar o que é vantagem competitiva real do que é conjuntura favorável

---

## Critérios de Qualidade

- [ ] Ao menos 3 fontes primárias consultadas
- [ ] Modelo de negócio descrito em 3 linhas sem depender de jargão
- [ ] Drivers de receita ranqueados por relevância
- [ ] Riscos com estimativa de materialidade
- [ ] Lacunas explicitamente listadas

---

## Scripts Relacionados

- `12_PYTHON/src/ingestion/cvm_downloader.py`
- `12_PYTHON/src/parsers/formulario_referencia_parser.py`

---

## Notas Complementares

Ver também: [[SKILL_PESQUISA_DE_CONCORRENCIA]], [[SKILL_PESQUISA_SETORIAL]]

---
*Última atualização: 2026-04-16*
