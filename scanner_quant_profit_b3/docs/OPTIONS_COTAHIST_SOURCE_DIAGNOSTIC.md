# OPTIONS — COTAHIST Source Diagnostic

**Data:** 2026-05-27  
**Autor:** Claude Code (OPTIONS-COTAHIST-SOURCE-DIAGNOSTIC)  
**Status:** CONCLUÍDO — somente diagnóstico, nenhuma alteração feita

---

## 0. Conclusão executiva

| Questão | Resposta |
|---------|---------|
| O arquivo bruto COTAHIST da B3 contém opções? | **SIM — a maioria dos registros é de opções** |
| A tabela `cotahist_daily` contém opções? | **SIM — 7.808.644 linhas de opções no banco** |
| As opções foram descartadas no download? | **NÃO** |
| As opções foram descartadas no parser? | **NÃO** |
| As opções foram descartadas na normalização? | **NÃO** |
| Existe filtro que exclui opções de backtests e sinais quant? | **SIM — `historical_loader.py`, intencional** |
| Existe bug que impede o RTD watchlist de encontrar opções? | **SIM — `options_rtd_watchlist_builder.py` linha 126** |

---

## A) Arquivo bruto da B3 — COTAHIST contém opções?

**Resposta: SIM, e elas dominam numericamente.**

Amostra do arquivo `data/raw/COTAHIST_A2024.ZIP` (varredura linha a linha):

```
market_type  linhas
─────────────────────────────────
080 (PUT)    1.067.937
070 (CALL)   1.051.469
010 (VISTA)    322.397
020 (TERMO)    103.249
030 (FUTURO)    55.898
012 (EX.CALL)   18.437
013 (EX.PUT)    15.758
021                346
017                 70
─────────────────────────────────
TOTAL        2.635.561
```

**Opções (070+080) = 2.119.406 linhas = 80,4% do arquivo bruto.**

Arquivos brutos disponíveis: COTAHIST_A2024.ZIP, COTAHIST_A2026.ZIP + centenas de arquivos diários (COTAHIST_D*.ZIP) de 2023 a 2026-05-22.

---

## B) Tabela `cotahist_daily` contém opções?

**Resposta: SIM.**

```sql
SELECT market_type, COUNT(*) FROM cotahist_daily GROUP BY market_type ORDER BY COUNT(*) DESC;
```

```
market_type  COUNT(*)
────────────────────────
070          3.939.785   ← CALL options
080          3.868.859   ← PUT options
010          1.102.845   ← Ações VISTA
020            344.913   ← Mercado a Termo (NÃO são opções)
030             91.437   ← Futuro
013             79.739   ← Exercício de opções de venda
012             78.757   ← Exercício de opções de compra
021              1.499   ← Opções de venda (formato antigo)
017                245   ← Leilão especial
────────────────────────
TOTAL        9.508.079
```

Resumo de opções reais (070+080):
- **Total de linhas:** 7.808.644
- **Tickers distintos:** 391.182 (193.641 CALLs + 197.541 PUTs)
- **Vencimentos distintos:** 347
- **Período:** 2023-01-02 a 2026-05-22

Exemplos de opções PETR no banco:
```
PETRF370 | 070 | CALL | strike=34.21 | exp=2024-06-21 | close=4.81
PETRF380 | 070 | CALL | strike=35.21 | exp=2024-06-21 | close=3.90
VALER750 | 080 | PUT  | strike=62.99 | exp=2024-06-21 | close=0.42
ABCBG240 | 070 | CALL | strike=24.00 | exp=2024-07-19 | close=0.24
```

---

## Mapeamento correto dos `market_type`

| Código | Significado | Observação |
|--------|-------------|------------|
| `010`  | Mercado à Vista (ações spot) | ações, ETFs, FIIs |
| `012`  | Exercício de Opções de Compra | operação de exercício, não opção ativa |
| `013`  | Exercício de Opções de Venda | idem |
| `017`  | Leilão especial | |
| `020`  | **Mercado a Termo (TERMO/FORWARD)** | **NÃO são opções vanilla** — tickers tipo PETR4F, BBAS3F; strike=0.0; expiration=9999-12-31 |
| `021`  | Termo antigo / opções de venda antigas | formato legacy |
| `030`  | Futuro | contratos futuros |
| `070`  | **Opções de Compra (CALL) — opções reais** | `option_type='CALL'`, strike e expiry corretos |
| `080`  | **Opções de Venda (PUT) — opções reais** | `option_type='PUT'`, strike e expiry corretos |

> **Armadilha:** `market_type='020'` (Mercado a Termo) parece "opção de compra" pelo nome histórico do campo, mas são **contratos a termo** (forward). Tickers terminam em `F` (ex: PETR4F), não têm strike válido (0.0) e têm expiration fictício (9999-12-31). As opções reais são **exclusivamente 070 e 080**.

---

## C) Onde as opções foram excluídas (e onde não foram)

### 1. Download — NÃO exclui opções

`src/collectors/b3_cotahist_collector.py` e `src/collectors/b3_cotahist_downloader.py` baixam e extraem os ZIPs sem filtro de `market_type`. Todos os tipos chegam ao parser.

### 2. Parser — NÃO exclui opções

**`src/parsers/parse_cotahist.py`** — importa tudo, atribui `option_type` corretamente:
```python
# linha 30-31
if tpmerc == "070": option_type = "CALL"
if tpmerc == "080": option_type = "PUT"
```
Salva direto em `cotahist_daily` via `df.to_sql(...)`.

**`src/collectors/b3_cotahist_collector.py`** — `parse_cotahist_txt()` também importa tudo:
```python
if market_type == "070":
    row["option_type"] = "CALL"
elif market_type == "080":
    row["option_type"] = "PUT"
else:
    row["option_type"] = None
```
Filtro opcional `ativos_base`: se configurado, mantém opções cujos 4 primeiros caracteres coincidem com qualquer ativo base — opções dos ativos monitorados são mantidas.

### 3. Normalização / banco — NÃO exclui opções

`save_cotahist_daily()` salva todo o DataFrame sem filtro de tipo. O schema suporta `strike`, `option_type`, `expiration_date`.

### 4. `historical_loader.py` — EXCLUI opções (intencional)

`src/quant/historical_loader.py` — função `_stock_filter()`:
```python
# linhas 86-92
if "option_type" in cols and "market_type" in cols:
    return (
        " AND (option_type IS NULL OR option_type NOT IN ('CALL', 'PUT'))"
        " AND (market_type IN ('010', '10', 10) OR market_type IS NULL)"
    )
if "market_type" in cols:
    return " AND (market_type IN ('010', '10', 10) OR market_type IS NULL)"
```
**Este filtro é intencional** — o loader de preços históricos é exclusivo para ações à vista. Correto. Opções não devem entrar em backtests de ações.

### 5. `options_rtd_watchlist_builder.py` — BUG CRÍTICO

**`src/scanners/options_rtd_watchlist_builder.py` linhas 126 e 67:**

```python
# linha 126 — BUG: '70' e '80' em vez de '070' e '080'
market_type IN ('70', '80')   -- Opções de compra e venda

# linha 67 — BUG: '10' em vez de '010'
WHERE ticker = ? AND market_type = '10'
```

O banco armazena `market_type` como string 3 dígitos (`'070'`, `'080'`, `'010'`). As comparações com `'70'` e `'80'` **nunca casam** — retorna 0 linhas. O RTD watchlist builder está **silenciosamente quebrado**. Nenhum erro é lançado, apenas retorna DataFrame vazio com a mensagem "cotahist_daily vazia — sem opções para filtrar".

### 6. `b3_quotes` VIEW (init_db.py) — parcialmente correto

```sql
WHERE option_type IN ('CALL', 'PUT') OR market_type IN ('010', '10', 10)
```
Inclui opções via `option_type` — funciona. Mas `'10'` nunca casa porque o banco tem `'010'`. Sem impacto real pois o `option_type` já captura tudo.

### 7. `options_chain_collector.py` — correto

Usa `market_type IN ('010', '10', 10)` para buscar spot price e `WHERE option_type IN ('CALL', 'PUT')` para opções — a cláusula do `option_type` funciona corretamente.

---

## D) Resumo dos pontos de exclusão

```
Arquivo bruto B3/COTAHIST
      ↓ (download)
   NÃO EXCLUI opções
      ↓ (parse_cotahist.py / b3_cotahist_collector.py)
   NÃO EXCLUI opções — 070=CALL, 080=PUT gravados corretamente
      ↓
cotahist_daily (SQLite)
   ✅ 7.808.644 linhas de opções (070+080)
   ✅ 391.182 tickers distintos de opções
   ✅ strike, option_type, expiration_date preenchidos
      ↓
      ├─→ historical_loader.py       → EXCLUI (INTENCIONAL — só ações)
      ├─→ options_rtd_watchlist_builder.py → EXCLUI (BUG — '70'≠'070')
      ├─→ options_chain_collector.py → USA opções corretamente
      └─→ options_intelligence_scanner.py → USA opções corretamente
```

---

## E) Recomendação de arquitetura (sem implementar)

### Arquitetura proposta — separação de concerns

| Tabela/Arquivo | Conteúdo | Status |
|----------------|----------|--------|
| `cotahist_daily` | Todos os market types (010, 020, 030, 070, 080...) | ✅ Existente, correto |
| View `b3_quotes` | Ações (010) + Opções (070/080) | ✅ Existente (corrigir `'10'`→`'010'`) |
| `option_cotahist_daily` | Histórico de opções isolado (070+080) | 🔲 Criar futuramente |
| `option_universe_daily` | Universo filtrado (liquidez, moneyness) | 🔲 Criar futuramente |
| `options_rtd_watchlist.csv` | Shortlist para RTD (top 50-200) | 🔲 Já existe mas quebrado |

### Fix imediato prioritário (uma linha)

**`src/scanners/options_rtd_watchlist_builder.py` linha 126:**
```python
# ANTES (quebrado):
market_type IN ('70', '80')

# DEPOIS (correto):
market_type IN ('070', '080')
```

**`src/scanners/options_rtd_watchlist_builder.py` linha 67:**
```python
# ANTES (quebrado):
AND market_type = '10'

# DEPOIS (correto):
AND market_type = '010'
```

### Próxima etapa recomendada

1. **Fix imediato**: corrigir os dois bugs de `market_type` acima — 2 linhas de código
2. **Testar**: `python -m src.scanners.options_rtd_watchlist_builder` deve gerar CSV com opções
3. **Validar**: confirmar que `options_chain_collector.py` (S01) está funcional
4. **Futuro**: criar view ou tabela `option_universe_daily` para isolar opções do universo ações

---

## F) Evidências diretas dos SELECTs

```sql
-- cotahist_daily total por segmento
SELECT market_type, COUNT(*) FROM cotahist_daily GROUP BY market_type ORDER BY 2 DESC;
-- 070: 3.939.785 | 080: 3.868.859 | 010: 1.102.845

-- Opções no banco
SELECT COUNT(*), COUNT(DISTINCT ticker), MIN(trade_date), MAX(trade_date)
FROM cotahist_daily WHERE option_type IN ('CALL','PUT');
-- 7.808.644 | 391.182 | 2023-01-02 | 2026-05-22

-- Arquivo bruto COTAHIST_A2024 (Python scan)
-- 080: 1.067.937 | 070: 1.051.469 | 010: 322.397
```

---

*Gerado em: 2026-05-27 — OPTIONS-COTAHIST-SOURCE-DIAGNOSTIC*
