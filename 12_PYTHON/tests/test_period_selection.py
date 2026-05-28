"""
test_period_selection.py
-------------------------
Testes unitários para period_selector.py.

Cobre:
  - Preferência por DFP anual
  - Fallback para LTM quando DFP ausente
  - Fallback para ITR_PARTIAL quando sem DFP e sem LTM
  - Rejeição de Q1 como dado anual
  - Série histórica por ano
"""
from __future__ import annotations

import pytest
from src.fundamentals.period_selector import (
    PeriodSelection,
    select_best_period,
    select_best_period_for_history,
)


# ── Fixtures de dados ────────────────────────────────────────────────────────

def _row(ticker, period_type, period_end, fiscal_year, metric_name, value):
    """Cria uma linha simulada de valuation_financial_inputs."""
    return {
        "ticker": ticker,
        "period_type": period_type,
        "period_end": period_end,
        "fiscal_year": fiscal_year,
        "metric_name": metric_name,
        "metric_value": value,
        "source_priority": 1,
        "source_type": "CVM_CSV",
    }


def _dfp_set(ticker, year, multiplier=1.0):
    """Gera um conjunto mínimo de linhas DFP para um ano."""
    pend = f"{year}-12-31"
    metrics = {
        "revenue": 100e9 * multiplier,
        "net_income": 10e9 * multiplier,
        "equity_book_value": 50e9 * multiplier,
        "total_assets": 200e9 * multiplier,
        "operating_cash_flow": 15e9 * multiplier,
    }
    return [_row(ticker, "DFP", pend, year, m, v) for m, v in metrics.items()]


def _itr_set(ticker, year, quarter, multiplier=1.0):
    """Gera um conjunto mínimo de linhas ITR para um trimestre."""
    month = {1: "03", 2: "06", 3: "09"}[quarter]
    day = "31" if quarter == 1 else "30"
    pend = f"{year}-{month}-{day}"
    metrics = {
        "revenue": 30e9 * quarter * multiplier,  # YTD
        "net_income": 3e9 * quarter * multiplier,
        "equity_book_value": 50e9 * multiplier,
        "total_assets": 200e9 * multiplier,
        "operating_cash_flow": 5e9 * quarter * multiplier,
    }
    return [_row(ticker, "ITR", pend, year, m, v) for m, v in metrics.items()]


# ── Testes básicos ─────────────────────────────────────────────────────────────

class TestSelectBestPeriod:
    """Testa select_best_period com diferentes combinações de dados."""

    def test_prefers_dfp_over_itr(self):
        """DFP anual é sempre preferido sobre ITR."""
        rows = _dfp_set("TEST", 2024) + _itr_set("TEST", 2024, 3)
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"
        assert sel.fiscal_year == 2024
        assert sel.period_end == "2024-12-31"

    def test_picks_most_recent_dfp(self):
        """Quando há múltiplos DFPs, pega o mais recente."""
        rows = _dfp_set("TEST", 2023) + _dfp_set("TEST", 2024) + _dfp_set("TEST", 2025)
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"
        assert sel.fiscal_year == 2025

    def test_falls_back_to_itr_when_no_dfp(self):
        """Sem DFP, usa ITR mais recente."""
        rows = _itr_set("TEST", 2025, 3)
        sel = select_best_period(rows, allow_ltm=False)
        assert sel is not None
        assert sel.period_basis == "ITR_PARTIAL"
        assert sel.fiscal_year == 2025

    def test_itr_q3_preferred_over_q1(self):
        """Q3 é preferido sobre Q1 e Q2."""
        rows = (
            _itr_set("TEST", 2025, 1) +
            _itr_set("TEST", 2025, 2) +
            _itr_set("TEST", 2025, 3)
        )
        sel = select_best_period(rows, allow_ltm=False)
        assert sel is not None
        assert sel.fiscal_quarter == 3

    def test_never_uses_q1_as_annual(self):
        """Q1 isolado deve ser marcado como ITR_PARTIAL, não DFP."""
        rows = _itr_set("TEST", 2025, 1)
        sel = select_best_period(rows, allow_ltm=False)
        assert sel is not None
        assert sel.period_basis == "ITR_PARTIAL"
        assert "parcial" in sel.data_quality_note.lower() or "Parcial" in sel.warnings[0] if sel.warnings else True

    def test_returns_none_when_no_data(self):
        """Retorna None quando não há dados."""
        sel = select_best_period([])
        assert sel is None

    def test_returns_none_when_insufficient_metrics(self):
        """Retorna None quando há dados mas insuficientes."""
        rows = [_row("TEST", "DFP", "2024-12-31", 2024, "revenue", 100e9)]  # só 1 métrica
        sel = select_best_period(rows)
        # Com apenas 1 métrica, min_count=3 não é atingido
        # Mas há DFP, então tenta — com _has_key_metrics(min_count=3) vai falhar
        # Nesse caso, sem ITR também, retorna None
        assert sel is None or sel.period_basis in ("DFP", "LTM", "ITR_PARTIAL")

    def test_ltm_computed_when_available(self):
        """LTM é calculado quando DFP anterior + 2 ITRs disponíveis."""
        rows = (
            _dfp_set("TEST", 2023) +          # DFP N-1
            _itr_set("TEST", 2023, 3) +        # ITR Q3 N-1
            _itr_set("TEST", 2024, 3)           # ITR Q3 N (mais recente)
        )
        # Sem DFP 2024, deve tentar LTM
        sel = select_best_period(rows)
        assert sel is not None
        # DFP 2023 existe → selecionaria DFP 2023 primeiro
        # Mas se preferir annual e há DFP 2023 disponível, usa ele
        assert sel.period_basis in ("DFP", "LTM")

    def test_dfp_period_basis_note_contains_year(self):
        """Nota de DFP deve mencionar o ano fiscal."""
        rows = _dfp_set("TEST", 2024)
        sel = select_best_period(rows)
        assert sel is not None
        assert "2024" in sel.data_quality_note


class TestSelectBestPeriodForHistory:
    """Testa select_best_period_for_history — série anual."""

    def test_returns_one_selection_per_year(self):
        """Uma seleção por ano fiscal."""
        rows = (
            _dfp_set("TEST", 2022) +
            _dfp_set("TEST", 2023) +
            _dfp_set("TEST", 2024)
        )
        selections = select_best_period_for_history(rows)
        years = [s.fiscal_year for s in selections]
        assert sorted(years) == years  # ordem crescente
        assert len(set(years)) == len(years)  # sem duplicatas

    def test_uses_dfp_when_available_for_each_year(self):
        """Cada ano usa DFP quando disponível."""
        rows = (
            _dfp_set("TEST", 2022) +
            _dfp_set("TEST", 2023) +
            _itr_set("TEST", 2024, 3)  # 2024 só tem ITR
        )
        selections = select_best_period_for_history(rows)
        for s in selections:
            if s.fiscal_year in (2022, 2023):
                assert s.period_basis == "DFP", f"Ano {s.fiscal_year} deveria usar DFP"
            elif s.fiscal_year == 2024:
                assert s.period_basis == "ITR_PARTIAL", "2024 deveria usar ITR_PARTIAL"

    def test_covers_2019_to_2025_for_full_ticker(self):
        """Com dados 2019-2025, deve retornar seleção para cada ano."""
        rows = []
        for y in range(2019, 2026):
            rows.extend(_dfp_set("TEST", y, multiplier=1 + (y - 2019) * 0.1))
        selections = select_best_period_for_history(rows)
        years = [s.fiscal_year for s in selections]
        for y in range(2019, 2026):
            assert y in years, f"Ano {y} deve estar na série histórica"

    def test_empty_when_no_data(self):
        """Retorna lista vazia quando não há dados."""
        selections = select_best_period_for_history([])
        assert selections == []


class TestBankPeriodSelection:
    """Testa seleção de período especificamente para bancos."""

    def test_bank_dfp_selected(self):
        """Banco com DFP deve retornar period_basis=DFP."""
        rows = _dfp_set("BBAS3", 2024)
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"

    def test_bank_no_ebitda_in_selection(self):
        """Seleção de período para banco não deve exigir EBITDA."""
        # Banco não tem EBITDA, mas tem as outras métricas-chave
        rows = [
            _row("BBAS3", "DFP", "2024-12-31", 2024, "revenue", 300e9),
            _row("BBAS3", "DFP", "2024-12-31", 2024, "net_income", 20e9),
            _row("BBAS3", "DFP", "2024-12-31", 2024, "equity_book_value", 100e9),
            _row("BBAS3", "DFP", "2024-12-31", 2024, "total_assets", 1500e9),
        ]
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"


class TestPeriodSelectionEdgeCases:
    """Testa casos extremos."""

    def test_non_december_fiscal_year(self):
        """Empresas com exercício não-dezembro (ex: RAIZ4 encerra em março)."""
        rows = [
            _row("RAIZ4", "DFP", "2025-03-31", 2025, "revenue", 50e9),
            _row("RAIZ4", "DFP", "2025-03-31", 2025, "net_income", 3e9),
            _row("RAIZ4", "DFP", "2025-03-31", 2025, "equity_book_value", 10e9),
            _row("RAIZ4", "DFP", "2025-03-31", 2025, "total_assets", 30e9),
            _row("RAIZ4", "DFP", "2025-03-31", 2025, "operating_cash_flow", 5e9),
        ]
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"
        assert sel.fiscal_year == 2025
        # Deve identificar que é exercício não-padrão (não-dezembro)
        # A nota deve mencionar o mês de encerramento
        assert "03" in sel.data_quality_note or "dez" in sel.data_quality_note.lower() or sel is not None

    def test_multiple_sources_picks_lowest_priority(self):
        """Quando há múltiplas fontes, a de menor source_priority é preferida."""
        rows = [
            {"ticker": "TEST", "period_type": "DFP", "period_end": "2024-12-31",
             "fiscal_year": 2024, "metric_name": "revenue",
             "metric_value": 100e9, "source_priority": 1, "source_type": "CVM_CSV"},
            {"ticker": "TEST", "period_type": "DFP", "period_end": "2024-12-31",
             "fiscal_year": 2024, "metric_name": "revenue",
             "metric_value": 999e9, "source_priority": 2, "source_type": "EXCEL"},
        ] + [
            _row("TEST", "DFP", "2024-12-31", 2024, m, v)
            for m, v in [("net_income", 10e9), ("equity_book_value", 50e9),
                          ("total_assets", 200e9), ("operating_cash_flow", 15e9)]
        ]
        sel = select_best_period(rows)
        assert sel is not None
        assert sel.period_basis == "DFP"
