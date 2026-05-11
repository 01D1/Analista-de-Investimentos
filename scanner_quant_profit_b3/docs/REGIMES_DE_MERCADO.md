# Regimes De Mercado

## Objetivo

A camada de regimes de mercado avalia sinais, filtros, thresholds e governança separadamente em ambientes diferentes.

Ela evita aprovar uma configuração quantitativa que só funcionou em um único tipo de mercado.

## Tipos De Regime

O sistema separa regimes em quatro dimensões:

- tendência: `ALTA_TENDENCIAL`, `BAIXA_TENDENCIAL`, `LATERAL`;
- volatilidade: `ALTA_VOLATILIDADE`, `BAIXA_VOLATILIDADE`;
- liquidez: `LIQUIDEZ_FORTE`, `LIQUIDEZ_FRACA`;
- risco: `RISCO_ELEVADO`, `RISCO_CONTROLADO`.

Também há `primary_regime`, que resume o regime dominante da data.

## Proxy De Mercado

Quando não há benchmark oficial no banco, o sistema cria um proxy usando os ativos disponíveis.

O proxy calcula por data:

- retorno médio do universo;
- retorno mediano;
- percentual de ativos positivos;
- volume total;
- volatilidade do universo;
- breadth de mercado.

Esse proxy não substitui o Ibovespa, mas permite classificar ambientes de mercado quando o índice não está disponível.

## Comandos

Gerar regimes e salvar no SQLite:

```powershell
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

Rodar backtest histórico com regimes:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
```

Usando benchmark, quando existir no banco:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --regime-source benchmark --benchmark IBOV --csv --save-db
```

## Backtest Por Regime

O resumo por regime mede:

- quantidade de sinais;
- retorno bruto médio D+5;
- retorno líquido médio D+5;
- hit rate;
- percentual tradeable;
- concentração por ativo;
- melhor `signal_type`;
- melhor `score_bucket`;
- classe de robustez por regime.

## Governança Por Regime

A governança pode classificar um candidato como:

- `CANDIDATO_RESTRITO_A_REGIME`;
- `BLOQUEADO_REGIME_INSUFICIENTE`;
- `BLOQUEADO_REGIME_RISCO`.

Isso significa que um candidato não precisa ser aprovado de forma ampla. Ele pode ser apenas um candidato restrito a ambientes específicos, como `ALTA_TENDENCIAL` com `LIQUIDEZ_FORTE`.

Quando a camada de eventos tambem estiver ativa, a governança pode diferenciar um regime favorável de um evento específico dentro daquele regime. Isso evita aprovar um filtro apenas porque houve poucos eventos fortes em um único ambiente de mercado.

## Mesa Quant

A aba `Regimes de Mercado` mostra:

- distribuição dos regimes;
- último regime classificado;
- retorno líquido por regime;
- hit rate por regime;
- qualidade de execução por regime;
- status de governança por regime.

## Limitações

- O proxy por universo depende dos ativos disponíveis.
- Regimes calculados com poucos ativos podem ser instáveis.
- COTAHIST é diário e não captura mudança intraday de regime.
- A classificação é heurística e deve ser validada com histórico maior.
- Nenhum regime aprova filtros ou scores automaticamente.
