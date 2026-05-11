# Score Quantitativo

## Objetivo

O score quantitativo composto foi criado para evoluir o ranking intraday sem substituir imediatamente o score legado. Nesta fase, os dois scores rodam em paralelo para permitir comparacao, auditoria e calibracao.

O sistema nao gera recomendacao financeira. O score indica prioridade analitica para investigacao.

## Score Legado

O score legado e uma soma de regras intraday simples:

- preco acima da abertura;
- preco acima do fechamento anterior;
- preco perto da maxima;
- variacao positiva;
- volume financeiro minimo;
- numero de negocios minimo;
- posicao alta dentro do range do dia.

Ele e util como baseline porque e simples, rapido e ja estava em uso. A limitacao principal e que ele tende a ser binario: quando muitos ativos passam pelos mesmos filtros, muitos recebem nota alta.

## Score Novo

O `score_final` e composto por blocos:

- `score_momentum`;
- `score_tendencia`;
- `score_liquidez`;
- `score_volatilidade`;
- `score_risco`.

Pesos iniciais:

- 35% momentum;
- 25% tendencia;
- 20% liquidez;
- 10% volatilidade;
- 10% risco.

O score de risco reduz a qualidade do sinal quando ha gap elevado, range esticado, preco muito perto da maxima apos alta amplitude ou liquidez insuficiente.

## Por Que Rodar Em Paralelo

O score legado nao deve ser removido sem evidencia. O modo paralelo permite:

- comparar rankings;
- encontrar ativos em que os modelos concordam;
- identificar quando o novo score esta mais rigoroso;
- identificar quando o novo score esta mais agressivo;
- detectar inflacao do score novo;
- calibrar pesos e limites antes de usar o score como ranking principal.

## Divergencias

O modulo de comparacao classifica cada ativo:

| Tipo | Interpretacao |
|---|---|
| `CONVERGENTE_FORTE` | score legado alto e score novo alto |
| `CONVERGENTE_FRACO` | score legado baixo e score novo baixo |
| `NOVO_SCORE_MAIS_RIGOROSO` | score legado alto, mas score novo abaixo da faixa forte |
| `NOVO_SCORE_MAIS_AGRESSIVO` | score legado baixo ou medio, mas score novo alto |
| `DIVERGENTE` | sinais ou rankings muito diferentes |
| `NEUTRO` | diferenca sem leitura forte |

Divergencia nao e erro automaticamente. Ela aponta casos que merecem revisao manual e, depois, backtest.

## Distribuicao E Inflacao De Score

A calibracao observa:

- media;
- mediana;
- desvio padrao;
- minimo e maximo;
- percentis 10, 25, 50, 75 e 90;
- quantidade de ativos nas faixas 0-20, 20-40, 40-60, 60-80 e 80-100.

Se mais de 40% dos ativos ficam acima de 80, o sistema alerta possivel inflacao de score:

> Possivel inflacao de score: muitos ativos classificados como fortes.

Esse alerta indica que pesos e limites podem estar permissivos demais para o universo analisado.

## Como Rodar A Comparacao

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores
```

Com CSV:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --csv
```

Para salvar a rodada de comparacao no SQLite:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --save-calibration
```

O CSV inclui:

- ativo;
- score legado;
- score novo;
- componentes do score;
- sinal legado;
- sinal novo;
- confianca;
- tipo de divergencia;
- explicacao.

## Historico De Calibracao

O modo `--save-calibration` grava cada rodada de comparacao em duas tabelas:

- `score_calibration_runs`;
- `score_calibration_assets`.

A tabela de rodadas salva a distribuicao agregada do `score_final`: media, mediana, desvio padrao, percentis, faixas de score e alerta de inflacao.

A tabela de ativos salva o detalhe de cada papel na rodada: score legado, score novo, componentes do score, sinais, mudanca de ranking, tipo de divergencia e explicacao.

Esse historico existe para responder perguntas como:

- O score novo esta ficando inflado ao longo do tempo?
- O score novo e mais rigoroso ou mais agressivo que o legado?
- Quais tipos de divergencia aparecem com mais frequencia?
- Os ativos com score acima de 80 performam melhor depois do sinal?
- O alerta de inflacao aparece em dias especificos ou de forma recorrente?

Mesmo com historico salvo, o score legado nao deve ser substituido sem backtest por tipo de sinal, por faixa de score e por regime de mercado.

## Calibracao Ao Longo Do Tempo

O proximo passo e gravar sinais por alguns pregoes e comparar:

- taxa de convergencia;
- distribuicao diaria do score;
- ativos que aparecem como falso positivo;
- retorno futuro por tipo de divergencia;
- estabilidade dos rankings;
- sensibilidade a volume relativo e volatilidade.

O score novo so deve substituir o legado depois de backtests por tipo de sinal e por regime de mercado.

## Calibracao Com Backtest Historico

A Fase 5 adiciona um backtest historico diario usando dados COTAHIST ja processados no SQLite. O objetivo e avaliar se o `score_final` e seus componentes ajudam a explicar retornos futuros.

Comando principal:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv
```

O processo:

1. carrega precos diarios disponiveis;
2. calcula features historicas por ativo;
3. gera `score_final`, componentes, tipo de sinal e explicacao;
4. mede retornos futuros em D+1, D+3, D+5 e D+10;
5. resume resultados por tipo de sinal e faixa de score;
6. sugere ajustes de peso sem alterar automaticamente o modelo.

A calibracao observa:

- correlacao entre `score_final` e retornos futuros;
- correlacao entre componentes e retornos futuros;
- retorno medio por quintil de score;
- monotonicidade do score;
- relacao entre `score_risco` e maxima adversa.

Se uma faixa alta de score nao entregar retorno maior, ou se muitos ativos ficarem concentrados em `80_100`, isso indica necessidade de revisar limites, pesos ou filtros de liquidez. Mesmo assim, o score legado permanece ativo ate haver evidencia historica suficiente.

## Calibracao Fora Da Amostra

A validacao fora da amostra compara treino e teste por data. Um componente so deve inspirar aumento de peso quando sua relacao com retorno futuro aparece no treino e tambem no teste.

Comando:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
```

O sistema pode sugerir que um componente seja mantido ou testado com mais peso apenas quando ele confirmar relacao positiva fora da amostra. Essa sugestao nao altera pesos automaticamente.

## Limitacoes

- O modo demo tem poucos ativos e tende a distorcer estatisticas de distribuicao.
- A comparacao intraday ainda nao usa noticias, valuation ou contexto macro.
- O score de tendencia intraday ainda usa proxies simples quando nao ha historico carregado.
- A calibracao deve ser feita com dados reais e historico suficiente.
