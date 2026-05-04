---
title: Prompt — Pesquisador de Empresa
tags:
  - prompt
  - agente
  - pesquisa
  - empresa
aliases:
  - Prompt Pesquisador
status: validado
---

# Prompt: Pesquisador de Empresa

## Agente

**Agente 1 — Researcher**
Especialista em coleta e leitura de documentos corporativos.

---

## Prompt

```
Analise a empresa [EMPRESA] como um analista fundamentalista profissional com experiência em buy-side.

Extraia e organize as seguintes informações:

1. MODELO DE NEGÓCIO
   - Como a empresa ganha dinheiro
   - Segmentos operacionais e peso de cada um
   - Mix de receita (produto, canal, geografia)

2. DRIVERS DE RECEITA
   - Os 3–5 principais drivers de crescimento
   - Pricing power: a empresa consegue repassar custos?
   - Natureza da demanda: cíclica, defensiva ou secular?

3. VANTAGENS COMPETITIVAS
   - Quais são os moats reais?
   - Barreiras de entrada
   - Switching costs, escala, marca, regulação

4. RISCOS PRINCIPAIS
   - Regulatório, competitivo, macroeconômico, operacional
   - Governança e risco de agência

5. DINÂMICA COMPETITIVA
   - Quem são os principais concorrentes?
   - Market share e tendência
   - Posicionamento relativo

6. GOVERNANÇA
   - Estrutura de controle
   - Histórico de capital allocation
   - Relacionamento com minoritários

7. ESTRATÉGIA ATUAL
   - Plano estratégico / guidance divulgado
   - M&A recente ou planejado

8. LACUNAS E HIPÓTESES
   - O que ainda não sabemos?
   - Quais questões precisam ser investigadas?

IMPORTANTE:
- Separe claramente FATOS (com fonte), INFERÊNCIAS (com base) e LACUNAS (sem resposta)
- Não generalize. Seja específico sobre esta empresa.
- Aponte contradições entre o discurso da empresa e os dados disponíveis.
```

---

## Como Usar

1. Substituir `[EMPRESA]` pelo ticker ou nome
2. Fornecer ao agente: Formulário de Referência, DFP mais recente, releases recentes
3. Output esperado: nota preenchida com estrutura acima
4. Salvar resultado em `03_COMPANIES/[TICKER]/VISAO_GERAL.md`

---

## Skill Relacionada

[[09_SKILLS/SKILL_PESQUISA_CORPORATIVA]]

---
*Última atualização: 2026-04-16*
