# Scanner Quant Profit + B3

Scanner quantitativo para acompanhar acoes e opcoes da B3 usando duas fontes principais:

- dados em tempo real do Profit exportados para Excel via RTD;
- historico diario da B3 via COTAHIST.

O projeto le a planilha do Profit, grava snapshots no SQLite, calcula sinais intraday, cruza esses sinais com opcoes do COTAHIST e expoe os resultados em linha de comando, arquivos CSV e dashboard Streamlit.

> Este sistema e apenas uma ferramenta de apoio analitico. Ele nao envia ordens e nao substitui avaliacao operacional, controle de risco ou recomendacao profissional.

## O Que Ele Faz

- Coleta cotacoes em tempo real do Profit por uma planilha Excel RTD.
- Salva snapshots intraday em banco SQLite.
- Gera ranking de acoes por forca, volume, negocios, posicao no range e rompimento.
- Baixa e processa arquivos COTAHIST da B3.
- Identifica opcoes relacionadas aos ativos configurados.
- Cruza sinais de acoes com opcoes liquidas.
- Calcula setups da estrategia `CALL_CONTINUIDADE`.
- Gera relatorios CSV, diario de trades, backtests e dashboard Streamlit.
- Estima risco institucional com volatilidade, VaR, Expected Shortfall, sizing sugerido para estudo, stress tests e governança de risco.

## Requisitos

- Python 3.10 ou superior.
- Windows, Excel e Profit Pro para uso com RTD em tempo real.
- Acesso a internet para baixar COTAHIST da B3.
- Uma planilha Excel com as formulas RTD do Profit.

Para usar apenas modo demo, COTAHIST, backtests e dashboard com dados ja salvos, o Profit nao precisa estar aberto.

## Instalacao

No PowerShell, entre na pasta do projeto:

```powershell
cd "Analista de Investimentos\scanner_quant_profit_b3"
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item config.example.yaml config.yaml
Copy-Item config_quant.example.yaml config_quant.yaml
```

Depois inicialize o banco:

```powershell
python -m src.db.init_db
```

O banco padrao e criado em `data/database/scanner_quant.db`. Os arquivos `config.yaml` e `config_quant.yaml` sao locais; para publicar no GitHub, mantenha os modelos `config.example.yaml` e `config_quant.example.yaml`.

## Risk Engine

Para gerar snapshots analíticos de risco:

```powershell
python -m src.scanners.risk_engine_snapshot --tickers PETR4 VALE3 ITUB4 --capital 100000 --risk-pct 0.005 --save-db --csv
```

O comando calcula volatilidade, VaR, Expected Shortfall, sizing sugerido para estudo, stress tests e governança de risco. Ele não executa ordens, não altera score principal e não substitui o ranking padrão.

## Paper Trading

Para simular uma carteira com sinais, custos, risco e governança:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --save-db --csv
```

O resultado é uma carteira simulada com ordens simuladas, posições, equity curve, exposição, VaR/ES agregado e governança. Nada é enviado ao mercado.

## Cobertura de Fontes de Sinal

Antes de validar hipóteses OOS por múltiplas fontes, popule e cheque as fontes em estudo:

```powershell
python -m src.scanners.populate_technical_signals --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --dedupe --save-db --csv
python -m src.scanners.populate_asset_intelligence_history --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
python -m src.scanners.signal_coverage_check --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
python -m src.scanners.limit_signal_source_calibration --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.cost_slippage_diagnostics --paper-run-id 2 --save-db --csv
python -m src.scanners.fine_cost_diagnostics --paper-run-id 2 --save-db --csv
python -m src.scanners.cost_reduction_simulation --paper-run-id 2 --save-db --csv
python -m src.scanners.cost_frontier_analysis --cost-reduction-run-id 3 --save-db --csv
```

### Relatório semanal Radar Macro

Gera o research output institucional consolidando dados, sinais, valuation, eventos, regimes, opções, risco, paper trading, governança e hipóteses. O relatório é não recomendativo e não altera modelos, score, ranking ou parâmetros.

```bash
python -m src.scanners.generate_radar_macro_weekly --start 2026-01-02 --end 2026-04-30 --save-db --md --pdf
```

Se `technical` ou `integrated` estiverem com cobertura insuficiente, a validação OOS registra bloqueio por amostra e não conclui robustez multi-fonte.

O deep dive aprofunda as melhores hipóteses do ranking, separando condição de fragilidade por fonte de sinal, custo, slippage, regime e ativo. O resultado é explicação de bloqueio ou observação analítica, sempre como não recomendação.

A calibração `LIMIT_SIGNAL_SOURCE` testa variações paramétricas com controle de custo e controle de slippage antes de qualquer observação recorrente.

O diagnóstico de custo/slippage mede cost drag, turnover, liquidez e break-even para explicar se o gargalo vem de giro, fonte de sinal, ativo, regime ou premissas de execução.

O diagnóstico fino de custos separa custo atribuído entre entrada, saída, rebalanceamento, eventos de saída, fechamento de simulação e metadado ausente/UNKNOWN. Ele não reescreve histórico antigo; apenas diagnostica e enriquece novas simulações.

A simulação de redução de custos testa variantes específicas de rebalanceamento e regras de saída contra o baseline, com governança própria. Variante simulada não é recomendação e não é aplicada automaticamente.

A fronteira custo-retorno-drawdown identifica variantes não dominadas e trade-offs entre redução de custo, retorno, drawdown e turnover. Estar na fronteira não libera aplicação automática.

Simulação avançada:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --exit-mode advanced --stop-loss-pct 0.03 --take-profit-pct 0.06 --trailing-stop-pct 0.04 --daily-loss-limit-pct 0.02 --enable-rebalancing --save-db --csv
```

Investigações analíticas sobre fragilidade:

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
```

O comando testa hipóteses simuladas, como exclusão analítica de ativo crítico, redução de fonte frágil e carteira sem rebalanceamento. É apenas comparação antes/depois em paper trading.

Validação OOS de hipótese promissora:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
```

Essa validação compara a hipótese contra baseline em janelas fora da amostra e cenários de custo, slippage, regime e fonte de sinal. A hipótese não é aplicada automaticamente.

Reteste robusto com diagnóstico de cobertura:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --train-months 1 --test-months 1 --include-cost-scenarios --include-regimes --signal-sources quant technical integrated --expand-signal-coverage --filter-coverage --save-db --csv
```

## Configuracao Da Planilha RTD

1. Abra o Profit Pro.
2. Abra sua planilha RTD no Excel.
3. Confirme que os valores estao atualizando.
4. Mantenha o Excel aberto enquanto o scanner estiver rodando.
5. Ajuste o caminho da planilha no seu `config.yaml`.

Exemplo:

```yaml
profit_excel_path: "data/realtime/RTD PROFIT.xlsx"
profit_sheet_name: "Planilha1"
database_path: "data/database/scanner_quant.db"
snapshot_interval_seconds: 5
```

A planilha deve conter, quando disponiveis, as seguintes colunas:

| Coluna no Excel | Campo interno |
|---|---|
| `Asset` | `asset` |
| `Data` | `trade_date` |
| `Hora` | `trade_time` |
| `Último` | `last` |
| `Abertura` | `open` |
| `Máximo` | `high` |
| `Mínimo` | `low` |
| `Fechamento Anterior` | `prev_close` |
| `Variação` | `variation_pct` |
| `Variação(pts)` | `variation_pts` |
| `Negócios` | `trades` |
| `Quantidade` | `quantity` |
| `Volume` | `volume` |

Os ativos monitorados ficam em `ativos_base` no `config.yaml`.

## Rodar O Scanner

Teste uma leitura unica com dados simulados:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo
```

Rode uma leitura unica com dados reais do Profit:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --csv
```

Rode continuamente:

```powershell
python -m src.scanners.realtime_profit_scanner --interval 5 --top 10 --csv
```

### Modo De Comparacao De Scores

O scanner calcula o score legado e o score quantitativo composto em paralelo. Para imprimir uma auditoria comparando os dois:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores
```

Para salvar CSV com componentes do score e tipo de divergencia:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --csv
```

Para salvar a rodada de calibração no SQLite:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --save-calibration
```

Esse modo grava estatísticas da distribuição do `score_final` e detalhes por ativo para análise futura.

Durante a execucao, o scanner:

1. le a planilha RTD;
2. normaliza os campos;
3. salva snapshots no SQLite;
4. calcula metricas intraday;
5. gera o score legado de 0 a 100;
6. calcula tambem o score quantitativo composto em paralelo;
7. classifica os ativos como `COMPRA/FORÇA`, `OBSERVAR`, `NEUTRO` ou `FRAQUEZA`;
8. grava componentes novos como momentum, tendencia, liquidez, volatilidade, risco e explicacao;
9. opcionalmente exporta CSV em `data/reports`.

## Baixar Dados Da B3

Baixe e processe um ano especifico do COTAHIST:

```powershell
python -m src.collectors.b3_cotahist_collector --year 2026
```

Baixe todos os anos configurados em `config.yaml`:

```powershell
python -m src.collectors.b3_cotahist_collector --all
```

Apenas baixe e extraia o arquivo, sem importar para o banco:

```powershell
python -m src.collectors.b3_cotahist_collector --year 2026 --download-only
```

Os arquivos ZIP/TXT ficam em `data/raw`. Os dados processados sao gravados no SQLite, na tabela `cotahist_daily`. A view `b3_quotes` existe para compatibilidade com scanners que ainda usam o nome antigo.

## Cruzar Acoes E Opcoes

Depois de ter sinais do Profit e dados COTAHIST no banco, rode:

```powershell
python -m src.scanners.combined_stock_options_scanner --min-volume 100000 --min-trades 10 --top 30 --csv
```

Esse comando busca o ultimo sinal intraday de cada acao, encontra opcoes relacionadas pelo prefixo do ativo e gera um ranking combinado.

Para ver um scanner simples de opcoes do ultimo pregao importado:

```powershell
python -m src.scanners.option_scanner
```

Para rodar o scanner inteligente de opções, com moneyness, valor intrínseco/extrínseco, Greeks aproximados, ranking de estruturas e governança analítica:

```powershell
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

Esse modo classifica opções e estruturas como material para estudo, observação ou bloqueio. Ele não executa ordens e não é recomendação financeira.

Para construir histórico de cadeia e preparar backtest preliminar de estruturas:

```powershell
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```

## Estrategia CALL_CONTINUIDADE

Rode o motor de decisao de opcoes:

```powershell
python -m src.strategies.call_continuity_strategy --top 20 --save
```

Para adicionar setups aprovados ao diario:

```powershell
python -m src.strategies.call_continuity_strategy --top 20 --save --journal
```

Os parametros de risco, filtros, score e integracoes ficam em `config_quant.yaml`. Use `config_quant.example.yaml` como modelo inicial.

## Backtest E Relatorios

Backtest simulado a partir dos sinais:

```powershell
python run_backtest.py --mode simulate --capital 10000 --risk 0.005 --top 20 --save
```

Backtest usando o diario de trades:

```powershell
python run_backtest.py --mode journal --capital 10000 --risk 0.005 --save
```

Backtest historico do `score_final` usando COTAHIST processado:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv
```

Com tickers especificos:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --tickers PETR4 VALE3 ITUB4 --csv
```

Para salvar o resultado estatistico no SQLite:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db
```

Esse backtest mede retornos futuros por tipo de sinal, faixa de score e componentes do modelo. Ele serve para calibracao estatistica; nao substitui o score legado automaticamente.

Backtest líquido com custos, slippage e liquidez mínima:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db --net --cost-bps 10 --slippage-bps 5 --min-volume 5000000
```

Backtest líquido com filtros de qualidade:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv
```

Otimização exploratória de thresholds, sem aplicar automaticamente ao ranking:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv
```

Walk-forward dos filtros, usando thresholds escolhidos no treino e avaliados no teste seguinte:

```powershell
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
```

Review de governança do último walk-forward dos filtros:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
```

Análise de regimes de mercado:

```powershell
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
```

Análise walk-forward e fora da amostra:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
```

Esse comando mede se sinais e faixas de score que funcionaram no treino continuam funcionando no teste seguinte. Ele não altera pesos automaticamente.

Walk-forward usando retorno líquido:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db --net
```

Gerar relatorios operacionais:

```powershell
python run_report.py --capital 10000 --account 10000 --risk 0.005 --top 20 --plans
```

## Dashboard Streamlit

Rode o dashboard principal:

```powershell
python -m streamlit run app.py
```

O app unificado abre paginas para radar quant, valuation engine, performance, calendario e agendador. Ele usa os dados do SQLite, CSVs gerados e configuracoes locais.

Tambem existe um dashboard de oportunidades:

```powershell
python -m streamlit run src/reports/opportunity_dashboard.py
```

### Rodar Mesa Quant Streamlit

A Mesa Quant mostra backtest histórico, calibração do score, comparação entre score legado e `score_final`, sinais por ativo, componentes e diagnósticos.

Antes de abrir, gere uma rodada de calibração e um backtest salvo no SQLite:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --save-calibration
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv --save-db
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

Abra a mesa:

```powershell
python -m streamlit run src/reports/quant_mesa_dashboard.py --server.headless true
```

Esse dashboard é uma camada de análise estatística. Ele não substitui o score legado, não muda o ranking principal e não representa recomendação financeira.

### Contexto De Eventos E Noticias

Importe eventos locais/manuais:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events_example.csv --save-db
```

Rode o backtest marcando sinais com eventos:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
```

Analise eventos contra sinais historicos:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

Rotina operacional de eventos com News Hunter, CVM/IPE, releases, calendário macro local e cobertura por regime:

```powershell
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
```

As fontes ficam em `config/events.yaml`. A rotina não faz scraping pesado; ela lê arquivos e bancos locais, deduplica eventos, mede cobertura geral e grava cobertura por regime quando `market_regime_daily` existir.

Essa camada usa CSV/local primeiro, nao faz scraping pesado e nao altera score, ranking ou filtros automaticamente.

### Saúde Das Fontes E Rotina Diária

Verifique a saúde das fontes:

```powershell
python -m src.scanners.source_health_check --save-db --csv
```

Rode a rotina diária completa:

```powershell
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
```

Calcule SLA e observabilidade operacional:

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

Rode retenção em modo seguro:

```powershell
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
```

Execução real de retenção exige confirmação:

```powershell
python -m src.scanners.data_retention_cleanup --execute --confirm --archive --save-db --csv
```

Gere o relatório semanal operacional:

```powershell
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

Rodar via PowerShell no Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/windows/run_daily_quant_routine.ps1
```

O script salva logs em `logs/`. Para agendar no Windows Task Scheduler, veja `scripts/windows/create_task_scheduler_command.md`.

## Validacao Local

Rode a suite automatizada:

```powershell
python -m pytest -q
```

Rode os smoke tests principais:

```powershell
python -m src.db.init_db
python -m src.scanners.realtime_profit_scanner --once --top 3 --demo
```

O projeto tambem inclui um workflow de GitHub Actions para rodar os testes em Windows com Python 3.10.

## Documentacao Tecnica

- `docs/DIAGNOSTICO_FASE1.md` — diagnostico da arquitetura atual, riscos e plano de refatoracao.
- `docs/CORE_QUANTITATIVO_FASE2.md` — desenho do core quantitativo minimo criado na Fase 2.
- `docs/SCORE_QUANTITATIVO.md` — metodologia, comparacao e calibracao do score composto.
- `docs/BACKTEST_HISTORICO.md` — metodologia do backtest diario com COTAHIST e calibracao estatistica.
- `docs/MESA_QUANT.md` — uso da Mesa Quant Streamlit, abas, metricas e fluxo operacional.
- `docs/WALK_FORWARD.md` — validacao fora da amostra, janelas walk-forward e alertas de overfitting.
- `docs/CUSTOS_E_EXECUCAO.md` — custos, slippage, liquidez mínima e retorno líquido.
- `docs/FILTROS_E_CAPACIDADE.md` — filtros de qualidade, thresholds, capacidade por liquidez e sizing.
- `docs/WALK_FORWARD_FILTROS.md` — validação fora da amostra dos filtros e thresholds.
- `docs/GOVERNANCA_QUANT.md` — critérios de aprovação/rejeição de candidatos quantitativos.
- `docs/REGIMES_DE_MERCADO.md` — regimes de tendência, volatilidade, liquidez, risco e governança por regime.
- `docs/EVENTOS_E_NOTICIAS.md` — importação de eventos, link evento-sinal e análise event-driven.
- `docs/PIPELINE_EVENTOS.md` — conectores locais, deduplicação, classificação e cobertura de eventos.
- `docs/ROTINA_EVENTOS.md` — rotina operacional de eventos, calendário macro e cobertura por regime.
- `docs/SAUDE_DAS_FONTES.md` — health checks das fontes locais.
- `docs/ROTINA_DIARIA.md` — orquestração diária, registros e status.
- `docs/ALERTAS_OPERACIONAIS.md` — alertas persistidos e Telegram opcional.
- `docs/WINDOWS_TASK_SCHEDULER.md` — execução automática no Windows.
- `docs/SLA_DADOS.md` — SLA historico, disponibilidade e confiabilidade por fonte.
- `docs/OBSERVABILIDADE_OPERACIONAL.md` — snapshots, alertas recorrentes e tendencia operacional.
- `docs/RETENCAO_E_LIMPEZA.md` — política de retenção, dry-run, archive e limpeza segura.
- `docs/CONTRATOS_QUALIDADE_FONTES.md` — mínimos de idade, registros e cobertura por fonte.
- `docs/RELATORIO_SEMANAL_OPERACIONAL.md` — relatório consolidado de rotina, SLA, cobertura e governança.
- `docs/OPCOES_INTELIGENTES.md` — scanner analítico de opções, métricas, Greeks, ranking e governança.
- `docs/ESTRUTURAS_OPCOES.md` — estruturas iniciais, payoff, risco e interpretação dos status.
- `docs/BACKTEST_OPCOES.md` — desenho futuro e limitações de backtest histórico de opções.
- `docs/HISTORICO_CADEIA_OPCOES.md` — construção de snapshots históricos da cadeia de opções.
- `docs/BACKTEST_ESTRUTURAS_OPCOES.md` — backtest preliminar com bid/ask, custos e vencimento.
- `docs/CUSTOS_OPCOES.md` — custos por perna, slippage e qualidade de execução.
- `docs/WALK_FORWARD_OPCOES.md` — validação fora da amostra de estruturas de opções.
- `docs/GOVERNANCA_OOS_OPCOES.md` — governança específica do walk-forward de opções.
- `docs/ESTABILIDADE_OPCOES.md` — estabilidade por vencimento, moneyness, liquidez, regime e evento.

## Dados De Entrada

| Fonte | Uso |
|---|---|
| Planilha Profit RTD | Cotacoes intraday, volume, negocios, maxima, minima e variacao |
| B3 COTAHIST | Historico diario de acoes e opcoes |
| `config.yaml` | Caminhos, ativos monitorados, filtros intraday e anos da B3 |
| `config_quant.yaml` | Parametros da estrategia, risco, score e integracoes |
| Diario de trades | Historico manual/operacional para performance e backtest |
| CSV de eventos | Eventos, notícias, fatos relevantes, resultados e contexto macro/setorial |
| `config/events.yaml` | Fontes locais de eventos, News Hunter, CVM, releases e calendário macro |

## Dados De Saida

| Saida | Conteudo |
|---|---|
| SQLite | Snapshots do Profit, sinais, COTAHIST, diario e Greeks |
| CSV em `data/reports` | Rankings, setups, backtests e relatorios |
| Diario em `data/journal` | Setups adicionados para acompanhamento |
| Dashboard Streamlit | Visualizacao operacional dos rankings, performance e calendario |

Principais tabelas criadas no SQLite:

- `profit_snapshots`
- `realtime_signals`
- `cotahist_daily`
- `b3_quotes` (view de compatibilidade)
- `trade_journal`
- `options_greeks_snapshot`
- `score_calibration_runs`
- `score_calibration_assets`
- `historical_backtest_runs`
- `historical_backtest_results`
- `walk_forward_runs`
- `walk_forward_results`
- `quality_filter_runs`
- `threshold_optimization_runs`
- `filter_walk_forward_runs`
- `filter_walk_forward_results`
- `governance_reviews`
- `market_regime_daily`
- `regime_backtest_summary`
- `market_events`
- `signal_event_links`
- `event_context_runs`
- `event_coverage_runs`
- `event_coverage_by_regime`
- `source_health_checks`
- `daily_routine_runs`
- `operational_alerts`
- `source_sla_snapshots`
- `operational_observability_snapshots`
- `retention_cleanup_runs`
- `retention_cleanup_details`

## Limitacoes

- O scanner depende da planilha RTD estar aberta e atualizando no Excel.
- Fora do pregao, os dados reais podem ficar vazios ou defasados; use `--demo` para teste tecnico.
- O layout da planilha precisa manter nomes de colunas compativeis.
- O download do COTAHIST depende da disponibilidade do endpoint publico da B3.
- A relacao entre opcao e ativo objeto usa inferencia por prefixo; isso pode exigir revisao em casos especiais.
- Scores e filtros sao heuristicas, nao garantia de retorno.
- Backtests podem sofrer vieses de dados, liquidez, slippage e custos.
- Thresholds e filtros sao exploratorios e podem sofrer overfitting se calibrados em amostra pequena.
- A camada de eventos depende da cobertura do CSV local; ausência de evento importado não prova ausência real de notícia.
- A cobertura por regime depende de `market_regime_daily`; se estiver ausente, a rotina diária apenas salva a cobertura geral.
- Nenhum modulo envia ordens automaticamente.

## Fluxo Recomendado

```powershell
python -m src.db.init_db
python -m src.collectors.b3_cotahist_collector --year 2026
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo
python -m src.scanners.realtime_profit_scanner --once --top 10 --csv
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --net --cost-bps 10 --slippage-bps 5 --min-volume 5000000
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
python -m src.scanners.import_market_events --csv data/events/market_events_example.csv --save-db
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
python -m src.scanners.source_health_check --save-db --csv
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
python -m src.scanners.technical_analysis_scanner --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --save-db --csv --with-backtest
python -m src.scanners.technical_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --train-months 3 --test-months 1 --dedupe --optimize-thresholds --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv
python -m streamlit run src/reports/quant_mesa_dashboard.py --server.headless true
python -m src.scanners.combined_stock_options_scanner --top 30 --csv
python -m src.strategies.call_continuity_strategy --top 20 --save
python -m streamlit run app.py
```

## Status

Projeto em desenvolvimento ativo. Antes de usar em rotina operacional, valide caminhos, qualidade dos dados, liquidez das opcoes, custos, parametros de risco, setups tecnicos e consistencia dos resultados exportados. A camada tecnica e analitica e nao altera o score principal.
## Fase 24 - Inteligência Integrada por Ativo

A camada de inteligência integrada consolida técnico quantitativo, score quant, valuation/fundamentos, eventos, regimes, opções e governança em snapshots por ticker. Ela não altera o score principal, não substitui o ranking e não gera recomendação financeira.

Comandos:

```bash
python -m src.scanners.asset_intelligence_snapshot --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
python -m src.scanners.generate_asset_intelligence_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence
```

Documentação:

- `docs/INTELIGENCIA_INTEGRADA_ATIVOS.md`
- `docs/GOVERNANCA_INTEGRADA.md`
- `docs/RELATORIO_INTEGRADO_ATIVO.md`

## Fase 25 - Histórico e Mudanças da Inteligência Integrada

A camada de histórico compara snapshots integrados por ativo e cria trilha auditável de mudanças de status, score, governança, valuation, eventos, regimes, opções e qualidade de dados.

Comandos:

```bash
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
python -m src.scanners.generate_asset_change_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence_changes
```

Documentação:

- `docs/HISTORICO_INTELIGENCIA_ATIVOS.md`
- `docs/MUDANCAS_STATUS_INTEGRADO.md`
- `docs/ALERTAS_INTELIGENCIA_INTEGRADA.md`
## Auditoria de fontes de dados

```bash
python -m src.scanners.data_source_audit --save-db --csv
python -m src.scanners.data_source_audit --sources ri --check-ri-online --save-db --csv
python -m src.scanners.b3_reconciliation --csv --save-db
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```

## Fase 32 - Robustez das Regras de Paper Trading

A camada de robustez compara simulação simples vs avançada, otimiza parâmetros de saída como estudo e roda walk-forward fora da amostra. Ela não executa ordens reais, não recomenda compra/venda e não aplica parâmetros automaticamente.

Comandos:

```bash
python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv
python -m src.scanners.compare_paper_simulations --simple-run-id 1 --advanced-run-id 2 --save-db --csv
python -m src.scanners.generate_paper_rules_report --output-dir data/reports/paper_rules
```

Documentação:

- `docs/PAPER_TRADING_WALK_FORWARD.md`
- `docs/PAPER_TRADING_ROBUSTEZ_REGRAS.md`
- `docs/PAPER_TRADING_OTIMIZACAO_SAIDAS.md`

## Fase 33 - Validação Multi-Cenário do Paper Trading

A validacao multi-cenario testa a carteira simulada em multiplos periodos, fontes de sinal, custos, slippage e regimes. Ela serve para separar parametro em estudo de melhora potencialmente superajustada.

Comando:

```bash
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
python -m src.scanners.generate_paper_scenario_report --output-dir data/reports/paper_scenario_validation
```

Documentação:

- `docs/PAPER_TRADING_VALIDACAO_MULTICENARIO.md`
- `docs/PAPER_TRADING_CENARIOS_CUSTO.md`
- `docs/PAPER_TRADING_FONTES_SINAL.md`

## Fase 34 - Diagnóstico de Fragilidade da Carteira Simulada

A camada de fragilidade decompõe P&L, custos, slippage, drawdown, ativos e fontes de sinal para explicar por que uma carteira simulada perde robustez.

Comandos:

```bash
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
python -m src.scanners.generate_paper_fragility_report --output-dir data/reports/paper_fragility
```

Documentação:

- `docs/PAPER_TRADING_FRAGILIDADE.md`
- `docs/PAPER_TRADING_DRAWDOWN_ATTRIBUTION.md`
- `docs/PAPER_TRADING_CUSTO_FRAGILIDADE.md`
