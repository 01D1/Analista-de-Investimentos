---
title: Padrões Identificados
tags:
  - memória
  - padrões
  - cvm
  - dados
aliases:
  - Padrões
---

# Padrões Identificados

Padrões repetíveis observados nos dados, nas fontes e nas análises.

---

## Estrutura do DFP da CVM — DRE

### 2026-04-16 — Codificação CVM: 3.01 = Receita Líquida (não bruta)

**Contexto:** Descoberto ao parsear o DFP 2023 da WEG (código CVM 005410).

**Padrão:**
A grande maioria das companhias abertas brasileiras apresenta a DRE no DFP CVM com a seguinte estrutura:

```
3.01 = Receita de Venda de Bens e/ou Serviços  ← JÁ É RECEITA LÍQUIDA
3.02 = Custo dos Bens e/ou Serviços Vendidos   ← CPV / COGS
3.03 = Resultado Bruto                          ← LUCRO BRUTO
3.04 = Despesas/Receitas Operacionais           ← TOTAL DAS DESPESAS
3.04.01 = Despesas com Vendas
3.04.02 = Despesas Gerais e Administrativas
3.05 = Resultado Antes do Resultado Financeiro  ← EBIT
3.06 = Resultado Financeiro
3.07 = Resultado Antes dos Tributos            ← EBT
3.08 = IR e CSLL
3.09 = Resultado Líquido (Operações Continuadas)
3.11 = Lucro/Prejuízo Consolidado do Período
3.11.01 = Atribuído à Controladora             ← NET INCOME (atribuível ao acionista)
3.11.02 = Atribuído a Não Controladores        ← MINORITY INTEREST
```

**Atenção:** Algumas empresas podem ter 3.01 = Receita Bruta + 3.02 = Deduções + 3.03 = Receita Líquida (estrutura alternativa, menos comum). Verificar pelo nome da conta, não apenas pelo código.

**Aplicação:** Parser `dfp_parser.py` usa esta estrutura como padrão.

---

## Estrutura do DFC da CVM — Variação Cambial

### 2026-04-16 — 6.04 = Forex Effect (linha fora do CFO+CFI+CFF)

**Contexto:** Ao reconciliar o DFC da WEG 2023, CFO+CFI+CFF não fechava com a variação de caixa.

**Padrão:**
```
6.01 = CFO
6.02 = CFI
6.03 = CFF
6.04 = Variação Cambial s/ Caixa e Equivalentes  ← FORA dos 3 grupos!
6.05 = Aumento (Redução) de Caixa                ← = 6.01+6.02+6.03+6.04
6.05.01 = Saldo Inicial de Caixa
6.05.02 = Saldo Final de Caixa
```

**Regra:** Reconciliação correta: `CFO + CFI + CFF + 6.04 = Variação de Caixa`

**Aplicação:** `reconciler.py` e `schemas.py` já corrigidos para incluir `forex_effect_on_cash`.

---

## Estrutura do BP da CVM — PL Consolidado

### 2026-04-16 — Cálculo do PL da Controladora

**Contexto:** WEG tem estrutura de PL onde 2.03.09 = Participação dos não controladores.

**Padrão:**
```
2.03 = PL Consolidado Total  ← inclui minoritários
2.03.09 = Participação dos Acionistas Não Controladores
PL Controladora = 2.03 - 2.03.09
```

**Atenção:** O código de não controladores varia por empresa (pode ser 2.03.01, 2.03.09, etc.). Verificar pelo nome da conta.

**Regra:** Nunca usar uma subconta do PL diretamente como "shareholders_equity" sem verificar se é o total ou um componente.

---

## DFC: Ponto de Partida ≠ Lucro Líquido

### 2026-04-16 — DFC começa pelo EBT (pré-IR), não pelo lucro líquido

**Contexto:** No DFC da WEG 2023, o ponto de partida (6.01.01.01) é o "Lucro Antes dos Impostos" (EBT = R$ 6.59 bi), não o lucro líquido (R$ 5.73 bi). Diferença ≈ IR pago.

**Padrão:** Algumas empresas usam EBT como ponto de partida no método indireto — o IR pago aparece como ajuste em "Variações nos Ativos e Passivos". Isso é tecnicamente correto e comum.

**Aplicação:** O aviso do reconciler sobre esta diferença é esperado e não é erro.

---

## Estrutura CVM para Bancos — DRE Bancária

### 2026-04-16 — 3.01 = Receitas de Intermediação (≠ Receita Líquida industrial)

**Contexto:** Ao adaptar o parser industrial para bancos brasileiros.

**Padrão:**
```
3.01 = Receitas da Intermediação Financeira  ← TOTAL (NÃO é Receita Líquida industrial)
3.01.01 = Juros e Similares
3.01.05 = Tarifas e Serviços (fee income)
3.01.06 = Seguros e Previdência
3.02 = Despesas da Intermediação
3.02.01 = Juros (funding cost)
3.02.02 = PDD / Provisão para Perda Esperada
3.03 = Resultado Bruto da Intermediação (NII após PDD)
3.04 = Outras Despesas/Receitas Operacionais
3.04.03 = Despesas Administrativas
3.04.08 = Equivalência Patrimonial (BB/Bradesco usam .08, Itaú usa .07)
3.05 = EBT (Resultado Antes dos Tributos)
```

**Atenção:** Não usar `3.01` como proxy de Receita Líquida para bancos — é revenue bruto de intermediação.

---

## Variações de Layout de PL entre Bancos CVM

### 2026-04-16 — Itaú usa 2.08, BB usa 2.07, Itaúsa usa 2.03

**Contexto:** Ao mapear BPP de diferentes bancos no mesmo pipeline.

**Padrão:**
```
Itaú Unibanco / BTG / Bradesco / Santander:
  2.08 = Patrimônio Líquido Consolidado
  2.08.09 = Participação Não Controladores

Banco do Brasil / Banrisul:
  2.07 = Patrimônio Líquido Consolidado
  2.07.01 = PL Atribuído ao Controlador (direto)
  2.07.02 = Não Controladores

Itaúsa (holding industrial):
  2.03 = Patrimônio Líquido Consolidado
  2.03.09 = Não Controladores
```

**Regra:** Usar nome da conta ("Patrimônio Líquido Consolidado") como campo de maior confiança — mais robusto que código.

**Aplicação:** `bank_account_mapper.py` usa `NAME_PRIORITY_FIELDS` para dar prioridade ao nome sobre o código para campos de PL.

---

## Variações de Layout de Carteira de Crédito — BPA Bancos

### 2026-04-16 — Itaú usa 1.02.03.04, BB usa 1.02.04.04

**Padrão:**
```
Itaú / BTG:
  1.02.03 = Custo Amortizado
  1.02.03.04 = Operações de Crédito e Arrendamento Mercantil

BB / Bradesco:
  1.02.04 = Custo Amortizado (layout alternativo)
  1.02.04.04 = Operações de Crédito
```

**Aplicação:** Ambos os códigos mapeados em `BANK_ACCOUNT_MAP`.

---

## net_income = 0 em bancos sem minority interest

### 2026-04-16 — 3.11.01 = 0 quando não há não controladores

**Contexto:** ABCB4 e BPAN4 mostravam net_income = 0.

**Padrão:** Alguns bancos sem participação de não controladores significativa declaram `3.11.01 = 0` e `3.11.02 = 0`, colocando o resultado integralmente em `3.11` (nível consolidado).

**Regra:** Se `net_income = 0` mas `net_income_consolidated != 0`, usar consolidated como fallback.

**Aplicação:** `bank_parser.py` tem este fallback implementado.

---
*Última atualização: 2026-04-16*
