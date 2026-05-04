"""
bank_parser.py
--------------
Parser especializado para DFPs de bancos brasileiros.

Reutiliza o DFPParser para leitura/filtragem dos CSVs CVM, mas aplica o
BankAccountMapper e constrói BankStatements ao invés dos schemas industriais.

Bancos cobertos:
  ITUB4  — Itaú Unibanco Holding    CVM 019348
  BBAS3  — Banco do Brasil           CVM 001023
  BBDC4  — Banco Bradesco            CVM 000906
  SANB11 — Santander Brasil          CVM 020532
  BPAC11 — BTG Pactual               CVM 022616
  INTR4  — Inter & Co                CVM 080217  (holding Cayman, DRE padrão industrial)
  BRSR6  — Banrisul (BCO EST RS)     CVM 001210
  ABCB4  — Banco ABC Brasil          CVM 020958
  BMGB4  — Banco BMG                 CVM 024600
  BPAN4  — Banco Pan                 CVM 021199
  PINE4  — Banco Pine                CVM 020567
  ITSA4  — Itaúsa (holding Itaú)     CVM 007617
  ROXO34 — Nubank (BDR)              N/A — não publica DFP no CVM como cia aberta brasileira
"""

from __future__ import annotations

import logging
from pathlib import Path

from normalization.bank_account_mapper import BankAccountMapper
from parsers.dfp_parser import DFPParser
from validation.bank_schemas import (
    BankAssets,
    BankBalanceSheet,
    BankCashFlow,
    BankIncomeStatement,
    BankLiabilities,
    BankMetadata,
    BankStatements,
    BankType,
    Consolidation,
    Periodicity,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cadastro de bancos
# ---------------------------------------------------------------------------

BANK_REGISTRY: dict[str, dict] = {
    "ITUB4": {
        "cvm_code": "019348",
        "name": "Itaú Unibanco Holding S.A.",
        "bank_type": BankType.LARGE_BANK,
        "is_standard_bank": True,  # usa estrutura DRE bancária (3.01 = Intermediação)
    },
    "BBAS3": {
        "cvm_code": "001023",
        "name": "Banco do Brasil S.A.",
        "bank_type": BankType.LARGE_BANK,
        "is_standard_bank": True,
    },
    "BBDC4": {
        "cvm_code": "000906",
        "name": "Banco Bradesco S.A.",
        "bank_type": BankType.LARGE_BANK,
        "is_standard_bank": True,
    },
    "SANB11": {
        "cvm_code": "020532",
        "name": "Banco Santander (Brasil) S.A.",
        "bank_type": BankType.LARGE_BANK,
        "is_standard_bank": True,
    },
    "BPAC11": {
        "cvm_code": "022616",
        "name": "Banco BTG Pactual S.A.",
        "bank_type": BankType.INVESTMENT_BANK,
        "is_standard_bank": True,
    },
    "INTR4": {
        "cvm_code": "080217",
        "name": "Inter & Co, Inc.",
        "bank_type": BankType.BDR,
        "is_standard_bank": False,  # holding Cayman — usa DRE industrial (3.01 = Revenue)
    },
    "BRSR6": {
        "cvm_code": "001210",
        "name": "Banco do Estado do Rio Grande do Sul S.A. (Banrisul)",
        "bank_type": BankType.MEDIUM_BANK,
        "is_standard_bank": True,
    },
    "ABCB4": {
        "cvm_code": "020958",
        "name": "Banco ABC Brasil S.A.",
        "bank_type": BankType.MEDIUM_BANK,
        "is_standard_bank": True,
    },
    "BMGB4": {
        "cvm_code": "024600",
        "name": "Banco BMG S/A",
        "bank_type": BankType.MEDIUM_BANK,
        "is_standard_bank": True,
    },
    "BPAN4": {
        "cvm_code": "021199",
        "name": "Banco Pan S.A.",
        "bank_type": BankType.MEDIUM_BANK,
        "is_standard_bank": True,
    },
    "PINE4": {
        "cvm_code": "020567",
        "name": "Banco Pine S.A.",
        "bank_type": BankType.MEDIUM_BANK,
        "is_standard_bank": True,
    },
    "ITSA4": {
        "cvm_code": "007617",
        "name": "Itaúsa S.A.",
        "bank_type": BankType.HOLDING,
        "is_standard_bank": False,  # holding — DRE industrial mas revenue = dividendos/equiv.
    },
}

# Nubank (ROXO34) é BDR de empresa listada no NYSE — não publica DFP CVM como cia aberta brasileira
UNSUPPORTED = {
    "ROXO34": "Nubank — listada no NYSE como NU HOLDINGS. Não publica DFP no CVM. "
    "Usar relatórios 20-F (SEC) ou earnings releases convertidos para BRL.",
}


# ---------------------------------------------------------------------------
# BankParser
# ---------------------------------------------------------------------------


class BankParser:
    """
    Extrai e constrói BankStatements a partir dos arquivos CVM DFP.
    """

    def __init__(self):
        self._dfp_parser = DFPParser()
        self._mapper = BankAccountMapper()

    def parse(
        self,
        ticker: str,
        year: int,
        raw_dir: Path,
        consolidation: str = "con",
    ) -> BankStatements | None:
        """
        Retorna BankStatements para um banco/ano específico.

        Args:
            ticker: ex "ITUB4"
            year: ex 2023
            raw_dir: pasta raiz com os CSVs CVM (ex: data/raw/cvm/DFP/2023)
            consolidation: "con" ou "ind"
        """
        if ticker in UNSUPPORTED:
            logger.warning(f"{ticker}: {UNSUPPORTED[ticker]}")
            return None

        if ticker not in BANK_REGISTRY:
            logger.error(f"Ticker {ticker} não está no BANK_REGISTRY.")
            return None

        info = BANK_REGISTRY[ticker]
        cvm_code = info["cvm_code"]

        # Lê DataFrames brutos via DFPParser
        dfs = self._dfp_parser.parse_company(
            cvm_code=cvm_code,
            raw_dir=raw_dir,
            consolidation=consolidation,
        )
        if not dfs:
            logger.warning(f"{ticker} {year}: sem dados em {raw_dir}")
            return None

        # Mapeia para dicionários padronizados
        # DFPParser retorna chave "DFC" (mapeada para DFC_MI)
        mapped = {name: self._mapper.to_dict(df) for name, df in dfs.items()}
        dre = mapped.get("DRE", {})
        bpa = mapped.get("BPA", {})
        bpp = mapped.get("BPP", {})
        dfc = mapped.get("DFC", {})

        if not dre:
            logger.warning(f"{ticker} {year}: DRE vazia após mapeamento")
            return None

        # Verifica se é banco padrão ou holding/BDR
        is_bank = info["is_standard_bank"]
        if not is_bank:
            # Para holdings (ITSA4) e BDRs (INTR4) com estrutura industrial,
            # a net_revenue vira total_financial_revenues por convenção
            if "net_revenue" in dre and "total_financial_revenues" not in dre:
                dre["total_financial_revenues"] = dre["net_revenue"]
            if "net_income" not in dre:
                logger.warning(f"{ticker} {year}: sem lucro líquido mapeado")
                return None

        try:
            meta = BankMetadata(
                ticker=ticker,
                company_name=info["name"],
                cvm_code=cvm_code,
                period=f"{year}A",
                bank_type=info["bank_type"],
                consolidation=Consolidation.CONSOLIDATED,
                source=f"CVM DFP {year}",
                periodicity=Periodicity.ANNUAL,
                unit=1000,
            )

            # Fallback para net_income: alguns bancos têm 3.11.01=0 mas 3.11=lucro total
            # (ABCB4, BPAN4 sem minority interest — tudo em net_income_consolidated)
            raw_ni = dre.get("net_income", 0.0)
            raw_ni_consol = dre.get("net_income_consolidated", 0.0)
            if raw_ni == 0.0 and raw_ni_consol != 0.0:
                dre["net_income"] = raw_ni_consol

            income = BankIncomeStatement(
                total_financial_revenues=dre.get("total_financial_revenues", 0.0),
                interest_income=dre.get("interest_income"),
                fee_income=dre.get("fee_income"),
                insurance_result=dre.get("insurance_result"),
                fx_result=dre.get("fx_result"),
                trading_result=dre.get("trading_result"),
                other_revenues=dre.get("other_revenues"),
                total_financial_expenses=dre.get("total_financial_expenses", 0.0),
                interest_expense=dre.get("interest_expense"),
                loan_loss_provision=dre.get("loan_loss_provision"),
                nii_gross=dre.get("nii_gross", 0.0),
                other_operating_result=dre.get("other_operating_result"),
                admin_expenses=dre.get("admin_expenses"),
                tax_expenses=dre.get("tax_expenses"),
                personnel_expenses=dre.get("personnel_expenses"),
                equity_income=dre.get("equity_income"),
                other_operating_expenses=dre.get("other_operating_expenses"),
                ebt=dre.get("ebt"),
                income_tax=dre.get("income_tax"),
                net_income_consolidated=dre.get("net_income_consolidated"),
                minority_interest=dre.get("minority_interest"),
                net_income=dre.get("net_income", 0.0),
            )

            # Equity — dois layouts:
            # Itaú/BTG: 2.08 = total PL, 2.08.09 = minoritários → PL controladora = total - minorities
            # BB/Banrisul: 2.07 = total PL, 2.07.01 = PL controladora direta, 2.07.02 = minoritários
            total_equity = bpp.get("total_equity", 0.0)
            minority_bs = bpp.get("minority_interest_bs") or 0.0
            shareholders_equity_direct = bpp.get("shareholders_equity_direct")
            if shareholders_equity_direct is not None:
                shareholders_equity = shareholders_equity_direct
            else:
                shareholders_equity = total_equity - minority_bs

            assets = BankAssets(
                cash=bpa.get("cash", 0.0),
                total_financial_assets=bpa.get("total_financial_assets"),
                fv_through_pl=bpa.get("fv_through_pl"),
                fv_through_oci=bpa.get("fv_through_oci"),
                amortized_cost_assets=bpa.get("amortized_cost_assets"),
                loan_portfolio_gross=bpa.get("loan_portfolio_gross"),
                loan_loss_reserve=bpa.get("loan_loss_reserve"),
                securities=bpa.get("securities"),
                compulsory_deposits=bpa.get("compulsory_deposits"),
                deferred_taxes=bpa.get("deferred_taxes"),
                other_assets=bpa.get("other_assets"),
                equity_investments=bpa.get("equity_investments"),
                ppe_net=bpa.get("ppe_net"),
                intangibles_net=bpa.get("intangibles_net"),
                total_assets=bpa.get("total_assets", 0.0),
            )

            liabilities = BankLiabilities(
                fv_liabilities=bpp.get("fv_liabilities"),
                derivatives_liability=bpp.get("derivatives_liability"),
                funding_at_cost=bpp.get("funding_at_cost"),
                deposits=bpp.get("deposits"),
                repo_funding=bpp.get("repo_funding"),
                interbank_funding=bpp.get("interbank_funding"),
                institutional_funding=bpp.get("institutional_funding"),
                provisions=bpp.get("provisions"),
                other_liabilities=bpp.get("other_liabilities"),
                insurance_liabilities=bpp.get("insurance_liabilities"),
                total_equity=total_equity,
                minority_interest_bs=minority_bs or None,
                shareholders_equity=shareholders_equity,
                total_liabilities_and_equity=assets.total_assets,
            )

            balance = BankBalanceSheet(assets=assets, liabilities=liabilities)

            cashflow = None
            if dfc:
                cashflow = BankCashFlow(
                    cfo=dfc.get("cfo", 0.0),
                    cfi=dfc.get("cfi", 0.0),
                    cff=dfc.get("cff", 0.0),
                    forex_effect_on_cash=dfc.get("forex_effect_on_cash"),
                    dividends_paid=dfc.get("dividends_paid"),
                    capex=dfc.get("capex"),
                    beginning_cash=dfc.get("beginning_cash", 0.0),
                    ending_cash=dfc.get("ending_cash", assets.cash),
                )

            return BankStatements(
                metadata=meta,
                income_statement=income,
                balance_sheet=balance,
                cash_flow=cashflow,
            )

        except Exception as e:
            logger.error(f"{ticker} {year}: erro ao construir BankStatements — {e}")
            return None
