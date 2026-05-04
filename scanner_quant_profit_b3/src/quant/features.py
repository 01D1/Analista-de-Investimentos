"""
Feature Engineering — Quant Research Layer.

Transforma dados OHLCV + opção em vetores normalizados prontos
para o signal engine probabilístico.

Features geradas:
  Retornos:    ret_1, ret_3, ret_5, ret_10, ret_20 (%)
  Volatilidade: vol_10, vol_20, vol_60 (anualizada)
  Vol relativa: vol_ratio (vol_10 / vol_60)
  Volume:      volume_ratio (atual / média 20d)
  Técnico:     dist_sma9, dist_sma20, high_break_20, range_pos_20
  Opção:       moneyness_pct, dte, dte_norm, liq_score, spread_pct, premium_pct
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import sma, log_returns
from .volatility import historical_volatility


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StockFeatures:
    ret_1: float = 0.0
    ret_3: float = 0.0
    ret_5: float = 0.0
    ret_10: float = 0.0
    ret_20: float = 0.0
    vol_10: float = 0.0
    vol_20: float = 0.0
    vol_60: float = 0.0
    vol_ratio: float = 1.0        # vol_10 / vol_60 — regime de vol
    volume_ratio: float = 1.0     # vol atual / média 20d
    dist_sma9: float = 0.0        # % distância da SMA 9
    dist_sma20: float = 0.0       # % distância da SMA 20
    high_break_20: float = 0.0    # 1 se rompeu máx dos últimos 20d
    range_pos: float = 0.5        # posição no range [0,1] dos últimos 20d
    close: float = 0.0


@dataclass
class OptionFeatures:
    moneyness_pct: float = 0.0    # (S/K - 1)*100 para CALL; (K/S - 1)*100 para PUT
    dte: int = 0
    dte_norm: float = 0.0         # DTE / 30 (normalizado)
    liq_score: float = 0.0        # score de liquidez 0-100
    spread_pct: float = 0.0       # spread estimado / prêmio
    premium_pct: float = 0.0      # prêmio / preço do ativo (%)
    delta: float = 0.0


@dataclass
class FeatureVector:
    ticker: str
    underlying: str
    option_type: str
    stock: StockFeatures = field(default_factory=StockFeatures)
    option: OptionFeatures = field(default_factory=OptionFeatures)

    def to_dict(self) -> dict:
        d = {
            "ticker": self.ticker,
            "underlying": self.underlying,
            "option_type": self.option_type,
        }
        for k, v in vars(self.stock).items():
            d[f"s_{k}"] = v
        for k, v in vars(self.option).items():
            d[f"o_{k}"] = v
        return d


# ---------------------------------------------------------------------------
# Computação de features do ativo
# ---------------------------------------------------------------------------

def compute_stock_features(history: pd.DataFrame) -> StockFeatures:
    """
    Computa features do ativo a partir do histórico OHLCV.
    Requer colunas: close, high, low, volume.
    """
    if len(history) < 5:
        return StockFeatures()

    close = history["close"].astype(float).reset_index(drop=True)
    volume = history["volume"].astype(float).reset_index(drop=True)
    high = history["high"].astype(float).reset_index(drop=True)
    low = history["low"].astype(float).reset_index(drop=True)

    last = float(close.iloc[-1])
    n = len(close)

    def _ret(periods: int) -> float:
        if n > periods:
            prev = float(close.iloc[-(periods + 1)])
            return round((last / prev - 1.0) * 100.0, 3) if prev > 0 else 0.0
        return 0.0

    def _vol(window: int) -> float:
        if n > window:
            hv = historical_volatility(close, window=window).dropna()
            return round(float(hv.iloc[-1]), 4) if not hv.empty else 0.0
        return 0.0

    vol_w = min(20, n - 1)
    avg_vol = float(sma(volume, vol_w).iloc[-1]) if vol_w > 0 else 1.0
    volume_ratio = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

    sma9 = float(sma(close, min(9, n)).iloc[-1])
    sma20 = float(sma(close, min(20, n)).iloc[-1])
    dist_sma9 = round((last / sma9 - 1.0) * 100.0, 3) if sma9 > 0 else 0.0
    dist_sma20 = round((last / sma20 - 1.0) * 100.0, 3) if sma20 > 0 else 0.0

    win = min(20, n)
    recent_high = float(high.iloc[-win:].max())
    recent_low = float(low.iloc[-win:].min())
    high_break = 1.0 if last >= recent_high else 0.0
    rng = recent_high - recent_low
    range_pos = round((last - recent_low) / rng, 3) if rng > 0 else 0.5

    vol_10 = _vol(10)
    vol_20 = _vol(20)
    vol_60 = _vol(60)

    return StockFeatures(
        ret_1=_ret(1),
        ret_3=_ret(3),
        ret_5=_ret(5),
        ret_10=_ret(10),
        ret_20=_ret(20),
        vol_10=vol_10,
        vol_20=vol_20,
        vol_60=vol_60,
        vol_ratio=round(vol_10 / vol_60, 3) if vol_60 > 0 else 1.0,
        volume_ratio=round(volume_ratio, 3),
        dist_sma9=dist_sma9,
        dist_sma20=dist_sma20,
        high_break_20=high_break,
        range_pos=range_pos,
        close=round(last, 4),
    )


# ---------------------------------------------------------------------------
# Computação de features da opção
# ---------------------------------------------------------------------------

def compute_option_features(
    opt_row: pd.Series,
    stock_close: float,
    min_trades: int = 10,
    min_volume: float = 100_000,
) -> OptionFeatures:
    from .options_math import estimated_spread, liquidity_score

    strike = float(opt_row.get("strike", 0))
    dte = int(opt_row.get("dte", 0))
    entry = float(opt_row.get("close", 0))
    trades = int(opt_row.get("trades", 0))
    volume_opt = float(opt_row.get("volume", 0))
    delta = float(opt_row.get("delta", 0) or 0)
    option_type = str(opt_row.get("option_type", "CALL")).upper()

    if strike > 0 and stock_close > 0:
        moneyness_pct = (
            (stock_close / strike - 1.0) * 100.0
            if option_type == "CALL"
            else (strike / stock_close - 1.0) * 100.0
        )
    else:
        moneyness_pct = 0.0

    spread = estimated_spread(entry, volume_opt, trades)
    spread_pct = round(spread / entry, 4) if entry > 0 else 0.0
    liq = liquidity_score(trades, volume_opt, min_trades, min_volume)
    premium_pct = round(entry / stock_close * 100.0, 3) if stock_close > 0 else 0.0

    return OptionFeatures(
        moneyness_pct=round(moneyness_pct, 3),
        dte=dte,
        dte_norm=round(dte / 30.0, 3),
        liq_score=liq,
        spread_pct=spread_pct,
        premium_pct=premium_pct,
        delta=round(delta, 4),
    )


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

def build_feature_vector(
    ticker: str,
    underlying: str,
    option_type: str,
    history: pd.DataFrame,
    opt_row: pd.Series,
) -> FeatureVector:
    stock_feat = compute_stock_features(history)
    opt_feat = compute_option_features(opt_row, stock_feat.close)
    return FeatureVector(
        ticker=ticker,
        underlying=underlying,
        option_type=option_type,
        stock=stock_feat,
        option=opt_feat,
    )


def feature_vectors_to_df(vectors: list[FeatureVector]) -> pd.DataFrame:
    """Converte lista de FeatureVector em DataFrame para análise."""
    return pd.DataFrame([fv.to_dict() for fv in vectors])
