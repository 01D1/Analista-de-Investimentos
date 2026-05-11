# Contratos De Qualidade Das Fontes

## Objetivo

Contratos de qualidade definem o mínimo esperado para cada fonte de eventos. Eles ajudam a separar uma fonte saudável de uma fonte tecnicamente disponível, mas pobre ou desatualizada.

## Configuração

Os contratos ficam em `config/source_quality_contracts.yaml`.

Cada fonte pode definir:

- se é obrigatória;
- idade máxima dos dados;
- número mínimo de registros;
- cobertura mínima;
- severidade se falhar.

## Status

- `PASS`: contrato atendido;
- `FAIL`: contrato obrigatório ou crítico não atendido;
- `WARNING`: fonte opcional ou não crítica fora do padrão;
- `NOT_APPLICABLE`: fonte opcional sem health check;
- `NO_CONTRACT`: fonte sem contrato definido.

## Uso

Os contratos são avaliados no relatório semanal e na Mesa Quant. Eles não bloqueiam o scanner por conta própria, mas podem gerar alertas:

- `SOURCE_CONTRACT_FAILED`;
- `SOURCE_CONTRACT_WARNING`.

## Interpretação

Um contrato `FAIL` não significa que o dado está errado. Significa que ele não atende ao nível mínimo para sustentar conclusões fortes sobre eventos, cobertura ou ausência de notícia.

## Limitações

- A cobertura por fonte depende dos metadados salvos nas rotinas de eventos.
- Fontes com poucos eventos relevantes podem falhar por baixa contagem mesmo funcionando corretamente.
- Contratos devem ser revisados conforme o universo monitorado cresce.
