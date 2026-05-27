# APP — Backend × Frontend × Design System: Auditoria de Integração

**Data:** 2026-05-26

---

## 1. Mapa Backend → Frontend

### Módulos de inteligência e suas integrações

| Dado / Inteligência | Origem | Página atual | Componente visual | Status | Correção necessária |
|---|---|---|---|---|---|
| Score de Convicção Integrado | `asset_intelligence_snapshots.integrated_score` | `radar_quant.py`, `radar_ai.py`, `inteligencia_oportunidades.py` | Score card, KPI | ✅ Integrado | — |
| Direção (BUY/WATCH/SELL) | Derivado de `integrated_status` em `data.py` | `inteligencia_oportunidades.py` | Tier chip, direction chip | ✅ Integrado | — |
| Market Regime | `market_regime_engine.detect_regime()` | `inteligencia_oportunidades.py` (regime banner) | Banner macro | ✅ Integrado | — |
| Signal Explainer | `signal_explainer.explain_html()` | `inteligencia_oportunidades.py` (expander) | HTML expandido | ✅ Integrado | — |
| Institutional Meta Score | `institutional_meta_score.py` | `inteligencia_oportunidades.py` (via `data.py`) | Score numérico | ⚠️ Parcial | Integrar `institutional_meta_score` diretamente ao payload |
| Expected Value (opções) | `expected_value_engine.py` | — Nenhuma página consome | Card de assimetria | ❌ Não integrado | Adicionar ao `get_opportunities()` ou `radar_oportunidades.py` |
| Watchlist Summary | `data.get_watchlist_summary()` | `radar_ai.py`, `inteligencia_watchlist.py` | Watchlist cards | ✅ Integrado | — |
| Asset Detail | `data.get_asset_detail()` | `radar_ai.py`, `inteligencia_ativo.py` | Hero + drivers + riscos | ✅ Integrado | — |
| Risk Snapshots | `data.get_risk_snapshots()` | `radar_ai.py`, `diagnostico_tecnico.py` | Risco card | ✅ Integrado | Diagnóstico técnico — OK |
| Option Structure Candidates | `option_structure_candidates` table | `radar_quant.py` (count), `opcoes_monitoramento.py` | KPI count, tabela | ⚠️ Parcial | Expandir no Radar de Oportunidades |
| Market Regime Daily | `market_regime_daily` table | `radar_quant.py`, `diagnostico_tecnico.py` | Regime panel | ✅ Integrado | — |
| Macro Series (Selic, PTAX, etc.) | `macro_series` table | `inteligencia_macro.py` | Plotly charts | ✅ Integrado | — |
| Valuation (preços preservados) | Hardcoded em `valuation_engine.py` | `valuation_engine.py`, `valuation_coverage.py` | WL cards | ✅ Integrado | — |
| Valuation Preliminar (M018) | `valuation_results` table | `valuation_engine.py` (Tab 6) | Tabela com disclaimer | ✅ Integrado | Rebaixado para última tab |
| Financial Inputs | `valuation_financial_inputs` table | `valuation_engine.py` (Tab 2) | KPI strip + coverage | ✅ Integrado | Linguagem simplificada |
| Technical Scores | `asset_intelligence_snapshots` | `radar_quant.py`, `radar_ai.py` | Score rows | ✅ Integrado | — |
| Source Health | `source_health_checks` table | `diagnostico_tecnico.py` | Health chips | ✅ Integrado (movido) | — |
| CVM / RI Coverage | `data_quality.ri_sites` | `inteligencia_ativo.py` | Link RI na tese | ✅ Integrado | — |
| News / Boletins | `news_connector.py` | `radar_ai.py` | News cards | ⚠️ Parcial | Depende de news_hunter.db fresh data |

---

## 2. Módulos não integrados ao frontend

### expected_value_engine.py
- **O que entrega:** Expected value probabilístico para opções — probabilidade × payoff
- **Pergunta que responde:** "Qual é a assimetria risco/retorno desta operação?"
- **Página atual:** Nenhuma
- **Componente ideal:** Card de assimetria no Radar de Oportunidades
- **O que falta:** Integrar ao `get_opportunities()` ou adicionar loader no `radar_oportunidades.py`

### options_universe_expansion.py (scanners)
- **O que entrega:** Expansão do universo de opções B3 — candidatos por critério
- **Pergunta que responde:** "Quais opções têm sinal técnico + estrutura favorável?"
- **Página atual:** Parcialmente em `opcoes_monitoramento.py` (posições abertas)
- **Componente ideal:** Tabela ranqueada em Opções & Derivativos
- **O que falta:** Conectar ao scanner de opções mais amplo

### institutional_meta_score.py
- **O que entrega:** Score consolidado combinando todos os sinais
- **Pergunta que responde:** "Qual é a convicção institucional total neste ativo?"
- **Página atual:** Usado via `data.py` indiretamente, mas sem chamada direta ao módulo
- **O que falta:** Mapear se `integrated_score` já incorpora o meta score ou se são separados

---

## 3. Integridade das Páginas

### Páginas funcionais (dados reais, renderização OK)
| Página | Dados reais? | Renderização | Issues conhecidos |
|---|---|---|---|
| `radar_oportunidades.py` (nova) | ✅ Sim | ✅ Streamlit nativo + HTML inline | Faltam: gatilho, liquidez, assimetria |
| `inteligencia_oportunidades.py` | ✅ Sim | ✅ HTML inline com CSS | Funciona bem |
| `radar_ai.py` | ✅ Sim | ✅ HTML + st.dataframe | Funciona |
| `inteligencia_macro.py` | ✅ Sim | ✅ Plotly dark theme | Só mostra se BCB data disponível |
| `inteligencia_ativo.py` | ✅ Sim | ✅ HTML inline | Funciona |
| `inteligencia_watchlist.py` | ✅ Sim | ✅ HTML inline | Funciona |
| `valuation_engine.py` | ✅ Sim | ✅ HTML + st.html | Tab 6 com disclaimer forte |
| `valuation_coverage.py` | ✅ Sim | ✅ HTML + st.dataframe | Funciona |
| `opcoes_monitoramento.py` | ✅ Sim | ✅ HTML inline | Requer posições abertas |
| `radar_quant.py` | ✅ Sim | ✅ HTML inline | Renomeado Scanner Quantitativo |
| `performance.py` | ✅ Sim | ✅ Plotly + HTML | Requer journal entries |
| `calendario.py` | ✅ Sim | ✅ HTML/Streamlit | Funciona |
| `agendador.py` | ✅ Sim | ✅ HTML | Movido para Técnico |
| `diagnostico_tecnico.py` (nova) | ✅ Sim | ✅ HTML + st.dataframe | Nova página técnica |

---

## 4. Recomendação de Abordagem

**Manter Streamlit + Design System Streamlit-nativo.**

### Justificativa
| Alternativa | Prós | Contras |
|---|---|---|
| Manter Streamlit | Zero esforço de infraestrutura; design system já implementado em Python; deploy simples | Limitações de interatividade avançada |
| Migrar para React/Next | Flexibilidade total; design system HTML portável | Semanas de trabalho; backend API necessário; operação dobrada |
| Abordagem híbrida (Streamlit + React embed) | Melhor dos dois mundos pontualmente | Complexidade de integração; maintainability ruim |

**Conclusão:** Streamlit resolve 95% dos casos de uso. A interface atual precisa de produto, não de tecnologia nova.

---

## 5. Plano de Implementação Incremental

| Slice | Descrição | Status |
|---|---|---|
| **S01** — Design System Audit | Inventário de tokens, componentes, prototipagem | ✅ Concluído (este documento) |
| **S02** — Backend Intelligence Map | Mapeamento de módulos → páginas | ✅ Concluído (este documento) |
| **S03** — Navigation/Product IA | Sidebar agrupada, nova ordem de páginas | ✅ Executado |
| **S04** — Radar de Oportunidades MVP | Home operacional com sinais existentes | ✅ Executado |
| **S05** — Portar componentes visuais | Gauge, radar chart, tabelas → Streamlit nativo | ⏳ Próximo |
| **S06** — Limpar páginas técnicas | Diagnóstico técnico isolado, poluição removida | ✅ Executado |
| **S07** — Integração final Valuation Hub | Valores aprovados, upside real, disclaimer refinado | ⏳ Aguarda aprovação de valuations |
| **S08** — Expected Value no Radar | Integrar `expected_value_engine.py` ao Radar de Oportunidades | ⏳ Próximo |
| **S09** — Liquidez e ADV | Volume diário de `cotahist_daily` no payload | ⏳ Próximo |

---

## 6. Dados Críticos Ausentes

Para completar a experiência de produto, os seguintes dados precisam ser conectados:

| Campo | Módulo existente | Ação necessária |
|---|---|---|
| Expected Value / Assimetria | `src/quant/expected_value_engine.py` | Integrar no payload de `get_opportunities()` |
| Liquidez ADV | `cotahist_daily` (já no banco) | Calcular rolling 21d volume médio |
| Gatilho técnico | `src/quant/signal_explainer.py` | Extrair nível técnico do `explain_html()` |
| Fair value aprovado | `valuation_results` | Aprovar ao menos 1 valor via validação |
| Score institucional explícito | `src/quant/institutional_meta_score.py` | Verificar se já está em `integrated_score` |
