# Radar Histórico de Opções — Integração no Trading Desk

## Visão Geral

A aba **📡 Radar Histórico** integra os dados gerados pelo `historical_opportunity_scanner.py`
diretamente no Trading Desk. Ela exibe oportunidades descobertas via COTAHIST B3 para
planejamento do próximo pregão e horizontes futuros, **sem confundir com recomendações
operacionais intraday**.

> **Regra central:** COTAHIST descobre oportunidade. RTD confirma execução.

---

## Fluxo de Dados

```
COTAHIST B3 (SQLite)
        │
        ▼
historical_opportunity_scanner.py
        │
        ├── data/realtime/options_historical_opportunities.csv  (todas oportunidades)
        └── data/realtime/options_next_session_watchlist.csv   (candidatas/monitorar)
                │
                ▼
        Trading Desk — Aba "📡 Radar Histórico"
                │
                ├── Cruzamento com RTD ao vivo (all_inst)
                ├── Exibição de KPIs, filtros, tabela principal
                ├── Top 10 ideias para próximo pregão
                ├── Bloco longo prazo / recuperação
                └── Ponte → Aba "🧠 Estratégias" (se RTD confirmado)
```

---

## Como Usar

### 1. Gerar os dados históricos

```bash
# Todos os 20 ativos monitorados
python -m src.options.historical_opportunity_scanner

# Ativos específicos
python -m src.options.historical_opportunity_scanner --ativos PETR4 VALE3 ITUB4

# Com log detalhado
python -m src.options.historical_opportunity_scanner --verbose
```

### 2. Abrir o Trading Desk

```bash
streamlit run app.py
```

Navegar para: **Trade Desk → 📡 Radar Histórico**

---

## Seções da Aba

### KPIs (10 métricas)

| KPI | Descrição |
|---|---|
| Total Oportunidades | Todas as oportunidades encontradas no COTAHIST |
| Candidatas Pregão | Status = CANDIDATA_PROXIMO_PREGAO |
| Monitorar RTD | Status = MONITORAR_NO_RTD |
| Ativos Únicos | Número de ativos com pelo menos 1 opção |
| No RTD | Opções históricas detectadas no arquivo RTD PROFIT.xlsx |
| Aguardando Liq. | Status = AGUARDAR_LIQUIDEZ |
| Descard. Ilíquida | Status = DESCARTAR_ILIQUIDA |
| Descard. Sem Edge | Status = DESCARTAR_SEM_ASSIMETRIA |
| Curto/Médio | DTE 0–30 / 31–90 dias |
| Longo/Extra | DTE 91–180 / 180+ dias |

### Filtros

- **Ativo Objeto**: PETR4, VALE3, etc.
- **Cenário**: RECUPERACAO_APOS_QUEDA, CONTINUACAO_ALTA, etc.
- **Status**: CANDIDATA, MONITORAR, AGUARDAR, ESTUDAR, DESCARTAR_*
- **Tipo**: CALL / PUT
- **Horizonte**: CURTO / MEDIO / LONGO / EXTRA_LONGO
- **Vencimento**: data específica (YYYY-MM-DD)
- **Estrutura**: Call Longa, Trava de Alta, Protective Put, etc.
- **Score mínimo**: slider 0–100

### Tabela Principal

Colunas exibidas (até 200 linhas, refinar via filtros):

| Coluna | Fonte |
|---|---|
| Ativo | ativo_objeto (CSV) |
| Opção | ticker_opcao (CSV) |
| Tipo | CALL / PUT (badge) |
| Strike | strike (CSV) |
| Venc. | vencimento (CSV) |
| DTE | dias para vencimento |
| Moneyness | % e categoria ATM/OTM/ITM |
| Cenário | badge colorido por tipo |
| Horizonte | CURTO/MEDIO/LONGO/EXTRA_LONGO |
| Estrutura | estruturas_sugeridas (CSV) |
| Score | badge 0–100 por faixa |
| Liq. | liquidez_score (0–100) |
| Vol.21d | vol_media_21d |
| Neg.5d | negocios_media_5d |
| Status | badge por status |
| Motivo | explicação resumida |
| Risco | risco_principal (truncado) |
| RTD | ✓ RTD confirmado / No RTD / Histórico |
| Próxima Ação | ação recomendada (ver abaixo) |

### Coluna "Próxima Ação"

| Status + RTD | Próxima Ação |
|---|---|
| CANDIDATA + RTD confirmado (bid/ask) | Enviar para motor de estratégias ao vivo |
| CANDIDATA + No RTD (sem bid/ask) | RTD detectado — confirmar bid/ask |
| CANDIDATA + Sem RTD | Adicionar ao RTD no próximo pregão |
| MONITORAR + No RTD | Monitorar liquidez no RTD |
| MONITORAR + Sem RTD | Adicionar ao RTD — monitorar liquidez |
| AGUARDAR_LIQUIDEZ | Aguardar confirmação técnica |
| ESTUDAR | Aguardar confirmação técnica |
| DESCARTAR_ILIQUIDA | Descartar por iliquidez |
| DESCARTAR_SEM_ASSIMETRIA | Descartar por falta de assimetria |

### Bloco "Top Ideias para Próximo Pregão"

- Top 10 por score entre CANDIDATA_PROXIMO_PREGAO e MONITORAR_NO_RTD
- Ranking com cor: verde (top 3), amarelo (4–7), cinza (8–10)
- Inclui: ativo, ticker, tipo, strike, venc/DTE, cenário, horizonte, estrutura, score, motivo, risco, próxima ação

### Bloco "Longo Prazo & Recuperação"

- Filtra: categoria_vencimento ∈ {LONGO, EXTRA_LONGO}
- Cenários incluídos: RECUPERACAO_APOS_QUEDA, CONTINUACAO_ALTA, PROTECAO_CARTEIRA
- Exclui descartadas
- Claramente marcado como "estudo de planejamento — não entrada imediata"

### Bloco "Resumo por Cenário"

Tabela com 8 cenários:
- Total de oportunidades
- Candidatas para próximo pregão
- Monitorar no RTD
- Descartadas
- Score médio
- Ativos afetados

### Ponte RTD → Motor de Estratégias

Se alguma opção histórica tiver bid/ask confirmado no RTD, a aba exibe um banner verde
indicando quantas opções estão prontas para análise de estruturas. O usuário é direcionado
para a aba **🧠 Estratégias** onde o motor ao vivo consome os preços.

---

## Cruzamento com RTD

O cruzamento é feito em tempo real a partir de `all_inst` (lido pelo `RTDLiveReader`):

| Condição | Badge exibido |
|---|---|
| ticker_opcao in RTD + bid/ask presentes | ✓ RTD confirmado (verde) |
| ticker_opcao in RTD + sem bid/ask | No RTD (ciano) |
| ticker_opcao não em RTD | Histórico (cinza) |

---

## Regras de Segurança

1. **Não executa ordens** — apenas exibe informações
2. **Não calcula valuation** — usa dados pré-calculados do CSV
3. **Não gera mocks** — estado vazio honesto com instrução de como resolver
4. **Não classifica automático como operacional** — exige confirmação RTD com bid/ask
5. **Disclaimer sempre visível** no topo da aba
6. O histórico **nunca substitui** a confirmação intraday via RTD

---

## Arquivos Envolvidos

| Arquivo | Papel |
|---|---|
| `pages/trading_desk.py` | Exibição da aba (nova seção adicionada) |
| `src/options/historical_opportunity_scanner.py` | Gerador dos CSVs |
| `data/realtime/options_historical_opportunities.csv` | Saída completa do scanner |
| `data/realtime/options_next_session_watchlist.csv` | Candidatas/monitorar próximo pregão |
| `src/dashboard/rtd_live_reader.py` | Fonte de dados RTD para cruzamento |

---

## Cenários Suportados

| Cenário | Badge | Estruturas |
|---|---|---|
| RECUPERACAO_APOS_QUEDA | 🟢 verde | Call Longa, Trava de Alta, Call Debit Spread |
| CONTINUACAO_ALTA | 🟢 verde | Trava de Alta, Call Debit Spread |
| CONTINUACAO_BAIXA | 🔴 vermelho | Trava de Baixa, Put Debit Spread |
| PROTECAO_CARTEIRA | 🔵 azul | Protective Put, Collar |
| RENDA_COM_ATIVO | 🟡 amarelo | Covered Call, Collar com Venda |
| VOLATILIDADE_EM_ALTA | 🟠 laranja | Monitorar (não estruturar no MVP) |
| LATERALIDADE | ⚪ cinza | Monitorar — Iron Condor futuro |
| SEM_ASSIMETRIA | ⚪ cinza | — (descartar) |

---

## Troubleshooting

**Aba vazia / "Nenhuma oportunidade histórica carregada":**
```bash
python -m src.options.historical_opportunity_scanner --verbose
```
Verificar se `data/database/scanner_quant.db` existe e tem dados COTAHIST.

**Todas as opções mostram "Histórico" (sem RTD):**
- O Profit RTD não está exportando as opções no xlsx
- As opções históricas não foram adicionadas à shortlist RTD
- Execute o watchlist builder e adicione no Profit

**Score baixo em todas as opções:**
- Banco COTAHIST pode estar desatualizado
- Volume histórico insuficiente para as opções monitoradas
- Verificar `ultima_data_cotahist` no rodapé da aba

---

*Documento gerado em 2026-05-27*
