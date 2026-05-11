"""
Strategy Builder

Para cada ativo, classifica o cenário de mercado e monta as estruturas
mais aderentes, retornando uma lista de StrategyOpportunity prontas para
ranking e relatório.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np

from src.options.options_chain import OptionsChain, OptionRecord
from src.options.payoff_models import (
    Leg, StrategyPayoff,
    bull_call_spread, bear_put_spread, bear_call_spread, bull_put_spread,
    iron_condor, butterfly_calls, butterfly_puts,
    straddle, strangle, covered_call, collar, protective_put,
    long_call, long_put,
)
from src.options.probability_models import prob_profit, expected_value

CONTRACT_SIZE = 100


# ---------------------------------------------------------------------------
# Cenário de mercado
# ---------------------------------------------------------------------------

class MarketCondition(str, Enum):
    ALTA_FORTE = "ALTA_FORTE"
    ALTA_MODERADA = "ALTA_MODERADA"
    BAIXA_FORTE = "BAIXA_FORTE"
    BAIXA_MODERADA = "BAIXA_MODERADA"
    LATERAL = "LATERAL"
    ALTA_VOLATILIDADE = "ALTA_VOL"
    BAIXA_VOLATILIDADE = "BAIXA_VOL"
    INDEFINIDO = "INDEFINIDO"


def classify_market(
    con,
    underlying: str,
    qcfg: dict,
) -> MarketCondition:
    """
    Classifica o mercado usando SMA, RSI e volatilidade histórica.
    """
    import pandas as pd
    from src.quant.indicators import atr
    from src.quant.volatility import historical_volatility

    q = """
    SELECT trade_date, AVG(close) AS close, MAX(high) AS high, MIN(low) AS low
    FROM b3_quotes
    WHERE ticker = ? AND asset_type = 'ACAO'
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT 60
    """
    try:
        df = pd.read_sql_query(q, con, params=(underlying,))
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.sort_values("trade_date").reset_index(drop=True)
    except Exception:
        return MarketCondition.INDEFINIDO

    if len(df) < 22:
        return MarketCondition.INDEFINIDO

    closes = df["close"]
    s = float(closes.iloc[-1])
    sma9 = float(closes.tail(9).mean())
    sma21 = float(closes.tail(21).mean())

    # RSI simples
    delta = closes.diff().dropna()
    gain = delta.where(delta > 0, 0.0).tail(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).tail(14).mean()
    rsi = 100.0 - 100.0 / (1 + gain / loss) if loss > 0 else 70.0

    # Volatilidade
    _hv_now = historical_volatility(closes, window=10)
    _hv_ref = historical_volatility(closes, window=21)
    hv_now = float(_hv_now.iloc[-1]) if hasattr(_hv_now, "iloc") else float(_hv_now)
    hv_ref = float(_hv_ref.iloc[-1]) if hasattr(_hv_ref, "iloc") else float(_hv_ref)
    if hv_now != hv_now: hv_now = 0.30
    if hv_ref != hv_ref: hv_ref = 0.30
    vol_ratio = hv_now / hv_ref if hv_ref > 0 else 1.0

    # Tendência
    above_sma9 = s > sma9
    above_sma21 = s > sma21
    sma9_above_sma21 = sma9 > sma21

    if vol_ratio > 1.8 or hv_now > 0.50:
        return MarketCondition.ALTA_VOLATILIDADE
    if vol_ratio < 0.6 and hv_now < 0.20:
        return MarketCondition.BAIXA_VOLATILIDADE
    if above_sma9 and above_sma21 and sma9_above_sma21 and rsi >= 58:
        return MarketCondition.ALTA_FORTE
    if above_sma21 and rsi >= 50:
        return MarketCondition.ALTA_MODERADA
    if not above_sma9 and not above_sma21 and not sma9_above_sma21 and rsi <= 42:
        return MarketCondition.BAIXA_FORTE
    if not above_sma21 and rsi <= 50:
        return MarketCondition.BAIXA_MODERADA
    return MarketCondition.LATERAL


# ---------------------------------------------------------------------------
# StrategyOpportunity
# ---------------------------------------------------------------------------

@dataclass
class StrategyOpportunity:
    payoff: StrategyPayoff
    market_condition: MarketCondition
    scenario_adherence: float   # 0-1 — quão bem se encaixa no cenário
    prob_profit: float           # 0-1
    expected_value: float        # R$ esperado
    hv: float                    # HV usada nos cálculos
    score: float = 0.0          # preenchido pelo ranking
    rank: int = 0

    @property
    def name(self) -> str:
        return self.payoff.name

    @property
    def underlying(self) -> str:
        return self.payoff.underlying

    @property
    def net_cost(self) -> float:
        return self.payoff.net_cost

    @property
    def max_profit(self) -> float:
        return self.payoff.max_profit

    @property
    def max_loss(self) -> float:
        return self.payoff.max_loss

    @property
    def breakevens(self) -> list:
        return self.payoff.breakevens

    @property
    def risk_level(self) -> str:
        return self.payoff.risk_level

    @property
    def legs(self) -> list:
        return self.payoff.legs

    @property
    def status(self) -> str:
        """OPERACIONAL | ESTUDO | DESCARTAR baseado em score e risk_category."""
        p = self.payoff
        if p.risk_category == "ALTO_RISCO_NAO_RECOMENDADO" or self.score < 30:
            return "DESCARTAR"
        if self.score >= 60 and p.risk_category in ("BAIXO", "MODERADO"):
            return "OPERACIONAL"
        return "ESTUDO"

    @property
    def why_ranked(self) -> str:
        """Explicação legível do motivo de aparecimento no ranking."""
        p = self.payoff
        reasons = []
        if self.scenario_adherence >= 0.8:
            reasons.append(
                f"cenário {self.market_condition.value} "
                f"({self.scenario_adherence:.0%} aderência)"
            )
        if p.risk_level == "DEFINIDO":
            reasons.append("risco definido")
        if not math.isinf(p.risk_reward) and p.risk_reward >= 1.5:
            reasons.append(f"R/R {p.risk_reward:.1f}x")
        if self.prob_profit >= 0.55:
            reasons.append(f"P(lucro) {self.prob_profit:.0%}")
        if p.risk_category == "BAIXO":
            reasons.append("categoria BAIXO risco")
        if not reasons:
            reasons.append("estrutura aderente ao cenário")
        return "Apareceu porque: " + ", ".join(reasons) + "."


# ---------------------------------------------------------------------------
# Helpers de conversão OptionRecord → Leg
# ---------------------------------------------------------------------------

def _to_leg(opt: OptionRecord, direction: str, qty: int = 1) -> Leg:
    return Leg(
        ticker=opt.ticker,
        option_type=opt.option_type,
        direction=direction,
        strike=opt.strike,
        expiry=opt.expiry,
        dte=opt.dte,
        price=opt.price,
        quantity=qty,
        volume=opt.volume,
        trades=opt.trades,
        delta=opt.delta,
        liq_score=opt.liq_score,
    )


def _min_liq_score(legs: list) -> float:
    scores = [l.liq_score for l in legs if hasattr(l, "liq_score")]
    return min(scores) if scores else 0.0


def _scenario_adherence(stype: str, condition: MarketCondition) -> float:
    mapping = {
        MarketCondition.ALTA_FORTE:       {"DIRECIONAL": 1.0, "SPREAD_ALTA": 0.9, "SPREAD_BAIXA": 0.1, "CONDOR": 0.2, "BUTTERFLY": 0.2, "VOLATILIDADE": 0.4, "RENDA": 0.3, "PROTECAO": 0.2},
        MarketCondition.ALTA_MODERADA:    {"SPREAD_ALTA": 1.0, "DIRECIONAL": 0.8, "RENDA": 0.7, "CONDOR": 0.4, "BUTTERFLY": 0.4, "SPREAD_BAIXA": 0.1, "VOLATILIDADE": 0.3, "PROTECAO": 0.3},
        MarketCondition.BAIXA_FORTE:      {"DIRECIONAL": 1.0, "SPREAD_BAIXA": 0.9, "PROTECAO": 0.8, "SPREAD_ALTA": 0.1, "CONDOR": 0.2, "BUTTERFLY": 0.2, "VOLATILIDADE": 0.4, "RENDA": 0.2},
        MarketCondition.BAIXA_MODERADA:   {"SPREAD_BAIXA": 1.0, "DIRECIONAL": 0.8, "PROTECAO": 0.7, "CONDOR": 0.4, "BUTTERFLY": 0.4, "SPREAD_ALTA": 0.1, "VOLATILIDADE": 0.3, "RENDA": 0.2},
        MarketCondition.LATERAL:          {"CONDOR": 1.0, "BUTTERFLY": 1.0, "RENDA": 0.8, "SPREAD_ALTA": 0.5, "SPREAD_BAIXA": 0.5, "DIRECIONAL": 0.2, "VOLATILIDADE": 0.3, "PROTECAO": 0.5},
        MarketCondition.ALTA_VOLATILIDADE:{"VOLATILIDADE": 1.0, "DIRECIONAL": 0.6, "SPREAD_ALTA": 0.5, "SPREAD_BAIXA": 0.5, "CONDOR": 0.2, "BUTTERFLY": 0.2, "RENDA": 0.3, "PROTECAO": 0.6},
        MarketCondition.BAIXA_VOLATILIDADE:{"CONDOR": 1.0, "BUTTERFLY": 0.9, "RENDA": 0.8, "SPREAD_ALTA": 0.6, "SPREAD_BAIXA": 0.6, "DIRECIONAL": 0.4, "VOLATILIDADE": 0.2, "PROTECAO": 0.4},
        MarketCondition.INDEFINIDO:       {k: 0.5 for k in ["DIRECIONAL","SPREAD_ALTA","SPREAD_BAIXA","CONDOR","BUTTERFLY","VOLATILIDADE","RENDA","PROTECAO"]},
    }
    return mapping.get(condition, {}).get(stype, 0.5)


def _make_opportunity(payoff: StrategyPayoff, condition: MarketCondition,
                      hv: float, S: float, r: float) -> StrategyOpportunity:
    T = max(payoff.dte / 365.0, 1e-6)
    pp = prob_profit(payoff, S, T, hv, r)
    ev = expected_value(payoff, S, T, hv, r)
    adherence = _scenario_adherence(payoff.strategy_type, condition)
    return StrategyOpportunity(
        payoff=payoff,
        market_condition=condition,
        scenario_adherence=adherence,
        prob_profit=pp,
        expected_value=ev if not math.isnan(ev) else 0.0,
        hv=hv,
    )


# ---------------------------------------------------------------------------
# Builders por estratégia
# ---------------------------------------------------------------------------

def _build_bull_call_spreads(chain: OptionsChain, condition: MarketCondition,
                              qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))

    for exp in chain.expiries():
        calls = [c for c in chain.liquid_calls(min_vol, min_tr) if c.expiry == exp]
        calls = sorted(calls, key=lambda c: c.strike)
        if len(calls) < 2:
            continue
        # compra ATM/levemente OTM, vende strike maior ~5-10% acima
        atm = min(calls, key=lambda c: abs(c.moneyness_pct))
        otm_targets = [c for c in calls if c.strike > atm.strike * 1.03]
        if not otm_targets:
            continue
        sell_leg_opt = min(otm_targets, key=lambda c: abs(c.strike - atm.strike * 1.06))
        buy_leg = _to_leg(atm, "BUY")
        sell_leg = _to_leg(sell_leg_opt, "SELL")
        if buy_leg.price <= sell_leg.price:
            continue
        payoff = bull_call_spread(buy_leg, sell_leg, chain.underlying, chain.stock_price)
        if payoff.net_cost <= 0:
            continue
        results.append(_make_opportunity(payoff, condition, chain.hv, chain.stock_price, r))
    return results


def _build_bear_put_spreads(chain: OptionsChain, condition: MarketCondition,
                             qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))

    for exp in chain.expiries():
        puts = [p for p in chain.liquid_puts(min_vol, min_tr) if p.expiry == exp]
        puts = sorted(puts, key=lambda p: p.strike, reverse=True)
        if len(puts) < 2:
            continue
        atm = min(puts, key=lambda p: abs(p.moneyness_pct))
        lower_targets = [p for p in puts if p.strike < atm.strike * 0.97]
        if not lower_targets:
            continue
        sell_leg_opt = min(lower_targets, key=lambda p: abs(p.strike - atm.strike * 0.94))
        buy_leg = _to_leg(atm, "BUY")
        sell_leg = _to_leg(sell_leg_opt, "SELL")
        if buy_leg.price <= sell_leg.price:
            continue
        payoff = bear_put_spread(buy_leg, sell_leg, chain.underlying, chain.stock_price)
        if payoff.net_cost <= 0:
            continue
        results.append(_make_opportunity(payoff, condition, chain.hv, chain.stock_price, r))
    return results


def _build_bear_call_spreads(chain: OptionsChain, condition: MarketCondition,
                              qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))

    for exp in chain.expiries():
        calls = [c for c in chain.liquid_calls(min_vol, min_tr) if c.expiry == exp]
        calls = sorted(calls, key=lambda c: c.strike)
        if len(calls) < 2:
            continue
        atm = min(calls, key=lambda c: abs(c.moneyness_pct))
        otm_candidates = [c for c in calls if c.strike > atm.strike * 1.02]
        if not otm_candidates:
            continue
        sell_leg_opt = otm_candidates[0]  # mais próximo do ATM ainda OTM
        buy_leg_opt = min(otm_candidates, key=lambda c: abs(c.strike - sell_leg_opt.strike * 1.06))
        if sell_leg_opt.ticker == buy_leg_opt.ticker:
            if len(otm_candidates) < 2:
                continue
            buy_leg_opt = otm_candidates[1]
        sell_leg = _to_leg(sell_leg_opt, "SELL")
        buy_leg = _to_leg(buy_leg_opt, "BUY")
        if sell_leg.price <= buy_leg.price:
            continue
        payoff = bear_call_spread(sell_leg, buy_leg, chain.underlying, chain.stock_price)
        if payoff.net_cost >= 0:
            continue
        results.append(_make_opportunity(payoff, condition, chain.hv, chain.stock_price, r))
    return results


def _build_bull_put_spreads(chain: OptionsChain, condition: MarketCondition,
                             qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))

    for exp in chain.expiries():
        puts = [p for p in chain.liquid_puts(min_vol, min_tr) if p.expiry == exp]
        puts = sorted(puts, key=lambda p: p.strike)
        if len(puts) < 2:
            continue
        atm = min(puts, key=lambda p: abs(p.moneyness_pct))
        lower_targets = [p for p in puts if p.strike < atm.strike * 0.98]
        if not lower_targets:
            continue
        sell_leg = _to_leg(atm, "SELL")
        buy_leg = _to_leg(lower_targets[-1], "BUY")
        if sell_leg.price <= buy_leg.price:
            continue
        payoff = bull_put_spread(sell_leg, buy_leg, chain.underlying, chain.stock_price)
        if payoff.net_cost >= 0:
            continue
        results.append(_make_opportunity(payoff, condition, chain.hv, chain.stock_price, r))
    return results


def _build_iron_condors(chain: OptionsChain, condition: MarketCondition,
                         qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))
    S = chain.stock_price

    for exp in chain.expiries():
        calls = sorted([c for c in chain.liquid_calls(min_vol, min_tr) if c.expiry == exp],
                       key=lambda c: c.strike)
        puts = sorted([p for p in chain.liquid_puts(min_vol, min_tr) if p.expiry == exp],
                      key=lambda p: p.strike)
        if len(calls) < 2 or len(puts) < 2:
            continue

        # put side: sell ATM put, buy lower put (~5% abaixo)
        sell_put_opt = min(puts, key=lambda p: abs(p.strike - S * 0.97))
        buy_put_candidates = [p for p in puts if p.strike < sell_put_opt.strike * 0.95]
        if not buy_put_candidates:
            continue
        buy_put_opt = max(buy_put_candidates, key=lambda p: p.strike)

        # call side: sell OTM call (~3% acima), buy higher call (~8% acima)
        sell_call_opt = min(calls, key=lambda c: abs(c.strike - S * 1.03))
        buy_call_candidates = [c for c in calls if c.strike > sell_call_opt.strike * 1.05]
        if not buy_call_candidates:
            continue
        buy_call_opt = min(buy_call_candidates, key=lambda c: c.strike)

        if (sell_put_opt.price <= buy_put_opt.price or
                sell_call_opt.price <= buy_call_opt.price):
            continue

        sp = _to_leg(sell_put_opt, "SELL")
        bp = _to_leg(buy_put_opt, "BUY")
        sc = _to_leg(sell_call_opt, "SELL")
        bc = _to_leg(buy_call_opt, "BUY")
        payoff = iron_condor(sp, bp, sc, bc, chain.underlying, S)
        if payoff.net_cost >= 0:
            continue
        results.append(_make_opportunity(payoff, condition, chain.hv, S, r))
    return results


def _build_butterflies(chain: OptionsChain, condition: MarketCondition,
                        qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))
    S = chain.stock_price

    for exp in chain.expiries():
        calls = sorted([c for c in chain.liquid_calls(min_vol, min_tr) if c.expiry == exp],
                       key=lambda c: c.strike)
        if len(calls) < 3:
            continue
        mid = min(calls, key=lambda c: abs(c.strike - S))
        lowers = [c for c in calls if c.strike < mid.strike]
        uppers = [c for c in calls if c.strike > mid.strike]
        if not lowers or not uppers:
            continue
        low = max(lowers, key=lambda c: c.strike)
        high = min(uppers, key=lambda c: c.strike)
        if abs((mid.strike - low.strike) - (high.strike - mid.strike)) > low.strike * 0.02:
            continue  # asas desiguais
        bl = _to_leg(low, "BUY")
        sm1 = _to_leg(mid, "SELL")
        sm2 = _to_leg(mid, "SELL")
        bh = _to_leg(high, "BUY")
        debit = (low.price - 2 * mid.price + high.price) * CONTRACT_SIZE
        if debit <= 0:
            continue
        payoff = butterfly_calls(bl, sm1, sm2, bh, chain.underlying, S)
        results.append(_make_opportunity(payoff, condition, chain.hv, S, r))
    return results


def _build_straddles(chain: OptionsChain, condition: MarketCondition,
                      qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))

    for exp in chain.expiries():
        atm_call = chain.atm_call(exp)
        atm_put = chain.atm_put(exp)
        if atm_call is None or atm_put is None:
            continue
        # usa mesmo strike (mais próximo)
        target_strike = atm_call.strike
        put_candidates = [p for p in chain.liquid_puts(min_vol, min_tr)
                         if p.expiry == exp and abs(p.strike - target_strike) / target_strike < 0.03]
        if not put_candidates:
            continue
        put_opt = min(put_candidates, key=lambda p: abs(p.strike - target_strike))
        cl = _to_leg(atm_call, "BUY")
        pl = _to_leg(put_opt, "BUY")
        payoff = straddle(cl, pl, chain.underlying, chain.stock_price)
        results.append(_make_opportunity(payoff, condition, chain.hv, chain.stock_price, r))
    return results


def _build_strangles(chain: OptionsChain, condition: MarketCondition,
                      qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))
    S = chain.stock_price

    for exp in chain.expiries():
        otm_calls = sorted([c for c in chain.liquid_calls(min_vol, min_tr)
                            if c.expiry == exp and c.moneyness_pct < -2.0],
                           key=lambda c: c.strike)
        otm_puts = sorted([p for p in chain.liquid_puts(min_vol, min_tr)
                           if p.expiry == exp and p.moneyness_pct < -2.0],
                          key=lambda p: p.strike, reverse=True)
        if not otm_calls or not otm_puts:
            continue
        call_opt = min(otm_calls, key=lambda c: abs(c.strike - S * 1.05))
        put_opt = min(otm_puts, key=lambda p: abs(p.strike - S * 0.95))
        cl = _to_leg(call_opt, "BUY")
        pl = _to_leg(put_opt, "BUY")
        payoff = strangle(cl, pl, chain.underlying, S)
        results.append(_make_opportunity(payoff, condition, chain.hv, S, r))
    return results


def _build_covered_calls(chain: OptionsChain, condition: MarketCondition,
                          qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))
    S = chain.stock_price

    for exp in chain.expiries():
        otm_calls = [c for c in chain.liquid_calls(min_vol, min_tr)
                    if c.expiry == exp and c.moneyness_pct < -1.0]
        if not otm_calls:
            continue
        sell_opt = min(otm_calls, key=lambda c: abs(c.strike - S * 1.05))
        cl = _to_leg(sell_opt, "SELL")
        payoff = covered_call(S, cl, chain.underlying)
        results.append(_make_opportunity(payoff, condition, chain.hv, S, r))
    return results


def _build_collars(chain: OptionsChain, condition: MarketCondition,
                   qcfg: dict) -> List[StrategyOpportunity]:
    results = []
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 3))
    r = float(qcfg.get("taxa_livre_risco", 0.1475))
    S = chain.stock_price

    for exp in chain.expiries():
        otm_puts = [p for p in chain.liquid_puts(min_vol, min_tr)
                   if p.expiry == exp and p.moneyness_pct < -2.0]
        otm_calls = [c for c in chain.liquid_calls(min_vol, min_tr)
                    if c.expiry == exp and c.moneyness_pct < -2.0]
        if not otm_puts or not otm_calls:
            continue
        put_opt = min(otm_puts, key=lambda p: abs(p.strike - S * 0.95))
        call_opt = min(otm_calls, key=lambda c: abs(c.strike - S * 1.05))
        pl = _to_leg(put_opt, "BUY")
        cl = _to_leg(call_opt, "SELL")
        payoff = collar(S, pl, cl, chain.underlying)
        results.append(_make_opportunity(payoff, condition, chain.hv, S, r))
    return results


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

_CONDITION_STRATEGIES = {
    MarketCondition.ALTA_FORTE:        [_build_bull_call_spreads, _build_bull_put_spreads, _build_covered_calls],
    MarketCondition.ALTA_MODERADA:     [_build_bull_call_spreads, _build_bull_put_spreads, _build_covered_calls, _build_collars],
    MarketCondition.BAIXA_FORTE:       [_build_bear_put_spreads, _build_bear_call_spreads],
    MarketCondition.BAIXA_MODERADA:    [_build_bear_put_spreads, _build_bear_call_spreads, _build_collars],
    MarketCondition.LATERAL:           [_build_iron_condors, _build_butterflies, _build_bear_call_spreads, _build_bull_put_spreads, _build_covered_calls],
    MarketCondition.ALTA_VOLATILIDADE: [_build_straddles, _build_strangles, _build_bull_call_spreads, _build_bear_put_spreads],
    MarketCondition.BAIXA_VOLATILIDADE:[_build_iron_condors, _build_butterflies, _build_covered_calls],
    MarketCondition.INDEFINIDO:        [_build_bull_call_spreads, _build_bear_call_spreads, _build_iron_condors],
}


def build_all_strategies(
    chain: OptionsChain,
    condition: MarketCondition,
    qcfg: dict,
) -> List[StrategyOpportunity]:
    """
    Monta todas as estruturas aderentes ao cenário e retorna a lista
    de oportunidades para ranking.
    """
    if len(chain) == 0:
        return []

    builders = _CONDITION_STRATEGIES.get(condition, [])
    results: List[StrategyOpportunity] = []
    for builder in builders:
        try:
            results.extend(builder(chain, condition, qcfg))
        except Exception:
            pass

    return results
