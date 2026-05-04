"""
dfp_parser.py
-------------
Parseia os arquivos CSV extraídos da CVM (DFP/ITR) e os converte
nos schemas padronizados definidos em validation/schemas.py.

Os CSVs da CVM têm o seguinte formato:
  CNPJ_CIA, DT_REFER, VERSAO, DENOM_CIA, CD_CVM, ESCALA_MOEDA,
  MOEDA, ORDEM_EXERC, DT_FIM_EXERC, CD_CONTA, DS_CONTA, VL_CONTA, ST_CONTA_FIXA

Colunas relevantes:
  - CD_CVM:       código CVM da empresa
  - DENOM_CIA:    nome da empresa
  - DT_FIM_EXERC: data de encerramento do período
  - ORDEM_EXERC:  ÚLTIMO (período atual) | PENÚLTIMO (ano anterior)
  - CD_CONTA:     código da conta (ex: 3.01 = Receita Líquida)
  - DS_CONTA:     descrição da conta
  - VL_CONTA:     valor (já na escala informada em ESCALA_MOEDA)
  - ESCALA_MOEDA: UNIDADE / MIL / BILHÃO

Uso:
    from ingestion.cvm_downloader import CVMDownloader
    from parsers.dfp_parser import DFPParser

    dl = CVMDownloader()
    files = dl.download_dfp(2023)

    parser = DFPParser()
    records = parser.parse_company(
        cvm_code="005410",   # código CVM da WEG
        year=2023,
        raw_dir="data/raw/cvm/DFP/2023",
        consolidation="con",
    )
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento de contas CVM → nomes padronizados
# ---------------------------------------------------------------------------

# Prefixos de código CVM para mapeamento
# A CVM usa prefixos de conta padronizados (Plano de Contas CVM)
ACCOUNT_MAP = {
    # DRE (3.xx) — estrutura padrão CVM (maioria das empresas brasileiras)
    # 3.01 = Receita Líquida (já líquida de impostos — a CVM apresenta assim)
    # 3.02 = CPV / Custo dos Produtos Vendidos
    # 3.03 = Resultado Bruto (Lucro Bruto)
    # 3.04 = Despesas Operacionais (total)
    # 3.05 = EBIT (Resultado Antes do Resultado Financeiro)
    # 3.06 = Resultado Financeiro
    # 3.07 = EBT (Resultado Antes dos Tributos)
    # 3.08 = IR / CSLL
    # 3.09 = Lucro Líquido Consolidado (Operações Continuadas)
    # 3.11 = Lucro Líquido Consolidado Total
    # 3.11.01 = Atribuído à Controladora (o que usamos como net_income)
    "3.01": "net_revenue",
    "3.02": "cogs",
    "3.03": "gross_profit",
    "3.04": "operating_expenses",
    "3.04.01": "selling_expenses",
    "3.04.02": "general_admin_expenses",
    "3.04.04": "other_operating_income",
    "3.04.06": "equity_income",
    "3.05": "ebit",
    "3.06": "net_financial_result",
    "3.06.01": "financial_income",
    "3.06.02": "financial_expenses",
    "3.07": "ebt",
    "3.08": "income_tax",
    "3.09": "net_income_consolidated",
    "3.11": "net_income_consolidated",
    "3.11.01": "net_income",
    "3.11.02": "minority_interest",
    "3.17": "net_income",
    # BPA — Ativo (1.xx)
    "1.01": "total_current_assets",
    "1.01.01": "cash",
    "1.01.02": "short_term_investments",
    "1.01.03": "accounts_receivable",
    "1.01.04": "inventories",
    "1.02": "total_non_current_assets",
    "1.02.01": "long_term_investments",
    "1.02.02": "equity_investments",
    "1.02.03": "ppe_net",
    "1.02.04": "intangibles_net",
    # BPP — Passivo (2.xx)
    # Nota: estrutura do PL varia por empresa. Para calcular PL da controladora:
    # shareholders_equity = total_equity - minority_interest_bs
    "2.01": "total_current_liabilities",
    "2.01.04": "short_term_debt",  # Empréstimos e Financiamentos CP
    "2.01.02": "suppliers",
    "2.02": "total_non_current_liabilities",
    "2.02.01": "long_term_debt",  # Empréstimos e Financiamentos LP
    "2.03": "total_equity",
    "2.03.09": "minority_interest_bs",  # Participação dos não-controladores (posição padrão CVM)
    # DFC método indireto (6.xx)
    # 6.01 = CFO total | 6.01.01 = caixa gerado (ajustes não-caixa) | 6.01.02 = variações de capital de giro
    # 6.01.01.01 = lucro antes dos impostos (ponto de partida) | 6.01.01.02 = D&A
    "6.01": "cfo",
    "6.01.01.01": "net_income_cfo",  # Lucro antes dos impostos (ponto de partida)
    "6.01.01.02": "depreciation_amortization_cfo",
    "6.01.02": "working_capital_changes",
    "6.02": "cfi",
    "6.02.02": "capex",  # Imobilizado (PP&E capex)
    "6.03": "cff",
    "6.03.01": "debt_issuance",
    "6.03.02": "debt_repayment",
    "6.03.04": "dividends_paid",  # Dividendos/JCP pagos
    "6.04": "forex_effect_on_cash",  # Variação cambial s/ caixa
    "6.05": "net_cash_change",  # Aumento (Redução) de Caixa
    "6.05.01": "beginning_cash",
    "6.05.02": "ending_cash",
}

SCALE_MAP = {
    "UNIDADE": 1,
    "MIL": 1_000,
    "BILHÃO": 1_000_000_000,
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class DFPParser:
    """
    Parseia CSVs da CVM e retorna DataFrames normalizados por empresa.

    Args:
        encoding: Encoding dos CSVs da CVM (padrão: iso-8859-1)
        separator: Separador de campos (padrão: ;)
    """

    def __init__(self, encoding: str = "iso-8859-1", separator: str = ";"):
        self.encoding = encoding
        self.separator = separator

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def parse_company(
        self,
        cvm_code: str,
        raw_dir: str | Path,
        consolidation: str = "con",
        period_order: str = "ÚLTIMO",
    ) -> dict[str, pd.DataFrame]:
        """
        Parseia todos os demonstrativos de uma empresa a partir dos CSVs locais.

        Args:
            cvm_code: Código CVM da empresa (ex: "005410" para WEG)
            raw_dir: Diretório com os CSVs extraídos pela CVM
            consolidation: "con" (consolidado) ou "ind" (controladora)
            period_order: "ÚLTIMO" para período atual, "PENÚLTIMO" para comparativo

        Returns:
            Dicionário com DataFrames por tipo:
            {
                "DRE": pd.DataFrame,
                "BPA": pd.DataFrame,  # Ativo
                "BPP": pd.DataFrame,  # Passivo + PL
                "DFC": pd.DataFrame,
            }
        """
        raw_dir = Path(raw_dir)
        cvm_code = str(cvm_code).zfill(6)
        results: dict[str, pd.DataFrame] = {}

        # Mapear arquivos disponíveis
        file_map = self._find_files(raw_dir, consolidation)

        for stmt_type, path in file_map.items():
            try:
                df = self._load_csv(path)
                df = self._filter_company(df, cvm_code, period_order)
                if df.empty:
                    logger.warning(
                        "[%s] Nenhum dado para cód. CVM %s em %s", stmt_type, cvm_code, path.name
                    )
                    continue
                df = self._normalize(df)
                results[stmt_type] = df
                logger.info("[%s] %d linhas parseadas para %s", stmt_type, len(df), cvm_code)
            except Exception as e:
                logger.error("[%s] Erro ao parsear %s: %s", stmt_type, path.name, e)

        return results

    def to_dict(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Converte um DataFrame de demonstração em dicionário {nome_normalizado: valor}.
        Útil para alimentar os schemas Pydantic.

        Args:
            df: DataFrame retornado por parse_company

        Returns:
            Dicionário {campo_schema: valor_float}
        """
        result: dict[str, float] = {}
        for _, row in df.iterrows():
            code = str(row.get("account_code", ""))
            value = row.get("value", 0.0)

            # Mapeamento direto pelo código
            if code in ACCOUNT_MAP:
                result[ACCOUNT_MAP[code]] = float(value)

            # Mapeamento por prefixo (para contas com subcódigos)
            for prefix, field_name in ACCOUNT_MAP.items():
                if code.startswith(prefix + ".") and field_name not in result:
                    result.setdefault(field_name, float(value))

        return result

    def list_companies(self, csv_path: str | Path) -> pd.DataFrame:
        """
        Lista todas as empresas disponíveis em um CSV da CVM.

        Returns:
            DataFrame com colunas: CD_CVM, DENOM_CIA (únicos)
        """
        df = self._load_csv(Path(csv_path))
        return (
            df[["CD_CVM", "DENOM_CIA"]]
            .drop_duplicates()
            .sort_values("DENOM_CIA")
            .reset_index(drop=True)
        )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _find_files(self, raw_dir: Path, consolidation: str) -> dict[str, Path]:
        """Mapeia arquivos CSV disponíveis no diretório."""
        patterns = {
            "DRE": f"*DRE_{consolidation}*.csv",
            "BPA": f"*BPA_{consolidation}*.csv",
            "BPP": f"*BPP_{consolidation}*.csv",
            "DFC": f"*DFC_MI_{consolidation}*.csv",
        }
        found = {}
        for name, pattern in patterns.items():
            matches = list(raw_dir.glob(pattern))
            if matches:
                found[name] = matches[0]
                if len(matches) > 1:
                    logger.warning(
                        "Múltiplos arquivos para %s: %s — usando o primeiro.", name, matches
                    )
            else:
                logger.warning("Arquivo não encontrado: %s/%s", raw_dir, pattern)
        return found

    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Carrega CSV da CVM com encoding e separador corretos."""
        df = pd.read_csv(
            path,
            encoding=self.encoding,
            sep=self.separator,
            dtype=str,  # Carrega tudo como string para controle de tipos
            low_memory=False,
        )
        # Normalizar nomes de colunas
        df.columns = [c.strip().upper() for c in df.columns]
        return df

    def _filter_company(
        self,
        df: pd.DataFrame,
        cvm_code: str,
        period_order: str,
    ) -> pd.DataFrame:
        """Filtra pelo código CVM e período."""
        mask = (df["CD_CVM"].str.strip().str.zfill(6) == cvm_code) & (
            df["ORDEM_EXERC"].str.strip().str.upper() == period_order.upper()
        )
        return df[mask].copy()

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza e converte tipos."""
        # Escala monetária
        scale = (
            df["ESCALA_MOEDA"].iloc[0].strip().upper() if "ESCALA_MOEDA" in df.columns else "MIL"
        )
        multiplier = SCALE_MAP.get(scale, 1_000)

        # Converter valor
        df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"].str.replace(",", "."), errors="coerce")

        # Aplicar escala para padronizar em R$ mil
        if multiplier != 1_000:
            df["VL_CONTA"] = df["VL_CONTA"] * multiplier / 1_000

        # Renomear colunas para o schema interno
        rename = {
            "CD_CONTA": "account_code",
            "DS_CONTA": "account_name",
            "VL_CONTA": "value",
            "DT_FIM_EXERC": "reference_date",
            "DENOM_CIA": "company_name",
            "CD_CVM": "cvm_code",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        # Adicionar nome normalizado via ACCOUNT_MAP
        df["normalized_name"] = df["account_code"].map(ACCOUNT_MAP)

        # Selecionar colunas relevantes
        cols = [
            "account_code",
            "account_name",
            "normalized_name",
            "value",
            "reference_date",
            "company_name",
            "cvm_code",
        ]
        cols = [c for c in cols if c in df.columns]

        return df[cols].reset_index(drop=True)
