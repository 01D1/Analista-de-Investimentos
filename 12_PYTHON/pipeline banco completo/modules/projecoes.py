"""
Módulo 06 — Motor de Projeções
Projeta os dados históricos para os anos futuros.

Dois motores:
  - MotorProjecoes: bancos (FCFE) — NIM, carteira, provisão, Ke
  - MotorProjecoesGeral: empresas não-financeiras (FCFF) — receita,
    margem EBITDA, CAPEX, NCG, resultado financeiro, WACC
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
        nim_maximo = self.cfg.get("NIM_MAXIMO", float("inf"))
        resultado = {}

        for ano in anos_proj:
            selic = selic_proj.get(ano, 0.10)

            # Modelo base: regressão com Selic
            nim_regressao = intercept_nim + slope_nim_selic * selic

            # Convergência para mediana setorial
            nim_conv = self._convergir(nim_atual, nim_alvo, n_conv, ano_base, ano)

            # Ponderar: 50% regressão + 50% convergência
            nim_proj = 0.5 * nim_regressao + 0.5 * nim_conv
            nim_proj = max(nim_proj, 0.005)        # floor mínimo
            nim_proj = min(nim_proj, nim_maximo)   # cap por banco (evita inflação)

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
            # Usar apenas valores positivos para evitar NaN ao elevar base negativa
            clean_pos = clean[clean > 0]
            if len(clean_pos) >= 3:
                ratio = clean_pos.iloc[-1] / clean_pos.iloc[0]
                if ratio > 0:   # guard: base positiva para potência fracionária
                    cagr = ratio ** (1 / (len(clean_pos) - 1)) - 1
                    cagr = max(min(cagr, 0.12), 0.03)
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
        """
        Projeta IR/CSLL = alíquota efetiva × resultado operacional.

        Para bancos brasileiros, a alíquota estatutária de IR+CSLL é ~34%.
        A alíquota efetiva oscila muito por créditos tributários e diferidos.
        Usa-se a mediana (mais robusta que a média) com clamp [10%, 40%].
        """
        # Clamp histórico para excluir distorções de crédito tributário
        validos = aliquota_hist.dropna().replace(0, np.nan).dropna()
        validos_clamp = validos[(validos >= 0.05) & (validos <= 0.50)]

        if not validos_clamp.empty:
            # Mediana: mais robusta contra outliers de deferred tax
            aliquota_med = float(validos_clamp.median())
        else:
            aliquota_med = 0.25   # alíquota típica para bancos (34% nominal - benefícios)

        # Garante intervalo razoável
        aliquota_med = max(0.10, min(aliquota_med, 0.35))

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
            """Extrai série histórica de um DataFrame com orientação flexível."""
            if df is None or df.empty:
                return pd.Series(dtype=float)
            if linha in df.index:
                s = df.loc[linha]
                s.index = s.index.astype(int)
                return s
            if linha in df.columns:
                s = df[linha]
                s.index = s.index.astype(int)
                return s
            return pd.Series(dtype=float)

        selic_proj  = macro_proj.get("projecao",  {}).get("di", {})
        ipca_proj   = macro_proj.get("projecao",  {}).get("ipca", {})
        selic_hist  = macro_proj.get("historico", {}).get("selic_efet", {})

        # Série combinada Selic: histórico (anos reais) + projeção (anos futuros)
        # Necessária para a regressão NIM ~ Selic usar dados históricos reais
        selic_completa = {**selic_hist, **selic_proj}

        logger.info("\n=== Rodando projeções ===")

        # 1. Carteira de crédito
        carteira_proj = self.projetar_carteira(
            serie(bp, "carteira_credito_bruta"), anos_proj)

        # 2. Ativos remuneráveis
        ar_proj = self.projetar_ativos_remuneraveis(
            serie(bp, "ativos_remuneraveis"), carteira_proj, anos_proj)

        # 3. NIM
        nim_hist  = serie(ind, "nim")
        # Passa selic_completa para que a regressão use selic histórica real
        nim_proj  = self.projetar_nim(nim_hist, selic_completa, anos_proj)

        # 4. Margem financeira bruta
        spread_cli = serie(ind, "nim")   # proxy
        mfb_proj   = {a: ar_proj[a] * nim_proj[a] for a in anos_proj}

        # 5. Margem com clientes e mercado
        mc_proj = self.projetar_margem_clientes(
            carteira_proj, spread_cli, selic_proj, anos_proj)
        mm_proj = {a: mfb_proj[a] - mc_proj[a] for a in anos_proj}

        # 6. Provisão
        pcld_pct_hist = serie(ind, "pcld_carteira")
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

        # 12. Resultado operacional (pré-IR)
        #
        # Metodologia: projeta diretamente como proporção da MFB.
        # A abordagem bottom-up (soma de componentes) é instável para bancos
        # porque os mapeamentos de contas variam entre anos e omitem despesas.
        # Usar a margem operacional/MFB histórica é mais robusta.
        res_op_hist    = serie(dre, "resultado_operacional")
        mfb_hist_serie = serie(dre, "margem_financeira_bruta")

        margens_hist = {}
        for a in res_op_hist.index:
            mfb_a = float(mfb_hist_serie.get(a, 0)) if a in mfb_hist_serie.index else 0
            if mfb_a != 0 and not np.isnan(float(res_op_hist.get(a, 0))):
                margens_hist[a] = float(res_op_hist.get(a, 0)) / mfb_a

        # Mediana dos últimos 5 anos (mais robusta que média contra outliers)
        recentes = sorted(margens_hist.keys())[-5:]
        margem_alvo = (float(np.median([margens_hist[a] for a in recentes]))
                       if recentes else 0.22)
        # Clamp razoável: 8% a 45% da MFB como resultado operacional
        margem_alvo = max(0.08, min(margem_alvo, 0.45))
        logger.info(f"  Margem op./MFB histórica (median 5a): {margem_alvo:.2%}")

        # Mantém as linhas individuais projetadas para o template Excel,
        # mas usa o res_op direto para o lucro (mais confiável)
        res_op_proj = {a: round(mfb_proj[a] * margem_alvo, 3) for a in anos_proj}

        # 13. IR
        aliq_hist = serie(ind, "aliquota_ir")
        ir_proj   = self.projetar_ir(aliq_hist, res_op_proj, anos_proj)

        # 14. Lucro líquido
        lucro_proj = {a: res_op_proj[a] + ir_proj[a] for a in anos_proj}

        # 15. CAPEX, D&A (menos relevante para bancos — manutenção infra)
        capex_proj, da_proj = self.projetar_capex_da(
            serie(bp, "ativo_total"), anos_proj)

        # 16. Capital regulatório (retenção de capital para suportar crescimento)
        cap_reg_proj = self.projetar_capital_regulatorio(
            carteira_proj, serie(bp, "pl_controladores"), anos_proj)

        # 17. FCFE = Lucro × payout  (modelo simplificado para bancos)
        # Para bancos, FCFE ≈ dividendos pagos = lucro × (1 - retention_rate).
        # A abordagem alternativa (lucro + D&A + CAPEX + Δcapital) produz valores
        # muito negativos quando o banco cresce rápido e já tem capital excedente.
        payout = self.cfg.get("PAYOUT_PROJETADO", 0.45)
        fcfe_proj = {a: round(lucro_proj[a] * payout, 3) for a in anos_proj}

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
            "outras_despesas_operacionais":  outras_proj,
            "resultado_participacoes":      participacoes_proj,
            "resultado_operacional":        res_op_proj,
            "ir_csll":                      ir_proj,
            "lucro_liquido":                lucro_proj,
            "da":                           da_proj,
            "capex":                        capex_proj,
            "capital_regulatorio":          cap_reg_proj,
            "fcfe":                         fcfe_proj,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Motor de Projeções — Empresas Não-Financeiras (FCFF)
# ═══════════════════════════════════════════════════════════════════════════════

class MotorProjecoesGeral:
    """
    Gera projeções financeiras para empresas não-financeiras.

    Metodologia FCFF:
      1. Receita: crescimento premissado (convergindo para g_perpetuidade)
      2. EBITDA: margem convergindo para alvo setorial
      3. D&A: % da receita (histórico)
      4. EBIT: EBITDA - D&A
      5. NOPAT: EBIT × (1 - alíquota efetiva)
      6. CAPEX: % da receita (premissa setorial)
      7. ΔNCG: variação da necessidade de capital de giro
      8. FCFF: NOPAT + D&A - CAPEX - ΔNCG
      9. Resultado financeiro, IR, lucro líquido (para template)
    """

    def __init__(self, config: dict, premissas_empresa: dict = None):
        """
        Args:
            config: dict do settings.py
            premissas_empresa: premissas mescladas (empresa > setor > global)
        """
        self.cfg = config
        self.prem = premissas_empresa or {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ultimo_valor(self, serie: pd.Series) -> float:
        validos = serie.dropna().replace(0, np.nan).dropna()
        return float(validos.iloc[-1]) if not validos.empty else 0.0

    def _media_historica(self, serie: pd.Series, n: int = 5) -> float:
        validos = serie.dropna().replace(0, np.nan).dropna()
        return float(validos.tail(n).mean()) if not validos.empty else 0.0

    def _convergir(self, valor_atual: float, valor_alvo: float,
                   n_anos: int, ano_base: int, ano: int) -> float:
        if n_anos <= 0 or ano <= ano_base:
            return valor_atual
        passos = ano - ano_base
        if passos >= n_anos:
            return valor_alvo
        return valor_atual + (valor_alvo - valor_atual) * (passos / n_anos)

    # ── Receita ──────────────────────────────────────────────────────────────

    def projetar_receita(self, receita_hist: pd.Series,
                          anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta receita líquida com crescimento premissado por ano.
        Convergência para g_perpetuidade nos últimos anos.
        """
        crescimentos = self.prem.get("crescimento_receita", {})
        g_perp = self.prem.get("g_perpetuidade", 0.055)

        ultimo = self._ultimo_valor(receita_hist)
        resultado = {}
        valor = ultimo

        for i, ano in enumerate(anos_proj):
            # Premissa por ano, fallback para convergência linear até g_perp
            if isinstance(crescimentos, dict) and ano in crescimentos:
                g = crescimentos[ano]
            elif isinstance(crescimentos, (int, float)):
                g = float(crescimentos)
            else:
                # Default: começa em 8% e converge para g_perp em 6 anos
                g_inicio = 0.08
                g = self._convergir(g_inicio, g_perp, 6, anos_proj[0] - 1, ano)

            valor = valor * (1 + g)
            resultado[ano] = round(valor, 3)
            logger.debug(f"  Receita {ano}: R$ {valor:,.0f} MM (+{g:.1%})")

        return resultado

    # ── Margens e EBITDA ─────────────────────────────────────────────────────

    def projetar_ebitda(self, receita_proj: dict[int, float],
                         margem_ebitda_hist: pd.Series,
                         anos_proj: list[int]) -> tuple[dict, dict]:
        """
        Projeta EBITDA via convergência da margem EBITDA para alvo setorial.

        Returns:
            (ebitda_proj, margem_proj) — ambos dicts {ano: valor}
        """
        margem_alvo = self.prem.get("margem_ebitda_alvo", 0.25)
        margem_atual = self._ultimo_valor(margem_ebitda_hist)
        if margem_atual == 0:
            margem_atual = self._media_historica(margem_ebitda_hist)
        if margem_atual == 0:
            margem_atual = margem_alvo  # fallback

        ano_base = anos_proj[0] - 1
        n_conv = 6  # convergência em 6 anos

        ebitda_proj = {}
        margem_proj = {}

        for ano in anos_proj:
            margem = self._convergir(margem_atual, margem_alvo, n_conv, ano_base, ano)
            # Clamp: margem entre 5% e 60%
            margem = max(0.05, min(margem, 0.60))
            receita = receita_proj.get(ano, 0)
            ebitda_proj[ano] = round(receita * margem, 3)
            margem_proj[ano] = round(margem, 5)

        logger.info(f"  Margem EBITDA: {margem_atual:.1%} → {margem_alvo:.1%} (conv {n_conv}a)")
        return ebitda_proj, margem_proj

    # ── D&A ──────────────────────────────────────────────────────────────────

    def projetar_da(self, da_hist: pd.Series, receita_hist: pd.Series,
                     receita_proj: dict[int, float],
                     anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta D&A como % da receita (estável historicamente).
        """
        # Calcular D&A/Receita histórica média
        da_pct_hist = []
        for ano in da_hist.index:
            da_val = float(da_hist.get(ano, 0))
            rec_val = float(receita_hist.get(ano, 0)) if ano in receita_hist.index else 0
            if rec_val > 0 and da_val > 0:
                da_pct_hist.append(da_val / rec_val)

        da_pct = np.mean(da_pct_hist) if da_pct_hist else 0.05  # default 5%
        da_pct = max(0.01, min(da_pct, 0.20))  # clamp

        resultado = {}
        for ano in anos_proj:
            receita = receita_proj.get(ano, 0)
            resultado[ano] = round(receita * da_pct, 3)

        logger.info(f"  D&A/Receita: {da_pct:.1%}")
        return resultado

    # ── CAPEX ────────────────────────────────────────────────────────────────

    def projetar_capex(self, receita_proj: dict[int, float],
                        capex_hist: pd.Series, receita_hist: pd.Series,
                        anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta CAPEX como % da receita.
        Usa premissa setorial ou média histórica.
        """
        capex_pct_alvo = self.prem.get("capex_pct_receita", 0.05)

        # Média histórica
        capex_pct_hist = []
        for ano in capex_hist.index:
            capex_val = abs(float(capex_hist.get(ano, 0)))
            rec_val = float(receita_hist.get(ano, 0)) if ano in receita_hist.index else 0
            if rec_val > 0 and capex_val > 0:
                capex_pct_hist.append(capex_val / rec_val)

        capex_pct_atual = np.mean(capex_pct_hist) if capex_pct_hist else capex_pct_alvo
        ano_base = anos_proj[0] - 1

        resultado = {}
        for ano in anos_proj:
            pct = self._convergir(capex_pct_atual, capex_pct_alvo, 5, ano_base, ano)
            receita = receita_proj.get(ano, 0)
            resultado[ano] = round(-receita * pct, 3)  # negativo (investimento)

        logger.info(f"  CAPEX/Receita: {capex_pct_atual:.1%} → {capex_pct_alvo:.1%}")
        return resultado

    # ── NCG (Necessidade de Capital de Giro) ─────────────────────────────────

    def projetar_ncg(self, receita_proj: dict[int, float],
                      ncg_hist: pd.Series, receita_hist: pd.Series,
                      anos_proj: list[int]) -> tuple[dict, dict]:
        """
        Projeta NCG como % da receita e calcula variação (ΔNCG).

        Returns:
            (ncg_proj, delta_ncg_proj)
        """
        ncg_pct_alvo = self.prem.get("ncg_pct_receita", 0.15)

        # Média histórica
        ncg_pct_hist = []
        for ano in ncg_hist.index:
            ncg_val = float(ncg_hist.get(ano, 0))
            rec_val = float(receita_hist.get(ano, 0)) if ano in receita_hist.index else 0
            if rec_val > 0:
                ncg_pct_hist.append(ncg_val / rec_val)

        ncg_pct_atual = np.mean(ncg_pct_hist) if ncg_pct_hist else ncg_pct_alvo
        ano_base = anos_proj[0] - 1

        # NCG do último ano histórico
        ncg_ultimo = self._ultimo_valor(ncg_hist)

        ncg_proj = {}
        delta_ncg_proj = {}
        ncg_anterior = ncg_ultimo

        for ano in anos_proj:
            pct = self._convergir(ncg_pct_atual, ncg_pct_alvo, 5, ano_base, ano)
            receita = receita_proj.get(ano, 0)
            ncg_ano = receita * pct
            ncg_proj[ano] = round(ncg_ano, 3)
            delta_ncg_proj[ano] = round(-(ncg_ano - ncg_anterior), 3)  # negativo = consumo
            ncg_anterior = ncg_ano

        logger.info(f"  NCG/Receita: {ncg_pct_atual:.1%} → {ncg_pct_alvo:.1%}")
        return ncg_proj, delta_ncg_proj

    # ── Resultado Financeiro ─────────────────────────────────────────────────

    def projetar_resultado_financeiro(self, divida_liq_hist: pd.Series,
                                       selic_proj: dict,
                                       receita_proj: dict[int, float],
                                       anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta resultado financeiro = -Dívida Líquida × custo da dívida.
        Custo da dívida = Selic + spread.
        """
        spread = self.prem.get("custo_divida_spread",
                               self.cfg.get("CUSTO_DIVIDA_SPREAD", 0.02))
        dl_ultimo = self._ultimo_valor(divida_liq_hist)
        g_dl = 0.05  # dívida cresce moderadamente

        resultado = {}
        dl = dl_ultimo

        for ano in anos_proj:
            selic = selic_proj.get(ano, 0.10)
            custo = selic + spread
            desp_fin = -abs(dl) * custo if dl > 0 else abs(dl) * 0.02  # caixa líquido rende pouco
            resultado[ano] = round(desp_fin, 3)
            dl = dl * (1 + g_dl)  # simplificação

        return resultado

    # ── IR / CSLL ────────────────────────────────────────────────────────────

    def projetar_ir_geral(self, aliquota_hist: pd.Series,
                           ebt_proj: dict[int, float],
                           anos_proj: list[int]) -> dict[int, float]:
        """
        Projeta IR/CSLL sobre o resultado antes do IR.
        """
        validos = aliquota_hist.dropna().replace(0, np.nan).dropna()
        validos_clamp = validos[(validos >= 0.10) & (validos <= 0.50)]
        aliquota = float(validos_clamp.median()) if not validos_clamp.empty else 0.34
        aliquota = max(0.15, min(aliquota, 0.40))

        resultado = {}
        for ano in anos_proj:
            ebt = ebt_proj.get(ano, 0)
            if ebt > 0:
                resultado[ano] = round(-ebt * aliquota, 3)
            else:
                resultado[ano] = 0  # prejuízo: sem IR

        logger.info(f"  Alíquota efetiva: {aliquota:.1%}")
        return resultado

    # ── Orquestrador ─────────────────────────────────────────────────────────

    def projetar_tudo(self, dados_norm: dict,
                       macro_proj: dict,
                       anos_proj: list[int]) -> dict:
        """
        Roda todas as projeções para empresas não-financeiras.

        Returns:
            dict com todas as linhas projetadas + fcff
        """
        dre = dados_norm.get("dre", pd.DataFrame())
        bp  = dados_norm.get("balanco", pd.DataFrame())
        ind = dados_norm.get("indicadores", pd.DataFrame())
        dfc = dados_norm.get("dfc", pd.DataFrame())

        def serie(df, linha):
            if df is None or df.empty:
                return pd.Series(dtype=float)
            if linha in df.index:
                s = df.loc[linha]
                s.index = s.index.astype(int)
                return s
            if linha in df.columns:
                s = df[linha]
                s.index = s.index.astype(int)
                return s
            return pd.Series(dtype=float)

        selic_proj = macro_proj.get("projecao", {}).get("di", {})
        ipca_proj  = macro_proj.get("projecao", {}).get("ipca", {})

        logger.info("\n=== Projeções (não-financeira / FCFF) ===")

        # 1. Receita
        receita_proj = self.projetar_receita(serie(dre, "receita_liquida"), anos_proj)

        # 2. EBITDA
        ebitda_proj, margem_proj = self.projetar_ebitda(
            receita_proj, serie(ind, "margem_ebitda"), anos_proj)

        # 3. D&A
        da_proj = self.projetar_da(
            serie(dre, "depreciacao_amortizacao"),
            serie(dre, "receita_liquida"),
            receita_proj, anos_proj)

        # 4. EBIT
        ebit_proj = {a: round(ebitda_proj[a] - da_proj[a], 3) for a in anos_proj}

        # 5. Custo mercadorias / lucro bruto (para template)
        margem_bruta_hist = serie(ind, "margem_bruta")
        mb_atual = self._ultimo_valor(margem_bruta_hist)
        mb_alvo = self.prem.get("margem_bruta_alvo", mb_atual or 0.40)
        lucro_bruto_proj = {a: round(receita_proj[a] * mb_alvo, 3) for a in anos_proj}
        cpv_proj = {a: round(receita_proj[a] - lucro_bruto_proj[a], 3) for a in anos_proj}

        # 6. CAPEX
        capex_proj = self.projetar_capex(
            receita_proj,
            serie(dfc, "capex_total") if not dfc.empty else serie(ind, "capex_mm"),
            serie(dre, "receita_liquida"),
            anos_proj)

        # 7. NCG
        ncg_proj, delta_ncg_proj = self.projetar_ncg(
            receita_proj,
            serie(bp, "capital_de_giro"),
            serie(dre, "receita_liquida"),
            anos_proj)

        # 8. NOPAT e FCFF
        aliq_hist = serie(ind, "aliquota_ir")
        aliq_validos = aliq_hist.dropna().replace(0, np.nan).dropna()
        aliq_validos = aliq_validos[(aliq_validos >= 0.10) & (aliq_validos <= 0.50)]
        aliquota_ef = float(aliq_validos.median()) if not aliq_validos.empty else 0.34

        nopat_proj = {a: round(ebit_proj[a] * (1 - aliquota_ef), 3) for a in anos_proj}

        fcff_proj = {}
        for a in anos_proj:
            fcff = nopat_proj[a] + da_proj[a] + capex_proj[a] + delta_ncg_proj[a]
            fcff_proj[a] = round(fcff, 3)

        # 9. Resultado financeiro (para template — não afeta FCFF)
        res_fin_proj = self.projetar_resultado_financeiro(
            serie(bp, "divida_liquida"), selic_proj, receita_proj, anos_proj)

        # 10. EBT
        ebt_proj = {a: round(ebit_proj[a] + res_fin_proj[a], 3) for a in anos_proj}

        # 11. IR
        ir_proj = self.projetar_ir_geral(aliq_hist, ebt_proj, anos_proj)

        # 12. Lucro líquido
        lucro_proj = {a: round(ebt_proj[a] + ir_proj[a], 3) for a in anos_proj}

        # 13. Payout / dividendos (informativo)
        payout = self.prem.get("payout", 0.40)
        dividendos_proj = {a: round(max(lucro_proj[a], 0) * payout, 3) for a in anos_proj}

        logger.info("Projeções concluídas (FCFF). Resumo:")
        logger.info(f"{'Ano':>6} {'Receita':>12} {'EBITDA':>10} {'Mg%':>6} "
                    f"{'NOPAT':>10} {'FCFF':>10}")
        for a in anos_proj[:5]:
            logger.info(f"{a:>6} {receita_proj[a]:>12,.0f} "
                        f"{ebitda_proj[a]:>10,.0f} "
                        f"{margem_proj[a]:>6.1%} "
                        f"{nopat_proj[a]:>10,.0f} "
                        f"{fcff_proj[a]:>10,.0f}")

        return {
            "receita_liquida":          receita_proj,
            "custo_mercadorias":        cpv_proj,
            "lucro_bruto":              lucro_bruto_proj,
            "ebitda":                   ebitda_proj,
            "margem_ebitda_proj":       margem_proj,
            "depreciacao_amortizacao":  da_proj,
            "ebit":                     ebit_proj,
            "resultado_financeiro":     res_fin_proj,
            "resultado_antes_ir":       ebt_proj,
            "ir_csll":                  ir_proj,
            "lucro_liquido":            lucro_proj,
            "capex":                    capex_proj,
            "ncg":                      ncg_proj,
            "delta_ncg":                delta_ncg_proj,
            "nopat":                    nopat_proj,
            "fcff":                     fcff_proj,
            "dividendos":               dividendos_proj,
            "aliquota_efetiva":         aliquota_ef,
        }
