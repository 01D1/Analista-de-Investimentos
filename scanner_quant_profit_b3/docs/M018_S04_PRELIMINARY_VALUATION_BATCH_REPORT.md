# M018-S04 — Controlled Preliminary Valuation Batch for 18 New Tickers

**Milestone:** M018 — Controlled Fair Value Calculation, Validation and Preserved Value Review  
**Slice:** S04 — Preliminary Valuation Batch  
**Data:** 2026-05-26  
**Executado por:** Claude Sonnet 4.6  
**Status:** ✅ CONCLUÍDO

---

## 1. Resumo Executivo

| Métrica | Resultado |
|---------|-----------|
| Tickers processados | **18/18** ✅ |
| approved_fair_value definidos | **0** ✅ |
| Writes em asset_intelligence_snapshots | **0** ✅ |
| Alterações nos 9 preservados | **0** ✅ |
| Tickers BLOCKED_FOR_VALIDATION | **0** — todos dentro da banda 0,1×–5,0× |
| Sanity check auto-pass | **7/18** |
| Sanity check pendente (manual) | **11/18** |
| Tickers DISTRESSED | **2** (MGLU3, PCAR3) |
| Tickers FCF_NEGATIVE_EXPECTED | **3** (RECV3, SBSP3, VAMO3) |
| Tickers UNIT (validação extra) | **2** (KLBN11, TAEE11) |

> ✅ **Nenhum ticker ficou BLOCKED_FOR_VALIDATION** — todos os 18 fair values preliminares estão dentro da banda de segurança 0,1×–5,0× do preço de mercado.

> **Autorização para S05 Dashboard Integration:** ✅ **AUTORIZADO COM CONDIÇÕES** — ver Seção 7.

---

## 2. Metodologia

### 2.1 Método Principal: EV/EBITDA por Setor

Dado o estado preliminary (não aprovado) dos cálculos e a necessidade de consistência inter-setorial, foi adotado **EV/EBITDA como método único** para os 18 tickers.

```
equity_value = EBITDA × múltiplo_setor − net_debt
fair_value_por_ação = equity_value / shares_outstanding
```

Vantagens sobre DCF neste contexto:
- Mais robusto a variações de CAPEX e depreciação
- Menos sensível a premissas de crescimento (crítico em dados DFP one-shot)
- Comparabilidade direta entre tickers do mesmo setor
- Imune ao problema de FCF_ANOMALY (ex: MGLU3)

### 2.2 Múltiplos Setoriais (EV/EBITDA Base)

| Setor | Múltiplo Base | Mín | Máx | Tickers |
|-------|:-------------:|:---:|:---:|---------|
| oil_gas | 5,5× | 4,0× | 7,0× | PRIO3, RECV3 |
| utilities | 9,0× | 7,5× | 11,0× | EGIE3, SBSP3, TAEE11 |
| retail (normal) | 7,0× | 5,0× | 9,0× | AZZA3, LREN3, VIVA3* |
| retail (distressed) | 3,5–4,0× | 2,5× | 5,5× | MGLU3, PCAR3 |
| healthcare | 11,0–14,0× | 8,5× | 17,0× | FLRY3, HYPE3, RADL3 |
| industrial | 6,5–9,0× | 5,0× | 11,0× | KLBN11, RAIL3, RENT3, SUZB3, VAMO3 |

*VIVA3 usa 9,0× por ser varejo de luxo (Vivara) com margem EBITDA ~29%.

### 2.3 Fontes de Dados

- **EBITDA / net_debt:** `valuation_financial_inputs` — DFP 2025-12-31 (CVM_CSV)
- **shares_outstanding:** `financial_ltm` (preferencialmente) ou `valuation_financial_inputs` (fallback para UNIT)
- **market_price:** `price_ohlcv` — fechamento 2026-05-19

### 2.4 Critérios de Auto-Pass (sanity_check_passed=True)

Para receber `sanity_check_passed=True` automaticamente, o ticker deve satisfazer **todas** as condições:
1. FV entre **0,5× e 2,0×** do preço de mercado (banda conservadora)
2. ND/EBITDA < 3,5×
3. Não ser DISTRESSED (MGLU3, PCAR3)
4. Não ser UNIT com shares pendentes (KLBN11, TAEE11)
5. Não ter FCF_NEGATIVE_EXPECTED (RECV3, SBSP3, VAMO3)

---

## 3. Resultados por Ticker

### 3.1 Matriz Completa

| Ticker | Setor | FV Prelim (R$) | Preço (R$) | Upside | Método | Multiple | Qualidade | Confiança | Sanity | Flags |
|--------|-------|:--------------:|:----------:|:------:|--------|:--------:|:---------:|:---------:|:------:|-------|
| **PRIO3** | oil_gas | 21,28 | 68,32 | **-68,8%** | EV/EBITDA | 5,5× | FULL | LOW | ✗ PEND | elevated_leverage; EV atual 10,4× vs 5,5× target |
| **RECV3** | oil_gas | 27,93 | 12,10 | **+130,8%** | EV/EBITDA | 5,5× | PARTIAL | MEDIUM | ✗ PEND | FCF_NEGATIVE_EXPECTED; EV atual 2,9× vs 5,5× target |
| **EGIE3** | utilities | 38,21 | 31,90 | **+19,8%** | EV/EBITDA | 9,0× | FULL | LOW | ✓ PASS | elevated_leverage (3,3×); EV atual 8,9× vs 9,0× |
| **SBSP3** | utilities | 30,09 | 28,65 | **+5,0%** | EV/EBITDA | 9,0× | PARTIAL | MEDIUM | ✗ PEND | FCF_NEGATIVE_EXPECTED (-5,4B); EV atual 9,0× |
| **TAEE11** | utilities | 43,43 | 38,15 | **+13,8%** | EV/EBITDA | 9,0× | FULL | LOW | ✗ PEND | UNIT_SHARES_VALIDATION; elevated_leverage (3,7×) |
| **AZZA3** | retail | 52,99 | 19,14 | **+176,8%** | EV/EBITDA | 7,0× | FULL | HIGH | ✗ PEND | Upside > 2,0× — requer validação manual |
| **LREN3** | retail | 23,70 | 13,47 | **+76,0%** | EV/EBITDA | 7,0× | FULL | HIGH | ✓ PASS | net_cash (−1,5B); sólida |
| **MGLU3** | retail | 12,78 | 6,48 | **+97,3%** | EV/EBITDA | 4,0× | DISTRESSED | LOW | ✗ PEND | DISTRESSED_DCF_BLOCKED; FCF_ANOMALY 4,8× EBITDA |
| **PCAR3** | retail | 2,74 | 2,22 | **+23,5%** | EV/EBITDA | 3,5× | DISTRESSED | LOW | ✗ PEND | DISTRESSED_DCF_BLOCKED; NI negativo (−815M) |
| **VIVA3** | retail | 33,48 | 22,47 | **+49,0%** | EV/EBITDA | 9,0× | FULL | HIGH | ✓ PASS | margem EBITDA 29%; net_debt baixíssimo |
| **FLRY3** | healthcare | 37,21 | 15,49 | **+140,2%** | EV/EBITDA | 11,0× | FULL | HIGH | ✗ PEND | Upside > 2,0× — requer validação manual |
| **HYPE3** | healthcare | 21,63 | 22,41 | **-3,5%** | EV/EBITDA | 11,0× | FULL | LOW | ✗ PEND | very_high_leverage (3,7×); próximo ao FV |
| **KLBN11** | industrial | 29,41 | 16,23 | **+81,2%** | EV/EBITDA | 6,5× | FULL | MEDIUM | ✗ PEND | UNIT; discrepância shares ltm(7,1B)/vfi(1,21B) → 5,84× |
| **RADL3** | healthcare | 36,74 | 18,70 | **+96,5%** | EV/EBITDA | 14,0× | FULL | HIGH | ✓ PASS | ND/EBITDA baixo 0,7×; crescimento estrutural |
| **RAIL3** | industrial | 24,27 | 14,65 | **+65,6%** | EV/EBITDA | 9,0× | FULL | MEDIUM | ✓ PASS | ND/EBITDA 2,4×; concessão ferroviária |
| **RENT3** | industrial | 70,31 | 41,99 | **+67,4%** | EV/EBITDA | 8,0× | FULL | MEDIUM | ✓ PASS | ND/EBITDA 2,4×; líder locação |
| **SUZB3** | industrial | 77,40 | 41,81 | **+85,1%** | EV/EBITDA | 7,5× | FULL | LOW | ✓ PASS | ND/EBITDA 3,2×; USD revenues |
| **VAMO3** | industrial | 11,11 | 3,27 | **+239,8%** | EV/EBITDA | 7,0× | PARTIAL | MEDIUM | ✗ PEND | FCF_NEGATIVE_EXPECTED; ND/EBITDA 3,3× |

---

## 4. Análise Detalhada por Cluster

### 4.1 Petróleo & Gás (PRIO3, RECV3)

**PRIO3 — PetroRio**
- FV R$21,28 vs Preço R$68,32 = **-68,8% downside**
- O mercado precifica PRIO3 a 10,4× EV/EBITDA vs múltiplo base de 5,5×.
- Esta divergência é esperada: PRIO3 possui prêmio por (a) reservas provadas não capturadas no EBITDA corrente, (b) histórico de crescimento de produção, (c) posição de custo operacional baixo.
- **Diagnóstico**: EV/EBITDA 5,5× (sectors.yaml) é conservador para E&P premium. A metodologia preliminar conservadora está correta; a revisão em S05 deve considerar ajuste de múltiplo para 7,0–8,0× ou complementar com NAV analysis.
- ⚠️ **Flags**: `elevated_leverage_nd_ebitda=3.3x`

**RECV3 — Petrorecôncavo**
- FV R$27,93 vs Preço R$12,10 = **+130,8% upside**
- FCF negativo (-R$134M) esperado por fase de crescimento orgânico (capex R$1,6B vs D&A R$1,0B).
- EV atual apenas 2,9× EBITDA vs alvo 5,5× — severo desconto de mercado.
- ⚠️ **Flag**: `FCF_NEGATIVE_EXPECTED`

---

### 4.2 Utilities (EGIE3, SBSP3, TAEE11)

**EGIE3 — Engie Brasil** ✓ AUTO-PASS
- FV R$38,21 vs Preço R$31,90 = **+19,8% upside** (sanity_check_passed=True)
- Empresa de geração e transmissão bem gerida, alto payout histórico.
- ND/EBITDA = 3,3× (elevado para utility — alavancagem regulatória normal).
- EV atual ≈ 8,9× vs alvo 9,0× — praticamente no fair value.
- ⚠️ **Nota**: LOW confidence por ND/EBITDA acima de 3,0×.

**SBSP3 — Sabesp** ✗ FCF_NEGATIVE_EXPECTED
- FV R$30,09 vs Preço R$28,65 = **+5,0% upside**
- FCF fortemente negativo (-R$5,4B) por programa de investimentos regulatório pós-privatização.
- ND/EBITDA = 1,9× (baixo — positivo).
- O fair value está muito próximo ao preço de mercado, indicando boa precificação atual.

**TAEE11 — Taesa** ✗ UNIT_VALIDATION
- FV R$43,43 vs Preço R$38,15 = **+13,8% upside**
- shares_outstanding ltm e vfi em alinhamento (344M) — discrepância < 30% threshold.
- ND/EBITDA = 3,7× (limítrofe — acima do threshold 3,5× para auto-pass).
- Requer validação da natureza unit (TAEE11 = unit composto por ações ON+PN).

---

### 4.3 Varejo (AZZA3, LREN3, MGLU3, PCAR3, VIVA3)

**AZZA3 — Azzas 2154**
- FV R$52,99 vs Preço R$19,14 = **+176,8% upside**
- EBITDA margin saudável (15,5%), ND/EBITDA = 1,2×.
- Upside >2× impede auto-pass, mas dados são sólidos. Múltiplo 7,0× pode ser conservador para Azzas pós-fusão.
- **Pendente**: revisão manual do múltiplo setorial e validação de sinergias pós-fusão.

**LREN3 — Lojas Renner** ✓ AUTO-PASS
- FV R$23,70 vs Preço R$13,47 = **+76,0% upside**
- Net cash (-R$1,5B net_debt), margem EBITDA 19,5% — fundamentos sólidos.
- AUTO-PASS por estar dentro da banda 0,5×–2,0× e leverage negativo.

**MGLU3 — Magazine Luiza** ✗ DISTRESSED_DCF_BLOCKED
- FV R$12,78 vs Preço R$6,48 = **+97,3% upside**
- **DCF BLOQUEADO** conforme regra M018-S03.
- Net income marginal (R$204M / R$38,7B receita = margem 0,5%).
- ⚠️ **FCF_ANOMALY**: FCF = R$15,4B vs EBITDA = R$3,2B (ratio 4,8×) — provavelmente liberação de capital de giro ou evento não-recorrente. Não usar FCF para valuation.
- Múltiplo conservador 4,0× reflete risco de execução.
- **Status**: DISTRESSED — requer validação manual aprofundada.

**PCAR3 — GPA (Grupo Pão de Açúcar)** ✗ DISTRESSED_DCF_BLOCKED
- FV R$2,74 vs Preço R$2,22 = **+23,5% upside**
- **DCF BLOQUEADO** conforme regra M018-S03.
- Net income negativo (-R$815M) — único ticker com NI negativo entre os 18.
- EBITDA positivo (R$984M) permite o cálculo EV/EBITDA com múltiplo reduzido (3,5×).
- Equity value = R$1,36B sobre ações R$2,22 → margem de segurança mínima.
- **Status**: DISTRESSED — upside modesto, fundamentalmente fragilizado.

**VIVA3 — Vivara** ✓ AUTO-PASS
- FV R$33,48 vs Preço R$22,47 = **+49,0% upside**
- Melhor qualidade de negócio no cluster varejo: margem EBITDA ~29%, net_debt mínimo (R$133M).
- AUTO-PASS com HIGH confidence.

---

### 4.4 Saúde e Farmácia (FLRY3, HYPE3, RADL3)

**FLRY3 — Fleury**
- FV R$37,21 vs Preço R$15,49 = **+140,2% upside**
- Dados sólidos (margem EBITDA 25,6%, ND/EBITDA 1,5×), HIGH confidence.
- Upside 2,4× impede auto-pass mas indica forte potencial de valorização.
- Pendente validação manual do múltiplo (11×) para diagnósticos no Brasil.

**HYPE3 — Hypera**
- FV R$21,63 vs Preço R$22,41 = **-3,5% downside**
- Praticamente no fair value ao múltiplo 11×.
- Bloqueio de auto-pass por ND/EBITDA = 3,7× (acima do threshold 3,5×).
- ⚠️ **Flag**: `very_high_leverage_nd_ebitda=3.7x` — alavancagem pós-aquisições merece atenção.

**RADL3 — Raia Drogasil** ✓ AUTO-PASS
- FV R$36,74 vs Preço R$18,70 = **+96,5% upside**
- Baixíssimo ND/EBITDA (0,7×), crescimento estrutural de farmácias no Brasil.
- Múltiplo 14× justificado por crescimento orgânico contínuo e expansão de lojas.
- AUTO-PASS (ratio 1,96× < 2,0×; ND/EBITDA 0,7× ≪ 3,5×).

---

### 4.5 Industrial, Logística e Locação (KLBN11, RAIL3, RENT3, SUZB3, VAMO3)

**KLBN11 — Klabin** ✗ UNIT_VALIDATION
- FV R$29,41 vs Preço R$16,23 = **+81,2% upside**
- ⚠️ **Discrepância crítica de shares**: ltm = 7.106M vs vfi = 1.215M (ratio 5,84×).
  - Usando vfi (1.215M) — market cap R$19,7B → alinhado com expectativa para Klabin.
  - ltm de 7.106M geraria market cap absurdo (R$115B) → confirmado como inválido.
  - **Raiz provável**: ltm pode estar contando ON+PN separadamente × n (dilution calc).
- Múltiplo 6,5× conservador para celulose integrada (EBITDA margin 45,7%).
- Requer validação manual das shares antes de promover.

**RAIL3 — Rumo** ✓ AUTO-PASS
- FV R$24,27 vs Preço R$14,65 = **+65,6% upside**
- Concessão ferroviária de longo prazo, EBITDA margin 49% — negócio de alta qualidade.
- ND/EBITDA = 2,4× controlado. AUTO-PASS.

**RENT3 — Localiza** ✓ AUTO-PASS
- FV R$70,31 vs Preço R$41,99 = **+67,4% upside**
- Líder absoluto de locação de veículos no Brasil.
- ND/EBITDA = 2,4× (razoável para asset-heavy). AUTO-PASS.

**SUZB3 — Suzano** ✓ AUTO-PASS
- FV R$77,40 vs Preço R$41,81 = **+85,1% upside**
- Maior produtora de celulose de eucalipto do mundo. Receitas em USD.
- ND/EBITDA = 3,2× (elevado por capex pós-Arauco) mas < 3,5× threshold.
- AUTO-PASS com LOW confidence (leverage moderada).

**VAMO3 — Vamos Locação** ✗ FCF_NEGATIVE_EXPECTED
- FV R$11,11 vs Preço R$3,27 = **+239,8% upside**
- FCF negativo (-R$918M) esperado por crescimento acelerado de frota.
- ND/EBITDA = 3,3× (elevado para o setor).
- Upside 3,4× dentro da banda segura (< 5,0×) — não bloqueado.
- Requer validação manual: alta sensibilidade à trajetória de juros e CAPEX.

---

## 5. Validações de Segurança

### 5.1 Verificação Pós-Escrita (4/4 checks ✅)

| Check | Resultado | Detalhes |
|-------|-----------|----------|
| C1: 18/18 processados | ✅ PASS | Todos os 18 tickers têm registro em `valuation_results` |
| C2: 0 approved_fair_value | ✅ PASS | `approved_fair_value IS NULL` para todos os 18 |
| C3: 0 writes em asset_intelligence_snapshots | ✅ PASS | Tabela não tocada |
| C4: 0 alterações nos preservados | ✅ PASS | 9 preservados com `source=M018_COMPARISON` inalterados |

### 5.2 Proteções Ativas

- `write_preliminary()` bloqueou automaticamente qualquer tentativa de escrever nos 9 PRESERVE_EXISTING (proteção RULE-04 ativa)
- `_preflight_checks()` verificou overlap PRESERVE_EXISTING × NEW_TICKERS antes de qualquer escrita → 0 overlap confirmado
- `approved_fair_value` permanece NULL para todos os 18 tickers (RULE-02 ativa)
- `asset_intelligence_snapshots` não foi acessada em nenhum momento (RULE-03 ativa)

### 5.3 Validação de Shares

| Ticker | Tipo | shares_ltm | shares_vfi | Discrepância | Usado | Flag |
|--------|------|:----------:|:----------:|:----------:|:-----:|------|
| KLBN11 | UNIT | 7.106M | 1.215M | 5,84× | **vfi** | UNIT_SHARES_DISCREPANCY |
| TAEE11 | UNIT | 344M | 344M | 1,00× | ltm | unit_shares_validation_required |
| MGLU3 | normal | 775M | 775M | 1,00× | ltm | — |
| PCAR3 | normal | 495M | 492M | 1,01× | ltm | — |
| Demais | normal | ≈match | ≈match | < 5% | ltm | — |

---

## 6. CSV Matrix

Ver arquivo: **`M018_S04_RESULTS.csv`** (gerado junto a este relatório)

Campos: `ticker, sector, method, multiple, ebitda_bn, net_debt_bn, shares_mn, market_price, preliminary_fv, upside_pct, nd_ebitda, current_ev_ebitda, input_quality, confidence, sanity_check_passed, flags`

---

## 7. Autorização para S05 Dashboard Integration

### ✅ AUTORIZADO COM CONDIÇÕES

**Condições para integração no dashboard S05:**

1. **18/18 tickers:** podem aparecer no dashboard com status `preliminary`
2. **Disclaimer obrigatório** em todos os cards: *"Valuation Preliminar — não aprovado — sujeito a revisão"*
3. **MGLU3 e PCAR3:** exibir badge `DISTRESSED` + tooltip explicativo (DCF bloqueado)
4. **KLBN11:** exibir badge `UNIT_REVIEW` + nota sobre discrepância de shares
5. **PRIO3:** exibir badge `METHODOLOGY_DIVERGENCE` + nota sobre múltiplo vs mercado (−69%)
6. **FCF_NEGATIVE tickers** (RECV3, SBSP3, VAMO3): exibir ícone de alerta FCF
7. **Não expor** `approved_fair_value` (campo NULL) — usar apenas `preliminary_fair_value`
8. **Não habilitar** botão "Aprovar" para qualquer um dos 18 tickers até S05 aprovação formal

### Tickers com sanity_check_passed=True (7) — mais confiáveis para exibição prioritária:
`EGIE3`, `LREN3`, `VIVA3`, `RADL3`, `RAIL3`, `RENT3`, `SUZB3`

### Tickers pendentes de revisão manual antes de S05 (11):
`PRIO3`, `RECV3`, `SBSP3`, `TAEE11`, `AZZA3`, `MGLU3`, `PCAR3`, `FLRY3`, `HYPE3`, `KLBN11`, `VAMO3`

---

## 8. Próximos Passos

| Passo | Ação | Prioridade |
|-------|------|-----------|
| **S05** | Dashboard integration — exibir 18 tickers como preliminary | ALTA |
| **S05** | Resolver discrepância shares KLBN11 (ltm 7,1B vs vfi 1,2B) | ALTA |
| **S05** | Revisar múltiplo PRIO3 (5,5× → considerar 7,0–8,0× para E&P premium) | MÉDIA |
| **S05** | Validar FCF_ANOMALY MGLU3 (FCF 15,4B vs EBITDA 3,2B — possível working capital) | MÉDIA |
| **S06** | Sanity check manual dos 11 tickers PEND | ALTA |
| **S06** | Complementar PRIO3 com NAV analysis (reservas) | ALTA |
| **S06** | Calibrar múltiplo healthcare (FLRY3 +140%, RADL3 +97%) com peers regionais | MÉDIA |
| **Futuro** | Migrar MGLU3/PCAR3 de EV/EBITDA para P/BV ou Asset-Liquidation quando NI voltar positivo | BAIXA |

---

*Relatório gerado em 2026-05-26 às 15:27 UTC*  
*Fonte de dados: `ingestion.db` → tabelas `valuation_financial_inputs`, `financial_ltm`, `price_ohlcv`*  
*Script: `src/valuation/m018_s04_preliminary_batch.py`*  
*Todos os valores em BRL. Preços de fechamento em 2026-05-19.*
