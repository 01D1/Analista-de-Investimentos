"""Requisitos mínimos de cobertura para validação de amostra."""
from __future__ import annotations

from typing import Any

import pandas as pd


DEFAULT_REQUIREMENTS = {
    "min_signals_per_source": 30,
    "min_tickers_per_source": 2,
    "min_active_days_per_source": 10,
    "min_regimes_per_source": 2,
    "min_useful_coverage_pct": 0.50,
}


def evaluate_signal_coverage_requirements(
    coverage_df: pd.DataFrame,
    requirements: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Avalia requisitos mínimos por fonte de sinal em estudo."""
    req = {**DEFAULT_REQUIREMENTS, **(requirements or {})}
    columns = list(coverage_df.columns if coverage_df is not None else []) + [
        "requirements_status",
        "requirements_message",
    ]
    if coverage_df is None or coverage_df.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for _, row in coverage_df.iterrows():
        source = str(row.get("signal_source", "")).lower()
        if str(row.get("coverage_status", "")).upper() == "SEM_DADOS":
            status = "COVERAGE_INSUFFICIENT"
            failures = ["sem dados persistidos"]
        else:
            failures = []
            if int(row.get("signals_count") or 0) < int(req["min_signals_per_source"]):
                failures.append(f"sinais < {req['min_signals_per_source']}")
            if int(row.get("tickers_count") or 0) < int(req["min_tickers_per_source"]):
                failures.append(f"tickers < {req['min_tickers_per_source']}")
            if int(row.get("active_days_count") or 0) < int(req["min_active_days_per_source"]):
                failures.append(f"dias úteis < {req['min_active_days_per_source']}")
            regimes = int(row.get("regimes_count") or 0)
            if regimes and regimes < int(req["min_regimes_per_source"]):
                failures.append(f"regimes < {req['min_regimes_per_source']}")
            if float(row.get("coverage_pct") or 0) < float(req["min_useful_coverage_pct"]):
                failures.append(f"cobertura útil < {req['min_useful_coverage_pct']:.0%}")

            if not failures:
                status = "COVERAGE_REQUIREMENTS_PASS"
            elif source in {"options"}:
                status = "COVERAGE_REQUIREMENTS_WARNING"
            else:
                status = "COVERAGE_REQUIREMENTS_FAIL"

        item = row.to_dict()
        item["requirements_status"] = status
        item["requirements_message"] = "OK" if not failures else "Cobertura insuficiente: " + "; ".join(failures)
        rows.append(item)
    return pd.DataFrame(rows, columns=columns)

