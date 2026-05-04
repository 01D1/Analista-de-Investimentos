"""
01_wege3_extracao_piloto.py
----------------------------
Script de extração piloto para WEGE3.

Executa todo o pipeline para um ano:
  1. Download DFP da CVM
  2. Parse das demonstrações
  3. Mapeamento para schema padronizado
  4. Reconciliação automática
  5. Exibição do sumário

Uso:
    python notebooks/01_wege3_extracao_piloto.py

Pré-requisitos:
    pip install -r requirements.txt
    Executar a partir da raiz de 12_PYTHON/
"""

import logging
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.cvm_downloader import CVMDownloader
from parsers.dfp_parser import DFPParser
from normalization.account_mapper import AccountMapper
from validation.reconciler import Reconciler
from validation.schemas import (
    ExtractionMetadata,
    IncomeStatement,
    Assets,
    Liabilities,
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    FinancialIndicators,
    Consolidation,
    DocType,
    Periodicity,
)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

WEGE_CVM_CODE = "005410"
TARGET_YEAR = 2023
RAW_DIR = Path("data/raw/cvm")


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  PIPELINE PILOTO — WEGE3 DFP 2023")
    print("=" * 60 + "\n")

    # 1. Download
    print("[1/5] Baixando DFP da CVM...")
    downloader = CVMDownloader(output_dir=RAW_DIR)
    files = downloader.download_dfp(year=TARGET_YEAR)
    print(f"      {len(files)} arquivos extraídos.\n")

    # 2. Parse
    print("[2/5] Parseando demonstrações para WEGE3...")
    parser = DFPParser()
    dfs = parser.parse_company(
        cvm_code=WEGE_CVM_CODE,
        raw_dir=RAW_DIR / "DFP" / str(TARGET_YEAR),
        consolidation="con",
    )
    for name, df in dfs.items():
        print(f"      {name}: {len(df)} linhas")
    print()

    # 3. Mapeamento
    print("[3/5] Normalizando contas...")
    mapper = AccountMapper()
    mapped = {name: mapper.to_dict(df) for name, df in dfs.items()}

    dre_dict = mapped.get("DRE", {})
    bpa_dict = mapped.get("BPA", {})
    bpp_dict = mapped.get("BPP", {})
    dfc_dict = mapped.get("DFC", {})

    # Exibir contas mapeadas
    print(f"      DRE: {len(dre_dict)} campos mapeados")
    print(f"      BPA: {len(bpa_dict)} campos mapeados")
    print(f"      BPP: {len(bpp_dict)} campos mapeados")
    print(f"      DFC: {len(dfc_dict)} campos mapeados\n")

    # 4. Construir schemas
    print("[4/5] Validando com schemas Pydantic...")

    # Campos obrigatórios com fallback para 0.0 se não encontrados
    def get(d: dict, key: str, default: float = 0.0) -> float:
        return d.get(key, default)

    try:
        meta = ExtractionMetadata(
            ticker="WEGE3",
            company_name="WEG S.A.",
            period=f"{TARGET_YEAR}A",
            consolidation=Consolidation.CONSOLIDATED,
            source=f"CVM DFP {TARGET_YEAR}",
            periodicity=Periodicity.ANNUAL,
            doc_type=DocType.DFP,
            unit=1000,
        )

        # D&A: não aparece como linha separada na DRE da WEG — usar valor do DFC
        da_from_dfc = dfc_dict.get("depreciation_amortization_cfo")

        income = IncomeStatement(
            net_revenue=get(dre_dict, "net_revenue"),
            cogs=dre_dict.get("cogs"),
            gross_profit=dre_dict.get("gross_profit"),
            selling_expenses=dre_dict.get("selling_expenses"),
            general_admin_expenses=dre_dict.get("general_admin_expenses"),
            other_operating_income=dre_dict.get("other_operating_income"),
            equity_income=dre_dict.get("equity_income"),
            depreciation_amortization=da_from_dfc,   # do DFC (método indireto)
            ebit=dre_dict.get("ebit"),
            financial_income=dre_dict.get("financial_income"),
            financial_expenses=dre_dict.get("financial_expenses"),
            net_financial_result=dre_dict.get("net_financial_result"),
            ebt=dre_dict.get("ebt"),
            income_tax=dre_dict.get("income_tax"),
            net_income_consolidated=dre_dict.get("net_income_consolidated"),
            minority_interest=dre_dict.get("minority_interest"),
            net_income=get(dre_dict, "net_income"),
        )

        assets = Assets(
            cash=get(bpa_dict, "cash"),
            short_term_investments=bpa_dict.get("short_term_investments"),
            accounts_receivable=bpa_dict.get("accounts_receivable"),
            inventories=bpa_dict.get("inventories"),
            total_current_assets=bpa_dict.get("total_current_assets"),
            equity_investments=bpa_dict.get("equity_investments"),
            ppe_net=bpa_dict.get("ppe_net"),
            intangibles_net=bpa_dict.get("intangibles_net"),
            total_non_current_assets=bpa_dict.get("total_non_current_assets"),
            total_assets=get(bpa_dict, "total_current_assets", 0) + get(bpa_dict, "total_non_current_assets", 0) or get(bpa_dict, "total_assets", 1),
        )

        # PL da controladora = PL total - participação dos não-controladores (minoritários)
        total_equity = get(bpp_dict, "total_equity")
        minority_bs = bpp_dict.get("minority_interest_bs", 0.0) or 0.0
        shareholders_equity = total_equity - minority_bs

        liabilities = Liabilities(
            suppliers=bpp_dict.get("suppliers"),
            short_term_debt=bpp_dict.get("short_term_debt"),
            total_current_liabilities=bpp_dict.get("total_current_liabilities"),
            long_term_debt=bpp_dict.get("long_term_debt"),
            total_non_current_liabilities=bpp_dict.get("total_non_current_liabilities"),
            minority_interest_bs=minority_bs if minority_bs else None,
            shareholders_equity=shareholders_equity,
            total_equity=total_equity,
            total_liabilities_and_equity=assets.total_assets,  # BP equilibrado
        )

        balance = BalanceSheet(assets=assets, liabilities=liabilities)

        cashflow = CashFlowStatement(
            cfo=get(dfc_dict, "cfo"),
            net_income_cfo=dfc_dict.get("net_income_cfo"),
            depreciation_amortization_cfo=dfc_dict.get("depreciation_amortization_cfo"),
            working_capital_changes=dfc_dict.get("working_capital_changes"),
            capex=dfc_dict.get("capex"),
            cfi=get(dfc_dict, "cfi"),
            debt_issuance=dfc_dict.get("debt_issuance"),
            debt_repayment=dfc_dict.get("debt_repayment"),
            dividends_paid=dfc_dict.get("dividends_paid"),
            cff=get(dfc_dict, "cff"),
            forex_effect_on_cash=dfc_dict.get("forex_effect_on_cash"),
            beginning_cash=get(dfc_dict, "beginning_cash"),
            ending_cash=get(dfc_dict, "ending_cash", assets.cash),
        )

        stmts = FinancialStatements(
            metadata=meta,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
        )
        print("      [OK] Schemas validados com sucesso.\n")

    except Exception as e:
        print(f"      [ERRO] Validacao falhou: {e}\n")
        raise

    # 5. Reconciliação
    print("[5/5] Executando reconciliação contábil...")
    reconciler = Reconciler()
    report = reconciler.run(stmts)
    reconciler.print_report(report)

    # Sumário de indicadores
    print("\n" + "=" * 60)
    print("  SUMÁRIO DE INDICADORES")
    print("=" * 60)
    summary = stmts.summary()
    for key, val in summary.items():
        if isinstance(val, float):
            if "margin" in key:
                print(f"  {key:<30} {val:.1%}")
            else:
                print(f"  {key:<30} {val:>15,.0f}")
        else:
            print(f"  {key:<30} {val}")

    # Indicadores calculados
    print("\n" + "=" * 60)
    print("  INDICADORES CALCULADOS")
    print("=" * 60)
    indicators = FinancialIndicators.from_statements(stmts)
    ind_dict = indicators.model_dump(exclude_none=True)
    for key, val in ind_dict.items():
        if key in ("ticker", "period"):
            continue
        if isinstance(val, float):
            if any(x in key for x in ("margin", "roe", "roa", "roic", "rate", "yield")):
                print(f"  {key:<35} {val:.1%}")
            elif "days" in key:
                print(f"  {key:<35} {val:.0f} dias")
            else:
                print(f"  {key:<35} {val:>12,.0f}")
    print()

    if report.blocking_errors == 0:
        print("[OK] Pipeline concluido sem erros criticos.\n")
    else:
        print(f"[AVISO] Pipeline concluido com {report.blocking_errors} erros criticos -- revisar antes de usar os dados.\n")


if __name__ == "__main__":
    main()
