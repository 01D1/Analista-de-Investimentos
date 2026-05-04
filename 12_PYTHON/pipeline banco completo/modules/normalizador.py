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

        # Sem anos com dados — retorna imediatamente sem tentar calcular derivadas
        if dre.empty or len(dre.columns) == 0:
            return dre

        # ── Contas calculadas ──────────────────────────────────────────────
        # Regra: só sobrescreve uma linha se ela ainda não foi lida diretamente
        # (i.e., não está no index ou está toda zerada).

        def _set_calc(df, key, value):
            """
            Escreve valor calculado onde o valor direto está ausente (zero/NaN).
            Faz preenchimento por ano individual para não descartar valores válidos
            em outros anos quando apenas um ano está zerado.
            """
            if df.empty or len(df.columns) == 0:
                return
            if key not in df.index:
                df.loc[key] = value
                return
            existing = df.loc[key]
            needs_fill = (existing == 0) | existing.isna()
            if not needs_fill.any():
                return  # todos os anos já têm valor — não sobrescreve
            # Preenche apenas os anos onde o valor está ausente/zero
            try:
                fill_vals = value if isinstance(value, pd.Series) else pd.Series(
                    value, index=existing.index)
                df.loc[key] = existing.where(~needs_fill, fill_vals)
            except Exception:
                if needs_fill.all():
                    df.loc[key] = value

        # MFB: lida diretamente de 3.03; soma como fallback caso 3.03 esteja vazio
        if "receita_juros_total" in dre.index and "despesa_juros_total" in dre.index:
            _set_calc(dre, "margem_financeira_bruta",
                      dre.loc["receita_juros_total"] + dre.loc["despesa_juros_total"])

        # MFL: sempre calculada (sem código CVM direto)
        if ("margem_financeira_bruta" in dre.index and
                "provisao_credito" in dre.index):
            _set_calc(dre, "margem_financeira_liquida",
                      dre.loc["margem_financeira_bruta"] + dre.loc["provisao_credito"])

        # resultado_operacional: calculado a partir de MFL + receitas - despesas
        # Só aplica se 3.05 não foi lido (i.e., ainda está zerado)
        if "margem_financeira_liquida" in dre.index:
            receitas = [c for c in ["resultado_seguros", "receita_servicos",
                                     "resultado_participacoes"]
                        if c in dre.index]
            despesas = [c for c in ["despesa_pessoal", "outras_despesas_operacionais"]
                        if c in dre.index]
            calc_res_op = (
                dre.loc["margem_financeira_liquida"] +
                dre.loc[receitas].sum() -
                dre.loc[despesas].abs().sum()
            ) if receitas else dre.loc["margem_financeira_liquida"]
            _set_calc(dre, "resultado_operacional", calc_res_op)

        # resultado_antes_ir: lido de 3.05; calculado como fallback
        if "resultado_operacional" in dre.index:
            res_nao_op = (dre.loc["resultado_nao_operacional"]
                          if ("resultado_nao_operacional" in dre.index and
                              (dre.loc["resultado_nao_operacional"] != 0).any())
                          else 0)
            _set_calc(dre, "resultado_antes_ir",
                      dre.loc["resultado_operacional"] + res_nao_op)

        # resultado_antes_minoritarios: calculado (= pre-tax + IR/CSLL)
        if "resultado_antes_ir" in dre.index and "ir_csll" in dre.index:
            _set_calc(dre, "resultado_antes_minoritarios",
                      dre.loc["resultado_antes_ir"] + dre.loc["ir_csll"])

        # lucro_liquido: lido diretamente de 3.11.01;
        # calculado como fallback (resultado_antes_minoritarios + deduções)
        if "resultado_antes_minoritarios" in dre.index:
            estat = (dre.loc["participacoes_estatutarias"]
                     if "participacoes_estatutarias" in dre.index else 0)
            minor = (dre.loc["participacoes_minoritarias"]
                     if "participacoes_minoritarias" in dre.index else 0)
            _set_calc(dre, "lucro_liquido",
                      dre.loc["resultado_antes_minoritarios"] + estat + minor)

        # ── Contas calculadas — empresas não-financeiras (IFRS geral) ─────
        # EBITDA: será preenchido quando DFC estiver disponível (via inject_da)
        # Por enquanto, marca placeholder se EBIT existe mas EBITDA não
        if "ebit" in dre.index and "ebitda" not in dre.index:
            dre.loc["ebitda"] = dre.loc["ebit"]  # placeholder = EBIT (D&A será somada depois)

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

        # Sem anos com dados — retorna imediatamente sem tentar calcular derivadas
        if bp.empty or len(bp.columns) == 0:
            return bp

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
            depositos_calc = bp.loc[existentes_dep].sum()
            if "depositos_total" not in bp.index:
                if (depositos_calc != 0).any():
                    bp.loc["depositos_total"] = depositos_calc
            else:
                atual = bp.loc["depositos_total"]
                precisa_preencher = ((atual == 0) | atual.isna()) & (depositos_calc != 0)
                if precisa_preencher.any():
                    bp.loc["depositos_total"] = atual.where(
                        ~precisa_preencher,
                        depositos_calc,
                    )

        # Passivos onerosos
        pass_on = ["depositos_total", "captacoes_mercado_aberto",
                   "recursos_emissao_titulos", "obrigacoes_emprestimos",
                   "dividas_subordinadas"]
        existentes_po = [c for c in pass_on if c in bp.index]
        if existentes_po:
            bp.loc["passivos_onerosos_total"] = bp.loc[existentes_po].sum()

        # ── Contas calculadas — empresas não-financeiras ──────────────────
        # NCG (Necessidade de Capital de Giro)
        ncg_pos = [c for c in ["contas_receber", "estoques"] if c in bp.index]
        ncg_neg = [c for c in ["fornecedores"] if c in bp.index]
        if ncg_pos:
            bp.loc["capital_de_giro"] = (
                bp.loc[ncg_pos].sum() -
                (bp.loc[ncg_neg].sum() if ncg_neg else 0)
            )

        # Dívida bruta
        div_comps = [c for c in ["emprestimos_cp", "emprestimos_lp"] if c in bp.index]
        if div_comps:
            bp.loc["divida_bruta"] = bp.loc[div_comps].sum()

        # Dívida líquida
        if "divida_bruta" in bp.index:
            caixa_comps = [c for c in ["caixa_equivalentes", "aplicacoes_financeiras_cp"]
                           if c in bp.index]
            caixa_total = bp.loc[caixa_comps].sum() if caixa_comps else 0
            bp.loc["divida_liquida"] = bp.loc["divida_bruta"] - caixa_total

        # PL controladores (para empresas não-financeiras: PL - minoritários)
        if "patrimonio_liquido" in bp.index and "pl_controladores" not in bp.index:
            minor_pl = (bp.loc["participacoes_minoritarias_pl"]
                        if "participacoes_minoritarias_pl" in bp.index else 0)
            bp.loc["pl_controladores"] = bp.loc["patrimonio_liquido"] - minor_pl

        if "patrimonio_liquido" in bp.index and "pl_controladores" in bp.index:
            bp.loc["participacoes_nao_controladoras_pl"] = (
                bp.loc["patrimonio_liquido"] - bp.loc["pl_controladores"]
            )

        # Capital investido (PL + Dívida Líquida)
        if "patrimonio_liquido" in bp.index and "divida_liquida" in bp.index:
            bp.loc["capital_investido"] = (
                bp.loc["patrimonio_liquido"] + bp.loc["divida_liquida"]
            )

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
                "inadimplencia":    provisao_bp / carteira_bruta if carteira_bruta else None,  # proxy ECL stock / carteira
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

        return pd.DataFrame(ind)

    # ── DFC (empresas não-financeiras) ──────────────────────────────────────

    def normalizar_dfc(self, dados_brutos: dict[int, dict],
                        mapa_dfc: dict) -> pd.DataFrame:
        """
        Monta o fluxo de caixa histórico normalizado.

        Returns:
            DataFrame: index=nome_conta, columns=anos
        """
        if not mapa_dfc:
            return pd.DataFrame()

        anos   = sorted(dados_brutos.keys())
        linhas = {}

        from modules._helpers import extrair_valores_df

        for nome, config in mapa_dfc.items():
            if config.get("calculado"):
                continue
            serie = {}
            for ano in anos:
                dfs = dados_brutos.get(ano, {})
                # Preferir método indireto, fallback para direto
                df = dfs.get("dfc_mi")
                if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                    df = dfs.get("dfc_md")
                if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                    serie[ano] = 0.0
                    continue
                valor = extrair_valores_df(df, config["codigos"],
                                            periodo=f"{ano}-12-31")
                serie[ano] = round(valor * config.get("sinal", 1) / self.divisor, 3)
            linhas[nome] = serie

        dfc = pd.DataFrame(linhas).T

        if dfc.empty or len(dfc.columns) == 0:
            return dfc

        # CAPEX total = imobilizado + intangível
        capex_comps = [c for c in ["capex_imobilizado", "capex_intangivel"]
                       if c in dfc.index]
        if capex_comps:
            dfc.loc["capex_total"] = dfc.loc[capex_comps].sum()

        return dfc

    def inject_da(self, dre: pd.DataFrame, bp: pd.DataFrame) -> pd.DataFrame:
        """
        Estima D&A e atualiza EBITDA na DRE.

        Usa variação do imobilizado+intangível como proxy de D&A:
            D&A ≈ -(Δ Imobilizado + Δ Intangível) + CAPEX
        Se CAPEX não está disponível, usa aproximação conservadora:
            D&A ≈ Imobilizado_medio × taxa típica (5-8%)

        Na prática, a forma mais confiável é: EBITDA = EBIT + D&A,
        onde D&A é derivada da DFC (diferença entre caixa_gerado_operacoes
        e lucro_líquido + ajustes). Aqui aplicamos a forma simplificada
        usando dados do balanço.
        """
        if "ebit" not in dre.index:
            return dre

        anos = sorted(dre.columns)

        # Estimar D&A via balanço: taxa de depreciação × ativo imobilizado médio
        da_serie = {}
        for i, ano in enumerate(anos):
            imob = 0
            if "imobilizado" in bp.index:
                imob_atual = float(bp.loc["imobilizado", ano]) if ano in bp.columns else 0
                if i > 0:
                    imob_ant = float(bp.loc["imobilizado", anos[i-1]]) if anos[i-1] in bp.columns else 0
                    imob = (imob_atual + imob_ant) / 2
                else:
                    imob = imob_atual
            intang = 0
            if "intangivel" in bp.index:
                intang_atual = float(bp.loc["intangivel", ano]) if ano in bp.columns else 0
                if i > 0:
                    intang_ant = float(bp.loc["intangivel", anos[i-1]]) if anos[i-1] in bp.columns else 0
                    intang = (intang_atual + intang_ant) / 2
                else:
                    intang = intang_atual
            # Taxa de depreciação típica: ~7% do imobilizado, ~10% do intangível
            da_serie[ano] = abs(imob * 0.07 + intang * 0.10)

        for ano in anos:
            ebit_val = float(dre.loc["ebit", ano]) if ano in dre.columns else 0
            da_val   = da_serie.get(ano, 0)
            dre.loc["depreciacao_amortizacao", ano] = da_val
            dre.loc["ebitda", ano] = ebit_val + da_val

        return dre

    # ── Indicadores — empresas não-financeiras ───────────────────────────────

    def calcular_indicadores_geral(self, dre: pd.DataFrame,
                                    bp: pd.DataFrame,
                                    dados_mercado: dict,
                                    macro: dict,
                                    dfc: pd.DataFrame = None) -> pd.DataFrame:
        """
        Calcula indicadores financeiros para empresas NÃO-FINANCEIRAS.

        Indicadores:
          - Rentabilidade: ROE, ROA, ROIC, margens (bruta, EBITDA, líquida)
          - Eficiência: giro do ativo, SGA/receita
          - Alavancagem: DL/EBITDA, DL/PL, dívida bruta/PL
          - Cobertura: EBITDA/desp financeiras, EBIT/desp financeiras
          - Valuation helpers: EV, P/L, P/VP, EV/EBITDA
          - Macro benchmark: Selic, IPCA

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

        if dfc is None:
            dfc = pd.DataFrame()

        for ano in anos:
            # ── DRE ──────────────────────────────────────────────────────
            receita    = get(dre, "receita_liquida", ano)
            lucro_br   = get(dre, "lucro_bruto", ano)
            ebit       = get(dre, "ebit", ano)
            ebitda     = get(dre, "ebitda", ano)
            lucro      = get(dre, "lucro_liquido", ano)
            desp_fin   = abs(get(dre, "despesas_financeiras", ano))
            res_fin    = get(dre, "resultado_financeiro", ano)
            ir         = get(dre, "ir_csll", ano)
            ebt        = get(dre, "resultado_antes_ir", ano)
            desp_vend  = abs(get(dre, "despesas_vendas", ano))
            desp_adm   = abs(get(dre, "despesas_gerais_adm", ano))
            da         = get(dre, "depreciacao_amortizacao", ano)

            # ── Balanço ──────────────────────────────────────────────────
            ativo_total  = get(bp, "ativo_total", ano)
            pl_total     = get(bp, "patrimonio_liquido", ano)
            pl_ctrl      = get(bp, "pl_controladores", ano) or pl_total
            divida_bruta = get(bp, "divida_bruta", ano)
            divida_liq   = get(bp, "divida_liquida", ano)
            cap_invest   = get(bp, "capital_investido", ano)
            ncg          = get(bp, "capital_de_giro", ano)
            imobilizado  = get(bp, "imobilizado", ano)
            intangivel   = get(bp, "intangivel", ano)

            # Ano anterior para médias
            ano_ant      = ano - 1
            pl_ant       = get(bp, "pl_controladores", ano_ant) or get(bp, "patrimonio_liquido", ano_ant)
            at_ant       = get(bp, "ativo_total", ano_ant)
            ci_ant       = get(bp, "capital_investido", ano_ant)

            pl_med       = (pl_ctrl + pl_ant) / 2 if pl_ant else pl_ctrl
            at_med       = (ativo_total + at_ant) / 2 if at_ant else ativo_total
            ci_med       = (cap_invest + ci_ant) / 2 if ci_ant else cap_invest

            # NOPAT (lucro operacional líquido de impostos)
            aliquota_ef  = abs(ir / ebt) if ebt and ebt != 0 else 0.34
            nopat        = ebit * (1 - aliquota_ef) if ebit else 0

            # Macro
            selic = macro.get("historico", {}).get("selic_efet", {}).get(ano, 0)
            ipca  = macro.get("historico", {}).get("ipca", {}).get(ano, 0)

            # ── DFC ──────────────────────────────────────────────────────
            capex_total  = abs(get(dfc, "capex_total", ano))
            fluxo_op     = get(dfc, "fluxo_operacional", ano)

            # ── Mercado (para múltiplos) ─────────────────────────────────
            preco_on     = dados_mercado.get("preco", 0)
            acoes_total  = dados_mercado.get("acoes_total", 0)
            market_cap   = preco_on * acoes_total / 1000 if preco_on and acoes_total else 0
            # market_cap está em R$ MM (acoes em mil, preco em R$)
            ev           = market_cap + divida_liq if market_cap else 0

            ind[ano] = {
                # ── Rentabilidade ────────────────────────────────────────
                "roe":              lucro / pl_med if pl_med else 0,
                "roa":              lucro / at_med if at_med else 0,
                "roic":             nopat / ci_med if ci_med else 0,
                "margem_bruta":     lucro_br / receita if receita else 0,
                "margem_ebitda":    ebitda / receita if receita else 0,
                "margem_ebit":      ebit / receita if receita else 0,
                "margem_liquida":   lucro / receita if receita else 0,

                # ── Eficiência ───────────────────────────────────────────
                "giro_ativo":       receita / at_med if at_med else 0,
                "sga_receita":      (desp_vend + desp_adm) / receita if receita else 0,
                "aliquota_ir":      abs(ir / ebt) if ebt else 0,

                # ── Alavancagem ──────────────────────────────────────────
                "dl_ebitda":        divida_liq / ebitda if ebitda else 0,
                "dl_pl":            divida_liq / pl_total if pl_total else 0,
                "divida_bruta_pl":  divida_bruta / pl_total if pl_total else 0,
                "alavancagem":      ativo_total / pl_total if pl_total else 0,

                # ── Cobertura ────────────────────────────────────────────
                "cobertura_juros_ebitda": ebitda / desp_fin if desp_fin else 0,
                "cobertura_juros_ebit":   ebit / desp_fin if desp_fin else 0,

                # ── Capital de giro e investimento ───────────────────────
                "ncg_receita":      ncg / receita if receita else 0,
                "capex_receita":    capex_total / receita if receita and capex_total else 0,
                "fluxo_op_mm":      fluxo_op,
                "capex_mm":         capex_total,

                # ── Valuation multiples (último ano apenas, usa cotação atual)
                "ev_ebitda":        ev / ebitda if ebitda and ev else 0,
                "p_l":              market_cap / lucro if lucro and market_cap else 0,
                "p_vp":             market_cap / pl_ctrl if pl_ctrl and market_cap else 0,

                # ── Macro benchmark ──────────────────────────────────────
                "selic":            selic,
                "ipca":             ipca,

                # ── Valores absolutos úteis ──────────────────────────────
                "receita_mm":       receita,
                "ebitda_mm":        ebitda,
                "ebit_mm":          ebit,
                "lucro_mm":         lucro,
                "ativo_total_mm":   ativo_total,
                "divida_liquida_mm": divida_liq,
                "pl_mm":            pl_total,
                "nopat_mm":         nopat,
                "da_mm":            da,
            }

        return pd.DataFrame(ind)

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
