# APP — Product Navigation Plan

**Data:** 2026-05-26  
**Status:** Implementado

---

## Estrutura de Navegação (Nova)

A navegação migrou de horizontal flat (11 itens em 1 linha) para **sidebar agrupada** com 4 grupos e 14 páginas.

### Por que sidebar?
- 14 páginas não cabem em nav horizontal sem quebrar layout
- Grupos semânticos melhoram onboarding para novos usuários
- Sidebar permite label completo (legível) sem truncar
- Padrão Streamlit multipage nativo — sem hacks de layout

---

## Grupos e Páginas

```
🎯 Decisão
├── 📡 Radar de Oportunidades   ← HOME — top sinais do dia
├── 🔬 Scanner Quantitativo     ← scores ranqueados por ativo
├── ⚡ Opções & Derivativos     ← posições, lifecycle, sinais de saída
├── 🏆 Matriz de Sinais         ← opportunity cards com tier/direção
└── 📈 Conviction Desk          ← equity curve, drawdown, Sharpe

🔭 Research
├── 🌐 Macro → B3               ← Selic, PTAX, IPCA, CDS, PIB
├── 🧠 Radar AI                 ← inteligência integrada por ativo
├── 🧩 Construtor de Tese       ← deep-dive single asset
├── 👁 Empresas Monitoradas     ← watchlist consolidada
└── 📅 Calendário Econômico     ← macro events + earnings

📊 Fundamentos
├── 💎 Valuation Hub            ← preços justos + base financeira
└── 🗺 Cobertura de Valuation   ← universo 32 empresas

⚙️ Técnico
├── 🔧 Diagnóstico Técnico      ← fontes, risco, snapshots, DB paths
└── 🤖 Pipeline & Agentes       ← agent runtime, pipeline graph
```

---

## Especificação: Radar de Oportunidades (Home Operacional)

### Propósito
Primeira página do app. Responde a pergunta: **"O que eu olho hoje?"**

### Campos exibidos hoje (dados reais)
| Campo | Fonte | Tipo |
|---|---|---|
| Ticker | `asset_intelligence_snapshots` | Texto |
| Tipo de ativo | Derivado de `signal_type` | Badge |
| Score de convicção | `integrated_score` | Número grande |
| Tier (S/A/B/C/D) | Derivado de `integrated_status` | Chip |
| Direção (BUY/WATCH/HOLD/SELL) | Derivado de `integrated_status` | Chip colorido |
| Sinal técnico | `technical_score_final` | Número |
| Score quant | `quant_score` | Número |
| Próxima ação | Derivado de score + direção + tier | Chip ação |
| Regime macro | `market_regime_engine.detect_regime()` | Banner |

### Campos em desenvolvimento (mostrados como "aguardando dados")
| Campo | Módulo fonte | Prioridade |
|---|---|---|
| Gatilho | `signal_explainer.py` | Alta |
| Liquidez (ADV) | `cotahist_daily` 21d avg | Alta |
| Assimetria | `expected_value_engine.py` | Alta |
| Valuation (preço justo validado) | `valuation_results` | Média |

### Próxima ação derivada (lógica atual)
| Condição | Ação |
|---|---|
| BUY + Tier S/A | Montar tese |
| BUY + Tier B | Estudar |
| WATCH | Aguardar gatilho |
| HOLD | Monitorar |
| SELL | Descartar |

---

## Especificação: Scanner Quantitativo

### Propósito
Responde: **"Qual é o score de cada ativo hoje?"**

### Dados exibidos
- Score integrado por ativo (ranqueado)
- Status de convicção
- Scores técnico, quant e qualidade de dados
- Regime de mercado vigente
- Contagem de candidatos de opções
- Saúde das fontes (resumo) → detalhes em Diagnóstico Técnico

---

## Especificação: Valuation Hub

### Propósito
Responde: **"Qual é o valor justo deste ativo?"**

### Organização das tabs (nova ordem)
1. **Visão Geral** — 9 preços justos auditados + 17 prontos para cálculo + 6 pendências
2. **Base Fundamentalista** — cobertura de dados por empresa
3. **Qualidade Fundamental** — scores de qualidade dos dados
4. **Contexto Macro** — Selic, PTAX, IPCA para WACC
5. **Simulação dos Modelos** — resultados de simulação (modo técnico)
6. **Valores Preliminares ⚠️** — valores em validação com disclaimer forte

### Regras de exibição para valores preliminares
| Situação | Label |
|---|---|
| Passou na checagem automática | "Preliminar — passou na checagem" |
| Sanity check pendente | "Preliminar — requer validação" |
| Distressed case | "Caso especial" |
| Upside > 200% | Flag "Upside > 2×" visível |
| Nenhum aprovado | Badge "Não aprovado" em todos |

### O que NÃO mostrar no Valuation Hub
- Nomes de milestones (`M015`, `M016`, `M018`)
- Caminhos de banco (`ingestion.db`, `valuation_financial_inputs`)
- Flags internas (`source=M018_CONTROLLED`, `write=False`, `approved_fair_value=NULL`)
- Upside extremo como oportunidade — apenas como flag de alerta

---

## Regras de produto para toda a UI

### Nunca exibir
- Nomes de arquivos de banco de dados
- Referências a milestones (M014, M015, M016, M017, M018)
- Flags internas de sistema (`write=False`, `approved_fair_value`)
- JSON bruto
- HTML não estilizado
- Logs de pipeline
- Caminhos absolutos do filesystem
- `source=M018_CONTROLLED` ou strings similares

### Sempre exibir
- Status em português produto
- Disclaimers claros quando dados são preliminares ou em validação
- Empty states honestos quando não há dados
- "Em desenvolvimento" quando campo existe no design mas dados não chegaram

### Página de destino para informações técnicas
→ **Diagnóstico Técnico** (`diagnostico_tecnico.py`) é o único lugar onde:
- Caminhos de banco são mostrados
- `source_name` de fontes é exibido literalmente
- Snapshots brutos de `asset_intelligence_snapshots` são visíveis
- VaR, ES, `limiting_factor` aparecem com detalhes técnicos

---

## Status de Implementação

| Item | Status |
|---|---|
| Sidebar agrupada com 4 grupos | ✅ Implementado |
| Radar de Oportunidades (home) | ✅ Implementado |
| Diagnóstico Técnico | ✅ Implementado |
| Watchlist na navegação | ✅ Implementado |
| Referências técnicas removidas do Valuation | ✅ Implementado |
| Tab order do Valuation Hub corrigido | ✅ Implementado |
| Subtítulo do Scanner Quantitativo corrigido | ✅ Implementado |
| Logo no sidebar | ✅ Implementado |
| CSS de sidebar personalizado | ✅ Implementado |
| Radar de opções expandido | ⏳ Próximo sprint |
| Expected value integrado | ⏳ Próximo sprint |
| Gauge chart de score | ⏳ Próximo sprint |
