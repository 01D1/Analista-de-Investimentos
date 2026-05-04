---
title: Estrutura Societária
tags:
  - governança
  - estrutura-societária
  - controle
aliases:
  - Estrutura Societária
---

# Estrutura Societária — Análise de Controle e Propriedade

> Mapeamento da estrutura de controle e propriedade das empresas analisadas. Entender quem controla, como e com qual exposição econômica.

---

## Por que Importa

A estrutura societária determina:
1. Quem toma as decisões estratégicas finais
2. Quais são os incentivos do controlador
3. Qual a proteção real do acionista minoritário
4. Em quanto tempo e a que custo é possível contestar o controle

---

## Tipos de Estrutura de Controle

### 1. Controle Familiar Direto
**Descrição:** Uma família detém diretamente ≥ 50% das ações ON.  
**Exemplos B3:** WEG (família Werner), Itaúsa/Itaú (Egydio Souza Aranha), Magazine Luiza (família Magalhães).  
**Vantagens:** Visão de longo prazo, alinhamento de interesse, agilidade decisória.  
**Riscos:** Conflitos de sucessão, burocracia familiar, nepotismo, divergência gerações.

### 2. Controle via Holding
**Descrição:** Família ou grupo controla holding que por sua vez controla a empresa listada.  
**Exemplos B3:** Itaúsa → Itaú Unibanco; Bradespar → Bradesco.  
**Risco específico:** Alavancagem na holding pode forçar decisões na operacional. Desconto de holding é estrutural.

### 3. Controle Estatal
**Descrição:** União, Estado ou Município detém controle.  
**Exemplos B3:** Petrobras (União), Banco do Brasil (União), Cemig (Governo MG).  
**Riscos:** Interferência política, dividendos políticos, objetivo duplo (social + lucrativo).  
**Oportunidade:** Desconto estrutural que pode ser capturado com mudança política.

### 4. Controle Disperso (Tag Along de Fato)
**Descrição:** Nenhum acionista com > 20% — controle de fato com gestores ou grandes fundos.  
**Exemplos B3:** Ambev (controlada pela InBev, mas disperso no Brasil).  
**Riscos:** Menor accountability. Gestores podem agir por interesse próprio sem contestação.

### 5. Controle por Acordo de Acionistas
**Descrição:** Grupo de acionistas minoritários individualmente que se unem para exercer controle.  
**Exemplos B3:** Embraer (acordo Estado + fundos), JBS (família Batista + fundos).  
**Risco:** Instabilidade do controle quando o acordo é dissolvido.

---

## Estrutura de Classes de Ações no Brasil

### Ações Ordinárias (ON)
- Direito a voto integral nas assembleias
- Dividendo mínimo de 25% do lucro ajustado (mínimo legal)
- Tag along obrigatório de 80% para Novo Mercado+ = 100%

### Ações Preferenciais (PN)
- Sem direito a voto (ou com restrições)
- Dividendo preferencial ≥ dividendo das ON (regra geral)
- Tag along: mínimo legal = 0% para PN sem voto; Novo Mercado = proibido (só ON)
- Histórico: criadas para separar controle de capital. Novo Mercado eliminou (2001+).

### Regras de Listagem B3

| Segmento | Tipo de ação | Tag Along | Free float mínimo |
|---|---|---|---|
| Básico (tradicional) | ON + PN | 80% ON, 0% PN | N/D |
| Nível 1 | ON + PN | 80% ON, 0% PN | 25% |
| Nível 2 | ON + PN | 100% ON + PN | 25% |
| Novo Mercado | Só ON | 100% | 25% |
| Bovespa Mais | Só ON | 100% | 25% |

---

## Como Mapear a Estrutura Societária

### Passo 1 — Identificar o acionista controlador
**Fonte:** Formulário de Referência, seção 15.1 (Controle)
- Nome do controlador direto e indireto
- % capital e % voto

### Passo 2 — Traçar a cadeia de controle
Se o controlador é uma holding, mapear até a pessoa física final (UBO — Ultimate Beneficial Owner).

```
Exemplo WEG:
[Família Werner/Hess/Peretti] → [Fundação Werner, Hess e Peretti]
→ detem ~32% capital + controle via acordo → WEG S.A. (WEGE3)
```

### Passo 3 — Calcular a exposição econômica vs. poder de controle
```
Razão Controle = % Votos / % Capital
Se Razão > 2x: controlador tem poder desproporcionalmente grande
Se Razão ≈ 1x: alinhamento vote/capital — melhor para minoritários
```

### Passo 4 — Identificar acordos de acionistas
**Fonte:** FR seção 15.5, atas de AGO, comunicados CVM.
- Quem são as partes do acordo?
- Quais são as cláusulas (votar em bloco, direito de preferência, lock-up)?
- Por quanto tempo está vigente?

---

## Template de Mapeamento Societário

```
Empresa: ___________________  Ticker: _______  Data: ___________

ESTRUTURA DE CONTROLE
─────────────────────
Controlador final (UBO): _______________
Tipo de controle: [ ] Familiar  [ ] Estatal  [ ] Disperso  [ ] Acordo

Cadeia de controle:
  [Pessoa/Família/Estado]
  ─ detem ___% capital e ___% votos em →
  [Holding/Veículo intermediário] (se houver)
  ─ detem ___% capital e ___% votos em →
  [Empresa Listada]

ESTRUTURA ACIONÁRIA
──────────────────
| Acionista | % Capital | % Votos | Tipo |
|-----------|-----------|---------|------|
| Controlador | | | |
| Acionistas institucionais | | | |
| Free float | | | |

Razão controle (votos/capital controlador): ___x

PROTEÇÃO DO MINORITÁRIO
──────────────────────
Free float: ___%
Segmento de listagem: _______________
Tag along ON: ___%   PN: ___%
Poison pill: SIM / NÃO  (gatilho: ___%))
Acordo de acionistas: SIM / NÃO

AVALIAÇÃO
─────────
Score estrutura societária (1–10): ___
Principais riscos: ___
Mitigantes: ___
```

---

## Empresas Cobertas — Resumo de Estrutura

| Ticker | Controlador | % Capital | % Votos | Razão | Segmento |
|---|---|---|---|---|---|
| WEGE3 | Família fundadora | ~32% | ~32% | ~1x | Novo Mercado |
| ITUB4 | Itaúsa (família Souza Aranha) | ~37% | ~53% | ~1.4x | Nível 1 |
| BBAS3 | União Federal | ~50% | ~50% | ~1x | Novo Mercado |
| BBDC4 | Fundação Bradesco (família) | ~28% | ~56% | ~2x | Nível 1 |
| SANB11 | Banco Santander S.A. (Espanha) | ~89% | ~89% | ~1x | Nível 2 |
| BPAC11 | Família Esteves | ~30% | ~73% | ~2.4x | Novo Mercado |
| ITSA4 | Família Souza Aranha (via holdings) | ~41% | ~41% | ~1x | Nível 1 |
| INTR4 | SoftBank + família Menin | ~34% | ~34% | ~1x | Nasdaq (dual list) |
| BRSR6 | Governo Rio Grande do Sul | ~57% | ~57% | ~1x | Nível 1 |
| ABCB4 | Banco ABC Brasil (saiu B3 2024) | — | — | — | Fechou capital |
| BMGB4 | Família Pentagna Guimarães | ~54% | ~54% | ~1x | Básico |
| BPAN4 | BTG Pactual | ~31% | ~31% | ~1x | Nível 1 |
| PINE4 | Família Pentagna Guimarães | ~34% | ~51% | ~1.5x | Básico |

> Dados aproximados. Verificar FR mais recente para posições atualizadas.

---

## Links Cruzados

- [[FRAMEWORK_GERAL_DE_GOVERNANCA]] — Metodologia
- [[PARTES_RELACIONADAS]] — Transações com controladores
- [[DIREITOS_DO_MINORITARIO]] — Proteção legal
- [[ALOCACAO_DE_CAPITAL]] — Como o controlador usa o caixa

---
*Última atualização: 2026-04-16*
