# Backtest Técnico

O backtest técnico em `src/technical/technical_backtest.py` mede retornos futuros após setups detectados.

Métricas:

- retornos futuros D+1, D+3, D+5 e D+10;
- hit rate por horizonte;
- máxima excursão favorável;
- máxima excursão adversa;
- resumo por setup, status técnico, regime e contexto, quando essas colunas existirem.

Limitações:

- é preliminar e depende da qualidade do histórico diário;
- custos e slippage só entram quando disponíveis no dataset;
- não valida automaticamente fora da amostra;
- não promove setup para uso operacional.

Para validação fora da amostra, use o walk-forward técnico documentado em `WALK_FORWARD_TECNICO.md`.
