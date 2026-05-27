# OPTIONS-HISTORICAL-OPPORTUNITY-SCANNER

## Visão Geral

Módulo standalone que varre o histórico COTAHIST de opções B3 para identificar oportunidades estratégicas por ativo, classificá-las por cenário e liquidez, e gerar dois CSVs de output prontos para consumo.

**Princípio:** COTAHIST descobre oportunidade. RTD confirma execução.

---

## Localização

```
src/options/historical_opportunity_scanner.py
tests/test_options_historical_opportunity_scanner.py
```

---

## Fonte de Dados

- **Banco:** `data/database/scanner_quant.db`
- **Tabela:** `cotahist_daily`
- **market_type:** `070` = CALL, `080` = PUT, `010` = ação objeto
- **Excluído:** `020` (termo/forward) e todos os outros tipos

O módulo é **somente leitura** — nunca escreve nem altera o banco.

---

## Ativos Monitorados (20 ativos)

```
PETR4, VALE3, ITUB4, BBDC4, BBAS3, B3SA3, ABEV3, WEGE3, PRIO3, SUZB3,
RENT3, BPAC11, GGBR4, ENEV3, CMIG4, CPLE6, TAEE11, EGIE3, RADL3, HAPV3
```

O prefixo para busca de opções é os **primeiros 4 caracteres** do ticker (ex.: `PETR4` → busca `PETR%`).

---

## Outputs

### `data/realtime/options_historical_opportunities.csv`
Todas as oportunidades encontradas para todos os ativos, ordenadas por `score` decrescente.

Colunas principais:

| Coluna | Descrição |
|--------|-----------|
| `ativo_objeto` | Ativo subjacente (ex.: PETR4) |
| `ticker_opcao` | Código da opção (ex.: PETRF440) |
| `tipo` | CALL ou PUT |
| `strike` | Preço de exercício |
| `vencimento` | Data de vencimento (YYYY-MM-DD) |
| `dte` | Dias para vencimento (a partir de hoje) |
| `categoria_vencimento` | CURTO / MEDIO / LONGO / EXTRA_LONGO |
| `ultimo_preco` | Último close da opção |
| `vol_media_5d/10d/21d` | Volume médio por janela |
| `negocios_media_5d` | Negócios médios 5 pregões |
| `variacao_volume` | vol_5d / vol_21d - 1 |
| `variacao_preco` | close_last / close_5d_ago - 1 |
| `moneyness` | Valor numérico do moneyness |
| `moneyness_cat` | DEEP_ITM / ITM / ATM / OTM / DEEP_OTM |
| `liquidez_score` | Score 0-100 (ver cálculo abaixo) |
| `spot` | Último preço do ativo objeto |
| `retorno_5d/21d/63d` | Retornos históricos |
| `vol_hist_21d` | Volatilidade histórica anualizada 21d |
| `dist_max/dist_min` | Distância da máxima/mínima 52 semanas |
| `vol_relativa` | Aumento de volume relativo |
| `tendencia` | ALTA_FORTE / ALTA_MODERADA / LATERAL / BAIXA_MODERADA / BAIXA_FORTE |
| `cenario` | Cenário estratégico classificado |
| `estruturas_sugeridas` | Estruturas de opções recomendadas |
| `score` | Score de oportunidade 0-100 |
| `status` | Status da oportunidade |
| `motivo` | Explicação textual do status |
| `risco_principal` | Risco principal da posição |
| `data_analise` | Data da análise |
| `ultima_data_cotahist` | Última data disponível no banco |

### `data/realtime/options_next_session_watchlist.csv`
Subconjunto filtrado para `CANDIDATA_PROXIMO_PREGAO` e `MONITORAR_NO_RTD`, ordenado por `score` DESC.

Colunas: `ativo_objeto`, `ticker_opcao`, `tipo`, `strike`, `vencimento`, `dte`, `categoria_vencimento`, `ultimo_preco`, `liquidez_score`, `cenario`, `estruturas_sugeridas`, `score`, `status`, `motivo`

---

## Métricas e Cálculos

### Liquidez Score (0-100)
```python
vol_score = min(vol_5d / 100_000, 1.0) * 60   # max 60 pts
neg_score = min(negocios_5d / 10, 1.0) * 40   # max 40 pts
liquidez_score = vol_score + neg_score
```

### Moneyness
- **CALL:** `(spot - strike) / strike`
- **PUT:** `(strike - spot) / strike`
- DEEP_ITM: > 10% | ITM: 2–10% | ATM: -2% a 2% | OTM: -2% a -10% | DEEP_OTM: < -10%

### Volatilidade Histórica Anualizada 21d
```python
log_retornos = np.diff(np.log(closes_21d))
vol_hist_21d = std(log_retornos, ddof=1) * sqrt(252)
```

### Score de Oportunidade (0-100)
| Componente | Peso máx |
|------------|----------|
| Liquidez (`liq_score * 0.30`) | 30 pts |
| Moneyness (ATM=20, OTM=15, ITM=10, DEEP=5) | 20 pts |
| Vencimento (CURTO=20, MEDIO=15, LONGO=10, EXTRA=5) | 20 pts |
| Assimetria do cenário (forte=20, moderado=10) | 20 pts |
| Volume relativo (>0.5→10, >0.2→5) | 10 pts |

---

## Cenários Identificados

| Cenário | Condição |
|---------|----------|
| `RECUPERACAO_APOS_QUEDA` | retorno_21d < -8% **e** retorno_5d > -3% |
| `CONTINUACAO_ALTA` | retorno_5d > 2% **e** retorno_21d > 0% |
| `CONTINUACAO_BAIXA` | retorno_5d < -2% **e** retorno_21d < -4% |
| `PROTECAO_CARTEIRA` | retorno_21d < -6% |
| `RENDA_COM_ATIVO` | tendencia=LATERAL **e** vol_hist_21d < 0.25 |
| `VOLATILIDADE_EM_ALTA` | vol_relativa > 0.5 **e** vol_hist_21d > 0.35 |
| `LATERALIDADE` | tendencia=LATERAL |
| `SEM_ASSIMETRIA` | nenhuma das condições acima |

A classificação tem **prioridade por ordem** — o primeiro match vence.

---

## Status das Oportunidades

| Status | Condição |
|--------|----------|
| `DESCARTAR_ILIQUIDA` | liquidez_score < 10 |
| `DESCARTAR_SEM_ASSIMETRIA` | cenário = SEM_ASSIMETRIA |
| `CANDIDATA_PROXIMO_PREGAO` | liq ≥ 50 **e** vencimento = CURTO **e** cenário ≠ SEM_ASSIMETRIA |
| `MONITORAR_NO_RTD` | liq ≥ 30 |
| `AGUARDAR_LIQUIDEZ` | liq ≥ 10 |
| `ESTUDAR` | demais casos |

---

## Uso

### Como módulo Python
```python
from src.options.historical_opportunity_scanner import run_historical_scanner
from pathlib import Path
from datetime import date

df = run_historical_scanner(
    db_path=Path("data/database/scanner_quant.db"),
    ativos=["PETR4", "VALE3"],
    output_dir=Path("data/realtime"),
    today=date.today(),
)
print(df[["ticker_opcao","tipo","score","status","cenario"]].head(10))
```

### Via CLI
```bash
# Todos os ativos monitorados
python -m src.options.historical_opportunity_scanner

# Ativos específicos
python -m src.options.historical_opportunity_scanner --ativos PETR4 VALE3 ITUB4

# Com diretório de saída customizado
python -m src.options.historical_opportunity_scanner --output-dir /tmp/saida

# Banco customizado + verbose
python -m src.options.historical_opportunity_scanner --db /caminho/banco.db --verbose
```

---

## Testes

```bash
python -m pytest tests/test_options_historical_opportunity_scanner.py -v
```

75 testes cobrindo:

1. `TestCategorizarVencimento` (6 casos) — CURTO/MEDIO/LONGO/EXTRA_LONGO/EXPIRADO
2. `TestClassificarMoneyness` (12 casos) — CALL e PUT em todas as categorias
3. `TestLiquidezScore` (8 casos) — pontuação, caps, tipos
4. `TestCalcularScore` (7 casos) — composição do score 0-100
5. `TestClassificarCenario` (9 casos) — todos os 8 cenários + prioridade
6. `TestClassificarStatus` (9 casos) — todos os 6 status + limites exatos
7. `TestRunSemBanco` (1 caso) — DataFrame vazio quando banco inexistente
8. `TestRunComMock` (8 casos) — filtros de market_type, DTE, CALL/PUT, iliquidez
9. `TestOutputCsvCols` (4 casos) — colunas, criação dos CSVs, ordenação
10. `TestEstruturasPorCenario` (10 casos) — mapeamento completo cenário→estruturas

Todos os testes rodam **sem banco real** (SQLite temporário em `tmp_path`).

---

## Regras Críticas

1. **Nunca altera o banco de dados** — somente leitura
2. **Nunca calcula valuation** (DCF, preço justo) — usa apenas COTAHIST
3. **Nunca executa ordens** — identificação apenas
4. **market_type '070'=CALL, '080'=PUT, excluir '020'** (termo)
5. **Toda oportunidade tem risco explicado** via campo `risco_principal`
6. **Opção com liquidez_score < 10 = DESCARTAR_ILIQUIDA** — não estruturar

---

## Arquitetura

```
cotahist_daily (SQLite)
        │
        ├─ market_type='010' → Spot Data → Métricas do Ativo Objeto
        │                                  (retornos, vol, tendência, cenário)
        │
        └─ market_type='070'/'080' → Options Data → Métricas da Opção
                                                     (vol, negócios, moneyness)
                                                            │
                                                     Score + Status + Risco
                                                            │
                                          options_historical_opportunities.csv
                                          options_next_session_watchlist.csv
```
