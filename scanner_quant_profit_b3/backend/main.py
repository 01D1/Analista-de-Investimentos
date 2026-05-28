"""
backend/main.py — FastAPI minimal como ponte entre Python motors e React/Next.js.

Arquitetura:
  src/services/*.py  →  backend/main.py (FastAPI)  →  frontend/ (Next.js)

Regras:
  - Consome src/services/ apenas.
  - Não calcula nada.
  - Não acessa banco direto.
  - Não retorna HTML.
  - Cada endpoint chama exactly um service function.

Startup:
  uvicorn backend.main:app --port 8000 --reload
  → http://localhost:8000/health
  → http://localhost:8000/docs (Swagger UI)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Services — fonte canônica de dados
from src.services import (
    get_trading_desk_payload,
    get_options_strategy_payload,
    get_macro_b3_payload,
    get_economic_calendar_payload,
    get_valuation_payload,
    get_watchlist_payload,
    get_quant_signals_payload,
    get_signal_matrix_payload,
    get_thesis_payload,
    get_conviction_positions_payload,
    get_agent_runtime_payload,
    get_intelligence_unified_payload,
    get_asset_history_payload,
    get_multi_asset_history_summary,
    get_all_actions_from_rtd,
    get_options_chain_payload,
    get_option_history_payload,
    get_options_radar_payload,
    get_futures_live_payload,
    get_futures_summary_payload,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Radar Macro API",
    version="1.0.0",
    description="Ponte entre motores Python (src/services/) e frontend React/Next.js",
)

# CORS: permite frontend Next.js em localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, Any]:
    """Health check — indica se a API e os services estão operacionais."""
    return {
        "status": "ok",
        "service": "radar-macro-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Trading Desk ─────────────────────────────────────────────────────────────

@app.get("/api/trading/live")
def api_trading_live() -> dict[str, Any]:
    """
    Dados ao vivo do Trading Desk: ações, opções, macro, regime B3, diagnóstico RTD.
    Consumido por: frontend/components/pages/TradingDesk.tsx (futuro)
    """
    logger.info("[api] /api/trading/live")
    return get_trading_desk_payload()


# ── Opções / Estratégias ──────────────────────────────────────────────────────

@app.get("/api/options/strategies")
def api_options_strategies() -> dict[str, Any]:
    """
    Estratégias e oportunidades de opções: estruturas, histórico, Greeks, watchlist.
    Consumido por: frontend/components/pages/OptionsStrategy.tsx (futuro)
    """
    logger.info("[api] /api/options/strategies")
    return get_options_strategy_payload()


@app.get("/api/options/historical-radar")
def api_options_historical_radar() -> dict[str, Any]:
    """
    Radar histórico de opções (backtest, candidatos, scoring).
    Alias para /api/options/strategies com focus em histórico.
    """
    logger.info("[api] /api/options/historical-radar")
    payload = get_options_strategy_payload()
    return {
        "status":    payload.get("status", "ok"),
        "timestamp": payload.get("timestamp"),
        "history":   payload.get("history", []),
        "watchlist": payload.get("watchlist", []),
        "structures": payload.get("structures", [])[:20],
        "diagnostic": {
            "history_count":  payload.get("diagnostic", {}).get("history_count", 0),
            "watchlist_count": payload.get("diagnostic", {}).get("watchlist_count", 0),
        },
    }


# ── Macro B3 ─────────────────────────────────────────────────────────────────

@app.get("/api/macro/b3")
def api_macro_b3() -> dict[str, Any]:
    """
    Macro B3: Selic, IPCA, PTAX, regime macro, impacto setorial, séries para gráficos.
    Consumido por: frontend/components/pages/MacroEngine.tsx
    """
    logger.info("[api] /api/macro/b3")
    return get_macro_b3_payload()


# ── Calendário Econômico ──────────────────────────────────────────────────────

@app.get("/api/calendar/economic")
def api_calendar_economic(
    start_date: str | None = None,
    end_date: str | None = None,
    countries: str | None = None,
    importances: str | None = None,
    search: str = "",
) -> dict[str, Any]:
    """
    Calendário econômico: eventos, métricas, filtros.
    
    Query params:
      start_date: ISO date (YYYY-MM-DD), default: hoje
      end_date: ISO date (YYYY-MM-DD), default: +30 dias
      countries: comma-separated (e.g. "BR,US")
      importances: comma-separated (e.g. "alta,média")
      search: texto livre para busca
    """
    logger.info(f"[api] /api/calendar/economic start={start_date} end={end_date}")

    # Parse date params
    from datetime import date, timedelta
    start = date.fromisoformat(start_date) if start_date else date.today()
    end   = date.fromisoformat(end_date)   if end_date   else date.today() + timedelta(days=30)

    # Parse lists
    country_list   = [c.strip() for c in countries.split(",")] if countries else None
    importance_list = [i.strip() for i in importances.split(",")] if importances else None

    return get_economic_calendar_payload(
        start_date=start,
        end_date=end,
        countries=country_list if country_list else None,
        importances=importance_list if importance_list else None,
        search_text=search,
    )


# ── Valuation ─────────────────────────────────────────────────────────────────

@app.get("/api/valuation/summary")
def api_valuation_summary(
    ticker: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Resumo de valuation: resultados, preliminary, summary, diagnostic.
    
    Query params:
      ticker: filtro por ticker específico (opcional)
      limit: limite de resultados (default 20, max 100)
    """
    logger.info(f"[api] /api/valuation/summary ticker={ticker} limit={limit}")
    limit = min(limit, 100)
    return get_valuation_payload(ticker=ticker, limit=limit)


# ── Radar (oportunidades) — proxy para frontend existente ─────────────────────

@app.get("/api/radar/opportunities")
def api_radar_opportunities() -> dict[str, Any]:
    """
    Radar de oportunidades combinando sinais quant + intelligence.
    Alias que também pode consumir get_trading_desk_payload() para ações.
    
    Nota: O frontend atual (frontend/components/pages/RadarAI.tsx) espera
    formato simples [{ticker, type, score, description}].
    Mantém backward compat enquanto migra para formato completo.
    """
    logger.info("[api] /api/radar/opportunities")
    payload = get_trading_desk_payload()

    # Converte para formato esperado pelo frontend existente
    opportunities = []
    for action in payload.get("actions", []):
        opportunities.append({
            "ticker":      action.get("ticker", ""),
            "type":        action.get("signal_type", "NEUTRO"),
            "score":       action.get("score_final", 50),
            "description": f"Score: {action.get('score_final', 'N/A')} | Momentum: {action.get('score_momentum', 'N/A')}",
        })

    return {
        "status":         payload.get("status", "ok"),
        "timestamp":      payload.get("timestamp"),
        "opportunities":  opportunities,
        "total":          len(opportunities),
        "rtd_diagnostic": payload.get("rtd_diagnostic", {}),
    }


# ── Oportunidades legado (mock original) ──────────────────────────────────────
# Mantido para backward compat do frontend durante transição.
# Remover quando frontend for atualizado para /api/radar/opportunities.

@app.get("/api/opportunities")
def api_opportunities() -> list[dict[str, Any]]:
    """
    Endpoint legado — mantinha mock data.
    Agora tenta consumir get_trading_desk_payload().
    Se falhar, retorna mock para não quebrar frontend.
    """
    try:
        payload = get_trading_desk_payload()
        if payload.get("status") == "error":
            raise RuntimeError("Service unavailable")

        opportunities = []
        for action in payload.get("actions", []):
            opportunities.append({
                "ticker":      action.get("ticker", ""),
                "type":        action.get("signal_type", "NEUTRO"),
                "score":       action.get("score_final", 50),
                "description": f"Score: {action.get('score_final', 'N/A')} | Momentum: {action.get('score_momentum', 'N/A')}",
            })
        return opportunities[:10]  # limit
    except Exception:
        # Fallback: mock para não quebrar frontend durante transição
        logger.warning("[api] /api/opportunities: fallback para mock")
        return [
            {"ticker": "VALE3", "type": "DCF DIVERGENCE", "score": 78,
             "description": "Preço descontado frente ao valor justo estimado."},
            {"ticker": "PETR4", "type": "MOMENTUM", "score": 82,
             "description": "Momentum positivo com liquidez relevante."},
            {"ticker": "ITUB4", "type": "IPE EVENT", "score": 71,
             "description": "Evento corporativo monitorado pelo radar."},
        ]


# ── System ────────────────────────────────────────────────────────────────────

@app.get("/api/system/health")
def api_system_health() -> dict[str, Any]:
    """
    Health detalhado: serviços disponíveis, DB acessível, última atualização.
    """
    health_checks = {
        "trading_desk": False,
        "options":      False,
        "macro":         False,
        "calendar":      False,
        "valuation":    False,
    }
    errors: list[str] = []

    try:
        p = get_trading_desk_payload()
        health_checks["trading_desk"] = p.get("status") != "error"
        if p.get("errors"):
            errors.extend(p["errors"])
    except Exception as e:
        health_checks["trading_desk"] = False
        errors.append(f"trading_desk: {e}")

    try:
        p = get_options_strategy_payload()
        health_checks["options"] = p.get("status") != "error"
    except Exception:
        health_checks["options"] = False

    try:
        p = get_macro_b3_payload()
        health_checks["macro"] = p.get("status") != "error"
    except Exception:
        health_checks["macro"] = False

    try:
        p = get_economic_calendar_payload()
        health_checks["calendar"] = p.get("status") != "error"
    except Exception:
        health_checks["calendar"] = False

    try:
        p = get_valuation_payload(limit=1)
        health_checks["valuation"] = p.get("status") != "error"
    except Exception:
        health_checks["valuation"] = False

    all_ok = all(health_checks.values())
    return {
        "status":    "ok" if all_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services":  health_checks,
        "errors":     errors,
    }


# ── M023: Watchlist ───────────────────────────────────────────────────────────

@app.get("/api/watchlist")
def api_watchlist() -> dict[str, Any]:
    """
    Watchlist: tickers monitorados com scores, direção, status, risco, liquidez.
    Consumido por: página Watchlist do frontend.

    Query params:
      (nenhum — retorna todos os tickers monitorados)
    """
    logger.info("[api] /api/watchlist")
    return get_watchlist_payload()


# ── M023: Quant Signals ────────────────────────────────────────────────────────

@app.get("/api/quant/signals")
def api_quant_signals() -> dict[str, Any]:
    """
    Ranking quantitativo: scores, direção, gatilho, momentum, tendência, liquidez.
    Consumido por: página Quant Core do frontend.
    """
    logger.info("[api] /api/quant/signals")
    return get_quant_signals_payload()


# ── M023: Signal Matrix ────────────────────────────────────────────────────────

@app.get("/api/ai/signal-matrix")
def api_signal_matrix(
    ticker: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Matriz de sinais por ativo: 7 blocos (técnico, momentum, liquidez,
    macro, opções, valuation, risco), score agregado, conflitos, conclusão.

    Query params:
      ticker: filtro por ticker específico (opcional)
      limit: limite de ativos (default 20, max 100)
    """
    logger.info(f"[api] /api/ai/signal-matrix ticker={ticker} limit={limit}")
    limit = min(limit, 100)
    return get_signal_matrix_payload(ticker=ticker, limit=limit)


# ── M023: Thesis Builder ───────────────────────────────────────────────────────

@app.get("/api/ai/thesis")
def api_ai_thesis(
    ticker: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Tese de investimento por ticker: hipótese, evidências bullish/bearish,
    fatores de risco, catalisadores, indicadores usados, confiança.

    Query params:
      ticker: filtro por ticker específico (opcional)
      limit: limite de teses (default 10)
    """
    logger.info(f"[api] /api/ai/thesis ticker={ticker}")
    return get_thesis_payload(ticker=ticker, limit=limit)


# ── M023: Conviction Desk ─────────────────────────────────────────────────────

@app.get("/api/conviction/positions")
def api_conviction_positions(
    limit: int = 20,
    days: int = 30,
) -> dict[str, Any]:
    """
    Posições com maior convicção: score, upside, nível de convicção,
    upgrades/downgrades, racional.

    Query params:
      limit: limite de posições (default 20)
      days: janela de histórico para mudanças de score (default 30)
    """
    logger.info(f"[api] /api/conviction/positions limit={limit} days={days}")
    limit = min(limit, 50)
    days = min(days, 90)
    return get_conviction_positions_payload(limit=limit, days=days)


# ── M023: Agent Runtime ───────────────────────────────────────────────────────

@app.get("/api/agents/status")
def api_agents_status() -> dict[str, Any]:
    """
    Status do Agent Runtime: backend, services, DB, RTD, endpoints, arquivos gerados.
    Health checks com latência para cada serviço.
    """
    logger.info("[api] /api/agents/status")
    return get_agent_runtime_payload()


# ── M025: Intelligence Unified ────────────────────────────────────────────────

@app.get("/api/intelligence/unified")
def api_intelligence_unified(
    ticker: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Payload unificado com todos os blocos de inteligência:
    watchlist, quant_signals, signal_matrix, thesis, macro,
    options_strategies, valuation, conviction, agent_runtime.

    Query params:
      ticker: filtro por ticker específico (opcional)
      limit: limite de itens por bloco (default 20, max 100)

    Retorna status=partial + errors[] se algum bloco falhar.
    M025 só concluído quando este endpoint retornar HTTP 200.
    """
    logger.info(f"[api] /api/intelligence/unified ticker={ticker} limit={limit}")
    limit = min(limit, 100)
    return get_intelligence_unified_payload(ticker=ticker, limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ── M029: Market History ─────────────────────────────────────────────────────────

@app.get("/api/market/assets/{ticker}/history")
def api_asset_history(
    ticker: str,
    period: str = "1y",
) -> dict[str, Any]:
    """
    Histórico de ação: OHLCV snapshot + indicadores técnicos + resumos de retorno.
    Fonte: RTD PROFIT.xlsx (snapshot único; COTAHIST series em milestone futuro).

    Query params:
      period: 1w/1m/3m/6m/1y/ytd (default 1y — respeitado quando COTAHIST disponível)
    """
    logger.info(f"[api] /api/market/assets/{ticker}/history period={period}")
    return get_asset_history_payload(ticker=ticker, period=period)


@app.get("/api/market/assets/history-summary")
def api_market_history_summary(
    tickers: str,
) -> dict[str, Any]:
    """
    Resumo histórico para múltiplos tickers.
    Útil para cards de ações na Watchlist e RadarAI.

    Query params:
      tickers: lista separada por vírgula, ex: PETR4,VALE3,WEGE3
    """
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    logger.info(f"[api] /api/market/assets/history-summary tickers={ticker_list}")
    return get_multi_asset_history_summary(ticker_list)


@app.get("/api/market/actions")
def api_market_actions() -> dict[str, Any]:
    """
    Todas as ações disponíveis no RTD PROFIT.xlsx.
    Usado por: RadarAI, Trading Desk, cards de ações.
    """
    logger.info("[api] /api/market/actions")
    return get_all_actions_from_rtd()


# ── M029: Options ─────────────────────────────────────────────────────────────────

@app.get("/api/options/chain/{underlying}")
def api_options_chain(
    underlying: str,
    expiration: str | None = None,
) -> dict[str, Any]:
    """
    Cadeia de opções por ativo objeto: calls, puts, strikes, Greeks, spread, liquidez.
    Fontes: RTD PROFIT.xlsx + options CSVs.

    Query params:
      expiration: filtro por vencimento YYYY-MM-DD (opcional)
    """
    logger.info(f"[api] /api/options/chain/{underlying} expiration={expiration}")
    return get_options_chain_payload(underlying=underlying, expiration=expiration)


@app.get("/api/options/history/{option_ticker}")
def api_option_history(
    option_ticker: str,
    period: str = "6m",
) -> dict[str, Any]:
    """
    Histórico de uma opção específica.
    Retorna registros de múltiplas fontes (RTD, watchlist, historical CSV).

    Query params:
      period: 1m/3m/6m/ytd (default 6m)
    """
    logger.info(f"[api] /api/options/history/{option_ticker} period={period}")
    return get_option_history_payload(option_ticker=option_ticker, period=period)


@app.get("/api/options/radar")
def api_options_radar(
    underlying: str | None = None,
) -> dict[str, Any]:
    """
    Radar de oportunidades de opções: candidatas próximo pregão, monitorar RTD,
    aguardando liquidez. Agregação por status e por ativo objeto.
    Fontes: options CSVs.

    Query params:
      underlying: filtro por ativo objeto, ex: PETR4 (opcional)
    """
    logger.info(f"[api] /api/options/radar underlying={underlying}")
    return get_options_radar_payload(underlying=underlying)


# ── M029: Futures ─────────────────────────────────────────────────────────────────

@app.get("/api/futures/live")
def api_futures_live() -> dict[str, Any]:
    """
    Futuros e índices ao vivo do RTD PROFIT.xlsx.
    Detecta: DOL, WIN, IND, DI, IBOV, SMLL, IFIX e outros.

    Empty state honesto se nenhum futuro estiver configurado no RTD.
    """
    logger.info("[api] /api/futures/live")
    return get_futures_live_payload()


@app.get("/api/futures/summary")
def api_futures_summary() -> dict[str, Any]:
    """
    Resumo de futuros e índices: agregações por classe, IBOV, variação.
    """
    logger.info("[api] /api/futures/summary")
    return get_futures_summary_payload()