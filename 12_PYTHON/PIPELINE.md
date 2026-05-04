# Data Pipeline

Fluxo padrao de processamento de dados no sistema.

## Etapas

### 1. Coleta
Ingestao de dados brutos de fontes externas (CVM, RI, B3, APIs).
Dados salvos em formato raw, sem transformacao.

### 2. Parsing
Extracao de informacoes estruturadas a partir de documentos (PDF, XBRL, HTML).
Cada parser e especializado por tipo de fonte.

### 3. Normalizacao
Padronizacao de contas, periodos e unidades.
Mapeamento para o plano de contas interno do sistema.

### 4. Validacao
Checagem de consistencia: BP fecha, DFC reconcilia, sem duplicatas.
Dados que nao passam na validacao sao sinalizados, nunca descartados silenciosamente.

### 5. Modelagem
Calculo de metricas, projecoes e cenarios.
Inputs documentados, premissas explicitas.

### 6. Output
Geracao de resultados finais: valuations, relatorios, dashboards.
Todo output deve ter rastreabilidade ate os dados brutos.

## Principio

Cada etapa e independente. Um erro no parsing nao deve contaminar a normalizacao.
Logs devem ser suficientes para reproduzir qualquer resultado.

> Referencia: [[12_PYTHON/README]]
