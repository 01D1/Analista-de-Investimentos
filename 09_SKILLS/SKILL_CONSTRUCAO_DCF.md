---
title: "Skill: Construção de DCF"
tags:
  - skill
  - valuation
  - dcf
  - wacc
aliases:
  - DCF
  - Fluxo de Caixa Descontado
status: validado
---

# Skill: Construção de DCF

## Objetivo

Construir um modelo de fluxo de caixa descontado (DCF) completo, rastreável e auditável, para estimar o valor intrínseco de uma empresa.

---

## Quando Usar

- Valuation de empresa industrial, de serviços, varejo ou tecnologia
- Quando o negócio tem histórico de geração de caixa estável
- Como ancoragem junto a múltiplos comparáveis

> [!warning] Não usar DCF como método principal para bancos, seguradoras ou holdings com ativos complexos. Ver [[07_VALUATION/Valuation_Bancos]] e [[07_VALUATION/Valuation_Seguros]].

---

## Entradas Necessárias

- Histórico financeiro limpo (DRE, BP, DFC)
- Premissas macroeconômicas (IPCA, SELIC, câmbio)
- Premissas operacionais da empresa
- Beta setorial / alavancado
- Custo da dívida (CDI + spread ou taxa de emissão)
- Taxa livre de risco

---

## Processo

### 1. Construção do Histórico

- [ ] Mínimo 5 anos de histórico
- [ ] Calcular EBIT, NOPAT, FCF histórico
- [ ] Identificar ciclo de capex (manutenção vs crescimento)
- [ ] Mapear capital de giro histórico

### 2. Projeção Operacional (5–10 anos)

- [ ] **Receita:** crescimento por driver (volume × preço, ou top-down setorial)
- [ ] **Margem EBIT:** trajetória com justificativa
- [ ] **NOPAT:** EBIT × (1 – taxa efetiva de IR)
- [ ] **Reinvestimento:** capex + variação de capital de giro
- [ ] **FCF Firm:** NOPAT – Reinvestimento

### 3. WACC

```
WACC = Ke × (E/V) + Kd × (1-t) × (D/V)
```

| Componente | Método | Observação |
|---|---|---|
| Taxa livre de risco (Rf) | NTN-B longa (IPCA+) ou Treasuries | ajustar para moeda do modelo |
| Beta | setorial desalavancado, re-alavancado | Damodaran por setor |
| Prêmio de risco de mercado (ERP) | 5–6% histórico ou implícito | |
| Custo do equity (Ke) | CAPM: Rf + β × ERP | |
| Custo da dívida (Kd) | taxa média da dívida ou CDI + spread | pré-IR |
| Estrutura de capital | D/V e E/V a valor de mercado | |

### 4. Valor Terminal

Dois métodos:

**Perpetuidade com crescimento (Gordon):**
```
VT = FCF_n × (1 + g) / (WACC – g)
```

**Múltiplo de saída:**
```
VT = EBITDA_n × Múltiplo_terminal
```

> [!tip] Triangular os dois. O valor terminal não deve representar mais de 70–75% do valor total — se ultrapassar, rever premissas de crescimento ou WACC.

### 5. Desconto a Valor Presente

- [ ] Descontar FCFs do período explícito ao WACC
- [ ] Descontar Valor Terminal ao WACC
- [ ] Somar: Enterprise Value (EV)

### 6. Equity Value

```
Equity Value = EV – Dívida Líquida – Minorias – Contingências
Preço Justo por Ação = Equity Value / Ações Totais
```

### 7. Análise de Sensibilidade

Variar as duas variáveis mais impactantes:

- WACC (tipicamente ±0,5pp e ±1pp)
- Taxa de crescimento terminal (tipicamente ±0,5pp)
- Margem EBIT no estado estacionário

### 8. Triangulação com Múltiplos

Ver [[SKILL_MULTIPLOS]] para validar o DCF contra:
- EV/EBITDA implícito vs peers
- P/L implícito vs histórico da empresa

---

## Saídas Esperadas

- Arquivo do modelo com premissas documentadas
- Tabela de sensibilidade
- Nota de valuation: [[15_TEMPLATES/TEMPLATE_VALUATION]]

---

## Erros Comuns

> [!danger]

- WACC artificialmente baixo que infla o valor sem justificativa
- Crescimento terminal acima do PIB de longo prazo nominal (implausível)
- Valor terminal > 80% do EV sem questionamento
- Beta de empresa diferente do setor sem ajuste
- Dívida líquida calculada com caixa errado (pegar bruto ou não excluir caixa restrito)
- FCF negativo em anos de transição sem justificativa de por que melhora

---

## Critérios de Qualidade

- [ ] Cada premissa tem justificativa explícita
- [ ] WACC documentado componente a componente
- [ ] Valor terminal testado por dois métodos
- [ ] Sensibilidade executada nas variáveis críticas
- [ ] Equity Value reconcilia com ações em circulação corretas

---

## Scripts Relacionados

- `12_PYTHON/src/valuation/dcf_calculator.py`
- `12_PYTHON/src/valuation/wacc_builder.py`
- `12_PYTHON/src/valuation/sensitivity_engine.py`

---

## Notas Complementares

Ver também: [[07_VALUATION/DCF]], [[07_VALUATION/WACC]], [[07_VALUATION/Taxa_Terminal]]

---
*Última atualização: 2026-04-16*
