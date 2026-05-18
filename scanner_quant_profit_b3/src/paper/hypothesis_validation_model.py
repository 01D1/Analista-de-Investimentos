"""Modelo de cenarios para validacao OOS de hipoteses de investigacao."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import pandas as pd


SCENARIO_COLUMNS = [
    "validation_id",
    "hypothesis_id",
    "hypothesis_type",
    "target",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "cost_bps",
    "slippage_bps",
    "regime_filter",
    "universe_filter",
    "parameters_json",
    "metadata_json",
]


@dataclass
class HypothesisValidationScenario:
    validation_id: str
    hypothesis_id: str
    hypothesis_type: str
    target: str
    scenario_name: str
    signal_source: str
    start_date: str
    end_date: str
    cost_bps: float = 10
    slippage_bps: float = 5
    regime_filter: str = ""
    universe_filter: str = ""
    parameters_json: str = "{}"
    metadata_json: str = "{}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["parameters_json"] = data.get("parameters_json") or "{}"
        data["metadata_json"] = data.get("metadata_json") or "{}"
        return data


def _hypothesis_rows(hypotheses_df: pd.DataFrame) -> pd.DataFrame:
    if hypotheses_df is None or hypotheses_df.empty:
        return pd.DataFrame(columns=["hypothesis_id", "hypothesis_type", "target"])
    out = hypotheses_df.copy()
    for col in ["hypothesis_id", "hypothesis_type", "target"]:
        if col not in out.columns:
            out[col] = ""
    return out


def _params(**kwargs) -> str:
    return json.dumps(kwargs, ensure_ascii=False, sort_keys=True)


def build_hypothesis_validation_scenarios(hypotheses_df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Cria cenarios padronizados para testar hipoteses promissoras."""
    scenarios: list[dict] = []
    for _, hyp in _hypothesis_rows(hypotheses_df).iterrows():
        hypothesis_id = str(hyp.get("hypothesis_id", "HYPOTHESIS"))
        hypothesis_type = str(hyp.get("hypothesis_type", "UNKNOWN"))
        target = str(hyp.get("target", ""))
        base = {
            "hypothesis_id": hypothesis_id,
            "hypothesis_type": hypothesis_type,
            "target": target,
            "start_date": str(start_date),
            "end_date": str(end_date),
        }
        specs = [
            ("BASE_COST", "quant", 10, 5, "", _params(risk_pct=0.005, max_positions=5)),
            ("HIGH_COST", "quant", 20, 10, "", _params(risk_pct=0.005, max_positions=5)),
            ("HIGH_SLIPPAGE", "quant", 10, 20, "", _params(risk_pct=0.005, max_positions=5)),
            ("LOW_RISK", "quant", 10, 5, "", _params(risk_pct=0.0025, max_positions=4)),
            ("HIGH_RISK", "quant", 10, 5, "", _params(risk_pct=0.01, max_positions=6)),
            ("QUANT_ONLY", "quant", 10, 5, "", _params(risk_pct=0.005, max_positions=5)),
            ("TECHNICAL_ONLY", "technical", 10, 5, "", _params(risk_pct=0.005, max_positions=5)),
            ("INTEGRATED_ONLY", "integrated", 10, 5, "", _params(risk_pct=0.005, max_positions=5)),
            ("REGIME_LATERAL", "quant", 10, 5, "LATERAL", _params(risk_pct=0.005, max_positions=5)),
            ("REGIME_ALTA_TENDENCIAL", "quant", 10, 5, "ALTA_TENDENCIAL", _params(risk_pct=0.005, max_positions=5)),
            ("REGIME_ALTA_VOLATILIDADE", "quant", 10, 5, "ALTA_VOLATILIDADE", _params(risk_pct=0.005, max_positions=5)),
        ]
        for idx, (name, source, cost, slippage, regime, params) in enumerate(specs, start=1):
            scenarios.append(
                HypothesisValidationScenario(
                    validation_id=f"{hypothesis_id}_{name}",
                    scenario_name=name,
                    signal_source=source,
                    cost_bps=cost,
                    slippage_bps=slippage,
                    regime_filter=regime,
                    parameters_json=params,
                    metadata_json=json.dumps({"scenario_order": idx}, ensure_ascii=False),
                    **base,
                ).to_dict()
            )
    return pd.DataFrame(scenarios, columns=SCENARIO_COLUMNS)
