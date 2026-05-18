# Governança Integrada

A governança integrada combina os bloqueios e limitações das camadas técnica, quant, eventos, regimes, opções e valuation.

## Estados

- `INTEGRATED_APPROVED_FOR_STUDY`: leitura suficiente para estudo analítico, sem caráter operacional.
- `INTEGRATED_OBSERVATION_ONLY`: manter em observação.
- `INTEGRATED_BLOCKED_GOVERNANCE`: uma camada crítica está bloqueada.
- `INTEGRATED_BLOCKED_DATA`: qualidade de dados insuficiente.
- `INTEGRATED_DIVERGENT_SIGNALS`: camadas relevantes divergem.
- `INTEGRATED_REQUIRES_REVIEW`: cobertura ou contexto exige revisão.
- `INTEGRATED_BLOCKED_LIQUIDITY`: liquidez impede uso do componente de opções.
- `INTEGRATED_BLOCKED_EVENT_RISK`: evento/contexto reduz confiança.

## Regras Gerais

- Técnico OOS bloqueado reduz ou bloqueia a leitura integrada.
- Quant governance bloqueada bloqueia o snapshot integrado.
- Valuation ausente reduz confiança, mas não quebra o processo.
- Evento com cobertura fraca impede conclusão forte sobre contexto.
- Opções bloqueadas por liquidez não viram argumento operacional.
- Data quality baixo gera `INTEGRATED_BLOCKED_DATA`.

## Saída

A avaliação retorna:

- status de governança integrada;
- nível de risco;
- nível de confiança;
- razões favoráveis;
- razões contrárias;
- ações necessárias.

Nenhum status integrado deve ser tratado como recomendação de compra ou venda.
## Bloqueios por Risco

A governança integrada considera `risk_status` quando houver snapshot do Risk Engine.

Regras:

- `RISK_BLOCKED_*`: bloqueia a leitura integrada por governança;
- `RISK_WARNING`: exige revisão e reduz confiança;
- `RISK_OK`: pode contar como evidência favorável, desde que as demais camadas também estejam consistentes.

O bloqueio por risco é diagnóstico. Ele não executa ordens e não aplica sizing automaticamente.
