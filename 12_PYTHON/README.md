---
title: Sistema Python — Documentação Técnica
tags:
  - python
  - arquitetura
  - código
aliases:
  - Python README
  - Documentação Técnica
---

# Sistema Python — Plataforma de Inteligência Financeira

---

## Estrutura do Projeto

```
12_PYTHON/
├── README.md              ← este arquivo
├── architecture.md        ← decisões de arquitetura
├── environments.md        ← setup de ambiente
├── dependencies.md        ← dependências e versões
├── src/
│   ├── ingestion/         ← coleta de dados brutos
│   ├── parsers/           ← extração de documentos
│   │   └── xbrl/          ← parsing XBRL (CVM)
│   ├── normalization/     ← padronização e mapeamento de contas
│   ├── models/            ← modelos financeiros
│   ├── valuation/         ← engines de valuation
│   ├── research/          ← geração de research
│   ├── reporting/         ← geração de relatórios
│   ├── validation/        ← testes de qualidade de dados
│   └── utils/             ← utilitários compartilhados
├── tests/                 ← testes automatizados
├── notebooks/             ← exploração e análise ad hoc
├── configs/               ← configurações e parâmetros
├── logs/                  ← logs de execução
└── examples/              ← exemplos de uso
```

---

## Princípios de Código

1. **Separação de responsabilidades:** cada módulo faz uma coisa
2. **Dado bruto nunca mistura com dado tratado:** camadas separadas
3. **Logs suficientes para rastrear:** toda etapa importante logada
4. **Validação nas bordas:** validar entrada e saída de cada pipeline
5. **Sem hardcode:** configs em arquivos, credenciais em variáveis de ambiente

---

## Camadas de Dados

```
raw/        → dados brutos como coletados (nunca modificar)
processed/  → dados limpos e normalizados
output/     → resultados finais prontos para uso
```

---

## Stack Principal

| Biblioteca | Função |
|---|---|
| `requests` / `aiohttp` | Coleta HTTP |
| `pandas` | Manipulação de dados |
| `numpy` | Cálculos numéricos |
| `lxml` / `bs4` | Parsing HTML/XML |
| `pdfplumber` / `pdfminer` | Extração de PDF |
| `openpyxl` | Leitura de Excel |
| `pydantic` | Validação de schema |
| `duckdb` / `sqlite3` | Banco local |
| `pyarrow` / `fastparquet` | Formato Parquet |
| `pytest` | Testes |
| `loguru` | Logging |
| `python-dotenv` | Variáveis de ambiente |
| `ruff` | Linting |
| `black` | Formatação |

---

## Módulos Principais

### `ingestion/`

Responsável por baixar dados brutos das fontes.

- `cvm_downloader.py` — DFP/ITR via API CVM
- `ri_scraper.py` — releases do RI das empresas
- `b3_fetcher.py` — dados de mercado B3

### `parsers/`

Responsável por extrair conteúdo estruturado de documentos.

- `dfp_parser.py` — parsing de DFP/ITR
- `xbrl_parser.py` — parsing XBRL (CVM padrão)
- `release_parser.py` — extração de releases
- `pdf_extractor.py` — extração de PDFs

### `normalization/`

Responsável por padronizar e mapear contas.

- `account_mapper.py` — mapeamento para schema padrão
- `normalizer.py` — limpeza e normalização
- `reconciler.py` — reconciliação entre demonstrações

### `valuation/`

Responsável pelos engines de valuation.

- `dcf_calculator.py` — DCF completo
- `wacc_builder.py` — cálculo de WACC
- `multiples_engine.py` — comparáveis e múltiplos
- `sensitivity_engine.py` — análise de sensibilidade

### `validation/`

Responsável por checar qualidade dos dados.

- `reconciliation.py` — checks contábeis automáticos
- `alerts.py` — regras de alerta (ver [[13_VALIDATION/REGRAS_DE_ALERTA]])
- `schema_validator.py` — validação Pydantic

---

## Como Adicionar um Novo Módulo

1. Criar arquivo em `src/[modulo]/`
2. Adicionar schema Pydantic para inputs/outputs
3. Adicionar logging em pontos críticos
4. Criar testes em `tests/`
5. Documentar no vault em `12_PYTHON/`

---

## Variáveis de Ambiente

Criar `.env` na raiz do projeto (nunca versionar):

```bash
CVM_API_URL=
ALPHA_VANTAGE_KEY=
FMP_API_KEY=
DB_PATH=
LOG_LEVEL=INFO
```

---

## Pipeline Semanal End-to-End (Fase 48)

> Uso interno — pesquisa e auditoria. Nenhuma ordem real. CVM IN 598.

### Comando principal

```bash
python -m src.scanners.run_weekly_pipeline \
    --start 2026-01-02 --end 2026-04-30 \
    --tickers PETR4 VALE3 ITUB4 BBAS3 \
    --execute --save-db --reports
```

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `src/pipeline/weekly_pipeline.py` | Orquestrador 14 etapas |
| `src/pipeline/weekly_pipeline_store.py` | Persistência SQLite |
| `src/scanners/run_weekly_pipeline.py` | CLI principal |
| `src/reports/weekly_pipeline_report.py` | Relatório do pipeline |

### Tabelas SQLite

| Tabela | Conteúdo |
|---|---|
| `weekly_pipeline_runs` | Execuções (status, counters, datas) |
| `weekly_pipeline_steps` | Etapas (stdout, stderr, output) |

### Documentação

- `docs/PIPELINE_SEMANAL_RADAR_MACRO.md` — referência completa
- `docs/ROTINA_END_TO_END_RADAR_MACRO.md` — runbook operacional

---

## Fluxo Editorial — Radar Macro Semanal (Fase 47)

> Uso interno — pesquisa e auditoria. Não constitui recomendação de investimento (CVM IN 598).

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `src/reports/editorial_workflow.py` | Estados, gates e transições editoriais |
| `src/reports/editorial_checklist.py` | Checklist humano de revisão (10 itens) |
| `src/reports/editorial_store.py` | Persistência SQLite (revisões + diffs) |
| `src/reports/weekly_report_diff.py` | Comparação semana contra semana |
| `src/reports/editorial_review_report.py` | Geração de relatório editorial Markdown |
| `src/reports/quant_dashboard_data.py` | Dados para Mesa Quant |
| `src/reports/quant_mesa_dashboard.py` | Aba Radar Macro na Mesa Quant |

### Tabelas SQLite

| Tabela | Conteúdo |
|---|---|
| `radar_macro_editorial_reviews` | Revisões editoriais com status e checklist |
| `radar_macro_weekly_diffs` | Diffs semana contra semana |

### Comandos

```bash
# Criar revisão editorial do relatório mais recente
python -m src.scanners.editorial_review --latest-report --create-review --save-db

# Aprovar para uso interno
python -m src.scanners.editorial_review --latest-report --approve-internal --reviewer NOME --save-db

# Comparar relatórios semanais e salvar diff
python -m src.scanners.compare_weekly_reports --save-db --csv

# Gerar relatório editorial Markdown
python -m src.scanners.generate_editorial_review_report
```

### Documentação

- `docs/FLUXO_EDITORIAL_RADAR_MACRO.md` — fluxo e estados editoriais
- `docs/CHECKLIST_RELATORIO_RADAR_MACRO.md` — checklist humano (10 itens)
- `docs/COMPARACAO_SEMANAL_RELATORIOS.md` — comparação semanal

---

## Dashboard Institucional — Mesa Quant (Fase 49)

> Uso interno — pesquisa e auditoria. Não constitui recomendação de investimento (CVM IN 598).

### Iniciar Dashboard

```bash
python -m streamlit run src/reports/quant_mesa_dashboard.py
```

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `src/reports/ui_components.py` | Componentes visuais padronizados (badges, cards, empty states) |
| `src/reports/quant_dashboard_data.py` | Camada de dados com cache, queries seguras e fallback |
| `src/reports/quant_mesa_dashboard.py` | App Streamlit institucional — 12 seções + Command Center |

### Seções do Dashboard

```
🏠  Home / Visão Executiva      📋  Paper Trading (12 subáreas)
📡  Radar de Ativos             🗄️  Dados & Auditoria
🧠  Inteligência Integrada      ⚙️  Pipeline Semanal
📈  Análise Técnica Quant       📰  Relatórios Radar Macro
📊  Opções Inteligentes         🏛️  Governança
⚖️  Risco & Volatilidade        ⌨️  Command Center
```

### Documentação

- `docs/DASHBOARD_INSTITUCIONAL.md` — arquitetura e componentes
- `docs/GUIA_USO_MESA_QUANT.md` — fluxo operacional semanal
- `docs/COMMAND_CENTER.md` — referência de todos os comandos

---
*Última atualização: 2026-05-19 — Fase 49: Dashboard Institucional Mesa Quant*
