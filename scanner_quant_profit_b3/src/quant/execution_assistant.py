"""
Execution Assistant — Quant Research Layer.

Gera o plano operacional detalhado para cada setup aprovado.

⚠️  APENAS INFORMATIVO — NUNCA ENVIA ORDENS REAIS.
O operador recebe todas as informações necessárias para executar
manualmente na plataforma de sua preferência.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


# ---------------------------------------------------------------------------
# Plano operacional
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlan:
    # Identificação
    ticker: str
    underlying: str
    option_type: str
    trade_date: str
    expiration_date: str
    # Preços (R$)
    entry: float
    stop: float
    target_1: float
    target_2: float
    invalidation: float    # preço do ativo que invalida o setup
    # Tamanho
    contracts: int
    contract_size: int = 100
    risk_financial: float = 0.0
    # Classificação
    score: float = 0.0
    signal_type: str = "COMPRA"       # COMPRA / OBSERVAR / DESCARTAR
    confidence: str = "MEDIA"         # ALTA / MEDIA / BAIXA
    # Explicação
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: str = ""
    # Greeks
    delta: float = 0.0
    theta: float = 0.0
    vega: float = 0.0

    @property
    def payoff_ratio(self) -> float:
        risk = self.entry - self.stop
        reward = self.target_1 - self.entry
        return round(reward / risk, 2) if risk > 0 else 0.0

    @property
    def stop_pct(self) -> float:
        return round((1.0 - self.stop / self.entry) * 100, 1) if self.entry > 0 else 0.0

    @property
    def target1_pct(self) -> float:
        return round((self.target_1 / self.entry - 1.0) * 100, 1) if self.entry > 0 else 0.0

    @property
    def target2_pct(self) -> float:
        return round((self.target_2 / self.entry - 1.0) * 100, 1) if self.entry > 0 else 0.0

    def to_terminal(self) -> str:
        sep = "=" * 72
        lines = [
            "",
            sep,
            f"  PLANO OPERACIONAL  |  {self.ticker} ({self.underlying} · {self.option_type})",
            sep,
            f"  Sinal:       {self.signal_type}  |  Score: {self.score:.1f}/100  |  Confiança: {self.confidence}",
            f"  Vencimento:  {self.expiration_date}  |  Data:  {self.trade_date}",
            "",
            f"  ENTRADA:       R$ {self.entry:.4f}",
            f"  STOP:          R$ {self.stop:.4f}   ({self.stop_pct:.1f}% de perda no prêmio)",
            f"  ALVO 1:        R$ {self.target_1:.4f}   (+{self.target1_pct:.1f}%)",
            f"  ALVO 2:        R$ {self.target_2:.4f}   (+{self.target2_pct:.1f}%)",
            f"  INVALIDAÇÃO:   Ativo cai abaixo de R$ {self.invalidation:.2f}",
            "",
            f"  TAMANHO:       {self.contracts} contratos × {self.contract_size} ações",
            f"  RISCO:         R$ {self.risk_financial:.2f}",
            f"  PAYOFF:        {self.payoff_ratio:.1f}x",
            "",
            f"  Greeks:  Delta {self.delta:.3f}  |  Theta/dia {self.theta:.4f}  |  Vega {self.vega:.4f}",
        ]
        if self.reasons_for:
            lines += ["", "  ✅ Favoráveis:"]
            lines += [f"     • {r}" for r in self.reasons_for]
        if self.reasons_against:
            lines += ["", "  ⚠️  Contrários:"]
            lines += [f"     • {r}" for r in self.reasons_against]
        if self.warnings:
            lines += ["", "  🔔 Alertas de Risco:"]
            lines += [f"     • {w}" for w in self.warnings]
        if self.notes:
            lines += ["", f"  📝 Notas: {self.notes}"]
        lines += [
            "",
            "  ⚠️  DECISÃO E EXECUÇÃO SÃO EXCLUSIVAMENTE DO OPERADOR",
            sep,
            "",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "underlying": self.underlying,
            "option_type": self.option_type,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "score": self.score,
            "entry": self.entry,
            "stop": self.stop,
            "stop_pct": self.stop_pct,
            "target_1": self.target_1,
            "target1_pct": self.target1_pct,
            "target_2": self.target_2,
            "target2_pct": self.target2_pct,
            "invalidation": self.invalidation,
            "contracts": self.contracts,
            "risk_financial": self.risk_financial,
            "payoff_ratio": self.payoff_ratio,
            "delta": self.delta,
            "theta": self.theta,
            "vega": self.vega,
            "reasons_for": " | ".join(self.reasons_for),
            "reasons_against": " | ".join(self.reasons_against),
            "warnings": " | ".join(self.warnings),
            "trade_date": self.trade_date,
            "expiration_date": self.expiration_date,
        }


# ---------------------------------------------------------------------------
# Construção do plano
# ---------------------------------------------------------------------------

def _build_reasons(row: pd.Series) -> tuple[list[str], list[str]]:
    reasons_for: list[str] = []
    reasons_against: list[str] = []

    trend = str(row.get("trend", ""))
    momentum = str(row.get("momentum_condition", ""))
    vol_cond = str(row.get("volume_condition", ""))
    moneyness = str(row.get("moneyness", ""))
    rsi = float(row.get("rsi", 50) or 50)
    hv = float(row.get("hist_vol_pct", 0) or 0)
    vol_ratio = float(row.get("volume_ratio", 1) or 1)
    dte = int(row.get("dte", 0) or 0)

    # Favoráveis
    if "ALTA" in trend:
        reasons_for.append(f"Tendência {trend} — SMA rápida acima da lenta")
    if momentum in ("FORTE", "POSITIVO"):
        reasons_for.append(f"RSI {rsi:.1f} — Momentum {momentum}")
    if vol_cond in ("EXPLOSIVO", "MUITO_ALTO", "ALTO"):
        reasons_for.append(f"Volume {vol_cond} ({vol_ratio:.1f}x a média)")
    if moneyness == "ATM":
        reasons_for.append("Moneyness ATM — melhor perfil risco/retorno para CALL")
    if 20 <= dte <= 35:
        reasons_for.append(f"DTE {dte}d — zona ideal de theta/gamma")

    # Contrários
    if "BAIXO" in vol_cond:
        reasons_against.append(f"Volume abaixo da média ({vol_ratio:.1f}x)")
    if hv > 55:
        reasons_against.append(f"Volatilidade muito alta ({hv:.1f}%) — prêmio possivelmente caro")
    if hv < 10:
        reasons_against.append(f"Volatilidade muito baixa ({hv:.1f}%) — prêmio sem valor temporal")
    if dte < 10:
        reasons_against.append(f"DTE muito curto ({dte}d) — risco de theta acelerado")
    if dte > 50:
        reasons_against.append(f"DTE longo ({dte}d) — capital imobilizado por mais tempo")

    return reasons_for, reasons_against


def build_execution_plan(
    setup_row: pd.Series,
    risk_warnings: list[str] | None = None,
    invalidation_pct: float = 0.03,
) -> ExecutionPlan:
    """
    Constrói o plano operacional a partir de uma linha de setup do scanner.
    """
    entry = float(setup_row.get("entrada_planejada", setup_row.get("preco_opcao", 0)) or 0)
    ativo_close = float(setup_row.get("preco_ativo", 0) or 0)
    invalidation = round(ativo_close * (1.0 - invalidation_pct), 2) if ativo_close > 0 else 0.0

    score = float(setup_row.get("final_score", 0) or 0)
    status = str(setup_row.get("status", "INVALIDADO"))

    if status == "ENTRADA_VALIDADA":
        signal_type = "COMPRA"
        confidence = "ALTA" if score >= 80 else "MEDIA"
    elif status == "AGUARDAR_GATILHO":
        signal_type = "OBSERVAR"
        confidence = "MEDIA" if score >= 60 else "BAIXA"
    else:
        signal_type = "DESCARTAR"
        confidence = "BAIXA"

    reasons_for, reasons_against = _build_reasons(setup_row)

    return ExecutionPlan(
        ticker=str(setup_row.get("ticker", "")),
        underlying=str(setup_row.get("underlying", "")),
        option_type=str(setup_row.get("option_type", "CALL")),
        trade_date=str(setup_row.get("trade_date", "")),
        expiration_date=str(setup_row.get("expiration_date", "")),
        entry=entry,
        stop=float(setup_row.get("stop", 0) or 0),
        target_1=float(setup_row.get("alvo_1", 0) or 0),
        target_2=float(setup_row.get("alvo_2", 0) or 0),
        invalidation=invalidation,
        contracts=int(setup_row.get("contratos", 0) or 0),
        contract_size=100,
        risk_financial=float(setup_row.get("risco_financeiro", 0) or 0),
        score=score,
        signal_type=signal_type,
        confidence=confidence,
        reasons_for=reasons_for,
        reasons_against=reasons_against,
        warnings=risk_warnings or [],
        notes=str(setup_row.get("motivo", "")),
        delta=float(setup_row.get("delta", 0) or 0),
        theta=float(setup_row.get("theta", 0) or 0),
        vega=float(setup_row.get("vega", 0) or 0),
    )


def generate_execution_plans(df: pd.DataFrame) -> list[ExecutionPlan]:
    """Gera planos para todos os setups ENTRADA_VALIDADA e AGUARDAR_GATILHO."""
    if df.empty:
        return []
    active = {"ENTRADA_VALIDADA", "AGUARDAR_GATILHO"}
    return [
        build_execution_plan(row)
        for _, row in df.iterrows()
        if row.get("status") in active
    ]


def plans_to_df(plans: list[ExecutionPlan]) -> pd.DataFrame:
    """Converte lista de planos em DataFrame."""
    return pd.DataFrame([p.to_dict() for p in plans]) if plans else pd.DataFrame()
