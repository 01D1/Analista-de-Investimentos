"""
Módulo 05 — Motor de Valuation
Calcula o valor justo da empresa pelo método DCF.

Dois modos:
  A) FCFE / Ke — bancos (calcular_tudo)
  B) FCFF / WACC — empresas não-financeiras (calcular_tudo_fcff)

Métodos compartilhados:
  1. DCF — fluxo de caixa descontado
  2. Perpetuidade de Gordon — FCF_n × (1+g) / (taxa - g)
  3. TIR — taxa interna de retorno implícita
  4. Preço Teto — preço que remunera exatamente a taxa requerida
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
        g = g or self.cfg.get("G_PERPETUIDADE", 0.055)
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
        # acoes_on_mil e acoes_pn_mil estão em MIL unidades
        # equity_mm está em R$ MM
        equity_total   = equity_mm * 1_000_000     # R$ MM → R$ 1
        acoes_on_u     = acoes_on_mil * 1_000       # mil → unidades
        acoes_pn_u     = acoes_pn_mil * 1_000       # mil → unidades
        total_on_equiv = acoes_on_u + acoes_pn_u / relacao

        if total_on_equiv <= 0:
            return {"preco_on": 0, "preco_pn": 0}

        preco_on = equity_total / total_on_equiv   # R$ por ação
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
                      fator_ultimo: float,
                      total_on_equiv_mil: float = None) -> float:
        """
        Calcula a TIR implícita dado o preço atual.
        Usa bisseção de 100 iterações.

        Args:
            cotacao_atual:       preço atual por ação (R$)
            fcfe_proj:           FCFE projetado em R$ MM (total, não por ação)
            total_on_equiv_mil:  total de ações ON-equivalentes em MIL unidades
                                 (usado para converter FCFE MM → por ação)

        Returns:
            TIR como decimal (ex: 0.15 = 15%)
        """
        if cotacao_atual <= 0:
            return 0.0

        # Converter FCFE MM → FCFE por ação ON-equivalente
        # FCFE_MM × 1e6 / (total_on_equiv_mil × 1e3)  =  FCFE_MM × 1e3 / total_on_equiv_mil
        if total_on_equiv_mil and total_on_equiv_mil > 0:
            escala = 1_000.0 / total_on_equiv_mil       # MM → R$ por ação
        else:
            # Fallback: inferir escala a partir do equity já calculado
            # (chamador deve preferir passar total_on_equiv_mil)
            escala = 1.0

        anos = sorted(fcfe_proj.keys())
        g    = self.cfg.get("G_PERPETUIDADE", 0.055)

        def vpl_dado_tir(tir: float) -> float:
            if tir <= -1:
                return float("inf")
            vpl     = -cotacao_atual
            fator_a = 1.0
            for ano in anos:
                fator_a *= (1 + tir)
                fcfe_pa = fcfe_proj[ano] * escala   # R$ por ação
                vpl    += fcfe_pa / fator_a

            # Terminal (Gordon Growth)
            if fator_a > 0 and tir > g:
                fcfe_ult_pa = fcfe_proj[anos[-1]] * escala
                perp_pa     = fcfe_ult_pa * (1 + g) / (tir - g)
                vpl        += perp_pa / fator_a

            return vpl

        # Bisseção entre g+δ e 1.50
        # Começamos logo acima de g para garantir que a perpetuidade de Gordon seja válida
        # (ke-g > 0). Abaixo de g, o terminal seria negativo/indefinido, portanto não
        # há cruzamento de sinal válido abaixo de g.
        delta = 0.005   # pequena margem acima de g
        lo = g + delta
        hi = 1.50

        vpl_lo = vpl_dado_tir(lo)
        vpl_hi = vpl_dado_tir(hi)

        if vpl_lo <= 0:
            # Mesmo logo acima de g o VPL é negativo → cotação acima do valor intrínseco
            # TIR existe mas abaixo do nível de crescimento; reportar como floor
            logger.warning(f"TIR < g ({g:.1%}) — cotação acima do valor intrínseco (DCF)")
            return round(lo, 5)

        if vpl_hi > 0:
            logger.warning("TIR > 150% — valor intrínseco muito acima do preço de mercado")
            return round(hi, 5)

        for _ in range(120):
            mid = (lo + hi) / 2
            vpl = vpl_dado_tir(mid)
            if abs(vpl) < 0.001:
                return round(mid, 5)
            if vpl > 0:
                lo = mid
            else:
                hi = mid
            if hi - lo < 1e-7:
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

        g    = g or self.cfg.get("G_PERPETUIDADE", 0.055)
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
        g = g or self.cfg.get("G_PERPETUIDADE", 0.055)

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
        relacao   = self.cfg.get("RELACAO_PN_ON", 1.10)
        precos    = self.calcular_preco_justo(
            equity_mm, acoes_on_mil, acoes_pn_mil, relacao)
        preco_on  = precos["preco_on"]
        preco_pn  = precos["preco_pn"]

        # Denominador em MIL ações ON-equivalentes (mesmo que calcular_preco_justo)
        total_on_equiv_mil = (acoes_on_mil + acoes_pn_mil / relacao)

        # 6. Upside
        upside_on = (preco_on / cotacao_on - 1) if cotacao_on else 0
        upside_pn = (preco_pn / cotacao_pn - 1) if cotacao_pn else 0

        # 7. TIR — FCFE está em R$ MM; cotação está em R$ por ação
        #    escala: FCFE_MM × (1000 / total_on_equiv_mil) = R$ por ação ON-equiv
        tir_on = self.calcular_tir(cotacao_on, fcfe_proj, fcfe_desc,
                                    perpetuidade, fator_ult,
                                    total_on_equiv_mil=total_on_equiv_mil)
        # Para TIR da PN, cotação é preco_pn mas o FCFE por ação é o mesmo (ON-equiv)
        # então usamos cotacao_pn diretamente mas mantemos a escala por ON-equiv:
        tir_pn = self.calcular_tir(cotacao_pn, fcfe_proj, fcfe_desc,
                                    perpetuidade, fator_ult,
                                    total_on_equiv_mil=total_on_equiv_mil)

        # 8. Preço Teto
        equity_teto    = self.calcular_preco_teto(fcfe_proj, ke_list, g)
        precos_teto    = self.calcular_preco_justo(
            equity_teto, acoes_on_mil, acoes_pn_mil)
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

    # ═════════════════════════════════════════════════════════════════════════
    # WACC / FCFF — Empresas não-financeiras
    # ═════════════════════════════════════════════════════════════════════════

    def calcular_wacc_por_ano(self, ke_proj: dict[int, float],
                               di_proj: dict[int, float],
                               spread_divida: float = 0.02,
                               aliquota_ir: float = 0.34,
                               pct_equity: float = 0.60) -> dict[int, float]:
        """
        Calcula WACC por ano.

        WACC = Ke × E/(E+D) + Kd × (1-t) × D/(E+D)

        Args:
            ke_proj: custo do equity por ano
            di_proj: taxa DI (base para custo da dívida)
            spread_divida: spread sobre DI para custo da dívida
            aliquota_ir: alíquota de IR/CSLL
            pct_equity: % de equity na estrutura de capital (E / (E+D))
        """
        pct_debt = 1 - pct_equity
        resultado = {}

        for ano in sorted(ke_proj.keys()):
            ke = ke_proj.get(ano, 0.15)
            di = di_proj.get(ano, 0.10)
            kd = di + spread_divida

            wacc = ke * pct_equity + kd * (1 - aliquota_ir) * pct_debt
            resultado[ano] = round(max(wacc, 0.06), 5)  # floor 6%

        return resultado

    def calcular_wacc_dinamico(self, ke_proj: dict[int, float],
                                di_proj: dict[int, float],
                                divida_liq: float,
                                market_cap: float,
                                spread_divida: float = 0.02,
                                aliquota_ir: float = 0.34) -> dict[int, float]:
        """
        WACC com estrutura de capital baseada em valores de mercado.
        """
        ev = market_cap + divida_liq
        if ev <= 0:
            return self.calcular_wacc_por_ano(ke_proj, di_proj, spread_divida, aliquota_ir)

        pct_equity = market_cap / ev
        pct_equity = max(0.20, min(pct_equity, 0.95))  # clamp razoável

        logger.info(f"  Estrutura de capital: E={pct_equity:.0%} | D={1-pct_equity:.0%}")
        return self.calcular_wacc_por_ano(
            ke_proj, di_proj, spread_divida, aliquota_ir, pct_equity)

    def calcular_tudo_fcff(self, fcff_proj: dict[int, float],
                            wacc_proj: dict[int, float],
                            divida_liquida: float,
                            cotacao_on: float,
                            cotacao_pn: float,
                            acoes_on_mil: float,
                            acoes_pn_mil: float,
                            g: float = None) -> dict:
        """
        Valuation completo pelo método FCFF/WACC.

        Enterprise Value = VP_FCFF + VP_Perpetuidade
        Equity = EV - Dívida Líquida

        Returns:
            dict com todos os resultados de valuation
        """
        g = g or self.cfg.get("G_PERPETUIDADE", 0.055)

        anos    = sorted(fcff_proj.keys())
        wacc_map = {a: wacc_proj.get(a, 0.12) for a in anos}

        # 1. Fatores de desconto (usando WACC em vez de Ke)
        fatores = self.calcular_fatores_desconto(wacc_map)

        # 2. FCFFs descontados
        fcff_desc = self.descontar_fcfe(fcff_proj, fatores)  # reutiliza método genérico
        vp_fcff   = self.calcular_vp_fcfe(fcff_desc)

        # 3. Perpetuidade (usando WACC como taxa)
        wacc_ult   = wacc_map.get(anos[-1], 0.12)
        fcff_ult   = fcff_proj.get(anos[-1], 0)
        fator_ult  = fatores.get(anos[-1], 1.0)

        perpetuidade    = self.calcular_perpetuidade(fcff_ult, wacc_ult, g)
        vp_perpetuidade = self.descontar_perpetuidade(perpetuidade, fator_ult)

        # 4. Enterprise Value
        ev_mm = round(vp_fcff + vp_perpetuidade, 3)

        # 5. Equity = EV - Dívida Líquida
        equity_mm = round(ev_mm - divida_liquida, 3)

        # 6. Preços
        relacao   = self.cfg.get("RELACAO_PN_ON", 1.10)
        precos    = self.calcular_preco_justo(
            equity_mm, acoes_on_mil, acoes_pn_mil, relacao)
        preco_on  = precos["preco_on"]
        preco_pn  = precos["preco_pn"]

        total_on_equiv_mil = (acoes_on_mil + acoes_pn_mil / relacao)

        # 7. Upside
        upside_on = (preco_on / cotacao_on - 1) if cotacao_on else 0
        upside_pn = (preco_pn / cotacao_pn - 1) if cotacao_pn else 0

        # 8. TIR (baseada no equity = EV - DL, usando FCFF convertido para por ação)
        # Para TIR precisamos converter FCFF em FCFE-equivalente:
        # FCFE ≈ FCFF - Desp Financeiras × (1-t) ≈ FCFF quando DL é estável
        # Simplificação: usar FCFF direto com escala por ação
        tir_on = self.calcular_tir(cotacao_on, fcff_proj, fcff_desc,
                                    perpetuidade, fator_ult,
                                    total_on_equiv_mil=total_on_equiv_mil)
        tir_pn = self.calcular_tir(cotacao_pn, fcff_proj, fcff_desc,
                                    perpetuidade, fator_ult,
                                    total_on_equiv_mil=total_on_equiv_mil)

        # 9. Preço Teto
        equity_teto   = self.calcular_preco_teto(fcff_proj, wacc_map, g)
        equity_teto   = round(equity_teto - divida_liquida, 3)  # EV → equity
        precos_teto   = self.calcular_preco_justo(
            equity_teto, acoes_on_mil, acoes_pn_mil)
        preco_teto_on = precos_teto["preco_on"]
        preco_teto_pn = precos_teto["preco_pn"]

        logger.info(f"\n{'='*50}")
        _ticker_log = self.cfg.get('_ticker', self.cfg.get('TICKER_B3',''))
        logger.info(f"VALUATION FCFF/WACC — {_ticker_log}")
        logger.info(f"  VP FCFF (10a):     R$ {vp_fcff:>12,.0f} MM")
        logger.info(f"  Valor Perp. (VP):  R$ {vp_perpetuidade:>12,.0f} MM")
        logger.info(f"  ENTERPRISE VALUE:  R$ {ev_mm:>12,.0f} MM")
        logger.info(f"  (-) Dívida Líq.:   R$ {divida_liquida:>12,.0f} MM")
        logger.info(f"  VALOR DO EQUITY:   R$ {equity_mm:>12,.0f} MM")
        logger.info(f"  Preço Justo ON:    R$ {preco_on:>8.2f}")
        logger.info(f"  Preço Justo PN:    R$ {preco_pn:>8.2f}")
        logger.info(f"  Cotação ON:        R$ {cotacao_on:>8.2f}")
        logger.info(f"  Upside ON:            {upside_on:>8.1%}")
        logger.info(f"  TIR (ON):             {tir_on:>8.1%}")
        logger.info(f"  WACC último ano:      {wacc_ult:>8.1%}")

        return {
            "vp_fcff":          vp_fcff,
            "vp_perpetuidade":  vp_perpetuidade,
            "ev_mm":            ev_mm,
            "divida_liquida":   divida_liquida,
            "equity_mm":        equity_mm,
            "acoes_on_mil":     acoes_on_mil,
            "acoes_pn_mil":     acoes_pn_mil,
            "relacao_pn_on":    relacao,
            "preco_justo_on":   preco_on,
            "preco_justo_pn":   preco_pn,
            "upside_on":        round(upside_on, 4),
            "upside_pn":        round(upside_pn, 4),
            "tir_on":           tir_on,
            "tir_pn":           tir_pn,
            "preco_teto_on":    preco_teto_on,
            "preco_teto_pn":    preco_teto_pn,
            "fcff_descontado":  fcff_desc,
            "fatores_desconto": fatores,
            "vp_fcff_por_ano":  fcff_desc,
            "perpetuidade":     perpetuidade,
            "wacc_por_ano":     wacc_map,
            "g_perpetuidade":   g,
            "motor":            "fcff_wacc",
        }
