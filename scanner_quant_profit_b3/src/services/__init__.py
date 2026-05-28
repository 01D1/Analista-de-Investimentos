"""src/services/ — Camada de serviços pura (sem Streamlit, sem HTML).

Estes módulos são a fonte canônica de dados para todas as interfaces:
  - Streamlit (cockpit interno)
  - FastAPI (ponte)
  - React/Next.js (produto comercial)

Regras:
  - Nenhum import streamlit.
  - Nenhum return HTML/CSS/st components.
  - Apenas dict/dataclass puros.
  - Tratamento de erro explícito.
  - Metadados de fonte e timestamp em todo payload.

Módulos:
  trading_desk_service.py    — ações ao vivo, RTD, macro, regime B3
  options_strategy_service.py — estruturas, histórico, Greeks, watchlist
  macro_service.py           — Selic, IPCA, PTAX, regime macro, impacto setorial
  economic_calendar_service.py — eventos econômicos, filtros, métricas
  valuation_service.py       — results, preliminary, summary, diagnostic

  # M023 — novos services para páginas frontend
  watchlist_service.py       — tickers monitorados, scores, direções, status
  quant_signals_service.py    — ranking quantitativo, sinais, direção, gatilhos
  signal_matrix_service.py    — matriz de sinais por ativo (7 blocos)
  thesis_service.py           — estrutura de tese por ticker (evidências, riscos)
  conviction_service.py       — posições com maior convicção, upgrades/downgrades
  agent_runtime_service.py    — status dos serviços, health, arquivos RTD, endpoints
"""
from __future__ import annotations

from .trading_desk_service import get_trading_desk_payload
from .options_strategy_service import get_options_strategy_payload
from .macro_service import get_macro_b3_payload
from .economic_calendar_service import get_economic_calendar_payload
from .valuation_service import get_valuation_payload
from .watchlist_service import get_watchlist_payload
from .quant_signals_service import get_quant_signals_payload
from .signal_matrix_service import get_signal_matrix_payload
from .thesis_service import get_thesis_payload
from .conviction_service import get_conviction_positions_payload
from .agent_runtime_service import get_agent_runtime_payload
from .intelligence_unified_service import get_intelligence_unified_payload

# M029 — market data core
from .market_history_service import (
    get_asset_history_payload,
    get_multi_asset_history_summary,
    get_all_actions_from_rtd,
)
from .options_market_service import (
    get_options_chain_payload,
    get_option_history_payload,
    get_options_radar_payload,
)
from .futures_market_service import (
    get_futures_live_payload,
    get_futures_summary_payload,
)

__all__ = [
    # Legacy services
    "get_trading_desk_payload",
    "get_options_strategy_payload",
    "get_macro_b3_payload",
    "get_economic_calendar_payload",
    "get_valuation_payload",
    # M023 — new services
    "get_watchlist_payload",
    "get_quant_signals_payload",
    "get_signal_matrix_payload",
    "get_thesis_payload",
    "get_conviction_positions_payload",
    "get_agent_runtime_payload",
    # M025 — unified intelligence
    "get_intelligence_unified_payload",
    # M029 — market data core
    "get_asset_history_payload",
    "get_multi_asset_history_summary",
    "get_all_actions_from_rtd",
    "get_options_chain_payload",
    "get_option_history_payload",
    "get_options_radar_payload",
    "get_futures_live_payload",
    "get_futures_summary_payload",
]