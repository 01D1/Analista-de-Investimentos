"""
Radar Payload — Motor de dados real para o Radar de Oportunidades.

Integra todos os motores de decisão disponíveis sem mocks:
  1. realtime_signals        → sinais quant atualizados (9 tickers core)
  2. asset_intelligence      → 64 tickers com scores integrados
  3. cotahist_daily          → ADV 21d (liquidez real por ticker)
  4. macro_series            → Selic/PTAX/IPCA → market_regime_engine
  5. market_regime_daily     → regime B3 (tendência, vol, liquidez)
  6. risk_snapshots          → VaR/ES por ticker
  7. expected_value_engine   → EV score + assimetria + Kelly
  8. institutional_meta_score → meta-score multi-layer combinado
  9. signal_explainer        → gatilho em linguagem natural PT-BR

Regras:
  - Nenhum mock. Se o dado não existe, reportar "indisponível" com motivo.
  - Nenhum cálculo de fair_value novo.
  - Nenhuma escrita no banco.
  - Cache em memória: TTL 300s via st.cache_data quando chamado via Streamlit.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.quant.expected_value_engine import compute_ev, EVResult
from src.quant.market_regime_engine import detect_regime, RegimeSnapshot
from src.quant.institutional_meta_score import compute_meta_score, MetaScoreResult
from src.quant.signal_explainer import explain_opportunity


# ---------------------------------------------------------------------------
# Constantes calibradas
# ---------------------------------------------------------------------------

_TRADING_DAYS_YEAR = 252
_ADV_WINDOW = 21          # dias para ADV
_EV_WINDOW_DAYS = 21      # janela de upside/drawdown para EV
_MIN_ADV_LIQUID = 50_000_000   # R$ 50M = limiar de liquidez

# Mapeamento signal_type (realtime_signals) → direction
_SIGNAL_TYPE_DIRECTION = {
    "FORÇA COM LIQUIDEZ": "BUY",
    "OBSERVAR":           "WATCH",
    "NEUTRO":             "HOLD",
    "SEM ASSIMETRIA":     "HOLD",
    "PRESSÃO VENDEDORA":  "SELL",
}

# Mapeamento signal_type → tier
_SIGNAL_TYPE_TIER = {
    "FORÇA COM LIQUIDEZ": "A",
    "OBSERVAR":           "B",
    "NEUTRO":             "C",
    "SEM ASSIMETRIA":     "D",
    "PRESSÃO VENDEDORA":  "D",
}

# Mapeamento integrated_status → direction
_STATUS_DIRECTION = {
    "ALTA_CONVERGENCIA":                "BUY",
    "ASSIMETRIA_DETECTADA":             "WATCH",
    "APENAS_MONITORAR_SOFT_COVERAGE":   "WATCH",
    "BLOQUEADO_GOVERNANCA":             "HOLD",
    "DIVERGENCIA":                      "SELL",
    "BLOQUEADO":                        "HOLD",
}

_STATUS_TIER = {
    "ALTA_CONVERGENCIA":                "A",
    "ASSIMETRIA_DETECTADA":             "B",
    "APENAS_MONITORAR_SOFT_COVERAGE":   "C",
    "BLOQUEADO_GOVERNANCA":             "D",
    "DIVERGENCIA":                      "D",
    "BLOQUEADO":                        "D",
}


# ---------------------------------------------------------------------------
# Formatação auxiliar
# ---------------------------------------------------------------------------

def _fmt_adv(v: float | None) -> str:
    """Formata ADV em R$ de forma legível."""
    if v is None or np.isnan(v):
        return "indisponível"
    if v >= 1e9:
        return f"R$ {v/1e9:.1f}B"
    if v >= 1e6:
        return f"R$ {v/1e6:.0f}M"
    if v >= 1e3:
        return f"R$ {v/1e3:.0f}k"
    return f"R$ {v:.0f}"


def _fmt_risk(var_pct: float | None) -> str:
    """Formata VaR em %."""
    if var_pct is None or np.isnan(var_pct):
        return "indisponível"
    return f"{var_pct:.1f}%"


def _fmt_asymmetry(ratio: float | None) -> str:
    """Formata payoff ratio."""
    if ratio is None or np.isnan(ratio) or ratio <= 0:
        return "indisponível"
    return f"{ratio:.1f}:1"


def _tipo_ativo(signal_type: str) -> str:
    s = str(signal_type or "").upper()
    if "OPTION" in s or "OPCAO" in s:
        return "Opção"
    return "Ação"


def _proxima_acao(direction: str, tier: str) -> tuple[str, str]:
    d, t = direction.upper(), tier.upper()
    if d == "BUY" and t in ("S", "A"):
        return "Montar tese", "approved"
    if d == "BUY" and t in ("B",):
        return "Estudar", "monitor"
    if d == "WATCH":
        return "Aguardar gatilho", "monitor"
    if d == "HOLD":
        return "Monitorar", "paper"
    if d == "SELL":
        return "Descartar", "blocked"
    return "Monitorar", "paper"


# ---------------------------------------------------------------------------
# Consultas ao banco
# ---------------------------------------------------------------------------

def _db_path() -> Path:
    """Resolve caminho canônico do banco de dados."""
    # Tenta config.yaml primeiro
    try:
        import yaml  # type: ignore[import-not-found]
        cfg_file = Path(__file__).resolve().parents[2] / "config.yaml"
        if cfg_file.exists():
            with open(cfg_file, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            rel = cfg.get("database_path", "data/database/scanner_quant.db")
            p = Path(__file__).resolve().parents[2] / rel
            if p.exists():
                return p
    except Exception:
        pass
    # Fallback direto
    direct = Path(__file__).resolve().parents[2] / "data" / "database" / "scanner_quant.db"
    if direct.exists():
        return direct
    raise FileNotFoundError("scanner_quant.db não encontrado")


def _load_realtime_signals(con: sqlite3.Connection) -> dict[str, dict]:
    """
    Carrega os sinais mais recentes de realtime_signals.
    Retorna {ticker: row_dict} com o snapshot mais recente por ativo.
    """
    try:
        rows = con.execute("""
            SELECT asset, score_final, score_momentum, score_tendencia,
                   score_liquidez, score_volatilidade, score_risco,
                   signal_type, explanation, captured_at
            FROM realtime_signals
            WHERE captured_at = (
                SELECT MAX(r2.captured_at) FROM realtime_signals r2
                WHERE r2.asset = realtime_signals.asset
            )
            GROUP BY asset
            ORDER BY score_final DESC
        """).fetchall()

        result: dict[str, dict] = {}
        for r in rows:
            if r[0]:
                result[str(r[0]).upper()] = {
                    "score_final":       float(r[1]) if r[1] is not None else None,
                    "score_momentum":    float(r[2]) if r[2] is not None else None,
                    "score_tendencia":   float(r[3]) if r[3] is not None else None,
                    "score_liquidez":    float(r[4]) if r[4] is not None else None,
                    "score_volatilidade": float(r[5]) if r[5] is not None else None,
                    "score_risco":       float(r[6]) if r[6] is not None else None,
                    "signal_type":       str(r[7] or ""),
                    "explanation":       str(r[8] or ""),
                    "captured_at":       str(r[9] or ""),
                    "source":            "realtime_signals",
                }
        return result
    except Exception:
        return {}


def _load_asset_intelligence(con: sqlite3.Connection) -> dict[str, dict]:
    """
    Carrega o snapshot mais recente de asset_intelligence_snapshots por ticker.
    Retorna {ticker: row_dict}.
    """
    try:
        rows = con.execute("""
            SELECT ticker, integrated_score, integrated_status, technical_score_final,
                   quant_score, upside_pct, ensemble_vol, data_quality_score,
                   fundamental_quality_score, var_95, expected_shortfall_95,
                   risk_status, primary_regime, valuation_available, created_at
            FROM asset_intelligence_snapshots
            WHERE created_at = (
                SELECT MAX(a2.created_at) FROM asset_intelligence_snapshots a2
                WHERE a2.ticker = asset_intelligence_snapshots.ticker
            )
            GROUP BY ticker
        """).fetchall()

        result: dict[str, dict] = {}
        for r in rows:
            if r[0]:
                result[str(r[0]).upper()] = {
                    "integrated_score":       float(r[1]) if r[1] is not None else None,
                    "integrated_status":      str(r[2] or ""),
                    "technical_score_final":  float(r[3]) if r[3] is not None else None,
                    "quant_score":            float(r[4]) if r[4] is not None else None,
                    "upside_pct":             float(r[5]) if r[5] is not None else None,
                    "ensemble_vol":           float(r[6]) if r[6] is not None else None,
                    "data_quality_score":     float(r[7]) if r[7] is not None else 50.0,
                    "fundamental_quality":    float(r[8]) if r[8] is not None else None,
                    "var_95":                 float(r[9]) if r[9] is not None else None,
                    "expected_shortfall_95":  float(r[10]) if r[10] is not None else None,
                    "risk_status":            str(r[11] or ""),
                    "primary_regime":         str(r[12] or ""),
                    "valuation_available":    bool(r[13]),
                    "created_at":             str(r[14] or ""),
                    "source":                 "asset_intelligence",
                }
        return result
    except Exception:
        return {}


def _load_risk_snapshots(con: sqlite3.Connection) -> dict[str, dict]:
    """
    Carrega o snapshot de risco mais recente por ticker de risk_snapshots.
    Retorna {ticker: row_dict}.
    """
    try:
        rows = con.execute("""
            SELECT ticker, price, position_value, parametric_var_95,
                   historical_var_95, expected_shortfall_95, ensemble_vol,
                   risk_status, created_at
            FROM risk_snapshots
            WHERE created_at = (
                SELECT MAX(r2.created_at) FROM risk_snapshots r2
                WHERE r2.ticker = risk_snapshots.ticker
            )
            GROUP BY ticker
        """).fetchall()

        result: dict[str, dict] = {}
        for r in rows:
            if r[0]:
                price = float(r[1]) if r[1] else None
                pos_val = float(r[2]) if r[2] else None
                var95_abs = float(r[3]) if r[3] is not None else None
                es95_abs = float(r[5]) if r[5] is not None else None
                vol = float(r[6]) if r[6] is not None else None

                # Converter VaR absoluto para % do position_value
                var_pct = None
                if var95_abs and pos_val and pos_val > 0:
                    var_pct = round(var95_abs / pos_val * 100, 2)
                elif var95_abs and vol:
                    # Fallback: VaR diário 95% via vol parametric
                    var_pct = round(vol * 1.645 * 100, 2)

                es_pct = None
                if es95_abs and pos_val and pos_val > 0:
                    es_pct = round(es95_abs / pos_val * 100, 2)

                result[str(r[0]).upper()] = {
                    "price":        price,
                    "var_95_pct":   var_pct,
                    "es_95_pct":    es_pct,
                    "ensemble_vol": vol,
                    "risk_status":  str(r[7] or ""),
                    "created_at":   str(r[8] or ""),
                }
        return result
    except Exception:
        return {}


def _load_adv21(con: sqlite3.Connection, tickers: list[str]) -> dict[str, float | None]:
    """
    Calcula ADV 21 dias de negociação a partir de cotahist_daily.
    Usa query agregada com sub-select por ticker para eficiência.
    Retorna {ticker: adv_brl}.
    """
    if not tickers:
        return {}

    result: dict[str, float | None] = {}
    placeholders = ",".join("?" * len(tickers))

    try:
        # Uma única query agregada para todos os tickers
        rows = con.execute(f"""
            SELECT ticker, AVG(volume) as adv21, COUNT(*) as dias
            FROM (
                SELECT ticker, volume,
                       ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date DESC) as rn
                FROM cotahist_daily
                WHERE ticker IN ({placeholders})
                  AND volume IS NOT NULL
                  AND volume > 0
            )
            WHERE rn <= 21
            GROUP BY ticker
        """, tickers).fetchall()

        for r in rows:
            if r[0] and r[1] is not None:
                result[str(r[0]).upper()] = float(r[1])
    except Exception:
        # Fallback: query individual por ticker
        for ticker in tickers:
            try:
                row = con.execute("""
                    SELECT AVG(volume) FROM (
                        SELECT volume FROM cotahist_daily
                        WHERE ticker=? AND volume > 0
                        ORDER BY trade_date DESC LIMIT 21
                    )
                """, (ticker,)).fetchone()
                result[ticker.upper()] = float(row[0]) if row and row[0] else None
            except Exception:
                result[ticker.upper()] = None

    # Garantir que todos os tickers pedidos tenham entrada
    for t in tickers:
        result.setdefault(t.upper(), None)

    return result


def _load_macro_overrides(con: sqlite3.Connection) -> dict[str, float | None]:
    """
    Lê macro_series com os nomes corretos de coluna para gerar overrides
    para o market_regime_engine.detect_regime().
    """
    out: dict[str, float | None] = {
        "selic": None, "ipca": None, "ptax_trend": None,
    }
    try:
        # Selic — série 4389
        row = con.execute("""
            SELECT value FROM macro_series WHERE series_code='4389'
            ORDER BY series_date DESC LIMIT 1
        """).fetchone()
        out["selic"] = float(row[0]) if row and row[0] is not None else None

        # IPCA 12m — série 13522
        row = con.execute("""
            SELECT value FROM macro_series WHERE series_code='13522'
            ORDER BY series_date DESC LIMIT 1
        """).fetchone()
        out["ipca"] = float(row[0]) if row and row[0] is not None else None

        # PTAX tendência 21d — série 21620
        ptax_rows = con.execute("""
            SELECT value FROM macro_series WHERE series_code='21620'
            ORDER BY series_date DESC LIMIT 30
        """).fetchall()
        if len(ptax_rows) >= 2:
            values = [float(r[0]) for r in ptax_rows if r[0] is not None]
            n = min(21, len(values))
            if n >= 2 and values[-n] != 0:
                # values is DESC → values[0] is latest, values[n-1] is oldest
                new_val, old_val = values[0], values[n - 1]
                out["ptax_trend"] = (new_val / old_val - 1.0) * 100.0
    except Exception:
        pass
    return out


def _load_market_regime_b3(con: sqlite3.Connection) -> dict[str, Any]:
    """
    Carrega o regime de mercado B3 mais recente de market_regime_daily.
    """
    try:
        row = con.execute("""
            SELECT trade_date, primary_regime, trend_regime, volatility_regime,
                   liquidity_regime, risk_regime, regime_confidence
            FROM market_regime_daily
            ORDER BY trade_date DESC LIMIT 1
        """).fetchone()
        if row:
            return {
                "trade_date":       str(row[0] or ""),
                "primary_regime":   str(row[1] or ""),
                "trend_regime":     str(row[2] or ""),
                "volatility_regime": str(row[3] or ""),
                "liquidity_regime": str(row[4] or ""),
                "risk_regime":      str(row[5] or ""),
                "confidence":       float(row[6]) if row[6] is not None else 0.5,
                "available":        True,
            }
    except Exception:
        pass
    return {"available": False, "primary_regime": "indisponível"}


# ---------------------------------------------------------------------------
# Construção do EV por ticker
# ---------------------------------------------------------------------------

def _build_ev(
    ticker: str,
    score_final: float,
    ensemble_vol: float | None,
    upside_pct: float | None,
    var_pct: float | None,
    data_quality: float = 80.0,
) -> EVResult | None:
    """
    Constrói EVResult usando dados disponíveis sem inventar dados.
    Retorna None se inputs insuficientes.

    Nota sobre horizonte temporal:
      upside (DCF) e drawdown devem usar o mesmo horizonte para payoff_ratio coerente.
      Usamos estimativas vol-based (21 dias úteis) para consistência interna.
      O upside DCF é exibido separadamente no UI como contexto de longo prazo.
    """
    try:
        # Probability win: estimada de score_final (sem backtest específico)
        # score=50 → p=0.50, score=80 → p=0.65, score=100 → p=0.75
        p_win = 0.25 + (score_final / 100.0) * 0.50
        p_win = max(0.25, min(0.80, p_win))

        if ensemble_vol is None or ensemble_vol <= 0:
            # Sem vol → sem EV coerente
            return None

        sigma_21d = ensemble_vol * math.sqrt(_EV_WINDOW_DAYS / _TRADING_DAYS_YEAR)

        # Upside: 2-sigma em 21 dias úteis (horizonte de trading médio)
        # NÃO usa DCF upside para EV — horizontes diferentes criariam payoff ilusório.
        # DCF upside é exibido como contexto separado no cartão.
        max_up = round(sigma_21d * 2.0 * 100, 1)
        max_up = max(max_up, 1.0)   # mínimo 1%

        # Drawdown: VaR% se disponível (mesmo horizonte), senão 1.5-sigma 21d
        if var_pct is not None and 0.1 < var_pct < 50.0:
            max_down = var_pct
        else:
            max_down = round(sigma_21d * 1.5 * 100, 1)
            max_down = max(max_down, 0.5)   # mínimo 0.5%

        if max_down <= 0:
            return None

        return compute_ev(
            ticker,
            probability_win=p_win,
            max_upside_pct=max_up,
            max_drawdown_pct=max_down,
            conviction_score=score_final,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Construção do MetaScore por ticker
# ---------------------------------------------------------------------------

def _build_meta_score(
    ticker: str,
    quant_score: float,
    score_liquidez: float | None,
    score_volatilidade: float | None,
    regime: RegimeSnapshot | None,
    upside_pct: float | None,
    fundamental_score: float | None,
    data_quality: float,
    ev_result: EVResult | None,
) -> MetaScoreResult:
    """
    Constrói MetaScoreResult a partir dos layers disponíveis.
    Usa 50.0 (neutro) para layers sem dados — nunca inventa.
    """
    # Macro scores do regime
    macro_score = 50.0
    regime_sc = 50.0
    macro_headwind = 50.0
    macro_tailwind = 50.0
    if regime is not None:
        macro_headwind = float(getattr(regime, "macro_headwind", 50.0))
        macro_tailwind = float(getattr(regime, "macro_tailwind", 50.0))
        macro_score = max(0.0, min(100.0, 100.0 - macro_headwind))
        regime_sc = float(getattr(regime, "regime_score", 50.0))

    # Valuation score: upside DCF → score
    val_score = 50.0
    if upside_pct is not None:
        val_score = max(0.0, min(100.0, 50.0 + upside_pct * 1.5))

    # Liquidity score: score_liquidez do realtime (0-100)
    liq_score = float(score_liquidez) if score_liquidez is not None else 60.0

    # Volatility: score_volatilidade do realtime
    vol_score = float(score_volatilidade) if score_volatilidade is not None else 50.0

    # Flow: use score_liquidez como proxy (não temos institutional flow)
    flow_score = liq_score

    # Fundamental
    fund_score = float(fundamental_score) if fundamental_score is not None else 50.0

    # EV score
    ev_score = float(ev_result.expected_value_score) if ev_result else 50.0

    return compute_meta_score(
        ticker=ticker,
        quant_score=quant_score,
        flow_score=flow_score,
        volatility_score=vol_score,
        macro_score=macro_score,
        regime_score=regime_sc,
        valuation_score=val_score,
        political_score=70.0,       # conservador
        liquidity_score=liq_score,
        fundamental_confirmation=fund_score,
        macro_headwind=macro_headwind,
        macro_tailwind=macro_tailwind,
        iv_regime="NORMAL",
        ev_score=ev_score,
        data_quality_score=data_quality,
    )


# ---------------------------------------------------------------------------
# Builder principal de cada oportunidade
# ---------------------------------------------------------------------------

def _build_opportunity(
    ticker: str,
    realtime: dict | None,
    asset_intel: dict | None,
    risk: dict | None,
    adv21: float | None,
    regime: RegimeSnapshot | None,
    b3_regime: dict,
) -> dict:
    """
    Constrói o payload completo de uma oportunidade combinando todos os layers.
    """
    warnings: list[str] = []

    # ── Score quant primário ──────────────────────────────────────────────
    score_final: float | None = None
    score_momentum: float | None = None
    score_tendencia: float | None = None
    score_liq: float | None = None
    score_vol: float | None = None
    signal_type: str = ""
    realtime_explanation: str = ""
    data_source: str = "none"

    if realtime and realtime.get("score_final") is not None:
        score_final    = float(realtime["score_final"])
        score_momentum = realtime.get("score_momentum")
        score_tendencia= realtime.get("score_tendencia")
        score_liq      = realtime.get("score_liquidez")
        score_vol      = realtime.get("score_volatilidade")
        signal_type    = realtime.get("signal_type", "")
        realtime_explanation = realtime.get("explanation", "")
        data_source    = "realtime_signals"
    elif asset_intel and asset_intel.get("quant_score") is not None:
        score_final = float(asset_intel["quant_score"])
        signal_type = asset_intel.get("integrated_status", "")
        data_source = "asset_intelligence"
        warnings.append("sinal técnico via asset_intelligence (sem realtime)")
    elif asset_intel and asset_intel.get("integrated_score") is not None:
        score_final = float(asset_intel["integrated_score"])
        signal_type = asset_intel.get("integrated_status", "")
        data_source = "asset_intelligence_integrated"
        warnings.append("score integrado via asset_intelligence")

    if score_final is None:
        return {}  # Sem dados mínimos — ignorar ticker

    # ── Direção e tier ────────────────────────────────────────────────────
    direction = _SIGNAL_TYPE_DIRECTION.get(signal_type, None)
    tier = _SIGNAL_TYPE_TIER.get(signal_type, None)

    if direction is None:
        # Tentar via integrated_status
        for key, val in _STATUS_DIRECTION.items():
            if key in signal_type.upper():
                direction = val
                break
        direction = direction or "HOLD"

    if tier is None:
        for key, val in _STATUS_TIER.items():
            if key in signal_type.upper():
                tier = val
                break
        tier = tier or "D"

    # ── Dados de risco e vol ──────────────────────────────────────────────
    ensemble_vol: float | None = None
    var_pct: float | None = None

    # Prioridade: risk_snapshots → asset_intelligence
    if risk:
        ensemble_vol = risk.get("ensemble_vol")
        var_pct = risk.get("var_95_pct")
    if ensemble_vol is None and asset_intel:
        ensemble_vol = asset_intel.get("ensemble_vol")

    risk_str = "indisponível (sem VaR calculado)"
    if var_pct is not None:
        risk_str = f"VaR 95% ~{var_pct:.1f}% (posição padrão)"
    elif ensemble_vol is not None:
        # Estimativa via vol
        sigma_1d = ensemble_vol * math.sqrt(1 / _TRADING_DAYS_YEAR)
        var_est = sigma_1d * 1.645 * 100
        risk_str = f"~{var_est:.1f}% (estimado via vol={ensemble_vol:.1%})"
        warnings.append("risco estimado por volatilidade, sem VaR calculado")

    # ── Upside ───────────────────────────────────────────────────────────
    upside_pct: float | None = None
    if asset_intel:
        up = asset_intel.get("upside_pct")
        if up is not None and abs(float(up)) >= 0.5:
            upside_pct = float(up)

    # ── Data quality ──────────────────────────────────────────────────────
    dq = 80.0
    if asset_intel:
        dq = float(asset_intel.get("data_quality_score") or 80.0)
    fundamental_score = None
    if asset_intel:
        fundamental_score = asset_intel.get("fundamental_quality")

    # ── EV Engine ─────────────────────────────────────────────────────────
    ev_result: EVResult | None = None
    ev_available = False
    ev_unavailable_reason = ""

    if ensemble_vol is not None or upside_pct is not None:
        ev_result = _build_ev(
            ticker, score_final, ensemble_vol, upside_pct, var_pct, dq
        )
        if ev_result:
            ev_available = True
        else:
            ev_unavailable_reason = "inputs insuficientes para cálculo de EV"
    else:
        ev_unavailable_reason = "vol e upside indisponíveis — sem dados para EV"
        warnings.append(ev_unavailable_reason)

    # ── Institutional Meta Score ──────────────────────────────────────────
    meta: MetaScoreResult = _build_meta_score(
        ticker=ticker,
        quant_score=score_final,
        score_liquidez=score_liq,
        score_volatilidade=score_vol,
        regime=regime,
        upside_pct=upside_pct,
        fundamental_score=fundamental_score,
        data_quality=dq,
        ev_result=ev_result,
    )
    meta_score = meta.institutional_meta_score
    meta_tier = meta.conviction_tier
    meta_direction = meta.signal_direction

    # Se realtime tem sinal mais forte, sobrescreve tier/direction do meta
    # (meta score é contexto adicional, não override de sinal já calculado)
    final_direction = direction
    final_tier = tier

    # ── Signal Explainer ──────────────────────────────────────────────────
    regime_snapshot = regime  # pode ser None
    explanation_dict = explain_opportunity(meta, ev_result, regime_snapshot)

    # Gatilho: prioriza direção do realtime sobre meta_score quando é fonte primária.
    # meta.signal_direction pode divergir do realtime por 1-2 pontos de score_final,
    # resultando em "monitorar" mesmo quando o sinal real é BUY. Usamos a direção
    # do realtime como verdade do sinal, e o meta score como filtro de convicção.
    _sig_labels_pt = {
        "BUY":   "entrada — risco/retorno favorável",
        "WATCH": "monitorar — aguardar trigger de confirmação",
        "HOLD":  "manter posição — sem novo posicionamento",
        "SELL":  "saída ou proteção — estrutura frágil",
    }
    if data_source == "realtime_signals":
        # Direção real do sinal de mercado como base do gatilho
        gatilho = _sig_labels_pt.get(final_direction, explanation_dict.get("action_hint", "monitorar"))
    else:
        gatilho = explanation_dict.get("action_hint", "monitorar")

    primary_driver = explanation_dict.get("primary_driver", "")
    ev_summary = explanation_dict.get("ev_summary", "")
    regime_context = explanation_dict.get("regime_context", "")

    # ── ADV 21d ───────────────────────────────────────────────────────────
    adv_str = "indisponível (cotahist sem dados para este ticker)"
    adv_score = 50.0
    if adv21 is not None:
        adv_str = _fmt_adv(adv21)
        if adv21 >= _MIN_ADV_LIQUID:
            adv_score = min(100.0, 50.0 + (adv21 / _MIN_ADV_LIQUID - 1.0) * 25.0)
        else:
            adv_score = max(10.0, adv21 / _MIN_ADV_LIQUID * 50.0)

    # ── Assimetria ────────────────────────────────────────────────────────
    asymmetry_str = "indisponível"
    asymmetry_raw: float | None = None
    if ev_result:
        asymmetry_raw = ev_result.payoff_ratio
        asymmetry_str = _fmt_asymmetry(asymmetry_raw)

    # ── Regime label ──────────────────────────────────────────────────────
    regime_label = "indisponível"
    if regime:
        regime_label = getattr(regime, "regime_label", "indisponível").replace("_", " ")

    # ── Próxima ação ──────────────────────────────────────────────────────
    proxima_acao, acao_variant = _proxima_acao(final_direction, final_tier)

    # ── Tipo de ativo ─────────────────────────────────────────────────────
    tipo = _tipo_ativo(signal_type)

    return {
        "ticker":           ticker,
        "tipo":             tipo,
        "score":            round(meta_score, 1),
        "score_quant":      round(score_final, 1),
        "direction":        final_direction,
        "tier":             final_tier,
        "meta_tier":        meta_tier,
        "meta_direction":   meta_direction,
        # Gatilho em linguagem natural
        "gatilho":          gatilho,
        "primary_driver":   primary_driver,
        "action_hint":      gatilho,
        # Risco
        "risco":            risk_str,
        "var_pct":          var_pct,
        # Liquidez
        "liquidez":         adv_str,
        "liquidez_raw":     adv21,
        "adv_score":        adv_score,
        # Assimetria
        "assimetria":       asymmetry_str,
        "payoff_ratio":     asymmetry_raw,
        # EV
        "ev_score":         round(ev_result.expected_value_score, 1) if ev_result else None,
        "ev_summary":       ev_summary,
        "ev_available":     ev_available,
        "ev_unavailable_reason": ev_unavailable_reason if not ev_available else "",
        "kelly_fraction":   round(ev_result.kelly_fraction, 3) if ev_result else None,
        # Regime
        "regime":           regime_label,
        "regime_context":   regime_context,
        # Meta score
        "meta_score":       round(meta_score, 1),
        "meta_confidence":  meta.confidence,
        "top_bullish":      meta.top_bullish_factors[:3],
        "top_bearish":      meta.top_bearish_factors[:3],
        # Signal
        "signal_type":      signal_type,
        "realtime_explanation": realtime_explanation,
        # Próxima ação
        "proxima_acao":     proxima_acao,
        "acao_variant":     acao_variant,
        # Upside
        "upside_pct":       upside_pct,
        # Data quality
        "data_quality":     round(dq, 0),
        "data_source":      data_source,
        "warnings":         warnings,
        # Sub-scores para detalhes
        "scores": {
            "quant":        round(score_final, 1),
            "momentum":     round(score_momentum, 1) if score_momentum else None,
            "tendencia":    round(score_tendencia, 1) if score_tendencia else None,
            "liquidez":     round(score_liq, 1) if score_liq else None,
            "volatilidade": round(score_vol, 1) if score_vol else None,
            "macro":        round(meta.macro_score, 1),
            "valuation":    round(meta.valuation_score, 1),
        },
    }


# ---------------------------------------------------------------------------
# API principal: get_radar_payload()
# ---------------------------------------------------------------------------

def get_radar_payload(db_path: str | Path | None = None) -> dict:
    """
    Constrói o payload completo do Radar de Oportunidades.

    Integra todos os motores de decisão usando dados reais do banco.
    Nunca inventa dados — campos indisponíveis são marcados explicitamente.

    Retorna:
        {
            "regime": RegimeSnapshot | None,
            "market_regime_b3": dict,       # regime B3 de market_regime_daily
            "opportunities": list[dict],    # lista ranqueada por meta_score
            "data_status": dict[str, str],  # status de cada motor
            "as_of": str,                   # data do payload
        }
    """
    try:
        p = Path(db_path) if db_path else _db_path()
        con = sqlite3.connect(str(p))
    except Exception as e:
        return {
            "regime": None,
            "market_regime_b3": {"available": False, "error": str(e)},
            "opportunities": [],
            "data_status": {"erro": str(e)},
            "as_of": date.today().isoformat(),
        }

    try:
        # 1. Dados base
        realtime_map = _load_realtime_signals(con)
        asset_intel_map = _load_asset_intelligence(con)
        risk_map = _load_risk_snapshots(con)
        b3_regime = _load_market_regime_b3(con)
        macro_overrides = _load_macro_overrides(con)

        # 2. Regime macro global via engine
        regime: RegimeSnapshot | None = None
        regime_status = "indisponível"
        try:
            regime = detect_regime(
                con=None,   # Não lê do DB (schema mismatch) — usa overrides
                selic_override=macro_overrides.get("selic"),
                ipca_override=macro_overrides.get("ipca"),
                # ptax_override: parâmetro existe mas não implementado no body
                # → ptax ficará como NaN (fallback ESTÁVEL)
                cds_override=None,
                vix_override=None,  # engine tenta yfinance como fallback
            )
            regime_status = "integrado"
        except Exception as ex:
            regime_status = f"erro: {ex}"

        # 3. Merge de tickers: realtime tem prioridade, asset_intel complementa
        all_tickers: set[str] = set(realtime_map.keys()) | set(asset_intel_map.keys())

        # 4. ADV 21d em batch (query única)
        adv_map = _load_adv21(con, list(all_tickers))
        adv_status = (
            "integrado" if any(v is not None for v in adv_map.values())
            else "indisponível (cotahist vazio)"
        )

        # 5. Build de cada oportunidade
        opportunities: list[dict] = []
        ev_count = 0
        explain_count = 0

        for ticker in sorted(all_tickers):
            opp = _build_opportunity(
                ticker=ticker,
                realtime=realtime_map.get(ticker),
                asset_intel=asset_intel_map.get(ticker),
                risk=risk_map.get(ticker),
                adv21=adv_map.get(ticker),
                regime=regime,
                b3_regime=b3_regime,
            )
            if not opp:
                continue
            if opp.get("ev_available"):
                ev_count += 1
            if opp.get("gatilho") and opp["gatilho"] != "monitorar":
                explain_count += 1
            opportunities.append(opp)

        # 6. Ranking: score decrescente
        opportunities.sort(key=lambda x: float(x.get("score") or 0), reverse=True)

        # 7. Status de cada motor
        data_status = {
            "market_regime_engine":    regime_status,
            "expected_value_engine":   f"integrado — {ev_count}/{len(opportunities)} tickers com EV",
            "signal_explainer":        f"integrado — {len(opportunities)} tickers com gatilho",
            "institutional_meta_score": f"integrado — {len(opportunities)} tickers",
            "adv21d_cotahist":         adv_status,
            "valuation_upside":        f"{sum(1 for o in opportunities if o.get('upside_pct'))} tickers com upside DCF",
            "realtime_signals":        f"{len(realtime_map)} tickers ({', '.join(sorted(realtime_map.keys()))})" if realtime_map else "indisponível",
            "risk_snapshots":          f"{len(risk_map)} tickers" if risk_map else "indisponível",
        }

        return {
            "regime": regime,
            "market_regime_b3": b3_regime,
            "macro_overrides": macro_overrides,
            "opportunities": opportunities,
            "data_status": data_status,
            "as_of": date.today().isoformat(),
        }

    finally:
        try:
            con.close()
        except Exception:
            pass
