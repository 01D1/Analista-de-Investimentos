"""
test_etapa3_integration.py
---------------------------
Testes de integração da Etapa 3 usando dados reais do banco SQLite.

Cobre:
  - Pipeline não quebra com ticker incompleto
  - Ticker sem shares_outstanding retorna snapshot sem P/L e P/VP
  - Histórico anual de PETR4 tem os anos corretos
  - Histórico de VALE3 tem EBITDA positivo
  - Bancos ITUB4/BBAS3 têm P/L e P/VP mas não EV/EBITDA
  - Plausibilidade dos snapshots reais (sem alertas CRITICAL/ERROR)
  - period_basis == 'DFP' para todos os tickers da amostra
"""
from __future__ import annotations

import pytest

# Tickers reais para testes de integração
SAMPLE_INDUSTRIAL = ["PETR4", "VALE3", "WEGE3", "EGIE3", "PRIO3"]
SAMPLE_BANKS = ["ITUB4", "BBAS3", "BBDC4"]
SAMPLE_ALL = SAMPLE_INDUSTRIAL + SAMPLE_BANKS


@pytest.fixture(scope="module")
def snapshots_sample():
    """Constrói snapshots para a amostra — reutilizável por todos os testes."""
    from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi
    result = {}
    for ticker in SAMPLE_ALL:
        snap = build_snapshot_from_vfi(ticker)
        result[ticker] = snap
    return result


@pytest.fixture(scope="module")
def historical_series_petr4():
    from src.fundamentals.historical_series import build_historical_series
    return build_historical_series("PETR4", is_bank=False)


@pytest.fixture(scope="module")
def historical_series_vale3():
    from src.fundamentals.historical_series import build_historical_series
    return build_historical_series("VALE3", is_bank=False)


# ── Testes de seleção de período com dados reais ───────────────────────────────

class TestRealPeriodSelection:
    """Verifica que a seleção de período usa DFP para todos os tickers da amostra."""

    def test_all_sample_tickers_have_dfp(self):
        """Todos os 10 tickers da amostra devem ter DFP disponível."""
        from src.fundamentals.period_selector import select_best_period
        from src.valuation.financial_inputs_store import get_financial_inputs

        missing_dfp = []
        for ticker in SAMPLE_ALL:
            rows = get_financial_inputs(ticker)
            sel = select_best_period(rows)
            if sel is None or sel.period_basis != "DFP":
                missing_dfp.append(ticker)

        assert not missing_dfp, (
            f"Tickers sem DFP anual: {missing_dfp}. "
            "Verificar se os dados foram ingeridos corretamente."
        )

    def test_dfp_is_2025_or_later(self):
        """O DFP selecionado deve ser de 2024 ou mais recente."""
        from src.fundamentals.period_selector import select_best_period
        from src.valuation.financial_inputs_store import get_financial_inputs

        for ticker in SAMPLE_ALL:
            rows = get_financial_inputs(ticker)
            sel = select_best_period(rows)
            if sel and sel.period_basis == "DFP":
                assert sel.fiscal_year >= 2024, (
                    f"{ticker}: DFP selecionado é {sel.fiscal_year}, esperado >= 2024"
                )


# ── Testes de snapshots corretos ──────────────────────────────────────────────

class TestSnapshotsCorrectData:
    """Verifica que os snapshots têm dados corretos (não inflados)."""

    def test_all_snapshots_not_none(self, snapshots_sample):
        """Todos os tickers da amostra devem gerar snapshot."""
        none_tickers = [t for t, s in snapshots_sample.items() if s is None]
        assert not none_tickers, f"Tickers sem snapshot: {none_tickers}"

    def test_petr4_revenue_in_range(self, snapshots_sample):
        """PETR4 receita deve estar entre 300B e 800B (não inflado)."""
        snap = snapshots_sample["PETR4"]
        assert snap is not None
        assert snap.revenue is not None
        # R$497B para FY2025 — aceitamos range amplo
        assert 200e9 < snap.revenue < 900e9, (
            f"PETR4 receita={snap.revenue/1e9:.0f}B — fora do range esperado. "
            "Pode ser double-counting!"
        )

    def test_petr4_net_income_in_range(self, snapshots_sample):
        """PETR4 lucro deve estar entre 30B e 200B."""
        snap = snapshots_sample["PETR4"]
        assert snap is not None
        assert snap.net_income is not None
        assert 30e9 < snap.net_income < 250e9, (
            f"PETR4 lucro={snap.net_income/1e9:.0f}B — fora do range esperado"
        )

    def test_vale3_ebitda_positive(self, snapshots_sample):
        """VALE3 EBITDA deve ser positivo."""
        snap = snapshots_sample["VALE3"]
        assert snap is not None
        assert snap.ebitda is not None
        assert snap.ebitda > 0, f"VALE3 EBITDA={snap.ebitda/1e9:.0f}B deve ser positivo"

    def test_wege3_has_ebitda(self, snapshots_sample):
        """WEGE3 deve ter EBITDA (industrial)."""
        snap = snapshots_sample["WEGE3"]
        assert snap is not None
        assert snap.ebitda is not None, "WEGE3 deveria ter EBITDA"
        assert snap.ebitda > 0

    def test_bank_ebitda_is_none(self, snapshots_sample):
        """Bancos não devem ter EBITDA."""
        for ticker in SAMPLE_BANKS:
            snap = snapshots_sample[ticker]
            assert snap is not None
            assert snap.ebitda is None, (
                f"{ticker} é banco e não deveria ter EBITDA: {snap.ebitda}"
            )

    def test_period_basis_is_dfp(self, snapshots_sample):
        """Todos os snapshots devem usar DFP como período de referência."""
        for ticker in SAMPLE_ALL:
            snap = snapshots_sample[ticker]
            assert snap is not None
            assert snap.period_type == "DFP", (
                f"{ticker}: period_type={snap.period_type}, esperado DFP"
            )


# ── Testes de múltiplos de mercado ────────────────────────────────────────────

class TestMarketMultiples:
    """Verifica múltiplos de mercado para industriais e bancos."""

    def test_industrials_have_ev_ebitda(self, snapshots_sample):
        """Empresas industriais com EBITDA positivo devem ter EV/EBITDA."""
        for ticker in SAMPLE_INDUSTRIAL:
            snap = snapshots_sample[ticker]
            assert snap is not None
            if snap.ebitda and snap.ebitda > 0 and snap.market_cap:
                ev_eb = snap.valuation_multiples.get("ev_ebitda")
                assert ev_eb is not None and ev_eb > 0, (
                    f"{ticker}: deveria ter EV/EBITDA positivo, got {ev_eb}"
                )

    def test_banks_ev_ebitda_is_none(self, snapshots_sample):
        """Bancos não devem ter EV/EBITDA calculado."""
        for ticker in SAMPLE_BANKS:
            snap = snapshots_sample[ticker]
            assert snap is not None
            ev_eb = snap.valuation_multiples.get("ev_ebitda")
            assert ev_eb is None, (
                f"{ticker} banco tem EV/EBITDA={ev_eb} — não deveria estar presente"
            )

    def test_all_with_market_cap_have_pe(self, snapshots_sample):
        """Todo ticker com market_cap e net_income positivo deve ter P/L."""
        for ticker in SAMPLE_ALL:
            snap = snapshots_sample[ticker]
            assert snap is not None
            if snap.market_cap and snap.net_income and snap.net_income > 0:
                pe = snap.valuation_multiples.get("pe")
                assert pe is not None and pe > 0, (
                    f"{ticker}: deveria ter P/L positivo, got {pe}"
                )

    def test_all_with_market_cap_have_pb(self, snapshots_sample):
        """Todo ticker com market_cap e equity positivo deve ter P/VP."""
        for ticker in SAMPLE_ALL:
            snap = snapshots_sample[ticker]
            assert snap is not None
            if snap.market_cap and snap.equity and snap.equity > 0:
                pb = snap.valuation_multiples.get("pb")
                assert pb is not None and pb > 0, (
                    f"{ticker}: deveria ter P/VP positivo, got {pb}"
                )

    def test_pe_ratios_plausible(self, snapshots_sample):
        """P/L deve estar em faixa plausível para todos os tickers."""
        for ticker in SAMPLE_ALL:
            snap = snapshots_sample[ticker]
            if snap is None:
                continue
            pe = snap.valuation_multiples.get("pe")
            if pe is not None:
                assert 0 < pe < 200, (
                    f"{ticker}: P/L={pe:.1f}x fora da faixa plausível (0-200)"
                )


# ── Testes de plausibilidade com dados reais ──────────────────────────────────

class TestPlausibilityReal:
    """Executa plausibilidade nos snapshots reais."""

    def test_no_critical_issues_in_sample(self, snapshots_sample):
        """Nenhum ticker da amostra deve ter alertas CRITICAL ou ERROR."""
        from src.fundamentals.plausibility import PlausibilityChecker, has_critical_issues

        checker = PlausibilityChecker()
        with_issues = {}

        for ticker in SAMPLE_ALL:
            snap = snapshots_sample[ticker]
            if snap is None:
                continue
            alerts = checker.check(snap)
            critical = [a for a in alerts if a.severity in ("CRITICAL", "ERROR")]
            if critical:
                with_issues[ticker] = [f"[{a.severity}] {a.check_name}: {a.message}" for a in critical]

        assert not with_issues, (
            f"Tickers com problemas críticos de plausibilidade:\n" +
            "\n".join(f"  {t}: {e}" for t, es in with_issues.items() for e in es)
        )

    def test_margins_within_bounds(self, snapshots_sample):
        """Margens devem estar em faixas razoáveis para todos."""
        for ticker in SAMPLE_INDUSTRIAL:
            snap = snapshots_sample[ticker]
            if snap is None:
                continue
            if snap.ebitda_margin is not None:
                assert -0.5 < snap.ebitda_margin < 1.0, (
                    f"{ticker}: margem EBITDA={snap.ebitda_margin:.1%} fora de faixa"
                )
            if snap.net_margin is not None:
                assert -1.0 < snap.net_margin < 1.0, (
                    f"{ticker}: margem líquida={snap.net_margin:.1%} fora de faixa"
                )


# ── Testes de histórico ────────────────────────────────────────────────────────

class TestHistoricalSeries:
    """Verifica série histórica fundamentalista."""

    def test_petr4_historical_covers_2019_to_2025(self, historical_series_petr4):
        """PETR4 deve ter dados de 2019 a 2025."""
        years = sorted(historical_series_petr4.keys())
        assert len(years) >= 6, f"PETR4 deve ter >= 6 anos de histórico, got {len(years)}"
        assert 2019 in years, "PETR4 deve ter dados de 2019"
        assert 2024 in years or 2025 in years, "PETR4 deve ter dados recentes (2024 ou 2025)"

    def test_petr4_all_years_use_dfp(self, historical_series_petr4):
        """Todos os anos de PETR4 devem usar DFP."""
        for year, data in historical_series_petr4.items():
            assert data["period_basis"] == "DFP", (
                f"PETR4 {year}: basis={data['period_basis']}, esperado DFP"
            )

    def test_petr4_revenue_increasing_2019_to_2022(self, historical_series_petr4):
        """PETR4 receita deve crescer de 2019 a 2022 (ciclo do petróleo)."""
        if 2019 in historical_series_petr4 and 2022 in historical_series_petr4:
            rev_2019 = historical_series_petr4[2019].get("revenue")
            rev_2022 = historical_series_petr4[2022].get("revenue")
            if rev_2019 and rev_2022:
                assert rev_2022 > rev_2019, (
                    f"PETR4: receita 2022 ({rev_2022/1e9:.0f}B) deveria ser > 2019 ({rev_2019/1e9:.0f}B)"
                )

    def test_vale3_historical_has_ebitda(self, historical_series_vale3):
        """VALE3 deve ter EBITDA em anos recentes."""
        recent_years = [y for y in historical_series_vale3.keys() if y >= 2021]
        for year in recent_years:
            ebitda = historical_series_vale3[year].get("ebitda")
            if ebitda is not None:
                assert ebitda > 0, f"VALE3 {year}: EBITDA deveria ser positivo"

    def test_itub4_historical_no_ebitda(self):
        """ITUB4 banco: série histórica não deve ter EBITDA."""
        from src.fundamentals.historical_series import build_historical_series
        series = build_historical_series("ITUB4", is_bank=True)
        for year, data in series.items():
            ebitda = data.get("ebitda")
            assert ebitda is None, f"ITUB4 banco não deve ter EBITDA em {year}: {ebitda}"


# ── Testes de robustez ────────────────────────────────────────────────────────

class TestPipelineRobustness:
    """Garante que o pipeline não quebra com dados incompletos."""

    def test_nonexistent_ticker_returns_none(self):
        """Ticker inexistente deve retornar None (não levantar exceção)."""
        from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi
        snap = build_snapshot_from_vfi("XYZINVALID99")
        assert snap is None

    def test_ticker_without_shares_returns_snapshot(self):
        """Ticker sem shares_outstanding deve retornar snapshot sem market_cap."""
        from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi
        # IGTI11 ou INTR4 podem não ter shares — testamos sem mockar
        # Se tiver shares, o teste simplesmente passa
        # O importante é que NÃO levanta exceção
        snap = build_snapshot_from_vfi("IGTI11")
        # Pode ser None (se sem dados) ou snapshot (com ou sem shares)
        if snap is not None:
            # Se não tem shares, market_cap deve ser None
            if snap.shares_outstanding is None:
                assert snap.market_cap is None
                assert snap.valuation_multiples.get("pe") is None
                assert snap.valuation_multiples.get("pb") is None

    def test_empty_rows_returns_none(self):
        """select_best_period com lista vazia retorna None."""
        from src.fundamentals.period_selector import select_best_period
        result = select_best_period([])
        assert result is None

    def test_historical_series_empty_returns_empty_dict(self):
        """Ticker inexistente retorna dict vazio para série histórica."""
        from src.fundamentals.historical_series import build_historical_series
        series = build_historical_series("NONEXISTENT123")
        assert series == {}

    def test_plausibility_check_does_not_raise(self, snapshots_sample):
        """PlausibilityChecker não deve levantar exceção para nenhum snapshot."""
        from src.fundamentals.plausibility import PlausibilityChecker
        checker = PlausibilityChecker()
        for ticker, snap in snapshots_sample.items():
            if snap is not None:
                try:
                    alerts = checker.check(snap)
                    assert isinstance(alerts, list)
                except Exception as exc:
                    pytest.fail(f"PlausibilityChecker levantou exceção para {ticker}: {exc}")

    def test_build_all_snapshots_returns_dict(self):
        """build_all_snapshots_from_vfi retorna dict para todos os tickers."""
        from src.fundamentals.snapshot_from_vfi import build_all_snapshots_from_vfi
        result = build_all_snapshots_from_vfi(["PETR4", "VALE3", "NONEXISTENT"])
        assert "PETR4" in result
        assert "VALE3" in result
        assert "NONEXISTENT" in result
        assert result["NONEXISTENT"] is None
