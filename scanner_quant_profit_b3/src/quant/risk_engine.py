"""
Risk Engine — Quant Research Layer.

Controla todos os limites operacionais antes de emitir um sinal:
  - risco fixo por trade (% do capital)
  - risco ajustado por volatilidade (vol-targeting)
  - limite diário de perda
  - limite semanal de perda
  - concentração por ativo
  - concentração por vencimento
  - concentração por tipo de opção
  - máximo de posições abertas

Retorna RiskVerdict com aprovação, alertas e bloqueios.
Nunca bloqueia sozinho — a decisão final é sempre do operador.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

@dataclass
class RiskConfig:
    risk_pct_per_trade: float = 0.005       # % capital por operação
    max_risk_abs_per_trade: float = 500.0   # teto absoluto (R$)
    use_vol_adjusted_risk: bool = False
    vol_target: float = 0.25               # volatilidade alvo para scaling
    daily_loss_limit: float = 0.02          # máx perda diária (% capital)
    weekly_loss_limit: float = 0.04         # máx perda semanal (% capital)
    max_risk_per_asset: float = 0.02        # máx risco por ativo (% capital)
    max_trades_same_expiry: int = 2
    max_trades_same_type: int = 3
    max_open_positions: int = 5


@dataclass
class RiskState:
    capital: float = 10_000.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    open_positions: list[dict] = field(default_factory=list)
    # Cada posição: {"underlying": str, "expiry": str, "type": str, "risk": float}


# ---------------------------------------------------------------------------
# Veredito
# ---------------------------------------------------------------------------

@dataclass
class RiskVerdict:
    approved: bool
    risk_amount: float
    contracts: int
    warnings: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)

    @property
    def verdict_str(self) -> str:
        if not self.approved:
            return "🚫 BLOQUEADO"
        if self.warnings:
            return "⚠️  APROVADO C/ ALERTAS"
        return "✅ APROVADO"

    def print_verdict(self) -> None:
        print(f"\n  Risk Engine: {self.verdict_str}")
        print(f"  Risco calculado: R$ {self.risk_amount:.2f}  |  Contratos: {self.contracts}")
        for w in self.warnings:
            print(f"  ⚠️  {w}")
        for b in self.blocks:
            print(f"  🚫 {b}")


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------

class RiskEngine:

    def __init__(self, config: RiskConfig, state: RiskState):
        self.cfg = config
        self.state = state

    def compute_trade_risk(self, hist_vol: float = 0.0) -> float:
        """Calcula o valor monetário a arriscar no trade."""
        base = self.state.capital * self.cfg.risk_pct_per_trade
        if self.cfg.use_vol_adjusted_risk and hist_vol > 0 and self.cfg.vol_target > 0:
            # vol-targeting: reduz risco quando vol está alta, aumenta quando está baixa
            scale = min(max(self.cfg.vol_target / hist_vol, 0.5), 2.0)
            base *= scale
        return round(min(base, self.cfg.max_risk_abs_per_trade), 2)

    def compute_contracts(
        self,
        entry: float,
        stop: float,
        contract_size: int = 100,
        hist_vol: float = 0.0,
    ) -> tuple[int, float]:
        """Retorna (n_contratos, risco_financeiro)."""
        risk_budget = self.compute_trade_risk(hist_vol)
        risk_per_contract = (entry - stop) * contract_size
        if risk_per_contract <= 0 or entry <= 0:
            return 0, 0.0
        contracts = max(int(risk_budget / risk_per_contract), 0)
        fin_risk = round(contracts * risk_per_contract, 2)
        return contracts, fin_risk

    def evaluate(
        self,
        underlying: str,
        option_type: str,
        expiry: str,
        entry: float,
        stop: float,
        contracts: int,
        hist_vol: float = 0.0,
        contract_size: int = 100,
    ) -> RiskVerdict:
        warnings: list[str] = []
        blocks: list[str] = []

        risk_amount = self.compute_trade_risk(hist_vol)
        actual_risk = max((entry - stop) * contracts * contract_size, 0.0) if contracts > 0 else 0.0

        # Limite diário
        daily_limit = self.state.capital * self.cfg.daily_loss_limit
        if self.state.daily_pnl < 0 and abs(self.state.daily_pnl) >= daily_limit:
            blocks.append(
                f"Limite diário: perda R$ {abs(self.state.daily_pnl):.2f} ≥ R$ {daily_limit:.2f}"
            )

        # Limite semanal
        weekly_limit = self.state.capital * self.cfg.weekly_loss_limit
        if self.state.weekly_pnl < 0 and abs(self.state.weekly_pnl) >= weekly_limit:
            blocks.append(
                f"Limite semanal: perda R$ {abs(self.state.weekly_pnl):.2f} ≥ R$ {weekly_limit:.2f}"
            )

        # Concentração por ativo
        asset_risk = sum(p["risk"] for p in self.state.open_positions if p.get("underlying") == underlying)
        max_asset = self.state.capital * self.cfg.max_risk_per_asset
        if asset_risk + actual_risk > max_asset:
            warnings.append(
                f"Concentração {underlying}: R$ {asset_risk + actual_risk:.2f} > limite R$ {max_asset:.2f}"
            )

        # Por vencimento
        n_expiry = sum(1 for p in self.state.open_positions if p.get("expiry") == expiry)
        if n_expiry >= self.cfg.max_trades_same_expiry:
            warnings.append(
                f"Vencimento {expiry}: {n_expiry} trades abertos (limite {self.cfg.max_trades_same_expiry})"
            )

        # Por tipo
        n_type = sum(1 for p in self.state.open_positions if p.get("type") == option_type)
        if n_type >= self.cfg.max_trades_same_type:
            warnings.append(
                f"{option_type}: {n_type} trades abertos (limite {self.cfg.max_trades_same_type})"
            )

        # Total de posições
        if len(self.state.open_positions) >= self.cfg.max_open_positions:
            blocks.append(
                f"Posições abertas: {len(self.state.open_positions)} (limite {self.cfg.max_open_positions})"
            )

        return RiskVerdict(
            approved=len(blocks) == 0,
            risk_amount=risk_amount,
            contracts=contracts,
            warnings=warnings,
            blocks=blocks,
        )

    def risk_summary(self) -> dict:
        """Resumo do estado atual de risco."""
        return {
            "capital": self.state.capital,
            "daily_pnl": self.state.daily_pnl,
            "weekly_pnl": self.state.weekly_pnl,
            "daily_pnl_pct": round(self.state.daily_pnl / self.state.capital * 100, 3),
            "weekly_pnl_pct": round(self.state.weekly_pnl / self.state.capital * 100, 3),
            "daily_limit_pct": self.cfg.daily_loss_limit * 100,
            "weekly_limit_pct": self.cfg.weekly_loss_limit * 100,
            "open_positions": len(self.state.open_positions),
            "max_open": self.cfg.max_open_positions,
            "daily_headroom": round(
                self.state.capital * self.cfg.daily_loss_limit + self.state.daily_pnl, 2
            ),
            "weekly_headroom": round(
                self.state.capital * self.cfg.weekly_loss_limit + self.state.weekly_pnl, 2
            ),
        }

    @classmethod
    def from_qcfg(cls, qcfg: dict, capital: Optional[float] = None) -> "RiskEngine":
        cap = capital or qcfg.get("capital_inicial", 10_000.0)
        cfg = RiskConfig(
            risk_pct_per_trade=qcfg.get("risco_por_trade", 0.005),
            max_risk_abs_per_trade=qcfg.get("max_risco_abs_por_trade", 500.0),
            use_vol_adjusted_risk=qcfg.get("risco_ajustado_vol", False),
            vol_target=qcfg.get("volatilidade_alvo", 0.25),
            daily_loss_limit=qcfg.get("limite_perda_diaria", 0.02),
            weekly_loss_limit=qcfg.get("limite_perda_semanal", 0.04),
            max_risk_per_asset=qcfg.get("max_risco_por_ativo", 0.02),
            max_trades_same_expiry=qcfg.get("max_trades_mesmo_vencimento", 2),
            max_trades_same_type=qcfg.get("max_trades_mesmo_tipo", 3),
            max_open_positions=qcfg.get("max_posicoes_abertas", 5),
        )
        return cls(cfg, RiskState(capital=cap))
