# M017-S03 — Metric Extraction Engine Report

> Executado em: 2026-05-26
> Status: ✅ CONCLUÍDO

---

## 1. Objetivo

Extrair métricas financeiras estruturadas dos dados CVM já ingeridos em `cvm_statements`
e populá-las em `valuation_financial_inputs` para uso pelo Financial Engine de valuation.

---

## 2. Bug Fix — parse_and_store() KeyError: 'CD_CVM'

**Arquivo:** `src/ingestion/cvm_downloader.py:246`

**Problema:** `download_dfp(year)` retorna todos os CSVs do diretório extraído, incluindo
o arquivo de metadados `dfp_cia_aberta_{year}.csv` que não possui coluna `CD_CVM`.
O acesso `df["CD_CVM"]` na linha seguinte lançava `KeyError`.

**Fix aplicado:**
```python
# Antes (linha 247):
df = pd.read_csv(csv_path, ...)
df["CD_CVM"] = df["CD_CVM"].astype(str)...  # KeyError aqui

# Depois:
df = pd.read_csv(csv_path, ...)
if "CD_CVM" not in df.columns:
    log.debug("skipping metadata CSV without CD_CVM", file=csv_path.name)
    continue  # ← FIX M017-S03
df["CD_CVM"] = df["CD_CVM"].astype(str)...
```

---

## 3. Arquitetura do Extractor

**Arquivo:** `src/ingestion/metric_extractor.py`

**Fonte de dados:** `cvm_statements` (SQLite, já ingerido em M017-S02)

**Estratégia de deduplicação:**
- Filtra `year = CAST(SUBSTR(reference_date, 1, 4) AS INTEGER)` — seleciona apenas
  linhas ÚLTIMO (ano corrente) eliminando os comparativos PENÚLTIMO de DFPs posteriores
- Evita duplicação de contas quando empresas renumeram DFC entre exercícios

**Tipos de extração:**

| Tipo | Método | Exemplos |
|------|--------|---------|
| `structured` | Código CVM exato + validação de nome | total_assets, revenue, net_income |
| `keyword` | Busca por palavras-chave em 6.01.01.xx / 6.02.xx | D&A, CapEx |
| `derived` | Cálculo a partir de métricas estruturadas | EBITDA, net_debt, FCF |

**Mapeamento de codes principais (não-bancos):**

| Conta CVM | Métrica |
|-----------|---------|
| `1` | total_assets |
| `1.01` | current_assets |
| `1.01.01` | cash_and_equivalents |
| `1.01.02` | financial_applications |
| `1.02` | non_current_assets |
| `2.01` | current_liabilities |
| `2.01.04` (valida nome) | short_term_debt |
| `2.02` | non_current_liabilities |
| `2.02.01` (valida nome) | long_term_debt |
| `2.03` (valida nome) | equity_book_value |
| `3.01` | revenue |
| `3.05` | ebit |
| `3.11` (valida nome) | net_income |
| `6.01` | operating_cash_flow |
| `6.01.01.xx` (keyword: deprecia/amortiza) | depreciation_amortization |
| `6.02.xx` (keyword: imobilizado/intangível/etc) | capex |

**Derivações:**
- `gross_debt` = short_term_debt + long_term_debt
- `net_debt` = gross_debt − cash − financial_applications
- `ebitda` = ebit + depreciation_amortization
- `free_cash_flow` = operating_cash_flow − capex
- `total_liabilities` = current_liabilities + non_current_liabilities

**Tratamento de bancos (COSIF):**
- Não extrai short/long_term_debt (estrutura incompatível com 2.01.04/2.02.01)
- equity_book_value via busca keyword em `2.xx`: "patrimônio líquid"
- net_income via fallback keyword quando `3.11` não contém "lucro/prejuízo"
- D&A e CapEx: mesma lógica keyword dos não-bancos

---

## 4. Execução

### 4.1 Canário — EGIE3

| Item | Resultado |
|------|-----------|
| Períodos processados | 28 |
| Métricas extraídas | 588 |
| Erros | 0 |
| Métricas distintas | 21 |
| Cobertura | 2019-Q1 a 2025-12-31 (DFP+ITR) |

**Validação DFP 2024-12-31 (EGIE3):**

| Métrica | Valor | Método |
|---------|-------|--------|
| total_assets | R$ 50.112B | structured |
| current_assets | R$ 7.198B | structured |
| cash_and_equivalents | R$ 3.959B | structured |
| short_term_debt | R$ 2.611B | structured |
| long_term_debt | R$ 21.037B | structured |
| gross_debt | R$ 23.648B | derived |
| net_debt | R$ 19.689B | derived |
| equity_book_value | R$ 12.280B | structured |
| revenue | R$ 11.219B | structured |
| ebit | R$ 7.682B | structured |
| net_income | R$ 4.303B | structured |
| depreciation_amortization | R$ 1.072B | keyword |
| ebitda | R$ 8.754B | derived |
| operating_cash_flow | R$ 4.154B | structured |
| capex | R$ 6.646B | keyword |
| free_cash_flow | R$ -2.492B | derived |
| total_liabilities | R$ 37.832B | derived |

### 4.2 Batch 18 NEEDS_FINANCIALS

| Resultado | Valor |
|-----------|-------|
| Tickers | 18 |
| Total records | 9.223 |
| Erros | 0 |

### 4.3 Batch amplo — todos os tickers

| Resultado | Valor |
|-----------|-------|
| Tickers processados | 89 |
| Tickers com dados | 88 |
| Total records | **47.603** |
| Erros | 1 (AUAU3 — sem CVM data, esperado) |
| Métricas distintas | **21** |

---

## 5. Cobertura Final

### 5.1 Não-bancos (IFRS) — 21 métricas

Tickers com cobertura completa (21 métricas, 28 períodos):
`ABEV3`, `ALOS3`, `AXIA3`, `AZUL4`, `AZZA3`, `B3SA3`, `BEEF3`, `BRAV3`\*, `BRFS3`,
`BRKM5`, `CCRO3`, `CMIG4`, `CMIN3`\*, `COGN3`, `CPFE3`, `CPLE6`, `CSAN3`, `CSNA3`,
`CVCB3`, `CYRE3`, `EGIE3`, `EMBR3`, `ENEV3`, `ENGI11`, `EQTL3`, `FLRY3`, `GGBR4`,
`GOAU4`, `HAPV3`, `HYPE3`, `IGTI11`, `ISAE4`, `ITSA4`, `JBSS3`, `KLBN11`, `LREN3`,
`LWSA3`, `MGLU3`, `MRFG3`, `MRVE3`, `MULT3`, `NTCO3`, `PCAR3`, `PETR4`, `POMO4`,
`PRIO3`, `PSSA3`, `RADL3`, `RAIL3`, `RAIZ4`, `RDOR3`, `RENT3`, `SBSP3`, `SLCE3`,
`SMTO3`, `STBP3`, `SUZB3`, `TAEE11`, `TIMS3`, `TOTS3`, `UGPA3`, `USIM5`, `VALE3`,
`VAMO3`, `VBBR3`, `VIVA3`, `VIVT3`, `WEGE3`, `YDUQ3`

Tickers com cobertura parcial (IPO recente ou estrutura diferente):
| Ticker | Métricas | Períodos | Observação |
|--------|---------|---------|------------|
| AMOB3 | 21 | 9 | IPO recente (2023+) |
| AURE3 | 21 | 20 | IPO recente (2021+) |
| RECV3 | 21 | 21 | IPO recente (2020+) |
| CRFB3 | 21 | 27 | dados parciais 2025 |
| VIVA3 | 21 | 27 | dados parciais 2025 |
| BBSE3 | 17 | 28 | seguradora — sem debt codes padrão |
| IRBR3 | 17 | 28 | resseguros — sem debt codes padrão |
| CXSE3 | 19 | 28 | seguradora — sem 2.01.04/2.02.01 padrão |
| BRAP4 | 19 | 28 | holding — estrutura parcial |

### 5.2 Bancos (COSIF) — 14 métricas

| Ticker | Métricas | Períodos |
|--------|---------|---------|
| ABCB4 | 14 | 28 |
| BBAS3 | 14 | 28 |
| BBDC4 | 14 | 28 |
| BMGB4 | 14 | 28 |
| BPAC11 | 14 | 28 |
| BPAN4 | 14 | 27 |
| BRSR6 | 14 | 28 |
| INTR4 | 10 | 17 |
| ITUB4 | 14 | 28 |
| PINE4 | 14 | 28 |
| SANB11 | 14 | 28 |

*Bancos: short_term_debt, long_term_debt, gross_debt, net_debt, current_liabilities,
non_current_liabilities, total_liabilities não extraídos (COSIF). Métricas extraídas:
total_assets, current_assets, cash_and_equivalents, financial_applications,
non_current_assets, equity_book_value, revenue, ebit, net_income, operating_cash_flow,
depreciation_amortization, capex, ebitda, free_cash_flow.*

---

## 6. Gaps e Pendências

| Gap | Impacto | Próxima ação |
|-----|---------|-------------|
| `shares_outstanding` não extraído | Não disponível nos CSVs CVM | S04: yfinance ou B3 scraper |
| AUAU3: sem dados CVM | 1 ticker ausente | Excluir da análise ou adicionar manual |
| `normalized_name=None` para EQTL3/VAMO3 em cvm_statements | Cosmético | S04 |
| Bancos: sem debt breakdown | 12 tickers com 14/21 métricas | S04: COSIF debt extractor |
| Seguradoras (BBSE3, IRBR3): sem debt | 2 tickers com 17/21 métricas | S04: specific handling |

---

## 7. Artefatos

| Arquivo | Descrição |
|---------|-----------|
| `src/ingestion/metric_extractor.py` | Engine principal |
| `src/ingestion/cvm_downloader.py` | Fix M017-S03 bug CD_CVM |
| `run_extract_metrics.py` | Runner CLI (canary/batch/all) |
| `data/ingestion.db → valuation_financial_inputs` | 47.603 registros |

---

## 8. Métricas de Qualidade

| Métrica | Valor |
|---------|-------|
| Registros totais | 47.603 |
| Tickers cobertos | 88/89 (99%) |
| Métricas completas (21/21) | 68 tickers (77%) |
| Métricas parciais | 20 tickers (23%) |
| Erros de extração | 1 (AUAU3, sem dados) |
| Source_type | CVM_CSV |
| Source_priority | 1 (máxima confiança) |
| Confidence (direct) | 1.0 |
| Confidence (keyword) | 1.0 |
| Confidence (derived) | 1.0 |

---

## 9. Autorização S04

| Critério | Status |
|----------|--------|
| valuation_financial_inputs populado | ✅ 47.603 registros |
| Cobertura mínima ≥ 80% tickers | ✅ 99% |
| Derivações calculadas | ✅ gross_debt, net_debt, ebitda, FCF, total_liab |
| Parse_and_store() bug fixed | ✅ |
| Source CVM_CSV priority=1 | ✅ |
| **S04 autorizada?** | **✅ SIM** |

---

*Relatório M017-S03 — gerado em 2026-05-26*
