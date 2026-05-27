# Design System Inventory

**Data:** 2026-05-26

---

## 1. Localização e Tecnologia

| Pasta | Tecnologia | Tipo |
|---|---|---|
| `radar-macro-design-system/project/` | HTML/CSS/JS | Protótipos estáticos (Claude Design export) |
| `src/ui/styles.py` | Python + CSS-in-string | Streamlit runtime — fonte canônica para o app |
| `src/ui/components.py` | Python (Streamlit) | Componentes funcionais para as páginas |
| `src/ui/design_tokens.css` | CSS custom properties | Tokens de design (carregado em styles.py) |

---

## 2. Inventário — radar-macro-design-system/project/

### Arquivos de tokens / base
| Arquivo | Função |
|---|---|
| `colors_and_type.css` | Tokens completos de cor, tipografia, espaçamento, sombras, motion |
| `_base.css` | Reset e base layout |
| `preview/` | 24 HTML estáticos de cards e componentes |

### Componentes documentados (preview/)
| Componente | Arquivo HTML | Função Visual |
|---|---|---|
| Badge (posicionamento) | `comp-badges-positioning.html` | Chips de status/direção |
| Botões | `comp-buttons.html` | CTAs primário/secundário |
| Driver/Risco | `comp-driver-risk.html` | Cards de driver e risco |
| Hero | `comp-hero.html` | Hero section com ticker + score |
| Inputs | `comp-inputs.html` | Campos de formulário |
| KPI Strip | `comp-kpi-strip.html` | Faixa de métricas numéricas |
| Opportunity Card | `comp-opportunity-card.html` | Card de oportunidade ranqueada |
| Score Bars | `comp-score-bars.html` | Barras de score numérico |
| Section Title | `comp-section-title.html` | Cabeçalho de seção |
| Watchlist Card | `comp-watchlist-card.html` | Card de ativo monitorado |
| Cores de superficie | `colors-surface.html` | Paleta bg-0 → bg-elevated |
| Cores de texto | `colors-text.html` | Paleta fg-1 → fg-6 |
| Cores semânticas | `colors-semantic-other.html` | pos/neg/warn/brand |
| Cores de marca | `colors-brand.html` | Brand 300→700 |
| Tipografia display | `type-display.html` | Sora — headlines |
| Tipografia mono | `type-mono.html` | JetBrains Mono — dados |
| Tipografia body | `type-body.html` | Inter — texto |
| Tipografia eyebrow | `type-eyebrow.html` | Labels uppercase |
| Espaçamento | `spacing-scale.html` | 4-128px scale |
| Raios | `spacing-radius.html` | r-sm → r-2xl |
| Elevação | `spacing-elevation.html` | shadow-1 → shadow-5 |
| Motion | `spacing-motion.html` | Easing curves |

### UI Kit (dashboard)
| Arquivo | Tipo |
|---|---|
| `ui_kits/dashboard/index.html` | Protótipo interativo click-through completo |
| `ui_kits/dashboard/*.jsx` | Componentes React-style (design fictício, não produção) |

---

## 3. Implementação Streamlit (fonte canônica)

### src/ui/design_tokens.css → carregado em PREMIUM_CSS
Contém todas as custom properties usadas pelos componentes:
- Paleta: `--bg-0` a `--bg-elevated`, `--fg-1` a `--fg-6`
- Semântica: `--pos-500`, `--neg-500`, `--warn-500`, `--brand-300`-`700`
- Tipografia: `--font-display` (Sora), `--font-mono` (JetBrains Mono), `--font-body` (Inter)
- Raios: `--r-sm`, `--r-md`, `--r-xl`, `--r-2xl`, `--r-pill`
- Sombras: `--shadow-1` a `--shadow-5`

### src/ui/components.py — Componentes funcionais disponíveis
| Função | Uso |
|---|---|
| `section_title(title, subtitle, icon)` | Cabeçalho de seção |
| `kpi_card(label, value, delta, color, sub)` | Card de métrica individual |
| `kpi_strip(items)` | Faixa de múltiplos KPIs |
| `hero_section(...)` | Hero ticker/nome/score |
| `opportunity_card(ticker, description, signal_type, conviction_score)` | Card de oportunidade |
| `watchlist_card(ticker, nome, score, upside, positioning, setor)` | Card de watchlist |
| `status_chip(status, label)` | Chip colorido de status |
| `positioning_badge(direction)` | Badge BUY/HOLD/SELL |
| `alert_block(variant, title, body)` | Bloco de alerta contextual |
| `empty_state(message, icon)` | Estado vazio honesto |
| `score_bar(score, label, max_score)` | Barra de score |
| `metric_card(label, value, ...)` | Card métrica compacta |
| `metric_table_row(...)` | Linha de tabela de métricas |

---

## 4. Matriz: Design System → Streamlit

| Componente Design | Implementado em Streamlit? | Como |
|---|---|---|
| Opportunity Card | ✅ Sim | `components.opportunity_card()` |
| Watchlist Card | ✅ Sim | `components.watchlist_card()` |
| KPI Strip | ✅ Sim | `components.kpi_strip()` |
| Hero Section | ✅ Sim | `components.hero_section()` |
| Status Chip | ✅ Sim | `components.status_chip()` |
| Score Bars | ✅ Sim | `components.score_bar()` |
| Alert Block | ✅ Sim | `components.alert_block()` |
| Section Title | ✅ Sim | `components.section_title()` |
| Driver/Risk Card | ⚠️ Parcial | Renderizado inline com HTML nos pages |
| Tabela de dados | ⚠️ Misto | `st.dataframe` (nativo) + tabelas HTML inline |
| Sidebar nav grupos | ✅ Sim | `st.navigation({groups}, position="sidebar")` |
| Gráficos macro | ✅ Sim | `plotly.graph_objects` com tema dark |
| Radar chart (score) | ❌ Não portado | Existe no design kit, não no Streamlit |
| Gauge de convicção | ❌ Não portado | Existe no design kit, não no Streamlit |

---

## 5. Recomendação de Abordagem

**Manter Streamlit + portar design incrementalmente.**

Razões:
1. O design system HTML é um protótipo de referência, não código de produção
2. Os tokens CSS (`design_tokens.css`) já estão sincronizados com o design system
3. Os componentes críticos (cards, badges, KPIs, tabelas) já existem em `components.py`
4. Uma migração para React/Next adicionaria complexidade sem ganho de produto imediato

**Componentes prioritários para portar nos próximos sprints:**
- Radar chart de scores (score_gauge do design kit → Plotly radar chart)
- Tabelas HTML inline → substituir por `st.dataframe` styled onde possível
- Sidebar logo section (já implementado no novo `app.py`)

---

## 6. Design Tokens em Uso — Mapeamento de Cor

| Variável | Valor Hex | Uso |
|---|---|---|
| `--bg-0` | `#080D17` | Background base app |
| `--bg-2` | `#0F1A2A` | Painéis secundários |
| `--bg-3` | `#111827` | Cards e componentes |
| `--brand-300` | `#22D3EE` | Cyan — accent principal |
| `--pos-500` | `#22C55E` | Verde — positivo/buy |
| `--neg-500` | `#EF4444` | Vermelho — negativo/sell |
| `--warn-500` | `#F59E0B` | Âmbar — atenção/watch |
| `--fg-1` | `#F1F5F9` | Texto principal |
| `--fg-5` | `#475569` | Texto secundário/labels |
| `--fg-6` | `#334155` | Texto terciário/placeholders |
