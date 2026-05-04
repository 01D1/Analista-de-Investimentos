"""
Módulo 04 — Normalizador de Dados
Recebe os dados brutos (CVM + mercado + macro) e os transforma
nas séries padronizadas que o template Excel espera.

Responsabilidades:
  1. Aplicar o mapa de contas (mapeamento_contas.py)
  2. Calcular contas derivadas (MFL, ativos remuneráveis, etc.)
  3. Converter unidades (R$ 1 → R$ MM)
  4. Tratar ausências e inconsistências
  5. Calcular indicadores básicos (NIM, ROE, NPL proxy)
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("pipeline.normalizador")


class Normalizador:
    """Transforma dados brutos em séries prontas para o template."""

    def __init__(self, divisor: float = 1_000_000):
        """
        Args:
            divisor: CVM reporta em R$ 1 → dividir por 1_000_000 para R$ MM
        """
        self.divisor = divisor

    # ── DRE ──────────────────────────────────────────────────────────────────

    def normalizar_dre(self, dados_brutos: dict[int, dict],
                        mapa: dict) -> pd.DataFrame:
        """
        Monta a DRE histórica normalizada.

        Returns:
            DataFrame: index=nome_conta, columns=anos
        """
        anos     = sorted(dados_brutos.keys())
        from modules.coletor_cvm import ColetorCVM   # import local para evitar circular
        coletor  = ColetorCVM.__new__(ColetorCVM)

        linhas   = {}

        for nome, config in mapa.items():
            if config.get("calculado"):
                continue
            serie = {}
            for ano in anos:
                dfs = dados_brutos.get(ano, {})
                df  = dfs.get("dre")
                if df is None:
                    serie[ano] = 0.0
                    continue

                from modules._helpers import extrair_valores_df
                valor = extrair_valores_df(df, config["codigos"],
                                            periodo=f"{ano}-12-31")
                serie[ano] = round(valor * config.get("sinal", 1) / self.divisor, 3)
            linhas[nome] = serie

        dre = pd.DataFrame(linhas).T

        # ── Contas calculadas ──────────────────────────────────────────────
        if "receita_juros_total" in dre.index and "despesa_juros_total" in dre.index:
            dre.loc["margem_financeira_bruta"] = (
                dre.loc["receita_juros_total"] + dre.loc["despesa_juros_total"])

        if ("margem_financeira_bruta" in dre.index and
                "provisao_credito" in dre.index):
            dre.loc["margem_financeira_liquida"] = (
                dre.loc["margem_financeira_bruta"] +
                dre.loc["provisao_credito"])

        if "margem_financeira_liquida" in dre.index:
            receitas = [c for c in ["resultado_seguros", "receita_servicos",
                                     "resultado_participacoes"]
                        if c in dre.index]
            despesas = [c for c in ["despesa_pessoal", "outras_despesas_operacionais"]
                        if c in dre.index]
            dre.loc["resultado_operacional"] = (
                dre.loc["margem_financeira_liquida"] +
                dre.loc[receitas].sum() -
                dre.loc[despesas].abs().sum()
            ) if receitas else dre.loc["margem_financeira_liquida"]

        if "resultado_operacional" in dre.index:
            res_nao_op = dre.loc["resultado_nao_operacional"] if (
                "resultado_nao_operacional" in dre.index) else 0
            dre.loc["resultado_antes_ir"] = (
                dre.loc["resultado_operacional"] + res_nao_op)

        if "resultado_antes_ir" in dre.index and "ir_csll" in dre.index:
            dre.loc["resultado_antes_minoritarios"] = (
                dre.loc["resultado_antes_ir"] + dre.loc["ir_csll"])

        if "resultado_antes_minoritarios" in dre.index:
            estat = (dre.loc["participacoes_estatutarias"]
                     if "participacoes_estatutarias" in dre.index else 0)
            minor = (dre.loc["participacoes_minoritarias"]
                     if "participacoes_minoritarias" in dre.index else 0)
            dre.loc["lucro_liquido"] = (
                dre.loc["resultado_antes_minoritarios"] + estat + minor)

        return dre

    def normalizar_balanco(self, dados_brutos: dict[int, dict],
                            mapa_ativo: dict, mapa_passivo: dict) -> pd.DataFrame:
        """
        Monta o balanço patrimonial histórico normalizado.
        """
        anos   = sorted(dados_brutos.keys())
        linhas = {}

        from modules._helpers import extrair_valores_df

        for mapa in [mapa_ativo, mapa_passivo]:
            for nome, config in mapa.items():
                if config.get("calculado"):
                    continue
                serie = {}
                for ano in anos:
                    dfs = dados_brutos.get(ano, {})
                    # Ativo → bpa, Passivo → bpp
                    tipo = "bpa" if mapa is mapa_ativo else "bpp"
                    df   = dfs.get(tipo)
                    if df is None:
                        serie[ano] = 0.0
                        continue
                    valor = extrair_valores_df(df, config["codigos"],
                                               periodo=f"{ano}-12-31")
                    serie[ano] = round(valor * config.get("sinal", 1) / self.divisor, 3)
                linhas[nome] = serie

        bp = pd.DataFrame(linhas).T

        # ── Contas calculadas do balanço ──────────────────────────────────
        # Ativos remuneráveis
        componentes_ar = ["carteira_credito_bruta", "tvm_derivativos",
                          "aplicacoes_interfinanceiras", "compulsorios_bacen",
                          "arrendamento_mercantil", "disponibilidades"]
        existentes = [c for c in componentes_ar if c in bp.index]
        if existentes:
            bp.loc["ativos_remuneraveis"] = bp.loc[existentes].sum()

        # Carteira crédito líquida
        if "carteira_credito_bruta" in bp.index and "provisao_pdd" in bp.index:
            bp.loc["carteira_credito_liquida"] = (
                bp.loc["carteira_credito_bruta"] + bp.loc["provisao_pdd"])

        # Depósitos total
        deps = ["depositos_vista", "depositos_poupanca", "depositos_prazo"]
        existentes_dep = [c for c in deps if c in bp.index]
        if existentes_dep:
            bp.loc["depositos_total"] = bp.loc[existentes_dep].sum()

        # Passivos onerosos
        pass_on = ["depositos_total", "captacoes_mercado_aberto",
                   "recursos_emissao_titulos", "obrigacoes_emprestimos",
                   "dividas_subordinadas"]
        existentes_po = [c for c in pass_on if c in bp.index]
        if existentes_po:
            bp.loc["passivos_onerosos_total"] = bp.loc[existentes_po].sum()

        return bp

    # ── Indicadores ───────────────────────────────────────────────────────────

    def calcular_indicadores(self, dre: pd.DataFrame,
                              bp: pd.DataFrame,
                              dados_mercado: dict,
                              macro: dict) -> pd.DataFrame:
        """
        Calcula o painel completo de indicadores financeiros.

        Returns:
            DataFrame: index=nome_indicador, columns=anos
        """
        anos = sorted(set(dre.columns.tolist() + bp.columns.tolist()))
        ind  = {}

        def get(df, linha, ano):
            try:
                return float(df.loc[linha, ano]) if linha in df.index else 0.0
            except Exception:
                return 0.0

        for ano in anos:
            lucro   = get(dre, "lucro_liquido", ano)
            mfb     = get(dre, "margem_financeira_bruta", ano)
            mfl     = get(dre, "margem_financeira_liquida", ano)
            provisao= get(dre, "provisao_credito", ano)
            servicos= get(dre, "receita_servicos", ano)
            pessoal = abs(get(dre, "despesa_pessoal", ano))
            outras  = abs(get(dre, "outras_despesas_operacionais", ano))
            res_op  = get(dre, "resultado_operacional", ano)
            ir      = get(dre, "ir_csll", ano)
            seguros = get(dre, "resultado_seguros", ano)

            ativo_total    = get(bp, "ativo_total", ano)
            at_remuner     = get(bp, "ativos_remuneraveis", ano)
            carteira_bruta = get(bp, "carteira_credito_bruta", ano)
            pass_on        = get(bp, "passivos_onerosos_total", ano)
            pl_ctrl        = get(bp, "pl_controladores", ano)
            pl_total       = get(bp, "patrimonio_liquido", ano)
            depositos      = get(bp, "depositos_total", ano)
            provisao_bp    = abs(get(bp, "provisao_pdd", ano))   # saldo balanço

            # Ano anterior para médias
            ano_ant = ano - 1
            pl_ant  = get(bp, "pl_controladores", ano_ant)
            at_ant  = get(bp, "ativo_total", ano_ant)
            ar_ant  = get(bp, "ativos_remuneraveis", ano_ant)

            pl_med  = (pl_ctrl + pl_ant) / 2 if pl_ant else pl_ctrl
            at_med  = (ativo_total + at_ant) / 2 if at_ant else ativo_total
            ar_med  = (at_remuner + ar_ant) / 2 if ar_ant else at_remuner

            receita_total = (mfb + servicos + seguros +
                             get(dre, "resultado_participacoes", ano))

            # Macro
            selic  = macro.get("historico", {}).get("selic_efet", {}).get(ano, 0)
            ipca   = macro.get("historico", {}).get("ipca", {}).get(ano, 0)

            ind[ano] = {
                # Rentabilidade
                "roe":              lucro / pl_med if pl_med else 0,
                "roa":              lucro / at_med if at_med else 0,
                "nim":              mfb / ar_med if ar_med else 0,
                "margem_liquida":   lucro / receita_total if receita_total else 0,
                "spread_global":    (mfb / ar_med - pass_on / at_remuner)
                                    if at_remuner and pass_on else 0,

                # Eficiência
                "indice_eficiencia": (pessoal + outras) / receita_total
                                      if receita_total else 0,
                "cost_to_income":    (pessoal + outras) / (mfb + servicos)
                                      if (mfb + servicos) else 0,
                "aliquota_ir":       abs(ir) / abs(res_op) if res_op else 0,

                # Capital
                "independencia_financeira": pl_total / ativo_total if ativo_total else 0,
                "alavancagem":              ativo_total / pl_total if pl_total else 0,
                "rel_capital_pass_on":      pl_ctrl / pass_on if pass_on else 0,

                # Liquidez
                "emp_depositos":    carteira_bruta / depositos if depositos else 0,
                "part_emprestimos": carteira_bruta / ativo_total if ativo_total else 0,

                # Crédito
                "pcld_carteira":    provisao / carteira_bruta if carteira_bruta else 0,
                "cobertura_pdd":    provisao_bp / (carteira_bruta * 0.04)
                                    if carteira_bruta else 0,   # proxy NPL 4%

                # Macro benchmark
                "selic":   selic,
                "ipca":    ipca,
                "nim_selic_spread": (mfb / ar_med - selic) if ar_med and selic else 0,

                # Valores absolutos úteis
                "mfb_mm":           mfb,
                "mfl_mm":           mfl,
                "lucro_mm":         lucro,
                "ativo_total_mm":   ativo_total,
                "carteira_mm":      carteira_bruta,
                "pl_mm":            pl_total,
                "servicos_mm":      servicos,
            }

        return pd.DataFrame(ind).T

    # ── Crescimentos ─────────────────────────────────────────────────────────

    def calcular_crescimentos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adiciona linhas de crescimento YoY para cada conta da DRE/balanço.
        """
        resultado = df.copy()
        for linha in df.index:
            try:
                crescimento = df.loc[linha].pct_change()
                crescimento.name = f"{linha}_yoy"
                resultado = pd.concat([resultado, crescimento.to_frame().T])
            except Exception:
                continue
        return resultado

    # ── Consolidação final ────────────────────────────────────────────────────

    def consolidar(self, dre: pd.DataFrame, bp: pd.DataFrame,
                   indicadores: pd.DataFrame, macro: dict,
                   dados_mercado: dict) -> dict:
        """
        Retorna um dicionário consolidado com todos os dados
        prontos para o escritor Excel.
        """
        return {
            "dre":         dre,
            "balanco":     bp,
            "indicadores": indicadores,
            "macro":       macro,
            "mercado":     dados_mercado,
        }
