# M014 S02.5 — Universe Expansion Audit

Arquivo CSV: `valuation_universe_audit_20260524.csv`

## Escopo

Universo alvo: Ibovespa + bancos + commodities + elétricas/utilities + varejo + seguradoras.

## Filtro aplicado

Foram excluídos:
- opções;
- derivativos;
- tickers com strike;
- tickers com expiration_date;
- códigos fora do padrão de ação/unit.

Padrão aceito: `AAAA3`, `AAAA4`, `AAAA5`, `AAAA6`, `AAAA11`.

## Totais

- Total de ações/units encontradas: 64
- Candidatos ao universo inicial: 34

## Por status

- NEEDS_CVM_DATA: 29
- NEEDS_SECTOR: 5

## Por grupo

- BANKS: 7
- COMMODITIES: 5
- IBOVESPA: 28
- RETAIL: 7
- UTILITIES: 4

## Semântica

- ELIGIBLE_NOW: possui dados mínimos e metadata suficiente para avançar.
- NEEDS_CVM_DATA: possui preço, mas não possui documentos CVM/RI reais.
- NEEDS_AI_ENTRY: possui dados, mas ainda não entrou no asset intelligence.
- NEEDS_SECTOR: falta setor confiável.
- NEEDS_MODEL: falta metodologia/modelo de valuation.
- LOW_LIQUIDITY_OR_IGNORE: fora do universo inicial definido.
- UNSUPPORTED: reservado para ativos não suportados.

Nenhum dado foi alterado. Nenhum valuation foi calculado. Nenhum dado mockado foi criado.
