# Opções RTD — Diagnóstico e Configuração

## Status Atual

| Métrica | Valor |
|---|---|
| Opções na shortlist | **50** |
| No RTD Profit atual | **0** |
| Com preço RTD ao vivo | **0** |
| Com bid/ask RTD | **0** |
| Monitoráveis | **0** |

**O RTD atual contém apenas ações (88 tickers). Nenhuma opção da shortlist está configurada no Profit.**

---

## Arquivos Gerados

| Arquivo | Conteúdo |
|---|---|
| `data/realtime/options_rtd_watchlist.csv` | Shortlist completa (50 opções, dados históricos) |
| `data/realtime/options_rtd_symbols.csv` | Tickers minimalistas para copiar ao Profit (6 colunas) |

---

## Como Aparecerão no Trading Desk

Quando os tickers forem adicionados ao Profit RTD:
1. A seção **"Opções Selecionadas para RTD"** no Trading Desk mostrará preço ao vivo, bid/ask e spread
2. O status mudará de "Não configurada no RTD" → "Com preço ao vivo"
3. Serão exibidos: ticker, ativo objeto, tipo CALL/PUT, strike, vencimento, moneyness, preço, bid, ask, spread, volume, negócios, liquidez e estratégia sugerida
4. KPIs serão atualizados: "No RTD", "Com Preço", "Com Bid/Ask", "Monitoráveis"

---

## Como Adicionar as Opções no Profit RTD

### Passo a passo:

1. **Abra o Excel RTD PROFIT.xlsx** no Profit
2. **Vá para a aba de opções** (ou crie uma nova aba chamada "Opções")
3. **Copie os tickers** do arquivo `data/realtime/options_rtd_symbols.csv`
4. **Cole na coluna Asset** do RTD
5. **Salve** o arquivo em `data/realtime/RTD PROFIT.xlsx`
6. **O app atualiza automaticamente** — a cada 30 segundos

### Colunas do CSV para copiar:

```
ticker,ativo_objeto,tipo,strike,vencimento,prioridade
PETRR477,PETR,PUT,47.73,2026-06-19,0.8831
PETRF462,PETR,CALL,46.23,2026-06-19,0.7273
...
```

### Prioridades recomendadas:

| Prioridade | Quantidade | Sugestão |
|---|---|---|
| 0.88–0.65 | ~10 | Adicionar primeiro — mais líquidas |
| 0.65–0.50 | ~20 | Adicionar em segundo lote |
| 0.50–0.38 | ~20 | Adicionar por último ou monitorar via COTAHIST |

### Limite recomendado:

**Não adicionar todas as 50 opções de uma vez.** Adicione no máximo 20–30 para começar (as de maior prioridade). O RTD do Profit pode ficar lento com muitas séries de opções.

---

## Estratégia por Tipo de Opção

| Tipo | Prioridade | Quando usar |
|---|---|---|
| PUT ATM/ITM | Alta | Viés de baixa do ativo objeto, proteção |
| CALL ATM/ITM | Alta | Viés de alta do ativo objeto |
| CALL OTM | Média | Opportunismo em rallies |
| PUT OTM | Média | Proteção barata ( hedging ) |

---

## Como a Estratégia Será Sugerida

Quando o RTD estiver configurado:
- **PUTs**: Priorizadas se o ativo objeto tiver viés de baixa (RSI > 65, MACD negativo, preço abaixo do VWAP)
- **CALLs**: Priorizadas se o ativo objeto tiver viés de alta (RSI < 35, MACD positivo, preço acima do VWAP)
- **Travas de baixa**: Se spread bid/ask aceitável (< 1%) e ADV alto
- **Monitorar**: Se nenhuma condição clara

---

## Arquivos

```
data/realtime/
  options_rtd_watchlist.csv   ← shortlist completa (não editar manualmente)
  options_rtd_symbols.csv     ← CSV para copiar ao Profit RTD
  RTD PROFIT.xlsx             ← planilha que o app lê (adicione os tickers aqui)
```

---

## Rotina Diária

1. Executar builder: `python src/scanners/options_rtd_watchlist_builder.py`
2. Copiar tickers de `options_rtd_symbols.csv` para o Excel RTD do Profit
3. Abrir o app Streamlit: `streamlit run pages/trading_desk.py`
4. Verificar seção **"Opções Selecionadas para RTD"**
5. Monitorar price, bid/ask, spread e estratégia sugerida
