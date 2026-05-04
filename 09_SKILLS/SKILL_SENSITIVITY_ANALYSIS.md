---
title: "Skill: Sensitivity Analysis"
tags: [skill, modelagem, valuation]
status: validado
---

# Skill: Sensitivity Analysis

## Objetivo
Quantificar como o valor justo muda quando premissas-chave variam — e identificar quais premissas realmente importam.

## Premissas típicas a testar

| Premissa | Range sugerido |
|---|---|
| Crescimento da receita | ±3 p.p. |
| Margem EBITDA | ±2 p.p. |
| WACC / Ke | ±1 p.p. |
| g (perpetuidade) | ±0,5 p.p. |
| Múltiplo de saída | ±1x |

## Tipos de análise

### 1. Tabela de sensibilidade 2×2
- Eixo X: WACC / Ke
- Eixo Y: crescimento ou margem
- Resultado: matriz de preços justo

### 2. Tornado chart
- Ordena premissas por impacto no valor
- Identifica os "value drivers" reais

### 3. Monte Carlo (avançado)
- Distribui premissas com distribuições probabilísticas
- Gera range de valor com intervalo de confiança

## Interpretação
- Premissas com alto impacto = foco da due diligence
- Se valor só é atrativo em cenários otimistas = red flag
- Se valor é atrativo mesmo no cenário pessimista = margem de segurança real

## Erros Comuns
- Variar premissas isoladamente ignorando correlações
- Usar ranges simétricos quando distribuição é assimétrica
- Não documentar o cenário-base explicitamente
