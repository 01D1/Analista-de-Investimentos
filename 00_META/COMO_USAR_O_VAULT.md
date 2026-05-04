---
title: Como Usar o Vault
tags:
  - meta
  - guia
  - onboarding
aliases:
  - Guia do Vault
  - Onboarding
---

# Como Usar o Vault

Guia prático para operadores humanos e agentes de IA.

---

## Para começar uma sessão

1. Abrir [[README_GERAL]] para orientação geral
2. Verificar [[ROADMAP]] para prioridades ativas
3. Consultar [[01_OPERATING_SYSTEM/PROTOCOLO_DE_ATUALIZACAO]] para tarefas recorrentes

---

## Para cobrir uma nova empresa

→ Seguir [[10_WORKFLOWS/WORKFLOW_COBERTURA_DE_EMPRESA]]

Resumo:
1. Criar pasta em `03_COMPANIES/[TICKER]/`
2. Usar [[15_TEMPLATES/TEMPLATE_COBERTURA_EMPRESA]] como base
3. Baixar documentos históricos via scripts em `12_PYTHON/`
4. Validar com [[13_VALIDATION/CHECKLIST_EXTRACAO]]
5. Construir modelo e valuation
6. Registrar tese inicial

---

## Para atualizar resultados trimestrais

→ Seguir [[10_WORKFLOWS/WORKFLOW_ATUALIZACAO_TRIMESTRAL]]

---

## Para construir um valuation

→ Seguir [[10_WORKFLOWS/WORKFLOW_VALUATION_DO_ZERO]]

Metodologias disponíveis:
- [[07_VALUATION/DCF]]
- [[07_VALUATION/Multiples]]
- [[07_VALUATION/DDM]]
- [[07_VALUATION/SOTP]]
- [[07_VALUATION/NAV]]

---

## Para pesquisar um tema

→ Seguir [[10_WORKFLOWS/WORKFLOW_PESQUISA_TEMATICA]]

---

## Para auditar um modelo

→ Seguir [[10_WORKFLOWS/WORKFLOW_AUDITORIA_MODELO]]
→ Usar [[13_VALIDATION/CHECKLIST_RECONCILIACAO]]

---

## Para usar um agente de IA

Consultar [[11_PROMPTS]] para o prompt correto:

| Tarefa | Prompt |
|---|---|
| Pesquisar empresa | [[11_PROMPTS/PROMPT_PESQUISADOR_EMPRESA]] |
| Extrair dados financeiros | [[11_PROMPTS/PROMPT_EXTRATOR_FINANCEIRO]] |
| Auditar dados | [[11_PROMPTS/PROMPT_AUDITOR_DADOS]] |
| Construir valuation | [[11_PROMPTS/PROMPT_CONSTRUTOR_VALUATION]] |
| Escrever research | [[11_PROMPTS/PROMPT_REDATOR_RESEARCH]] |

---

## Para documentar um erro

→ Registrar em [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]]

Formato: descrição, sintoma, causa, impacto, detecção, correção, prevenção.

---

## Para registrar uma decisão importante

→ Criar arquivo em `18_DECISIONS/` com formato:
`AAAA-MM-DD_decisao_[descricao_curta].md`

Usar [[15_TEMPLATES/TEMPLATE_DECISAO]] como base.

---

## Para adicionar uma skill nova

→ Criar arquivo em `09_SKILLS/` usando [[15_TEMPLATES/TEMPLATE_SKILL]]

---

## Ritual Semanal

Ver [[01_OPERATING_SYSTEM/RITUAL_DE_REVISAO_SEMANAL]]

---

## Ritual Mensal

- Revisar arquitetura geral
- Consolidar aprendizados em [[17_MEMORY]]
- Eliminar duplicidades
- Promover notas úteis para conhecimento permanente
- Arquivar notas obsoletas em [[25_ARCHIVE]]
- Revisar métricas de qualidade em [[ROADMAP]]

---
*Última atualização: 2026-04-16*
