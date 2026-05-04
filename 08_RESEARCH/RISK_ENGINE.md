# Risk Engine

Motor de deteccao e classificacao de riscos.

## Tipos de Risco

- **Operacional** — Falhas de execucao, problemas de gestao, dependencia de pessoas-chave
- **Financeiro** — Alavancagem excessiva, descasamento de moeda, liquidez, refinanciamento
- **Governanca** — Conflitos de interesse, falta de transparencia, historico de abusos
- **Macro** — Exposicao a juros, cambio, ciclos economicos, regulacao

## Funcao

Detectar riscos relevantes de forma sistematica, cruzando:
1. Dados financeiros (Financial Engine)
2. Eventos macro (Macro News Engine)
3. Avaliacao de governanca (Governance Engine)

## Classificacao

| Nivel | Descricao |
|-------|-----------|
| 1 - Baixo | Risco identificado mas controlado |
| 2 - Moderado | Risco presente, requer monitoramento |
| 3 - Alto | Risco material, pode afetar tese |
| 4 - Critico | Risco que invalida ou suspende a tese |

## Regra

Todo risco identificado deve estar vinculado a pelo menos uma empresa ou setor.
Riscos sem conexao pratica nao devem ser registrados.

> Referencia: [[00_META/INTELLIGENCE_SYSTEM/INTELLIGENCE_LAYER]]
