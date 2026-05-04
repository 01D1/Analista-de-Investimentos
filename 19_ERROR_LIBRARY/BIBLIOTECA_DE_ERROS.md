---
title: Biblioteca de Erros
tags:
  - erros
  - governança
  - qualidade
aliases:
  - Biblioteca de Erros
  - Error Library
---

# Biblioteca de Erros

> [!tip] Erro documentado vira ativo. Cada entrada aqui previne que o mesmo erro seja cometido novamente.

---

## Como Registrar um Novo Erro

Use o formato abaixo para cada entrada:

```
### ERR-[NNN]: [Título Curto]
**Descrição:** O que aconteceu
**Sintoma:** Como o erro se manifesta
**Causa:** Por que aconteceu
**Impacto:** Consequência para análise / output
**Como detectar:** Sinal de alerta
**Como corrigir:** Passo a passo para resolução
**Como prevenir:** Mudança de processo
**Data:** AAAA-MM-DD
**Categoria:** dados / modelo / valuation / código / interpretação
```

---

## Categoria: Dados

### ERR-001: Confusão de unidade (R$ mil vs R$ MM)

**Descrição:** Dado extraído em R$ mil foi tratado como R$ MM no modelo.
**Sintoma:** Receita ou lucro 1000x maior ou menor do que o esperado.
**Causa:** CVM publica em R$ mil, mas algumas empresas publicam em R$ MM. Sem verificação de unidade.
**Impacto:** Todos os indicadores e valuation corrompidos.
**Como detectar:** Checar se número faz sentido em ordem de grandeza. Receita de empresa mid-cap deve estar em bilhões (R$ MM) ou bilhões de milhares (R$ mil).
**Como corrigir:** Identificar a unidade correta no cabeçalho do documento. Recalcular tudo.
**Como prevenir:** [[13_VALIDATION/CHECKLIST_EXTRACAO]] exige campo "unidade" preenchido.
**Data:** 2026-04-16
**Categoria:** dados

---

### ERR-002: Mistura de consolidado com controladora

**Descrição:** Dados do balanço consolidado misturados com dados da controladora.
**Sintoma:** Capital de giro, caixa ou dívida com valores inconsistentes vs releases.
**Causa:** CVM disponibiliza ambos. Parser sem filtro de consolidação.
**Impacto:** Indicadores de alavancagem e liquidez distorcidos.
**Como detectar:** Comparar caixa extraído com release da empresa. Grandes diferenças indicam problema.
**Como corrigir:** Re-extrair usando somente demonstrativo consolidado.
**Como prevenir:** Metadado "consolidação" obrigatório em [[CHECKLIST_EXTRACAO]].
**Data:** 2026-04-16
**Categoria:** dados

---

### ERR-003: Acumulado do ano tratado como trimestre isolado

**Descrição:** DRE acumulada 9M usada como se fosse Q3 isolado.
**Sintoma:** Receita do trimestre 3× maior do que histórico de Q3.
**Causa:** Documento é "Jan–Set" mas código não isola o trimestre.
**Impacto:** Base histórica com erro para todos os períodos.
**Como corrigir:** T3 isolado = Acum_9M – Acum_6M. Recalcular.
**Como prevenir:** Parser deve identificar periodicidade e calcular isolado automaticamente.
**Data:** 2026-04-16
**Categoria:** dados

---

### ERR-004: Caixa bruto usado como caixa líquido

**Descrição:** Caixa bruto (antes de dívidas CP) usado como caixa disponível para dívida líquida.
**Sintoma:** Dívida líquida subestimada. Empresa parece menos alavancada do que é.
**Causa:** Não subtraída a parcela de dívida de curto prazo do caixa.
**Impacto:** Equity Value superestimado.
**Como corrigir:** Dívida Líquida = Dívida Bruta (CP + LP) – (Caixa + Aplicações).
**Como prevenir:** Fórmula de dívida líquida fixada no modelo. [[REGRAS_DE_ALERTA]] verifica coerência.
**Data:** 2026-04-16
**Categoria:** dados

---

## Categoria: Modelo

### ERR-005: Capex duplicado

**Descrição:** Capex contabilizado tanto na linha de "compra de ativo" quanto na variação de imobilizado.
**Sintoma:** FCF subavaliado. Imobilizado crescendo o dobro do esperado.
**Causa:** Duas fontes de capex no DFC sem perceber que são a mesma coisa.
**Impacto:** FCF e valuation incorretos.
**Como corrigir:** Identificar todas as linhas de capex no DFC e garantir que representa a saída total uma única vez.
**Como prevenir:** [[CHECKLIST_MODELAGEM]] verifica ligação capex ↔ imobilizado.
**Data:** 2026-04-16
**Categoria:** modelo

---

### ERR-006: D&A não adicionada de volta no CFO

**Descrição:** Modelo começa pelo lucro líquido no CFO mas não adiciona D&A.
**Sintoma:** CFO muito abaixo do reportado. FCF aparentemente fraco.
**Causa:** Confundir CFO com FCFF. D&A é ajuste não-caixa obrigatório no método indireto.
**Impacto:** FCF e valuation subavaliados.
**Como corrigir:** Adicionar D&A ao ponto de partida do CFO no modelo.
**Como prevenir:** [[CHECKLIST_MODELAGEM]] exige D&A no CFO explicitamente.
**Data:** 2026-04-16
**Categoria:** modelo

---

## Categoria: Valuation

### ERR-007: Valor terminal dominante (> 80% do EV)

**Descrição:** Valor terminal representa 85% do EV calculado.
**Sintoma:** Preço-alvo extremamente sensível a pequenas variações de g ou WACC.
**Causa:** Período explícito curto (5 anos) com taxa de crescimento no terminal alta.
**Impacto:** Valuation pouco confiável — qualquer erro de premissa muda radicalmente o resultado.
**Como corrigir:** Estender período explícito. Reduzir g. Verificar se WACC está correto.
**Como prevenir:** [[CHECKLIST_VALUATION]] e [[REGRAS_DE_ALERTA]] alertam quando VT > 75%.
**Data:** 2026-04-16
**Categoria:** valuation

---

### ERR-008: PEG calculado com crescimento inconsistente

**Descrição:** PEG usa crescimento esperado para 5 anos mas P/L usa LPA dos últimos 12 meses.
**Sintoma:** PEG artificialmente baixo (empresa parece "barata" quando não é).
**Causa:** Mistura de períodos: P/L retroativo com crescimento prospectivo.
**Impacto:** Comparação de múltiplos enganosa.
**Como corrigir:** P/L forward (próximos 12 meses) ÷ crescimento esperado nos próximos 3–5 anos.
**Como prevenir:** Documentar período de cada múltiplo e crescimento na análise.
**Data:** 2026-04-16
**Categoria:** valuation

---

## Categoria: Interpretação

### ERR-009: EBITDA ajustado divulgado como verdade

**Descrição:** EBITDA ajustado divulgado pela empresa aceito sem verificação.
**Sintoma:** Margem EBITDA parece muito melhor do que a estrutura do negócio sugere.
**Causa:** Empresa exclui itens que são recorrentes operacionalmente (ex: SBC, reestruturação anual).
**Impacto:** Valuation superestimado. Comparação com peers distorcida.
**Como corrigir:** Calcular EBITDA a partir do EBIT + D&A extraídos. Comparar com divulgado. Investigar diferença.
**Como prevenir:** [[REGRAS_DE_ALERTA]] alerta quando EBITDA ajustado > EBITDA calculado em > 20%.
**Data:** 2026-04-16
**Categoria:** interpretação

---
*Última atualização: 2026-04-16*
