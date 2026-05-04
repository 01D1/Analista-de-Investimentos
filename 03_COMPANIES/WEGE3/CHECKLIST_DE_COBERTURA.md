---
title: WEGE3 — Checklist de Cobertura
tags:
  - empresa/WEGE3
  - checklist
  - cobertura
empresa: WEGE3
---

# Checklist de Cobertura — WEGE3

Baseado no [[10_WORKFLOWS/WORKFLOW_COBERTURA_DE_EMPRESA]].

---

## Etapa 1 — Estrutura ✓

- [x] Pasta `03_COMPANIES/WEGE3/` criada
- [x] `VISAO_GERAL.md` criado
- [x] `CHECKLIST_DE_COBERTURA.md` criado
- [x] Peers e setor identificados

## Etapa 2 — Pesquisa do Negócio ✓ (preliminar)

- [x] Modelo de negócio descrito
- [x] Segmentos operacionais mapeados
- [x] Drivers de receita identificados (5)
- [x] Riscos mapeados
- [x] Governança documentada
- [ ] Transcrições de conference call dos últimos 4 trimestres lidas

## Etapa 3 — Coleta de Documentos

- [x] DFP 2019–2025 baixados via `cvm_downloader.py` (dados CVM)
- [ ] ITRs dos últimos 8 trimestres baixados
- [ ] Releases dos últimos 8 trimestres baixados
- [ ] Formulário de Referência 2023 baixado

## Etapa 4 — Extração Financeira

- [x] DRE consolidada 2019–2025 extraída (7 anos)
- [x] BP consolidado 2019–2025 extraído (7 anos)
- [x] DFC consolidada 2019–2025 extraída (7 anos)
- [x] Metadados de extração preenchidos (via schemas Pydantic)
- [x] `DADOS_HISTORICOS.md` completo com 2019–2025

## Etapa 5 — Validação e Reconciliação

- [x] [[13_VALIDATION/CHECKLIST_EXTRACAO]] executado
- [x] [[13_VALIDATION/CHECKLIST_RECONCILIACAO]] executado para todos os anos
- [x] `reconciler.py` rodado: **0 erros críticos em todos os 7 anos**
- [x] 1 aviso estrutural por ano (esperado — DFC usa EBT como ponto de partida)
- [x] Padrões documentados em [[17_MEMORY/Padroes_identificados]]

## Etapa 6 — Base Histórica

- [x] Indicadores calculados (margens, ROE, ROA, dív/EBITDA, ciclo de caixa, FCFF)
- [x] Ciclo de capex mapeado (aceleração 2022–2025: 0,5 → 2,6 bi)
- [x] Eventos não recorrentes identificados (2021 estoques, 2025 dividendos)
- [x] `DADOS_HISTORICOS.md` completo

## Etapa 7 — Modelo

- [ ] Modelo 3-Statements construído
- [ ] Projeções de receita por driver
- [ ] Margens projetadas com justificativa
- [ ] [[13_VALIDATION/CHECKLIST_MODELAGEM]] executado

## Etapa 8 — Valuation Inicial

- [ ] DCF construído
- [ ] WACC calculado
- [ ] Sensibilidade executada
- [ ] Múltiplos comparáveis calculados
- [ ] `VALUATION_INICIAL.md` criado

## Etapa 9 — Tese

- [ ] `TESE_DE_INVESTIMENTO.md` criado
- [ ] Catalisadores (≥3) identificados
- [ ] Riscos da tese documentados
- [ ] Conclusão clara com preço-alvo e upside

## Etapa 10 — Integração ao Vault

- [ ] Empresa linkada em [[04_SECTORS/INDEX]]
- [ ] Aprendizados registrados em [[17_MEMORY]]
- [ ] Erros encontrados registrados em [[19_ERROR_LIBRARY/BIBLIOTECA_DE_ERROS]]

---

## Status Geral

**Progresso:** Etapas 1–6 concluídas | 2019–2025 completos | Etapas 7–10 pendentes

**Última execução do pipeline:** 2026-04-16 — 0 erros críticos em todos os 7 anos

**Prioridade:** Alta — empresa piloto do sistema

---
*Última atualização: 2026-04-16*
