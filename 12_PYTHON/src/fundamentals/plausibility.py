"""
plausibility.py
---------------
Validação de plausibilidade de dados fundamentalistas.

Detecta valores implausíveis gerados por:
  - Double-counting no mapper (parent + child accounts somados)
  - ITR trimestral tratado como dado anual
  - Shares incorretas ou market cap impossível
  - Ratios matematicamente impossíveis

Uso:
    from src.fundamentals.plausibility import PlausibilityChecker, PlausibilityAlert

    checker = PlausibilityChecker()
    alerts = checker.check(snapshot)
    for alert in alerts:
        print(alert.severity, alert.message)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

AlertSeverity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class PlausibilityAlert:
    """Alerta gerado pela validação de plausibilidade."""
    ticker: str
    check_name: str
    severity: AlertSeverity
    message: str
    metric: str | None = None
    actual_value: float | None = None
    reference_value: float | None = None
    remediation: str = ""


class PlausibilityChecker:
    """
    Valida um conjunto de métricas fundamentalistas para detectar anomalias.

    Pode receber um FundamentalSnapshot (importado dinamicamente para evitar
    dependência circular) ou um dict de métricas.
    """

    # ── Limites de plausibilidade ────────────────────────────────────────────

    # Margens (% da receita): máximos plausíveis
    MARGIN_MAX = {
        "gross_margin":  1.20,   # 120% — externo apenas para royalties / IP
        "ebitda_margin": 0.95,   # 95%
        "net_margin":    0.80,   # 80%
        "roe":           2.00,   # 200% — altamente alavancadas
    }

    # Alavancagem máxima (DívLíq/EBITDA)
    LEVERAGE_MAX = 25.0

    # P/E máximo razoável
    PE_MAX = 200.0

    # P/VPA máximo razoável (exceto bancos)
    PB_MAX = 30.0

    # EV/EBITDA máximo razoável
    EV_EBITDA_MAX = 80.0

    # Crescimento YoY máximo suspeito (500% = 5x)
    GROWTH_SUSPECT = 5.0

    # Mercado: market cap mínimo (R$ 50M) e máximo (R$ 3T)
    MKTCAP_MIN = 50_000_000.0
    MKTCAP_MAX = 3_000_000_000_000.0

    # Revenue mínimo para empresa operacional (R$ 1M)
    REVENUE_MIN = 1_000_000.0

    def check(self, data: Any) -> list[PlausibilityAlert]:
        """
        Executa todas as verificações de plausibilidade.

        Args:
            data: FundamentalSnapshot OU dict com campos do snapshot.

        Returns:
            Lista de PlausibilityAlert (pode ser vazia se tudo ok).
        """
        if hasattr(data, "__dict__"):
            d = data.__dict__
            ticker = getattr(data, "ticker", "UNKNOWN")
            is_bank = str(getattr(data, "industry", "") or "").lower() in {"bank", "banco"}
            period_type = getattr(data, "period_type", "DFP")
        else:
            d = data
            ticker = d.get("ticker", "UNKNOWN")
            is_bank = str(d.get("industry", "") or "").lower() in {"bank", "banco"}
            period_type = d.get("period_type", "DFP")

        alerts: list[PlausibilityAlert] = []

        def alert(
            check_name: str,
            severity: AlertSeverity,
            message: str,
            metric: str | None = None,
            actual: float | None = None,
            ref: float | None = None,
            remediation: str = "",
        ) -> None:
            alerts.append(PlausibilityAlert(
                ticker=ticker,
                check_name=check_name,
                severity=severity,
                message=message,
                metric=metric,
                actual_value=actual,
                reference_value=ref,
                remediation=remediation,
            ))

        # ── 1. Receita negativa para empresa operacional ───────────────────────
        revenue = d.get("revenue")
        if revenue is not None and not is_bank:
            if revenue < 0:
                alert(
                    "negative_revenue",
                    "ERROR",
                    f"Receita negativa ({revenue:,.0f}) para empresa operacional",
                    "revenue", revenue, 0,
                    "Verificar mapeamento de contas — possível inversão de sinal",
                )
            elif revenue > 0 and revenue < self.REVENUE_MIN:
                alert(
                    "suspiciously_low_revenue",
                    "WARNING",
                    f"Receita muito baixa ({revenue:,.0f}) — pode ser erro de unidade",
                    "revenue", revenue, self.REVENUE_MIN,
                )

        # ── 2. Margens implausíveis ───────────────────────────────────────────
        if revenue and revenue > 0:
            for margin_field, max_val in self.MARGIN_MAX.items():
                val = d.get(margin_field)
                if val is not None and abs(val) > max_val:
                    alert(
                        f"implausible_{margin_field}",
                        "ERROR",
                        f"{margin_field}={val:.1%} excede limite de plausibilidade ({max_val:.0%})",
                        margin_field, val, max_val,
                        "Verificar double-counting no mapper ou período incorreto",
                    )

        # ── 3. ROE/ROA impossível ─────────────────────────────────────────────
        roe = d.get("roe")
        if roe is not None and abs(roe) > 2.0:  # 200%
            alert(
                "implausible_roe",
                "ERROR",
                f"ROE={roe:.1%} — valor implausível (>200% ou <-200%)",
                "roe", roe, None,
                "Verificar patrimônio líquido e lucro líquido",
            )

        # ── 4. Alavancagem absurda ─────────────────────────────────────────────
        if not is_bank:
            nd_ebitda = d.get("debt_ebitda")
            if nd_ebitda is not None and nd_ebitda > self.LEVERAGE_MAX:
                alert(
                    "extreme_leverage",
                    "ERROR",
                    f"Dívida Líquida/EBITDA={nd_ebitda:.1f}x — valor extremo",
                    "debt_ebitda", nd_ebitda, self.LEVERAGE_MAX,
                    "Verificar cálculo de net_debt e ebitda",
                )

        # ── 5. EV/EBITDA negativo ou extremo ──────────────────────────────────
        ev_ebitda = d.get("valuation_multiples", {}).get("ev_ebitda") if hasattr(d.get("valuation_multiples"), "get") else None
        if ev_ebitda is not None:
            if ev_ebitda < 0:
                alert(
                    "negative_ev_ebitda",
                    "WARNING",
                    f"EV/EBITDA={ev_ebitda:.1f}x negativo — empresa com net_debt negativo ou EBITDA negativo",
                    "ev_ebitda", ev_ebitda, None,
                    "Marcar como situação especial no relatório",
                )
            elif ev_ebitda > self.EV_EBITDA_MAX:
                alert(
                    "extreme_ev_ebitda",
                    "ERROR",
                    f"EV/EBITDA={ev_ebitda:.1f}x — valor extremo",
                    "ev_ebitda", ev_ebitda, self.EV_EBITDA_MAX,
                    "Verificar enterprise_value e ebitda",
                )

        # ── 6. P/E implausível ────────────────────────────────────────────────
        pe = d.get("valuation_multiples", {}).get("pe") if hasattr(d.get("valuation_multiples"), "get") else None
        if pe is not None and pe > self.PE_MAX:
            alert(
                "extreme_pe",
                "WARNING",
                f"P/E={pe:.1f}x — valor muito alto",
                "pe", pe, self.PE_MAX,
                "Verificar net_income (pode ser muito baixo) e market_cap",
            )
        if pe is not None and pe < 0:
            alert(
                "negative_pe",
                "INFO",
                f"P/E={pe:.1f}x negativo — empresa com lucro negativo",
                "pe", pe, None,
            )

        # ── 7. Banco sem EV/EBITDA como métrica principal ─────────────────────
        if is_bank:
            vm = d.get("valuation_multiples") or {}
            if hasattr(vm, "get"):
                ev_val = vm.get("ev_ebitda")
                if ev_val is not None and ev_val != 0:
                    alert(
                        "bank_ev_ebitda_invalid",
                        "ERROR",
                        f"EV/EBITDA calculado para banco ({ticker}) — métrica não aplicável",
                        "ev_ebitda", ev_val, None,
                        "Remover EV/EBITDA para bancos e usar P/L e P/VP",
                    )

        # ── 8. Dado trimestral comparado como anual ───────────────────────────
        if period_type == "ITR_PARTIAL":
            # Emitir alerta informativo
            alert(
                "partial_period",
                "WARNING",
                "Dados parciais (ITR_PARTIAL) — não comparar com dados anuais sem ajuste",
                "period_type", None, None,
                "Usar LTM ou DFP anual para comparações entre empresas",
            )

        # ── 9. Market cap implausível ──────────────────────────────────────────
        market_cap = d.get("market_cap")
        if market_cap is not None:
            if market_cap < self.MKTCAP_MIN:
                alert(
                    "suspiciously_low_market_cap",
                    "ERROR",
                    f"Market Cap={market_cap/1e6:.1f}M — suspeito de erro de unidade ou shares incorretas",
                    "market_cap", market_cap, self.MKTCAP_MIN,
                    "Verificar shares_outstanding e preço",
                )
            elif market_cap > self.MKTCAP_MAX:
                alert(
                    "extreme_market_cap",
                    "ERROR",
                    f"Market Cap={market_cap/1e12:.1f}T — valor extremo",
                    "market_cap", market_cap, self.MKTCAP_MAX,
                )

        # ── 10. Shares_outstanding ausente (impede P/L, P/VP) ─────────────────
        shares = d.get("shares_outstanding")
        if shares is None:
            alert(
                "missing_shares",
                "WARNING",
                "shares_outstanding não disponível — P/L e P/VP não calculáveis",
                "shares_outstanding", None, None,
                "Buscar shares via yfinance ou CVM FRE",
            )

        # ── 11. Ativo total vs Passivo + PL ───────────────────────────────────
        assets = d.get("assets")
        liabilities = d.get("liabilities")
        equity = d.get("equity")
        if assets and liabilities and equity:
            diff = assets - (liabilities + equity)
            tol = abs(assets) * 0.05  # 5% de tolerância
            if abs(diff) > tol and abs(diff) > 1e6:
                alert(
                    "balance_sheet_imbalance",
                    "ERROR",
                    f"Balanço não fecha: Ativo={assets/1e9:.1f}B vs Passivo+PL={((liabilities or 0)+(equity or 0))/1e9:.1f}B",
                    "assets", diff, 0,
                    "Verificar double-counting — mapper pode estar somando contas-pai e filhas",
                )

        # ── 12. EBITDA > Receita (impossível para negócios reais) ─────────────
        ebitda = d.get("ebitda")
        if ebitda and revenue and revenue > 0:
            if ebitda > revenue:
                alert(
                    "ebitda_exceeds_revenue",
                    "CRITICAL",
                    f"EBITDA ({ebitda/1e9:.1f}B) > Receita ({revenue/1e9:.1f}B) — impossível",
                    "ebitda", ebitda, revenue,
                    "Erro de mapeamento. Verificar contas de EBITDA e receita",
                )

        # ── 13. Net income > Revenue (muito suspeito) ─────────────────────────
        net_income = d.get("net_income")
        if net_income and revenue and revenue > 0:
            if net_income > revenue * 0.80:
                alert(
                    "net_income_close_to_revenue",
                    "ERROR",
                    f"Lucro Líquido ({net_income/1e9:.1f}B) > 80% da Receita ({revenue/1e9:.1f}B)",
                    "net_income", net_income, revenue * 0.80,
                    "Verificar double-counting — mapper pode estar somando 3.09+3.11+4.01",
                )

        return alerts


def check_snapshot(snapshot: Any) -> list[PlausibilityAlert]:
    """Atalho: cria PlausibilityChecker e executa verificação."""
    return PlausibilityChecker().check(snapshot)


def classify_alerts(
    alerts: list[PlausibilityAlert],
) -> dict[str, list[PlausibilityAlert]]:
    """Agrupa alertas por severidade."""
    result: dict[str, list[PlausibilityAlert]] = {
        "CRITICAL": [],
        "ERROR": [],
        "WARNING": [],
        "INFO": [],
    }
    for a in alerts:
        result.setdefault(a.severity, []).append(a)
    return result


def has_critical_issues(alerts: list[PlausibilityAlert]) -> bool:
    """Retorna True se houver algum CRITICAL ou ERROR."""
    return any(a.severity in ("CRITICAL", "ERROR") for a in alerts)


def format_alert_report(
    alerts: list[PlausibilityAlert],
    ticker: str,
) -> str:
    """Formata relatório de alertas em texto."""
    if not alerts:
        return f"✅ {ticker}: sem alertas de plausibilidade"

    lines = [f"🔍 Relatório de Plausibilidade — {ticker}", ""]
    by_sev = classify_alerts(alerts)

    icons = {"CRITICAL": "🚨", "ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
    for sev in ("CRITICAL", "ERROR", "WARNING", "INFO"):
        for a in by_sev.get(sev, []):
            icon = icons.get(sev, "")
            line = f"  {icon} [{sev}] {a.check_name}: {a.message}"
            if a.remediation:
                line += f"\n       → {a.remediation}"
            lines.append(line)

    return "\n".join(lines)
