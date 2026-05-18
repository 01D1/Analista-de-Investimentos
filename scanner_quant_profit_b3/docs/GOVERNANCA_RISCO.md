# Governança de Risco

Status possíveis:

- `RISK_OK`
- `RISK_WARNING`
- `RISK_BLOCKED_VAR`
- `RISK_BLOCKED_VOLATILITY`
- `RISK_BLOCKED_LIQUIDITY`
- `RISK_BLOCKED_DRAWDOWN`
- `RISK_BLOCKED_DATA`

Critérios avaliados:

- VaR acima do limite analítico;
- volatilidade extrema;
- liquidez insuficiente ou sizing final nulo;
- dados insuficientes;
- risco estatístico elevado.

Quando `risk_status` é bloqueado, a inteligência integrada não classifica o ativo como `ALTA_CONVERGENCIA_ANALITICA`. O bloqueio é analítico e não executa qualquer ação operacional.
