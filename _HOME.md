---
title: HOME — Central do Analista
tags:
  - hub
  - navegacao
  - home
aliases:
  - Home
  - Central
  - Início
cssclasses:
  - wide
---

# HOME — Central do Analista

> Porta de entrada única do vault. Conecta as 26 pastas em 5 camadas + a arquitetura do sistema (`INTELLIGENCE_SYSTEM`).
> Toda navegação começa aqui.

---

## Status atual (abr/2026)

- **Fase 1 — Fundação:** ✅ estrutura criada, pipeline CVM funcionando para 12 bancos brasileiros
- **Fase 2 — Valuation bancário:** ✅ 5 modelos DDM Gordon 2-estágios (ITUB4, BBAS3, BBDC4, SANB11, BPAC11) + comparativa
- **Fase 3 — Em andamento:** INTR4 (digital), ITSA4 (SOTP), bancos médios (BRSR6, BMGB4, BPAN4, PINE4, ABCB4)

Atalhos do que está vivo agora:

- 📊 [[07_VALUATION/BANCOS_GRANDES/INDEX|Valuation Bancos Grandes — 5 modelos + comparativa]]
- 📝 [[20_LEARNING_LOG/INDEX|Learning Log — aprendizados do projeto]]
- 🧭 [[00_META/INTELLIGENCE_SYSTEM/README|Intelligence System — arquitetura em 4 motores]]

---

## Arquitetura do Sistema (4 motores)

O [[00_META/INTELLIGENCE_SYSTEM/README|Intelligence System]] define o contrato entre os componentes. Cada motor tem responsabilidade isolada.

| Motor | Manifesto | Onde vive no vault |
|---|---|---|
| 🔧 **Financial Engine** | [[00_META/INTELLIGENCE_SYSTEM/FINANCIAL_ENGINE]] | [[12_PYTHON]] · [[03_COMPANIES]] · [[06_MODELS]] · [[07_VALUATION]] |
| 📰 **Macro News Engine** | [[00_META/INTELLIGENCE_SYSTEM/MACRO_NEWS_ENGINE]] | _(a construir)_ — futuro `26_NEWS/` |
| 🧠 **Intelligence Layer** | [[00_META/INTELLIGENCE_SYSTEM/INTELLIGENCE_LAYER]] | [[04_GOVERNANCA]] · [[08_RESEARCH]] · [[17_MEMORY]] · [[18_DECISIONS]] · [[20_LEARNING_LOG]] |
| ✍️ **Content Engine** | [[00_META/INTELLIGENCE_SYSTEM/CONTENT_ENGINE]] | [[14_OUTPUTS]] · [[15_TEMPLATES]] · [[22_DASHBOARDS]] |

Ver também: [[00_META/INTELLIGENCE_SYSTEM/ARCHITECTURE|ARCHITECTURE]] · [[00_META/INTELLIGENCE_SYSTEM/RULES|Regras]] · [[00_META/INTELLIGENCE_SYSTEM/GOVERNANCE|Governance]] · [[00_META/INTELLIGENCE_SYSTEM/THESIS_TEMPLATE|Thesis Template]] · [[00_META/INTELLIGENCE_SYSTEM/VALIDATION|Validation]] · [[00_META/INTELLIGENCE_SYSTEM/INSIGHTS|Insights]] · [[00_META/INTELLIGENCE_SYSTEM/PROMPT_CLAUDE|Prompt Claude]]

---

## Camada 0 — Meta / Sistema Operacional

Identidade, governança e operação do vault.

- [[00_META/README_GERAL|00_META/README_GERAL]] — introdução e regras gerais
- [[00_META/MISSAO|Missão]]
- [[00_META/PRINCIPIOS|Princípios]]
- [[00_META/ROADMAP|Roadmap]]
- [[00_META/ARQUITETURA_DO_CONHECIMENTO|Arquitetura do Conhecimento]]
- [[00_META/COMO_USAR_O_VAULT|Como Usar o Vault]]
- [[00_META/INTELLIGENCE_SYSTEM/README|🆕 Intelligence System (manifesto)]]
- [[01_OPERATING_SYSTEM/SISTEMA_DE_NOTAS|Sistema de Notas]]
- [[01_OPERATING_SYSTEM/PADRAO_DE_NOMENCLATURA|Padrão de Nomenclatura]]
- [[01_OPERATING_SYSTEM/PROTOCOLO_DE_ATUALIZACAO|Protocolo de Atualização]]
- [[01_OPERATING_SYSTEM/RITUAL_DE_REVISAO_SEMANAL|Ritual de Revisão Semanal]]
- [[01_OPERATING_SYSTEM/CRITERIOS_DE_QUALIDADE|Critérios de Qualidade]]
- [[24_SECURITY]] · [[23_DOCS]] · [[25_ARCHIVE]]

---

## Camada 1 — Conhecimento

Onde o saber é organizado.

- [[04_SECTORS]] — inteligência setorial _(a popular)_
- [[05_DATA_SOURCES]] — inventário de fontes
- [[16_GLOSSARY]] — vocabulário comum
- [[17_MEMORY/INDEX|17_MEMORY/INDEX]] — heurísticas e padrões aprendidos
	- [[17_MEMORY/Padroes_identificados|Padrões Identificados]]
	- [[17_MEMORY/Heuristicas_uteis|Heurísticas Úteis]]
	- [[17_MEMORY/Falhas_recorrentes|Falhas Recorrentes]]

---

## Camada 2 — Dados

Ingestão, parsing, ETL e validação.

- [[12_PYTHON]] — toda a engrenagem quantitativa
	- `12_PYTHON/src/` — ingestão, normalização, parsers
	- `12_PYTHON/notebooks/` — scripts de construção (incluindo os builders dos 5 bancos)
	- `12_PYTHON/data/` — raw, processed
- [[13_VALIDATION/INDEX|13_VALIDATION/INDEX]] — regras de qualidade
	- [[13_VALIDATION/CHECKLIST_EXTRACAO|Checklist Extração]]
	- [[13_VALIDATION/CHECKLIST_RECONCILIACAO|Checklist Reconciliação]]
	- [[13_VALIDATION/CHECKLIST_MODELAGEM|Checklist Modelagem]]
	- [[13_VALIDATION/CHECKLIST_VALUATION|Checklist Valuation]]
	- [[13_VALIDATION/REGRAS_DE_ALERTA|Regras de Alerta]]

---

## Camada 3 — Modelagem

Onde dados viram modelos analíticos.

- [[03_COMPANIES/INDEX|03_COMPANIES/INDEX]] — modelos por empresa
	- Bancos cobertos: [[03_COMPANIES/ITUB4/DADOS_HISTORICOS|ITUB4]] · [[03_COMPANIES/BBAS3/DADOS_HISTORICOS|BBAS3]] · [[03_COMPANIES/BBDC4/DADOS_HISTORICOS|BBDC4]] · [[03_COMPANIES/SANB11/DADOS_HISTORICOS|SANB11]] · [[03_COMPANIES/BPAC11/DADOS_HISTORICOS|BPAC11]] · [[03_COMPANIES/INTR4/DADOS_HISTORICOS|INTR4]] · [[03_COMPANIES/ITSA4/DADOS_HISTORICOS|ITSA4]] · [[03_COMPANIES/ABCB4/DADOS_HISTORICOS|ABCB4]] · [[03_COMPANIES/BMGB4/DADOS_HISTORICOS|BMGB4]] · [[03_COMPANIES/BPAN4/DADOS_HISTORICOS|BPAN4]] · [[03_COMPANIES/BRSR6/DADOS_HISTORICOS|BRSR6]] · [[03_COMPANIES/PINE4/DADOS_HISTORICOS|PINE4]]
	- Industrial: [[03_COMPANIES/WEGE3/TESE_DE_INVESTIMENTO|WEGE3 (tese)]] · [[03_COMPANIES/WEGE3/VISAO_GERAL|WEGE3 (visão geral)]]
- [[06_MODELS]] — biblioteca de modelos financeiros _(a popular)_
- [[07_VALUATION/INDEX|07_VALUATION/INDEX]] — metodologias e outputs
	- [[07_VALUATION/BANCOS_GRANDES/INDEX|🔥 Bancos Grandes (5 valuations ativos)]]

---

## Camada 4 — Inteligência

Modelos viram insights, teses e decisões.

- [[04_GOVERNANCA/INDEX|04_GOVERNANCA/INDEX]] — governança corporativa como fator analítico
	- [[04_GOVERNANCA/FRAMEWORK_GERAL_DE_GOVERNANCA|Framework Geral]]
	- [[04_GOVERNANCA/CHECKLIST_GOVERNANCA|Checklist]]
	- [[04_GOVERNANCA/ALOCACAO_DE_CAPITAL|Alocação de Capital]]
	- [[04_GOVERNANCA/ESTRUTURA_SOCIETARIA|Estrutura Societária]]
	- [[04_GOVERNANCA/DIREITOS_DO_MINORITARIO|Direitos do Minoritário]]
	- [[04_GOVERNANCA/PARTES_RELACIONADAS|Partes Relacionadas]]
	- [[04_GOVERNANCA/COMUNICACAO_COM_MERCADO|Comunicação com Mercado]]
- [[08_RESEARCH]] — teses e relatórios _(a popular)_
- [[09_SKILLS/INDEX|09_SKILLS/INDEX]] — capacidades analíticas
	- [[09_SKILLS/SKILL_CONSTRUCAO_DCF|DCF]] · [[09_SKILLS/SKILL_PROJECAO_FINANCEIRA|Projeção]] · [[09_SKILLS/SKILL_MODELO_3_STATEMENTS|3-Statements]] · [[09_SKILLS/SKILL_MISPRICING_DETECTION|Mispricing]] · [[09_SKILLS/SKILL_TOMADA_DE_DECISAO|Decisão]] · [[09_SKILLS/SKILL_ANALISE_MACRO|Macro]] · [[09_SKILLS/SKILL_LEITURA_DE_GRAFICO|Gráfico]] · [[09_SKILLS/SKILL_PRICE_ACTION|Price Action]] · [[09_SKILLS/SKILL_RISCO_RETORNO|Risco/Retorno]] · [[09_SKILLS/INDEX|→ ver índice completo (34 skills)]]
- [[11_PROMPTS/INDEX|11_PROMPTS/INDEX]] — instruções para agentes
	- [[11_PROMPTS/PROMPT_CONSTRUTOR_VALUATION|Construtor de Valuation]] · [[11_PROMPTS/PROMPT_EXTRATOR_FINANCEIRO|Extrator]] · [[11_PROMPTS/PROMPT_AUDITOR_DADOS|Auditor]] · [[11_PROMPTS/PROMPT_PESQUISADOR_EMPRESA|Pesquisador]] · [[11_PROMPTS/PROMPT_AGENTE_REVISAO|Revisor]] · [[11_PROMPTS/PROMPT_REDATOR_RESEARCH|Redator]]
- [[18_DECISIONS]] — decisões de investimento
- [[19_ERROR_LIBRARY]] — erros catalogados
- [[20_LEARNING_LOG/INDEX|20_LEARNING_LOG/INDEX]] — aprendizados do projeto

---

## Camada 5 — Entrega

Insights viram outputs de valor.

- [[14_OUTPUTS]] — entregáveis _(a popular)_
- [[15_TEMPLATES]] — modelos reutilizáveis
	- [[15_TEMPLATES/TEMPLATE_TESE_DE_INVESTIMENTO_COMPLETA|Tese Completa]]
	- [[15_TEMPLATES/TEMPLATE_TESE_DE_INVESTIMENTO_CURTA|Tese Curta]]
	- [[15_TEMPLATES/TEMPLATE_COBERTURA_EMPRESA|Cobertura de Empresa]]
	- [[15_TEMPLATES/TEMPLATE_VALUATION|Valuation]]
	- [[15_TEMPLATES/TEMPLATE_GOVERNANCA_POR_EMPRESA|Governança por Empresa]]
	- [[15_TEMPLATES/TEMPLATE_NOTA_PADRAO|Nota Padrão]]
- [[22_DASHBOARDS]] — visualizações _(a popular)_

---

## Projetos e Fluxo

- [[02_PROJECTS]] — projetos em andamento _(a popular)_
- [[10_WORKFLOWS/INDEX|10_WORKFLOWS/INDEX]] — processos documentados
	- [[10_WORKFLOWS/WORKFLOW_COBERTURA_DE_EMPRESA|Cobertura de Empresa]]
	- [[10_WORKFLOWS/WORKFLOW_VALUATION_DO_ZERO|Valuation do Zero]]
	- [[10_WORKFLOWS/WORKFLOW_AUDITORIA_MODELO|Auditoria de Modelo]]
	- [[10_WORKFLOWS/WORKFLOW_ATUALIZACAO_TRIMESTRAL|Atualização Trimestral]]
	- [[10_WORKFLOWS/WORKFLOW_PESQUISA_TEMATICA|Pesquisa Temática]]
- [[21_BACKLOG]] — ideias e pendências

---

## Fluxos típicos

**Cobrir uma nova empresa (do zero → tese):**
[[10_WORKFLOWS/WORKFLOW_COBERTURA_DE_EMPRESA]] → [[05_DATA_SOURCES]] → [[12_PYTHON]] → [[13_VALIDATION/CHECKLIST_EXTRACAO]] → [[03_COMPANIES]] → [[06_MODELS]] → [[07_VALUATION]] → [[04_GOVERNANCA]] → [[15_TEMPLATES/TEMPLATE_TESE_DE_INVESTIMENTO_COMPLETA]] → [[08_RESEARCH]]

**Atualizar resultado trimestral:**
[[10_WORKFLOWS/WORKFLOW_ATUALIZACAO_TRIMESTRAL]] → [[12_PYTHON]] → [[13_VALIDATION/CHECKLIST_RECONCILIACAO]] → [[03_COMPANIES]] → [[07_VALUATION]] → [[20_LEARNING_LOG/INDEX]]

**Construir um valuation bancário (igual aos 5 atuais):**
[[07_VALUATION/BANCOS_GRANDES/INDEX]] → script em `12_PYTHON/notebooks/build_banks.py` → recalc → validação → INDEX atualizado → learning log

---

## Legenda de status

- 🔥 = trabalho ativo agora
- 🆕 = adicionado recentemente
- _(a popular)_ = pasta existe mas ainda sem conteúdo

---

## Manutenção

- Este HOME é a **única porta de entrada**. Qualquer nova pasta ou módulo deve ser referenciado aqui.
- Pastas começando com `_ARQUIVO_` são legados (duplicatas antigas do vault). Não usar.
- Obsidian Graph View: abrir no HOME para ver o mapa completo de conexões.

---
*Última atualização: 2026-04-24*
