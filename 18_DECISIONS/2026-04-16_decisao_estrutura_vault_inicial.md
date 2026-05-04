---
title: "Decisão: Estrutura Inicial do Vault"
tags:
  - decisão
  - vault
  - arquitetura
date: 2026-04-16
status: Ativa
---

# Decisão: Estrutura Inicial do Vault de Inteligência Financeira

**Data:** 2026-04-16
**Status:** Ativa

---

## Contexto

Necessidade de criar um sistema de conhecimento organizado para suportar modelagem financeira, valuation e pesquisa de empresas automatizada com Python e agentes de IA. O sistema precisava funcionar tanto para operadores humanos quanto como base de conhecimento para agentes.

---

## Decisão

Adotar uma estrutura de vault com 26 pastas numeradas (00–25), cada uma com responsabilidade clara, seguindo os princípios de: separação entre dado/premissa/interpretação, reprodutibilidade, modularidade e evolução contínua.

---

## Alternativas Consideradas

1. **Estrutura flat (sem subpastas)** — descartada por falta de escalabilidade com cobertura de múltiplas empresas
2. **Estrutura por tipo de nota apenas** — descartada por não refletir os domínios funcionais do projeto
3. **Wiki simples** — descartada por não suportar skills, workflows e prompts estruturados

---

## Motivação

A estrutura numerada permite:
- Ordenação visual consistente no Obsidian
- Adição de novas pastas sem reorganização
- Separação clara entre camadas (conhecimento, dados, modelagem, inteligência, entrega)

---

## Impacto Esperado

- Navegação intuitiva para humanos e agentes
- Skills e workflows reutilizáveis
- Base para automação Python integrada ao vault

---

## Riscos

- Estrutura pode se tornar rígida se o projeto evoluir para áreas não previstas
- Nomenclatura em português pode complicar integração com ferramentas em inglês

## Revisão

Revisar após cobrir as primeiras 5 empresas e executar os primeiros workflows completos.

---
