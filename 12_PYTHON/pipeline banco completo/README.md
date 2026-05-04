# Pipeline de Valuation Bancário 🏦

Pipeline Python completo para automatizar análise fundamentalista e valuation de bancos brasileiros, integrado ao template Excel profissional.

## Estrutura do Projeto

```
pipeline_banco/
├── main.py                      ← Ponto de entrada — roda o pipeline completo
├── requirements.txt             ← Dependências Python
├── .env.example                 ← Variáveis de ambiente (copiar para .env)
├── config/
│   ├── settings.py              ← Premissas globais (Ke, crescimento, beta)
│   └── mapeamento_contas.py     ← Mapa de contas CVM → template Excel
├── modules/
│   ├── coletor_cvm.py           ← Baixa DFPs/ITRs da API pública CVM
│   ├── coletor_mercado.py       ← Preços, beta, market cap (yfinance)
│   ├── coletor_macro.py         ← Selic, IPCA, DI, TJLP (BCB API)
│   ├── normalizador.py          ← Padroniza contas e calcula indicadores
│   ├── valuation.py             ← DCF, perpetuidade, TIR, preço justo
│   ├── projecoes.py             ← Projeta NIM, carteira, provisão, FCFE
│   ├── escritor_excel.py        ← Popula o template .xlsx
│   └── _helpers.py              ← Utilitários compartilhados
├── outputs/                     ← Arquivos Excel gerados
├── cache/                       ← JSONs/Parquet locais (evita re-download)
└── logs/                        ← Logs de execução
```

## Instalação

```bash
# 1. Clonar / descompactar o projeto
cd pipeline_banco

# 2. Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar (opcional)
cp .env.example .env
# Editar .env com suas premissas
```

## Uso Rápido

```bash
# Análise completa do Bradesco com download da CVM
python main.py --ticker BBDC4 --nome Bradesco

# Banco do Brasil com cotações manuais
python main.py --ticker BBAS3 --nome "Banco do Brasil" \
    --cotacao-on 27.79 --acoes-on 5707910

# Itaú — modo rápido sem CVM (só macro + mercado + projeções)
python main.py --ticker ITUB4 --nome Itaú --sem-cvm

# BTG Pactual com premissas customizadas
python main.py --ticker BPAC11 --nome BTG \
    --beta 0.90 --g 0.075 \
    --cotacao-on 35.50 --acoes-on 3835370

# Santander com debug ativado
python main.py --ticker SANB11 --nome Santander --debug

# Especificar template e saída
python main.py --ticker BBDC4 \
    --template /caminho/Template_Valuation_Banco.xlsx \
    --output /caminho/saida/BBDC4_2025.xlsx
```

## O que o pipeline faz

### 1. Coleta de Dados de Mercado (yfinance)
- Cotação atual da ação na B3
- Número de ações emitidas
- Beta estatístico vs. Ibovespa (janela de 252 dias úteis)
- Série de preços históricos para análise

### 2. Coleta Macroeconômica (API BCB/SGS)
- **Histórico:** Selic, DI, IPCA, TJLP (2010–hoje)
- **Projetado:** Combina Relatório Focus + premissas do settings.py
- **CDS Brasil:** Usado no cálculo do custo de capital (Rf = DI − CDS − Inflação Implícita)

### 3. Demonstrações Financeiras (API CVM)
- Download automático de DFPs anuais (2019–2024)
- Mapeamento de contas pelo código CVM → linhas do template
- Cache local para evitar re-downloads

### 4. Normalização
- Padronização das contas em R$ MM
- Cálculo de contas derivadas (MFB, MFL, capital regulatório)
- Indicadores: ROE, ROA, NIM, Basileia, spread, inadimplência

### 5. Projeções (10 anos)
| Linha             | Metodologia                                          |
|-------------------|------------------------------------------------------|
| Carteira crédito  | Crescimento premissado por ano (settings.py)         |
| NIM               | Regressão NIM~Selic + convergência à mediana setorial|
| Provisão          | % da carteira convergindo para média histórica       |
| Serviços          | Crescimento pelo PIB nominal projetado               |
| Despesas pessoal  | IPCA + 1,5% de reajuste real                         |
| Capital regulatório | ΔRWA × Basileia alvo                               |

### 6. Valuation DCF/FCFE
```
FCFE = Lucro Líquido + D&A − CAPEX − ΔCapital Regulatório
Ke   = (DI − CDS − Inflação Implícita) + β × ERP
VP   = Σ FCFE_t / Π(1 + Ke_t)  +  FCFE_n×(1+g)/(Ke−g) / Π(1+Ke_t)
```
Saídas: Valor do Equity, Preço Justo ON/PN, Upside, TIR, Preço Teto

### 7. Escrita no Template Excel
- Popula automaticamente todas as 8 abas do template
- Preserva formatação original (cores, bordas, fórmulas)
- Histórico em azul (dados reais), projeções em verde

## Personalizando Premissas

Edite `config/settings.py`:

```python
# Crescimento da carteira por ano
CRESCIMENTO_CARTEIRA_CREDITO = {
    2025: 0.10,   # 10% em 2025
    2026: 0.08,   # 8% em 2026
    ...
}

# Beta arbitrado (default: 0.85)
BETA_UTILIZADO = 0.85

# Taxa de crescimento na perpetuidade (default: 7%)
G_PERPETUIDADE = 0.070

# NIM alvo de longo prazo (convergência)
NIM_ALVO = 0.076
```

## Adicionando um Novo Banco

1. Descobrir o código CVM em https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/
2. Adicionar aliases em `config/mapeamento_contas.py` se o banco usar terminologia diferente
3. Executar: `python main.py --ticker XXXX --codigo-cvm YYYY`

## Bancos Testados
| Banco       | Ticker  | Código CVM |
|-------------|---------|------------|
| Bradesco    | BBDC4   | 906        |
| Banco do Brasil | BBAS3 | 1023     |
| Itaú Unibanco | ITUB4 | 19348     |
| BTG Pactual | BPAC11  | 21610      |
| Santander   | SANB11  | 20532      |

## Limitações e Próximos Passos
- CVM pode ter latência alta — usar `--sem-cvm` para análises rápidas
- Dados trimestrais (ITR) ainda não preenchem as projeções trimestrais do template
- Notas explicativas (NPL, Basileia real) requerem parsing manual das DFPs em PDF
- Próximo: módulo de comparação entre pares (peer analysis)

## Licença
Uso educacional e pessoal. Não constitui recomendação de investimento.

---

## Projetos Relacionados

- [[12_PYTHON/Projetos Implementados|Hub — Projetos Python Implementados]]
- [[scanner_quant_profit_b3/README_OBSIDIAN|Scanner Quant Profit + B3]] — fornece preços e dados de mercado em tempo real que complementam as coletas do yfinance
- [[12_PYTHON/news_hunter/README|News Hunter]] — contexto macro e de notícias que explica premissas do valuation (Selic, FOMC, resultados)

---

*Última atualização: 2026-05-03*
