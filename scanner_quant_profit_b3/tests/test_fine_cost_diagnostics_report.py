import pandas as pd

from src.reports.fine_cost_diagnostics_report import generate_fine_cost_diagnostics_markdown


def test_generate_fine_cost_diagnostics_markdown_contains_sections():
    markdown = generate_fine_cost_diagnostics_markdown(
        {
            "lifecycle_summary": {"entry_cost_pct": 0.2, "exit_cost_pct": 0.3, "rebalance_cost_pct": 0.5},
            "lifecycle": pd.DataFrame([{"lifecycle_id": "L1", "ticker": "PETR4", "total_cost": 10}]),
            "rebalance": {"summary": {"rebalance_cost_class": "REBALANCE_COST_HIGH"}, "rebalance_cost_by_ticker": pd.DataFrame()},
            "exit_rules": pd.DataFrame([{"exit_rule": "EXIT_STOP_LOSS", "exit_count": 1, "cost_drag": 2}]),
            "unknown": {"summary": {"unknown_orders_count": 1, "unknown_cost_total": 2, "missing_fields_summary": {"signal_source": 1}}},
            "metadata_fixes": ["Garantir signal_source em toda ordem simulada."],
        }
    )

    assert "# Diagnóstico Fino de Custos" in markdown
    assert "Não recomendação" in markdown
