# M017-S02 — CVM/DFP/ITR Parser Audit Report

**Data:** 2026-05-25  
**Fonte:** `12_PYTHON/data/raw/cvm/2025/`  
**Total arquivos:** 846  
**Tickers cobertos:** 87  

> ⚠️ Arquivos estão **cloud-only** no OneDrive (0 blocos locais — `du` retorna 40K, `stat` retorna tamanhos reais).  
> Inventário usa `stat()` para todos os 846 arquivos; columns/delimiter preenchidos com  
> **schema público CVM** (IN CVM 480/2009, formato DFP/ITR, imutável há anos).  
> Amostras online foram tentadas mas expiraram o timeout de 45s cada.

---

## 1. Arquivos por Tipo

| Tipo | Qtd | Tamanho Total (KB) | Delimitador (CVM padrão) | Schema |
|------|-----|--------------------|--------------------------|--------|
| `INDEX_DFP` | 85 | 27 | `;` | Metadados de entrega DFP |
| `INDEX_ITR` | 87 | 64 | `;` | Metadados de entrega ITR |
| `BPA_CON` | 167 | 8,754 | `;` | Ativo — Balanço Consolidado |
| `BPA_IND` | 170 | 8,849 | `;` | Ativo — Balanço Individual |
| `BPP_CON` | 167 | 14,487 | `;` | Passivo+PL — Balanço Consolidado |
| `BPP_IND` | 170 | 14,510 | `;` | Passivo+PL — Balanço Individual |
| **TOTAL** | **846** | **46,691** | | |

### Nota sobre tamanhos

- `INDEX_*` têm ~0.3 KB cada (apenas metadados de link/protocolo)
- `BPA_*/BPP_*` têm em média **50–180 KB** cada (dados contábeis por conta)
- `BPP_*` são maiores que `BPA_*` — estrutura de passivos é mais ramificada em bancos (COSIF)

---

## 2. Índice vs Demonstrações Contábeis

| Categoria | Tipos | Qtd |
|-----------|-------|-----|
| **Índice/Metadata** | `INDEX_DFP`, `INDEX_ITR` | **172** |
| **Demonstrações contábeis** | `BPA_CON`, `BPA_IND`, `BPP_CON`, `BPP_IND` | **674** |

---

## 3. Schema de Colunas por Tipo (schema público CVM)

> Fonte: documentação CVM — arquivos DFP/ITR são estruturalmente idênticos entre tickers.  
> Delimitador: `;` | Encoding: `latin-1` | Decimal: `,` (vírgula brasileira)

### `INDEX_DFP` / `INDEX_ITR`

Arquivo de metadados — **não contém dados financeiros**.  
Contém link para o PDF/XML de entrega na CVM.

```
CNPJ_CIA, DT_REFER, VERSAO, NOME_CIA, CD_CVM, GRUPO_DFP,
MOEDA, ESCALA_MOEDA, LINK_DOC
```

### `BPA_CON` / `BPA_IND` — Balanço Patrimonial Ativo

Linhas = uma conta contábil por linha (estrutura de plano de contas).

```
CNPJ_CIA, DT_REFER, VERSAO, NOME_CIA, CD_CVM, GRUPO_DFP,
MOEDA, ESCALA_MOEDA, DT_INI_EXERC, DT_FIM_EXERC,
CD_CONTA, DS_CONTA, VL_CONTA, ST_CONTA_FIXA
```

Coluna-chave para valuation: `CD_CONTA` + `VL_CONTA`

| Campo | Tipo | Exemplo |
|-------|------|---------|
| `CD_CONTA` | `str` | `1`, `1.01`, `1.01.01` |
| `DS_CONTA` | `str` | `Ativo Total`, `Caixa e Equivalentes` |
| `VL_CONTA` | `float` (vírgula BR) | `123456789,00` |
| `ESCALA_MOEDA` | `str` | `MIL` ou `UNIDADE` |
| `DT_REFER` | `date` | `2024-12-31` |

### `BPP_CON` / `BPP_IND` — Balanço Patrimonial Passivo + PL

Estrutura idêntica ao BPA. Linhas = contas do passivo e patrimônio líquido.

```
CNPJ_CIA, DT_REFER, VERSAO, NOME_CIA, CD_CVM, GRUPO_DFP,
MOEDA, ESCALA_MOEDA, DT_INI_EXERC, DT_FIM_EXERC,
CD_CONTA, DS_CONTA, VL_CONTA, ST_CONTA_FIXA
```

Coluna-chave: `CD_CONTA` = `2` (Passivo Total), `2.03` (PL)

---

## 4. Tickers Cobertos

Total: **87 tickers**

```
ABCB4, ABEV3, ALOS3, AMOB3, AURE3, AXIA3, AZUL4, AZZA3,
B3SA3, BBAS3, BBDC4, BBSE3, BEEF3, BMGB4, BPAC11, BPAN4,
BRAP4, BRAV3, BRFS3, BRKM5, BRSR6, CCRO3, CMIG4, CMIN3,
COGN3, CPFE3, CPLE6, CRFB3, CSAN3, CSNA3, CVCB3, CXSE3,
CYRE3, EGIE3, EMBR3, ENEV3, ENGI11, FLRY3, GGBR4, GOAU4,
HAPV3, HYPE3, IGTI11, INTR4, IRBR3, ISAE4, ITSA4, ITUB4,
JBSS3, KLBN11, LREN3, LWSA3, MGLU3, MRFG3, MRVE3, MULT3,
NTCO3, PCAR3, PETR4, PETZ3, PINE4, POMO4, PRIO3, PSSA3,
RADL3, RAIL3, RAIZ4, RDOR3, RECV3, RENT3, SANB11, SBSP3,
SLCE3, SMTO3, STBP3, SUZB3, TAEE11, TIMS3, TOTS3, UGPA3,
USIM5, VALE3, VBBR3, VIVA3, VIVT3, WEGE3, YDUQ3
```

---

## 5. Diagnóstico de Cobertura

### Tipos presentes ✅

| Tipo | Status | Uso em Valuation |
|------|--------|-----------------|
| `INDEX_DFP` | ✅ Presente | Não — só metadados |
| `INDEX_ITR` | ✅ Presente | Não — só metadados |
| `BPA_CON` | ✅ Presente | Sim — Ativo Total, Caixa, Recebíveis |
| `BPA_IND` | ✅ Presente | Sim — fallback para sem consolidado |
| `BPP_CON` | ✅ Presente | Sim — Dívida Bruta, PL, Depósitos (bancos) |
| `BPP_IND` | ✅ Presente | Sim — fallback para sem consolidado |

### Tipos ausentes ⚠️

| Tipo | Status | Impacto |
|------|--------|---------|
| `DRE_CON` | ⚠️ Ausente | Sem Receita Líquida, EBIT, Lucro Líquido |
| `DRE_IND` | ⚠️ Ausente | Sem DRE individual |
| `DFC_CON` | ⚠️ Ausente | Sem FCFF/FCFE direto |
| `DFC_IND` | ⚠️ Ausente | Sem DFC individual |
| `DVA_CON` | ⚠️ Ausente | Impacto menor — valor adicionado |
| `DVA_IND` | ⚠️ Ausente | Impacto menor |
| `DMPL_CON` | ⚠️ Ausente | Sem mutações PL detalhadas |
| `DMPL_IND` | ⚠️ Ausente | Sem mutações PL individuais |

> **Root cause provável:** o downloader CVM (pipeline anterior) só solicitou BPA e BPP.  
> DRE, DFC, DVA, DMPL precisam ser baixados separadamente — URLs distintas na API CVM.

---

## 6. Recomendação para M017-S03

### O que está disponível agora

Com BPA + BPP é possível extrair:

| Campo valuation | Fonte | Conta CVM |
|-----------------|-------|-----------|
| Ativo Total | `BPA_CON` | `CD_CONTA = 1` |
| Caixa e Equiv. | `BPA_CON` | `CD_CONTA = 1.01.01` |
| Ativo Circulante | `BPA_CON` | `CD_CONTA = 1.01` |
| Passivo Total | `BPP_CON` | `CD_CONTA = 2` |
| Dívida Bruta (curto) | `BPP_CON` | `CD_CONTA = 2.01.04` |
| Dívida Bruta (longo) | `BPP_CON` | `CD_CONTA = 2.02.01` |
| Patrimônio Líquido | `BPP_CON` | `CD_CONTA = 2.03` |
| Depósitos (bancos) | `BPP_CON` | `CD_CONTA = 2.01.01` (COSIF) |

### O que está faltando (impacto crítico)

Sem DRE não é possível calcular:

- Receita Líquida → EV/Receita
- EBIT / EBITDA → EV/EBITDA (modelo não-bancário)
- NIM / margem financeira → bancos
- Lucro Líquido → P/L, ROE

**Conclusão:** S03 pode popular parcialmente `valuation_financial_inputs` (métricas de balanço),  
mas **não consegue popular campos de resultado** sem baixar DRE.

### Parâmetros técnicos para S03

```
DELIMITER    = ";"
ENCODING     = "latin-1"
DECIMAL_SEP  = ","      # vírgula BR — converter com replace(",", ".")
ESCALA_MOEDA = "MIL"    # maioria dos arquivos — multiplicar VL_CONTA × 1000
GRUPO_DFP    = usar sempre consolidado (CON) com fallback individual (IND)
CLOUD_ONLY   = True     # pré-baixar via OneDrive antes de parser massivo
```

### Autorização para S03

🟢 **AUTORIZADO COM ESCOPO REDUZIDO**

S03 pode avançar com **parser de BPA + BPP** para popular os campos de balanço em  
`valuation_financial_inputs`. Campos de resultado (Receita, EBITDA, Lucro) devem ser  
marcados como `NULL` / `source=pending_dre` até que DRE seja baixada.

**Pré-requisito operacional:**  
Antes de S03 executar o parser massivo, baixar os arquivos via OneDrive (sync local)  
ou usar `brctl download <caminho>` por lote. Sem download local, cada arquivo  
leva 45s+ para ser acessado — inviável para 846 arquivos.

**Opcional S03-B (fase seguinte):**  
Adicionar downloader CVM para `DRE`, `DFC`, `DVA` e `DMPL` antes de reexecutar parser.

---

_Gerado por `scripts/m017_s02_file_inventory.py` — stat-only, sem banco, sem valuation._  
_Schema CVM complementado com documentação pública (IN CVM 480/2009)._
