---
title: Padrão de Nomenclatura
tags:
  - operating-system
  - nomenclatura
  - padrão
aliases:
  - Nomenclatura
  - Convenções de Nome
---

# Padrão de Nomenclatura

Convenções que garantem consistência e buscabilidade em todo o vault.

---

## Regras Gerais

| Regra | Correto | Errado |
|---|---|---|
| MAIÚSCULAS para arquivos do sistema | `MISSAO.md` | `missão.md` |
| Underscores no lugar de espaços | `TESE_DE_INVESTIMENTO` | `tese de investimento` |
| Sem acentos em nomes de arquivo | `DECISAO` | `DECISÃO` |
| Datas no início para arquivos datados | `2026-04-16_nota.md` | `nota_16-04.md` |
| Ticker em maiúsculo para empresas | `PETR4/` | `petrobras/` |

---

## Pastas

```
00_META/
01_OPERATING_SYSTEM/
...
NN_NOME_PASTA/
```

- Prefixo numérico com 2 dígitos
- Nome em MAIÚSCULAS com underscores
- Sem acentos

---

## Arquivos de Sistema

```
NOME_DO_ARQUIVO.md
```

- MAIÚSCULAS
- Underscores
- Sem acentos, sem espaços

Exemplos:
- `README_GERAL.md`
- `CHECKLIST_RECONCILIACAO.md`
- `WORKFLOW_COBERTURA_DE_EMPRESA.md`

---

## Arquivos Datados (Decisões, Erros, Logs)

```
AAAA-MM-DD_descricao_curta.md
```

Exemplos:
- `2026-04-16_decisao_adotar_duckdb.md`
- `2026-05-02_erro_mapeamento_capex.md`
- `2026-04-16_aprendizado_leitura_notas_explicativas.md`

---

## Empresas

```
03_COMPANIES/[TICKER]/
```

Exemplos:
- `03_COMPANIES/PETR4/`
- `03_COMPANIES/WEGE3/`
- `03_COMPANIES/ITUB4/`

Arquivos internos seguem padrão de sistema:
- `VISAO_GERAL.md`
- `TESE_DE_INVESTIMENTO.md`
- `DADOS_HISTORICOS.md`

---

## Outputs

```
AAAA-MM-DD_[TICKER]_[TIPO]_v[N].md
```

Exemplos:
- `2026-04-16_WEGE3_VALUATION_v1.md`
- `2026-07-10_PETR4_RESEARCH_v2.md`
- `2026-04-16_SETORIAL_ENERGIA_v1.md`

---

## Skills

```
SKILL_[NOME_DA_SKILL].md
```

Exemplos:
- `SKILL_PESQUISA_CORPORATIVA.md`
- `SKILL_CONSTRUCAO_DCF.md`
- `SKILL_LEITURA_DRE.md`

---

## Workflows

```
WORKFLOW_[NOME_DO_FLUXO].md
```

Exemplos:
- `WORKFLOW_COBERTURA_DE_EMPRESA.md`
- `WORKFLOW_ATUALIZACAO_TRIMESTRAL.md`

---

## Prompts

```
PROMPT_[FUNCAO_DO_AGENTE].md
```

Exemplos:
- `PROMPT_PESQUISADOR_EMPRESA.md`
- `PROMPT_EXTRATOR_FINANCEIRO.md`

---

## Scripts Python

```
[modulo]_[funcao].py
```

Exemplos:
- `cvm_downloader.py`
- `dfp_parser.py`
- `dcf_calculator.py`
- `indicators_engine.py`

---

## Tags

Tags em minúsculas, sem acentos, com hífens:

```
#empresa/PETR4
#setor/energia
#valuation/dcf
#status/em-andamento
#tipo/skill
#tipo/workflow
#tipo/template
```

---
*Última atualização: 2026-04-16*
