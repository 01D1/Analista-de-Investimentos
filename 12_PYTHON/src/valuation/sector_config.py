"""
sector_config.py
----------------
Camada Python que carrega config/sectors.yaml e fornece acesso tipado
às premissas de modelagem por setor.

Uso:
    from src.valuation.sector_config import SectorConfig

    cfg = SectorConfig.for_ticker("BBAS3")   # lê tickers.yaml → sectors.yaml
    cfg = SectorConfig.for_type("retail")

    cfg.valuation_method          # "dcf_fcff"
    cfg.financial_model           # "industrial"
    cfg.key_metrics               # ["ebitda_margin", "nd_ebitda", ...]
    cfg.dcf_assumptions           # dict com todas as premissas
    cfg.risk_threshold("nd_ebitda_high")  # 3.5
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_SECTORS_PATH = _CONFIG_DIR / "sectors.yaml"
_TICKERS_PATH = _CONFIG_DIR / "tickers.yaml"

# Setor fallback se o tipo do ticker não estiver mapeado
_DEFAULT_SECTOR = "industrial"


@lru_cache(maxsize=1)
def _load_sectors() -> dict:
    with open(_SECTORS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f).get("sectors", {})


@lru_cache(maxsize=1)
def _load_ticker_map() -> dict[str, str]:
    """Retorna {TICKER: tipo_setor}."""
    with open(_TICKERS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {t["ticker"]: t.get("type", _DEFAULT_SECTOR) for t in data.get("tickers", [])}


class SectorConfig:
    """
    Premissas de modelagem para um setor específico.

    Attrs:
        sector_type:        ex. "bank", "retail", "oil_gas"
        valuation_method:   "gordon_growth" | "dcf_fcff" | "ev_ebitda_multiple" | "ddm"
        financial_model:    "bank" | "industrial"
        key_metrics:        lista ordenada de métricas para exibição
        description:        descrição do setor
    """

    def __init__(self, sector_type: str):
        sectors = _load_sectors()

        # Fallback gracioso: se tipo não existe, usa industrial
        if sector_type not in sectors:
            sector_type = _DEFAULT_SECTOR

        self.sector_type: str = sector_type
        self._data: dict = sectors[sector_type]

    # ── Propriedades principais ───────────────────────────────────────────────

    @property
    def valuation_method(self) -> str:
        return self._data.get("valuation_method", "dcf_fcff")

    @property
    def financial_model(self) -> str:
        return self._data.get("financial_model", "industrial")

    @property
    def is_bank_model(self) -> bool:
        return self.financial_model == "bank"

    @property
    def key_metrics(self) -> list[str]:
        return self._data.get("key_metrics", [])

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    # ── Premissas por método ──────────────────────────────────────────────────

    @property
    def dcf_assumptions(self) -> dict:
        return self._data.get("dcf_assumptions", {})

    @property
    def gordon_assumptions(self) -> dict:
        return self._data.get("gordon_assumptions", {})

    @property
    def ddm_assumptions(self) -> dict:
        # DDM usa mesma estrutura que gordon; fallback para gordon se ddm não definido
        return self._data.get("ddm_assumptions") or self._data.get("gordon_assumptions", {})

    @property
    def ev_ebitda_assumptions(self) -> dict:
        return self._data.get("ev_ebitda_assumptions", {})

    @property
    def scenario_deltas(self) -> dict:
        """Variações para cenários otimista/pessimista no Gordon Growth / DDM."""
        return self._data.get(
            "scenario_deltas",
            {
                "optimistic": {"coe": -0.005, "terminal_growth": +0.005},
                "pessimistic": {"coe": +0.005, "terminal_growth": -0.005},
            },
        )

    # ── Risk thresholds ───────────────────────────────────────────────────────

    @property
    def risk_thresholds(self) -> dict:
        return self._data.get("risk_thresholds", {})

    def risk_threshold(self, key: str, default: Any = None) -> Any:
        return self.risk_thresholds.get(key, default)

    # ── Helpers para DCF ─────────────────────────────────────────────────────

    def build_dcf_scenarios(
        self,
        historical_ebitda_margin: float,
    ) -> dict[str, dict]:
        """
        Constrói dict de cenários para DCF FCFF.

        Returns:
            {"base": {...}, "optimistic": {...}, "pessimistic": {...}}
        """
        a = self.dcf_assumptions
        n = a.get("n_years", 5)
        offset = a.get("base_ebitda_margin_offset", 0.0)
        base_margin = max(0.05, historical_ebitda_margin + offset)
        gd = a.get("scenario_growth_delta", 0.05)
        wd = a.get("scenario_wacc_delta", 0.005)

        base_growth = a.get("base_revenue_growth", [0.08] * n)
        if len(base_growth) < n:
            base_growth = base_growth + [base_growth[-1]] * (n - len(base_growth))

        return {
            "base": {
                "rev_growth": base_growth[:n],
                "ebitda_margin": [base_margin] * n,
                "capex_pct": [a.get("base_capex_pct", 0.06)] * n,
                "wacc_adj": 0.0,
                "g_adj": 0.0,
            },
            "optimistic": {
                "rev_growth": [g + gd for g in base_growth[:n]],
                "ebitda_margin": [min(base_margin * 1.05, 0.55)] * n,
                "capex_pct": [a.get("base_capex_pct", 0.06)] * n,
                "wacc_adj": -wd,
                "g_adj": +wd,
            },
            "pessimistic": {
                "rev_growth": [max(0.0, g - gd) for g in base_growth[:n]],
                "ebitda_margin": [base_margin * 0.93] * n,
                "capex_pct": [a.get("base_capex_pct", 0.06) * 1.1] * n,
                "wacc_adj": +wd,
                "g_adj": -wd,
            },
        }

    def build_gordon_scenarios(self, roe: float) -> dict[str, dict]:
        """Constrói cenários para Gordon Growth / DDM."""
        a = self.gordon_assumptions or self.ddm_assumptions
        deltas = self.scenario_deltas

        base_coe = a.get("coe", 0.135)
        base_g = a.get("terminal_growth", 0.055)

        return {
            "base": {
                "coe": base_coe,
                "g": base_g,
            },
            "optimistic": {
                "coe": base_coe + deltas.get("optimistic", {}).get("coe", -0.005),
                "g": base_g + deltas.get("optimistic", {}).get("terminal_growth", +0.005),
            },
            "pessimistic": {
                "coe": base_coe + deltas.get("pessimistic", {}).get("coe", +0.005),
                "g": base_g + deltas.get("pessimistic", {}).get("terminal_growth", -0.005),
            },
        }

    # ── Construtores ─────────────────────────────────────────────────────────

    @classmethod
    def for_ticker(cls, ticker: str) -> SectorConfig:
        """Cria SectorConfig a partir de um ticker (lê tickers.yaml)."""
        ticker_map = _load_ticker_map()
        sector_type = ticker_map.get(ticker.upper(), _DEFAULT_SECTOR)
        return cls(sector_type)

    @classmethod
    def for_type(cls, sector_type: str) -> SectorConfig:
        return cls(sector_type)

    @classmethod
    def available_sectors(cls) -> list[str]:
        return list(_load_sectors().keys())

    def __repr__(self) -> str:
        return (
            f"SectorConfig(type={self.sector_type!r}, "
            f"method={self.valuation_method!r}, "
            f"model={self.financial_model!r})"
        )
