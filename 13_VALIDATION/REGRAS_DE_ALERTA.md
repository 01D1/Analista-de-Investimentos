---
title: Regras de Alerta
tags:
  - validação
  - alertas
  - red-flags
aliases:
  - Red Flags
  - Alertas do Sistema
status: validado
---

# Regras de Alerta

Condições que devem disparar revisão obrigatória antes de prosseguir.

---

## Alertas de Dados (nível crítico)

| Condição | Ação |
|---|---|
| Ativo ≠ Passivo + PL | Parar. Identificar causa antes de avançar. |
| Caixa BP ≠ Caixa DFC | Parar. Verificar extração de ambos. |
| Variação caixa DFC ≠ Final – Inicial | Parar. Dado corrompido ou extração errada. |
| Receita negativa | Parar. Erro de sinal ou extração. |
| PL negativo sem explicação | Investigar. Pode ser correto (ex: recompra massiva). |

---

## Alertas de Dados (nível aviso)

| Condição | Ação |
|---|---|
| EBITDA divulgado ≠ EBIT + D&A extraídos (> 5%) | Verificar ajustes da empresa |
| Alíquota efetiva de IR < 15% ou > 40% | Verificar crédito fiscal ou evento especial |
| Capex > 3× depreciação em empresa madura | Investigar ciclo de expansão ou reclassificação |
| FCF < 0 por mais de 3 anos consecutivos | Revisar projeções ou checar necessidade de capital |
| Dívida líquida > 4× EBITDA em empresa não-financeira | Verificar liquidez e covenant risk |

---

## Alertas de Valuation (nível crítico)

| Condição | Ação |
|---|---|
| Valor Terminal > 80% do EV | Parar. Rever g e WACC. Modelo sensível demais ao terminal. |
| WACC < 5% para empresa brasileira | Parar. Provável erro de cálculo. |
| g ≥ WACC | Parar. Modelo matematicamente inválido (denominador negativo). |
| Preço justo > 10× preço atual | Alertar. Verificar premissas com ceticismo alto. |

---

## Alertas de Valuation (nível aviso)

| Condição | Ação |
|---|---|
| g > IPCA esperado de longo prazo | Justificar explicitamente |
| EV/EBITDA implícito > 2× mediana setorial | Revisar premissas de crescimento |
| Beta < 0,5 para empresa cíclica | Revisar cálculo |
| WACC < custo da dívida | Erro de estrutura de capital |

---

## Alertas de Modelo (nível crítico)

| Condição | Ação |
|---|---|
| Lucro DRE não bate com ponto de partida DFC | Parar. Link entre demonstrações quebrado. |
| Imobilizado cresce sem capex | Parar. Fórmula errada no modelo. |
| Depreciação negativa | Parar. Erro de sinal. |

---

## Alertas Analíticos (nível observação)

| Condição | Ação |
|---|---|
| EBITDA "ajustado" muito acima do EBITDA reportado (> 20%) | Investigar ajustes da empresa |
| Lucro cresce mas FCF cai | Investigar qualidade do lucro (capital de giro, provisões) |
| Revenue guidance sistematicamente acima do realizado | Incorporar desconto ao guidance |
| Management vendendo ações após guidance positivo | Flag de risco de governança |

---
*Última atualização: 2026-04-16*
