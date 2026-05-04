---
title: Alocação de Capital — Framework de Análise
tags:
  - governança
  - capital-allocation
  - valuation
  - roic
aliases:
  - Capital Allocation
  - Alocação de Capital
---

# Alocação de Capital — Framework de Análise

> A qualidade do alocador de capital é o principal diferencial entre empresas que criam e destroem valor no longo prazo. Este framework estrutura a análise de como a empresa usa o caixa gerado.

---

## O Ciclo do Capital

```
Caixa Gerado (FCF)
        ↓
┌───────────────────────────────┐
│  Opções de Alocação:          │
│  1. Reinvestimento orgânico   │ → Capex crescimento, P&D, capital de giro
│  2. M&A / acquisitions        │ → Crescimento inorgânico
│  3. Dividendos                │ → Retorno imediato ao acionista
│  4. Recompra de ações         │ → Retorno via aumento do EPS
│  5. Amortização de dívida     │ → Redução de risco financeiro
│  6. Caixa acumulado           │ → Optionalidade futura (ou ineficiência)
└───────────────────────────────┘
```

**Pergunta central:** Qual opção maximiza o valor por ação para o acionista?

---

## 1. Reinvestimento Orgânico

### Métricas-chave

| Métrica | Como calcular | O que significa |
|---|---|---|
| ROIC | NOPAT / Capital Investido | Retorno sobre o capital reinvestido |
| WACC | Custo ponderado de capital | Custo mínimo do capital |
| ROIC - WACC (spread) | ROIC menos WACC | Criação (+) ou destruição (−) de valor |
| Taxa de reinvestimento | (Capex − Depreciação + ΔKg) / NOPAT | Quanto do lucro é reinvestido |
| Taxa de crescimento implícita | ROIC × Taxa reinvestimento | Crescimento sustentável com os retornos atuais |

### Como avaliar
- **ROIC > WACC por 5+ anos:** Empresa tem vantagem competitiva real. Reinvestimento cria valor → quanto mais, melhor.
- **ROIC ≈ WACC:** Empresa "zero NPV". Crescimento não cria nem destrói valor. Pagar dividendos pode ser mais eficiente.
- **ROIC < WACC:** Crescimento destrói valor. Cada real reinvestido vale menos que o custo. Distribuir capital é preferível.

### Capex de manutenção vs. crescimento
```
Capex Crescimento = Capex Total − Capex Manutenção
Capex Manutenção ≈ Depreciação (proxy conservadora)

FCF "verdadeiro" = EBITDA − Capex Manutenção − Impostos − ΔKg
```

---

## 2. M&A — Acquisitions

### Sinais de M&A de qualidade

- [ ] Preço pago < valor intrínseco do ativo (EV/EBITDA pago razoável para o setor)
- [ ] Empresa apresenta tese clara: sinergias específicas, verticais identificadas
- [ ] Acquisitions anteriores: retorno > WACC em 3–5 anos pós-aquisição
- [ ] Integração cultural cuidadosa, sem excessiva dependência do founder adquirido
- [ ] Sem pressa ou competição de leilão que force pagamento de prêmio excessivo

### Sinais de M&A destruidor de valor

- [ ] Empresa paga > 15x EV/EBITDA por ativos de crescimento moderado
- [ ] Acquisitions "transformacionais" anunciadas em momentos de pressão por crescimento
- [ ] Management faz muitas acquisitions pequenas sem consolidar as anteriores
- [ ] Goodwill cresce > 50% do capital total após aquisição
- [ ] Empresa emite ações para financiar aquisições (dilutivo se ações baratas)

### Cálculo rápido de retorno pós-aquisição

```
Retorno da Aquisição = EBITDA Adquirido / EV Pago
Custo de capital da aquisição = WACC ± ajuste de risco

Se Retorno > WACC → valor criado
Se Retorno < WACC → valor destruído
```

---

## 3. Política de Dividendos

### Tipos de política

| Tipo | Descrição | Empresa típica |
|---|---|---|
| Mínimo estatutário (25%) | Base legal mínima | Maioria das brasileiras |
| Mínimo elevado (40–60%) | Sinaliza confiança no caixa | WEG (40%), Itaú (~50%) |
| Payout variável | Baseado em FCF do ano | Empresas cíclicas |
| JCP + dividendos | Uso do JCP como eficiência fiscal | Bancos brasileiros |

### O que analisar
- **Payout consistente ou crescente?** Sinal de qualidade de lucro e disciplina financeira
- **Dividendos sustentados por caixa ou dívida?** Dividendos financiados por dívida são sinal de alerta grave
- **JCP:** Reduz base de IR/CSLL. Fiscalmente eficiente. Verificar se taxa usada (TJLP) é razoável

### Dividend yield vs. total shareholder return

```
TSR = Dividend Yield + Crescimento do Lucro/Dividendo por Ação
```
Empresa com yield alto e crescimento zero pode ter TSR menor que empresa com yield baixo e crescimento forte.

---

## 4. Recompra de Ações (Buyback)

### Quando buybacks criam valor
- Ação negociando abaixo do valor intrínseco estimado pelo management
- Management tem excesso de caixa sem oportunidades de reinvestimento acima do WACC
- Recompra reduz shares outstanding, aumentando EPS e valor por ação

### Quando buybacks destroem valor
- Ação cara (P/B > 5x, P/E > 30x para empresa madura) — pagando premium pelo próprio estoque
- Empresa usa caixa para recompras enquanto endividamento aumenta
- Recompras seguidas de emissão para pagar executivos (efeito nulo ao acionista)

### Análise de histórico de buybacks

| Período | Preço médio de recompra | Shares recompradas | Preço atual | Retorno implícito |
|---|---|---|---|---|
| | | | | |

---

## 5. Amortização de Dívida

### Quando priorizar amortização
- Alavancagem (Dívida Líquida/EBITDA) > 3x
- Dívida de curto prazo com risco de rolagem em ambiente de juros elevados
- Custo da dívida > ROIC (cada real de dívida pesa mais que o retorno gerado)

### Quando manter dívida
- Custo de dívida < ROIC → alavancagem financeira cria valor para o acionista
- Setor com fluxo previsível (utilities, locadoras) → alavancagem sustentável
- Período de capex intensivo com retornos altos esperados → bridge de dívida aceitável

---

## 6. Caixa Acumulado (Inefficient Cash Hoarding)

### Sinais de ineficiência
- Caixa líquido > 20% da capitalização de mercado sem plano claro de uso
- Aplicações financeiras a CDI em vez de reinvestimento ou distribuição
- Management alega "optionalidade futura" por vários anos sem executar

### Quando caixa acumulado é defensável
- Empresa em setor altamente cíclico (reserva para sobrevivência em downturn)
- M&A target identificado, mas negociação em andamento
- Regulatório exige buffer mínimo de liquidez (bancos: capital regulatório)

---

## Histórico de Alocação — Template

```
Empresa: ___________________  Período analisado: _______

Resumo de FCF gerado (Σ 5 anos): R$ ___ bi

Alocação histórica:
  Reinvestimento orgânico (capex − depreciação):  R$ ___ bi  (___%)
  M&A líquido (acquisitions − desinvestimentos):  R$ ___ bi  (___%)
  Dividendos + JCP pagos:                          R$ ___ bi  (___%)
  Recompras de ações líquidas:                    R$ ___ bi  (___%)
  Amortização de dívida líquida:                  R$ ___ bi  (___%)
  Variação de caixa:                              R$ ___ bi  (___%)
  Total:                                          R$ ___ bi  (100%)

Avaliação:
  ROIC médio 5 anos: ___%
  WACC estimado: ___%
  Spread (ROIC − WACC): ___%
  Criação/destruição de valor via reinvestimento: ___
```

---

## Benchmarks por Setor

| Setor | ROIC típico | Payout típico | Reinvestimento típico |
|---|---|---|---|
| Bens de Capital (WEG) | 25–35% | 40–50% | 40–60% FCF |
| Bancos grandes | ROE 18–25% | ~50% | N/A (retenção para capital regulatório) |
| Utilities | 8–12% | 70–90% | 20–30% FCF |
| Varejo food | 15–25% | 30–50% | 50–70% FCF |
| Telecom | 8–15% | 70–100% | 30–40% FCF |

---

## Links Cruzados

- [[FRAMEWORK_GERAL_DE_GOVERNANCA]] — Governança geral
- [[RED_FLAGS_DE_GOVERNANCA]] — Sinais de alerta
- [[REMUNERACAO_DA_ADMINISTRACAO]] — Incentivos do management
- [[TEMPLATE_TESE_DE_INVESTIMENTO_COMPLETA]] — Onde usar esta análise

---
*Última atualização: 2026-04-16*
