"""Radar de Oportunidades — Home Operacional.

Mostra as melhores oportunidades identificadas pelo motor quantitativo:
  - Score, direção, tier de convicção
  - Sinal técnico e sinal quant
  - Regime macro de fundo
  - Próxima ação sugerida (derivada dos sinais, sem LLM)
  - Diagnóstico honesto de quais dados ainda faltam para classificar
    um sinal como oportunidade acionável completa.

Regras:
  - Nenhum cálculo novo
  - Nenhuma escrita no banco
  - Nenhum mock — empty_state honesto quando não há dados
  - Nenhuma referência a nomes de milestones, fontes internas ou caminhos
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import section_title, empty_state, status_chip, alert_block, kpi_card
from src.dashboard.data import get_opportunities

try:
    from src.quant.market_regime_engine import detect_regime
    _HAS_REGIME = True
except Exception:
    _HAS_REGIME = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _proxima_acao(direction: str, tier: str, score: int) -> tuple[str, str]:
    """Deriva próxima ação e variante de cor a partir dos sinais disponíveis."""
    d = direction.upper()
    t = tier.upper()
    if d == "BUY" and t in ("S", "A"):
        return "Montar tese", "approved"
    if d == "BUY" and t in ("B",):
        return "Estudar", "monitor"
    if d == "WATCH":
        return "Aguardar gatilho", "monitor"
    if d == "HOLD":
        return "Monitorar", "paper"
    if d == "SELL":
        return "Descartar", "blocked"
    return "Monitorar", "paper"


def _tipo_ativo(signal_type: str) -> str:
    """Classifica tipo de ativo a partir do signal_type."""
    s = str(signal_type or "").upper()
    if "OPTION" in s or "OPCAO" in s or "OPCOES" in s:
        return "Opção"
    if "MACRO" in s:
        return "Macro"
    if "INTEGRATED" in s or "QUANT" in s or "TECHNICAL" in s:
        return "Ação"
    return "Ação"


def _score_color(score: int) -> str:
    if score >= 70:
        return "var(--pos-500)"
    if score >= 40:
        return "var(--warn-500)"
    return "var(--neg-500)"


def _tier_badge(tier: str, direction: str) -> str:
    tier = tier.upper()
    dir_colors = {
        "BUY":   ("var(--pos-tint)", "var(--pos-500)", "var(--pos-border)"),
        "WATCH": ("var(--warn-tint)", "var(--warn-500)", "var(--warn-border)"),
        "HOLD":  ("rgba(100,116,139,0.1)", "var(--fg-5)", "rgba(100,116,139,0.2)"),
        "SELL":  ("var(--neg-tint)", "var(--neg-500)", "var(--neg-border)"),
    }
    bg, fg, border = dir_colors.get(direction.upper(), dir_colors["HOLD"])
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'padding:2px 8px;border-radius:99px;border:1px solid {border};'
        f'background:{bg};font-size:.62rem;font-weight:800;color:{fg};">'
        f'Tier {tier}&nbsp;·&nbsp;{direction}</span>'
    )


def _action_chip(label: str, variant: str) -> str:
    colors = {
        "approved": ("var(--pos-tint)", "var(--pos-500)"),
        "monitor":  ("var(--warn-tint)", "var(--warn-500)"),
        "paper":    ("rgba(100,116,139,0.1)", "var(--fg-4)"),
        "blocked":  ("var(--neg-tint)", "var(--neg-500)"),
    }
    bg, fg = colors.get(variant, colors["paper"])
    return (
        f'<span style="padding:3px 10px;border-radius:99px;background:{bg};'
        f'color:{fg};font-size:.65rem;font-weight:700;">{label}</span>'
    )


def _regime_header(snapshot) -> None:
    """Renderiza banner compacto de regime macro."""
    if snapshot is None:
        return
    label     = str(getattr(snapshot, "regime_label", "—")).replace("_", " ")
    tailwind  = float(getattr(snapshot, "macro_tailwind", 50))
    risk_app  = str(getattr(snapshot, "risk_appetite", "NEUTRAL")).upper()

    if risk_app == "RISK_ON":
        chip = status_chip("APPROVED_FOR_STUDY", label="RISK ON")
        bar_color = "var(--pos-500)"
    elif risk_app == "RISK_OFF":
        chip = status_chip("BLOCKED", label="RISK OFF")
        bar_color = "var(--neg-500)"
    else:
        chip = status_chip("MONITOR_ONLY", label="NEUTRO")
        bar_color = "var(--warn-500)"

    st.markdown(f"""
    <div class="panel" style="padding:10px 16px;margin-bottom:18px;
         display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
      <span style="font-size:.6rem;font-weight:700;color:var(--fg-6);
                   text-transform:uppercase;letter-spacing:.8px;">Regime Macro</span>
      <span style="font-family:var(--font-mono);font-size:.8rem;font-weight:800;
                   color:var(--fg-1);">{label}</span>
      {chip}
      <div style="flex:1;min-width:80px;background:var(--bg-0);
                  border-radius:3px;height:4px;overflow:hidden;">
        <div style="width:{int(tailwind)}%;height:4px;
                    background:{bar_color};border-radius:3px;"></div>
      </div>
      <span style="font-family:var(--font-mono);font-size:.62rem;
                   color:var(--fg-5);">Tailwind {tailwind:.0f}</span>
    </div>
    """, unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="page-header">'
        '<div class="page-header-title">Radar de Oportunidades</div>'
        '<div class="page-header-sub">'
        'Sinais de entrada ranqueados por convicção — ações, opções e derivativos B3'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Regime macro ──────────────────────────────────────────────────────────
    if _HAS_REGIME:
        try:
            snap = detect_regime()
            _regime_header(snap)
        except Exception:
            snap = None

    # ── Carregar oportunidades ────────────────────────────────────────────────
    opps = get_opportunities()

    # ── KPIs rápidos ─────────────────────────────────────────────────────────
    total = len(opps)
    buys  = sum(1 for o in opps if o.get("signal_direction") == "BUY")
    watch = sum(1 for o in opps if o.get("signal_direction") == "WATCH")
    high  = sum(1 for o in opps if int(float(o.get("conviction_score") or 0)) >= 70)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("SINAIS ATIVOS", str(total), color="cyan")
    with c2:
        kpi_card("BUY / COMPRAR", str(buys), color="green")
    with c3:
        kpi_card("AGUARDAR", str(watch), color="amber")
    with c4:
        kpi_card("ALTA CONVICÇÃO", str(high), color="violet")

    if not opps:
        st.markdown("<br>", unsafe_allow_html=True)
        empty_state(
            "Nenhum sinal identificado para o período atual.\n"
            "O motor quantitativo precisa de dados de preço recentes para gerar sinais.",
        )
        _render_diagnostic()
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    cf1, cf2, cf3 = st.columns([1, 1, 2])
    with cf1:
        min_score = st.slider("Score mínimo", 0, 100, 0, 5, key="ro_score")
    with cf2:
        dirs_all = ["BUY", "WATCH", "HOLD", "SELL"]
        sel_dirs = st.multiselect("Direção", dirs_all, default=["BUY", "WATCH"], key="ro_dirs")
    with cf3:
        tiers_all = ["S", "A", "B", "C", "D"]
        sel_tiers = st.multiselect("Tier", tiers_all, default=tiers_all, key="ro_tiers")

    filtered = [
        o for o in opps
        if int(float(o.get("conviction_score") or 0)) >= min_score
        and (not sel_dirs or o.get("signal_direction") in sel_dirs)
        and (not sel_tiers or o.get("conviction_tier") in sel_tiers)
    ]
    filtered.sort(
        key=lambda o: int(float(o.get("conviction_score") or 0)),
        reverse=True,
    )

    section_title(
        f"{len(filtered)} sinal(is) ativo(s) — score ≥ {min_score}",
        icon="",
    )

    if not filtered:
        empty_state(f"Nenhum sinal com score ≥ {min_score} e direção/tier selecionados.")
        return

    # ── Tabela de oportunidades ───────────────────────────────────────────────
    for opp in filtered:
        ticker    = opp.get("ticker", "—")
        score     = int(float(opp.get("conviction_score") or 0))
        direction = opp.get("signal_direction", "HOLD")
        tier      = opp.get("conviction_tier", "D")
        tech      = opp.get("technical_score_final")
        quant_s   = opp.get("quant_score")
        sig_type  = opp.get("signal_type", "")
        desc      = opp.get("description", "")

        tipo         = _tipo_ativo(sig_type)
        acao_label, acao_variant = _proxima_acao(direction, tier, score)
        tier_html    = _tier_badge(tier, direction)
        acao_html    = _action_chip(acao_label, acao_variant)
        score_color  = _score_color(score)

        tech_str  = f"{tech:.1f}" if tech is not None else "—"
        quant_str = f"{quant_s:.1f}" if quant_s is not None else "—"

        # Descrição: limpar texto interno
        desc_clean = (
            str(desc)
            .replace("APENAS_MONITORAR", "Monitorar")
            .replace("ALTA_CONVERGENCIA", "Alta Convergência")
            .replace("ASSIMETRIA_DETECTADA", "Assimetria Detectada")
            .replace("DIVERGENCIA", "Divergência")
            .replace("BLOQUEADO", "Bloqueado")
            .replace("_", " ")
        )

        st.markdown(f"""
        <div class="panel" style="padding:14px 18px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;
                      align-items:flex-start;gap:12px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
              <div style="font-family:var(--font-display);font-weight:900;
                          font-size:1.2rem;color:var(--fg-1);">{ticker}</div>
              <span style="font-family:var(--font-mono);font-size:.65rem;
                           color:var(--fg-5);background:var(--bg-2);
                           padding:2px 8px;border-radius:4px;">{tipo}</span>
              {tier_html}
            </div>
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
              <div style="text-align:center;">
                <div style="font-family:var(--font-display);font-weight:900;
                            font-size:1.6rem;color:{score_color};">{score}</div>
                <div style="font-family:var(--font-mono);font-size:.55rem;
                            color:var(--fg-6);">SCORE</div>
              </div>
              {acao_html}
            </div>
          </div>
          <div style="margin-top:10px;display:flex;gap:24px;
                      font-family:var(--font-mono);font-size:.65rem;
                      color:var(--fg-5);flex-wrap:wrap;">
            <span>Sinal técnico: <strong style="color:var(--fg-2);">{tech_str}</strong></span>
            <span>Quant: <strong style="color:var(--fg-2);">{quant_str}</strong></span>
            <span style="color:var(--fg-4);flex:1;min-width:160px;">{desc_clean[:120] if desc_clean else ""}</span>
          </div>
          <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;
                      font-family:var(--font-mono);font-size:.6rem;color:var(--fg-6);">
            <span>Gatilho: <em>aguardando dados</em></span>
            <span>·</span>
            <span>Liquidez: <em>aguardando dados</em></span>
            <span>·</span>
            <span>Assimetria: <em>aguardando dados</em></span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Diagnóstico: o que falta para virar oportunidade completa ─────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _render_diagnostic()


def _render_diagnostic() -> None:
    """Mostra o diagnóstico do que ainda falta para transformar sinais em oportunidades completas."""
    with st.expander("O que falta para virar oportunidade completa?", expanded=False):
        st.markdown("""
        <div class="panel" style="padding:16px 20px;">
          <div style="font-size:.75rem;font-weight:800;color:var(--fg-2);margin-bottom:12px;">
            Campos de oportunidade: status por fonte
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.68rem;">

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--pos-tint);border-radius:6px;
                        border:1px solid var(--pos-border);">
              <span style="color:var(--fg-2);">Score de Convicção</span>
              <span style="color:var(--pos-500);font-weight:700;">✓ Disponível</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--pos-tint);border-radius:6px;
                        border:1px solid var(--pos-border);">
              <span style="color:var(--fg-2);">Direção (BUY/WATCH/SELL)</span>
              <span style="color:var(--pos-500);font-weight:700;">✓ Disponível</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--pos-tint);border-radius:6px;
                        border:1px solid var(--pos-border);">
              <span style="color:var(--fg-2);">Sinal Técnico</span>
              <span style="color:var(--pos-500);font-weight:700;">✓ Disponível</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--pos-tint);border-radius:6px;
                        border:1px solid var(--pos-border);">
              <span style="color:var(--fg-2);">Regime Macro</span>
              <span style="color:var(--pos-500);font-weight:700;">✓ Disponível</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--warn-tint);border-radius:6px;
                        border:1px solid var(--warn-border);">
              <span style="color:var(--fg-2);">Gatilho de Entrada</span>
              <span style="color:var(--warn-500);font-weight:700;">Em desenvolvimento</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--warn-tint);border-radius:6px;
                        border:1px solid var(--warn-border);">
              <span style="color:var(--fg-2);">Liquidez (ADV)</span>
              <span style="color:var(--warn-500);font-weight:700;">Em desenvolvimento</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--warn-tint);border-radius:6px;
                        border:1px solid var(--warn-border);">
              <span style="color:var(--fg-2);">Assimetria Risco/Retorno</span>
              <span style="color:var(--warn-500);font-weight:700;">Em desenvolvimento</span>
            </div>

            <div style="display:flex;justify-content:space-between;padding:6px 10px;
                        background:var(--warn-tint);border-radius:6px;
                        border:1px solid var(--warn-border);">
              <span style="color:var(--fg-2);">Valuation (preço justo validado)</span>
              <span style="color:var(--warn-500);font-weight:700;">Em validação</span>
            </div>

          </div>
        </div>
        """, unsafe_allow_html=True)


main()
