"""Força relativa contra benchmark ou cesta de ativos."""
from __future__ import annotations

from .metrics import to_float


def relative_strength(asset_return: float, benchmark_return: float) -> dict:
    asset = to_float(asset_return, 0.0)
    benchmark = to_float(benchmark_return, 0.0)
    relative = (asset - benchmark) * 100.0
    return {
        "asset_return": round(asset * 100.0, 4),
        "benchmark_return": round(benchmark * 100.0, 4),
        "relative_return": round(relative, 4),
        "condition": "FORTE_RELATIVO" if relative > 0 else ("FRACO_RELATIVO" if relative < 0 else "NEUTRO"),
    }
