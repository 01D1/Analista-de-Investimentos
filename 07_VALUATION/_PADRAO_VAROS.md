---
title: Padrão de Estrutura VAROS (DCF)
tags: [valuation, varos, template, referência]
aliases: [Estrutura VAROS, Padrão VAROS, Template VAROS]
---

# Padrão VAROS — Estrutura das planilhas DCF

> Referência mapeada a partir da análise de 60+ planilhas VAROS DCF (empresas B3).
> Usar como **template mental** ao construir valuations próprios no estilo VAROS.

## Abas típicas (14 abas)

| # | Aba | Propósito | Dependências |
|---|---|---|---|
| 1 | **Dashboard** | Resumo visual: Ticker, Preço Justo, Cotação, Upside, TIR, matriz de sensibilidade WACC × g | Todas |
| 2 | **WACC** | Cálculo do custo de capital (Ke, Kd, Beta, Prêmio de Risco) | Macro + estrutura de capital |
| 3 | **Valor do Equity** | Somatório dos FCD + valor terminal ÷ ações emitidas | DRE+DCF, WACC |
| 4 | **TIR ON / TIR PN / TIR UNIT** | TIR por classe de ação | Valor do Equity |
| 5 | **Preço Teto** | Preço máximo para manter retorno-alvo | Valor do Equity |
| 6 | **DRE + DCF** | DRE projetada + Fluxo de Caixa Livre para a Firma (FCFF) | Projeções Operacionais |
| 7 | **DRE - Contas Abertas** | DRE detalhada linha a linha | — |
| 8 | **Balanço Patrimonial** | BP projetado (principalmente Capital de Giro e Dívida Líquida) | — |
| 9 | **Projeções Operacionais** | Motor da modelagem (receita por linha, CAPEX por ativo) | — |
| 10 | **Projeções - CAPEX e CG** | CAPEX e Capital de Giro como % da receita | — |
| 11 | **Painel de Índices** | ROIC, ROE, Dívida Líquida/EBITDA, margens | DRE + BP |
| 12 | **Histórico por Trimestre** | Histórico de trimestres anteriores para calibração | — |

## Localização das premissas-chave

### Aba `Dashboard` (layout padrão)
Área central: linhas 9-20, colunas 5-6 (label|valor)

| Linha | Col 5 (label) | Col 6 (valor) |
|---|---|---|
| 9 | Trimestre Atual | nº do tri |
| 10 | Ticker | `XXXX3` |
| 11 | Ações Emitidas (mil) | nº ações |
| 12 | Valor da Empresa (mil) | Enterprise Value |
| 13 | Dívida (mil) | Dív. Líquida |
| 14 | Ativos/Passivos Não-Operacionais | ajuste |
| 15 | Valor do Equity (mil) | Equity Value |
| 16 | **Valor da Ação** | **Preço Justo/ação** |
| 17 | Cotação | Preço atual |
| 18 | Preço Teto | R$ |
| 18/19 | Upside/Downside | % |
| 19/20 | TIR | % a.a. |

Área direita: matriz de sensibilidade WACC × Growth (colunas 8-20, linhas 9-18).

### Aba `WACC` (linhas 14-20, coluna 5)

| Linha | Conteúdo |
|---|---|
| 14 | Bottom-up Beta |
| 15 | Prêmio de Risco (padrão **6,5%**) |
| 16 | Ke (Custo de Capital Próprio) |
| 18 | Kd (Custo de Capital de Terceiros) |
| 20 | **WACC** |

A direita há colunas por ano (2024, 2025, 2026, ...) com o WACC forward.

## Estética (observações)

- Cabeçalho com **ticker e nome** em fonte grande (L3)
- Coluna 1 funciona como menu de navegação (hyperlinks para cada aba)
- Células cinzas = input (premissa), cores escuras = cálculo/output
- Prêmio de risco fixado em **6,5%** (benchmark Damodaran ajustado BR)
- Uso extensivo de formatação condicional e formatos percentuais

## Implicações para seu modelo

1. **Abra pelo Dashboard**. O Dashboard é o "resumo gerencial" — tudo o mais alimenta ele.
2. **Separe inputs de cálculos**. Premissas cruas (crescimento, margens) ficam em abas dedicadas (Projeções); o Dashboard só consolida.
3. **Sensibilidade embutida**. A matriz WACC × g é a espinha dorsal da apresentação — mostra em quanto o preço-alvo se move com mudanças pequenas nas premissas.
4. **Múltiplas classes de ação**. Para empresas com ON/PN/UNIT (Taesa, Alupar, Klabin), faça uma aba TIR por classe e replique os preços-teto.

Ver também: [[09_SKILLS/SKILL_CONSTRUCAO_DCF]], [[15_TEMPLATES]]

*Gerado em 2026-04-22 a partir de análise automatizada das planilhas VAROS DCF.*
