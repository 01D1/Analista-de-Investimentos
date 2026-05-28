# M029 — Auditoria de Dados de Mercado

**Data:** 2026-05-28
**Escopo:** Fontes de dados de ações, opções, futuros, histórico disponíveis para o produto.

---

## 1. Banco SQLite: scanner_quant.db

| Tabela | Linhas | Status | Pronto p/ frontend |
|---|---|---|---|
| `cotahist_daily` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `realtime_signals` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `asset_intelligence_snapshots` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `technical_feature_snapshots` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `option_structure_candidates` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `market_regime_daily` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `macro_series` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `risk_snapshots` | **0** | Estrutura existe, sem dados | ❌ Sem dados |
| `valuation_results` | **não existe** | Tabela não existe | ❌ Não existe |

**Conclusão:** Todas as tabelas de dados de mercado estão vazias. O banco é operacional para runs/metrics mas não para dados de mercado brutos. Não criar dados mock — registrar lacuna.

**Próximo passo para dados reais:** Executar download COTAHIST (M015) para popular `cotahist_daily`, ou consumir RTD PROFIT.xlsx diretamente como fonte histórica.

---

## 2. Arquivos CSV em data/realtime

### 2.1 options_historical_opportunities.csv

| Campo | Descrição |
|---|---|
| `ativo_objeto` | Ticker do ativo objeto (ex: ENEV3, PETR4) |
| `ticker_opcao` | Código da opção (ex: ENEVR245) |
| `tipo` | CALL ou PUT |
| `strike` | Preço de exercício |
| `vencimento` | Data de vencimento (YYYY-MM-DD) |
| `dte` | Dias até o vencimento |
| `categoria_vencimento` | CURTO / MÉDIO / LONGO |
| `ultimo_preco` | Último preço da opção |
| `vol_media_5d/10d/21d` | Volume médio por período |
| `negocios_media_5d` | Média de negócios |
| `moneyness` | Moneyness (spot/strike - 1) |
| `moneyness_cat` | ITM / ATM / OTM |
| `liquidez_score` | Score 0-100 |
| `spot` | Preço do ativo objeto |
| `retorno_5d/21d/63d` | Retornos por período |
| `vol_hist_21d` | Volatilidade histórica 21 dias |
| `dist_max/dist_min` | Distância da máxima/mínima 52s |
| `cenario` | Cenário operacional |
| `estruturas_sugeridas` | Estratégias sugeridas |
| `score` | Score 0-100 |
| `status` | CANDIDATA_PROXIMO_PREGAO / MONITORAR_NO_RTD / AGUARDAR_LIQUIDEZ |
| `motivo` | Justificativa |
| `data_analise` | Data da análise |
| `ultima_data_cotahist` | Até qual data tem cotahist |

- **Linhas:** 13.938
- **Ativos:** 20 (ABEV3, B3SA3, BBAS3, BBDC4, BPAC11, CMIG4, CPLE6, EGIE3, ENEV3, GGBR4, HAPV3, ITUB4, PETR4, PRIO3, RADL3, RENT3, SUZB3, TAEE11, VALE3, WEGE3)
- **Período:** 2026-05-27 (snapshot único — não é série temporal)
- **Pronto para frontend:** ✅ Sim — via service dedicado
- **Needs service:** ✅ market_history_service + options_market_service

### 2.2 options_next_session_watchlist.csv

| Campo | Descrição |
|---|---|
| `ativo_objeto` | Ticker do ativo objeto |
| `ticker_opcao` | Código da opção |
| `tipo` | CALL / PUT |
| `strike` | Preço de exercício |
| `vencimento` | Data de vencimento |
| `dte` | Dias até o vencimento |
| `categoria_vencimento` | CURTO / MÉDIO / LONGO |
| `ultimo_preco` | Último preço |
| `liquidez_score` | Score 0-100 |
| `cenario` | Cenário operacional |
| `estruturas_sugeridas` | Estratégias |
| `score` | Score 0-100 |
| `status` | CANDIDATA_PROXIMO_PREGAO (1.320) / MONITORAR_NO_RTD (3.119) |
| `motivo` | Justificativa |

- **Linhas:** 4.439
- **Status:** CANDIDATA_PROXIMO_PREGAO (1.320) + MONITORAR_NO_RTD (3.119)
- **Tipos:** CALL (2.533) / PUT (1.906)
- **Pronto para frontend:** ✅ Sim
- **Needs service:** ✅ options_market_service

### 2.3 options_rtd_symbols.csv

| Campo | Descrição |
|---|---|
| `ticker` | Código da opção (ex: BBDCF17) |
| `ativo_objeto` | Ativo objeto (ex: BBDC) |
| `tipo` | CALL / PUT |
| `strike` | Preço de exercício |
| `vencimento` | Data de vencimento |
| `prioridade` | Prioridade de monitoramento |

- **Linhas:** 80
- **Ativos:** BBDC, ENEV, GGBR, ITUB, PETR, PRIO, VALE, ABEV, B3SA, BPAC
- **Vencimentos:** 2026-05-29, 2026-06-19, 2026-07-17, 2026-08-21, 2026-12-18, 2027-02-19
- **Pronto para frontend:** ✅ Sim
- **Needs service:** ✅ options_market_service

### 2.4 options_rtd_diagnostic.csv

| Campo | Descrição |
|---|---|
| `ativo` | Código do ativo |
| `spot` | Preço spot |
| `limite` | Limite de opções |
| `total_cand` | Total candidatos |
| `com_liquidez` | Com liquidez |
| `oportunidades` | Oportunidades |
| `na_shortlist` | Na watchlist |

- **Linhas:** 27 (27 ativos monitorados)
- **Pronto para frontend:** ⚠️ Parcial — diagnósticos agregados por ativo
- **Needs service:** ✅ options_market_service

### 2.5 options_rtd_watchlist.csv

- **Linhas:** 80
- **Status:** Corrompido — tickers com sufixo `;;`, colunas NaN
- **Pronto para frontend:** ❌ Não (precisa limpeza)
- **Action:** Ignorar este arquivo; usar `options_rtd_symbols.csv`

---

## 3. RTD PROFIT.xlsx

### Aba Ações

- **Linhas:** 152 tickers
- **Cols:** 99 colunas (OHLCV completo + indicadores técnicos)
- **Cols disponíveis:**

| Grupo | Colunas |
|---|---|
| Preço | Último, Abertura, Máximo, Mínimo, Fechamento Anterior, Ajuste |
| Volume | Volume, Quantidade, Negócio, QUL |
| Bid/Ask | Of. Compra, Of. Venda, VOC, VOV |
| Variação | Variação, Variação(pts) |
| VWAP | VWAP, VWAP Data, VWAP Mensal, VWAP Semanal |
| Técnico | IFR (RSI), MACD Histograma, ADX, Bollinger b%, HiLo Activator |
| Vol | Volatilidade Histórica, Volatilidade Implícita |
| Meta | Semana, Mês, 3 meses, 6 meses, 12 meses, Ano |
| Opções | Strike, Volt. Implícita, Delta, Gama, Theta, Vega, Rho |
| Nome | Nome do Ativo |
| Status | Estado Atual, Validade |
| Cont. Abertos |

- **Ações detectadas:** ~91 (terminam em 3/4/5/6/11)
- **Índices detectados:** IBOV e derivados
- **Futuros detectados:** Nenhum nesta aba
- **Pronto para frontend:** ✅ Sim — via rtd_live_reader existente + service dedicado

### Aba Opções

- **Linhas:** 53 tickers
- **Cols:** Mesma estrutura de 99 colunas
- **Opções detectadas:** ~35 (padrão sufixo F + dígitos)
- **Colunas extras de opções:** Strike, Volt. Implícita, Delta, Gama, Theta, Vega, Rho
- **Pronto para frontend:** ✅ Sim — via service dedicado

---

## 4. Módulos Existentes

| Módulo | Função | Status |
|---|---|---|
| `src/dashboard/rtd_live_reader.py` | Lê RTD PROFIT.xlsx | ✅ Funcionando — classificação ACAO/OPCAO/FUTURO/INDICE |
| `src/services/trading_desk_service.py` | Service principal | ✅ DB vazio, mas estrutura pronta |
| `src/services/options_strategy_service.py` | Estratégias de opções | ⚠️ Depende de DB vazio |
| `src/options/historical_opportunity_scanner.py` | Scanner histórico | ⚠️ Consome CSV, precisa verificação |
| `src/options/rtd_strategy_adapter.py` | Adapter RTD | ⚠️ Precisa verificação |
| `src/options/options_chain.py` | Cadeia de opções | ⚠️ Precisa verificação |
| `src/services/intelligence_unified_service.py` | Unificado | ⚠️ Depende de DB vazio |

---

## 5. Resumo: O que existe vs. o que falta

| Recurso | Fonte | Status | Service Needed |
|---|---|---|---|
| Histórico OHLCV ações | cotahist_daily | ❌ Vazio | ❌ — requer download B3 |
| Histórico OHLCV (snapshot RTD) | RTD PROFIT.xlsx | ✅ Disponível | ✅ market_history_service |
| Opções com strikes/Greeks | RTD PROFIT.xlsx | ✅ Disponível | ✅ options_market_service |
| Oportunidades históricas opts | CSV | ✅ 13.938 rows | ✅ options_market_service |
| Watchlist próxima sessão | CSV | ✅ 4.439 rows | ✅ options_market_service |
| Símbolos RTD | CSV | ✅ 80 rows | ✅ options_market_service |
| RTD Diagnósticos | CSV | ✅ 27 ativos | ✅ options_market_service |
| Futuros/Índices | RTD PROFIT.xlsx | ⚠️ Nenhum no RTD atual | ⚠️ Lacuna |
| Dados macro (Selic/IPCA/PTAX) | macro_series | ❌ Vazio | ⚠️ Lacuna — requer BCB download |
| Valuation | valuation_results | ❌ Tabela não existe | ❌ Lacuna |
| Sinais quant | technical_feature_snapshots | ❌ Vazio | ⚠️ Lacuna |

---

## 6. Plano de Ação

### Pronto para implementar agora
1. ✅ `market_history_service.py` — lê RTD PROFIT.xlsx como fonte histórica
2. ✅ `options_market_service.py` — lê CSVs + RTD
3. ✅ `futures_market_service.py` — lê RTD (nenhum futuro detectado ainda)
4. ✅ Endpoints FastAPI para os 3 services
5. ✅ Enriquecer `/api/trading/live` com RTD
6. ✅ `frontend/lib/api.ts` — adicionar interfaces
7. ✅ `AssetDetailDrawer.tsx` — abas Histórico e Opções
8. ✅ `OptionsRadar.tsx` — página de radar de opções
9. ✅ Testes backend
10. ✅ Documentação M029 final

### Lacunas a documentar para próximos milestones
- **cotahist_daily:** Requer execução de M015 (cvm_ri_ingestion) + B3 download
- **Selic/IPCA/PTAX:** Requer download BCB API
- **valuation_results:** Tabela não existe — requer M030 ou milestone específico
- **Futuros reais:** RTD atual não contém WDO/DOL/WIN —  adicionar ao Profit RTD
