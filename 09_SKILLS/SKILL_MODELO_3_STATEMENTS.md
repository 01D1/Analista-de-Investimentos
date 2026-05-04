---
title: "Skill: Modelo 3-Statements"
tags: [skill, modelagem, demonstrativos]
status: validado
---

# Skill: Modelo 3-Statements

## Objetivo
Integrar DRE, Balanço Patrimonial e Fluxo de Caixa em um modelo coeso e auto-consistente.

## Lógica de integração

```
DRE → Lucro Líquido → Patrimônio Líquido (BP)
DRE → EBITDA → ponto de partida do DFC Indireto
BP → variação de capital de giro → DFC
BP → dívida bruta → despesa financeira (DRE)
DFC → caixa final → caixa no BP
```

## Processo

### Passo 1 — DRE
- Receita líquida → CMV → Lucro Bruto
- Despesas operacionais → EBIT → resultado financeiro → LAIR → IR → Lucro Líquido

### Passo 2 — Balanço Patrimonial
- Ativo circulante: caixa, recebíveis, estoques
- Passivo circulante: fornecedores, obrigações fiscais
- PL: capital + reservas + lucro retido (do DRE)

### Passo 3 — DFC Indireto
- Lucro Líquido + D&A – ∆ capital de giro = FCO
- FCO – Capex = FCL
- FCL – amortizações + captações = variação de caixa

## Checklist de consistência
- [ ] Caixa do DFC = caixa no BP
- [ ] Lucro do DRE = variação do PL (sem dividendos)
- [ ] Dívida líquida do BP bate com DFC (captações – amortizações)

## Erros Comuns
- Circular reference no caixa
- Capital de giro não atrelado à receita
- D&A no DFC diferente do DRE
