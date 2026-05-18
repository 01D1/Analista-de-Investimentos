# Position Sizing

A camada de sizing calcula um tamanho sugerido para estudo, limitado pelo menor dos critérios válidos:

- risco fixo por stop;
- ATR;
- limite por VaR;
- liquidez;
- capital.

Campos principais:

- `size_fixed_risk`
- `size_atr`
- `size_var`
- `size_liquidity`
- `final_size`
- `final_position_value`
- `limiting_factor`
- `estimated_var`

O sizing não é aplicado automaticamente. Ele serve apenas para análise de risco e governança.
