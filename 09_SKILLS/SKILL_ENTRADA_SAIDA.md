---
title: "Skill: Entrada e Saída"
tags: [skill, analise-tecnica, trading]
status: validado
---

# Skill: Entrada e Saída

## Objetivo
Definir com precisão o ponto de entrada, o stop e o alvo antes de executar qualquer operação — eliminando decisões emocionais.

## Regra absoluta
> Toda operação começa pelo fim: defina o stop antes da entrada.

## Estrutura de setup

```
CONTEXTO (tendência) → ZONA (suporte/resistência) → GATILHO (confirmação) → ENTRADA
```

### 1. Contexto
- Qual é a tendência do timeframe maior?
- Estou operando a favor ou contra?

### 2. Zona
- Onde o preço está? (suporte, resistência, média)
- É uma zona de alta probabilidade?

### 3. Gatilho
- Candle de reversão (engolfo, martelo, estrela cadente)
- Rompimento de máxima/mínima do candle anterior
- Cruzamento de indicador na zona

### 4. Entrada
- Entrada na abertura do candle seguinte ao gatilho
- Ou entrada limitada dentro da zona

## Stop
- Abaixo da zona de suporte (compra)
- Acima da zona de resistência (venda)
- Em múltiplos de ATR: ex. 1,5 × ATR

## Alvo
- Próxima resistência relevante (compra)
- Próximo suporte relevante (venda)
- R/R mínimo: 2:1

## Saída parcial
- Realizar 50% na primeira resistência
- Mover stop para break-even
- Deixar 50% correr com trailing stop

## Erros Comuns
- Entrar sem stop definido
- Mover stop para baixo para "dar mais tempo"
- Sair no lucro cedo e segurar prejuízo
