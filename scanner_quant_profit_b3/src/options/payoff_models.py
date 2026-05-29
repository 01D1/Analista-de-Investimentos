"""
Payoff Models — Estruturas de Opções

Calcula payoff, risco máximo, ganho máximo, breakevens e risco/retorno
para todas as estruturas suportadas. Contrato padrão B3 = 100 ações.

Convenções:
  net_cost > 0  → débito (paga para entrar)
  net_cost < 0  → crédito (recebe para entrar)
  max_profit / max_loss em R$ por lote (100 ações)
  float('inf')  → ilimitado
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

CONTRACT_SIZE = 100  # lote padrão B3


# ---------------------------------------------------------------------------
# Perna de uma estrutura
# ---------------------------------------------------------------------------

@dataclass
class Leg:
    ticker: str
    option_type: str   # CALL | PUT | STOCK
    direction: str     # BUY | SELL
    strike: float      # 0 para STOCK
    expiry: str
    dte: int
    price: float       # prêmio ou preço da ação
    quantity: int = 1  # contratos (1 = CONTRACT_SIZE ações)
    volume: float = 0.0
    trades: int = 0
    delta: float = 0.0
    liq_score: float = 0.0

    @property
    def sign(self) -> float:
        return 1.0 if self.direction == "BUY" else -1.0

    def __str__(self) -> str:
        d = "C" if self.direction == "BUY" else "V"
        return (f"{d} {self.ticker} {self.option_type} "
                f"K={self.strike:.2f} @ R${self.price:.4f} vto={self.expiry}")


# ---------------------------------------------------------------------------
# Resultado de uma estrutura
# ---------------------------------------------------------------------------

@dataclass
class StrategyPayoff:
    name: str
    strategy_type: str          # SPREAD_ALTA | SPREAD_BAIXA | CONDOR | BUTTERFLY |
                                # VOLATILIDADE | PROTECAO | RENDA | DIRECIONAL
    legs: List[Leg]
    underlying: str
    stock_price: float
    dte: int
    expiry: str

    net_cost: float             # R$ por lote (positivo = débito)
    max_profit: float           # R$ por lote (inf = ilimitado)
    max_loss: float             # R$ por lote (inf = ilimitado)
    breakevens: List[float]

    risk_level: str             # DEFINIDO | ILIMITADO
    requires_margin: bool       # True se vende opção descoberta

    market_view: str            # descrição do cenário ideal
    best_scenario: str
    worst_scenario: str
    entry_condition: str
    exit_condition: str
    risk_observation: str

    # Classificação de risco e adequação (padrão seguro; sobrescrito por cada fábrica)
    risk_category: str = "MODERADO"
    # BAIXO | MODERADO | ALTO | ALTO_RISCO_NAO_RECOMENDADO

    suitability: str = "DIRECIONAL_ALTA"
    # DIRECIONAL_ALTA | DIRECIONAL_BAIXA | LATERAL | VOLATILIDADE_ALTA |
    # VOLATILIDADE_BAIXA | PROTECAO | RENDA_COM_CARTEIRA

    # computed
    _S_range: Optional[np.ndarray] = field(default=None, repr=False)
    _payoff_arr: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def risk_reward(self) -> float:
        if self.max_loss <= 0 or math.isinf(self.max_loss):
            return 0.0
        if math.isinf(self.max_profit):
            return float("inf")
        return round(self.max_profit / self.max_loss, 2)

    @property
    def credit(self) -> bool:
        return self.net_cost < 0

    def payoff_array(self, n_points: int = 200) -> tuple:
        """Retorna (S_range, payoff_per_share) para gráfico."""
        if self._S_range is not None:
            return self._S_range, self._payoff_arr

        lo = self.stock_price * 0.5
        hi = self.stock_price * 1.5
        S = np.linspace(lo, hi, n_points)
        payoff = compute_payoff_array(self.legs, S)
        return S, payoff / CONTRACT_SIZE  # por ação para gráfico legível

    def summary_line(self) -> str:
        mp = f"R${self.max_profit:,.0f}" if not math.isinf(self.max_profit) else "ilimitado"
        ml = f"R${self.max_loss:,.0f}" if not math.isinf(self.max_loss) else "ilimitado"
        be = " / ".join(f"{b:.2f}" for b in self.breakevens[:2])
        return (f"{self.name} | {self.underlying} | "
                f"Custo: R${self.net_cost:+.0f} | "
                f"MaxGanho: {mp} | MaxPerda: {ml} | BE: {be}")


# ---------------------------------------------------------------------------
# Motor genérico de payoff
# ---------------------------------------------------------------------------

def compute_payoff_array(legs: List[Leg], S_range: np.ndarray) -> np.ndarray:
    """Payoff total em R$ por lote para cada valor de S no vencimento."""
    total = np.zeros_like(S_range, dtype=float)
    for leg in legs:
        n = leg.quantity * CONTRACT_SIZE
        if leg.option_type == "CALL":
            intrinsic = np.maximum(S_range - leg.strike, 0.0)
        elif leg.option_type == "PUT":
            intrinsic = np.maximum(leg.strike - S_range, 0.0)
        else:  # STOCK
            intrinsic = S_range - leg.price
            total += leg.sign * n * intrinsic
            continue
        # opção: payoff = intrínseco - prêmio pago (ou + prêmio recebido)
        total += leg.sign * n * (intrinsic - leg.price)
    return total


def find_breakevens(legs: List[Leg], S_range: np.ndarray) -> List[float]:
    """Encontra os breakevens numericamente por mudança de sinal no payoff."""
    payoff = compute_payoff_array(legs, S_range)
    bes = []
    for i in range(len(payoff) - 1):
        if payoff[i] * payoff[i + 1] < 0:
            # interpolação linear
            be = S_range[i] - payoff[i] * (S_range[i + 1] - S_range[i]) / (payoff[i + 1] - payoff[i])
            bes.append(round(be, 2))
    return bes


# ---------------------------------------------------------------------------
# Fábricas por estrutura
# ---------------------------------------------------------------------------

def long_call(leg: Leg, underlying: str, stock_price: float) -> StrategyPayoff:
    cost = leg.price * CONTRACT_SIZE
    return StrategyPayoff(
        name="Long Call",
        strategy_type="DIRECIONAL",
        legs=[leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=leg.dte,
        expiry=leg.expiry,
        net_cost=cost,
        max_profit=float("inf"),
        max_loss=cost,
        breakevens=[round(leg.strike + leg.price, 2)],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Alta forte acima do breakeven",
        best_scenario=f"Ativo supera {leg.strike + leg.price:.2f} antes do vencimento",
        worst_scenario="Ativo fecha abaixo do strike → perde todo o prêmio",
        entry_condition="Tendência de alta confirmada, momentum positivo, HV baixa",
        exit_condition=f"Stop: prêmio cai 30%. Alvo: prêmio dobra ou ativo em {leg.strike*1.10:.2f}",
        risk_observation="Risco limitado ao prêmio. Decaimento temporal acelera próximo ao vencimento.",
        risk_category="MODERADO",
        suitability="DIRECIONAL_ALTA",
    )


def long_put(leg: Leg, underlying: str, stock_price: float) -> StrategyPayoff:
    cost = leg.price * CONTRACT_SIZE
    max_p = (leg.strike - leg.price) * CONTRACT_SIZE
    return StrategyPayoff(
        name="Long Put",
        strategy_type="DIRECIONAL",
        legs=[leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=leg.dte,
        expiry=leg.expiry,
        net_cost=cost,
        max_profit=max_p,
        max_loss=cost,
        breakevens=[round(leg.strike - leg.price, 2)],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Queda abaixo do breakeven",
        best_scenario=f"Ativo cai abaixo de {leg.strike - leg.price:.2f}",
        worst_scenario="Ativo sobe ou fica lateral → perde todo o prêmio",
        entry_condition="Tendência de queda, RSI abaixo de 40, rompimento de suporte",
        exit_condition="Stop: prêmio cai 30%. Alvo: prêmio dobra",
        risk_observation="Risco limitado ao prêmio. Decaimento temporal acelera próximo ao vencimento.",
        risk_category="MODERADO",
        suitability="DIRECIONAL_BAIXA",
    )


def short_call(leg: Leg, underlying: str, stock_price: float) -> StrategyPayoff:
    credit = leg.price * CONTRACT_SIZE
    return StrategyPayoff(
        name="Short Call (Descoberta)",
        strategy_type="RENDA",
        legs=[leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=leg.dte,
        expiry=leg.expiry,
        net_cost=-credit,
        max_profit=credit,
        max_loss=float("inf"),
        breakevens=[round(leg.strike + leg.price, 2)],
        risk_level="ILIMITADO",
        requires_margin=True,
        market_view="Lateral ou queda abaixo do strike",
        best_scenario=f"Ativo fecha abaixo de {leg.strike:.2f} no vencimento",
        worst_scenario="Ativo dispara acima do breakeven → perda ilimitada",
        entry_condition="Volatilidade alta, ativo em resistência, tendência lateral",
        exit_condition="Recompra se prêmio cair 50%. Stop: prêmio dobra",
        risk_observation="🚨 RISCO ILIMITADO — Ativo pode disparar sem limite. Exige margem de garantia e monitoramento constante. NÃO RECOMENDADO para operadores sem experiência.",
        risk_category="ALTO_RISCO_NAO_RECOMENDADO",
        suitability="VOLATILIDADE_BAIXA",
    )


def short_put(leg: Leg, underlying: str, stock_price: float) -> StrategyPayoff:
    credit = leg.price * CONTRACT_SIZE
    max_loss = (leg.strike - leg.price) * CONTRACT_SIZE
    return StrategyPayoff(
        name="Short Put (Descoberta)",
        strategy_type="RENDA",
        legs=[leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=leg.dte,
        expiry=leg.expiry,
        net_cost=-credit,
        max_profit=credit,
        max_loss=max_loss,
        breakevens=[round(leg.strike - leg.price, 2)],
        risk_level="DEFINIDO",
        requires_margin=True,
        market_view="Lateral ou alta acima do strike",
        best_scenario=f"Ativo fecha acima de {leg.strike:.2f}",
        worst_scenario="Ativo despenca → exercício com grande prejuízo",
        entry_condition="Suporte próximo, volatilidade alta, ativo estável",
        exit_condition="Recompra se prêmio cair 50%",
        risk_observation="Risco definido (exercício ao preço do strike). Exige margem. Só vender put com suporte técnico claro.",
        risk_category="ALTO",
        suitability="RENDA_COM_CARTEIRA",
    )


def bull_call_spread(buy_leg: Leg, sell_leg: Leg,
                     underlying: str, stock_price: float) -> StrategyPayoff:
    """Trava de Alta com CALL: compra K1 CALL, vende K2 CALL (K1 < K2)."""
    debit = (buy_leg.price - sell_leg.price) * CONTRACT_SIZE
    width = (sell_leg.strike - buy_leg.strike) * CONTRACT_SIZE
    max_p = width - debit
    be = round(buy_leg.strike + (buy_leg.price - sell_leg.price), 2)
    return StrategyPayoff(
        name="Trava de Alta (Bull Call Spread)",
        strategy_type="SPREAD_ALTA",
        legs=[buy_leg, sell_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=buy_leg.dte,
        expiry=buy_leg.expiry,
        net_cost=round(debit, 2),
        max_profit=round(max_p, 2),
        max_loss=round(debit, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view=f"Alta moderada até {sell_leg.strike:.2f}",
        best_scenario=f"Ativo acima de {sell_leg.strike:.2f} no vencimento",
        worst_scenario=f"Ativo abaixo de {buy_leg.strike:.2f} → perde R${debit:.0f}",
        entry_condition="Tendência de alta, RSI > 50, ativo acima das médias",
        exit_condition=f"Saída se ativo rompe suporte ou atinge {sell_leg.strike:.2f}",
        risk_observation="Risco totalmente definido. Uma das estruturas mais seguras para direcional de alta.",
        risk_category="BAIXO",
        suitability="DIRECIONAL_ALTA",
    )


def bear_put_spread(buy_leg: Leg, sell_leg: Leg,
                    underlying: str, stock_price: float) -> StrategyPayoff:
    """Trava de Baixa com PUT: compra K2 PUT, vende K1 PUT (K1 < K2)."""
    debit = (buy_leg.price - sell_leg.price) * CONTRACT_SIZE
    width = (buy_leg.strike - sell_leg.strike) * CONTRACT_SIZE
    max_p = width - debit
    be = round(buy_leg.strike - (buy_leg.price - sell_leg.price), 2)
    return StrategyPayoff(
        name="Trava de Baixa (Bear Put Spread)",
        strategy_type="SPREAD_BAIXA",
        legs=[buy_leg, sell_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=buy_leg.dte,
        expiry=buy_leg.expiry,
        net_cost=round(debit, 2),
        max_profit=round(max_p, 2),
        max_loss=round(debit, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view=f"Queda moderada abaixo de {sell_leg.strike:.2f}",
        best_scenario=f"Ativo abaixo de {sell_leg.strike:.2f} no vencimento",
        worst_scenario=f"Ativo acima de {buy_leg.strike:.2f} → perde R${debit:.0f}",
        entry_condition="Tendência de queda, RSI < 50, ativo abaixo das médias",
        exit_condition=f"Saída se ativo rompe resistência ou cai para {sell_leg.strike:.2f}",
        risk_observation="Risco limitado ao débito pago. Ideal para queda moderada.",
        risk_category="BAIXO",
        suitability="DIRECIONAL_BAIXA",
    )


def bear_call_spread(sell_leg: Leg, buy_leg: Leg,
                     underlying: str, stock_price: float) -> StrategyPayoff:
    """Trava de Baixa com CALL (crédito): vende K1 CALL, compra K2 CALL (K1 < K2)."""
    credit = (sell_leg.price - buy_leg.price) * CONTRACT_SIZE
    width = (buy_leg.strike - sell_leg.strike) * CONTRACT_SIZE
    max_loss = width - credit
    be = round(sell_leg.strike + (sell_leg.price - buy_leg.price), 2)
    return StrategyPayoff(
        name="Trava de Baixa com CALL (Bear Call Spread)",
        strategy_type="SPREAD_BAIXA",
        legs=[sell_leg, buy_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=sell_leg.dte,
        expiry=sell_leg.expiry,
        net_cost=round(-credit, 2),
        max_profit=round(credit, 2),
        max_loss=round(max_loss, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=True,
        market_view=f"Lateral ou queda — ativo abaixo de {sell_leg.strike:.2f}",
        best_scenario=f"Ativo fecha abaixo de {sell_leg.strike:.2f} → retém crédito R${credit:.0f}",
        worst_scenario=f"Ativo acima de {buy_leg.strike:.2f} → perde R${max_loss:.0f}",
        entry_condition="Resistência clara, tendência lateral/baixa, IV alta",
        exit_condition="Recompra se crédito = 80% ganho ou stop 2x crédito",
        risk_observation="⚠️ Exige margem. Risco máximo definido pela trava.",
        risk_category="MODERADO",
        suitability="DIRECIONAL_BAIXA",
    )


def bull_put_spread(sell_leg: Leg, buy_leg: Leg,
                    underlying: str, stock_price: float) -> StrategyPayoff:
    """Trava de Alta com PUT (crédito): vende K2 PUT, compra K1 PUT (K1 < K2)."""
    credit = (sell_leg.price - buy_leg.price) * CONTRACT_SIZE
    width = (sell_leg.strike - buy_leg.strike) * CONTRACT_SIZE
    max_loss = width - credit
    be = round(sell_leg.strike - (sell_leg.price - buy_leg.price), 2)
    return StrategyPayoff(
        name="Trava de Alta com PUT (Bull Put Spread)",
        strategy_type="SPREAD_ALTA",
        legs=[sell_leg, buy_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=sell_leg.dte,
        expiry=sell_leg.expiry,
        net_cost=round(-credit, 2),
        max_profit=round(credit, 2),
        max_loss=round(max_loss, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=True,
        market_view=f"Lateral ou alta — ativo acima de {sell_leg.strike:.2f}",
        best_scenario=f"Ativo fecha acima de {sell_leg.strike:.2f} → retém crédito R${credit:.0f}",
        worst_scenario=f"Ativo abaixo de {buy_leg.strike:.2f} → perde R${max_loss:.0f}",
        entry_condition="Suporte claro, tendência alta ou lateral, IV elevada",
        exit_condition="Recompra se crédito = 80% ganho ou stop 2x crédito",
        risk_observation="⚠️ Exige margem. Risco máximo definido pela trava.",
        risk_category="MODERADO",
        suitability="DIRECIONAL_ALTA",
    )


def iron_condor(
    sell_put: Leg, buy_put: Leg,
    sell_call: Leg, buy_call: Leg,
    underlying: str, stock_price: float,
) -> StrategyPayoff:
    """
    Iron Condor: Bull Put Spread + Bear Call Spread.
    Crédito recebido = soma dos dois spreads.
    """
    put_credit = (sell_put.price - buy_put.price)
    call_credit = (sell_call.price - buy_call.price)
    total_credit = (put_credit + call_credit) * CONTRACT_SIZE
    put_width = (sell_put.strike - buy_put.strike) * CONTRACT_SIZE
    call_width = (buy_call.strike - sell_call.strike) * CONTRACT_SIZE
    max_loss = max(put_width, call_width) - total_credit
    lower_be = round(sell_put.strike - put_credit - call_credit, 2)
    upper_be = round(sell_call.strike + put_credit + call_credit, 2)
    return StrategyPayoff(
        name="Iron Condor",
        strategy_type="CONDOR",
        legs=[sell_put, buy_put, sell_call, buy_call],
        underlying=underlying,
        stock_price=stock_price,
        dte=sell_put.dte,
        expiry=sell_put.expiry,
        net_cost=round(-total_credit, 2),
        max_profit=round(total_credit, 2),
        max_loss=round(max_loss, 2),
        breakevens=[lower_be, upper_be],
        risk_level="DEFINIDO",
        requires_margin=True,
        market_view=f"Lateral entre {sell_put.strike:.2f} e {sell_call.strike:.2f}",
        best_scenario=(f"Ativo entre {sell_put.strike:.2f} e {sell_call.strike:.2f} "
                       f"→ retém R${total_credit:.0f}"),
        worst_scenario="Ativo rompe qualquer uma das travas → perda máxima",
        entry_condition="Mercado lateral, IV elevada, ativo dentro do range",
        exit_condition=f"Recompra se 50% do crédito ganho. Stop se ativo sair do range.",
        risk_observation="⚠️ Exige margem. Monitorar rompimentos do range.",
        risk_category="MODERADO",
        suitability="LATERAL",
    )


def butterfly_calls(
    buy_low: Leg, sell_mid1: Leg, sell_mid2: Leg, buy_high: Leg,
    underlying: str, stock_price: float,
) -> StrategyPayoff:
    """Butterfly com CALLs: compra K1, vende 2x K2, compra K3."""
    debit = (buy_low.price - sell_mid1.price - sell_mid2.price + buy_high.price) * CONTRACT_SIZE
    wing = (sell_mid1.strike - buy_low.strike)
    max_p = (wing - debit / CONTRACT_SIZE) * CONTRACT_SIZE
    lower_be = round(buy_low.strike + debit / CONTRACT_SIZE, 2)
    upper_be = round(buy_high.strike - debit / CONTRACT_SIZE, 2)
    return StrategyPayoff(
        name="Butterfly (Calls)",
        strategy_type="BUTTERFLY",
        legs=[buy_low, sell_mid1, sell_mid2, buy_high],
        underlying=underlying,
        stock_price=stock_price,
        dte=buy_low.dte,
        expiry=buy_low.expiry,
        net_cost=round(debit, 2),
        max_profit=round(max_p, 2),
        max_loss=round(debit, 2),
        breakevens=[lower_be, upper_be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view=f"Ativo pina em {sell_mid1.strike:.2f} no vencimento",
        best_scenario=f"Ativo fecha exatamente em {sell_mid1.strike:.2f}",
        worst_scenario="Ativo longe do strike central → perde débito",
        entry_condition="Mercado lateral, IV alta, ativo perto do strike central",
        exit_condition="Saída com 50% do ganho máximo ou 2 semanas antes do vencimento",
        risk_observation="Custo baixo, ganho concentrado. Difícil de acertar o pin.",
        risk_category="BAIXO",
        suitability="LATERAL",
    )


def butterfly_puts(
    buy_high: Leg, sell_mid1: Leg, sell_mid2: Leg, buy_low: Leg,
    underlying: str, stock_price: float,
) -> StrategyPayoff:
    """Butterfly com PUTs: compra K3 PUT, vende 2x K2 PUT, compra K1 PUT."""
    debit = (buy_high.price - sell_mid1.price - sell_mid2.price + buy_low.price) * CONTRACT_SIZE
    wing = (buy_high.strike - sell_mid1.strike)
    max_p = (wing - debit / CONTRACT_SIZE) * CONTRACT_SIZE
    lower_be = round(buy_low.strike + debit / CONTRACT_SIZE, 2)
    upper_be = round(buy_high.strike - debit / CONTRACT_SIZE, 2)
    return StrategyPayoff(
        name="Butterfly (Puts)",
        strategy_type="BUTTERFLY",
        legs=[buy_high, sell_mid1, sell_mid2, buy_low],
        underlying=underlying,
        stock_price=stock_price,
        dte=buy_high.dte,
        expiry=buy_high.expiry,
        net_cost=round(debit, 2),
        max_profit=round(max_p, 2),
        max_loss=round(debit, 2),
        breakevens=[lower_be, upper_be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view=f"Ativo pina em {sell_mid1.strike:.2f} no vencimento",
        best_scenario=f"Ativo fecha em {sell_mid1.strike:.2f}",
        worst_scenario="Ativo longe do strike central → perde débito",
        entry_condition="Mesmo da butterfly com calls",
        exit_condition="Saída com 50% do ganho ou 2 semanas antes do vencimento",
        risk_observation="Custo baixo, ganho concentrado. Difícil de acertar o pin.",
        risk_category="BAIXO",
        suitability="LATERAL",
    )


def straddle(call_leg: Leg, put_leg: Leg,
             underlying: str, stock_price: float) -> StrategyPayoff:
    """Long Straddle: compra ATM CALL + ATM PUT (mesmo strike)."""
    debit = (call_leg.price + put_leg.price) * CONTRACT_SIZE
    K = call_leg.strike
    max_loss_downside = (K - call_leg.price - put_leg.price) * CONTRACT_SIZE
    lower_be = round(K - (call_leg.price + put_leg.price), 2)
    upper_be = round(K + (call_leg.price + put_leg.price), 2)
    return StrategyPayoff(
        name="Long Straddle",
        strategy_type="VOLATILIDADE",
        legs=[call_leg, put_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=call_leg.dte,
        expiry=call_leg.expiry,
        net_cost=round(debit, 2),
        max_profit=float("inf"),
        max_loss=round(debit, 2),
        breakevens=[lower_be, upper_be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Grande movimento esperado em qualquer direção",
        best_scenario=f"Ativo acima de {upper_be:.2f} ou abaixo de {lower_be:.2f}",
        worst_scenario=f"Ativo fecha em {K:.2f} → perde R${debit:.0f}",
        entry_condition="Antes de evento (resultado, macro), IV baixa, ativo comprimido",
        exit_condition="Saída se IV explodir ou ativo se mover >10% do strike",
        risk_observation="Decaimento temporal intenso. Ideal comprar com IV baixa.",
        risk_category="MODERADO",
        suitability="VOLATILIDADE_ALTA",
    )


def strangle(call_leg: Leg, put_leg: Leg,
             underlying: str, stock_price: float) -> StrategyPayoff:
    """Long Strangle: compra OTM CALL + OTM PUT (strikes diferentes)."""
    debit = (call_leg.price + put_leg.price) * CONTRACT_SIZE
    lower_be = round(put_leg.strike - (call_leg.price + put_leg.price), 2)
    upper_be = round(call_leg.strike + (call_leg.price + put_leg.price), 2)
    return StrategyPayoff(
        name="Long Strangle",
        strategy_type="VOLATILIDADE",
        legs=[call_leg, put_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=call_leg.dte,
        expiry=call_leg.expiry,
        net_cost=round(debit, 2),
        max_profit=float("inf"),
        max_loss=round(debit, 2),
        breakevens=[lower_be, upper_be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Grande movimento esperado, mas mais barato que straddle",
        best_scenario=f"Ativo acima de {upper_be:.2f} ou abaixo de {lower_be:.2f}",
        worst_scenario="Ativo fica entre os strikes → perde todo o prêmio",
        entry_condition="IV baixa, evento esperado, ativo em compressão",
        exit_condition="Saída se IV explodir ou ativo romper um dos breakevens",
        risk_observation="Precisa de movimento maior que o straddle para lucrar.",
        risk_category="MODERADO",
        suitability="VOLATILIDADE_ALTA",
    )


def covered_call(stock_price: float, call_leg: Leg,
                 underlying: str) -> StrategyPayoff:
    """Covered Call: possui ação + vende CALL OTM."""
    net_cost = (stock_price - call_leg.price) * CONTRACT_SIZE
    max_p = (call_leg.strike - stock_price + call_leg.price) * CONTRACT_SIZE
    max_loss = net_cost  # ação vai a zero
    be = round(stock_price - call_leg.price, 2)
    # cria perna de ação para o payoff
    stock_leg = Leg("ACAO", "STOCK", "BUY", 0, call_leg.expiry, call_leg.dte,
                    stock_price, 1, 0, 0, 1.0)
    return StrategyPayoff(
        name="Covered Call",
        strategy_type="RENDA",
        legs=[stock_leg, call_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=call_leg.dte,
        expiry=call_leg.expiry,
        net_cost=round(net_cost, 2),
        max_profit=round(max_p, 2),
        max_loss=round(max_loss, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view=f"Ação lateral ou leve alta até {call_leg.strike:.2f}",
        best_scenario=f"Ativo fecha em {call_leg.strike:.2f} → ganho R${max_p:.0f}",
        worst_scenario="Ativo despenca → protegido apenas pelo prêmio da call",
        entry_condition="Já possui ação em carteira, mercado lateral, IV elevada",
        exit_condition="Recompra a call se 80% do crédito já ganho",
        risk_observation="Limita upside. Posição em ações não protegida de queda.",
        risk_category="BAIXO",
        suitability="RENDA_COM_CARTEIRA",
    )


def collar(stock_price: float, put_leg: Leg, call_leg: Leg,
           underlying: str) -> StrategyPayoff:
    """Collar: possui ação + compra PUT + vende CALL."""
    hedge_cost = (put_leg.price - call_leg.price) * CONTRACT_SIZE
    max_p = (call_leg.strike - stock_price - put_leg.price + call_leg.price) * CONTRACT_SIZE
    max_loss = (stock_price - put_leg.strike + put_leg.price - call_leg.price) * CONTRACT_SIZE
    be = round(stock_price + put_leg.price - call_leg.price, 2)
    stock_leg = Leg("ACAO", "STOCK", "BUY", 0, put_leg.expiry, put_leg.dte,
                    stock_price, 1, 0, 0, 1.0)
    return StrategyPayoff(
        name="Collar",
        strategy_type="PROTECAO",
        legs=[stock_leg, put_leg, call_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=put_leg.dte,
        expiry=put_leg.expiry,
        net_cost=round(hedge_cost, 2),
        max_profit=round(max_p, 2),
        max_loss=round(max_loss, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Proteção de carteira com custo reduzido",
        best_scenario=f"Ativo sobe para {call_leg.strike:.2f} → ganho R${max_p:.0f}",
        worst_scenario=f"Ativo cai para {put_leg.strike:.2f} → perde R${max_loss:.0f}",
        entry_condition="Possui ação, mercado incerto, quer proteção com baixo custo",
        exit_condition="Fecha se tese de alta se confirmar ou antes do vencimento",
        risk_observation="Barato ou sem custo se put ≈ call. Limita ganho e perda.",
        risk_category="BAIXO",
        suitability="PROTECAO",
    )


def protective_put(stock_price: float, put_leg: Leg,
                   underlying: str) -> StrategyPayoff:
    """Protective Put: possui ação + compra PUT (seguro)."""
    net_cost = (stock_price + put_leg.price) * CONTRACT_SIZE
    max_p = float("inf")
    max_loss = (stock_price - put_leg.strike + put_leg.price) * CONTRACT_SIZE
    be = round(stock_price + put_leg.price, 2)
    stock_leg = Leg("ACAO", "STOCK", "BUY", 0, put_leg.expiry, put_leg.dte,
                    stock_price, 1, 0, 0, 1.0)
    return StrategyPayoff(
        name="Protective Put",
        strategy_type="PROTECAO",
        legs=[stock_leg, put_leg],
        underlying=underlying,
        stock_price=stock_price,
        dte=put_leg.dte,
        expiry=put_leg.expiry,
        net_cost=round(net_cost, 2),
        max_profit=max_p,
        max_loss=round(max_loss, 2),
        breakevens=[be],
        risk_level="DEFINIDO",
        requires_margin=False,
        market_view="Proteção total de posição comprada em ação",
        best_scenario="Ativo sobe → put expira sem valor, ação valoriza",
        worst_scenario=f"Ativo cai → PUT limita perda em R${max_loss:.0f}",
        entry_condition="Possui ação e quer proteção total contra queda",
        exit_condition="Fecha a put se tese de alta se confirmar",
        risk_observation="Custo da proteção reduz retorno. Similar a um seguro.",
        risk_category="BAIXO",
        suitability="PROTECAO",
    )


# ---------------------------------------------------------------------------
# Validação matemática de payoff
# ---------------------------------------------------------------------------

def validate_strategy_payoff(payoff: StrategyPayoff) -> dict:
    """
    Valida matematicamente o payoff de uma estratégia.

    Regras verificadas:
      1. net_cost não pode ser NaN ou infinito
      2. max_profit deve ser > 0 ou infinito
      3. max_loss deve ser > 0 (positivo = perda) ou infinito
      4. Para débito: max_loss deve ≈ net_cost (±1%)
      5. Para spreads de débito: max_profit + max_loss > 0 (width positiva)
      6. risk_reward deve ser ≥ 0
      7. Breakevens devem existir
      8. Pernas de opção no mesmo spread devem ter o mesmo vencimento
      9. Venda descoberta sem hedge deve ter requires_margin=True

    Retorna dict com:
      ok     (bool)       — True se nenhum erro crítico
      erros  (list[str])  — erros que invalidam a estrutura
      alertas(list[str])  — avisos não bloqueantes
    """
    erros: list[str] = []
    alertas: list[str] = []

    # 1. net_cost não pode ser NaN ou inf
    if math.isnan(payoff.net_cost) or math.isinf(payoff.net_cost):
        erros.append(f"net_cost é NaN ou infinito: {payoff.net_cost}")

    # 2. max_profit deve ser > 0 ou inf
    if not math.isinf(payoff.max_profit) and payoff.max_profit <= 0:
        erros.append(f"max_profit inválido: {payoff.max_profit}")

    # 3. max_loss deve ser > 0 (positivo = perda) ou inf
    if not math.isinf(payoff.max_loss) and payoff.max_loss <= 0:
        erros.append(f"max_loss inválido: {payoff.max_loss}")

    # 4. Para estruturas de débito: max_loss deve ≈ net_cost
    if payoff.net_cost > 0 and not math.isnan(payoff.net_cost):  # débito
        if not math.isinf(payoff.max_loss):
            if not math.isclose(payoff.max_loss, payoff.net_cost, rel_tol=0.01):
                if payoff.strategy_type in ("SPREAD_ALTA", "SPREAD_BAIXA", "DIRECIONAL", "BUTTERFLY"):
                    erros.append(
                        f"Débito ({payoff.net_cost:.2f}) ≠ max_loss ({payoff.max_loss:.2f}) "
                        f"— divergência > 1% em estrutura de risco definido"
                    )

    # 5. Para spreads de débito: max_profit + max_loss deve ser > 0 (width)
    if payoff.strategy_type in ("SPREAD_ALTA", "SPREAD_BAIXA") and payoff.net_cost > 0:
        if not math.isinf(payoff.max_profit) and not math.isinf(payoff.max_loss):
            total = payoff.max_profit + payoff.max_loss
            if total <= 0:
                erros.append(
                    f"max_profit + max_loss = {total:.2f} (esperado > 0 — verifica strikes)"
                )

    # 6. risk_reward deve ser ≥ 0
    rr = payoff.risk_reward
    if not math.isinf(rr) and rr < 0:
        erros.append(f"risk_reward negativo: {rr:.4f}")

    # 7. Breakevens devem existir
    if not payoff.breakevens:
        alertas.append("Sem breakevens calculados")

    # 8. Vencimentos das pernas de opção devem ser iguais em spreads
    option_legs = [l for l in payoff.legs if l.option_type in ("CALL", "PUT")]
    if len(option_legs) >= 2:
        expiries = {l.expiry for l in option_legs}
        if len(expiries) > 1:
            erros.append(f"Pernas com vencimentos diferentes: {expiries}")

    # 9. Venda descoberta sem perna comprada do mesmo tipo deve ter requires_margin=True
    sell_legs = [l for l in option_legs if l.direction == "SELL"]
    buy_legs  = [l for l in option_legs if l.direction == "BUY"]
    if sell_legs and not buy_legs and not payoff.requires_margin:
        alertas.append(
            "Venda sem hedge detectada — requires_margin deveria ser True"
        )

    return {
        "ok":      len(erros) == 0,
        "erros":   erros,
        "alertas": alertas,
    }
