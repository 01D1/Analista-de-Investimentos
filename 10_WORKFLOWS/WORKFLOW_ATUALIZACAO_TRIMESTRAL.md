---
title: Workflow — Atualização Trimestral
tags:
  - workflow
  - trimestral
  - atualização
aliases:
  - Atualização Trimestral
status: validado
---

# Workflow: Atualização Trimestral

> [!abstract] Execute este workflow sempre que um novo resultado for divulgado (release, ITR ou DFP).

---

## Gatilho

Disponibilização de:
- Release de resultados
- ITR (trimestral) ou DFP (anual)
- Apresentação de resultados

---

## Passo a Passo

### Etapa 1 — Coleta

- [ ] Baixar release de resultados (RI da empresa)
- [ ] Baixar ITR/DFP na CVM
- [ ] Baixar apresentação institucional (se disponível)
- [ ] Verificar data-base e periodicidade do documento

### Etapa 2 — Extração

- [ ] Extrair linhas da DRE, BP e DFC do novo período
- [ ] Registrar metadados (unidade, consolidação, periodicidade)
- [ ] Calcular trimestre isolado (se documento é acumulado: T_isolado = Acum_T – Acum_T-1)

### Etapa 3 — Atualização da Base Histórica

- [ ] Adicionar novo período à base em `DADOS_HISTORICOS.md`
- [ ] Verificar não recorrentes relevantes neste trimestre
- [ ] Recalcular LTM (últimos 12 meses)

### Etapa 4 — Reconciliação

- [ ] Executar [[13_VALIDATION/CHECKLIST_RECONCILIACAO]]
- [ ] Verificar consistência do novo período com os anteriores
- [ ] Documentar qualquer inconsistência

### Etapa 5 — Revisão de Premissas

- [ ] Comparar resultado vs premissas do modelo
- [ ] Identificar surpresas positivas e negativas
- [ ] Revisar premissas de receita, margem, capex se necessário
- [ ] Registrar mudança de premissa em [[18_DECISIONS]] se relevante

### Etapa 6 — Atualização do Modelo

- [ ] Inserir novo período real no modelo
- [ ] Ajustar projeções com novas informações
- [ ] Recalcular indicadores-chave

### Etapa 7 — Atualização do Valuation

- [ ] Rolar o valuation para nova data-base
- [ ] Verificar se preço justo variou significativamente
- [ ] Atualizar tabela de sensibilidade

### Etapa 8 — Registro de Mudanças de Tese

- [ ] O que mudou na tese desde o último trimestre?
- [ ] Catalisadores: algum se materializou ou se afastou?
- [ ] Riscos: algum aumentou ou diminuiu?
- [ ] Tese principal se mantém?

### Etapa 9 — Output Executivo

- [ ] Gerar nota de resultado: `AAAA-QN_[TICKER]_RESULTADO.md`
- [ ] Usar prompt: [[11_PROMPTS/PROMPT_REDATOR_RESEARCH]]
- [ ] Salvar em `14_OUTPUTS/Relatorios_Executivos/`

### Etapa 10 — Arquivamento

- [ ] Mover versão anterior do valuation para `25_ARCHIVE/`
- [ ] Atualizar data da última revisão na nota de cobertura

---

## Entregável

```
14_OUTPUTS/Relatorios_Executivos/
└── AAAA-QN_[TICKER]_RESULTADO_v1.md
```

---

## Links Relacionados

- [[WORKFLOW_COBERTURA_DE_EMPRESA]]
- [[13_VALIDATION/CHECKLIST_RECONCILIACAO]]
- [[11_PROMPTS/PROMPT_EXTRATOR_FINANCEIRO]]

---
*Última atualização: 2026-04-16*
