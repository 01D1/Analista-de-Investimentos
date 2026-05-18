# Rastreabilidade dos Dados

A auditoria grava registros em `data_source_traceability` para ligar cada dominio de dado a sua fonte local ou URL configurada.

Campos principais:

- ticker;
- dominio do dado;
- fonte;
- tipo de origem;
- caminho ou URL;
- data da fonte;
- momento da coleta;
- quantidade de registros;
- metadata.

Essa trilha permite explicar de onde vieram os dados usados por eventos, B3, valuation, opcoes e inteligencia integrada. Quando uma fonte nao informa ticker, a trilha fica no nivel da fonte.

