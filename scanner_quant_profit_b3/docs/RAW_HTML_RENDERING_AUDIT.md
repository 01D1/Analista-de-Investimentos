# RAW HTML Rendering Audit — STREAMLIT-RAW-HTML-ROOT-CAUSE

## Causa Raiz Identificada

### 🔴 CRÍTICO — `st.html()` com tabelas HTML completas

Ambas `valuation_engine.py` e `valuation_coverage.py` usam `st.html()` com HTML tables que contêm `<style>` blocks:

```python
tbl1_html = f"""
<style>
.tbl-wrap { border: 2px solid red; }
.tbl {{width:100%;border-collapse:collapse;font-size:.72rem;}}
...
</style>
<div class="tbl-wrap">
<table class="tbl">...<tr><td>...</td></tr>...</table>
</div>
"""
st.html(tbl1_html)
```

**O que acontece (Streamlit 1.45.1):**
1. Streamlit detecta `<style>` tag → CSS vai para event container (não renderiza)
2. O `<div>` + `<table>` vai para o main content container
3. O CSS **não é aplicados** à tabela → estilo quebrado
4. DOMPurify sanitiza o HTML → remove style tags do div-content
5. **Resultado visível:** `<div class="tbl-wrap">` ou `<table>` ou `<td>` aparece como TEXTO BRUTO na tela

**Arquivos afetados:**
- `pages/valuation_engine.py`: linhas 411 (`tbl1_html`), 733 (`tbl2_html`), 875 (`tbl3_html`), 1002 (`tbl4_html`)
- `pages/valuation_coverage.py`: linhas 508 (`html_table`), 609 (`html_table2`), 698 (`html_table3`)

### 🟠 ALTO — `st.markdown()` com divs HTML completas

`pages/valuation_engine.py` e `pages/valuation_coverage.py` usam `st.markdown()` com HTML de painel completo:

```python
st.markdown("""
<div class="panel" style="margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;...">...</div>
</div>
""", unsafe_allow_html=True)
```

**O que acontece:**
1. Streamlit processa como Markdown → interpola `class="panel"` como texto de classe CSS
2. Se o rendering falha ou CSS não existe para essa classe → aparece TEXTO CRU
3. O `<div>` pode não fechar corretamente → quebra de layout

### 🟡 MÉDIO — Funções helper em `src/ui/components.py`

Todas as funções de `components.py` retornam strings HTML para serem passadas à `st.markdown()`:
- `section_title()` — div de seção
- `kpi_card()` — div de KPI
- `stage_card()` — div de card com animacao
- `hero_section()` — div de hero
- `opportunity_card()` — div de card
- `score_breakdown_bars()` — divs de barras
- `empty_state()` — div de estado vazio
- `thesis_card()` — div de tese
- `driver_list()` — div de lista
- `risk_item()` — div de risco

Se qualquer página chama `st.write(component_html)` em vez de `st.markdown(..., unsafe_allow_html=True)`, o HTML aparece como texto.

### 🟢 BAIXO — CSS inline em `st.markdown()`

Páginas com `<div class="td-section">`, `<div class="panel">`, `<div class="td-info">` nos blocos markdown.

## Inventário Completo

| Arquivo | Linha | Tipo | Renderizador | Risco | Correção |
|---------|-------|------|-------------|-------|---------|
| pages/valuation_engine.py | 411 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_engine.py | 733 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_engine.py | 875 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_engine.py | 1002 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_engine.py | 761 | div panel | st.markdown() | ALTO | → st.container |
| pages/valuation_engine.py | 1037 | div note | st.markdown() | ALTO | → texto simples |
| pages/valuation_coverage.py | 508 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_coverage.py | 609 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_coverage.py | 698 | HTML table + style | st.html() | CRÍTICO | → st.dataframe |
| pages/valuation_coverage.py | 761 | div + badge | st.markdown() | ALTO | → texto simples |
| pages/valuation_coverage.py | 780 | div grid-card | st.markdown() | ALTO | → st.container |
| src/ui/components.py | 4,22,39... | HTML helpers | st.markdown() | MÉDIO | Legacy — migrar para native_components |
| pages/calendario.py | 192,276... | f-string markdown | st.markdown() | BAIXO | CSS inline OK (funciona) |
| pages/agendador.py | 172,215... | HTML chip/pills | st.markdown() | BAIXO | CSS inline OK |
| pages/inteligencia_oportunidades.py | 196,197 | HTML injection | st.markdown() | MÉDIO | Passa via opportunity_card OK |
| pages/radar_ai.py | 169 | HTML from helper | st.markdown() | MÉDIO | Passa via watchlist_card OK |
| pages/trading_desk.py | 1581,1790,1793 | div style | st.markdown() | BAIXO | CSS inline OK |
| pages/opcoes_monitoramento.py | 454,471,475,492 | HTML panels | st.markdown() | MÉDIO | CSS inline OK |
| pages/inteligencia_ativo.py | 173,179,317,343 | div HTML | st.markdown() | MÉDIO | CSS inline OK |
| pages/performance.py | 460,463,465,475,480,491,544,580 | div sec-title | st.markdown() | BAIXO | CSS inline OK |

## Corrigir Primeiro (Prioridade)

1. **valuation_engine.py** — 4 tabelas st.html() → st.dataframe
2. **valuation_coverage.py** — 3 tabelas st.html() → st.dataframe
3. **valuation_engine.py** — divs st.markdown() → componentes nativos
4. **valuation_coverage.py** — divs st.markdown() → componentes nativos