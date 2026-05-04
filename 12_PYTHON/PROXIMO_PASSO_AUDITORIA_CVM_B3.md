---
title: Proximo Passo - Auditoria CVM e B3
tags:
  - python
  - cvm
  - b3
  - dados
  - valuation
  - qualidade
aliases:
  - Auditoria CVM B3
  - Completude de Dados
---

# Proximo Passo - Auditoria CVM e B3

Data: 2026-05-03

## Decisao

Antes de integrar `scanner_quant_profit_b3`, `news_hunter` e `pipeline banco completo`, o proximo passo deve ser resolver a **confiabilidade da base historica CVM/B3**.

Motivo: se DRE, BP, DFC, DFP, ITR e precos entram incompletos, o valuation, os scores, os alertas e o Excel ficam bonitos, mas fragilizados.

---

## Problema observado

O `pipeline banco completo` esta bem estruturado, mas ainda ha dificuldade em obter historico completo para todas as empresas:

- nem todas as empresas tem `codigo_cvm` cadastrado;
- algumas empresas tem ticker novo, fusao, troca de nome ou historico societario quebrado;
- alguns outputs Excel ficam sem todas as linhas historicas de DRE, BP, DFC e indicadores;
- o pipeline baixa DFP/ITR, mas ainda nao mostra claramente onde o dado se perdeu;
- a B3/yfinance cobre preco, mas nao resolve demonstracoes financeiras.

---

## Hipoteses principais

### 1. Cadastro incompleto ou incorreto

Algumas empresas no `config/empresas.yaml` estao sem `codigo_cvm`.

Exemplos observados:

- `AESB3`
- `ENBR3`
- `AERI3`
- `SEQL3`
- `MDNE3`
- `PLPL3`
- `MELK3`
- `LAVV3`
- `SOJA3`
- `BRIT3`
- `FIQE3`
- `VAMO3`
- `RRRP3`
- `LVTC3`

Sem `codigo_cvm`, o pipeline depende da busca automatica, que pode falhar por ticker, nome de pregao, alias ou reorganizacao societaria.

### 2. DFP anual versus ITR trimestral

O pipeline tenta baixar DFP anual e, se faltar, anualiza via ITR. Isso e correto, mas precisa ser auditado por empresa e ano.

Perguntas:

- a DFP nao existe na CVM?
- existe, mas nao tem a empresa?
- existe, mas so no consolidado ou individual?
- o pipeline buscou `con`, mas a empresa so apareceu como `ind`, ou vice-versa?
- o ITR anualizado gerou linhas suficientes?

### 3. Mapeamento de contas incompleto

Mesmo quando o CSV da CVM vem completo, uma linha pode virar zero se o codigo da conta nao estiver no mapeamento.

Exemplo:

```text
CVM entregou a conta -> mapa nao reconheceu -> normalizador colocou 0 -> Excel ficou vazio
```

Isso afeta especialmente:

- bancos com estrutura diferente;
- varejo com contas operacionais especificas;
- empresas com reorganizacao societaria;
- companhias que mudam nomenclatura/codigo de conta ao longo dos anos.

### 4. Escrita no Excel

Tambem e possivel que a informacao esteja no DataFrame normalizado, mas nao esteja sendo escrita na aba/linha correta do template.

Esse e um problema diferente de coleta. Precisa ser diagnosticado separadamente.

---

## Proximo passo tecnico

Criar uma fase de auditoria antes de mexer na integracao dos projetos:

```text
CVM/B3 -> raw audit -> normalized audit -> excel audit -> valuation
```

Essa auditoria deve responder, para cada ticker:

1. Cadastro
   - ticker existe em `empresas.yaml`?
   - tem `codigo_cvm`?
   - tem setor?
   - tem tipo de empresa?

2. Raw CVM
   - DFP existe para cada ano esperado?
   - ITR existe para o ano corrente?
   - docs encontrados: DRE, BPA, BPP, DFC_MI, DFC_MD?
   - quantas linhas vieram por documento?

3. Normalizacao
   - quais contas esperadas ficaram zeradas?
   - quais anos ficaram vazios?
   - quais linhas criticas existem em DRE/BP/DFC?

4. Excel
   - linhas historicas foram escritas?
   - anos historicos aparecem nas abas corretas?
   - DRE/BP/DFC batem com os DataFrames normalizados?

---

## Implementacao recomendada

Criar um modulo novo no pipeline:

```text
12_PYTHON/pipeline banco completo/modules/data_completeness_auditor.py
```

Funcoes iniciais:

```python
auditar_cadastro(ticker: str) -> dict
auditar_raw_cvm(ticker: str, anos: list[int]) -> dict
auditar_normalizacao(ticker: str, dre_hist, bp_hist, dfc_hist=None) -> dict
gerar_relatorio_completude(ticker: str, auditoria: dict) -> Path
```

Criar tambem um comando CLI:

```powershell
python main.py --auditar-dados --ticker BBDC4
python main.py --auditar-dados --all
```

Saida desejada:

```text
outputs/data_quality/
  audit_BBDC4_20260503.md
  audit_BBDC4_20260503.json
  audit_all_20260503.csv
```

---

## Criterios minimos para confiar no valuation

Para liberar um valuation como confiavel:

- DRE historica com pelo menos 5 anos;
- BP historico com pelo menos 5 anos;
- para empresas nao financeiras, DFC com pelo menos 5 anos ou justificativa clara;
- ativo total e passivo total conciliando;
- receita/lucro/PL/ativo nao zerados no ultimo ano;
- mapeamento de contas criticas sem buracos;
- escala CVM validada (`MIL`, `REAL`, divisor por empresa quando necessario);
- relatorio de auditoria salvo junto do Excel.

---

## Ordem pratica de ataque

1. Rodar auditoria em 5 empresas de teste:
   - `BBDC4` banco
   - `WEGE3` industrial
   - `PETR4` petroleo
   - `LREN3` varejo
   - `TAEE11` energia

2. Separar falhas por tipo:
   - falta de codigo CVM;
   - CVM sem documento;
   - erro de consolidado/individual;
   - erro de mapeamento;
   - erro de escala;
   - erro de escrita no Excel.

3. Corrigir primeiro cadastro e mapeamento, depois Excel.

4. So depois retomar a integracao com `scanner_quant_profit_b3` e `news_hunter`.

---

## Decisao de arquitetura

O pipeline deve passar a tratar **completude de dados** como etapa obrigatoria, nao como detalhe de log.

Sem auditoria, o sistema nao sabe se esta analisando uma empresa de verdade ou uma planilha preenchida parcialmente.

