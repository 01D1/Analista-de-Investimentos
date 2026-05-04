---
title: "Skill: Valuation por Múltiplos"
tags:
  - skill
  - valuation
  - múltiplos
  - comparáveis
aliases:
  - Múltiplos
  - Valuation por Múltiplos
status: validado
---

# Skill: Valuation por Múltiplos

## Objetivo

Avaliar uma empresa com base em múltiplos de mercado, cruzando com peers e histórico, para triangular valor e validar um DCF.

---

## Quando Usar

- Como complemento ao DCF
- Quando não há dados suficientes para DCF robusto
- Para análise rápida de mispricing relativo
- Para comparação dentro de um setor

> [!warning] Múltiplos sem análise de comparabilidade real são perigosos.

---

## Principais Múltiplos

### Múltiplos de Enterprise Value

| Múltiplo | Fórmula | Quando usar |
|---|---|---|
| EV/EBITDA | EV / EBITDA | universal, compara estrutura operacional |
| EV/EBIT | EV / EBIT | quando depreciação é relevante (ex: varejo físico) |
| EV/Receita | EV / Receita | para empresas sem lucro (crescimento early stage) |
| EV/FCFF | EV / FCF Firm | foco em geração de caixa |

### Múltiplos de Equity

| Múltiplo | Fórmula | Quando usar |
|---|---|---|
| P/L (P/E) | Preço / LPA | lucro recorrente por ação |
| P/VP | Preço / VPA | bancos, seguradoras, holdings |
| P/FCF | Preço / FCF Equity | geração de caixa disponível ao acionista |
| Dividend Yield | DPS / Preço | empresas maduras com payout alto |
| PEG | P/L / Crescimento | crescimento ajustado ao preço |

---

## Processo

### 1. Selecionar Peers

- [ ] Mesma indústria / setor
- [ ] Modelo de negócio comparável
- [ ] Porte similar ou ajustar para escala
- [ ] Mesma geografia (ou ajustar prêmio de risco)
- [ ] Qualidade de lucro comparável

> [!tip] 4–8 peers é o ideal. Mais do que isso dilui a análise. Menos do que 3 é insuficiente.

### 2. Calcular Múltiplos dos Peers

- Usar mesmos períodos (LTM ou ano fiscal)
- Usar EBITDA e lucro **recorrentes** — não o divulgado diretamente
- Calcular EV corretamente: Mkt Cap + Dívida Bruta – Caixa + Minorias + Outras obrigações

### 3. Calcular Múltiplos da Empresa-Alvo

- Mesmo critério que os peers
- Calcular com preço de mercado atual
- Calcular com projeção forward (próximos 12 meses)

### 4. Comparação

| Empresa | EV/EBITDA LTM | EV/EBITDA Fwd | P/L LTM | P/L Fwd |
|---|---|---|---|---|
| [Alvo] | | | | |
| [Peer 1] | | | | |
| [Peer 2] | | | | |
| Mediana | | | | |

### 5. Precificação Implícita

- Aplicar mediana dos peers ao EBITDA / lucro da empresa-alvo
- Calcular preço implícito por ação
- Comparar com preço atual

### 6. Análise Histórica

- Plotar múltiplo da empresa vs médias históricas (1, 3, 5 anos)
- Identificar se está em desconto ou prêmio histórico
- Levantar hipóteses para o porquê

---

## Ajustes Obrigatórios Antes de Comparar

- Excluir não recorrentes do EBITDA e do lucro
- Neutralizar diferenças de alíquota de IR
- Ajustar para variações de estrutura de capital (dívida)
- Considerar diferenças de crescimento (PEG se necessário)

---

## Erros Comuns

> [!danger]

- Comparar P/L sem ajustar não recorrentes
- Usar múltiplo de empresa de outro país sem ajuste de risco / custo de capital
- Usar EV sem incluir dívida líquida correta
- Comparar empresa em ciclo de expansão (EBITDA deprimido) com empresa estabilizada
- PEG com crescimento de períodos inconsistentes

---

## Critérios de Qualidade

- [ ] Peers com comparabilidade real justificada
- [ ] EBITDA e lucro recorrentes utilizados
- [ ] EV calculado corretamente para todos os peers
- [ ] Análise histórica do múltiplo realizada
- [ ] Conclusão não baseada em um único múltiplo

---
*Última atualização: 2026-04-16*
