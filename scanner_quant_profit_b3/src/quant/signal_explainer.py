"""
Signal Explainer — Por que essa oportunidade apareceu?

Transforma o MetaScoreResult em linguagem natural estruturada (PT-BR).
O output é um dict com chaves padronizadas — o LLM usa como input de síntese,
nunca como texto final direto ao usuário.

Exemplo de output:
  {
    "headline": "ITUB4 — Assimetria favorável com fluxo institucional comprador",
    "conviction_tier": "A",
    "signal_direction": "BUY",
    "primary_driver": "fluxo institucional comprador concentrado",
    "supporting_factors": ["IV percentile extremo", "valuation descontado", "macro favorável"],
    "risk_factors": ["risco político moderado", "Selic elevada"],
    "ev_summary": "P(acerto)=58%, payoff=2.1:1, EV=+4.2%",
    "regime_context": "APERTO_MONETÁRIO com tailwind setorial para exportadores",
    "action_hint": "considerar entrada — confirmar liquidez",
  }
"""
from __future__ import annotations

from typing import Any

from .institutional_meta_score import MetaScoreResult


# ---------------------------------------------------------------------------
# Tradução de labels técnicos → linguagem institucional PT-BR
# ---------------------------------------------------------------------------

_TIER_LABELS = {
    "S": "Conviction máxima — sinal raro e convergente",
    "A": "Alta conviction — múltiplos layers alinhados",
    "B": "Conviction moderada — setup em formação",
    "C": "Baixa conviction — aguardar confirmação",
    "D": "Sem conviction — descartar ou monitorar",
}

_SIGNAL_LABELS = {
    # ── Lado comprado ───────────────────────────────────────────────────────
    "BUY":                    "entrada — risco/retorno favorável",
    "WATCH":                  "monitorar — aguardar trigger final",
    "HOLD":                   "manter — sem novo posicionamento",
    # ── Lado vendido / proteção ────────────────────────────────────────────
    "SELL":                   "reduzir exposição — estrutura técnica vendida",
    "MONITORAR_VENDA":        "monitorar saída — fraqueza técnica em desenvolvimento",
    "AVOID":                  "evitar — estrutura frágil sem gatilho",
    "EVITAR":                 "evitar — estrutura frágil sem gatilho",
    # ── Opções / proteção (conceitual — sem ticker de opção) ───────────────
    "PROTEÇÃO":               "proteção recomendada — macro adverso ou resistência",
    "PROTECAO":               "proteção recomendada — macro adverso ou resistência",
    "PUT_OPPORTUNITY":        "avaliar put ou trava de baixa — queda com vol favorável",
    "BEAR_SPREAD_OPPORTUNITY":"avaliar trava de baixa — tendência de baixa com vol controlada",
    "VOLATILITY_WATCH":       "monitorar volatilidade — direcão indefinida, vol elevada",
}

_REGIME_CONTEXT = {
    "APERTO_MONETÁRIO":         "Selic em ciclo restritivo — favorece financeiras e exportadores",
    "CICLO_EXPANSIONISTA":      "Selic em queda — favorece crescimento e consumo doméstico",
    "INFLAÇÃO_ALTA":            "Inflação acima da meta — pressão sobre margens e custo de capital",
    "INFLAÇÃO_CONTROLADA":      "Inflação controlada — ambiente favorável para ativos de risco",
    "DÓLAR_FORTE":              "BRL depreciado — exportadores se beneficiam, importadores pressionados",
    "BRL_FORTE":                "BRL apreciado — favorece empresas com dívida em USD",
    "RISCO_SOBERANO_ELEVADO":   "CDS elevado — prêmio de risco alto, fluxo estrangeiro reduzido",
    "RISCO_SOBERANO_BAIXO":     "CDS controlado — ambiente de risco favorável para B3",
    "RISK_OFF_GLOBAL":          "VIX elevado — apetite global reduzido, saída de emergentes",
    "RISK_ON_GLOBAL":           "VIX baixo — risk-on favorece fluxo para emergentes e B3",
}

_IV_CONTEXT = {
    "COMPRIMIDA": "vol implícita no piso histórico — opções baratas, bom momento para compra de proteção ou calls",
    "NORMAL":     "vol implícita em nível histórico neutro",
    "EXPANDIDA":  "vol implícita elevada — prêmios caros, considerar venda de vol ou spreads",
    "EXTREMA":    "vol implícita em pico extremo — custo de proteção máximo, cautela com compra de opções",
}


# ---------------------------------------------------------------------------
# Gerador de explicação
# ---------------------------------------------------------------------------

def explain_opportunity(
    result: MetaScoreResult,
    ev_result: Any | None = None,
    regime_snapshot: Any | None = None,
    institutional_flow: Any | None = None,
) -> dict[str, Any]:
    """
    Gera estrutura explicativa a partir do MetaScoreResult.

    Retorna dict padronizado para uso como input LLM ou display direto no dashboard.
    """
    tier = result.conviction_tier
    direction = result.signal_direction
    score = result.institutional_meta_score

    # Headline
    drivers = result.top_bullish_factors[:1] if result.top_bullish_factors else ["sinal técnico moderado"]
    headline = f"{result.ticker} — {drivers[0].capitalize()} (tier {tier}, score {score:.0f})"

    # Primary driver — lado vendido tem prioridade bearish
    _bearish_directions = {"SELL", "MONITORAR_VENDA", "PROTEÇÃO", "PROTECAO",
                           "PUT_OPPORTUNITY", "BEAR_SPREAD_OPPORTUNITY", "VOLATILITY_WATCH"}
    if direction in _bearish_directions and result.top_bearish_factors:
        primary_driver = result.top_bearish_factors[0]
    elif result.top_bullish_factors:
        primary_driver = result.top_bullish_factors[0]
    else:
        primary_driver = "sinal técnico"

    # Supporting factors (bullish)
    supporting = result.top_bullish_factors[1:4] if len(result.top_bullish_factors) > 1 else []

    # Risk factors (bearish)
    risks = result.top_bearish_factors[:3]

    # IV context
    iv_regime = result.explainability.get("iv_regime", "NORMAL")
    iv_comment = _IV_CONTEXT.get(iv_regime, "")

    # EV summary
    ev_summary = ""
    if ev_result is not None:
        p = getattr(ev_result, "probability_win", None)
        pr = getattr(ev_result, "payoff_ratio", None)
        ep = getattr(ev_result, "expected_payoff", None)
        kf = getattr(ev_result, "kelly_fraction", None)
        if all(v is not None for v in [p, pr, ep]):
            ev_summary = f"P(acerto)={p:.0%}, payoff={pr:.1f}:1, EV={ep:+.1f}%"
            if kf and kf >= 0.05:
                ev_summary += f", Kelly={kf:.0%}"

    # Regime context
    regime_label = ""
    regime_comment = ""
    if regime_snapshot is not None:
        regime_label = str(getattr(regime_snapshot, "regime_label", ""))
        regime_comment = _REGIME_CONTEXT.get(regime_label, regime_label.replace("_", " ").lower())
        risk_app = str(getattr(regime_snapshot, "risk_appetite", "NEUTRAL"))
        headwind = float(getattr(regime_snapshot, "macro_headwind", 50))
        if headwind >= 70:
            regime_comment += f" — headwind macro elevado ({headwind:.0f}/100)"

    # Institutional flow comment
    flow_comment = ""
    if institutional_flow is not None:
        bias = str(getattr(institutional_flow, "directional_bias", "NEUTRAL"))
        cp = float(getattr(institutional_flow, "call_put_ratio", 1.0))
        conviction = float(getattr(institutional_flow, "flow_conviction_score", 0))
        if conviction >= 60:
            flow_comment = f"fluxo institucional {bias.lower()} (C/P={cp:.1f}, conviction={conviction:.0f})"
        elif conviction >= 35:
            flow_comment = f"fluxo moderado {bias.lower()} (C/P={cp:.1f})"

    # Action hint
    action = _SIGNAL_LABELS.get(direction, direction.lower())

    # Data quality warning
    dq_warning = ""
    if result.data_quality_flag == "UNRELIABLE":
        dq_warning = "DADOS NÃO CONFIÁVEIS — validar manualmente antes de agir"
    elif result.data_quality_flag == "DEGRADED":
        dq_warning = "qualidade de dados degradada — conviction penalizada"

    return {
        "headline": headline,
        "conviction_tier": tier,
        "tier_label": _TIER_LABELS.get(tier, ""),
        "signal_direction": direction,
        "action_hint": action,
        "primary_driver": primary_driver,
        "supporting_factors": supporting,
        "risk_factors": risks,
        "ev_summary": ev_summary,
        "iv_context": iv_comment,
        "regime_context": regime_comment,
        "regime_label": regime_label,
        "flow_comment": flow_comment,
        "institutional_meta_score": score,
        "confidence": result.confidence,
        "data_quality_warning": dq_warning,
        # Scores brutos para LLM usar como contexto
        "raw_scores": {
            "quant": result.quant_score,
            "flow": result.flow_score,
            "volatility": result.volatility_score,
            "macro": result.macro_score,
            "valuation": result.valuation_score,
            "liquidity": result.liquidity_score,
        },
    }


# ---------------------------------------------------------------------------
# Renderização HTML para dashboard Streamlit
# ---------------------------------------------------------------------------

def explain_html(explanation: dict[str, Any]) -> str:
    """Bloco HTML institucional para uso no dashboard via st.markdown(..., unsafe_allow_html=True)."""
    tier = explanation.get("conviction_tier", "C")
    score = float(explanation.get("institutional_meta_score", 0))
    direction = explanation.get("signal_direction", "WATCH")

    tier_colors = {"S": "#22D3EE", "A": "#22C55E", "B": "#F59E0B", "C": "#64748B", "D": "#EF4444"}
    dir_colors  = {
        # Alta (verde)
        "BUY":                    "#22C55E",
        # Neutro (âmbar)
        "WATCH":                  "#F59E0B",
        "HOLD":                   "#64748B",
        # Baixa/venda (vermelho)
        "SELL":                   "#EF4444",
        "MONITORAR_VENDA":        "#F97316",
        "AVOID":                  "#EF4444",
        "EVITAR":                 "#EF4444",
        # Proteção/hedge (azul)
        "PROTEÇÃO":               "#3B82F6",
        "PROTECAO":               "#3B82F6",
        "PUT_OPPORTUNITY":        "#8B5CF6",
        "BEAR_SPREAD_OPPORTUNITY":"#8B5CF6",
        # Volatilidade (âmbar escuro)
        "VOLATILITY_WATCH":       "#D97706",
    }
    tier_color = tier_colors.get(tier, "#64748B")
    dir_color  = dir_colors.get(direction, "#64748B")

    supporting = explanation.get("supporting_factors", [])
    risks = explanation.get("risk_factors", [])

    sup_html = "".join(
        f'<span class="badge-cyan" style="margin:2px 4px 2px 0">{f}</span>'
        for f in supporting
    )
    risk_html = "".join(
        f'<span style="display:inline-block;background:#1C0A0A;border:1px solid #7F1D1D;'
        f'border-radius:4px;padding:2px 8px;font-size:0.62rem;color:#FCA5A5;margin:2px 4px 2px 0">{f}</span>'
        for f in risks
    )

    ev = explanation.get("ev_summary", "")
    regime = explanation.get("regime_context", "")
    flow = explanation.get("flow_comment", "")
    dq_warn = explanation.get("data_quality_warning", "")

    dq_block = (
        f'<div style="background:#1C0A0A;border:1px solid #7F1D1D;border-radius:6px;'
        f'padding:8px 12px;margin-top:10px;font-size:0.7rem;color:#FCA5A5">'
        f'Aviso: {dq_warn}</div>'
    ) if dq_warn else ""

    return f"""
<div class="rm-exec" style="margin-top:12px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div>
      <span style="font-size:0.6rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:1px">
        Explicação Institucional
      </span>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <span style="background:{'#082531'};border:1px solid {tier_color};border-radius:4px;
            padding:2px 10px;font-size:0.72rem;font-weight:800;color:{tier_color}">
        Tier {tier}
      </span>
      <span style="background:{'#111827'};border:1px solid {dir_color};border-radius:4px;
            padding:2px 10px;font-size:0.72rem;font-weight:800;color:{dir_color}">
        {direction}
      </span>
      <span style="font-size:1.1rem;font-weight:900;color:{tier_color};
            font-family:'Sora',system-ui">{score:.0f}</span>
    </div>
  </div>

  <div style="font-size:0.82rem;font-weight:700;color:#E2E8F0;margin-bottom:8px">
    {explanation.get("primary_driver", "").capitalize()}
  </div>

  {f'<div style="margin-bottom:8px">{sup_html}</div>' if sup_html else ""}
  {f'<div style="margin-bottom:8px">{risk_html}</div>' if risk_html else ""}

  <div style="display:flex;flex-direction:column;gap:4px;font-size:0.72rem;color:#64748B">
    {f'<span>EV: <strong style="color:#CBD5E1">{ev}</strong></span>' if ev else ""}
    {f'<span>Regime: <strong style="color:#CBD5E1">{regime}</strong></span>' if regime else ""}
    {f'<span>Fluxo: <strong style="color:#CBD5E1">{flow}</strong></span>' if flow else ""}
  </div>
  {dq_block}
</div>
"""
