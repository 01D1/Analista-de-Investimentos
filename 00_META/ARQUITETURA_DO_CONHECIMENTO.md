---
title: Arquitetura do Conhecimento
tags:
  - meta
  - arquitetura
  - design
aliases:
  - Arquitetura
  - Mapa do Vault
---

# Arquitetura do Conhecimento

Este documento descreve como o conhecimento está organizado, como as partes se relacionam e como o sistema deve ser navegado.

---

## Síntese do Fluxo

```
ENTRADA                    PROCESSAMENTO              SAÍDA
──────────                 ──────────────             ────
Documentos financeiros  →  Extração + Validação  →   Dados estruturados
Dados estruturados      →  Modelagem + Valuation →   Análise financeira
Análise financeira      →  Síntese + Revisão     →   Research / Tese
Research / Tese         →  Aprendizado           →   Memória do sistema
```

---

## As 5 Camadas

### Camada 1 — Conhecimento
Onde o **saber** é armazenado e organizado.

- [[00_META]] — identidade e governança do vault
- [[04_SECTORS]] — inteligência setorial
- [[05_DATA_SOURCES]] — inventário de fontes
- [[16_GLOSSARY]] — vocabulário comum
- [[17_MEMORY]] — heurísticas e padrões aprendidos

### Camada 2 — Dados
Onde os **fatos** são coletados, limpos e estruturados.

- [[12_PYTHON]] — código de ingestão, parsing, ETL
- [[05_DATA_SOURCES]] — manual de cada fonte
- [[13_VALIDATION]] — regras de qualidade

### Camada 3 — Modelagem
Onde os dados viram **modelos analíticos**.

- [[06_MODELS]] — biblioteca de modelos financeiros
- [[07_VALUATION]] — metodologias de valuation
- [[03_COMPANIES]] — modelos por empresa

### Camada 4 — Inteligência
Onde modelos viram **insights e raciocínios**.

- [[09_SKILLS]] — capacidades analíticas documentadas
- [[11_PROMPTS]] — instruções para agentes
- [[08_RESEARCH]] — notas de pesquisa e teses
- [[17_MEMORY]] — padrões identificados

### Camada 5 — Entrega
Onde insights viram **outputs de valor**.

- [[14_OUTPUTS]] — entregáveis produzidos
- [[22_DASHBOARDS]] — visualizações
- [[15_TEMPLATES]] — modelos reutilizáveis

---

## Hierarquia de Confiabilidade

```
Fato documentado (fonte primária)          ← máxima confiança
Fato inferido (fonte secundária)           ← alta confiança
Premissa explícita (racional registrado)   ← confiança controlada
Estimativa orientada (benchmark/setor)     ← confiança moderada
Hipótese investigativa                     ← baixa confiança, sinalizada
```

> [!warning] Nunca tratar premissa como fato. Sempre sinalizar o nível de confiança.

---

## Ontologia Principal

### Entidades Centrais

- **Empresa** → tem Segmentos, Drivers, Riscos, Demonstrativos, Modelo, Valuation, Tese
- **Setor** → tem Dinâmica, Métricas, Peers, Riscos estruturais
- **Fonte** → tem Tipo, Frequência, Formato, Confiabilidade, Parser
- **Modelo** → tem Inputs, Outputs, Premissas, Versão
- **Skill** → tem Objetivo, Processo, Entradas, Saídas, Critérios de qualidade
- **Workflow** → tem Passos, Dependências, Entregável, Responsável

### Relações Fundamentais

- Empresa `pertence_a` Setor
- Empresa `tem_dados_em` Fonte
- Empresa `avaliada_por` Modelo + Valuation
- Modelo `usa` Skills + Dados
- Valuation `depende_de` Premissas + WACC + Projeções
- Output `documenta` Empresa + Valuation + Fontes

---

## Ciclo de Vida de uma Nota

```
Rascunho → Em revisão → Validado → Publicado → Arquivado
```

Notas validadas ficam em suas pastas definitivas.
Notas arquivadas vão para [[25_ARCHIVE]].

---

## Links Relacionados

- [[README_GERAL]]
- [[MISSAO]]
- [[PRINCIPIOS]]
- [[01_OPERATING_SYSTEM/SISTEMA_DE_NOTAS]]

---
*Última atualização: 2026-04-16*
