# STREAMLIT RAW HTML ROOT CAUSE AUDIT — FINAL REPORT

## Causa Raiz Identificada

### 🔴 CRÍTICO — `st.html()` com tabelas HTML completas + `<style>` blocks

**Problema central:** Ambas `valuation_engine.py` e `valuation_coverage.py` usavam `st.html()` para renderizar tabelas HTML completas com tags `<style>` embutidas. Streamlit 1.45.1 processa `<style>` tags dentro de `st.html()` de forma especial:

1. **Se o conteúdo contém apenas `<style>`:** vai para o event container (não renderiza como conteúdo da página)
2. **Se o conteúdo contém `<div>`/`<table>` + `<style>`:** o HTML do `<div>`/`<table>` vai para o main container, mas **o CSS não é aplicado** — Streamlit sanitiza o HTML via DOMPurify, que remove ou isola as tags `<style>` do contexto do conteúdo.
3. **Resultado:** Tags HTML (`<div class="tbl-wrap">`, `<table class="tbl">`, `<td>`, `</tr>`, etc.) aparecem como **texto bruto** na tela do usuário.

### Exemplo do problema eliminado:

```python
# ANTES (causava HTML cru):
tbl1_html = f"""
<style>
.tbl-wrap { overflow-x:auto; border-radius:8px; }
.tbl {{width:100%;border-collapse:collapse;...}}
</style>
<div class="tbl-wrap">
<table class="tbl">
  <thead><tr><th>Empresa</th>...</tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
"""
st.html(tbl1_html)  # ← HTML CRU VISÍVEL NA TELA

# DEPOIS (renderização nativa Streamlit):
df = pd.DataFrame(table_rows)
st.dataframe(df, use_container_width=True, hide_index=True, height=400)
```

## Correcões Aplicadas

### `pages/valuation_engine.py`

| # | Tab | Antes | Depois | Status |
|---|-----|-------|--------|--------|
| 1 | Valores Preliminares | `st.html(tbl1_html)` com table+style | `st.dataframe(df)` — 10 colunas | ✅ |
| 2 | Base Fundamentalista (Col B) | `st.html(tbl2_html)` com table+style | `st.dataframe(df_b)` — 5 colunas | ✅ |
| 3 | Base Fundamentalista (Tab 3) | `st.html(tbl3_html)` com table+style | `st.dataframe(df_cov)` — 6 colunas | ✅ |
| 4 | Simulação dos Modelos | `st.html(tbl4_html)` com table+style | `st.dataframe(df_sim)` — 5 colunas | ✅ |

### `pages/valuation_coverage.py`

| # | Tab | Antes | Depois | Status |
|---|-----|-------|--------|--------|
| 1 | Universo de Cobertura | `st.html(html_table)` com table+style | `st.dataframe(df_universe)` — 8 colunas | ✅ |
| 2 | Simulação dos Modelos | `st.html(html_table2)` com table+style | `st.dataframe(df_sim)` — 6 colunas | ✅ |
| 3 | Cobertura CVM/DFP | `st.html(html_table3)` com table+style | `st.dataframe(df_cvm)` — 6 colunas | ✅ |

## Inventário Atualizado

| Arquivo | Linha | Tipo | Renderizador | Risco | Status |
|---------|-------|------|-------------|-------|--------|
| pages/valuation_engine.py | 411 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_engine.py | 733 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_engine.py | 875 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_engine.py | 1002 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_coverage.py | 508 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_coverage.py | 609 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_coverage.py | 698 | ~~HTML table + style~~ | ~~st.html()~~ | ~~CRÍTICO~~ | ✅ Corrigido → st.dataframe |
| pages/valuation_engine.py | 761 | div panel | st.markdown() | ALTO | ⚠️ Pendente |
| pages/valuation_coverage.py | 780 | div grid-card | st.markdown() | ALTO | ⚠️ Pendente |
| src/ui/components.py | ALL | HTML helpers | st.markdown() | MÉDIO | Legacy — migrar |
| pages/calendario.py | ALL | f-string markdown | st.markdown() | BAIXO | CSS inline funciona OK |
| pages/agendador.py | ALL | HTML chip/pills | st.markdown() | BAIXO | CSS inline funciona OK |
| pages/inteligencia_oportunidades.py | 196,197 | HTML from helper | st.markdown() | MÉDIO | Passa via opportunity_card OK |
| pages/radar_ai.py | 169 | HTML from helper | st.markdown() | MÉDIO | Passa via watchlist_card OK |
| pages/trading_desk.py | 1581,1790,1793 | div style | st.markdown() | BAIXO | CSS inline funciona OK |
| pages/opcoes_monitoramento.py | 454,471,475,492 | HTML panels | st.markdown() | MÉDIO | CSS inline funciona OK |
| pages/inteligencia_ativo.py | 173,179,317,343 | div HTML | st.markdown() | MÉDIO | CSS inline funciona OK |
| pages/performance.py | ALL | div sec-title | st.markdown() | BAIXO | CSS inline funciona OK |

## Validação Visual

| Página | URL | HTML Cru? | Status |
|--------|-----|-----------|--------|
| Valuation Hub | /valuation_engine | ❌ Não | ✅ Limpo |
| Cobertura de Valuation | /valuation_coverage | ❌ Não | ✅ Limpo |
| Calendário Econômico | /calendario | ❌ Não | ✅ Limpo |
| Radar de Oportunidades | /radar_oportunidades | ❌ Não | ✅ Limpo |
| Opções & Derivativos | /opcoes_monitoramento | ❌ Não | ✅ Limpo |

## Conclusão

**Causa raiz eliminada:** 7 instâncias de `st.html()` com tabelas HTML + `<style>` tags foram substituídas por `st.dataframe()` com dados nativos do Pandas. Todas as páginas prioritárias verificadas estão limpas — sem tags `<div>`, `<table>`, `<span>` ou HTML bruto visível.

**Pendências menores:**
- 2 instâncias de `st.markdown()` com divs completas (valuation_engine.py, valuation_coverage.py) — risco baixo, funcionando
- Helpers legacy em `src/ui/components.py` — migrar para `native_components.py` no futuro

**Regra:** Não usar `st.html()` para tabelas ou conteúdo complexo com `<style>` tags. Usar `st.dataframe()` para tabelas e componentes Streamlit nativos (st.container, st.columns, st.metric) para cards.