---
title: Workflow — Auditoria de Modelo
tags:
  - workflow
  - auditoria
  - validação
aliases:
  - Auditoria de Modelo
status: validado
---

# Workflow: Auditoria de Modelo Financeiro

> [!warning] Execute este workflow antes de qualquer output que será utilizado para decisão.

---

## Passo a Passo

### 1. Verificar Links entre Demonstrativos
- [ ] Lucro líquido da DRE aparece corretamente na DFC?
- [ ] Caixa final da DFC = caixa no BP?
- [ ] Dívida líquida está consistente entre BP e DFC?

### 2. Validar Sinais
- [ ] Capex é negativo (saída de caixa)?
- [ ] Depreciação é positiva no DFC (adição)?
- [ ] Resultado financeiro: despesa é negativa?
- [ ] Variação de capital de giro: crescimento normalmente é saída?

### 3. Validar Fórmulas Críticas
- [ ] EBITDA = EBIT + D&A?
- [ ] FCFF = NOPAT – ΔCapital Investido?
- [ ] EV = Mkt Cap + Dívida Bruta – Caixa + Minorias?
- [ ] Dívida líquida = Dívida Bruta – Caixa e Aplicações?

### 4. Validar Consistência Histórica
- [ ] Crescimento de receita faz sentido histórico?
- [ ] Margens oscilam dentro de range razoável para o setor?
- [ ] ROIC histórico coerente com qualidade percebida do negócio?

### 5. Testar Extremos
- [ ] O que acontece se crescimento for 0? O modelo não quebra?
- [ ] O que acontece se margem cair 5pp?
- [ ] WACC 2pp acima ainda gera valor razoável?

### 6. Verificar Circularidade
- [ ] Há referências circulares não intencionais?
- [ ] Juros dependem de dívida que depende de juros? (circular intencional — documentar)

### 7. Revisar Premissas
- [ ] Todas as premissas têm justificativa?
- [ ] Premissas estão dentro de range histórico ou há justificativa para extrapolar?
- [ ] Executar [[13_VALIDATION/CHECKLIST_VALUATION]]

### 8. Emitir Relatório de Inconsistências
- [ ] Listar tudo que não passou nos checks acima
- [ ] Classificar: erro crítico / aviso / observação
- [ ] Registrar em [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]] se erro novo

---

## Critério de Aprovação

> [!success] Modelo aprovado quando:
> - Zero erros críticos
> - Todos os links entre demonstrativos funcionando
> - Premissas documentadas
> - Sensibilidade executada

---
*Última atualização: 2026-04-16*
