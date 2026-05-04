---
title: Workflow — Cobertura de Nova Empresa
tags:
  - workflow
  - empresa
  - cobertura
aliases:
  - Cobertura de Empresa
status: validado
---

# Workflow: Cobertura de Nova Empresa

> [!abstract] Use este workflow sempre que iniciar cobertura de uma empresa pela primeira vez.

---

## Pré-requisitos

- Ticker e nome da empresa definidos
- Acesso a CVM, RI e B3
- Scripts de ingestão disponíveis em `12_PYTHON/`

---

## Passo a Passo

### Etapa 1 — Estrutura e Identidade

- [ ] Criar pasta: `03_COMPANIES/[TICKER]/`
- [ ] Criar `VISAO_GERAL.md` a partir de [[15_TEMPLATES/TEMPLATE_COBERTURA_EMPRESA]]
- [ ] Preencher: razão social, ticker, CNPJ, setor, segmento B3
- [ ] Identificar peers principais → linkar [[04_SECTORS]]

### Etapa 2 — Pesquisa do Negócio

- [ ] Executar [[09_SKILLS/SKILL_PESQUISA_CORPORATIVA]]
- [ ] Usar prompt: [[11_PROMPTS/PROMPT_PESQUISADOR_EMPRESA]]
- [ ] Preencher: modelo de negócio, segmentos, drivers, riscos, governança

### Etapa 3 — Coleta de Documentos Históricos

- [ ] Baixar DFPs dos últimos 5 anos via CVM
- [ ] Baixar releases dos últimos 8 trimestres (se disponível)
- [ ] Baixar Formulário de Referência mais recente
- [ ] Organizar em `03_COMPANIES/[TICKER]/docs/`

### Etapa 4 — Extração Financeira

- [ ] Executar [[09_SKILLS/SKILL_EXTRACAO_FINANCEIRA]]
- [ ] Usar prompt: [[11_PROMPTS/PROMPT_EXTRATOR_FINANCEIRO]]
- [ ] Extrair: DRE, BP, DFC para todo o período histórico
- [ ] Preencher `DADOS_HISTORICOS.md`

### Etapa 5 — Validação e Reconciliação

- [ ] Executar [[13_VALIDATION/CHECKLIST_EXTRACAO]]
- [ ] Verificar: ativo = passivo + PL
- [ ] Verificar: caixa final BP = caixa final DFC
- [ ] Verificar: variação do caixa DFC coerente
- [ ] Documentar inconsistências encontradas

### Etapa 6 — Construção da Base Histórica

- [ ] Calcular indicadores-chave: margens, ROE, ROIC, dívida líquida/EBITDA
- [ ] Identificar ciclos operacionais e financeiros
- [ ] Mapear capex histórico (manutenção vs expansão)
- [ ] Identificar eventos não recorrentes relevantes

### Etapa 7 — Construção do Modelo

- [ ] Usar [[06_MODELS]] como referência para o setor
- [ ] Montar modelo 3-Statements base
- [ ] Projetar receita, margens, reinvestimento
- [ ] Validar com [[13_VALIDATION/CHECKLIST_MODELAGEM]]

### Etapa 8 — Valuation Inicial

- [ ] Executar [[WORKFLOW_VALUATION_DO_ZERO]]
- [ ] Usar [[09_SKILLS/SKILL_CONSTRUCAO_DCF]]
- [ ] Triangular com [[09_SKILLS/SKILL_MULTIPLOS]]
- [ ] Preencher `VALUATION_INICIAL.md`

### Etapa 9 — Tese Preliminar

- [ ] Usar prompt: [[11_PROMPTS/PROMPT_REDATOR_RESEARCH]]
- [ ] Preencher `TESE_DE_INVESTIMENTO.md`
- [ ] Identificar: catalisadores, riscos, assimetria

### Etapa 10 — Checklist de Cobertura

- [ ] Criar `CHECKLIST_DE_COBERTURA.md` com itens pendentes
- [ ] Linkar a empresa ao setor em [[04_SECTORS]]
- [ ] Atualizar [[17_MEMORY]] com padrões relevantes aprendidos

---

## Entregável Final

```
03_COMPANIES/[TICKER]/
├── VISAO_GERAL.md          ← modelo de negócio, contexto
├── DADOS_HISTORICOS.md     ← base financeira histórica
├── MODELO_FINANCEIRO.md    ← modelo integrado
├── VALUATION_INICIAL.md    ← DCF + múltiplos
├── TESE_DE_INVESTIMENTO.md ← tese, catalisadores, riscos
└── CHECKLIST_DE_COBERTURA.md
```

---

## Tempo Estimado

| Etapa | Estimativa |
|---|---|
| Pesquisa do negócio | 2–4h |
| Coleta e extração | 1–3h (com scripts) |
| Validação | 30–60min |
| Modelo e valuation | 3–6h |
| Tese | 1–2h |
| **Total** | **7–15h** |

---

## Links Relacionados

- [[WORKFLOW_ATUALIZACAO_TRIMESTRAL]]
- [[15_TEMPLATES/TEMPLATE_COBERTURA_EMPRESA]]
- [[13_VALIDATION/CHECKLIST_EXTRACAO]]

---
*Última atualização: 2026-04-16*
