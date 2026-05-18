"""Explicações institucionais para paper trading."""
from __future__ import annotations


def explain_paper_order(order) -> str:
    return f"Ordem simulada {order.side} em {order.ticker}, status {order.status}. Não é ordem real."


def explain_paper_simulation(summary: dict) -> str:
    return (
        f"Carteira simulada com retorno {summary.get('total_return', 0):.2%}, "
        f"drawdown {summary.get('max_drawdown', 0):.2%} e {summary.get('trades_count', 0)} ordens simuladas. "
        "Resultado analítico; não constitui recomendação."
    )

