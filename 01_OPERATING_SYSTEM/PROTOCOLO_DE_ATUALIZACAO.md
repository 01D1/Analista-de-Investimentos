---
title: Protocolo de Atualização
tags:
  - operating-system
  - protocolo
  - atualização
aliases:
  - Protocolo de Atualização
---

# Protocolo de Atualização

Define como e quando o vault deve ser atualizado para manter sua integridade e utilidade.

---

## Atualizações Imediatas (quando ocorrem)

| Gatilho | Ação |
|---|---|
| Nova empresa coberta | Criar pasta em `03_COMPANIES/` + arquivos base |
| Novo release/ITR disponível | Atualizar dados históricos + premissas |
| Erro identificado | Registrar em [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]] |
| Decisão importante tomada | Criar arquivo em `18_DECISIONS/` |
| Nova skill desenvolvida | Criar arquivo em `09_SKILLS/` |
| Nova fonte mapeada | Criar arquivo em `05_DATA_SOURCES/` |
| Insight relevante | Registrar em `20_LEARNING_LOG/` |

---

## Ritual Semanal

> [!tip] Executar toda semana, preferencialmente no mesmo dia.

**Duração estimada:** 30–60 min

**Checklist:**

- [ ] Novos documentos recebidos processados?
- [ ] Empresas com dados desatualizados identificadas?
- [ ] Pipelines com falha identificados?
- [ ] Erros repetidos registrados na biblioteca?
- [ ] Backlog priorizado e revisado?
- [ ] Premissas que precisam revisão marcadas?
- [ ] Oportunidades de automação anotadas?
- [ ] Insights novos transformados em skills?

---

## Ritual Mensal

> [!tip] Revisão profunda do sistema.

**Duração estimada:** 2–4 horas

**Checklist:**

- [ ] Arquitetura geral revisada
- [ ] Aprendizados consolidados em [[17_MEMORY]]
- [ ] Duplicidades eliminadas
- [ ] Notas úteis promovidas a conhecimento permanente
- [ ] Notas obsoletas arquivadas em [[25_ARCHIVE]]
- [ ] Taxonomia de tags revisada
- [ ] Métricas de qualidade do [[ROADMAP]] atualizadas
- [ ] Dependências de dados críticas verificadas
- [ ] Versão do vault incrementada

---

## Controle de Versão de Outputs

Todo output importante deve ter versionamento explícito:

```
AAAA-MM-DD_[EMPRESA]_[TIPO]_v[N].md
```

Ao atualizar: criar **novo arquivo** com versão incrementada.
Nunca sobrescrever — mover versão anterior para `25_ARCHIVE/` se necessário.

---

## Versionamento de Premissas

Antes de alterar qualquer premissa de modelo:

1. Registrar versão anterior com data
2. Documentar motivo da mudança
3. Registrar quem/o que originou a revisão

Ver: [[18_DECISIONS]] para decisões que alteram premissas fundamentais.

---
*Última atualização: 2026-04-16*
