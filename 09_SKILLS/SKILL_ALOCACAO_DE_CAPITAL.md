---
title: "Skill: Alocação de Capital"
tags: [skill, portfolio, risco]
status: validado
---

# Skill: Alocação de Capital

## Objetivo
Definir o tamanho correto de cada posição para maximizar retorno ajustado ao risco do portfólio.

## Princípios

1. **Concentração com convicção**: posições grandes só em teses de alta qualidade
2. **Diversificação por risco real**: não misturar ativos altamente correlacionados
3. **Assimetria**: R/R favorável em toda entrada

## Frameworks de sizing

### Kelly Criterion (simplificado)
```
f = (p × b – q) / b
onde:
  p = probabilidade de ganho
  b = ganho relativo ao risco
  q = 1 – p
```

### Sizing por convicção
| Nível | Tamanho máximo |
|---|---|
| Alta convicção | 8–15% do portfólio |
| Média convicção | 3–7% |
| Baixa / especulativo | 1–2% |

### Sizing por volatilidade
- Posição inversa à volatilidade: ativo mais volátil → posição menor

## Regras de risco
- Nunca mais de 20% em 1 ativo (concentração tóxica)
- Nunca mais de 40% em 1 setor (risco setorial)
- Cash como posição legítima quando não há oportunidade

## Erros Comuns
- Posição igual para todas as teses
- Aumentar posição perdedora sem revisar a tese
- Ignorar correlação entre ativos na carteira
