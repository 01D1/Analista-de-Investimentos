---
title: Falhas Recorrentes
tags:
  - memória
  - falhas
  - qualidade
aliases:
  - Falhas Recorrentes
---

# Falhas Recorrentes

Erros que aparecem com frequência e merecem atenção sistêmica.

> [!warning] Se um erro aparece mais de uma vez, vira entrada aqui. Se vira entrada aqui, o sistema precisa de uma prevenção estrutural.

---

## Falhas de Dados

### Unidade incorreta
Ocorreu em: múltiplas extrações iniciais.
Prevenção instalada: [[13_VALIDATION/CHECKLIST_EXTRACAO]] — campo unidade obrigatório.

### Mistura consolidado/controladora
Ocorreu em: primeiras versões do parser CVM.
Prevenção instalada: metadado de consolidação obrigatório + filtro no script.

---

## Falhas de Modelo

### D&A não adicionada no CFO
Ocorreu em: modelos construídos sem template padronizado.
Prevenção instalada: [[13_VALIDATION/CHECKLIST_MODELAGEM]] — verificação explícita.

---

## Falhas de Valuation

### Terminal excessivo não questionado
Ocorreu em: valuations com período explícito curto.
Prevenção instalada: [[13_VALIDATION/REGRAS_DE_ALERTA]] — alerta automático se VT > 75%.

---

## Falhas de Interpretação

### EBITDA ajustado aceito sem verificação
Ocorreu em: análises rápidas sob pressão de tempo.
Prevenção instalada: regra de calcular EBITDA próprio antes de usar o divulgado.

---

*Para erros detalhados, ver: [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]]*

---
*Última atualização: 2026-04-16*
