# Confiabilidade dos Dados

O modulo `src/data_quality/source_reliability.py` transforma resultados de auditoria em um score de 0 a 100.

Componentes:

- disponibilidade;
- atualizacao;
- completude;
- rastreabilidade;
- origem primaria/secundaria;
- consistencia operacional.

Classes:

- `CONFIAVEL`
- `ACEITAVEL`
- `FRAGIL`
- `INSUFICIENTE`
- `INDISPONIVEL`

Uma fonte primaria ausente ou com erro gera alerta operacional. Fonte derivada ou secundaria pode reduzir a confianca, mas nao bloqueia automaticamente nenhuma decisao do scanner.

Quando a confiabilidade cair por lacuna de ingestao, rode a reconciliacao:

```bash
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
```
