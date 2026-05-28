"""
test_plausibility.py
---------------------
Testes unitários para plausibility.py.

Cobre:
  - Margem líquida acima de 100%
  - ROE acima de 200%
  - EV/EBITDA negativo
  - EV/EBITDA para bancos
  - Receita negativa
  - Net income > 80% da receita
  - EBITDA > Receita
  - Market cap fora de faixa
  - Período ITR marcado corretamente
  - Balanço não fechado
"""
from __future__ import annotations

import pytest
from src.fundamentals.plausibility import (
    PlausibilityChecker,
    PlausibilityAlert,
    classify_alerts,
    has_critical_issues,
    check_snapshot,
)


def _snap(overrides: dict = {}, **kwargs) -> dict:
    """Cria um snapshot mínimo de teste."""
    base = {
        "ticker": "TEST",
        "industry": "industrial",
        "period_type": "DFP",
        "revenue": 100e9,
        "ebitda": 25e9,
        "net_income": 10e9,
        "equity": 50e9,
        "assets": 200e9,
        "liabilities": 150e9,
        "market_cap": 100e9,
        "shares_outstanding": 1e9,
        "gross_margin": 0.40,
        "ebitda_margin": 0.25,
        "net_margin": 0.10,
        "roe": 0.20,
        "debt_ebitda": 2.0,
        "valuation_multiples": {
            "pe": 10.0,
            "pb": 2.0,
            "ev_ebitda": 8.0,
        },
    }
    base.update(overrides)
    base.update(kwargs)
    return base


class TestMarginChecks:
    """Testa verificações de margem."""

    def test_ok_when_margins_normal(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap())
        critical = [a for a in alerts if a.check_name in (
            "implausible_ebitda_margin", "implausible_net_margin"
        )]
        assert not critical

    def test_net_margin_above_80pct_is_error(self):
        """Lucro líquido > 80% da receita gera erro."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(net_income=90e9))  # 90% de 100B
        assert any(a.check_name == "net_income_close_to_revenue" for a in alerts)

    def test_ebitda_exceeds_revenue_is_critical(self):
        """EBITDA > Receita é erro crítico (impossível)."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(ebitda=120e9))  # 120% de 100B
        assert any(a.check_name == "ebitda_exceeds_revenue" for a in alerts)
        assert any(a.severity == "CRITICAL" for a in alerts)

    def test_net_margin_over_80pct(self):
        snap = _snap(net_income=85e9, net_margin=0.85)
        alerts = check_snapshot(snap)
        assert any(a.check_name == "net_income_close_to_revenue" for a in alerts)


class TestRoeChecks:
    """Testa verificações de ROE."""

    def test_roe_200pct_is_error(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(roe=2.5))  # 250%
        assert any(a.check_name == "implausible_roe" for a in alerts)

    def test_roe_negative_200pct_is_error(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(roe=-2.5))
        assert any(a.check_name == "implausible_roe" for a in alerts)

    def test_roe_100pct_is_ok(self):
        """ROE de 100% é alto mas plausível (empresas com patrimônio pequeno)."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(roe=1.0))
        roe_alerts = [a for a in alerts if a.check_name == "implausible_roe"]
        assert not roe_alerts  # 100% está dentro do limite de 200%


class TestLeverageChecks:
    """Testa verificações de alavancagem."""

    def test_extreme_leverage_is_error(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(debt_ebitda=30.0))
        assert any(a.check_name == "extreme_leverage" for a in alerts)

    def test_moderate_leverage_is_ok(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(debt_ebitda=5.0))
        lev_alerts = [a for a in alerts if a.check_name == "extreme_leverage"]
        assert not lev_alerts

    def test_bank_ignores_leverage(self):
        """Bancos não têm DívLíq/EBITDA verificado."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(industry="bank", debt_ebitda=100.0))
        lev_alerts = [a for a in alerts if a.check_name == "extreme_leverage"]
        assert not lev_alerts


class TestBankChecks:
    """Testa verificações específicas para bancos."""

    def test_bank_ev_ebitda_is_error(self):
        """EV/EBITDA calculado para banco deve gerar erro."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(
            industry="bank",
            valuation_multiples={"pe": 8.0, "pb": 1.5, "ev_ebitda": 10.0},
        ))
        assert any(a.check_name == "bank_ev_ebitda_invalid" for a in alerts)

    def test_bank_without_ev_ebitda_is_ok(self):
        """Banco sem EV/EBITDA não deve gerar alerta."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(
            industry="bank",
            valuation_multiples={"pe": 8.0, "pb": 1.5, "ev_ebitda": None},
        ))
        ev_alerts = [a for a in alerts if a.check_name == "bank_ev_ebitda_invalid"]
        assert not ev_alerts


class TestRevenueChecks:
    """Testa verificações de receita."""

    def test_negative_revenue_is_error(self):
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(revenue=-10e9))
        assert any(a.check_name == "negative_revenue" for a in alerts)
        assert any(a.severity == "ERROR" for a in alerts)

    def test_bank_negative_revenue_not_flagged_same_way(self):
        """Bancos podem ter receita de intermediação interpretada diferente."""
        # Para bancos a verificação de receita negativa ainda existe
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(industry="bank", revenue=-5e9))
        rev_alerts = [a for a in alerts if a.check_name == "negative_revenue"]
        # Bancos NÃO têm a checagem de receita negativa (is_bank=True pula o check)
        assert not rev_alerts  # check só para não-bancos


class TestMarketCapChecks:
    """Testa verificações de market cap."""

    def test_suspiciously_low_market_cap(self):
        """Market cap abaixo de R$ 50M deve ser alerta."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(market_cap=1e6))  # R$ 1M
        assert any(a.check_name == "suspiciously_low_market_cap" for a in alerts)

    def test_missing_shares_warning(self):
        """Falta de shares deve gerar aviso."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(shares_outstanding=None))
        assert any(a.check_name == "missing_shares" for a in alerts)


class TestPeriodChecks:
    """Testa verificações de período."""

    def test_itr_partial_warning(self):
        """Dados ITR_PARTIAL devem gerar aviso."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(period_type="ITR_PARTIAL"))
        assert any(a.check_name == "partial_period" for a in alerts)
        assert any(a.severity == "WARNING" for a in alerts)

    def test_dfp_no_partial_warning(self):
        """DFP não deve gerar aviso de parcial."""
        checker = PlausibilityChecker()
        alerts = checker.check(_snap(period_type="DFP"))
        partial_alerts = [a for a in alerts if a.check_name == "partial_period"]
        assert not partial_alerts


class TestBalanceSheetChecks:
    """Testa verificações de balanço."""

    def test_imbalanced_balance_sheet(self):
        """Balanço que não fecha deve gerar erro."""
        checker = PlausibilityChecker()
        # assets = 200B, liabilities + equity = 150 + 5 = 155B → diff = 45B > 5%
        alerts = checker.check(_snap(assets=200e9, liabilities=150e9, equity=5e9))
        assert any(a.check_name == "balance_sheet_imbalance" for a in alerts)

    def test_balanced_balance_sheet_ok(self):
        """Balanço que fecha não gera erro."""
        checker = PlausibilityChecker()
        # assets = 200B, liabilities + equity = 150 + 50 = 200B
        alerts = checker.check(_snap(assets=200e9, liabilities=150e9, equity=50e9))
        bal_alerts = [a for a in alerts if a.check_name == "balance_sheet_imbalance"]
        assert not bal_alerts


class TestHelpers:
    """Testa funções auxiliares."""

    def test_classify_alerts(self):
        alerts = [
            PlausibilityAlert("T", "check1", "CRITICAL", "msg"),
            PlausibilityAlert("T", "check2", "ERROR", "msg"),
            PlausibilityAlert("T", "check3", "WARNING", "msg"),
        ]
        classified = classify_alerts(alerts)
        assert len(classified["CRITICAL"]) == 1
        assert len(classified["ERROR"]) == 1
        assert len(classified["WARNING"]) == 1

    def test_has_critical_issues_true(self):
        alerts = [PlausibilityAlert("T", "c", "CRITICAL", "m")]
        assert has_critical_issues(alerts) is True

    def test_has_critical_issues_false_when_only_info(self):
        alerts = [PlausibilityAlert("T", "c", "INFO", "m")]
        assert has_critical_issues(alerts) is False

    def test_no_alerts_for_clean_snapshot(self):
        """Snapshot limpo não deve gerar alertas."""
        checker = PlausibilityChecker()
        clean = _snap(
            revenue=100e9,
            ebitda=25e9,
            net_income=10e9,
            equity=50e9,
            assets=200e9,
            liabilities=150e9,
            market_cap=100e9,
            shares_outstanding=1e9,
            gross_margin=0.40,
            ebitda_margin=0.25,
            net_margin=0.10,
            roe=0.20,
            debt_ebitda=2.0,
            valuation_multiples={"pe": 10.0, "pb": 2.0, "ev_ebitda": 8.0},
            period_type="DFP",
            industry="industrial",
        )
        alerts = checker.check(clean)
        # Apenas alertas de nível INFO são aceitáveis
        errors = [a for a in alerts if a.severity in ("CRITICAL", "ERROR")]
        assert not errors, f"Snapshot limpo não deveria ter CRITICAL/ERROR: {[a.check_name for a in errors]}"


class TestRealWorldCases:
    """Casos inspirados em dados reais da B3."""

    def test_itub4_bank_profile(self):
        """ITUB4: banco com P/L e P/VP, sem EV/EBITDA."""
        checker = PlausibilityChecker()
        snap = _snap(
            ticker="ITUB4",
            industry="bank",
            revenue=387e9,  # Resultado total de intermediação financeira
            net_income=46e9,
            equity=218e9,
            assets=2900e9,
            liabilities=2682e9,
            market_cap=210e9,
            shares_outstanding=5404e6,
            roe=0.21,
            debt_ebitda=None,
            ebitda=None,
            ebitda_margin=None,
            valuation_multiples={"pe": 4.6, "pb": 0.96, "ev_ebitda": None},
            period_type="DFP",
        )
        alerts = checker.check(snap)
        # Não deve ter erro por falta de EV/EBITDA
        ev_errors = [a for a in alerts if a.check_name == "bank_ev_ebitda_invalid"]
        assert not ev_errors

    def test_petr4_correct_revenue(self):
        """PETR4: receita 497.5B, lucro 110.6B — margens normais."""
        checker = PlausibilityChecker()
        snap = _snap(
            ticker="PETR4",
            industry="oil",
            revenue=497.5e9,
            ebitda=230e9,
            net_income=110.6e9,
            equity=417e9,
            assets=1223e9,
            liabilities=806e9,
            market_cap=249.6e9,
            shares_outstanding=5447e6,
            ebitda_margin=0.46,
            net_margin=0.22,
            roe=0.265,
            debt_ebitda=1.5,
            valuation_multiples={"pe": 2.3, "pb": 0.6, "ev_ebitda": 3.2},
            period_type="DFP",
        )
        alerts = checker.check(snap)
        errors = [a for a in alerts if a.severity in ("CRITICAL", "ERROR")]
        assert not errors, f"PETR4 limpo não deveria ter CRITICAL/ERROR: {[a.check_name for a in errors]}"

    def test_inflated_revenue_detected(self):
        """Receita inflada 5x (como o bug do snapshot_builder) deve gerar alertas."""
        checker = PlausibilityChecker()
        # PETR4 com revenue inflado de 497B para 2443B
        snap = _snap(
            ticker="PETR4",
            industry="oil",
            revenue=2443.6e9,   # inflado 5x
            ebitda=1150e9,      # inflado
            net_income=589.6e9, # inflado 5x
            equity=833e9,       # inflado 2x
            assets=2503e9,      # inflado 2x
            liabilities=3087e9, # inflado 2x — balanço não fecha!
            market_cap=249.6e9,
            ebitda_margin=0.47,
            net_margin=0.24,    # 24% — plausível individualmente
            roe=0.71,           # muito alto
            debt_ebitda=0.7,
            valuation_multiples={"pe": 0.42, "pb": 0.30, "ev_ebitda": 1.2},
            period_type="DFP",
        )
        alerts = checker.check(snap)
        # Deve ter pelo menos alerta de balanço não fechado
        assert any(a.check_name == "balance_sheet_imbalance" for a in alerts), \
            "Inflação de valores deve ser detectada pelo balanço não fechado"
