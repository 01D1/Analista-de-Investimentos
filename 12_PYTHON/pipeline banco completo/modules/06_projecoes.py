"""
Módulo 06 — Motor de Projeções
Projeta os dados históricos para os anos futuros.

Metodologia:
  - NIM: regressão linear + convergência para mediana setorial
  - Carteira de crédito: crescimento premissado por ano
  - Provisão: regressão NPL × PCLD + convergência
  - Receita de serviços: crescimento pelo PIB nominal
  - Despesas: % da receita ou crescimento nominal
  - CAPEX/D&A: % dos ativos
  - Capital regulatório: Basileia target × ΔRWA
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("pipeline.projecoes")


class MotorProjecoes:
    """Gera projeções financeiras para bancos."""

    def __init__(self, config: dict):
        """
        Args:
            config: dicionário do settings.py com premissas
        """
        self.cfg = config

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ultimo_valor(self, serie: pd.Series) -> float:
        """Retorna o último valor não-nulo de uma série."""
        validos = serie.dropna().replace(0, np.nan).dropna()
        return float(validos.iloc[-1]) if not validos.empty else 0.0

    def _media_historica(self, serie: pd.Series, n: int = 5) -> float:
        """Média dos últimos n valores."""
        validos = serie.dropna().replace(0, np.nan).dropna()
        return float(validos.tail(n).mean()) if not validos.empty else 0.0

    def _convergir(self, valor_atual: float, valor_alvo: float,
                   n_anos: int, ano_atual: int, ano: int) -> float:
        """Interpola linearmente entre valor_atual e valor_alvo ao longo de n_anos."""
        if n_anos <= 0 or ano <= ano_atual:
            return valor_atual
        passos = ano - ano_atual
        if passos >= n_anos:
            return valor_alvo
        return valor_atual + (valor_alvo - valor_atual) * (passos / n_anos)

    # ── NIM e Margem Financeira ───────────────────────────────────────────────

    def projetar_nim(self, nim_hist: pd.Series,
                     selic_proj: dict[int, float],
                     anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta o NIM por ano.
        Metodologia: NIM = f(Selic) via regressão histórica + convergência para mediana.

        Args:
            nim_hist:   Série histórica de NIM (index=ano)
            selic_proj: Selic projetada por ano
            anos_proj:  Lista de anos a projetar
        """
        nim_alvo   = self.cfg.get("NIM_ALVO", 0.076)
        nim_atual  = self._ultimo_valor(nim_hist)
        n_conv     = 6   # convergência em 6 anos

        # Regressão NIM ~ Selic histórica
        nim_clean  = nim_hist.dropna().replace(0, np.nan).dropna()
        slope_nim_selic = 0.0
        intercept_nim   = nim_atual

        if len(nim_clean) >= 3:
            anos_hist = nim_clean.index.astype(int).tolist()
            # Tentativa de usar Selic histórica se disponível
            try:
                selic_vals = [selic_proj.get(a, 0.10) for a in anos_hist]
                if any(s > 0 for s in selic_vals):
                    x = np.array(selic_vals)
                    y = nim_clean.values
                    cov = np.cov(x, y)
                    slope_nim_selic = cov[0][1] / cov[0][0] if cov[0][0] != 0 else 0
                    intercept_nim   = np.mean(y) - slope_nim_selic * np.mean(x)
                    logger.info(f"  NIM ~ Selic: slope={slope_nim_selic:.4f}, "
                                f"intercept={intercept_nim:.4f}")
            except Exception:
                pass

        ano_base = int(nim_clean.index[-1]) if not nim_clean.empty else anos_proj[0] - 1
        resultado = {}

        for ano in anos_proj:
            selic = selic_proj.get(ano, 0.10)

            # Modelo base: regressão com Selic
            nim_regressao = intercept_nim + slope_nim_selic * selic

            # Convergência para mediana setorial
            nim_conv = self._convergir(nim_atual, nim_alvo, n_conv, ano_base, ano)

            # Ponderar: 50% regressão + 50% convergência
            nim_proj = 0.5 * nim_regressao + 0.5 * nim_conv
            nim_proj = max(nim_proj, 0.02)   # floor razoável

            resultado[ano] = round(nim_proj, 5)
            logger.debug(f"  NIM {ano}: {nim_proj:.4%} "
                         f"(reg={nim_regressao:.4%}, conv={nim_conv:.4%})")

        return resultado

    def projetar_margem_clientes(self,
                                  carteira_proj: dict[int, float],
                                  spread_clientes_hist: pd.Series,
                                  selic_proj: dict[int, float],
                                  anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta margem financeira com clientes.
        = Carteira de crédito × spread com clientes
        """
        spread_alvo = self.cfg.get("NIM_ALVO", 0.076)
        spread_atual = self._ultimo_valor(spread_clientes_hist)
        ano_base = anos_proj[0] - 1

        resultado = {}
        for i, ano in enumerate(anos_proj):
            spread = self._convergir(spread_atual, spread_alvo, 8, ano_base, ano)
            carteira = carteira_proj.get(ano, 0)
            resultado[ano] = round(carteira * spread, 3)

        return resultado

    def projetar_margem_mercado(self,
                                 at_remuneraveis_proj: dict[int, float],
                                 nim_proj: dict[int, float],
                                 margem_clientes_proj: dict[int, float],
                                 anos_proj: list[int]) -> dict[int, float]:
        """
        Margem com mercado = MFB total - Margem com clientes.
        MFB total = Ativos remuneráveis × NIM
        """
        resultado = {}
        for ano in anos_proj:
            mfb_total = at_remuneraveis_proj.get(ano, 0) * nim_proj.get(ano, 0)
            marg_cli  = margem_clientes_proj.get(ano, 0)
            resultado[ano] = round(mfb_total - marg_cli, 3)
        return resultado

    # ── Carteira de Crédito ───────────────────────────────────────────────────

    def projetar_carteira(self, carteira_hist: pd.Series,
                           anos_proj: list[int],
                           crescimentos_premissados: dict = None) -> dict[int, float]:
        """
        Projeta carteira de crédito expandida.
        Usa crescimentos do settings ou CAGR histórico como fallback.
        """
        crescimentos = crescimentos_premissados or self.cfg.get(
            "CRESCIMENTO_CARTEIRA_CREDITO", {})

        ultimo = self._ultimo_valor(carteira_hist)
        resultado = {}
        valor = ultimo

        for ano in anos_proj:
            g = crescimentos.get(ano, 0.07)
            valor = valor * (1 + g)
            resultado[ano] = round(valor, 3)
            logger.debug(f"  Carteira {ano}: R$ {valor:,.0f} MM (+{g:.1%})")

        return resultado

    # ── Provisão ──────────────────────────────────────────────────────────────

    def projetar_provisao(self, pcld_pct_hist: pd.Series,
                           npl_hist: pd.Series,
                           carteira_proj: dict[int, float],
                           anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta despesa de provisão.
        Metodologia: regressão linear NPL → PCLD/Carteira + convergência.
        """
        pcld_alvo  = self.cfg.get("PCLD_PCT_ALVO", 0.035)
        pcld_atual = self._ultimo_valor(pcld_pct_hist)
        npl_med    = self._media_historica(npl_hist, 5) if not npl_hist.empty else 0.04
        ano_base   = anos_proj[0] - 1

        resultado = {}
        for ano in anos_proj:
            # Convergência linear para pcld_alvo em 5 anos
            pcld_pct = self._convergir(pcld_atual, pcld_alvo, 5, ano_base, ano)
            carteira = carteira_proj.get(ano, 0)
            resultado[ano] = round(-carteira * pcld_pct, 3)   # negativo (despesa)

        return resultado

    # ── Ativos Remuneráveis ───────────────────────────────────────────────────

    def projetar_ativos_remuneraveis(self,
                                      ar_hist: pd.Series,
                                      carteira_proj: dict[int, float],
                                      anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta ativos remuneráveis.
        Usa relação histórica carteira/ativos remuneráveis.
        """
        # Razão média histórica: carteira / ativos remuneráveis
        ar_clean = ar_hist.dropna().replace(0, np.nan).dropna()

        # Estimativa: AR cresce proporcionalmente à carteira
        ultimo_ar = self._ultimo_valor(ar_hist)
        ultimo_cart_hist = list(carteira_proj.values())[0] / (
            1 + self.cfg.get("CRESCIMENTO_CARTEIRA_CREDITO", {}).get(
                anos_proj[0], 0.07))

        ratio = ultimo_ar / ultimo_cart_hist if ultimo_cart_hist else 2.2

        resultado = {}
        for ano in anos_proj:
            carteira = carteira_proj.get(ano, 0)
            resultado[ano] = round(carteira * ratio, 3)

        return resultado

    # ── Receita de Serviços ───────────────────────────────────────────────────

    def projetar_servicos(self, servicos_hist: pd.Series,
                           anos_proj: list[int],
                           crescimentos: dict = None) -> dict[int, float]:
        """Projeta receita de serviços pelo PIB nominal."""
        g_map   = crescimentos or self.cfg.get("CRESCIMENTO_SERVICOS", {})
        ultimo  = self._ultimo_valor(servicos_hist)
        valor   = ultimo
        resultado = {}

        for ano in anos_proj:
            g = g_map.get(ano, 0.065)
            valor = valor * (1 + g)
            resultado[ano] = round(valor, 3)

        return resultado

    # ── Despesas ──────────────────────────────────────────────────────────────

    def projetar_despesas_pessoal(self, pessoal_hist: pd.Series,
                                   anos_proj: list[int],
                                   ipca_proj: dict) -> dict[int, float]:
        """Projeta despesas de pessoal: crescimento = IPCA + produtividade."""
        ultimo = abs(self._ultimo_valor(pessoal_hist))
        resultado = {}
        valor = ultimo

        for ano in anos_proj:
            ipca = ipca_proj.get(ano, 0.045)
            g    = ipca + 0.015   # IPCA + 1.5% de aumento real
            valor = valor * (1 + g)
            resultado[ano] = round(-valor, 3)   # negativo

        return resultado

    def projetar_outras_despesas(self, outras_hist: pd.Series,
                                  mfb_proj: dict[int, float],
                                  anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta outras despesas operacionais.
        Usa % histórica sobre MFB + crescimento gradual.
        """
        hist_clean = outras_hist.abs().dropna().replace(0, np.nan).dropna()
        pct_mfb_hist = 0.35   # default 35% da MFB

        ultimo = abs(self._ultimo_valor(outras_hist))
        resultado = {}
        valor = ultimo

        for ano in anos_proj:
            g = 0.05   # crescimento moderado
            valor = valor * (1 + g)
            resultado[ano] = round(-valor, 3)

        return resultado

    # ── CAPEX e D&A ──────────────────────────────────────────────────────────

    def projetar_capex_da(self, ativo_hist: pd.Series,
                           anos_proj: list[int],
                           capex_pct: float = None,
                           da_pct: float = None) -> tuple[dict, dict]:
        """
        Projeta CAPEX e Depreciação/Amortização como % do ativo total.

        Returns:
            (capex_proj, da_proj) — ambos positivos (FCF já faz o ajuste de sinal)
        """
        capex_pct = capex_pct or self.cfg.get("CAPEX_PCT_ATIVO", 0.0015)
        da_pct    = da_pct or 0.0010   # D&A para bancos é muito baixo

        ultimo_ativo = self._ultimo_valor(ativo_hist)
        g_ativo      = 0.08   # crescimento médio do ativo

        capex_proj = {}
        da_proj    = {}
        ativo      = ultimo_ativo

        for ano in anos_proj:
            ativo = ativo * (1 + g_ativo)
            capex_proj[ano] = round(-ativo * capex_pct, 3)   # negativo
            da_proj[ano]    = round(ativo * da_pct, 3)        # positivo

        return capex_proj, da_proj

    # ── Capital Regulatório ───────────────────────────────────────────────────

    def projetar_capital_regulatorio(self,
                                      carteira_proj: dict[int, float],
                                      pl_hist: pd.Series,
                                      anos_proj: list[int]) -> dict[int, float]:
        """
        Variação do capital regulatório = ΔRWA × (Basileia alvo - Basileia atual).
        RWA ≈ Carteira de crédito / 0.6 (fator de ponderação médio)

        Resultado negativo = capital retido (subtrai do FCFE).
        """
        basileia_alvo = self.cfg.get("BASILEIA_ALVO", 0.135)
        ponderacao_rwa = 0.60   # carteira / RWA
        resultado = {}

        anos_lista = sorted(carteira_proj.keys())
        for i, ano in enumerate(anos_proj):
            cart_atual = carteira_proj.get(ano, 0)
            cart_ant   = carteira_proj.get(ano - 1, cart_atual / 1.07)

            delta_rwa = (cart_atual - cart_ant) / ponderacao_rwa
            delta_cap = delta_rwa * basileia_alvo
            resultado[ano] = round(-delta_cap, 3)   # negativo = retenção de capital

        return resultado

    # ── Seguros ───────────────────────────────────────────────────────────────

    def projetar_seguros(self, seguros_hist: pd.Series,
                          anos_proj: list[int]) -> dict[int, float]:
        """Projeta resultado de seguros/previdência com crescimento histórico."""
        cagr = 0.055   # default
        try:
            clean = seguros_hist.dropna().replace(0, np.nan).dropna()
            if len(clean) >= 3:
                cagr = (clean.iloc[-1] / clean.iloc[0]) ** (1/(len(clean)-1)) - 1
                cagr = max(min(cagr, 0.12), 0.03)   # clamp 3% - 12%
        except Exception:
            pass

        ultimo   = self._ultimo_valor(seguros_hist)
        resultado = {}
        valor    = ultimo

        for ano in anos_proj:
            valor = valor * (1 + cagr)
            resultado[ano] = round(valor, 3)

        return resultado

    # ── IR / CSLL ─────────────────────────────────────────────────────────────

    def projetar_ir(self, aliquota_hist: pd.Series,
                    resultado_op_proj: dict[int, float],
                    anos_proj: list[int]) -> dict[int, float]:
        """Projeta IR/CSLL = alíquota efetiva × resultado operacional."""
        aliquota_med = self._media_historica(aliquota_hist, 5)
        if aliquota_med <= 0:
            aliquota_med = 0.20   # alíquota padrão

        resultado = {}
        for ano in anos_proj:
            res_op = resultado_op_proj.get(ano, 0)
            resultado[ano] = round(-abs(res_op) * aliquota_med, 3)

        return resultado

    # ── Orquestrador de projeções ─────────────────────────────────────────────

    def projetar_tudo(self, dados_norm: dict,
                       macro_proj: dict,
                       anos_proj: list[int]) -> dict:
        """
        Roda todas as projeções em sequência e retorna um dicionário
        com todas as linhas projetadas, pronto para o escritor Excel.

        Returns:
            dict {nome_linha: {ano: valor}}
        """
        dre = dados_norm.get("dre", pd.DataFrame())
        bp  = dados_norm.get("balanco", pd.DataFrame())
        ind = dados_norm.get("indicadores", pd.DataFrame())

        def serie(df, linha):
            if linha in df.index:
                s = df.loc[linha]
                s.index = s.index.astype(int)
                return s
            return pd.Series(dtype=float)

        selic_proj = macro_proj.get("projecao", {}).get("di", {})
        ipca_proj  = macro_proj.get("projecao", {}).get("ipca", {})

        logger.info("\n=== Rodando projeções ===")

        # 1. Carteira de crédito
        carteira_proj = self.projetar_carteira(
            serie(bp, "carteira_credito_bruta"), anos_proj)

        # 2. Ativos remuneráveis
        ar_proj = self.projetar_ativos_remuneraveis(
            serie(bp, "ativos_remuneraveis"), carteira_proj, anos_proj)

        # 3. NIM
        nim_hist  = serie(ind, "nim") if "nim" in ind.columns else pd.Series(dtype=float)
        nim_proj  = self.projetar_nim(nim_hist, selic_proj, anos_proj)

        # 4. Margem financeira bruta
        spread_cli = serie(ind, "nim")   # proxy
        mfb_proj   = {a: ar_proj[a] * nim_proj[a] for a in anos_proj}

        # 5. Margem com clientes e mercado
        mc_proj = self.projetar_margem_clientes(
            carteira_proj, spread_cli, selic_proj, anos_proj)
        mm_proj = {a: mfb_proj[a] - mc_proj[a] for a in anos_proj}

        # 6. Provisão
        pcld_pct_hist = serie(ind, "pcld_carteira") if "pcld_carteira" in ind.columns else pd.Series(dtype=float)
        provisao_proj = self.projetar_provisao(
            pcld_pct_hist, pd.Series(dtype=float), carteira_proj, anos_proj)

        # 7. MFL
        mfl_proj = {a: mfb_proj[a] + provisao_proj[a] for a in anos_proj}

        # 8. Serviços
        servicos_proj = self.projetar_servicos(
            serie(dre, "receita_servicos"), anos_proj)

        # 9. Seguros
        seguros_proj = self.projetar_seguros(
            serie(dre, "resultado_seguros"), anos_proj)

        # 10. Despesas
        pessoal_proj = self.projetar_despesas_pessoal(
            serie(dre, "despesa_pessoal"), anos_proj, ipca_proj)
        outras_proj  = self.projetar_outras_despesas(
            serie(dre, "outras_despesas_operacionais"),
            mfb_proj, anos_proj)

        # 11. Participações (Previ etc.)
        participacoes_proj = self.projetar_servicos(
            serie(dre, "resultado_participacoes"), anos_proj,
            {a: 0.065 for a in anos_proj})

        # 12. Resultado operacional
        res_op_proj = {
            a: (mfl_proj[a] + servicos_proj[a] + seguros_proj[a] +
                participacoes_proj[a] + pessoal_proj[a] + outras_proj[a])
            for a in anos_proj
        }

        # 13. IR
        aliq_hist = serie(ind, "aliquota_ir") if "aliquota_ir" in ind.columns else pd.Series(dtype=float)
        ir_proj   = self.projetar_ir(aliq_hist, res_op_proj, anos_proj)

        # 14. Lucro líquido (simplificado — sem minoritários por ora)
        lucro_proj = {a: res_op_proj[a] + ir_proj[a] for a in anos_proj}

        # 15. CAPEX, D&A
        capex_proj, da_proj = self.projetar_capex_da(
            serie(bp, "ativo_total"), anos_proj)

        # 16. Capital regulatório
        cap_reg_proj = self.projetar_capital_regulatorio(
            carteira_proj, serie(bp, "pl_controladores"), anos_proj)

        # 17. FCFE
        fcfe_proj = {
            a: lucro_proj[a] + da_proj[a] + capex_proj[a] + cap_reg_proj[a]
            for a in anos_proj
        }

        logger.info("Projeções concluídas. Resumo:")
        logger.info(f"{'Ano':>6} {'Carteira':>12} {'MFB':>10} {'Lucro':>10} {'FCFE':>10}")
        for a in anos_proj[:5]:
            logger.info(f"{a:>6} {carteira_proj[a]:>12,.0f} "
                        f"{mfb_proj[a]:>10,.0f} "
                        f"{lucro_proj[a]:>10,.0f} "
                        f"{fcfe_proj[a]:>10,.0f}")

        return {
            "carteira_credito_bruta":       carteira_proj,
            "ativos_remuneraveis":          ar_proj,
            "nim":                          nim_proj,
            "margem_financeira_bruta":      mfb_proj,
            "margem_clientes":              mc_proj,
            "margem_mercado":               mm_proj,
            "provisao_credito":             provisao_proj,
            "margem_financeira_liquida":    mfl_proj,
            "receita_servicos":             servicos_proj,
            "resultado_seguros":            seguros_proj,
            "despesa_pessoal":              pessoal_proj,
            "outras_despesas":              outras_proj,
            "resultado_participacoes":      participacoes_proj,
            "resultado_operacional":        res_op_proj,
            "ir_csll":                      ir_proj,
            "lucro_liquido":                lucro_proj,
            "da":                           da_proj,
            "capex":                        capex_proj,
            "capital_regulatorio":          cap_reg_proj,
            "fcfe":                         fcfe_proj,
        }
