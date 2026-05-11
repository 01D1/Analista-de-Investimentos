# RELATORIO_REVISAO_VALUATION

Gerado em: 2026-05-04 21:59:13

## Resumo executivo

- Arquivos relacionados a valuation mapeados: **81** (79 Excel, 2 CSV).
- Workbooks canonicos em `outputs/valuations`: **18**.
- Abas Excel auditadas: **882**.
- Abas com pelo menos uma formula Excel: **40**.
- Achados: critica=0, alta=303, media=56, baixa=61.

## Metodologia

- Inventario recursivo de `.xlsx`, `.xlsm`, `.xls` e `.csv` ligados a valuation.
- Auditoria profunda aplicada aos workbooks canonicos em `outputs/valuations`; snapshots historicos em `outputs/Valuation_*.xlsx` foram inventariados por abas para evitar bloqueios e duplicidade de achados antigos.
- Leitura de workbooks com `openpyxl` em modo formulas e valores calculados.
- Varredura limitada a area operacional relevante: primeiras 500 linhas e 80 colunas por aba, para evitar ranges fantasmas de formatacao.
- Varredura de formulas quebradas, erros Excel, abas criticas sem formulas, anos duplicados/lacunosos e linhas financeiras vazias/zeradas.
- Testes de consistencia para DRE/DCF, BP, FCFE, FCFF, YoY e WACC quando os rotulos estavam presentes.
- Separacao entre erro objetivo, risco estrutural e premissa discutivel.

## Contagem por categoria

- dados: 118
- vinculo: 117
- dcf: 74
- escopo: 61
- balanco: 19
- datas: 16
- formula: 15

## Achados tecnicos

| Gravidade | Arquivo | Aba | Celula/intervalo | Problema | Impacto | Correcao sugerida |
|---|---|---|---|---|---|---|
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `E10` | FCFE nao reconcilia com componentes: 2020: esperado 11,851.62, encontrado 4,740.65. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `F10` | FCFE nao reconcilia com componentes: 2021: esperado -4,355.53, encontrado 7,337.73. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `G10` | FCFE nao reconcilia com componentes: 2022: esperado 5,434.62, encontrado 11,052.16. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `H10` | FCFE nao reconcilia com componentes: 2023: esperado 12,233.87, encontrado 11,944.39. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `I10` | FCFE nao reconcilia com componentes: 2024: esperado 1,772.91, encontrado 10,543.54. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `J10` | FCFE nao reconcilia com componentes: 2025: esperado -11,618.32, encontrado 5,479.25. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `K10` | FCFE nao reconcilia com componentes: 2026: esperado 18,658.48, encontrado 15,265.47. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `L10` | FCFE nao reconcilia com componentes: 2027: esperado 17,510.48, encontrado 16,469.26. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `M10` | FCFE nao reconcilia com componentes: 2028: esperado 19,768.81, encontrado 18,129.79. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `N10` | FCFE nao reconcilia com componentes: 2029: esperado 25,055.84, encontrado 19,765.89. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `O10` | FCFE nao reconcilia com componentes: 2030: esperado 27,915.03, encontrado 21,598.29. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `P10` | FCFE nao reconcilia com componentes: 2031: esperado 34,211.31, encontrado 23,369.92. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `Q10` | FCFE nao reconcilia com componentes: 2032: esperado 36,067.45, encontrado 24,709.08. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `R10` | FCFE nao reconcilia com componentes: 2033: esperado 38,099.47, encontrado 26,155.64. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `S10` | FCFE nao reconcilia com componentes: 2034: esperado 40,258.28, encontrado 27,692.29. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `T10` | FCFE nao reconcilia com componentes: 2035: esperado 42,624.70, encontrado 29,353.83. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Painel de Índices` | `9:9` | Linha critica sem valores: Capital de Giro Próprio (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Projeções Trimestrais` | `28:28` | Linha critica sem valores: Receita de Serviços (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Projeções Trimestrais` | `4:4` | Linha critica sem valores: Lucro Líquido (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `F5/F24` | Ativo total diferente de passivo total: 2020: ativo=1,604,653.79, passivo=0.00, diferenca=1,604,653.79. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `G5/G24` | Ativo total diferente de passivo total: 2021: ativo=1,675,572.19, passivo=0.00, diferenca=1,675,572.19. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `H5/H24` | Ativo total diferente de passivo total: 2022: ativo=1,799,615.68, passivo=0.00, diferenca=1,799,615.68. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `I5/I24` | Ativo total diferente de passivo total: 2023: ativo=1,927,523.25, passivo=0.00, diferenca=1,927,523.25. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `F10` | FCFE nao reconcilia com componentes: 2020: esperado 15,836.86, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `G10` | FCFE nao reconcilia com componentes: 2021: esperado 23,172.32, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `H10` | FCFE nao reconcilia com componentes: 2022: esperado 20,983.69, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `I10` | FCFE nao reconcilia com componentes: 2023: esperado 14,251.33, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `N10` | FCFE nao reconcilia com componentes: 2026: esperado 4,151.65, encontrado 8,041.86. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `O10` | FCFE nao reconcilia com componentes: 2027: esperado 11,149.09, encontrado 11,628.52. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `P10` | FCFE nao reconcilia com componentes: 2028: esperado 14,692.25, encontrado 13,691.86. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `Q10` | FCFE nao reconcilia com componentes: 2029: esperado 18,676.69, encontrado 15,987.09. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `R10` | FCFE nao reconcilia com componentes: 2030: esperado 22,464.45, encontrado 18,229.49. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `S10` | FCFE nao reconcilia com componentes: 2031: esperado 28,766.62, encontrado 20,518.09. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `T10` | FCFE nao reconcilia com componentes: 2032: esperado 31,212.63, encontrado 22,089.83. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `U10` | FCFE nao reconcilia com componentes: 2033: esperado 33,446.66, encontrado 23,595.76. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `V10` | FCFE nao reconcilia com componentes: 2034: esperado 35,835.61, encontrado 25,202.88. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Painel de Índices` | `9:9` | Linha critica sem valores: Capital de Giro Próprio (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções Trimestrais` | `28:28` | Linha critica sem valores: Receita de Serviços (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções Trimestrais` | `4:4` | Linha critica sem valores: Lucro Líquido (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `E5/E24` | Ativo total diferente de passivo total: 2019: ativo=166,344.09, passivo=0.00, diferenca=166,344.09. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `F5/F24` | Ativo total diferente de passivo total: 2020: ativo=244,229.72, passivo=0.00, diferenca=244,229.72. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `G5/G24` | Ativo total diferente de passivo total: 2021: ativo=352,924.04, passivo=0.00, diferenca=352,924.04. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `H5/H24` | Ativo total diferente de passivo total: 2022: ativo=454,096.45, passivo=0.00, diferenca=454,096.45. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `I5/I24` | Ativo total diferente de passivo total: 2023: ativo=495,115.81, passivo=0.00, diferenca=495,115.81. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `E10` | FCFE nao reconcilia com componentes: 2019: esperado 4,022.76, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `F10` | FCFE nao reconcilia com componentes: 2020: esperado 4,374.66, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `G10` | FCFE nao reconcilia com componentes: 2021: esperado 7,168.44, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `H10` | FCFE nao reconcilia com componentes: 2022: esperado 7,564.22, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `I10` | FCFE nao reconcilia com componentes: 2023: esperado 9,980.34, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `M10` | FCFE nao reconcilia com componentes: 2025: esperado 1,851.28, encontrado 1,449.15. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `N10` | FCFE nao reconcilia com componentes: 2026: esperado -497.15, encontrado 1,652.03. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `O10` | FCFE nao reconcilia com componentes: 2027: esperado 261.95, encontrado 1,850.27. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `P10` | FCFE nao reconcilia com componentes: 2028: esperado 761.09, encontrado 2,053.80. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `Q10` | FCFE nao reconcilia com componentes: 2029: esperado 1,359.06, encontrado 2,259.18. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `R10` | FCFE nao reconcilia com componentes: 2030: esperado 2,055.61, encontrado 2,462.51. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `S10` | FCFE nao reconcilia com componentes: 2031: esperado 2,846.46, encontrado 2,659.51. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `T10` | FCFE nao reconcilia com componentes: 2032: esperado 3,074.18, encontrado 2,872.27. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `U10` | FCFE nao reconcilia com componentes: 2033: esperado 4,020.76, encontrado 3,073.33. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `V10` | FCFE nao reconcilia com componentes: 2034: esperado 4,295.73, encontrado 3,288.46. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Painel de Índices` | `9:9` | Linha critica sem valores: Capital de Giro Próprio (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções Trimestrais` | `28:28` | Linha critica sem valores: Receita de Serviços (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções Trimestrais` | `4:4` | Linha critica sem valores: Lucro Líquido (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `E5/E24` | Ativo total diferente de passivo total: 2019: ativo=1,637,481.00, passivo=0.00, diferenca=1,637,481.00. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `F5/F24` | Ativo total diferente de passivo total: 2020: ativo=2,019,251.00, passivo=0.00, diferenca=2,019,251.00. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `G5/G24` | Ativo total diferente de passivo total: 2021: ativo=2,069,206.00, passivo=0.00, diferenca=2,069,206.00. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `H5/H24` | Ativo total diferente de passivo total: 2022: ativo=2,323,440.00, passivo=0.00, diferenca=2,323,440.00. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `I5/I24` | Ativo total diferente de passivo total: 2023: ativo=2,543,100.00, passivo=0.00, diferenca=2,543,100.00. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `E10` | FCFE nao reconcilia com componentes: 2019: esperado 27,113.00, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `F10` | FCFE nao reconcilia com componentes: 2020: esperado 18,896.00, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `G10` | FCFE nao reconcilia com componentes: 2021: esperado 26,760.00, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `H10` | FCFE nao reconcilia com componentes: 2022: esperado 29,702.00, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `I10` | FCFE nao reconcilia com componentes: 2023: esperado 33,105.00, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `M10` | FCFE nao reconcilia com componentes: 2025: esperado 28,206.86, encontrado 23,100.84. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `N10` | FCFE nao reconcilia com componentes: 2026: esperado 29,364.57, encontrado 26,832.25. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `O10` | FCFE nao reconcilia com componentes: 2027: esperado 36,812.40, encontrado 30,270.65. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `P10` | FCFE nao reconcilia com componentes: 2028: esperado 42,547.72, encontrado 34,087.47. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `Q10` | FCFE nao reconcilia com componentes: 2029: esperado 51,300.23, encontrado 37,890.04. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `R10` | FCFE nao reconcilia com componentes: 2030: esperado 57,916.34, encontrado 42,065.37. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `S10` | FCFE nao reconcilia com componentes: 2031: esperado 64,924.89, encontrado 44,668.05. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `T10` | FCFE nao reconcilia com componentes: 2032: esperado 68,871.63, encontrado 47,398.21. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `U10` | FCFE nao reconcilia com componentes: 2033: esperado 73,039.59, encontrado 50,286.35. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `V10` | FCFE nao reconcilia com componentes: 2034: esperado 77,364.90, encontrado 53,303.53. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Painel de Índices` | `9:9` | Linha critica sem valores: Capital de Giro Próprio (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções Trimestrais` | `28:28` | Linha critica sem valores: Receita de Serviços (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções Trimestrais` | `4:4` | Linha critica sem valores: Lucro Líquido (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `E5/E24` | Ativo total diferente de passivo total: 2019: ativo=762,237.45, passivo=0.00, diferenca=762,237.45. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `F5/F24` | Ativo total diferente de passivo total: 2020: ativo=936,201.48, passivo=0.00, diferenca=936,201.48. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `G5/G24` | Ativo total diferente de passivo total: 2021: ativo=931,208.40, passivo=0.00, diferenca=931,208.40. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `H5/H24` | Ativo total diferente de passivo total: 2022: ativo=985,450.83, passivo=0.00, diferenca=985,450.83. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `I5/I24` | Ativo total diferente de passivo total: 2023: ativo=1,115,652.78, passivo=0.00, diferenca=1,115,652.78. | Indica BP desequilibrado ou escrita em coluna/linha errada. | Reconciliar ativo, passivo e patrimonio liquido no normalizador e escritor do BP. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `E10` | FCFE nao reconcilia com componentes: 2019: esperado 16,406.93, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `F10` | FCFE nao reconcilia com componentes: 2020: esperado 26,837.06, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `G10` | FCFE nao reconcilia com componentes: 2021: esperado 15,528.05, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `H10` | FCFE nao reconcilia com componentes: 2022: esperado 14,287.09, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `I10` | FCFE nao reconcilia com componentes: 2023: esperado 9,449.31, encontrado 0.00. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `M10` | FCFE nao reconcilia com componentes: 2025: esperado 7,621.19, encontrado 14,126.29. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `N10` | FCFE nao reconcilia com componentes: 2026: esperado 10,876.93, encontrado 17,298.29. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `O10` | FCFE nao reconcilia com componentes: 2027: esperado 14,098.36, encontrado 19,257.26. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `P10` | FCFE nao reconcilia com componentes: 2028: esperado 16,149.08, encontrado 21,389.03. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `Q10` | FCFE nao reconcilia com componentes: 2029: esperado 18,132.40, encontrado 23,497.36. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `R10` | FCFE nao reconcilia com componentes: 2030: esperado 20,295.25, encontrado 25,781.68. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `S10` | FCFE nao reconcilia com componentes: 2031: esperado 23,397.41, encontrado 27,304.42. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `T10` | FCFE nao reconcilia com componentes: 2032: esperado 24,691.46, encontrado 28,794.46. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `U10` | FCFE nao reconcilia com componentes: 2033: esperado 26,049.81, encontrado 30,360.72. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `V10` | FCFE nao reconcilia com componentes: 2034: esperado 27,315.16, encontrado 31,878.76. | Afeta diretamente VP dos fluxos, valor terminal e preco-alvo. | Revisar sinal de CAPEX/capital regulatorio e formula do FCFE. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Painel de Índices` | `9:9` | Linha critica sem valores: Capital de Giro Próprio (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Projeções Trimestrais` | `28:28` | Linha critica sem valores: Receita de Serviços (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Projeções Trimestrais` | `4:4` | Linha critica sem valores: Lucro Líquido (R$ MM): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TAEE11\Valuation_TAEE11.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TASA4\Valuation_TASA4.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\TUPY3\Valuation_TUPY3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Balanço Patrimonial` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Balanço Patrimonial` | `19:19` | Linha critica sem valores: PASSIVO + PATRIMÔNIO LÍQUIDO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `DRE + DCF` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `DRE + DCF` | `29:29` | Linha critica sem valores: FLUXO DE CAIXA DESCONTADO (FCFF): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `DRE Contas Abertas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Painel de Índices` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Projeções Capex e CG` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Projeções Capex e CG` | `20:20` | Linha critica sem valores: FCFF — MONTAGEM: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Projeções Premissas` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `Projeções Premissas` | `5:5` | Linha critica sem valores: RECEITA E CRESCIMENTO: A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `TIR ON` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `TIR ON` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `TIR PN` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `TIR PN` | `8:8` | Linha critica sem valores: (+) Valor Terminal (Preço Justo): A linha foi identificada como item financeiro relevante, mas esta vazia nas colunas anuais. | Pode deixar DRE/BP/DCF incompleto e distorcer margens, fluxo de caixa ou valuation. | Conferir mapeamento da conta no escritor e garantir escrita nas colunas anuais corretas. |
| alta | `outputs\valuations\WEGE3\Valuation_WEGE3.xlsx` | `WACC` | `aba inteira` | Aba critica sem formulas: A aba contem dados de valuation, mas nenhuma formula Excel. Os calculos foram escritos como valores fixos. | Reduz auditabilidade, impede rastrear dependencias e torna a planilha vulneravel a atualizacoes parciais. | Manter os resultados do Python, mas escrever tambem formulas nos blocos de DCF, WACC, multiplos e checagens. |
| media | `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE + DCF` | `48:48` | Linha critica zerada: Preço Justo ON (R$): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | `14:14` | Linha critica zerada: Valor da Perpetuidade (Gordon): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE Recorrente` | `18:18` | Linha critica zerada: Cartão de Crédito/Débito: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Projeções - NIM` | `13:13` | Linha critica zerada: Margem Líquida (% Receita): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | `24:24` | Linha critica zerada: PASSIVO TOTAL: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `14:14` | Linha critica zerada: Valor da Perpetuidade (Gordon): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `G6` | Crescimento YoY divergente da linha base: 2021: esperado 46.32%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `H6` | Crescimento YoY divergente da linha base: 2022: esperado -9.45%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | `I6` | Crescimento YoY divergente da linha base: 2023: esperado -32.08%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE Recorrente` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE Recorrente` | `18:18` | Linha critica zerada: Cartão de Crédito/Débito: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções - NIM` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções - NIM` | `13:13` | Linha critica zerada: Margem Líquida (% Receita): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `24:24` | Linha critica zerada: PASSIVO TOTAL: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | `43:43` | Linha critica zerada: PATRIMÔNIO LÍQUIDO: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `14:14` | Linha critica zerada: Valor da Perpetuidade (Gordon): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `F6` | Crescimento YoY divergente da linha base: 2020: esperado 8.75%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `G6` | Crescimento YoY divergente da linha base: 2021: esperado 63.86%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `H6` | Crescimento YoY divergente da linha base: 2022: esperado 5.52%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | `I6` | Crescimento YoY divergente da linha base: 2023: esperado 31.94%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE Recorrente` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE Recorrente` | `18:18` | Linha critica zerada: Cartão de Crédito/Débito: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções - NIM` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções - NIM` | `13:13` | Linha critica zerada: Margem Líquida (% Receita): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE + DCF` | `48:48` | Linha critica zerada: Preço Justo ON (R$): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE + DCF` | `48:48` | Linha critica zerada: Preço Justo ON (R$): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `24:24` | Linha critica zerada: PASSIVO TOTAL: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | `43:43` | Linha critica zerada: PATRIMÔNIO LÍQUIDO: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `14:14` | Linha critica zerada: Valor da Perpetuidade (Gordon): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `F6` | Crescimento YoY divergente da linha base: 2020: esperado -30.31%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `G6` | Crescimento YoY divergente da linha base: 2021: esperado 41.62%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `H6` | Crescimento YoY divergente da linha base: 2022: esperado 10.99%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | `I6` | Crescimento YoY divergente da linha base: 2023: esperado 11.46%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE Recorrente` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE Recorrente` | `18:18` | Linha critica zerada: Cartão de Crédito/Débito: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções - NIM` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções - NIM` | `13:13` | Linha critica zerada: Margem Líquida (% Receita): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Balanço Patrimonial` | `24:24` | Linha critica zerada: PASSIVO TOTAL: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `14:14` | Linha critica zerada: Valor da Perpetuidade (Gordon): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `F6` | Crescimento YoY divergente da linha base: 2020: esperado 63.57%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `G6` | Crescimento YoY divergente da linha base: 2021: esperado -42.14%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `H6` | Crescimento YoY divergente da linha base: 2022: esperado -7.99%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE + DCF` | `I6` | Crescimento YoY divergente da linha base: 2023: esperado -33.86%, encontrado 0.00%. | Pode distorcer leitura de crescimento historico/projetado e narrativa da tese. | Escrever formula YoY vinculada a linha imediatamente superior ou corrigir valor calculado. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE Recorrente` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `DRE Recorrente` | `18:18` | Linha critica zerada: Cartão de Crédito/Débito: Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Projeções - NIM` | `cabecalho de anos` | Sequencia anual com lacunas ou colunas nao anuais: Cabecalho detectado: [2019, 2020, 2021, 2022, 2023, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]. | Pode indicar exclusao de ano historico, ponte trimestral residual ou desalinhamento entre historico e projecao. | Usar apenas anos anuais na linha-base ou separar claramente colunas trimestrais/YTD/YTG. |
| media | `outputs\valuations\SANB11\Valuation_SANB11.xlsx` | `Projeções - NIM` | `13:13` | Linha critica zerada: Margem Líquida (% Receita): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| media | `outputs\valuations\TRPL4\Valuation_TRPL4.xlsx` | `DRE + DCF` | `48:48` | Linha critica zerada: Preço Justo ON (R$): Todos os valores detectados na linha critica sao zero. | Pode ser dado real, mas frequentemente indica falha de mapeamento ou escala. | Validar contra o DataFrame normalizado e relatorio de completude CVM. |
| baixa | `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |
| baixa | `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `workbook` | `-` | Snapshot legado inventariado sem auditoria profunda: O arquivo esta fora de `outputs/valuations` e foi tratado como snapshot historico para evitar que workbooks antigos bloqueiem a revisao do motor atual. | O risco operacional principal esta nos arquivos canonicos atuais; snapshots antigos podem conter problemas ja superados. | Regenerar ou arquivar snapshots antigos apos validar os canonicos. |

## Arquivos e abas auditados

| Arquivo | Aba | Linhas | Colunas | Formulas | Anos detectados |
|---|---:|---:|---:|---:|---|
| `outputs\data_quality\audit_all_20260503.csv` | `-` | 3 | 19 | 0 |  |
| `outputs\data_quality\audit_all_20260504.csv` | `-` | 64 | 19 | 0 |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Preco-Teto` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Projeções Operacionais` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Projeções - CG e Capex` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `Projeções 2024` |  |  |  |  |
| `outputs\Valuation_AESB3_AES Brasil_20260427.xlsx` | `To-Do` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `TIR UNIT` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Projeções de Receita` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Projeções - Geração` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Projeções - Transmissão` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Projeções - CG e CAPEX` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ALUP11_Alupar_20260427.xlsx` | `Histórico por Trimestre` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_AMAR3_Marisa Lojas_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_ASAI3_Assaí Atacadista_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_AUAU3_Petiko (Petz + Cobasi)_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_AZZA3_Azzas 2154_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260415.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBAS3_Banco do Brasil_20260423.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260414.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260415.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260423.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260502.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_20260503.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BBDC4_Bradesco_test_summary2.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_BHIA3_Casas Bahia_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260415.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_BPAC11_BTG Pactual_20260423.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `DFC` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `Projeções - Receita Varejo` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `Projeções - Receita Financeira` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260427.xlsx` | `Lojas` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_CEAB3_C&A Brasil_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Preço Teto ON` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Preço Teto PN` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Projeções - Receita e Capex` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Histórico por Trimestre` |  |  |  |  |
| `outputs\Valuation_CLSC4_Celesc_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Projeções - Receitas` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Contas Abertas` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Capital de Giro e Capex` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Projeções 2023` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Dashboard - TAG` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `DRE + DCF - TAG` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Balanço Patrimonial - TAG ` |  |  |  |  |
| `outputs\Valuation_EGIE3_ENGIE Brasil_20260427.xlsx` | `Capital de Giro e Capex - TAG` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Preço-Teto ON` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Preço-Teto PN` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Preço-Teto ON (ANTIGO)` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Preço-Teto PN (ANTIGO)` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Projeções - Capex e CG` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Projeção Operacional` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Projeção de Receita` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Painel de índice` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Histórico por Trimestre` |  |  |  |  |
| `outputs\Valuation_ELET3_Eletrobras_20260427.xlsx` | `Energia Gerada` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Projeções - Receita e EBIT` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Projeções Operacionais` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Projeções - Capex e CG` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `Projeções 2023` |  |  |  |  |
| `outputs\Valuation_ENBR3_EDP Brasil_20260427.xlsx` | `To-Do` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ITUB4_Bradesco_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260415.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_ITUB4_Itaú Unibanco_20260423.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_LREN3_Lojas Renner_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_MGLU3_Magazine Luiza_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_NATU3_Natura Cosméticos_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_NTCO3_Natura &Co_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_PCAR3_GPA (Pão de Açúcar)_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_PETR4_Petrobras_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Projeções - Receita` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Lojas` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Projeções CAPEX + CG` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260427.xlsx` | `Provisões e Processos` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Projeções - Receita` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Lojas` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Projeções CAPEX + CG` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_PETZ3_Petz_20260428.xlsx` | `Provisões e Processos` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Provisões e Processos` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Projeções - Receita` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Projeções - Capex` |  |  |  |  |
| `outputs\Valuation_RADL3_Raia Drogasil_20260428.xlsx` | `Projeções 2023` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260415.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260416.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Ke` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `DRE Recorrente` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Projeções - NIM` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_SANB11_Santander_20260423.xlsx` | `Projeções Trimestrais` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_SBFG3_SBF Group (Centauro)_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Projeções - Capex e CG` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Projeção Operacional e Receita` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Histórico por Trimestre` |  |  |  |  |
| `outputs\Valuation_SBSP3_Sabesp_20260428.xlsx` | `Painel de índice` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `TIR UNIT` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Projeções Operacionais` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Projeções - Receita e Capex` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `Projeções 2024` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260427.xlsx` | `To-Do` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_TAEE11_Taesa_20260504.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Projeções RAPs` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Projeções - Capex e CG` |  |  |  |  |
| `outputs\Valuation_TRPL4_ISA CTEEP_20260427.xlsx` | `Projeções 2023` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260427.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_VIVA3_Vivara_20260428.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `TIR` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Preco-Teto` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `DRE - Contas Abertas` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Projeções` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Dados Complementares` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Projeções 2024` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Projeções (crescimento)` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Projeções (% total)` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Provisões e Processos` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260427.xlsx` | `Aquisições` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Dashboard` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `WACC` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `TIR ON` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `TIR PN` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Valor do Equity` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Preço Teto` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `DRE + DCF` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `DRE Contas Abertas` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Balanço Patrimonial` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Painel de Índices` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Projeções Premissas` |  |  |  |  |
| `outputs\Valuation_WEGE3_WEG_20260504.xlsx` | `Projeções Capex e CG` |  |  |  |  |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AERI3\Valuation_AERI3.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `WACC` | 23 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE + DCF` | 50 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `DRE Contas Abertas` | 23 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Balanço Patrimonial` | 33 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Painel de Índices` | 41 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\AESB3\Valuation_AESB3.xlsx` | `Projeções Capex e CG` | 25 | 16 | 0 | 2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ALUP11\Valuation_ALUP11.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Dashboard` | 20 | 28 | 85 |  |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Metodologia` | 31 | 6 | 0 |  |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Ke` | 22 | 23 | 39 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Balanço Patrimonial` | 46 | 29 | 240 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE Recorrente` | 32 | 29 | 164 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `DRE + DCF` | 26 | 29 | 124 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Projeções - NIM` | 41 | 28 | 189 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Painel de Índices` | 39 | 20 | 122 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\BBAS3\Valuation_BBAS3.xlsx` | `Projeções Trimestrais` | 44 | 20 | 28 | 2022,2023,2024,2025 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Dashboard` | 20 | 28 | 85 |  |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Metodologia` | 31 | 6 | 0 |  |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Ke` | 22 | 23 | 39 | 2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Balanço Patrimonial` | 46 | 29 | 352 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE Recorrente` | 32 | 29 | 166 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `DRE + DCF` | 26 | 29 | 167 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções - NIM` | 41 | 28 | 197 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Painel de Índices` | 39 | 20 | 142 | 2019,2020,2021,2022,2023 |
| `outputs\valuations\BBDC4\Valuation_BBDC4.xlsx` | `Projeções Trimestrais` | 44 | 20 | 28 | 2022,2023,2024,2025 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Dashboard` | 20 | 28 | 85 |  |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Ke` | 22 | 23 | 39 | 2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Balanço Patrimonial` | 46 | 29 | 366 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE Recorrente` | 32 | 29 | 168 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `DRE + DCF` | 26 | 29 | 163 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções - NIM` | 41 | 28 | 190 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Painel de Índices` | 39 | 20 | 132 | 2019,2020,2021,2022,2023 |
| `outputs\valuations\BPAC11\Valuation_BPAC11.xlsx` | `Projeções Trimestrais` | 44 | 20 | 28 | 2022,2023,2024,2025 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\CLSC4\Valuation_CLSC4.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\EGIE3\Valuation_EGIE3.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ELET3\Valuation_ELET3.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `WACC` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR ON` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `TIR PN` | 14 | 12 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Valor do Equity` | 21 | 4 | 0 |  |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Preço Teto` | 10 | 5 | 0 |  |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE + DCF` | 50 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `DRE Contas Abertas` | 23 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Balanço Patrimonial` | 33 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Painel de Índices` | 41 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Premissas` | 17 | 11 | 0 | 2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ENBR3\Valuation_ENBR3.xlsx` | `Projeções Capex e CG` | 25 | 17 | 0 | 2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Dashboard` | 20 | 28 | 85 |  |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Ke` | 22 | 23 | 39 | 2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Balanço Patrimonial` | 46 | 29 | 366 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE Recorrente` | 32 | 29 | 168 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `DRE + DCF` | 26 | 29 | 163 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções - NIM` | 41 | 28 | 190 | 2019,2020,2021,2022,2023,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Painel de Índices` | 39 | 20 | 132 | 2019,2020,2021,2022,2023 |
| `outputs\valuations\ITUB4\Valuation_ITUB4.xlsx` | `Projeções Trimestrais` | 44 | 20 | 28 | 2022,2023,2024,2025 |
| `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Dashboard` | 21 | 8 | 0 |  |
| `outputs\valuations\KEPL3\Valuation_KEPL3.xlsx` | `Metodologia` | 28 | 6 | 0 |  |

## Correcoes automaticas

Nenhuma planilha Excel foi alterada automaticamente nesta rodada. Os achados objetivos encontrados exigem mudanca no gerador das planilhas ou regeneracao dos arquivos; corrigir diretamente celulas isoladas quebraria o vinculo com o pipeline e poderia mascarar o erro de origem. Backups devem ser criados antes de qualquer regravacao em massa dos workbooks.

Correcoes objetivas ja aplicadas no codigo do projeto durante a revisao:
- `modules/valuation.py`: relacao PN/ON corrigida para `ON + PN * relacao`, TIR PN ajustada pela paridade e preco teto respeitando a relacao.
- `main.py`: cotacao, par ON/PN e market cap do WACC passaram a usar relacao especifica da empresa.
- `modules/05_valuation.py`: arquivo legado alinhado para nao manter a formula PN/ON invertida.

## Proximos ajustes recomendados

1. Transformar blocos criticos de DCF, WACC, multiplos e checagens em formulas Excel rastreaveis, mantendo os valores calculados pelo Python como controle.
2. Adicionar uma aba `Checks` em cada valuation com reconciliacoes: BP fecha, FCFF/FCFE fecha, EV-to-equity fecha, preco por acao fecha, g < WACC/Ke.
3. Separar claramente historico anual de colunas trimestrais/YTD/YTG, evitando misturar anos e pontes na mesma linha de cabecalho.
4. Regenerar os workbooks canonicos em `outputs/valuations` depois de corrigir o gerador.
5. Manter a auditoria de completude CVM/B3 como gate antes de gerar valuation final.
