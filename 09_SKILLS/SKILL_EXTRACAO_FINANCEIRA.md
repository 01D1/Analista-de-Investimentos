---
title: "Skill: Extração Financeira"
tags:
  - skill
  - extração
  - dados-financeiros
  - dfp
  - itr
aliases:
  - Extração Financeira
  - Extrator Financeiro
status: validado
---

# Skill: Extração Financeira

## Objetivo

Transformar documentos financeiros (DFP, ITR, releases, notas explicativas) em dados estruturados, padronizados e reconciliados.

---

## Quando Usar

- Ao baixar novos demonstrativos de uma empresa
- Ao construir histórico financeiro do zero
- Ao atualizar base com novos trimestres
- Ao verificar consistência entre fontes

---

## Entradas Necessárias

- Documentos: DFP, ITR, release de resultados
- Fontes: [[05_DATA_SOURCES/CVM]], [[05_DATA_SOURCES/RI_Empresas]]
- Schema alvo de normalização

---

## Processo

### 1. Coleta dos Documentos

- [ ] Baixar DFP/ITR via CVM (XBRL ou PDF)
- [ ] Baixar release de resultados
- [ ] Baixar apresentação institucional (se disponível)
- [ ] Verificar data de referência e periodicidade

### 2. Extração da DRE

Linhas obrigatórias a extrair:

| Linha | Observação |
|---|---|
| Receita Bruta | pode estar implícita |
| Deduções | impostos sobre vendas |
| Receita Líquida | base de margem |
| CPV / COGS | custo direto |
| Lucro Bruto | = Rec. Líq. – CPV |
| Despesas Operacionais | SG&A, P&D |
| EBIT | resultado operacional |
| Resultado Financeiro | separar despesa de receita |
| EBT | antes do IR |
| IR / CSLL | |
| Lucro Líquido | |
| Participação Minoritária | se houver |
| Lucro Atribuível à Controladora | |

### 3. Extração do Balanço Patrimonial

Linhas obrigatórias:

**Ativo:**
- Caixa e equivalentes
- Aplicações financeiras
- Contas a receber
- Estoques
- Outros ativos circulantes
- Total Ativo Circulante
- Imobilizado líquido
- Intangível líquido
- Investimentos (equiv. patrimonial)
- Total Ativo Não Circulante
- Total do Ativo

**Passivo:**
- Fornecedores
- Dívida de CP (financiamentos CP)
- Outros passivos circulantes
- Total Passivo Circulante
- Dívida de LP
- Outros passivos não circulantes
- Total Passivo Não Circulante
- Patrimônio Líquido
- Total Passivo + PL

### 4. Extração do Fluxo de Caixa

| Linha | Observação |
|---|---|
| CFO — Caixa Operacional | antes do capex |
| Capex | separar manutenção e expansão se possível |
| CFI — Caixa de Investimentos | inclui capex + aquisições |
| CFF — Caixa de Financiamentos | dívida, juros, dividendos, recompras |
| Variação Líquida do Caixa | CFO + CFI + CFF |
| Caixa Inicial | |
| Caixa Final | deve = Caixa Inicial + Variação |

### 5. Validação e Reconciliação

- [ ] Ativo Total = Passivo Total + PL
- [ ] Caixa Final do BP = Caixa Final da DFC
- [ ] Variação do caixa: DFC bate com BP?
- [ ] Lucro Líquido da DRE = ponto de partida da DFC?
- [ ] Dívida líquida: (Dívida CP + LP) – (Caixa + Aplicações)

### 6. Metadados Obrigatórios

Para cada linha extraída, registrar:

```
empresa: [TICKER]
periodo: [AAAA-QN] ou [AAAA]
consolidacao: consolidado | controladora
unidade: R$ mil | R$ MM | USD mil
recorrencia: recorrente | nao_recorrente | ajustado
fonte: [URL ou arquivo]
data_coleta: [AAAA-MM-DD]
```

---

## Saídas Esperadas

- Arquivo CSV / Parquet com dados estruturados
- Log de inconsistências identificadas
- Nota de reconciliação vinculada à empresa

---

## Erros Comuns

> [!danger] Atenção especial

- **Unidade errada:** confundir R$ mil com R$ MM (erro de 1000x)
- **Consolidação errada:** misturar consolidado com controladora
- **Acumulado vs trimestral:** somar acumulado do ano inteiro quando precisava de trimestre isolado
- **Capex duplicado:** contar compra de ativo e variação de imobilizado como dois capex
- **Caixa bruto vs líquido:** não subtrair dívida CP para calcular dívida líquida

Ver: [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]]

---

## Critérios de Qualidade

- [ ] Todas as linhas obrigatórias preenchidas
- [ ] Metadados completos para cada extração
- [ ] Reconciliação executada e aprovada
- [ ] Inconsistências documentadas

---

## Scripts Relacionados

- `12_PYTHON/src/parsers/dfp_parser.py`
- `12_PYTHON/src/parsers/xbrl_parser.py`
- `12_PYTHON/src/validation/reconciliation.py`

---

## Notas Complementares

Ver também: [[SKILL_AJUSTES_CONTABEIS]], [[SKILL_QUALIDADE_DOS_LUCROS]]
Prompt para agente: [[11_PROMPTS/PROMPT_EXTRATOR_FINANCEIRO]]

---
*Última atualização: 2026-04-16*
