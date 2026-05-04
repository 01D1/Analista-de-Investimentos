---
title: Roadmap do Projeto
tags:
  - meta
  - roadmap
  - planejamento
aliases:
  - Roadmap
  - Plano
---

# Roadmap — Plataforma de Inteligência Financeira

## Fase 1 — Fundação (Conhecimento e Estrutura)

**Objetivo:** estabelecer a base do vault e os primeiros fluxos funcionais.

- [x] Criar estrutura de pastas do vault
- [x] Documentar missão, princípios e arquitetura
- [ ] Mapear fontes de dados prioritárias ([[05_DATA_SOURCES]])
- [ ] Criar glossário base ([[16_GLOSSARY]])
- [ ] Documentar padrão de nomenclatura ([[01_OPERATING_SYSTEM/PADRAO_DE_NOMENCLATURA]])
- [ ] Criar templates essenciais ([[15_TEMPLATES]])
- [ ] Montar biblioteca inicial de skills ([[09_SKILLS]])

---

## Fase 2 — Dados (Coleta e Normalização)

**Objetivo:** ter pipeline funcional de coleta e estruturação de dados.

- [ ] Parser de DFP/ITR da CVM
- [ ] Parser de release trimestral (PDF/HTML)
- [ ] Schema unificado de demonstrativos
- [ ] Camada de normalização de contas
- [ ] Reconciliação automática DRE/BP/DFC
- [ ] Armazenamento estruturado (DuckDB/Parquet)
- [ ] Logging e rastreabilidade de pipeline

---

## Fase 3 — Modelagem (Análise Estruturada)

**Objetivo:** produzir modelos financeiros confiáveis e reproduzíveis.

- [ ] Modelo 3-Statements base
- [ ] Cálculo automatizado de indicadores-chave
- [ ] Motor de DCF parametrizável
- [ ] Módulo de comparáveis e múltiplos
- [ ] Sensibilidade e cenários
- [ ] Cobertura inicial de 5 empresas piloto

---

## Fase 4 — Inteligência (Agentes e Heurísticas)

**Objetivo:** automatizar raciocínios analíticos repetíveis.

- [ ] Agente pesquisador de empresa
- [ ] Agente extrator financeiro
- [ ] Agente auditor de dados
- [ ] Agente construtor de valuation
- [ ] Agente redator de research
- [ ] Heurísticas de detecção de inconsistência

---

## Fase 5 — Entrega (Outputs Institucionais)

**Objetivo:** produzir outputs de alta qualidade de forma escalável.

- [ ] Template de relatório executivo
- [ ] Dashboard individual por empresa
- [ ] Dashboard setorial comparativo
- [ ] Sistema de atualização trimestral automatizado
- [ ] Export de research em Markdown/PDF

---

## Backlog de Evolução

Ver: [[21_BACKLOG/BACKLOG_GERAL]]

---

## Métricas de Maturidade

| Métrica | Alvo |
|---|---|
| Empresas com cobertura completa | ≥ 10 |
| % de dados reconciliados | ≥ 95% |
| Tempo para atualizar um trimestre | < 1 hora |
| Erros por pipeline | 0 bloqueantes |
| % de outputs reproduzíveis | 100% |
| % de premissas versionadas | 100% |

---

## Links Relacionados

- [[MISSAO]]
- [[ARQUITETURA_DO_CONHECIMENTO]]
- [[21_BACKLOG/BACKLOG_GERAL]]

---
*Última atualização: 2026-04-16*
