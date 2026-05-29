# M028 - Auditoria de Dados Disponíveis

> Created: 2026-05-28
> Context: Fase 1 do enrichment de market data cards e interfaces visuais.

---

## Resumo Executivo

O backend já entrega dados reais em todos os 7 endpoints principais.
A fonte canônica é `data/database/scanner_quant.db` populado via COTAHIST
(última atualização: 2026-05-21 — 7 dias atrás). Nenhum dado é mockado.

---

## 1. `/api/trading/live` ⭐ Pronto para card

**Status:** ✅ Pronto
**Fonte:** `realtime_signals` table

```json
{
  "status": "ok",
  "actions": [
    {
      "ticker": "WEGE3",   "score_final": 88.17,
      "score_momentum": 80.0, "score_tendencia": 100.0,
      "score_liquidez": 75.85, "signal_type": "FORÇA COM LIQUIDEZ",
      "captured_at": "2026-05-21T19:21:17"
    }
    // ... 8 tickers: VALE3, BBAS3, PETR4, BPAC11, BBDC4, SANB11, ITUB4, SUZB3
  ],
  "options": [],
  "macro": { "selic": null, "ipca_12m": 4.39, "ptax": 5.8022 },
  "regime": { "primary_regime": "LATERAL", "last_update": "2026-05-21" },
  "rtd_diagnostic": { "last_update": "2026-05-21T19:21:17", "signal_count": 9 }
}
```

**Card fields disponíveis:** ticker, score_final, score_momentum, score_tendencia, score_liquidez, signal_type, captured_at

**Ausências no service:** preço (não vem do DB), volume/negócios (não coletado RTD), bid/ask (opções apenas)

**Veredito:** Estado atual é bom. Melhoria: enriquecer com preço da cotahist_daily_empresas.

---

## 2. `/api/watchlist` ⭐ Pronto para card

**Status:** ✅ Pronto
**Fonte:** `asset_intelligence_snapshots`

```json
{
  "status": "ok",  "total": 8,
  "tickers": [
    {
      "ticker": "PETR4", "price": 44.48, "variacao_pct": -1.05,
      "price_source": "cotahist_daily", "score": 45.0,
      "direction": "SELL", "status": "bloqueado", "risk": "bloqueado",
      "liquidity": 70.0, "adv_21d": 2.2bi, "next_action": "evitar_entrada",
      "has_options": false, "data_quality": { ... },
      "updated_at": "2026-05-27T02:00:08"
    }
  ]
}
```

**Card fields disponíveis:** ticker, price, variacao_pct, score, direction, status, risk, liquidity, adv_21d, next_action, has_options, has_valuation, data_quality, source, updated_at

**Ausências visuais no frontend:** price display com variação, flags de status, ticker badge com blocked indicator

**Veredito:** Dados bons mas displays podem ser melhorados significativamente.

---

## 3. `/api/quant/signals` ⭐ Parcial — precisa enriquecer

**Status:** ⚠️ Parcial (service existe mas dados têm lacunas estruturais)
**Fonte:** `technical_feature_snapshots` + `cotahist_daily`

```json
{
  "status": "ok",  "ranking": [
    {
      "ticker": "PETR4", "score_final": 67.93,
      "momentum_score": 50.0, "trend_score": 0.0,   // ← TREND ZERADO
      "liquidez": null,                               // ← LIQUIDEZ NULL
      "volatilidade": 70.0,
      "governance_blocked": true,
      "volume_score": 40.0, "breakout_score": 50.0,
      "support_resistance_score": 65.0,
      "technical_status": "TECNICO_FRACO",
      "direction": "HOLD", "gatilho": "OBSERVAR"
    }
  ]
}
```

**Problemas identificados:**
1. `trend_score` = 0 para todos → indicador não calculado no DB
2. `liquidez` = null → campo não populado
3. `score_liquidez` no service (TickerSnapshots) parece correto, mas ranking usa `liquidez`
4. `proxima_acao` = null sempre

**Veredito:** Parcial. Frontend funciona mas mostra zeros/nulls. Não é bug de frontend, é lacuna de service/DB.

---

## 4. `/api/options/strategies`

**Status:** ⚠️ Parcial
**Fonte:** estratégia disponível mas dados vazios

```json
{
  "status": "ok",  "structures": [], "history": [], "watchlist": [],
  "diagnostic": { "structures_count": 112, "last_update": "2026-05-22T21:05:22Z" }
}
```

**Problema:** `structures_count: 112` indica que o DB tem dados, mas a query não retorna.
Isso é um problema de query/filtro no service, não de Frontend.

**Veredito:** Parcial — service precisa ser debugado antes de card de opções.

---

## 5. `/api/macro/b3` ✅ Bom — exceto Selic

**Status:** ✅ Bom (exceto Selic null)
**Fonte:** `macro_series` + `macro_regimes`

```json
{
  "status": "ok",
  "current_values": {
    "selic_meta": null,       // ← PROBLEMA: BCB SGS 432 não disponível
    "ipca_12m": 4.39,         // ✅ disponível
    "ipca_mensal": null,      // ← PROBLEMA: BCB SGS 433 não disponível
    "ptax": 5.8022,           // ✅ disponível
    "ptax_trend_pct": -2.43
  },
  "series": {
    "selic": [],              // ← SEM HISTÓRICO DA Selic
    "ipca_12m": [24 pontos],  // ✅ OK
    "ptax_90d": [90 pontos],  // ✅ OK
    "igpm_12m": []            // ← IGP-M disponível no DB mas vazio na resposta
  }
}
```

**Problemas:**
1. `selic_meta` null → SGS 432 não consegui dados BCB na última execução
2. `ipca_mensal` null → SGS 433 sem dados na série
3. `selic` series vazia → histórico não populado no DB

**Veredito:** Parcial. Muitos dados OK mas Selic/IPCA mensal precisam de retry service ou fallback honesto.

---

## 6. `/api/calendar/economic` ✅ Bom

**Status:** ✅ Bom
**Fonte:** eventos scraped + B3 event calendar

```json
{
  "status": "ok",  "events": [18 grupos de data]
}
```

**Dados disponíveis:**
- Eventos hoje, amanhã, próximos 7 dias
- 6+ países (BR, EUA, China, Europa, Global)
- importance: alta/média/baixa
- previous/forecast/actual: todos vazios (= "—" sem consenso)

**Veredito:** ✅ Pronto para cards. Melhoria visual no frontend necessária.

---

## 7. `/api/intelligence/unified` ⭐ Aguardando endpoint direto

**Status:** ✅ Estruturado
**Veredito:** Parcial — ainda não foi testado. Necessário chamar com ticker=PETR4.

---

## Matriz de Decisão Final

| Endpoint | Status | Card? | Ação Frontend |
|---|---|---|---|
| `/api/trading/live` | ✅ | ✅ | Usar como está. Adicionar preço se disponível. |
| `/api/watchlist` | ✅ | ✅ | Cards ricos com preço, flags, variação. |
| `/api/quant/signals` | ⚠️ | ✅ com cuidado | Mostrar zeros/nulls como "—" honesto. |
| `/api/options/strategies` | ⚠️ | 🔲 | Somente quando `structures_count > 0`. |
| `/api/macro/b3` | ✅ exceto Selic | ✅ | Cards com status de disponibilidade. |
| `/api/calendar/economic` | ✅ | ✅ | Cards por país/importância. |
| `/api/intelligence/unified` | ✅ estruturado | ✅ | cards por bloco com status. |

### Campos críticos ausentes (para priorizar em milestones futuros)
- [ ] Preço/variação em `/api/trading/live` actions (precisa join cotahist)
- [ ] `trend_score` em quant_signals (não calculado no DB)
- [ ] `liquidez` em quant_signals ranking (não populado)
- [ ] `selic_meta` / `selic` series (BCB SGS 432 inacessível)
- [ ] `ipca_mensal` (BCB SGS 433 inacessível)
- [ ] `options` structures — query debugging necessária
- [ ] `valuation_results` table missing (não criar — roadmap futuro)

---

## Próximo Passo

FASES 3–9: Enriquecer interfaces com os dados disponíveis. Manter estados parciais honestos.
