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
*Última atualização: 2026-04-16*
