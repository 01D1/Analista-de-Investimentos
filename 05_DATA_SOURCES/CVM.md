---
title: Fonte — CVM (Comissão de Valores Mobiliários)
tags:
  - fonte
  - cvm
  - dados
aliases:
  - CVM
  - Comissão de Valores Mobiliários
---

# Fonte: CVM

## O que é

Portal oficial de dados de companhias abertas brasileiras. Obrigatório para listadas na B3.

## Tipo de Dado Disponível

| Documento | Periodicidade | Conteúdo |
|---|---|---|
| DFP | Anual | Demonstrações completas auditadas |
| ITR | Trimestral | Demonstrações trimestrais |
| FRE | Anual | Formulário de Referência (governança, riscos, estrutura) |
| IAN | Anual | Informações anuais (descontinuado, substituído pelo FRE) |
| Fatos Relevantes | Ad hoc | Eventos materiais |
| Comunicados ao Mercado | Ad hoc | Informativos gerais |

## Formato

- **XBRL** — padrão estruturado, ideal para parsing automatizado
- **PDF** — versão legível
- **Dados abertos (JSON/CSV)** — API pública disponível

## API Pública

```
https://dados.cvm.gov.br/
```

Endpoint para DFP/ITR:
```
/dataset/cia_aberta-doc-dfp
/dataset/cia_aberta-doc-itr
```

## Confiabilidade

Alta — dados auditados, regulatórios.

## Limitações

- XBRL pode ter inconsistências em empresas menores
- Histórico via API limitado (dados mais antigos apenas em PDF)
- Algumas empresas entregam em controladora e consolidado — verificar qual usar
- Atraso: ITR em até 45 dias após fechamento do trimestre; DFP em até 3 meses após fechamento do exercício

## Script

`12_PYTHON/src/ingestion/cvm_downloader.py`
`12_PYTHON/src/parsers/xbrl_parser.py`
`12_PYTHON/src/parsers/dfp_parser.py`

## Problemas Conhecidos

- Unidade pode variar entre R$ mil e R$ MM dependendo da empresa
- Antes de 2010: dados em formato legado, qualidade variável
- Algumas empresas usam planos de contas personalizados no XBRL

---
*Última atualização: 2026-04-16*
