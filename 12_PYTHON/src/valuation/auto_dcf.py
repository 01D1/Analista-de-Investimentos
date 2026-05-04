"""
auto_dcf.py
-----------
Valuation automático com premissas carregadas de config/sectors.yaml.

Metodologias por setor:
  gordon_growth    — bancos, holdings financeiras
                     P/B implícito = (ROE − g) / (COE − g)
  ddm              — utilities, dividendos regulados
                     Fair Value = DPS / (COE − g)
  dcf_fcff         — industriais, retail, saúde, tech, agro
                     FCFF descontado ao WACC, valor terminal Gordon
  ev_ebitda_multiple — oil_gas, mineração, telecom, real_estate
                       EV = EBITDA × múltiplo alvo; bridge → equity

Cenários: base / optimistic / pessimistic
Tudo configurável via config/sectors.yaml — sem hardcode.

Uso:
    from src.valuation.auto_dcf import run_valuation

    result = run_valuation("BBAS3")   # Gordon Growth
    result = run_valuation("WEGE3")   # DCF FCFF
    result = run_valuation("PETR4")   # EV/EBITDA
    print(result.summary())
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.utils.logger import get_logger
from src.valuation.sector_config import SectorConfig

log = get_logger(__name__)


def _ensure_src_path() -> None:
    src = str(Path(__file__).parent.parent)
    if src not in sys.path:
        sys.path.insert(0, src)


# ── Resultado ─────────────────────────────────────────────────────────────────


@dataclass
class ScenarioResult:
    scenario: str
    fair_value: float  # equity value em R$ milhões
    current_price: float | None
    upside: float | None  # relativo ao preço de mercado (se disponível)
    method: str
    assumptions: dict = field(default_factory=dict)

    @property
    def recommendation(self) -> str:
        if self.upside is None:
            return "N/D"
        if self.upside > 0.30:
            return "COMPRA FORTE"
        if self.upside > 0.10:
            return "COMPRA"
        if self.upside > -0.05:
            return "NEUTRO"
        if self.upside > -0.20:
            return "VENDA MODERADA"
        return "VENDA"


@dataclass
class ValuationResult:
    ticker: str
    sector_type: str
    base_year: int
    method: str
    scenarios: dict[str, ScenarioResult] = field(default_factory=dict)
    calculated_at: str = field(default_factory=lambda: str(date.today()))

    def summary(self) -> str:
        lines = [
            f"=== Valuation {self.ticker} [{self.sector_type}] "
            f"(base {self.base_year}) — {self.method} ==="
        ]
        for name, s in self.scenarios.items():
            upside_str = f"{s.upside:+.1%}" if s.upside is not None else "N/D"
            lines.append(
                f"  {name:<12} R$ {s.fair_value:>12,.1f} mi  ({upside_str})  → {s.recommendation}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "sector_type": self.sector_type,
            "base_year": self.base_year,
            "method": self.method,
            "calculated_at": self.calculated_at,
            "scenarios": {
                name: {
                    "fair_value": s.fair_value,
                    "current_price": s.current_price,
                    "upside": s.upside,
                    "recommendation": s.recommendation,
                    "assumptions": s.assumptions,
                }
                for name, s in self.scenarios.items()
            },
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class AutoDCF:
    """
    Valuation automático guiado por config/sectors.yaml.

    Fluxo:
      1. Identifica setor via SectorConfig.for_ticker()
      2. Carrega métricas processadas + demonstrações brutas
      3. Roteia para o método de valuation correto
      4. Calcula 3 cenários
      5. Persiste em data/output/{ticker}/valuation.json
    """

    def __init__(self, output_dir: Path | None = None):
        from config.settings import settings

        self.output_dir = output_dir or settings.data_output

    def run(self, ticker: str, force: bool = False) -> ValuationResult | None:
        output_path = self.output_dir / ticker / "valuation.json"
        if output_path.exists() and not force:
            try:
                data = json.loads(output_path.read_text())
                log.info(f"[{ticker}] valuation carregado do cache")
                return self._from_cache(data)
            except Exception:
                pass

        cfg = SectorConfig.for_ticker(ticker)
        metrics = self._load_latest_metrics(ticker)
        if not metrics:
            log.warning(f"[{ticker}] sem métricas — execute 'analyze' primeiro")
            return None

        # Enriquece métricas com dados brutos do balanço
        base_year = int(metrics.get("year", date.today().year - 1))
        raw = self._load_raw_statements(ticker, base_year)
        if raw:
            self._enrich_with_raw(metrics, raw)

        current_price = metrics.get("market_price")

        log.info(
            f"[{ticker}] setor={cfg.sector_type}  "
            f"método={cfg.valuation_method}  "
            f"modelo={cfg.financial_model}"
        )

        method = cfg.valuation_method
        if method == "gordon_growth":
            result = self._gordon_growth(ticker, base_year, metrics, cfg, current_price)
        elif method == "ddm":
            result = self._ddm(ticker, base_year, metrics, cfg, current_price)
        elif method == "ev_ebitda_multiple":
            result = self._ev_ebitda(ticker, base_year, metrics, cfg, current_price)
        else:  # dcf_fcff (default)
            result = self._dcf_fcff(ticker, base_year, metrics, cfg, current_price)

        if result:
            self._save(result, output_path)
            log.success(
                f"[{ticker}] valuation concluído — "
                f"{result.method} | base={result.scenarios.get('base', None) and result.scenarios['base'].fair_value:,.0f} R$ mi"
            )
        return result

    # ── Gordon Growth (bancos / holdings) ─────────────────────────────────────

    def _gordon_growth(
        self,
        ticker: str,
        base_year: int,
        metrics: dict,
        cfg: SectorConfig,
        current_price: float | None,
    ) -> ValuationResult:
        roe = metrics.get("roe") or 0.12
        se = metrics.get("shareholders_equity") or 0
        scenarios = cfg.build_gordon_scenarios(roe)
        result = ValuationResult(
            ticker=ticker,
            sector_type=cfg.sector_type,
            base_year=base_year,
            method="Gordon Growth Model (P/B Implícito)",
        )

        for name, params in scenarios.items():
            coe, g = params["coe"], params["g"]
            if coe <= g:
                g = coe - 0.01

            pb = max(0.3, min((roe - g) / (coe - g), 6.0))
            equity_value_mi = (se * pb) / 1_000  # R$ mil → R$ milhões

            result.scenarios[name] = ScenarioResult(
                scenario=name,
                fair_value=equity_value_mi,
                current_price=current_price,
                upside=None,  # sem shares não há preço/ação
                method="Gordon Growth",
                assumptions={"roe": roe, "coe": coe, "g": g, "pb_implied": pb},
            )

        return result

    # ── DDM (utilities) ───────────────────────────────────────────────────────

    def _ddm(
        self,
        ticker: str,
        base_year: int,
        metrics: dict,
        cfg: SectorConfig,
        current_price: float | None,
    ) -> ValuationResult:
        a = cfg.ddm_assumptions
        ni = metrics.get("net_income") or 0
        payout = a.get("payout_ratio", 0.60)
        dps_total = abs(ni) * payout  # dividendos totais (R$ mil)

        scenarios = cfg.build_gordon_scenarios(roe=metrics.get("roe") or 0.10)
        result = ValuationResult(
            ticker=ticker,
            sector_type=cfg.sector_type,
            base_year=base_year,
            method="DDM — Gordon Growth",
        )

        for name, params in scenarios.items():
            coe, g = params["coe"], params["g"]
            if coe <= g:
                g = coe - 0.01

            # V = D₁ / (ke − g) onde D₁ = DPS × (1+g)
            equity_value = (dps_total * (1 + g)) / (coe - g)
            equity_value_mi = equity_value / 1_000

            result.scenarios[name] = ScenarioResult(
                scenario=name,
                fair_value=equity_value_mi,
                current_price=current_price,
                upside=None,
                method="DDM",
                assumptions={
                    "net_income": ni,
                    "payout": payout,
                    "dividends_total_mi": dps_total / 1000,
                    "coe": coe,
                    "g": g,
                },
            )

        return result

    # ── EV/EBITDA Múltiplo (oil_gas, mining, telecom) ────────────────────────

    def _ev_ebitda(
        self,
        ticker: str,
        base_year: int,
        metrics: dict,
        cfg: SectorConfig,
        current_price: float | None,
    ) -> ValuationResult:
        a = cfg.ev_ebitda_assumptions
        ebitda = self._calc_ebitda(metrics)
        net_debt = metrics.get("net_debt") or 0

        multiples = {
            "base": a.get("target_multiple_base", 5.5),
            "optimistic": a.get("target_multiple_max", 7.0),
            "pessimistic": a.get("target_multiple_min", 4.0),
        }

        result = ValuationResult(
            ticker=ticker,
            sector_type=cfg.sector_type,
            base_year=base_year,
            method="EV/EBITDA Múltiplo",
        )

        for name, multiple in multiples.items():
            ev = ebitda * multiple
            equity_value_mi = (ev - net_debt) / 1_000

            result.scenarios[name] = ScenarioResult(
                scenario=name,
                fair_value=max(0.0, equity_value_mi),
                current_price=current_price,
                upside=None,
                method="EV/EBITDA",
                assumptions={
                    "ebitda_mi": ebitda / 1000,
                    "ev_ebitda_multiple": multiple,
                    "net_debt_mi": net_debt / 1000,
                    "ev_mi": ev / 1000,
                },
            )

        return result

    # ── DCF FCFF (industrial, retail, saúde, tech, agro) ─────────────────────

    def _dcf_fcff(
        self,
        ticker: str,
        base_year: int,
        metrics: dict,
        cfg: SectorConfig,
        current_price: float | None,
    ) -> ValuationResult:
        _ensure_src_path()
        from valuation.valuation_dcf import DCFAssumptions, run_dcf

        a = cfg.dcf_assumptions
        net_revenue = metrics.get("net_revenue") or 0
        ebitda = self._calc_ebitda(metrics)
        net_debt = metrics.get("net_debt") or 0
        hist_ebitda_margin = (ebitda / net_revenue) if net_revenue > 0 else 0.12

        scenarios = cfg.build_dcf_scenarios(hist_ebitda_margin)

        result = ValuationResult(
            ticker=ticker,
            sector_type=cfg.sector_type,
            base_year=base_year,
            method="DCF FCFF",
        )

        for name, params in scenarios.items():
            g = a.get("terminal_growth", 0.055) + params["g_adj"]
            assumptions = DCFAssumptions(
                risk_free_rate=a.get("risk_free", 0.065),
                equity_risk_premium=a.get("erp", 0.055),
                beta=a.get("beta", 1.0),
                pre_tax_cost_of_debt=a.get("cost_of_debt", 0.115) + params["wacc_adj"],
                tax_rate=a.get("tax_rate", 0.27),
                debt_to_capital=a.get("debt_to_capital", 0.30),
                revenue_growth=params["rev_growth"],
                ebitda_margin=params["ebitda_margin"],
                capex_to_revenue=params["capex_pct"],
                wc_to_revenue=[0.01] * len(params["rev_growth"]),
                depreciation_to_revenue=[0.03] * len(params["rev_growth"]),
                terminal_growth_rate=g,
            )

            dcf = run_dcf(
                ticker=ticker,
                base_year=base_year,
                base_revenue=net_revenue,
                base_ebitda=ebitda,
                assumptions=assumptions,
                net_debt=net_debt,
            )

            equity_value_mi = dcf.equity_value / 1_000

            result.scenarios[name] = ScenarioResult(
                scenario=name,
                fair_value=max(0.0, equity_value_mi),
                current_price=current_price,
                upside=None,
                method="DCF FCFF",
                assumptions={
                    "wacc": round(assumptions.wacc, 4),
                    "g_terminal": round(g, 4),
                    "rev_growth_avg": round(
                        sum(params["rev_growth"]) / len(params["rev_growth"]), 4
                    ),
                    "ebitda_margin_avg": round(
                        sum(params["ebitda_margin"]) / len(params["ebitda_margin"]), 4
                    ),
                    "beta": a.get("beta", 1.0),
                    "tax_rate": a.get("tax_rate", 0.27),
                },
            )

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_raw_statements(self, ticker: str, year: int) -> dict | None:
        from src.processing.storage import ProcessedStore

        return ProcessedStore().load(ticker, year)

    def _load_latest_metrics(self, ticker: str) -> dict | None:
        d = self.output_dir / ticker
        files = sorted(d.glob("metrics_*.json")) if d.exists() else []
        if not files:
            return None
        try:
            return json.loads(files[-1].read_text())
        except Exception:
            return None

    @staticmethod
    def _enrich_with_raw(metrics: dict, raw: dict) -> None:
        """Adiciona dados brutos do balanço/DRE ao dict de métricas."""
        bal = raw.get("balance_sheet") or {}
        assets_d = (bal.get("assets") or {}) if isinstance(bal, dict) else {}
        liab_d = (bal.get("liabilities") or {}) if isinstance(bal, dict) else {}
        inc_d = raw.get("income_statement") or {}

        def _fv(d: dict, k: str) -> float:
            try:
                return float(d.get(k) or 0)
            except (TypeError, ValueError):
                return 0.0

        metrics.setdefault("shareholders_equity", _fv(liab_d, "shareholders_equity"))
        metrics.setdefault("total_assets", _fv(assets_d, "total_assets"))
        metrics.setdefault("net_income", _fv(inc_d, "net_income"))
        metrics.setdefault("nii_gross", _fv(inc_d, "nii_gross"))

        # Para industriais: dados do DRE (lista de records)
        if not metrics.get("net_revenue"):
            for stmt_key in ("DRE",):
                records = raw.get(stmt_key, [])
                for row in records:
                    name = row.get("normalized_name")
                    val = row.get("value")
                    if name and val is not None and name not in metrics:
                        try:
                            metrics[name] = float(val)
                        except (TypeError, ValueError):
                            pass

    @staticmethod
    def _calc_ebitda(m: dict) -> float:
        if m.get("ebitda"):
            return float(m["ebitda"])
        ebit = float(m.get("ebit") or 0)
        da = abs(float(m.get("depreciation_amortization_cfo") or 0))
        if ebit and da:
            return ebit + da
        return ebit * 1.20  # fallback: +20% de D&A estimado

    @staticmethod
    def _from_cache(data: dict) -> ValuationResult:
        result = ValuationResult(
            ticker=data.get("ticker", ""),
            sector_type=data.get("sector_type", ""),
            base_year=data.get("base_year", 0),
            method=data.get("method", ""),
            calculated_at=data.get("calculated_at", ""),
        )
        for name, s in data.get("scenarios", {}).items():
            result.scenarios[name] = ScenarioResult(
                scenario=name,
                fair_value=s.get("fair_value", 0),
                current_price=s.get("current_price"),
                upside=s.get("upside"),
                method=data.get("method", ""),
                assumptions=s.get("assumptions", {}),
            )
        return result

    @staticmethod
    def _save(result: ValuationResult, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))


# ── Função de alto nível ──────────────────────────────────────────────────────


def run_valuation(ticker: str, force: bool = False) -> ValuationResult | None:
    """Calcula valuation automático para um ticker usando premissas do seu setor."""
    return AutoDCF().run(ticker, force=force)
