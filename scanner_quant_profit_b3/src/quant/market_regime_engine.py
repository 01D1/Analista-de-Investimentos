"""
Market Regime Engine — Detecção de regime macro para o Brasil.

Classifica o ambiente macro-financeiro em regimes compostos usando:
  - Selic / DI curve     → política monetária
  - IPCA 12m             → pressão inflacionária
  - PTAX                 → câmbio
  - CDS Brasil           → risco soberano
  - VIX proxy (^VIX)    → apetite global a risco
  - S&P 500 trend       → sentimento global
  - Commodities (BCOM)  → ciclo de commodities

Saídas por regime:
  RegimeSnapshot.regime_label     → ex. "APERTO_MONETÁRIO"
  RegimeSnapshot.regime_score     → 0–100 (intensidade do regime)
  RegimeSnapshot.macro_headwind   → 0–100 (ventos contrários)
  RegimeSnapshot.macro_tailwind   → 0–100 (ventos favoráveis)
  RegimeSnapshot.risk_appetite    → RISK_ON | NEUTRAL | RISK_OFF
  RegimeSnapshot.components       → dict com sub-scores explicados
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Estrutura de saída
# ---------------------------------------------------------------------------

@dataclass
class RegimeSnapshot:
    as_of: str                        # YYYY-MM-DD
    regime_label: str                 # regime dominante
    regime_score: float               # 0–100 intensidade
    macro_headwind: float             # 0–100 ventos contrários
    macro_tailwind: float             # 0–100 ventos favoráveis
    risk_appetite: str                # RISK_ON | NEUTRAL | RISK_OFF
    monetary_stance: str              # EXPANSIONISTA | NEUTRO | RESTRITIVO
    fx_regime: str                    # DÓLAR_FORTE | DÓLAR_FRACO | ESTÁVEL
    inflation_regime: str             # ALTA | CONTROLADA | DEFLAÇÃO
    sovereign_risk: str               # ELEVADO | MODERADO | BAIXO
    components: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "components"}
        d["components"] = self.components
        return d


# ---------------------------------------------------------------------------
# Limiares calibrados para o Brasil
# ---------------------------------------------------------------------------

_SELIC_HIGH    = 12.0   # % a.a. — regime de juros altos
_SELIC_LOW     = 7.0    # % a.a. — regime de juros baixos
_IPCA_HIGH     = 6.0    # % a.a. — inflação acima da banda superior meta
_IPCA_MODERATE = 3.5    # % a.a. — inflação na meta
_PTAX_TREND_W  = 21     # janela em dias úteis para tendência do câmbio
_CDS_HIGH      = 250    # bp — risco soberano elevado
_CDS_MODERATE  = 150    # bp — risco soberano moderado
_VIX_HIGH      = 25.0   # VIX acima = risk-off global
_VIX_LOW       = 15.0   # VIX abaixo = risk-on global


# ---------------------------------------------------------------------------
# Leitura do banco SQLite
# ---------------------------------------------------------------------------

def _load_macro_series(con: sqlite3.Connection, series_name: str, days: int = 120) -> pd.Series:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    try:
        df = pd.read_sql(
            "SELECT date, value FROM macro_series WHERE series=? AND date>=? ORDER BY date",
            con, params=(series_name, cutoff),
        )
        if df.empty:
            return pd.Series(dtype=float)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["value"].astype(float)
    except Exception:
        return pd.Series(dtype=float)


def _load_price_series(con: sqlite3.Connection, ticker: str, days: int = 120) -> pd.Series:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    try:
        df = pd.read_sql(
            "SELECT trade_date, close FROM cotahist_daily WHERE ticker=? AND trade_date>=? ORDER BY trade_date",
            con, params=(ticker, cutoff),
        )
        if df.empty:
            return pd.Series(dtype=float)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        return df.set_index("trade_date")["close"].astype(float)
    except Exception:
        return pd.Series(dtype=float)


def _last(s: pd.Series) -> float:
    if s.empty:
        return float("nan")
    return float(s.iloc[-1])


def _trend_pct(s: pd.Series, window: int = 21) -> float:
    """Variação percentual nos últimos `window` observações."""
    if len(s) < 2:
        return 0.0
    n = min(window, len(s))
    old = float(s.iloc[-n])
    new = float(s.iloc[-1])
    if old == 0:
        return 0.0
    return (new / old - 1.0) * 100.0


# ---------------------------------------------------------------------------
# Sub-scores por dimensão (0–100)
# ---------------------------------------------------------------------------

def _monetary_score(selic: float) -> tuple[float, str]:
    """Quão restritiva está a política monetária (100 = máximo aperto)."""
    if np.isnan(selic):
        return 50.0, "NEUTRO"
    if selic >= _SELIC_HIGH:
        return min(100.0, 50.0 + (selic - _SELIC_HIGH) * 5), "RESTRITIVO"
    if selic <= _SELIC_LOW:
        return max(0.0, 50.0 - (_SELIC_LOW - selic) * 5), "EXPANSIONISTA"
    # Selic na faixa neutra: score proporcional
    score = 50.0 + (selic - 9.5) * 10.0
    return float(np.clip(score, 0, 100)), "NEUTRO"


def _inflation_score(ipca: float) -> tuple[float, str]:
    """Quão pressionada está a inflação (100 = muito acima da meta)."""
    if np.isnan(ipca):
        return 40.0, "CONTROLADA"
    if ipca >= _IPCA_HIGH:
        return min(100.0, 60.0 + (ipca - _IPCA_HIGH) * 8), "ALTA"
    if ipca <= 2.0:
        return 15.0, "DEFLAÇÃO"
    score = (ipca / _IPCA_HIGH) * 60.0
    label = "ALTA" if ipca > _IPCA_MODERATE else "CONTROLADA"
    return float(np.clip(score, 0, 100)), label


def _fx_score(ptax_trend_pct: float) -> tuple[float, str]:
    """Quão forte está o dólar contra o real (100 = BRL muito depreciado)."""
    if np.isnan(ptax_trend_pct):
        return 50.0, "ESTÁVEL"
    if ptax_trend_pct >= 5.0:
        return min(100.0, 60.0 + ptax_trend_pct * 2), "DÓLAR_FORTE"
    if ptax_trend_pct <= -5.0:
        return max(0.0, 40.0 + ptax_trend_pct * 2), "DÓLAR_FRACO"
    return 50.0 + ptax_trend_pct * 2, "ESTÁVEL"


def _sovereign_risk_score(cds: float) -> tuple[float, str]:
    """Score de risco soberano baseado no CDS Brasil (100 = risco máximo)."""
    if np.isnan(cds):
        return 40.0, "MODERADO"
    if cds >= _CDS_HIGH:
        return min(100.0, 60.0 + (cds - _CDS_HIGH) * 0.2), "ELEVADO"
    if cds <= _CDS_MODERATE:
        return max(0.0, (cds / _CDS_MODERATE) * 40.0), "BAIXO"
    score = 40.0 + (cds - _CDS_MODERATE) / (_CDS_HIGH - _CDS_MODERATE) * 20.0
    return float(np.clip(score, 0, 100)), "MODERADO"


def _global_risk_score(vix: float) -> tuple[float, str]:
    """Score de aversão a risco global (100 = máximo risk-off)."""
    if np.isnan(vix):
        return 40.0, "NEUTRAL"
    if vix >= _VIX_HIGH:
        return min(100.0, 50.0 + (vix - _VIX_HIGH) * 2), "RISK_OFF"
    if vix <= _VIX_LOW:
        return max(0.0, (vix / _VIX_LOW) * 30.0), "RISK_ON"
    score = 30.0 + (vix - _VIX_LOW) / (_VIX_HIGH - _VIX_LOW) * 20.0
    return float(np.clip(score, 0, 100)), "NEUTRAL"


# ---------------------------------------------------------------------------
# Engine principal
# ---------------------------------------------------------------------------

def detect_regime(
    con: sqlite3.Connection | None = None,
    *,
    selic_override: float | None = None,
    ipca_override: float | None = None,
    ptax_override: float | None = None,
    cds_override: float | None = None,
    vix_override: float | None = None,
) -> RegimeSnapshot:
    """
    Detecta o regime macro atual.

    Prioridade de dados: overrides → SQLite → yfinance → NaN (fallback seguro).
    Nunca lança exceção — retorna snapshot neutro se todos os dados falharem.
    """
    selic = selic_override
    ipca  = ipca_override
    ptax_trend = None
    cds   = cds_override
    vix   = vix_override

    if con is not None:
        if selic is None:
            s = _load_macro_series(con, "selic_over", 10)
            selic = _last(s)
        if ipca is None:
            s = _load_macro_series(con, "ipca_12m", 40)
            ipca = _last(s)
        if ptax_trend is None:
            s = _load_macro_series(con, "ptax_usd", 90)
            ptax_trend = _trend_pct(s, _PTAX_TREND_W)
        if cds is None:
            s = _load_macro_series(con, "cds_brasil", 60)
            cds = _last(s)

    # Fallback yfinance para VIX e S&P 500
    if vix is None:
        try:
            import yfinance as yf  # type: ignore[import-not-found]
            vix_hist = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
            if not vix_hist.empty:
                vix = float(vix_hist["Close"].iloc[-1])
        except Exception:
            vix = float("nan")

    ptax_trend_val = ptax_trend if ptax_trend is not None else float("nan")

    # Sub-scores
    mon_score, mon_stance = _monetary_score(selic if selic is not None else float("nan"))
    inf_score, inf_label  = _inflation_score(ipca if ipca is not None else float("nan"))
    fx_score_val, fx_label = _fx_score(ptax_trend_val)
    sov_score, sov_label  = _sovereign_risk_score(cds if cds is not None else float("nan"))
    gbl_score, risk_app   = _global_risk_score(vix if vix is not None else float("nan"))

    # Headwind: aperto monetário + inflação + câmbio fraco + risco soberano + risk-off
    headwind = float(np.clip(
        mon_score * 0.30
        + inf_score * 0.20
        + fx_score_val * 0.20
        + sov_score * 0.15
        + gbl_score * 0.15,
        0, 100,
    ))

    # Tailwind: inverso — juros expansivos + inflação controlada + BRL forte + risk-on
    tailwind = float(np.clip(100.0 - headwind, 0, 100))

    # Regime dominante: o componente com maior desvio do neutro (50)
    scores_labeled = [
        (abs(mon_score - 50), "APERTO_MONETÁRIO" if mon_score > 50 else "CICLO_EXPANSIONISTA"),
        (abs(inf_score - 40), "INFLAÇÃO_ALTA" if inf_score > 40 else "INFLAÇÃO_CONTROLADA"),
        (abs(fx_score_val - 50), "DÓLAR_FORTE" if fx_score_val > 50 else "BRL_FORTE"),
        (abs(sov_score - 40), "RISCO_SOBERANO_ELEVADO" if sov_score > 40 else "RISCO_SOBERANO_BAIXO"),
        (abs(gbl_score - 40), "RISK_OFF_GLOBAL" if gbl_score > 40 else "RISK_ON_GLOBAL"),
    ]
    dominant_deviation, dominant_label = max(scores_labeled, key=lambda x: x[0])
    regime_score = float(np.clip(50.0 + dominant_deviation, 0, 100))

    components = {
        "selic": round(selic, 2) if selic is not None and not np.isnan(selic) else None,
        "ipca_12m": round(ipca, 2) if ipca is not None and not np.isnan(ipca) else None,
        "ptax_trend_21d_pct": round(ptax_trend_val, 2) if not np.isnan(ptax_trend_val) else None,
        "cds_brasil_bp": round(cds, 0) if cds is not None and not np.isnan(cds) else None,
        "vix": round(vix, 1) if vix is not None and not np.isnan(vix) else None,
        "monetary_score": round(mon_score, 1),
        "inflation_score": round(inf_score, 1),
        "fx_score": round(fx_score_val, 1),
        "sovereign_risk_score": round(sov_score, 1),
        "global_risk_score": round(gbl_score, 1),
    }

    return RegimeSnapshot(
        as_of=date.today().isoformat(),
        regime_label=dominant_label,
        regime_score=round(regime_score, 1),
        macro_headwind=round(headwind, 1),
        macro_tailwind=round(tailwind, 1),
        risk_appetite=risk_app,
        monetary_stance=mon_stance,
        fx_regime=fx_label,
        inflation_regime=inf_label,
        sovereign_risk=sov_label,
        components=components,
    )


# ---------------------------------------------------------------------------
# Ajuste de score de ativo por regime
# ---------------------------------------------------------------------------

def apply_regime_adjustment(
    raw_score: float,
    snapshot: RegimeSnapshot,
    asset_type: str = "ACAO",   # ACAO | COMMODITY | FUNDO
    sector: str = "",           # FINANCEIRO | EXPORTADOR | DOMESTICO
) -> dict:
    """
    Ajusta o score quantitativo bruto pelo contexto macro.

    Retorna dict com:
        adjusted_score   : score ajustado [0–100]
        regime_multiplier: fator aplicado [0.5–1.2]
        regime_comment   : explicação humana do ajuste
    """
    multiplier = 1.0
    comments: list[str] = []

    # Penalidade por headwind macro elevado
    if snapshot.macro_headwind >= 70:
        multiplier -= 0.20
        comments.append("ambiente macro adverso (headwind elevado)")
    elif snapshot.macro_headwind >= 55:
        multiplier -= 0.10
        comments.append("pressão macro moderada")

    # Bônus por tailwind forte
    if snapshot.macro_tailwind >= 70:
        multiplier += 0.15
        comments.append("ambiente macro favorável")

    # Risk-off penaliza ativos cíclicos
    if snapshot.risk_appetite == "RISK_OFF" and sector in ("DOMESTICO", "CÍCLICO", ""):
        multiplier -= 0.15
        comments.append("risk-off global desfavorece ativos cíclicos")

    # Aperto monetário penaliza crescimento/small-caps
    if snapshot.monetary_stance == "RESTRITIVO" and sector not in ("FINANCEIRO", "EXPORTADOR"):
        multiplier -= 0.10
        comments.append("Selic alta pressiona custo de capital")

    # Exportadores beneficiados por dólar forte
    if snapshot.fx_regime == "DÓLAR_FORTE" and sector == "EXPORTADOR":
        multiplier += 0.10
        comments.append("câmbio favorece exportadores")

    multiplier = float(np.clip(multiplier, 0.5, 1.2))
    adjusted = float(np.clip(raw_score * multiplier, 0, 100))

    return {
        "raw_score": round(raw_score, 1),
        "adjusted_score": round(adjusted, 1),
        "regime_multiplier": round(multiplier, 3),
        "regime_comment": "; ".join(comments) if comments else "sem ajuste de regime significativo",
        "regime_label": snapshot.regime_label,
        "macro_headwind": snapshot.macro_headwind,
        "macro_tailwind": snapshot.macro_tailwind,
    }
