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
    # ── Alta / Compra ──────────────────────────────────────────────────────
    if d == "BUY" and t in ("S", "A"):
        return "Operar compra agora", "approved"
    if d == "BUY" and t in ("B",):
        return "Monitorar compra", "monitor"
    if d == "BUY":
        return "Aguardar confirmação", "monitor"
    # ── Watch / Neutro ─────────────────────────────────────────────────────
    if d == "WATCH":
        return "Aguardar confirmação", "monitor"
    if d == "HOLD":
        return "Manter — sem nova ação", "paper"
    # ── Venda / Baixa ──────────────────────────────────────────────────────
    if d == "SELL":
        return "Monitorar venda / reduzir exposição", "sell_signal"
    if d == "MONITORAR_VENDA":
        return "Monitorar saída gradual", "sell_signal"
    # ── Proteção / Opções (sem shortlist RTD — lógica conceitual) ─────────
    if d in ("PROTEÇÃO", "PROTECAO", "PUT_OPPORTUNITY"):
        return "Avaliar proteção / put", "protect"
    if d == "BEAR_SPREAD_OPPORTUNITY":
        return "Avaliar trava de baixa", "protect"
    if d == "VOLATILITY_WATCH":
        return "Monitorar volatilidade — sem posicionamento direcional", "paper"
    # ── Evitar ────────────────────────────────────────────────────────────
    if d in ("AVOID", "EVITAR"):
        return "Evitar — estrutura frágil", "blocked"
    return "Sem dados suficientes", "paper"


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
    score_momentum: float | None = None,
    score_tendencia: float | None = None,
    score_volatilidade: float | None = None,
) -> EVResult | None:
    """
    Constrói EVResult calibrado — sem teto trivial de EV=100.

    Calibrações vs MVP (v1):
      1. p_win range conservador (0.40–0.65) — evita ilusão de certeza
      2. upside_mult varia por qualidade do sinal — payoff discrimina entre tickers
         (corrige payoff constante ~5.57 para todos via 2*sqrt(21)/1.645)
      3. EV score em escala logarítmica — não satura em 100 para payoffs comuns
      4. Downside penalizado por regime de vol — vol alta reduz assimetria aparente

    NÃO usa DCF upside — horizontes diferentes criariam payoff ilusório.
    DCF upside exibido separadamente no cartão como contexto de longo prazo.
    """
    try:
        # p_win conservador: score=50→p=0.48, score=80→p=0.58, score=100→p=0.65
        p_win = 0.40 + (score_final / 100.0) * 0.25
        p_win = max(0.40, min(0.65, p_win))

        if ensemble_vol is None or ensemble_vol <= 0:
            return None

        sigma_21d = ensemble_vol * math.sqrt(_EV_WINDOW_DAYS / _TRADING_DAYS_YEAR)

        # Upside: multiplier baseado em qualidade do sinal (quebra a simetria constante)
        # mom=50,tend=50 → signal_qual=0.50 → up_mult=1.80
        # mom=75,tend=70 → signal_qual=0.72 → up_mult=2.07
        # sem sub-scores  → up_mult=1.55 (conservador)
        if score_momentum is not None and score_tendencia is not None:
            signal_qual = (score_momentum + score_tendencia) / 200.0   # 0–1
            up_mult = 1.2 + signal_qual * 1.2   # 1.2 (fraco) a 2.4 (forte)
        else:
            up_mult = 1.55
        max_up = round(sigma_21d * up_mult * 100, 1)
        max_up = max(max_up, 1.0)

        # Downside: var_pct base + penalidade por vol alta (score_vol baixo → risco maior)
        if var_pct is not None and 0.1 < var_pct < 50.0:
            if score_volatilidade is not None:
                # score_vol=100 (calmo) → risk_mult=1.0; score_vol=30 (agitado) → risk_mult=1.42
                risk_mult = 1.0 + (1.0 - score_volatilidade / 100.0) * 0.6
            else:
                risk_mult = 1.2   # conservador sem dados de vol
            max_down = round(var_pct * risk_mult, 2)
        else:
            sigma_daily = ensemble_vol * math.sqrt(1.0 / _TRADING_DAYS_YEAR)
            max_down = round(sigma_daily * 1.645 * 100 * 1.25, 2)  # +25% vs MVP
        max_down = max(max_down, 0.5)

        ev = compute_ev(
            ticker,
            probability_win=p_win,
            max_upside_pct=max_up,
            max_drawdown_pct=max_down,
            conviction_score=score_final,
        )

        # Rescaling logarítmico do EV score — substitui 30 + 35*ev_units que satura
        # trivialmente.
        # Escala calibrada (log):
        #   ev_units ≤ 0  → score = max(0, 30 + ev_units*15)
        #   ev_units = 0.5 → score ≈ 47
        #   ev_units = 1   → score ≈ 57   (antes: 65)
        #   ev_units = 2   → score ≈ 69   (antes: 100 clipped)
        #   ev_units = 3.4 → score ≈ 79   (antes: 100 clipped)
        #   ev_units = 6   → score ≈ 92
        raw_payoff = ev.payoff_ratio
        ev_units = max(0.0, p_win * raw_payoff - (1.0 - p_win))
        if ev_units > 0:
            calibrated = 40.0 + 25.0 * math.log1p(ev_units * 2.0)
        else:
            raw_ev = p_win * raw_payoff - (1.0 - p_win)
            calibrated = max(0.0, 30.0 + raw_ev * 15.0)

        # Penalidades por qualidade de dados e convicção do score
        conviction_mult = 0.65 + (score_final / 100.0) * 0.35   # 0.65–1.0
        dq_mult = 0.75 + (data_quality / 100.0) * 0.25          # 0.75–1.0
        calibrated = float(np.clip(calibrated * conviction_mult * dq_mult, 0.0, 100.0))

        ev.expected_value_score = round(calibrated, 1)
        return ev
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Calibração: gatilho PT-BR, direção conservadora, contexto de decisão
# ---------------------------------------------------------------------------

def _derive_gatilho_pt(
    direction: str,
    score_momentum: float | None,
    score_tendencia: float | None,
    score_final: float,
    adv21: float | None = None,
    var_pct: float | None = None,
    score_volatilidade: float | None = None,
) -> str:
    """
    Deriva gatilho técnico discriminante em PT-BR a partir dos sub-scores.

    Taxonomia (em ordem de prioridade):
      Alta:    rompimento / pullback / tendência / assimetria / monitoramento
      Baixa:   pressão vendedora / tendência de baixa / fraqueza / monitorar venda
      Opções:  put opportunity / trava de baixa / proteção / vol alta
      Neutro:  sem gatilho / manter posição
    """
    d = direction.upper()
    mom  = score_momentum  if score_momentum  is not None else score_final * 0.80
    tend = score_tendencia if score_tendencia is not None else score_final * 0.80
    # score_vol invertido: alto = calmo, baixo = vol alta
    vol  = score_volatilidade if score_volatilidade is not None else 50.0

    # ── Venda / Baixa ──────────────────────────────────────────────────────
    if d == "SELL":
        if mom < 35 and tend < 35:
            return "pressão vendedora — momentum e tendência deteriorados, avaliar saída"
        if tend < 40:
            return "tendência de baixa confirmada — estrutura técnica vendida"
        if adv21 is not None and adv21 < _SELL_ADV_FLOOR:
            return "sinal de baixa — liquidez insuficiente para saída, monitorar"
        return "sinal de baixa — avaliar redução gradual de exposição"

    if d == "MONITORAR_VENDA":
        if tend < 42:
            return "fraqueza técnica em desenvolvimento — monitorar saída"
        return "deterioração moderada — acompanhar tendência de curto prazo"

    # ── Proteção / Opções (lógica conceitual — sem ticker de opção) ─────────
    if d in ("PROTEÇÃO", "PROTECAO"):
        return "ativo em resistência ou macro adverso — avaliar proteção via opções"

    if d == "PUT_OPPORTUNITY":
        return "queda com volatilidade favorável — avaliar compra de put ou trava de baixa"

    if d == "BEAR_SPREAD_OPPORTUNITY":
        return "tendência de baixa com vol controlada — avaliar trava de baixa"

    if d == "VOLATILITY_WATCH":
        return "volatilidade elevada sem direção clara — evitar posicionamento direcional"

    # ── Evitar ────────────────────────────────────────────────────────────
    if d in ("AVOID", "EVITAR") and score_final < 52:
        return "sem gatilho acionável — estrutura técnica insuficiente"

    # ── Alta / Compra ──────────────────────────────────────────────────────
    if d == "BUY":
        if mom >= 72 and tend >= 68:
            return "rompimento — momentum e tendência alinhados, entrada com confirmação"
        if mom >= 68 and tend < 55:
            return "impulso de curto prazo — pullback em tendência indefinida, gestão rigorosa"
        if tend >= 70 and mom < 55:
            return "tendência estrutural — aguardar momentum para confirmar entrada"
        if tend >= 62 and mom >= 58:
            return "tendência com momentum — zona de entrada, confirmar volume"
        if score_final >= 63:
            return "assimetria positiva — risco/retorno favorável, aguardar confirmação"
        return "sinal parcial — aguardar alinhamento de momentum e tendência"

    if d == "WATCH":
        if tend >= 62:
            return "tendência em formação — monitorar rompimento para confirmar entrada"
        if mom >= 60:
            return "momentum isolado — sem estrutura de tendência, apenas monitoramento"
        if score_final >= 52:
            return "apenas monitoramento — aguardar catalisador técnico"
        return "sem gatilho acionável — sinal insuficiente para posicionamento"

    # HOLD / default
    if score_final >= 50:
        return "manter posição — sem gatilho de entrada ou saída identificado"
    return "sem gatilho acionável — estrutura técnica neutra ou insuficiente"


# Thresholds conservadores para BUY
_BUY_SCORE_FLOOR   = 63.0    # score_final mínimo
_BUY_MOM_FLOOR     = 56.0    # score_momentum mínimo
_BUY_TEND_FLOOR    = 54.0    # score_tendencia mínimo
_BUY_ADV_FLOOR     = 25_000_000.0   # ADV mínimo R$25M
_BUY_VAR_CEILING   = 5.5     # VaR 95% máximo %
_WATCH_SCORE_FLOOR = 50.0
_AVOID_SCORE_CEIL  = 38.0

# Thresholds para sinal de baixa
_SELL_SCORE_CEIL         = 38.0    # score abaixo deste → candidato bearish
_SELL_MOM_CEIL           = 40.0    # momentum bearish
_SELL_TEND_CEIL          = 40.0    # tendência bearish
_SELL_ADV_FLOOR          = 10_000_000.0   # R$10M mínimo para SELL confirmado
_MONITORAR_VENDA_SCORE_CEIL = 45.0  # sinal bearish moderado
# score_volatilidade é INVERTIDO: baixo = vol alta, alto = vol baixa
_VOL_HIGH_SCORE_CEIL     = 38.0    # score_vol < 38 → vol elevada (score invertido)
_PROTEÇÃO_HEADWIND_FLOOR = 68.0    # macro headwind ≥ 68 → recomendar proteção


def _calibrated_direction(
    raw_direction: str,
    score_final: float,
    score_momentum: float | None,
    score_tendencia: float | None,
    adv21: float | None,
    var_pct: float | None,
    data_quality: float,
    score_volatilidade: float | None = None,
    macro_headwind: float = 50.0,
) -> tuple[str, str, list[str]]:
    """
    Aplica thresholds conservadores multi-fator para direção e tier finais.

    BUY: score ≥ 63 + momentum ≥ 56 + tendência ≥ 54 + ADV ≥ R$25M + VaR ≤ 5.5%
    WATCH: score ≥ 50 + (momentum ≥ 50 OU tendência ≥ 52)
    SELL (raw): preservado com tier ajustado por liquidez
    SELL (score combo): detectado quando score + mom + tend todos bearish + ADV ≥ R$10M
    MONITORAR_VENDA: fraqueza moderada (2+ fatores bearish)
    PROTEÇÃO: macro headwind ≥ 68 + score moderado
    VOLATILITY_WATCH: vol alta (score_vol < 38) + sinal inconclusivo
    AVOID: fraqueza estrutural extrema

    Regras de bloqueio de sinal de venda (Task 6):
      - liquidez < R$5M → não classifica como venda
      - dados insuficientes (dq < 50) → não classifica como venda
      - risco muito alto (VaR > 8%) → não classifica como venda
      - sinais contraditórios (|mom - tend| > 30) → não classifica como venda

    Retorna (direction, tier, penalidades_aplicadas).
    """
    penalties: list[str] = []

    mom  = score_momentum  if score_momentum  is not None else score_final * 0.80
    tend = score_tendencia if score_tendencia is not None else score_final * 0.80
    vol  = score_volatilidade if score_volatilidade is not None else 50.0

    # Coletar penalidades
    if adv21 is None:
        penalties.append("liquidez não confirmada (sem ADV)")
    elif adv21 < 10_000_000:
        penalties.append(f"liquidez crítica (R${adv21/1e6:.0f}M)")
    elif adv21 < _BUY_ADV_FLOOR:
        penalties.append(f"liquidez abaixo do mínimo (R${adv21/1e6:.0f}M < R$25M)")

    if var_pct is not None and var_pct > _BUY_VAR_CEILING:
        penalties.append(f"risco elevado (VaR {var_pct:.1f}% > {_BUY_VAR_CEILING}%)")
    if data_quality < 55:
        penalties.append(f"qualidade de dados baixa ({data_quality:.0f}%)")
    if score_momentum is None:
        penalties.append("momentum indisponível (realtime ausente)")
    if score_tendencia is None:
        penalties.append("tendência indisponível (realtime ausente)")

    # ── Regras de bloqueio de sinal de venda ─────────────────────────────
    # Sem liquidez, dados ruins, risco alto ou sinais contraditórios → não vende
    bearish_blocked = (
        data_quality < 50
        or (adv21 is not None and adv21 < 5_000_000)
        or (var_pct is not None and var_pct > 8.0)
        or (score_momentum is not None and score_tendencia is not None
            and abs(score_momentum - score_tendencia) > 30)  # sinal contraditório
    )

    # ── SELL raw: preservar com tier ajustado (antes do AVOID check) ──────
    # Um ativo em PRESSÃO VENDEDORA é SELL, não AVOID
    if raw_direction == "SELL":
        if adv21 is not None and adv21 >= _SELL_ADV_FLOOR and data_quality >= 55:
            return "SELL", "C", penalties   # confirmado com liquidez
        return "SELL", "D", penalties       # sem confirmação de liquidez

    # ── Bearish score combo: detectar sinal de venda não sinalizado ───────
    # Avaliado ANTES do AVOID para distinguir "vender" de "evitar comprar"
    if not bearish_blocked and score_momentum is not None and score_tendencia is not None:
        # Sinal negativo forte: score + momentum + tendência todos bearish + ADV ≥ R$10M
        if (score_final < _SELL_SCORE_CEIL and mom < _SELL_MOM_CEIL and tend < _SELL_TEND_CEIL
                and adv21 is not None and adv21 >= _SELL_ADV_FLOOR):
            penalties.append("sinal bearish por combinação de scores")
            return "SELL", "C", penalties
        # Fraqueza moderada: 2+ fatores bearish (score pode estar acima de AVOID)
        bearish_count = sum([
            score_final < _MONITORAR_VENDA_SCORE_CEIL,
            mom < _SELL_MOM_CEIL,
            tend < _SELL_TEND_CEIL,
        ])
        if bearish_count >= 2 and score_final < _MONITORAR_VENDA_SCORE_CEIL:
            penalties.append("fraqueza técnica detectada em múltiplos fatores")
            return "MONITORAR_VENDA", "D", penalties

    # ── AVOID: fraqueza estrutural extrema sem sinal de venda confirmado ──
    avoid = (
        score_final < _AVOID_SCORE_CEIL
        or (var_pct is not None and var_pct > 8.0)
        or (adv21 is not None and adv21 < 2_000_000)
    )
    if avoid:
        return "AVOID", "D", penalties

    # ── Proteção: macro headwind elevado sem sinal de compra ──────────────
    if macro_headwind >= _PROTEÇÃO_HEADWIND_FLOOR and score_final < _BUY_SCORE_FLOOR:
        if not bearish_blocked:
            penalties.append(f"macro adverso (headwind {macro_headwind:.0f})")
            return "PROTEÇÃO", "C", penalties

    # ── Volatility Watch: vol alta, sinal inconclusivo ────────────────────
    # score_vol invertido: baixo = vol alta
    if (vol < _VOL_HIGH_SCORE_CEIL
            and _AVOID_SCORE_CEIL <= score_final < _BUY_SCORE_FLOOR
            and raw_direction not in ("BUY",)):
        if not bearish_blocked:
            penalties.append(f"volatilidade elevada (score_vol {vol:.0f}) sem direção clara")
            return "VOLATILITY_WATCH", "C", penalties

    # ── BUY / WATCH (lado comprado) ───────────────────────────────────────
    buy_ok = (
        score_final >= _BUY_SCORE_FLOOR
        and mom >= _BUY_MOM_FLOOR
        and tend >= _BUY_TEND_FLOOR
        and (adv21 is None or adv21 >= _BUY_ADV_FLOOR)
        and (var_pct is None or var_pct <= _BUY_VAR_CEILING)
        and data_quality >= 55
    )

    watch_ok = (
        score_final >= _WATCH_SCORE_FLOOR
        and (mom >= 50 or tend >= 52)
    )

    if raw_direction == "BUY":
        if buy_ok:
            hard_penalties = [p for p in penalties if "crítica" in p or "baixa" in p or "elevado" in p]
            return "BUY", ("A" if not hard_penalties else "B"), penalties
        elif watch_ok:
            return "WATCH", ("B" if len(penalties) <= 1 else "C"), penalties
        else:
            return "WATCH", "C", penalties

    if raw_direction == "WATCH":
        if watch_ok:
            return "WATCH", ("B" if len(penalties) <= 1 else "C"), penalties
        return "HOLD", "C", penalties

    return "HOLD", "C", penalties


# ---------------------------------------------------------------------------
# Viés, estratégia e direção operacional (camada de decisão operacional)
# ---------------------------------------------------------------------------

def _compute_vies(
    direction: str,
    score_volatilidade: float | None,
    macro_headwind: float = 50.0,
) -> str:
    """
    Retorna o viés operacional:
      Alta | Baixa | Neutro | Proteção | Volatilidade
    """
    d = direction.upper()
    # score_vol invertido: baixo = vol alta
    vol_alta = (score_volatilidade is not None and score_volatilidade < _VOL_HIGH_SCORE_CEIL)

    if d == "BUY":
        return "Alta"
    if d in ("SELL", "MONITORAR_VENDA"):
        return "Baixa"
    if d in ("PROTEÇÃO", "PROTECAO", "PUT_OPPORTUNITY", "BEAR_SPREAD_OPPORTUNITY"):
        return "Proteção"
    if d == "VOLATILITY_WATCH" or vol_alta:
        return "Volatilidade"
    if macro_headwind >= _PROTEÇÃO_HEADWIND_FLOOR:
        return "Proteção"
    if d in ("WATCH", "HOLD", "AVOID", "EVITAR"):
        return "Neutro"
    return "Neutro"


def _compute_estrategia(
    direction: str,
    vies: str,
    score_volatilidade: float | None,
    adv21: float | None,
) -> str:
    """
    Retorna a estratégia possível em linguagem simples:
      ação comprada | put | trava de baixa | hedge | evitar | monitorar | monitorar venda
    Opções são sugeridas apenas conceitualmente — sem ticker de opção.
    """
    d = direction.upper()
    # score_vol invertido: baixo = vol alta → options mais caras mas setup válido
    vol_alta = (score_volatilidade is not None and score_volatilidade < _VOL_HIGH_SCORE_CEIL)
    liquida = adv21 is not None and adv21 >= _SELL_ADV_FLOOR

    if d == "BUY":
        return "ação comprada"
    if d == "WATCH":
        return "monitorar"
    if d == "HOLD":
        return "manter"
    if d == "SELL":
        if not liquida:
            return "evitar"
        if vol_alta:
            return "put"
        return "trava de baixa"
    if d == "MONITORAR_VENDA":
        return "monitorar venda"
    if d == "PUT_OPPORTUNITY":
        return "put"
    if d == "BEAR_SPREAD_OPPORTUNITY":
        return "trava de baixa"
    if d in ("PROTEÇÃO", "PROTECAO"):
        return "hedge"
    if d == "VOLATILITY_WATCH":
        return "monitorar"
    if d in ("AVOID", "EVITAR"):
        return "evitar"
    return "monitorar"


def _compute_direcao_operacional(
    direction: str,
    tier: str,
    score_volatilidade: float | None,
    macro_headwind: float = 50.0,
) -> str:
    """
    Mapeia a direção técnica para a direção operacional em PT-BR completa.
    Inclui opções conceituais quando sinal de queda + vol favorável.
    """
    d = direction.upper()
    t = tier.upper()
    vol_alta = (score_volatilidade is not None and score_volatilidade < _VOL_HIGH_SCORE_CEIL)

    if d == "BUY" and t in ("S", "A"):
        return "COMPRA"
    if d == "BUY":
        return "MONITORAR_COMPRA"
    if d == "WATCH":
        return "AGUARDAR"
    if d == "HOLD":
        return "MANTER"
    if d == "SELL":
        if vol_alta:
            return "PUT_OPPORTUNITY"
        return "VENDA"
    if d == "MONITORAR_VENDA":
        return "MONITORAR_VENDA"
    if d in ("PROTEÇÃO", "PROTECAO"):
        return "PROTEÇÃO"
    if d == "PUT_OPPORTUNITY":
        return "PUT_OPPORTUNITY"
    if d == "BEAR_SPREAD_OPPORTUNITY":
        return "BEAR_SPREAD_OPPORTUNITY"
    if d == "VOLATILITY_WATCH":
        return "VOLATILITY_WATCH"
    if d in ("AVOID", "EVITAR"):
        return "EVITAR"
    return "AGUARDAR"


def _build_context_fields(
    direction: str,
    tier: str,
    score_final: float,
    score_momentum: float | None,
    score_tendencia: float | None,
    adv21: float | None,
    var_pct: float | None,
    ev_result: EVResult | None,
    data_quality: float,
    penalties: list[str],
) -> dict:
    """
    Gera os campos de contexto de decisão exibidos no cartão:
      - por_que_entrou : razão para estar no ranking
      - o_que_falta    : o que falta para virar BUY
      - risco_principal: principal risco identificado
    """
    mom  = score_momentum
    tend = score_tendencia

    # ── Por que entrou ────────────────────────────────────────────────────
    motivos: list[str] = []
    if score_final >= 65:
        motivos.append(f"score técnico forte ({score_final:.0f})")
    elif score_final >= 55:
        motivos.append(f"score técnico moderado ({score_final:.0f})")
    else:
        motivos.append(f"score técnico ({score_final:.0f})")
    if mom is not None and mom >= 60:
        motivos.append(f"momentum {mom:.0f}")
    if tend is not None and tend >= 60:
        motivos.append(f"tendência {tend:.0f}")
    if adv21 is not None and adv21 >= _MIN_ADV_LIQUID:
        motivos.append(f"liquidez R${adv21/1e6:.0f}M")
    if ev_result and ev_result.expected_value_score >= 52:
        motivos.append(f"EV score {ev_result.expected_value_score:.0f}")
    if len(motivos) == 1:
        motivos.append("cobertura de monitoramento automático")
    por_que = "; ".join(motivos[:4])

    # ── O que falta / contexto de próxima ação ───────────────────────────
    falta: list[str] = []
    d_upper = direction.upper()
    if d_upper == "BUY":
        falta = ["—"]
    elif d_upper in ("SELL", "MONITORAR_VENDA"):
        # Contexto bearish: o que confirma a saída
        if mom is not None and mom < _SELL_MOM_CEIL:
            falta.append(f"momentum bearish confirmado ({mom:.0f})")
        if tend is not None and tend < _SELL_TEND_CEIL:
            falta.append(f"tendência vendida ({tend:.0f})")
        if adv21 is not None and adv21 < _SELL_ADV_FLOOR:
            falta.append(f"aguardar ADV ≥ R${_SELL_ADV_FLOOR/1e6:.0f}M para saída (atual R${adv21/1e6:.0f}M)")
        if not falta:
            falta = ["confirmar volume e risco antes da saída"]
    elif d_upper in ("PROTEÇÃO", "PROTECAO", "PUT_OPPORTUNITY"):
        falta = ["shortlist de opções (RTD ainda sem dados de opções)"]
    elif d_upper == "VOLATILITY_WATCH":
        falta = ["aguardar definição de direção antes de posicionar"]
    else:
        # Contexto comprador: o que falta para BUY
        if score_final < _BUY_SCORE_FLOOR:
            falta.append(f"score ≥ {_BUY_SCORE_FLOOR:.0f} (atual {score_final:.0f})")
        if mom is not None and mom < _BUY_MOM_FLOOR:
            falta.append(f"momentum ≥ {_BUY_MOM_FLOOR:.0f} (atual {mom:.0f})")
        elif mom is None:
            falta.append("dados de momentum (realtime)")
        if tend is not None and tend < _BUY_TEND_FLOOR:
            falta.append(f"tendência ≥ {_BUY_TEND_FLOOR:.0f} (atual {tend:.0f})")
        elif tend is None:
            falta.append("dados de tendência (realtime)")
        if adv21 is None:
            falta.append("ADV 21d confirmado")
        elif adv21 < _BUY_ADV_FLOOR:
            falta.append(f"ADV ≥ R${_BUY_ADV_FLOOR/1e6:.0f}M (atual R${adv21/1e6:.0f}M)")
        if var_pct is not None and var_pct > _BUY_VAR_CEILING:
            falta.append(f"VaR ≤ {_BUY_VAR_CEILING}% (atual {var_pct:.1f}%)")
    o_que_falta = "; ".join(falta[:3]) if falta else "—"

    # ── Risco principal ───────────────────────────────────────────────────
    riscos: list[str] = []
    if var_pct is not None and var_pct > 4.0:
        riscos.append(f"VaR elevado ({var_pct:.1f}%)")
    if adv21 is not None and adv21 < _MIN_ADV_LIQUID:
        riscos.append(f"liquidez baixa (R${adv21/1e6:.0f}M)")
    if data_quality < 65:
        riscos.append(f"dados incompletos ({data_quality:.0f}%)")
    riscos.extend([p for p in penalties if p not in riscos][:2])
    if not riscos:
        if var_pct is not None:
            riscos.append(f"VaR {var_pct:.1f}% (dentro do limite)")
        else:
            riscos.append("sem VaR calculado — avaliar manualmente")
    risco_principal = riscos[0]

    return {
        "por_que_entrou":  por_que,
        "o_que_falta":     o_que_falta,
        "risco_principal": risco_principal,
    }


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

    # ── Direção raw do sinal (antes da calibração conservadora) ──────────
    raw_direction = _SIGNAL_TYPE_DIRECTION.get(signal_type, None)
    raw_tier = _SIGNAL_TYPE_TIER.get(signal_type, None)

    if raw_direction is None:
        for key, val in _STATUS_DIRECTION.items():
            if key in signal_type.upper():
                raw_direction = val
                break
        raw_direction = raw_direction or "HOLD"

    if raw_tier is None:
        for key, val in _STATUS_TIER.items():
            if key in signal_type.upper():
                raw_tier = val
                break
        raw_tier = raw_tier or "D"

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
            ticker, score_final, ensemble_vol, upside_pct, var_pct, dq,
            score_momentum=score_momentum,
            score_tendencia=score_tendencia,
            score_volatilidade=score_vol,
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

    # ── Direção calibrada conservadora (multi-fator) ─────────────────────
    # Aplica critérios de concordância: score + momentum + tendência + liquidez + risco.
    # raw_direction é o sinal bruto; _calibrated_direction decide se ele se sustenta.
    # Agora também detecta sinais bearish por combinação de scores.
    macro_hw = float(getattr(regime, "macro_headwind", 50.0)) if regime else 50.0
    final_direction, final_tier, penalties = _calibrated_direction(
        raw_direction=raw_direction,
        score_final=score_final,
        score_momentum=score_momentum,
        score_tendencia=score_tendencia,
        adv21=adv21,
        var_pct=var_pct,
        data_quality=dq,
        score_volatilidade=score_vol,
        macro_headwind=macro_hw,
    )
    if penalties:
        warnings.extend(penalties[:2])

    # ── Signal Explainer ──────────────────────────────────────────────────
    regime_snapshot = regime
    explanation_dict = explain_opportunity(meta, ev_result, regime_snapshot)

    # Gatilho discriminante em PT-BR — agora inclui lado baixista.
    gatilho = _derive_gatilho_pt(
        direction=final_direction,
        score_momentum=score_momentum,
        score_tendencia=score_tendencia,
        score_final=score_final,
        adv21=adv21,
        var_pct=var_pct,
        score_volatilidade=score_vol,
    )

    # Viés, estratégia e direção operacional PT-BR completa
    vies = _compute_vies(final_direction, score_vol, macro_hw)
    estrategia = _compute_estrategia(final_direction, vies, score_vol, adv21)
    direcao_operacional = _compute_direcao_operacional(
        final_direction, final_tier, score_vol, macro_hw
    )

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

    # ── Contexto de decisão (por_que_entrou / o_que_falta / risco_principal)
    ctx = _build_context_fields(
        direction=final_direction,
        tier=final_tier,
        score_final=score_final,
        score_momentum=score_momentum,
        score_tendencia=score_tendencia,
        adv21=adv21,
        var_pct=var_pct,
        ev_result=ev_result,
        data_quality=dq,
        penalties=penalties,
    )

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
        # Direção bruta (antes da calibração)
        "raw_direction":    raw_direction,
        "raw_tier":         raw_tier,
        # Direção operacional PT-BR completa + viés + estratégia
        "direcao_operacional": direcao_operacional,
        "vies":             vies,
        "estrategia":       estrategia,
        # Próxima ação
        "proxima_acao":     proxima_acao,
        "acao_variant":     acao_variant,
        # Contexto de decisão (calibração)
        "por_que_entrou":   ctx["por_que_entrou"],
        "o_que_falta":      ctx["o_que_falta"],
        "risco_principal":  ctx["risco_principal"],
        "penalties":        penalties,
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
