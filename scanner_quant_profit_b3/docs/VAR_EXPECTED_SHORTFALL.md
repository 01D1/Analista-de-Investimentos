# VaR e Expected Shortfall

O Risk Engine calcula VaR e Expected Shortfall como medidas estatísticas de perda potencial.

Modelos:

- VaR paramétrico com z-score de 95% ou 99%;
- VaR histórico por quantil da série de retornos;
- VaR modificado por Cornish-Fisher;
- Expected Shortfall histórico como perda média nos piores cenários além do VaR;
- Expected Shortfall paramétrico.

Quando a amostra é insuficiente, as funções retornam diagnóstico e `NaN`, sem quebrar o pipeline.

Essas métricas indicam risco estimado. Não são garantia de perda máxima e não constituem recomendação.
