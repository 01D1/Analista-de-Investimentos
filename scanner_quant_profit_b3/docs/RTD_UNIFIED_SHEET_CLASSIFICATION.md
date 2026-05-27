# RTD Unified Sheet Classification

**Data:** 2026-05-27
**Status:** ✅ Implementado

---

## Problema

O RTD PROFIT.xlsx concentra ações, opções e futuros na aba **"Ações"**, não em abas separadas. O antigo código exigia que opções estivessem em uma aba dedicada "Opções" que estava vazia.

## Solução

Classificação automática por ticker — sem dependência de aba, sem separação manual.

---

## Regras de Classificação

Prioridade: **OPCAO > FUTURO > INDICE > ACAO > OUTRO**

| Regra | Condição | Classe |
|---|---|---|
| Shortlist | Ticker em `options_rtd_watchlist.csv` ou `options_rtd_symbols.csv` | OPCAO |
| Sufixo opção | Padrão regex: `PETRF469`, `ITUBF404`, `VALEF856`, `BBDCF17`, `ENEVRF250` | OPCAO |
| Futuro prefixo | `WIN`, `WDO`, `DOL`, `IND`, `DI1` + sufixo (ex: `WDOJ26`) | FUTURO |
| Futuro completo | `WINFUT`, `DOLFUT`, `WDOFUT`, `DI1FUT` | FUTURO |
| Índice | `IBOV`, `IBOVX100`, `IBRA`, `SMLL`, `IFIX` etc. | INDICE |
| Ação B3 | Ticker termina em 3, 4, 5, 6 ou 11 (ex: `PETR4`, `BBDC4`) | ACAO |
| Ação prefixo | Prefixo conhecido (`PETR`, `VALE`, `ITUB`, etc.) | ACAO |
| Padrão desconhecido | Nenhum dos acima | OUTRO |

### Padrões regex de opção reconhecidos

```
^[A-Z]{2,5}F\d{3}$     →  PETRF469, ITUBF404, VALEF856, BBDCF17  (2-5 letras + F + 3 dígitos)
^[A-Z]{2,5}W\d{3}$     →  Warrant patterns (2-5 letras + W + 3 dígitos)
^[A-Z]{2,5}D\d{3}$     →  Days patterns (2-5 letras + D + 3 dígitos)
^[A-Z]{4,6}F\d{2,4}$    →  PETRF23, ENEVRF250, BBASF123           (4-6 letras + F + 2-4 dígitos)
^[A-Z]{1,4}F\d{2,4}$   →  Ações americanas com F + strike
```

---

## Mudanças Implementadas

### `src/dashboard/rtd_live_reader.py`
- Nova classe `TickerClassifier` com regras de classificação por ticker
- Prioridade OPCAO sobre ACAO (PETRF469 ≠ PETR4)
- Campo `aba_origem` em `InstrumentPayload` para rastrear origem dos dados
- Leitura de TODAS as abas do Excel (não só a primeira)
- Carregamento de `options_rtd_symbols.csv` em paralelo com watchlist
- Método `summary()` agora inclui `class_origins` (de qual aba cada classe veio)

### `pages/trading_desk.py`
- Aba "Opções ao Vivo" agora mostra opções detectadas na aba Ações (classificação automática)
- Nova seção "Opções RTD (fora da shortlist)" — opções no RTD classificadas por ticker mas ausentes da watchlist
- "Opções ao Vivo" NÃO DEPENDE mais da aba "Opções"
- Diagnostic tab mostra origem por classe (aba=quantidade)
- Aba "Estratégias" removida (era duplicada)
- Cache atualizado para incluir `symbols_path`

### `pages/rtd_raw_live_test.py`
- Classificação automática de todos os tickers lidos
- Contadores: ações, opções, futuros, índices, outros
- Coluna `classe_detectada` adicionada à tabela bruta
- Código de cores: ACAO=azul, OPCAO=amarelo, FUTURO=verde, INDICE=cinza

---

## Validação

### Testes de classificação
```
Ticker          Expected   Got        OK?
---------------------------------------------
PETRF469        OPCAO      OPCAO      ✅
PETR4           ACAO      ACAO       ✅  ← PETRF469 não vira ACAO
ITUBF404        OPCAO      OPCAO      ✅
VALEF856        OPCAO      OPCAO      ✅
WINFUT          FUTURO     FUTURO     ✅
DOLFUT          FUTURO     FUTURO     ✅
WDOJ26          FUTURO     FUTURO     ✅
IBOV            INDICE     INDICE     ✅
BBDC4           ACAO      ACAO       ✅
BBASF123        OPCAO      OPCAO      ✅
BBDCF17         OPCAO      OPCAO      ✅
ENEVR250        OUTRO      OUTRO      ✅  ← Sem F, não é opção
```

### Compilação
```
python -m py_compile pages/trading_desk.py pages/rtd_raw_live_test.py src/dashboard/rtd_live_reader.py
# ALL OK ✅
```

---

## Fluxo de Dados

```
RTD PROFIT.xlsx
    ├── Aba "Ações" → Ações + Opções + Futuros → classificados por ticker
    ├── Aba "Opções" → (lida se existir, mas não exige)
    └── Aba "Índices" → (lida se existir)

RTDLiveReader.read_all()
    ├── Lê todas as abas
    ├── Para cada ticker: TickerClassifier.classify(ticker)
    ├── Prioridade OPCAO sobre ACAO (evita PETRF469 → PETR)
    └── Retorna dict {ticker: InstrumentPayload}

Trading Desk
    ├── Ações ao Vivo → filtra ACAO
    ├── Opções ao Vivo → filtra OPCAO + shortlist cruzada
    ├── Futuros ao Vivo → filtra FUTURO
    └── Diagnóstico RTD → mostra tudo + origem por aba
```

---

## Limitações

1. **ENEVR250** (sem 'F') não é reconhecido por regex — adicione à watchlist se for opção.
2. A classificação é inferida por padrão de ticker — confiável para os formatos brasileiros padrão.
3. Se o usuário renomear tickers de opção para nomes não-padrão, adicione manualmente à shortlist.

---

## Exemplo de Opção Detectada Corretamente

- **PETRF469** classificado como `OPCAO` ✅ (não como `ACAO`)
- Aparece em "Opções ao Vivo" ✅
- Não aparece em "Ações ao Vivo" ✅
- No RTD Raw Test, coluna `classe_detectada` mostra `OPCAO` ✅

---

## Como Usar

1. O Profit RTD grava todos os instrumentos na aba "Ações" do RTD PROFIT.xlsx
2. O scanner lê todas as abas automaticamente
3. Cada ticker é classificado por padrão de nome
4. Abas dedicadas de opções/futuros são lidas se existirem, mas nunca exigidas

Nenhuma configuração manual de aba é necessária.