# Inteligência Integrada por Ativo

A Fase 24 cria um snapshot analítico por ativo, conectando camadas já existentes do projeto sem alterar o score principal, o ranking padrão ou qualquer filtro operacional.

## Objetivo

Consolidar, por ticker, sinais técnicos quantitativos, score quant, valuation/fundamentos, eventos, regimes de mercado, opções e governança em uma leitura auditável.

Essa leitura usa linguagem de estudo:

- ativo em estudo;
- assimetria a investigar;
- sinal em observação;
- divergência técnica/fundamentalista;
- bloqueado por governança;
- dados insuficientes.

## População Histórica

Para criar snapshots históricos integrados por ativo e data:

```powershell
python -m src.scanners.populate_asset_intelligence_history --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
```

Quando alguma camada estiver ausente, o campo fica vazio e o `data_quality_score` cai. A rotina não quebra por camada faltante e não representa recomendação.

## Fontes Integradas

- Técnica: `technical_feature_snapshots`, `technical_setup_signals`, `technical_walk_forward_runs`.
- Quant: `historical_backtest_results`, `governance_reviews`, `score_calibration_runs`.
- Valuation/fundamentos: arquivos do `12_PYTHON/pipeline banco completo`, especialmente `outputs/Valuation_<TICKER>_*.xlsx`.
- Eventos: `market_events` e `event_coverage_runs`.
- Regimes: `market_regime_daily`.
- Opções: `option_structure_candidates` e `option_walk_forward_runs`.

## Diagnóstico Local do Valuation

O repositório local possui o projeto `12_PYTHON/pipeline banco completo` com diretórios `outputs`, `config`, `data`, `modules`, `cache` e `logs`. A integração reutiliza o bridge existente `src/integration/valuation_bridge.py`, que procura planilhas `Valuation_<TICKER>_*.xlsx` e extrai preço justo e upside quando possível.

Se o arquivo de valuation não existir para um ticker, o snapshot não quebra: marca `valuation_available = False` e reduz a confiança da leitura.

## Comando Operacional

```bash
python -m src.scanners.asset_intelligence_snapshot --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
```

## Histórico Comparativo

Após salvar múltiplos snapshots, compare o penúltimo e o último registro por ativo:

```bash
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
```

Os diffs são persistidos em `asset_intelligence_diffs` e explicam por que status, score, governança, valuation, evento, regime ou opções mudaram.

## Interpretação

O `integrated_score` é apenas analítico. Ele combina disponibilidade de dados, técnico, quant, valuation, eventos, regime, opções e governança para priorizar investigação. Não substitui o score principal.

Status possíveis incluem:

- `ALTA_CONVERGENCIA_ANALITICA`
- `ASSIMETRIA_A_INVESTIGAR`
- `APENAS_MONITORAR`
- `DIVERGENCIA_TECNICA_VALUATION`
- `DIVERGENCIA_QUANT_TECNICA`
- `BLOQUEADO_GOVERNANCA`
- `BLOQUEADO_DADOS_INSUFICIENTES`

## Limitações

- Valuation depende de arquivos locais do pipeline externo.
- Opções podem estar ausentes se não houver cadeia histórica suficiente.
- Eventos dependem de cobertura operacional.
- A leitura integrada não é recomendação financeira e não executa ordens.
## Integração com Risk Engine

A inteligência integrada pode incorporar campos opcionais do snapshot de risco:

- `ensemble_vol`
- `var_95`
- `expected_shortfall_95`
- `recommended_size`
- `recommended_position_value`
- `risk_status`
- `risk_limiting_factor`
- `risk_explanation`

Quando `risk_status` estiver bloqueado, a governança integrada reduz a confiança e impede classificação como `ALTA_CONVERGENCIA_ANALITICA`. Esse comportamento é apenas analítico e não altera score principal, ranking ou execução.

Os snapshots integrados podem alimentar o paper trading como sinais em estudo, desde que não estejam bloqueados por governança.
