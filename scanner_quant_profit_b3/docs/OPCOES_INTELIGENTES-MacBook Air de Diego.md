# Opções Inteligentes

## Objetivo

O scanner inteligente de opções cria uma camada analítica para estudar cadeias de opções e estruturas simples com liquidez, moneyness, vencimento, payoff, risco, Greeks aproximados e governança.

Ele não altera o score principal de ações, não muda ranking padrão, não executa ordens e não gera recomendação financeira. A saída correta é sempre interpretada como estrutura potencial a estudar, assimetria a investigar, apenas observação ou bloqueio por risco, liquidez, spread, vencimento ou dados insuficientes.

## Comando Operacional

```powershell
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

Parâmetros úteis:

```powershell
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 --min-volume 10000 --min-trades 5 --max-spread-pct 15 --min-dte 7 --max-dte 90 --risk-free-rate 0.10 --save-db --csv
```

## Métricas Calculadas

Para cada opção, o scanner padroniza e calcula:

- tipo de opção: `CALL`, `PUT` ou `UNKNOWN`;
- vencimento e dias até vencimento;
- spread absoluto e percentual;
- volume financeiro;
- moneyness e classe `ITM`, `ATM`, `OTM`, `DEEP_ITM` ou `DEEP_OTM`;
- valor intrínseco;
- valor extrínseco;
- breakeven;
- volatilidade implícita aproximada, quando possível;
- delta, gamma, theta e vega aproximados;
- score de liquidez;
- score de risco.

## Governança

A governança bloqueia opções e estruturas com:

- spread percentual acima do limite;
- volume financeiro insuficiente;
- vencimento curto demais;
- dados essenciais ausentes;
- liquidez ruim;
- risco não mensurável.

Status como `OPTION_APPROVED_FOR_STUDY` e `STRUCTURE_APPROVED_FOR_STUDY` significam apenas que a estrutura passou por filtros mínimos para estudo. Não significam compra, venda, execução ou recomendação.

## Saídas

Com `--csv`, o comando gera arquivos para:

- cadeia de opções pontuada;
- estruturas candidatas.

Com `--save-db`, salva:

- snapshots da cadeia de opções;
- estruturas candidatas;
- runs do scanner.

## Histórico e Backtest Preliminar

Para construir histórico de cadeia:

```powershell
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

Para rodar backtest preliminar de estrutura:

```powershell
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
```

Esses comandos permanecem exploratórios. Se o histórico de cadeia for insuficiente, o backtest retorna `INSUFFICIENT_DATA`.

Para validar fora da amostra:

```powershell
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```

## Limitações

Os Greeks são aproximações de Black-Scholes e dependem de preço, strike, vencimento, taxa livre de risco e volatilidade. A volatilidade implícita pode ficar indisponível quando o preço é inconsistente ou faltam dados.

O scanner não substitui análise operacional de livro, bid/ask real, exercício, rolagem, risco de liquidez, custo de execução ou suitability. Opções com baixa liquidez devem ser tratadas como dados frágeis mesmo quando o payoff teórico parece atraente.
