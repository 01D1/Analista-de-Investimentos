# Relatório Integrado por Ativo

O relatório integrado gera um Markdown por ticker a partir do último snapshot salvo em `asset_intelligence_snapshots`.

## Comando

```bash
python -m src.scanners.generate_asset_intelligence_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence
```

Se não houver snapshot salvo, o comando tenta construir uma leitura integrada em memória com os dados disponíveis.

## Estrutura do Relatório

1. Resumo executivo.
2. Análise técnica quantitativa.
3. Sinal quantitativo.
4. Valuation e fundamentos.
5. Eventos e notícias.
6. Regime de mercado.
7. Opções e estruturas.
8. Governança integrada.
9. Conclusão analítica.

## Uso Esperado

O relatório é uma peça de auditoria e estudo. Ele registra divergências, bloqueios, dados ausentes e ações necessárias. Não é call operacional e não substitui o ranking principal.

## Relatório de Mudanças

Para auditar como a leitura mudou ao longo do tempo:

```bash
python -m src.scanners.generate_asset_change_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence_changes
```

Esse relatório usa `asset_intelligence_snapshots` e `asset_intelligence_diffs`.
## Seção de Risco

O relatório integrado por ativo passa a incluir uma seção de `Risco e Volatilidade` com:

- regime de volatilidade;
- volatilidade ensemble;
- VaR 95%;
- Expected Shortfall 95%;
- sizing sugerido para estudo;
- valor sugerido para estudo;
- fator limitante;
- status e explicação de risco.

Esses campos dependem de `risk_snapshots`. Caso não existam, o relatório mantém os campos como ausentes e não quebra a geração.
