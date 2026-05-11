"""
Módulo 05 — Motor de Valuation
Calcula o valor justo da empresa pelo método DCF (FCFE).

Métodos:
  1. DCF — Fluxo de Caixa ao Acionista descontado pelo Ke
  2. Perpetuidade de Gordon — FCFE_n × (1+g) / (Ke - g)
  3. TIR — taxa interna de retorno implícita pelo preço atual
  4. Múltiplos — P/L e P/VP comparativos
  5. Preço Teto — preço que remunera exatamente o Ke
"""

import logging
import math
from typing import Optional
import numpy as np

logger = logging.getLogger("pipeline.valuation")


class MotorValuation:
    """Calcula valuation bancário pelo método DCF/FCFE."""

    def __init__(self, config: dict):
        self.cfg = config

    # ── Ke e fatores de desconto ──────────────────────────────────────────────

    def calcular_ke_por_ano(self, di_proj: dict[int, float],
                             cds_proj: dict[int, float],
                             inflacao_proj: dict[int, float],
                             beta: float = None,
                             erp: float = None) -> dict[int, float]:
        """CAPM adaptado: Ke = (DI - CDS - Infl) + β × ERP"""
        beta = beta or self.cfg.get("BETA_UTILIZADO", 0.85)
        erp  = erp  or self.cfg.get("PREMIO_RISCO",   0.065)

        resultado = {}
        for ano in sorted(di_proj.keys()):
            di    = di_proj.get(ano, 0.10)
            cds   = cds_proj.get(ano, 0.004)
            infl  = inflacao_proj.get(ano, 0.045)
            rf    = di - cds - infl
            ke    = rf + beta * erp
            resultado[ano] = round(max(ke, 0.08), 5)   # floor 8%

        return resultado

    def calcular_fatores_desconto(self, ke_por_ano: dict[int, float]) -> dict[int, float]:
        """Fator acumulado: Π(1 + Ke_t) para cada ano."""
        fatores   = {}
        acumulado = 1.0
        for ano in sorted(ke_por_ano.keys()):
            ke = ke_por_ano[ano]
            acumulado *= (1 + ke)
            fatores[ano] = round(acumulado, 6)
        return fatores

    # ── DCF ───────────────────────────────────────────────────────────────────

    def descontar_fcfe(self, fcfe_proj: dict[int, float],
                        fatores: dict[int, float]) -> dict[int, float]:
        """Desconta cada FCFE pelo fator acumulado correspondente."""
        resultado = {}
        for ano, fcfe in fcfe_proj.items():
            fator = fatores.get(ano, 1.0)
            resultado[ano] = round(fcfe / fator, 3) if fator else 0.0
        return resultado

    def calcular_vp_fcfe(self, fcfe_descontado: dict[int, float]) -> float:
        """Soma dos FCFEs descontados (fase explícita)."""
        return round(sum(fcfe_descontado.values()), 3)

    # ── Perpetuidade ─────────────────────────────────────────────────────────

    def calcular_perpetuidade(self, fcfe_ultimo: float,
                               ke_ultimo: float,
                               g: float = None) -> float:
        """
        Gordon Growth Model: VP_Perp = FCFE_n × (1+g) / (Ke - g)
        Retorna o valor terminal (não descontado ainda).
        """
        g = g or self.cfg.get("G_PERPETUIDADE", 0.070)
        if ke_ultimo <= g:
            logger.warning(f"Ke ({ke_ultimo:.3%}) ≤ g ({g:.3%}) — ajustando g")
            g = ke_ultimo - 0.01
        perp = fcfe_ultimo * (1 + g) / (ke_ultimo - g)
        return round(perp, 3)

    def descontar_perpetuidade(self, perpetuidade: float,
                                fator_ultimo: float) -> float:
        """VP da perpetuidade = Perpetuidade / Fator_n"""
        return round(perpetuidade / fator_ultimo, 3) if fator_ultimo else 0.0

    # ── Equity e preço ────────────────────────────────────────────────────────

    def calcular_equity(self, vp_fcfe: float, vp_perpetuidade: float) -> float:
        """Valor do Equity = VP_FCFE + VP_Perpetuidade"""
        return round(vp_fcfe + vp_perpetuidade, 3)

    def calcular_preco_justo(self, equity_mm: float,
                              acoes_on_mil: float,
                              acoes_pn_mil: float,
                              relacao_pn_on: float = None) -> dict:
        """
        Converte equity (R$ MM) em preço por ação.
        equity_mm é o valor total do equity (não alocado entre ON e PN).

        Args:
            equity_mm:      Valor do equity em R$ MM
            acoes_on_mil:   Ações ON em mil (ex-treasury)
            acoes_pn_mil:   Ações PN em mil (ex-treasury)
            relacao_pn_on:  Relação de paridade PN/ON
        """
        relacao   = relacao_pn_on or self.cfg.get("RELACAO_PN_ON", 1.10)
        try:
            relacao = float(relacao)
        except (TypeError, ValueError):
            relacao = 1.0
        relacao = relacao if relacao > 0 else 1.0
        acoes_on  = acoes_on_mil / 1_000   # converter para unidades MM
        acoes_pn  = acoes_pn_mil / 1_000

        # Equity total em R$ 1 (não MM)
        equity_total = equity_mm * 1_000_000   # de MM para R$ 1

        # Total de ações ponderado: ON + PN × relação
        total_on_equiv = acoes_on + acoes_pn * relacao

        if total_on_equiv <= 0:
            return {"preco_on": 0, "preco_pn": 0}

        preco_on = equity_total / (total_on_equiv * 1_000)   # em R$
        preco_pn = preco_on * relacao

        return {
            "preco_on": round(preco_on, 2),
            "preco_pn": round(preco_pn, 2),
        }

    # ── TIR ───────────────────────────────────────────────────────────────────

    def calcular_tir(self, cotacao_atual: float,
                      fcfe_proj: dict[int, float],
                      fcfe_descontado: dict[int, float],
                      perpetuidade: float,
                      fator_ultimo: float) -> float:
        """
        Calcula a TIR implícita dado o preço atual.
        Usa método de Newton-Raphson ou bisseção.

        Returns:
            TIR como decimal (ex: 0.15 = 15%)
        """
        if cotacao_atual <= 0:
            return 0.0

        # Fluxos: -preço_on no tempo 0, FCFEs nos anos seguintes + terminal
        anos      = sorted(fcfe_proj.keys())
        n         = len(anos)
        ano_base  = min(anos) - 1

        def vpl_dado_tir(tir: float) -> float:
            if tir <= -1:
                return float("inf")
            vpl     = -cotacao_atual
            fator_a = 1.0
            for i, ano in enumerate(anos, 1):
                fator_a *= (1 + tir)
                fcfe = fcfe_proj[ano]
                vpl += fcfe / fator_a

            # Terminal
            if fator_a > 0:
                g  = self.cfg.get("G_PERPETUIDADE", 0.070)
                ke = tir
                if ke > g:
                    fcfe_ultimo = fcfe_proj[anos[-1]]
                    perp        = fcfe_ultimo * (1 + g) / (ke - g)
                    vpl        += perp / fator_a

            return vpl

        # Bisseção
        lo, hi = 0.01, 0.50
        for _ in range(60):
            mid = (lo + hi) / 2
            vpl = vpl_dado_tir(mid)
            if abs(vpl) < 0.01:
                return round(mid, 5)
            if vpl > 0:
                lo = mid
            else:
                hi = mid
            if hi - lo < 1e-6:
                break

        tir = (lo + hi) / 2
        logger.info(f"  TIR calculada: {tir:.4%}")
        return round(tir, 5)

    # ── Preço Teto ────────────────────────────────────────────────────────────

    def calcular_preco_teto(self, fcfe_proj: dict[int, float],
                             ke_base: dict[int, float],
                             g: float = None) -> float:
        """
        Preço teto = preço que gera retorno exatamente igual ao Ke.
        É simplesmente o preço justo calculado pelo DCF com o Ke-base.
        (Alias semântico — confirma a lógica dos modelos VAROS.)
        """
        # O preço teto é o próprio VP dos FCFEs descontados pelo Ke-base
        # Retorna o equity por ação ON — será convertido pelo escritor
        anos    = sorted(fcfe_proj.keys())
        vpl     = 0.0
        fator_a = 1.0
        ke_list = [ke_base.get(a, 0.15) for a in anos]

        for i, (ano, ke) in enumerate(zip(anos, ke_list)):
            fator_a *= (1 + ke)
            fcfe = fcfe_proj.get(ano, 0)
            vpl += fcfe / fator_a

        g    = g or self.cfg.get("G_PERPETUIDADE", 0.070)
        ke_u = ke_list[-1] if ke_list else 0.15
        if ke_u > g:
            fcfe_u = fcfe_proj.get(anos[-1], 0)
            perp   = fcfe_u * (1 + g) / (ke_u - g)
            vpl   += perp / fator_a

        return round(vpl, 3)   # R$ MM

    # ── Valuation completo ────────────────────────────────────────────────────

    def calcular_tudo(self, fcfe_proj: dict[int, float],
                       ke_proj: dict[int, float],
                       cotacao_on: float,
                       cotacao_pn: float,
                       acoes_on_mil: float,
                       acoes_pn_mil: float,
                       g: float = None) -> dict:
        """
        Executa o valuation completo e retorna um dicionário com todos
        os resultados prontos para o template.
        """
        g = g or self.cfg.get("G_PERPETUIDADE", 0.070)

        anos    = sorted(fcfe_proj.keys())
        ke_list = {a: ke_proj.get(a, 0.15) for a in anos}

        # 1. Fatores de desconto
        fatores = self.calcular_fatores_desconto(ke_list)

        # 2. FCFEs descontados
        fcfe_desc = self.descontar_fcfe(fcfe_proj, fatores)
        vp_fcfe   = self.calcular_vp_fcfe(fcfe_desc)

        # 3. Perpetuidade
        ke_ult    = ke_list.get(anos[-1], 0.15)
        fcfe_ult  = fcfe_proj.get(anos[-1], 0)
        fator_ult = fatores.get(anos[-1], 1.0)

        perpetuidade    = self.calcular_perpetuidade(fcfe_ult, ke_ult, g)
        vp_perpetuidade = self.descontar_perpetuidade(perpetuidade, fator_ult)

        # 4. Equity
        equity_mm = self.calcular_equity(vp_fcfe, vp_perpetuidade)

        # 5. Preços
        relacao = self.cfg.get("RELACAO_PN_ON", 1.10)
        precos    = self.calcular_preco_justo(
            equity_mm, acoes_on_mil, acoes_pn_mil, relacao)
        preco_on  = precos["preco_on"]
        preco_pn  = precos["preco_pn"]

        # 6. Upside
        upside_on = (preco_on / cotacao_on - 1) if cotacao_on else 0
        upside_pn = (preco_pn / cotacao_pn - 1) if cotacao_pn else 0

        # 7. TIR
        tir_on = self.calcular_tir(cotacao_on, fcfe_proj, fcfe_desc,
                                    perpetuidade, fator_ult)
        tir_pn = self.calcular_tir(cotacao_pn, fcfe_proj, fcfe_desc,
                                    perpetuidade, fator_ult)

        # 8. Preço Teto
        equity_teto    = self.calcular_preco_teto(fcfe_proj, ke_list, g)
        precos_teto    = self.calcular_preco_justo(
            equity_teto, acoes_on_mil, acoes_pn_mil, relacao)
        preco_teto_on  = precos_teto["preco_on"]
        preco_teto_pn  = precos_teto["preco_pn"]

        logger.info(f"\n{'='*50}")
        logger.info(f"VALUATION COMPLETO — {self.cfg.get('TICKER_B3','')}")
        logger.info(f"  VP FCFE (10a):     R$ {vp_fcfe:>12,.0f} MM")
        logger.info(f"  Valor Perp. (VP):  R$ {vp_perpetuidade:>12,.0f} MM")
        logger.info(f"  VALOR DO EQUITY:   R$ {equity_mm:>12,.0f} MM")
        logger.info(f"  Preço Justo ON:    R$ {preco_on:>8.2f}")
        logger.info(f"  Preço Justo PN:    R$ {preco_pn:>8.2f}")
        logger.info(f"  Cotação ON:        R$ {cotacao_on:>8.2f}")
        logger.info(f"  Upside ON:            {upside_on:>8.1%}")
        logger.info(f"  TIR (ON):             {tir_on:>8.1%}")
        logger.info(f"  Preço Teto ON:     R$ {preco_teto_on:>8.2f}")

        return {
            "vp_fcfe":          vp_fcfe,
            "vp_perpetuidade":  vp_perpetuidade,
            "equity_mm":        equity_mm,
            "preco_justo_on":   preco_on,
            "preco_justo_pn":   preco_pn,
            "upside_on":        round(upside_on, 4),
            "upside_pn":        round(upside_pn, 4),
            "tir_on":           tir_on,
            "tir_pn":           tir_pn,
            "preco_teto_on":    preco_teto_on,
            "preco_teto_pn":    preco_teto_pn,
            "fcfe_descontado":  fcfe_desc,
            "fatores_desconto": fatores,
            "perpetuidade":     perpetuidade,
            "ke_por_ano":       ke_list,
            "g_perpetuidade":   g,
        }
