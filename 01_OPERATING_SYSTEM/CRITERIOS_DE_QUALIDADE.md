---
title: Critérios de Qualidade
tags:
  - operating-system
  - qualidade
  - governança
aliases:
  - Critérios de Qualidade
  - Padrão de Qualidade
---

# Critérios de Qualidade

Define o que significa "feito com qualidade" em cada dimensão do projeto.

---

## Qualidade de Dados

> [!success] Dados com qualidade passam nestas verificações:

- [ ] Fonte identificada e datada
- [ ] Unidade explícita (R$ mil / R$ MM / USD)
- [ ] Consolidação identificada (consolidado / controladora)
- [ ] Periodicidade clara (trimestral / anual / LTM)
- [ ] Recorrência mapeada (recorrente / não recorrente / ajustado)
- [ ] DRE + BP + DFC reconciliados
- [ ] Variação do caixa bate com DFC

---

## Qualidade de Modelo

- [ ] Ligação entre as 3 demonstrações funcionando
- [ ] Capex refletindo no imobilizado
- [ ] Depreciação alimentando DRE e DFC corretamente
- [ ] Capital de giro movimentando o DFC
- [ ] Dívida e juros integrados
- [ ] Modelo auditado com [[13_VALIDATION/CHECKLIST_MODELAGEM]]

---

## Qualidade de Valuation

- [ ] Premissas documentadas e justificadas
- [ ] WACC calculado com premissas explícitas
- [ ] Valor terminal não domina excessivamente o valor total
- [ ] Múltiplos de saída comparados com peers reais
- [ ] Sensibilidade realizada nas variáveis críticas
- [ ] Triangulação com ao menos 2 metodologias
- [ ] Auditado com [[13_VALIDATION/CHECKLIST_VALUATION]]

---

## Qualidade de Research / Output

- [ ] Tese clara e objetiva
- [ ] Fatos separados de interpretações
- [ ] Riscos explicitados
- [ ] Lacunas identificadas
- [ ] Fontes citadas
- [ ] Conclusão direta e fundamentada
- [ ] Revisado com [[11_PROMPTS/PROMPT_AGENTE_REVISAO]]

---

## Qualidade de Código Python

- [ ] Função com responsabilidade única
- [ ] Inputs e outputs documentados
- [ ] Logs suficientes para rastrear problemas
- [ ] Tratamento de erros explícito
- [ ] Testes unitários para lógicas críticas
- [ ] Validação de schema nos dados de entrada
- [ ] Nenhum dado bruto e dado tratado no mesmo arquivo

---

## Qualidade do Vault

- [ ] Notas têm frontmatter completo
- [ ] Wikilinks funcionando (sem links quebrados)
- [ ] Tags seguem padrão definido em [[PADRAO_DE_NOMENCLATURA]]
- [ ] Notas de rascunho não ficam indefinidamente sem evolução
- [ ] Outputs têm versão, data e fontes

---
*Última atualização: 2026-04-16*
