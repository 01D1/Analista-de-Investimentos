"""
03_bancos_historico_completo.py
--------------------------------
Extrai DFP 2019–2025 para todos os bancos/financeiras cobertos e produz:
  1. Tabelas históricas por banco (DRE, Margens, BP, Indicadores)
  2. Tabela comparativa entre bancos para o último ano disponível

Bancos cobertos:
  ITUB4  BBAS3  BBDC4  SANB11  BPAC11
  INTR4  BRSR6  ABCB4  BMGB4  BPAN4  PINE4  ITSA4

Nota:
  ROXO34 (Nubank) não publica DFP no CVM — ver earnings releases no site de RI.

Uso:
    python -X utf8 notebooks/03_bancos_historico_completo.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.cvm_downloader import CVMDownloader
from parsers.bank_parser import BankParser, BANK_REGISTRY, UNSUPPORTED
from validation.bank_schemas import BankStatements, BankIndicators

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")

YEARS = list(range(2019, 2026))
RAW_DIR = Path("data/raw/cvm")

# Ordem de exibição
TICKERS = [
    "ITUB4", "BBAS3", "BBDC4", "SANB11",   # Grandes bancos
    "BPAC11",                                # Investimento
    "BRSR6", "ABCB4", "BMGB4", "BPAN4", "PINE4",  # Médios
    "INTR4", "ITSA4",                        # BDR / Holding
]


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def fmt_brl(v, scale=1_000_000) -> str:
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

def fmt_int(v) -> str:
    if v is None:
        return "—"
    return f"{int(v)}"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def download_all(dl: CVMDownloader):
    print("\nBaixando DFPs 2019–2025 (se necessario)...")
    for year in YEARS:
        try:
            dl.download_dfp(year)
            print(f"  {year} OK")
        except Exception as e:
            print(f"  {year} falhou: {e}")


def extract_bank(
    parser: BankParser,
    ticker: str,
    years: list[int],
) -> dict[int, BankStatements]:
    results = {}
    for year in years:
        raw_dir = RAW_DIR / "DFP" / str(year)
        stmts = parser.parse(ticker, year, raw_dir, consolidation="con")
        if stmts and stmts.income_statement.total_financial_revenues > 0:
            results[year] = stmts
    return results


def print_bank_history(ticker: str, results: dict[int, BankStatements]):
    years_ok = sorted(results.keys())
    if not years_ok:
        print(f"\n  {ticker}: sem dados\n")
        return

    prev: dict[int, BankStatements] = {}
    for i, y in enumerate(years_ok):
        if i > 0:
            prev[y] = results[years_ok[i - 1]]

    indicators: dict[int, BankIndicators] = {
        y: BankIndicators.from_statements(results[y], prev.get(y))
        for y in years_ok
    }

    name = BANK_REGISTRY[ticker]["name"]
    print(f"\n{'=' * 90}")
    print(f"  {ticker}  |  {name}")
    print(f"{'=' * 90}")

    header = "| Linha" + "".join(f" | {y}" for y in years_ok) + " |"
    sep    = "|---"   + "|---" * len(years_ok) + "|"

    def row(label, vals):
        return "| " + label + " | " + " | ".join(vals) + " |"

    i = {y: results[y].income_statement for y in years_ok}

    # DRE
    print("\n### DRE (R$ bi)")
    print(header); print(sep)
    print(row("Receitas Intermediação",  [fmt_brl(i[y].total_financial_revenues) for y in years_ok]))
    print(row("  Juros (bruto)",         [fmt_brl(i[y].interest_income)          for y in years_ok]))
    print(row("  Tarifas/Serviços",      [fmt_brl(i[y].fee_income)               for y in years_ok]))
    print(row("Desp. Intermediação",     [fmt_brl(i[y].total_financial_expenses)  for y in years_ok]))
    print(row("  Juros (custo)",         [fmt_brl(i[y].interest_expense)         for y in years_ok]))
    print(row("  PDD/Provisão",          [fmt_brl(i[y].loan_loss_provision)      for y in years_ok]))
    print(row("NII Bruto (pós-PDD)",     [fmt_brl(i[y].nii_gross)                for y in years_ok]))
    print(row("Desp. Pessoal",           [fmt_brl(i[y].personnel_expenses)       for y in years_ok]))
    print(row("Desp. Administrativas",   [fmt_brl(i[y].admin_expenses)           for y in years_ok]))
    print(row("EBT",                     [fmt_brl(i[y].ebt)                      for y in years_ok]))
    print(row("**Lucro Líquido**",        [fmt_brl(i[y].net_income)               for y in years_ok]))

    # Margens e Indicadores de Rentabilidade
    print("\n### Rentabilidade e Eficiência")
    print(header); print(sep)
    print(row("ROE",              [fmt_pct(indicators[y].roe)              for y in years_ok]))
    print(row("ROA",              [fmt_pct(indicators[y].roa)              for y in years_ok]))
    print(row("ROTE",             [fmt_pct(indicators[y].rote)             for y in years_ok]))
    print(row("Margem Líquida",   [fmt_pct(indicators[y].net_margin)       for y in years_ok]))
    print(row("Spread (NII/Rev)", [fmt_pct(indicators[y].nim_proxy)        for y in years_ok]))
    print(row("Índice Eficiência",[fmt_pct(indicators[y].efficiency_ratio) for y in years_ok]))
    print(row("Custo do Crédito", [fmt_pct(indicators[y].cost_of_credit)   for y in years_ok]))
    print(row("Fee Share",        [fmt_pct(indicators[y].fee_income_share) for y in years_ok]))

    # Balanço
    b = {y: results[y].balance_sheet for y in years_ok}
    print("\n### Balanço (R$ bi)")
    print(header); print(sep)
    print(row("Total Ativos",     [fmt_brl(b[y].assets.total_assets)                for y in years_ok]))
    print(row("Carteira Crédito", [fmt_brl(b[y].assets.loan_portfolio_gross)        for y in years_ok]))
    print(row("Provisão (reserva)",[fmt_brl(b[y].assets.loan_loss_reserve)          for y in years_ok]))
    print(row("Depósitos",        [fmt_brl(b[y].liabilities.deposits)               for y in years_ok]))
    print(row("PL Controladora",  [fmt_brl(b[y].liabilities.shareholders_equity)    for y in years_ok]))
    print(row("Alavancagem",      [fmt_x(indicators[y].leverage)                    for y in years_ok]))
    print(row("Crédito/Ativos",   [fmt_pct(indicators[y].loan_to_asset)             for y in years_ok]))

    # Crescimento YoY
    growth_years = [y for y in years_ok if y in prev]
    if growth_years:
        print("\n### Crescimento YoY")
        hdr2 = "| Linha" + "".join(f" | {y}" for y in growth_years) + " |"
        sep2 = "|---" + "|---" * len(growth_years) + "|"
        print(hdr2); print(sep2)
        print(row("Receitas",     [fmt_pct(indicators[y].revenue_growth)    for y in growth_years]))
        print(row("Lucro Líquido",[fmt_pct(indicators[y].net_income_growth) for y in growth_years]))
        print(row("Carteira",     [fmt_pct(indicators[y].loan_growth)       for y in growth_years]))
        print(row("PL",           [fmt_pct(indicators[y].equity_growth)     for y in growth_years]))


def print_comparative_table(all_results: dict[str, dict[int, BankStatements]]):
    """Tabela comparativa — último ano disponível para cada banco."""
    print(f"\n\n{'=' * 100}")
    print("  COMPARATIVO — BANCOS BRASILEIROS  |  Ultimo ano disponivel  |  R$ bilhoes")
    print(f"{'=' * 100}")

    # Monta linha por banco
    rows = []
    for ticker in TICKERS:
        res = all_results.get(ticker, {})
        if not res:
            continue
        last_year = max(res.keys())
        stmts = res[last_year]
        i = stmts.income_statement
        b = stmts.balance_sheet

        prev_years = sorted(res.keys())
        prev_stmts = res[prev_years[-2]] if len(prev_years) >= 2 else None
        ind = BankIndicators.from_statements(stmts, prev_stmts)

        rows.append({
            "Ticker":     ticker,
            "Ano":        last_year,
            "Receitas":   fmt_brl(i.total_financial_revenues),
            "NII":        fmt_brl(i.nii_gross),
            "LL":         fmt_brl(i.net_income),
            "Ativos":     fmt_brl(b.assets.total_assets),
            "Crédito":    fmt_brl(b.assets.loan_portfolio_gross),
            "PL":         fmt_brl(b.liabilities.shareholders_equity),
            "ROE":        fmt_pct(ind.roe),
            "ROTE":       fmt_pct(ind.rote),
            "Efic.":      fmt_pct(ind.efficiency_ratio),
            "Alav.":      fmt_x(ind.leverage),
            "FeeShare":   fmt_pct(ind.fee_income_share),
        })

    if not rows:
        print("Sem dados.")
        return

    cols = ["Ticker", "Ano", "Receitas", "NII", "LL", "Ativos", "Crédito",
            "PL", "ROE", "ROTE", "Efic.", "Alav.", "FeeShare"]

    header = "| " + " | ".join(cols) + " |"
    sep    = "|" + "|".join(["---"] * len(cols)) + "|"
    print(header)
    print(sep)
    for r in rows:
        print("| " + " | ".join(str(r.get(c, "—")) for c in cols) + " |")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dl = CVMDownloader(output_dir=RAW_DIR)
    parser = BankParser()

    # Download (pula se já existir)
    download_all(dl)

    all_results: dict[str, dict[int, BankStatements]] = {}

    print(f"\n\nExtracao DFP — Bancos — {YEARS[0]} a {YEARS[-1]}")
    print("=" * 70)

    for ticker in TICKERS:
        print(f"\n[{ticker}] ", end="", flush=True)
        results = extract_bank(parser, ticker, YEARS)
        if results:
            years_found = sorted(results.keys())
            print(f"{len(results)} ano(s): {years_found[0]}–{years_found[-1]}")
            all_results[ticker] = results
        else:
            print("sem dados")

    # Histórico por banco
    for ticker in TICKERS:
        if ticker in all_results:
            print_bank_history(ticker, all_results[ticker])

    # Comparativo final
    print_comparative_table(all_results)

    # Nota sobre bancos fora de cobertura
    print(f"\n\n{'=' * 70}")
    print("  FORA DE COBERTURA AUTOMATICA")
    print(f"{'=' * 70}")
    for ticker, msg in UNSUPPORTED.items():
        print(f"  {ticker}: {msg}")

    return all_results


if __name__ == "__main__":
    main()
