---
title: Prompt — Extrator Financeiro
tags:
  - prompt
  - agente
  - extração
  - dfp
  - itr
aliases:
  - Prompt Extrator
status: validado
---

# Prompt: Extrator Financeiro

## Agente

**Agente 2 — Financial Extractor**
Especialista em transformar documentos em dados estruturados.

---

## Prompt

```
Leia os documentos financeiros fornecidos e extraia os dados com máxima acurácia.

DOCUMENTOS FORNECIDOS: [lista de documentos]
EMPRESA: [TICKER]
PERÍODO: [trimestre/ano]

EXTRAIA AS SEGUINTES DEMONSTRAÇÕES:

1. DRE (Demonstração do Resultado)
Para cada linha, forneça:
- Nome da linha conforme documento
- Valor numérico
- Unidade (R$ mil / R$ MM / USD)
- Observação sobre recorrência se relevante

Linhas obrigatórias: Receita Bruta, Deduções, Receita Líquida, CPV, Lucro Bruto,
Despesas Operacionais (detalhadas), EBIT, Resultado Financeiro (detalhado),
EBT, IR/CSLL, Lucro Líquido, Lucro Atribuível à Controladora

2. BALANÇO PATRIMONIAL
Separar Ativo e Passivo. Incluir totais e subtotais.
Linhas obrigatórias: caixa, aplicações, contas a receber, estoques, imobilizado,
intangível, dívida CP, dívida LP, fornecedores, PL

3. FLUXO DE CAIXA
Linhas obrigatórias: CFO (antes de capex), capex, CFI total, CFF total,
dividendos, recompras, variação de dívida, variação líquida, caixa inicial, caixa final

METADADOS OBRIGATÓRIOS:
- Consolidação: consolidado ou controladora
- Periodicidade: trimestral ou anual
- Base: acumulado ou período isolado
- Nota de não recorrentes identificados

REGRAS:
- Nunca inferir ou estimar. Extrair apenas o que está explícito no documento.
- Se uma linha não estiver no documento, indicar como "não disponível"
- Marcar qualquer ambiguidade com [?] e explicar
- Separar itens divulgados como ajustados/não recorrentes pela empresa
```

---

## Como Usar

1. Fornecer documentos (DFP/ITR/release) ao agente
2. Preencher EMPRESA e PERÍODO
3. Output esperado: tabelas estruturadas prontas para inserir na base
4. Validar resultado com [[13_VALIDATION/CHECKLIST_EXTRACAO]]

---

## Skill Relacionada

[[09_SKILLS/SKILL_EXTRACAO_FINANCEIRA]]

---
*Última atualização: 2026-04-16*
