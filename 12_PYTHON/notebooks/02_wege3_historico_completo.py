"""
02_wege3_historico_completo.py
-------------------------------
Extrai DFP 2019–2025 da WEG (código CVM 005410) e produz
uma tabela histórica completa de indicadores.

Uso:
    python -X utf8 notebooks/02_wege3_historico_completo.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.cvm_downloader import CVMDownloader
from parsers.dfp_parser import DFPParser
from normalization.account_mapper import AccountMapper
from validation.reconciler import Reconciler
from validation.schemas import (
    ExtractionMetadata, IncomeStatement, Assets, Liabilities,
    BalanceSheet, CashFlowStatement, FinancialStatements,
    FinancialIndicators, Consolidation, DocType, Periodicity,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")

WEGE_CVM_CODE = "005410"
YEARS = list(range(2019, 2026))   # 2019 a 2025 inclusive
RAW_DIR = Path("data/raw/cvm")


def get(d: dict, key: str, default: float = 0.0) -> float:
    return d.get(key) if d.get(key) is not None else default


def build_statements(year: int, dfs: dict) -> FinancialStatements | None:
    mapper = AccountMapper()
    mapped = {name: mapper.to_dict(df) for name, df in dfs.items()}
    dre = mapped.get("DRE", {})
    bpa = mapped.get("BPA", {})
    bpp = mapped.get("BPP", {})
    dfc = mapped.get("DFC", {})

    if not dre or not get(dre, "net_revenue"):
        return None

    da = dfc.get("depreciation_amortization_cfo")
    total_equity = get(bpp, "total_equity")
    minority_bs = bpp.get("minority_interest_bs") or 0.0
    shareholders_equity = total_equity - minority_bs

    try:
        meta = ExtractionMetadata(
            ticker="WEGE3", company_name="WEG S.A.",
            period=f"{year}A", consolidation=Consolidation.CONSOLIDATED,
            source=f"CVM DFP {year}", periodicity=Periodicity.ANNUAL,
            doc_type=DocType.DFP, unit=1000,
        )
        income = IncomeStatement(
            net_revenue=get(dre, "net_revenue"),
            cogs=dre.get("cogs"),
            gross_profit=dre.get("gross_profit"),
            selling_expenses=dre.get("selling_expenses"),
            general_admin_expenses=dre.get("general_admin_expenses"),
            other_operating_income=dre.get("other_operating_income"),
            equity_income=dre.get("equity_income"),
            depreciation_amortization=da,
            ebit=dre.get("ebit"),
            financial_income=dre.get("financial_income"),
            financial_expenses=dre.get("financial_expenses"),
            net_financial_result=dre.get("net_financial_result"),
            ebt=dre.get("ebt"),
            income_tax=dre.get("income_tax"),
            net_income_consolidated=dre.get("net_income_consolidated"),
            minority_interest=dre.get("minority_interest"),
            net_income=get(dre, "net_income"),
        )
        assets = Assets(
            cash=get(bpa, "cash"),
            short_term_investments=bpa.get("short_term_investments"),
            accounts_receivable=bpa.get("accounts_receivable"),
            inventories=bpa.get("inventories"),
            total_current_assets=bpa.get("total_current_assets"),
            equity_investments=bpa.get("equity_investments"),
            ppe_net=bpa.get("ppe_net"),
            intangibles_net=bpa.get("intangibles_net"),
            total_non_current_assets=bpa.get("total_non_current_assets"),
            total_assets=get(bpa, "total_current_assets", 0) + get(bpa, "total_non_current_assets", 0)
                         or get(bpa, "total_assets", 1),
        )
        liabilities = Liabilities(
            suppliers=bpp.get("suppliers"),
            short_term_debt=bpp.get("short_term_debt"),
            total_current_liabilities=bpp.get("total_current_liabilities"),
            long_term_debt=bpp.get("long_term_debt"),
            total_non_current_liabilities=bpp.get("total_non_current_liabilities"),
            minority_interest_bs=minority_bs or None,
            shareholders_equity=shareholders_equity,
            total_equity=total_equity,
            total_liabilities_and_equity=assets.total_assets,
        )
        balance = BalanceSheet(assets=assets, liabilities=liabilities)
        cashflow = CashFlowStatement(
            cfo=get(dfc, "cfo"),
            net_income_cfo=dfc.get("net_income_cfo"),
            depreciation_amortization_cfo=da,
            working_capital_changes=dfc.get("working_capital_changes"),
            capex=dfc.get("capex"),
            cfi=get(dfc, "cfi"),
            debt_issuance=dfc.get("debt_issuance"),
            debt_repayment=dfc.get("debt_repayment"),
            dividends_paid=dfc.get("dividends_paid"),
            cff=get(dfc, "cff"),
            forex_effect_on_cash=dfc.get("forex_effect_on_cash"),
            beginning_cash=get(dfc, "beginning_cash"),
            ending_cash=get(dfc, "ending_cash", assets.cash),
        )
        return FinancialStatements(
            metadata=meta, income_statement=income,
            balance_sheet=balance, cash_flow=cashflow,
        )
    except Exception as e:
        print(f"  [ERRO] {year}: {e}")
        return None


def fmt_brl(v, scale=1_000_000) -> str:
    """Formata em R$ bilhões com 1 casa decimal."""
    if v is None or v == 0:
        return "—"
    return f"{v / scale:,.1f}"


def fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1%}"


def fmt_x(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}x"


def fmt_dias(v) -> str:
    if v is None:
        return "—"
    return f"{int(v)}d"


def main():
    dl = CVMDownloader(output_dir=RAW_DIR)
    parser = DFPParser()
    reconciler = Reconciler()

    results: dict[int, FinancialStatements] = {}
    recon_results: dict[int, str] = {}

    print(f"\nDownload e extração DFP — WEGE3 — {YEARS[0]} a {YEARS[-1]}")
    print("=" * 60)

    for year in YEARS:
        print(f"\n[{year}] ", end="", flush=True)
        try:
            dl.download_dfp(year)
        except Exception as e:
            print(f"download falhou: {e}")
            continue

        dfs = parser.parse_company(
            WEGE_CVM_CODE,
            raw_dir=RAW_DIR / "DFP" / str(year),
            consolidation="con",
        )
        if not dfs:
            print("sem dados")
            continue

        stmts = build_statements(year, dfs)
        if stmts is None:
            print("parse falhou")
            continue

        report = reconciler.run(stmts)
        status = "OK" if report.blocking_errors == 0 else f"{report.blocking_errors} ERRO(S) CRITICO(S)"
        print(f"{status} | {report.warnings} aviso(s)")
        results[year] = stmts
        recon_results[year] = status

    if not results:
        print("\nNenhum dado extraido.")
        return

    # ------------------------------------------------------------------
    # Tabelas de saída
    # ------------------------------------------------------------------
    years_ok = sorted(results.keys())
    prev: dict[int, FinancialStatements] = {}
    for i, y in enumerate(years_ok):
        if i > 0:
            prev[y] = results[years_ok[i - 1]]

    indicators: dict[int, FinancialIndicators] = {
        y: FinancialIndicators.from_statements(results[y], prev.get(y))
        for y in years_ok
    }

    header = "| Linha" + "".join(f" | {y}" for y in years_ok) + " |"
    sep    = "|---"   + "|---" * len(years_ok) + "|"

    def row(label, vals):
        return "| " + label + " | " + " | ".join(vals) + " |"

    print("\n\n" + "=" * 80)
    print("  RESULTADOS — WEGE3  |  R$ bilhões")
    print("=" * 80)

    # DRE
    print("\n### DRE (R$ bi)")
    print(header); print(sep)
    i  = {y: results[y].income_statement for y in years_ok}
    print(row("Receita Líquida",    [fmt_brl(i[y].net_revenue)       for y in years_ok]))
    print(row("Lucro Bruto",        [fmt_brl(i[y].gross_profit)       for y in years_ok]))
    print(row("EBIT",               [fmt_brl(i[y].ebit)               for y in years_ok]))
    print(row("D&A",                [fmt_brl(i[y].depreciation_amortization) for y in years_ok]))
    print(row("EBITDA",             [fmt_brl(i[y].ebitda)             for y in years_ok]))
    print(row("Res. Financeiro",    [fmt_brl(i[y].net_financial_result) for y in years_ok]))
    print(row("Lucro Líquido",      [fmt_brl(i[y].net_income)         for y in years_ok]))

    # Margens
    print("\n### Margens")
    print(header); print(sep)
    print(row("Margem Bruta",   [fmt_pct(i[y].gross_margin)   for y in years_ok]))
    print(row("Margem EBITDA",  [fmt_pct(i[y].ebitda_margin)  for y in years_ok]))
    print(row("Margem EBIT",    [fmt_pct(i[y].ebit_margin)    for y in years_ok]))
    print(row("Margem Líquida", [fmt_pct(i[y].net_margin)     for y in years_ok]))

    # BP
    b = {y: results[y].balance_sheet for y in years_ok}
    print("\n### Balanço (R$ bi)")
    print(header); print(sep)
    print(row("Caixa + Aplic.",      [fmt_brl(b[y].assets.cash)                        for y in years_ok]))
    print(row("Contas a Receber",    [fmt_brl(b[y].assets.accounts_receivable)         for y in years_ok]))
    print(row("Estoques",            [fmt_brl(b[y].assets.inventories)                 for y in years_ok]))
    print(row("Total Ativo",         [fmt_brl(b[y].assets.total_assets)                for y in years_ok]))
    print(row("Dívida CP",           [fmt_brl(b[y].liabilities.short_term_debt)        for y in years_ok]))
    print(row("Dívida LP",           [fmt_brl(b[y].liabilities.long_term_debt)         for y in years_ok]))
    print(row("PL (controladora)",   [fmt_brl(b[y].liabilities.shareholders_equity)    for y in years_ok]))
    print(row("**Dívida Líquida**",  [fmt_brl(b[y].net_debt)                           for y in years_ok]))

    # DFC
    c = {y: results[y].cash_flow for y in years_ok}
    print("\n### Fluxo de Caixa (R$ bi)")
    print(header); print(sep)
    print(row("CFO",            [fmt_brl(c[y].cfo)           for y in years_ok]))
    print(row("Capex",          [fmt_brl(c[y].capex)         for y in years_ok]))
    print(row("FCFF",           [fmt_brl(c[y].fcff)          for y in years_ok]))
    print(row("Dividendos",     [fmt_brl(c[y].dividends_paid) for y in years_ok]))

    # Indicadores
    print("\n### Indicadores")
    print(header); print(sep)
    print(row("ROE",              [fmt_pct(indicators[y].roe)              for y in years_ok]))
    print(row("ROA",              [fmt_pct(indicators[y].roa)              for y in years_ok]))
    print(row("Dív/EBITDA",       [fmt_x(indicators[y].net_debt_ebitda)    for y in years_ok]))
    print(row("Prazo Receb.",     [fmt_dias(indicators[y].receivables_days) for y in years_ok]))
    print(row("Prazo Estoque",    [fmt_dias(indicators[y].inventory_days)   for y in years_ok]))
    print(row("Prazo Pgto",       [fmt_dias(indicators[y].payables_days)    for y in years_ok]))
    print(row("Ciclo de Caixa",   [fmt_dias(indicators[y].cash_conversion_cycle) for y in years_ok]))
    print(row("Margem FCFF",      [fmt_pct(indicators[y].fcff_margin)      for y in years_ok]))

    # Reconciliação
    print("\n### Reconciliação")
    print(header); print(sep)
    print(row("Status",  [recon_results.get(y, "—") for y in years_ok]))

    # Retornar os dados para uso externo
    return results, indicators


if __name__ == "__main__":
    main()
