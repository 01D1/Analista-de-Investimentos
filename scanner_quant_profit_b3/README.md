# Scanner Quant Profit + B3

Scanner quantitativo para acompanhamento de ações e opções da B3, com integração a dados em tempo real via Profit/Excel RTD, histórico diário da B3 por meio dos arquivos COTAHIST, armazenamento em SQLite e geração de rankings operacionais para análise de mercado.

O objetivo do projeto é servir como uma base prática para identificar ativos com movimentação relevante, volume acima do normal, força intradiária, rompimentos, oportunidades em opções e possíveis distorções quantitativas que possam ser analisadas posteriormente em dashboards, relatórios e conteúdos de mercado.

---

## 1. O que o sistema faz

O projeto reúne módulos para:

- Ler cotações em tempo real a partir de uma planilha Excel conectada ao Profit via RTD;
- Normalizar os dados recebidos do Profit;
- Calcular métricas intradiárias de preço, volume, variação e posição no range do dia;
- Criar ranking quantitativo de ativos com base em critérios de força, liquidez e comportamento intradiário;
- Salvar snapshots e sinais em banco SQLite;
- Baixar e processar arquivos históricos da B3 no formato COTAHIST;
- Apoiar scanners de ações, opções e combinações entre ativo-objeto e derivativos;
- Exportar relatórios em CSV;
- Servir de base para dashboards em Streamlit.

---

## 2. Estrutura geral do projeto

Estrutura esperada da pasta principal:

```text
scanner_quant_profit_b3/
│
├── config.yaml
├── README.md
├── README_OBSIDIAN.md
├── requirements.txt
│
├── src/
│   ├── collectors/
│   ├── db/
│   ├── quant/
│   ├── reports/
│   ├── scanners/
│   └── utils/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── realtime/
│   ├── database/
│   └── reports/
│
└── tests/
```

Principais módulos:

| Módulo | Função |
|---|---|
| `src/collectors/profit_excel_collector.py` | Lê dados da planilha RTD do Profit |
| `src/collectors/b3_cotahist_collector.py` | Baixa e processa histórico da B3 |
| `src/collectors/b3_cotahist_downloader.py` | Faz download dos arquivos COTAHIST |
| `src/collectors/parse_cotahist.py` | Interpreta o layout dos arquivos da B3 |
| `src/scanners/realtime_profit_scanner.py` | Scanner intradiário com ranking dos ativos |
| `src/scanners/stock_scanner.py` | Scanner de ações |
| `src/scanners/option_scanner.py` | Scanner de opções |
| `src/scanners/combined_stock_options_scanner.py` | Cruza ações e opções correspondentes |
| `src/db/init_db.py` | Inicializa o banco SQLite |
| `src/reports/` | Dashboards e relatórios |

---

## 3. Requisitos

Antes de rodar o projeto, é recomendável ter:

- Python 3.10 ou superior;
- Profit instalado e funcionando;
- Microsoft Excel instalado;
- Planilha RTD configurada para receber dados do Profit;
- Git instalado, caso deseje clonar e versionar o projeto;
- Ambiente virtual Python, como `venv`.

Dependências comuns do projeto incluem:

- `pandas`
- `numpy`
- `openpyxl`
- `xlwings`
- `pyyaml`
- `streamlit`
- `plotly`
- `scipy`, quando necessário para modelos quantitativos

---

## 4. Instalação

Acesse a pasta do projeto:

```powershell
cd scanner_quant_profit_b3
```

Crie um ambiente virtual:

```powershell
python -m venv .venv
```

Ative o ambiente virtual no Windows:

```powershell
.venv\Scripts\activate
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

Inicialize o banco de dados:

```powershell
python -m src.db.init_db
```

---

## 5. Configuração do Profit RTD no Excel

O sistema lê os dados de mercado a partir de uma planilha Excel conectada ao Profit via RTD.

O arquivo esperado deve ficar preferencialmente em:

```text
data/realtime/RTD PROFIT.xlsx
```

No arquivo `config.yaml`, configure o caminho da planilha:

```yaml
profit_excel_path: "data/realtime/RTD PROFIT.xlsx"
profit_sheet_name: "Planilha1"
```

Também é possível usar um caminho absoluto, mas isso não é recomendado para versionamento no GitHub, pois o projeto pode quebrar ao mudar de computador ou diretório.

Exemplo não recomendado:

```yaml
profit_excel_path: "C:/Users/seu_usuario/Downloads/scanner_quant_profit_b3/data/realtime/RTD PROFIT.xlsx"
```

Durante o pregão, mantenha o Profit e o Excel abertos para que os dados RTD sejam atualizados corretamente.

---

## 6. Como rodar o scanner em tempo real

Para rodar uma única leitura e exibir os 10 principais ativos:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10
```

Para salvar também um relatório CSV:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --csv
```

Para rodar em modo contínuo:

```powershell
python -m src.scanners.realtime_profit_scanner --top 10
```

O intervalo entre as leituras pode ser definido no `config.yaml`:

```yaml
snapshot_interval_seconds: 5
```

Ou diretamente no comando:

```powershell
python -m src.scanners.realtime_profit_scanner --top 10 --interval 10
```

---

## 7. Modo demo

Fora do pregão ou sem a planilha RTD configurada, é possível testar o scanner com dados simulados:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo
```

Esse modo é útil para validar se o ambiente Python, os módulos e a lógica do ranking estão funcionando antes de conectar dados reais do Profit.

---

## 8. Como baixar dados históricos da B3

O projeto utiliza arquivos COTAHIST da B3 para processamento de dados históricos.

Para baixar e processar o histórico de um ano específico:

```powershell
python -m src.collectors.b3_cotahist_collector --year 2026
```

Os arquivos brutos devem ser armazenados em:

```text
data/raw/
```

Os arquivos processados devem ser armazenados em:

```text
data/processed/
```

Esses diretórios podem ser configurados no `config.yaml`:

```yaml
b3:
  raw_dir: "data/raw"
  processed_dir: "data/processed"
  years:
    - 2024
    - 2025
    - 2026
```

---

## 9. Como rodar o dashboard Streamlit

Caso o projeto esteja com dashboard Streamlit disponível em `src/reports/`, execute:

```powershell
python -m streamlit run src/reports/opportunity_dashboard.py --server.headless true
```

Após iniciar, o terminal deverá mostrar um endereço local semelhante a:

```text
Local URL: http://localhost:8501
```

Acesse esse endereço no navegador.

Se o Streamlit solicitar e-mail ou perguntar sobre estatísticas de uso, o modo `--server.headless true` ajuda a evitar interrupções no terminal.

---

## 10. Dados de entrada

O sistema pode utilizar as seguintes fontes de entrada:

| Entrada | Descrição |
|---|---|
| Planilha RTD do Profit | Dados em tempo real de ações e opções |
| COTAHIST B3 | Histórico diário oficial da B3 |
| `config.yaml` | Parâmetros de filtros, caminhos e ativos |
| Banco SQLite | Dados históricos processados, snapshots e sinais |

Exemplo de colunas esperadas da planilha RTD, a depender da configuração:

| Coluna | Descrição |
|---|---|
| `asset` | Código do ativo |
| `last` | Último preço |
| `open` | Preço de abertura |
| `high` | Máxima do dia |
| `low` | Mínima do dia |
| `prev_close` | Fechamento anterior |
| `variation_pct` | Variação percentual |
| `trades` | Número de negócios |
| `quantity` | Quantidade negociada |
| `volume` | Volume financeiro |

---

## 11. Dados de saída

O sistema pode gerar:

| Saída | Descrição |
|---|---|
| Ranking no terminal | Lista dos ativos com maior score quantitativo |
| CSV em `data/reports/` | Relatórios exportados do scanner |
| SQLite em `data/database/` | Banco local com snapshots e sinais |
| Dashboard Streamlit | Visualização operacional dos dados |

Exemplo de campos calculados pelo scanner:

| Campo | Descrição |
|---|---|
| `range_pct` | Amplitude percentual entre máxima e mínima |
| `position_range_pct` | Posição do preço atual dentro do range do dia |
| `gap_pct` | Diferença entre abertura e fechamento anterior |
| `last_vs_open_pct` | Diferença entre último preço e abertura |
| `score` | Pontuação quantitativa do ativo |
| `signal` | Classificação operacional do sinal |
| `motivos` | Explicação textual dos critérios atendidos |

---

## 12. Configuração dos filtros

Os principais filtros ficam no `config.yaml`:

```yaml
filtros:
  variacao_minima_pct: 0.3
  negocios_minimos: 1000
  volume_minimo: 50000000
  rompimento_tolerancia: 0.995
```

Descrição dos parâmetros:

| Parâmetro | Função |
|---|---|
| `variacao_minima_pct` | Variação mínima considerada relevante |
| `negocios_minimos` | Número mínimo de negócios para validar liquidez |
| `volume_minimo` | Volume financeiro mínimo |
| `rompimento_tolerancia` | Tolerância para considerar preço próximo da máxima |

---

## 13. Limitações atuais

Este projeto ainda deve ser tratado como uma base em desenvolvimento.

Principais limitações:

- A qualidade dos sinais depende da qualidade e atualização da planilha RTD;
- O Profit e o Excel precisam estar abertos durante o uso em tempo real;
- Caminhos absolutos no `config.yaml` podem quebrar o funcionamento ao mudar de máquina;
- O score atual é uma heurística inicial e deve ser validado com histórico e backtests;
- Dados de opções podem exigir tratamento adicional para vencimento, strike, liquidez, spread, volatilidade e Greeks;
- O sistema ainda não deve ser usado isoladamente para tomada de decisão financeira;
- Não há garantia de execução, liquidez ou acerto operacional;
- É recomendável revisar os cálculos antes de utilizar o projeto em ambiente profissional.

---

## 14. Próximas melhorias recomendadas

Melhorias prioritárias:

- Criar `config.example.yaml` e manter `config.local.yaml` fora do Git;
- Remover duplicidades de código e arquivos antigos;
- Criar testes unitários para os cálculos quantitativos;
- Validar parser COTAHIST com amostras reais;
- Criar score relativo ao histórico do próprio ativo;
- Incluir volume relativo, volatilidade relativa e força contra o Ibovespa;
- Melhorar scanner de opções com moneyness, spread, vencimento, valor extrínseco e liquidez;
- Criar camada de backtest para medir taxa de acerto dos sinais;
- Integrar notícias, fatos relevantes, releases e dados fundamentalistas;
- Evoluir dashboard Streamlit para formato de plataforma operacional.

---

## 15. Aviso importante

Este projeto tem finalidade educacional, analítica e experimental. As informações geradas pelo sistema não constituem recomendação de investimento, oferta de compra ou venda de ativos, consultoria financeira, análise de valores mobiliários ou promessa de rentabilidade.

Qualquer decisão de investimento deve considerar perfil de risco, liquidez, custos, tributação, estratégia própria e validação independente dos dados.
