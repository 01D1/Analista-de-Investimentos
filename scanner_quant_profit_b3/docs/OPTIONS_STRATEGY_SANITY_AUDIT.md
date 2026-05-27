# Auditoria de Sanidade — Motor de Estratégias de Opções

**Data:** 2026-05-27  
**Escopo:** `src/options/payoff_models.py`, `src/options/rtd_strategy_adapter.py`, `src/options/strategy_builder.py`, `pages/trading_desk.py`

---

## 1. Regra de Preço Conservadora

| Perna | Preço utilizado | Motivo |
|---|---|---|
| COMPRADA (BUY) | ASK | Pagamos o preço que o mercado oferece |
| VENDIDA (SELL) | BID | Recebemos o preço que o mercado compra |
| Referência/IV/Greeks | Mid-price | Cálculo interno apenas — nunca operacional |

### Problema identificado (corrigido)

`_build_option_record()` em `rtd_strategy_adapter.py` usava mid_price no campo `price`, sem armazenar bid e ask separadamente. O `_to_leg()` em `strategy_builder.py` usava `opt.price` para ambas as direções — otimista e incorreto.

### Correção implementada

1. `OptionRecord` agora tem campos `bid: float` e `ask: float` (default `0.0` para dados históricos sem book).
2. `_build_option_record()` armazena `bid` e `ask` reais do RTD. O campo `price` continua sendo mid-price, exclusivamente para IV e Greeks.
3. `_to_leg()` em `strategy_builder.py` aplica preço conservador:
   - `direction == "BUY"` → usa `opt.ask`
   - `direction == "SELL"` → usa `opt.bid`
   - Fallback para `opt.price` quando `bid/ask == 0` (dados históricos/cotahist)
4. Adicionada função helper `_get_conservative_price(bid, ask, direction)` em `rtd_strategy_adapter.py`.

---

## 2. Auditoria Matemática por Estrutura

### Notação
- `CONTRACT_SIZE = 100`
- `debit > 0` = débito; `credit < 0` = crédito recebido
- Preços conservadores: compra @ ASK, venda @ BID

| # | Estrutura | Tipo | net_cost | max_profit | max_loss | Break-even | Status |
|---|---|---|---|---|---|---|---|
| 1 | Long Call | DIRECIONAL | `ask * 100` | inf | `ask * 100` | `K + ask` | OPERACIONAL |
| 2 | Long Put | DIRECIONAL | `ask * 100` | `(K - ask) * 100` | `ask * 100` | `K - ask` | OPERACIONAL |
| 3 | Short Call (descoberta) | RENDA | `-bid * 100` | `bid * 100` | inf | `K + bid` | BLOQUEADA (risco ilimitado) |
| 4 | Short Put (descoberta) | RENDA | `-bid * 100` | `bid * 100` | `(K - bid) * 100` | `K - bid` | MONITORAR (exige margem) |
| 5 | Bull Call Spread | SPREAD_ALTA | `(ask_K1 - bid_K2) * 100` | `(K2-K1)*100 - debit` | `debit` | `K1 + (ask_K1 - bid_K2)` | OPERACIONAL |
| 6 | Bear Put Spread | SPREAD_BAIXA | `(ask_K2 - bid_K1) * 100` | `(K2-K1)*100 - debit` | `debit` | `K2 - (ask_K2 - bid_K1)` | OPERACIONAL |
| 7 | Bear Call Spread | SPREAD_BAIXA | `-(bid_K1 - ask_K2) * 100` | `(bid_K1 - ask_K2) * 100` | `(K2-K1)*100 - credit` | `K1 + (bid_K1 - ask_K2)` | OPERACIONAL |
| 8 | Bull Put Spread | SPREAD_ALTA | `-(bid_K2 - ask_K1) * 100` | `(bid_K2 - ask_K1) * 100` | `(K2-K1)*100 - credit` | `K2 - (bid_K2 - ask_K1)` | OPERACIONAL |
| 9 | Covered Call | RENDA | `(spot - bid_call) * 100` | `(K - spot + bid_call) * 100` | `net_cost` | `spot - bid_call` | OPERACIONAL |
| 10 | Collar | PROTECAO | `(ask_put - bid_call) * 100` | `(K_call - spot - ask_put + bid_call) * 100` | `(spot - K_put + ask_put - bid_call) * 100` | `spot + ask_put - bid_call` | OPERACIONAL |
| 11 | Protective Put | PROTECAO | `(spot + ask_put) * 100` | inf | `(spot - K_put + ask_put) * 100` | `spot + ask_put` | OPERACIONAL |
| 12 | Iron Condor | CONDOR | `-(credit_put + credit_call) * 100` | `(credit_put + credit_call) * 100` | `max(width_put, width_call) - credit` | 2 pontos | OPERACIONAL |
| 13 | Butterfly (Calls) | BUTTERFLY | `(ask_low - 2*mid + ask_high) * 100` | vide fórmula | `debit` | 2 pontos | OPERACIONAL |
| 14 | Long Straddle | VOLATILIDADE | `(ask_call + ask_put) * 100` | inf | `debit` | `K ± (ask_call + ask_put)` | OPERACIONAL |
| 15 | Long Strangle | VOLATILIDADE | `(ask_call + ask_put) * 100` | inf | `debit` | vide strikes | OPERACIONAL |

---

## 3. Exemplo Numérico — Bull Call Spread Conservador

**Ativo:** PETR4 @ R$ 37,50  
**Opção K1:** PETRF370 CALL | bid=1,40 | ask=1,60 | mid=1,50  
**Opção K2:** PETRF386 CALL | bid=0,55 | ask=0,65 | mid=0,60

| Métrica | Mid-price (otimista) | Conservador (ASK/BID) | Diferença |
|---|---|---|---|
| Débito K1 comprada | 1,50 | 1,60 (ASK) | +0,10 |
| Crédito K2 vendida | 0,60 | 0,55 (BID) | -0,05 |
| **Net debit** | **(1,50 - 0,60) × 100 = R$ 90** | **(1,60 - 0,55) × 100 = R$ 105** | **+R$ 16,67%** |
| Max ganho | R$ 110 | R$ 95 | -R$ 15 |
| Max perda | R$ 90 | R$ 105 | +R$ 15 |
| Break-even | R$ 38,90 | R$ 39,05 | +R$ 0,15 |
| R/R | 1,22x | 0,90x | Degradado |

**Conclusão:** O mid-price subestima o custo real em 16,67% neste exemplo. Para estruturas de crédito, o efeito inverte — o crédito real é menor que o mid-price sugere.

---

## 4. Filtros de Segurança Implementados

| Filtro | Onde | Valor |
|---|---|---|
| Spread máx. | `rtd_strategy_adapter.py` | 3% |
| Bid+Ask obrigatório | `_build_option_record()` | bid > 0 e ask > 0 |
| DTE mínimo | `_build_option_record()` | 3 dias |
| DTE máximo | `_build_option_record()` | 90 dias |
| Venda descoberta bloqueada | `strategy_builder.py` + status | `ALTO_RISCO_NAO_RECOMENDADO` → status `DESCARTAR` |
| Risco máximo calculado | `payoff_models.py` | todas as estruturas |
| Validação matemática | `validate_strategy_payoff()` | 9 regras |

---

## 5. Função validate_strategy_payoff()

Adicionada em `src/options/payoff_models.py`. Retorna `dict{ok, erros, alertas}`.

**Regras verificadas:**

| # | Regra | Tipo |
|---|---|---|
| 1 | net_cost não NaN/inf | Erro crítico |
| 2 | max_profit > 0 ou inf | Erro crítico |
| 3 | max_loss > 0 ou inf | Erro crítico |
| 4 | Débito: max_loss ≈ net_cost (±1%) | Erro em spreads/direcionais |
| 5 | Spreads débito: max_profit + max_loss > 0 | Erro crítico |
| 6 | risk_reward ≥ 0 | Erro crítico |
| 7 | Breakevens existem | Alerta |
| 8 | Pernas de opção: mesmo vencimento | Erro crítico |
| 9 | Venda descoberta: requires_margin=True | Alerta |

---

## 6. Status da Implementação

| Tarefa | Status |
|---|---|
| OptionRecord com bid/ask | CONCLUÍDO |
| _build_option_record armazena bid/ask | CONCLUÍDO |
| _to_leg usa ASK/BID conservador | CONCLUÍDO |
| _get_conservative_price() | CONCLUÍDO |
| validate_strategy_payoff() | CONCLUÍDO |
| Nota de sanidade em trading_desk.py | CONCLUÍDO |
| Testes (classes 11 e 12 + bid_ask) | CONCLUÍDO |
| Este documento | CONCLUÍDO |

---

*Auditoria executada por Claude Code em 2026-05-27*  
*Não é recomendação de investimento. Use como apoio à decisão.*
