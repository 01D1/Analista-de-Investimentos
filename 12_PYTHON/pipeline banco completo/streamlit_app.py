"""
Valuation Engine — Plataforma Profissional de Análise Fundamentalista
Dark mode · Cards · Nível XP / BTG / Bloomberg
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT      = Path(__file__).resolve().parent
QUAL_ROOT = ROOT / "data" / "qualitative"

# ── CSS dark mode ────────────────────────────────────────────────────────────

_CSS = """
<style>
section.main > div { padding-top: 0.5rem; }

/* HEADER */
.ve-header {
    background: linear-gradient(135deg, #060B14 0%, #0D1F38 55%, #060B14 100%);
    border: 1px solid #1E3A5F;
    border-radius: 12px;
    padding: 18px 26px 16px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}
.ve-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #1D4ED8 0%, #7C3AED 50%, #0EA5E9 100%);
}
.ve-title {
    font-size: 1.5rem; font-weight: 900; color: #F1F5F9;
    letter-spacing: -0.5px; margin: 0;
}
.ve-title em { color: #3B82F6; font-style: normal; }
.ve-sub { font-size: 0.75rem; color: #334155; margin-top: 5px; }
.ve-meta { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.ve-pill {
    display: inline-flex; align-items: center; gap: 5px;
    background: #0D1F38; border: 1px solid #1E3A5F;
    padding: 3px 11px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; color: #60A5FA;
}

/* KPI STRIP */
.kpi-strip { display: flex; gap: 10px; margin-bottom: 20px; }
.kpi-card {
    flex: 1; background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; padding: 14px 16px; text-align: center;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.kc-green::before  { background: #22C55E; }
.kc-amber::before  { background: #F59E0B; }
.kc-blue::before   { background: #3B82F6; }
.kc-purple::before { background: #7C3AED; }
.kc-red::before    { background: #EF4444; }
.kpi-label { font-size: 0.63rem; color: #334155; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 1.6rem; font-weight: 900; color: #F1F5F9; line-height: 1.1; }
.kpi-sub   { font-size: 0.65rem; margin-top: 2px; color: #475569; }

/* SECTION TITLE */
.sec-title {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #334155;
    margin: 22px 0 12px;
    display: flex; align-items: center; gap: 8px;
}
.sec-title::after { content: ''; flex: 1; height: 1px; background: #1E2D42; }

/* BADGES */
.badge {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 0.67rem; font-weight: 800; letter-spacing: 0.3px;
}
.b-compra { background: #052e16; color: #22C55E; border: 1px solid #166534; }
.b-forte  { background: #052e16; color: #22C55E; border: 1px solid #166534; }
.b-obs    { background: #1c1100; color: #F59E0B; border: 1px solid #92400e; }
.b-alerta { background: #1c0909; color: #EF4444; border: 1px solid #7f1d1d; }
.b-alta   { background: #0c1f40; color: #60A5FA; }
.b-baixa  { background: #1c0a1c; color: #F472B6; }
.b-neutro { background: #1A1A2E; color: #64748B; }

/* TOP PICK CARD */
.tp-card {
    background: #111827; border: 1px solid #1E2D42; border-radius: 12px;
    padding: 16px; height: 100%; box-sizing: border-box;
}
.tp-card-forte { border-left: 4px solid #22C55E !important; }
.tp-card-obs   { border-left: 4px solid #F59E0B !important; }
.tp-card-alerta{ border-left: 4px solid #EF4444 !important; }
.tp-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.tp-ativo { font-size: 1.35rem; font-weight: 900; color: #F1F5F9; }
.tp-nome  { font-size: 0.72rem; color: #334155; margin-top: 2px; }
.tp-score-val { font-size: 1.9rem; font-weight: 900; line-height: 1; }
.tp-score-lbl { font-size: 0.58rem; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; }
.tp-badges { margin-bottom: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
.tp-divider { border-top: 1px solid #1E2D42; margin: 10px 0; }
.tp-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
.tp-key { font-size: 0.68rem; color: #334155; }
.tp-val { font-size: 0.8rem; font-weight: 700; color: #E2E8F0; }
.tp-val-g { color: #22C55E !important; }
.tp-val-r { color: #EF4444 !important; }
.tp-val-a { color: #F59E0B !important; }
.tp-bar-bg { background: #1E2D42; border-radius: 3px; height: 3px; margin-top: 10px; }
.tp-bar    { height: 3px; border-radius: 3px; }

/* ANALYSIS CARD */
.ac {
    background: #111827; border: 1px solid #1E2D42;
    border-radius: 10px; margin-bottom: 12px; overflow: hidden;
}
.ac-buy    { border-left: 4px solid #22C55E; }
.ac-watch  { border-left: 4px solid #F59E0B; }
.ac-alert  { border-left: 4px solid #EF4444; }
.ac-head   { padding: 14px 18px 10px; border-bottom: 1px solid #162034; }
.ac-body   { padding: 14px 18px; }
.ac-foot   {
    background: #0A0E1A; padding: 7px 18px;
    font-size: 0.72rem; color: #334155; font-family: monospace;
    border-top: 1px solid #162034;
}
.ac-title-row { display: flex; justify-content: space-between; align-items: flex-start; }
.ac-ativo  { font-size: 1.15rem; font-weight: 800; color: #F1F5F9; }
.ac-nome   { font-size: 0.82rem; color: #334155; }
.ac-score-block { text-align: right; }
.ac-score-val { font-size: 1.1rem; font-weight: 900; }
.ac-meta   { margin-top: 8px; display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
.ac-prog   { background: #1E2D42; border-radius: 3px; height: 3px; margin-top: 10px; }
.ac-grid   { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.ac-col-head {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; color: #334155; margin-bottom: 7px;
}
.ac-row  { display: flex; justify-content: space-between; padding: 3px 0; font-size: 0.78rem; }
.ac-dk   { color: #334155; }
.ac-dv   { font-weight: 700; color: #CBD5E1; }
.ac-dv-g { color: #22C55E !important; }
.ac-dv-r { color: #EF4444 !important; }
.human-text { font-size: 0.84rem; color: #64748B; line-height: 1.65; }

/* SCROLLBAR */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2D4A6B; }

/* DETAIL BOX */
.detail-box {
    background: #0D1421; border: 1px solid #1E3A5F;
    border-radius: 12px; padding: 22px; margin-top: 12px;
}
.detail-box h4 { color: #94A3B8; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 8px; }
.detail-box p  { color: #64748B; font-size: 0.84rem; line-height: 1.65; margin: 0; }

/* DIMENSION TABLE */
.dim-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid #1E2D42; font-size: 0.82rem;
}
.dim-row:last-child { border-bottom: none; }
.dim-name  { color: #94A3B8; flex: 2; }
.dim-score { font-weight: 900; width: 40px; text-align: right; }
.dim-bar-wrap { flex: 3; margin: 0 12px; }
.dim-bar-bg   { background: #1E2D42; border-radius: 2px; height: 4px; }
.dim-bar-fill { height: 4px; border-radius: 2px; }
.dim-conf  { color: #475569; font-size: 0.7rem; width: 60px; text-align: right; }

/* EVENT PILL */
.ev-pill {
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    font-size: 0.72rem; color: #94A3B8; background: #111827;
    border: 1px solid #1E2D42; margin: 3px 3px 3px 0; line-height: 1.5;
}
.ev-melhora  { background: #052e16; color: #4ADE80; border-color: #166534; }
.ev-piora    { background: #1c0909; color: #FCA5A5; border-color: #7f1d1d; }
.ev-neutro   { background: #1A1A2E; color: #94A3B8; border-color: #1E2D42; }
</style>
"""


# ── Helpers de dados ─────────────────────────────────────────────────────────

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _available_tickers() -> list[str]:
    tickers: set[str] = set()
    for base in [QUAL_ROOT / "summaries", QUAL_ROOT / "reports", QUAL_ROOT / "events"]:
        if base.exists():
            tickers.update(p.name.upper() for p in base.iterdir() if p.is_dir())
    return sorted(tickers)


def _load_ticker_data(ticker: str) -> dict:
    scorecard = _load_json(QUAL_ROOT / "summaries" / ticker / "qualitative_scorecard.json", {})
    events    = _load_json(QUAL_ROOT / "events"    / ticker / "events.json", [])
    alert     = scorecard.get("thesis_alert") or {}
    return {"scorecard": scorecard, "events": events, "alert": alert}


def _latest_run_summary(ticker: str) -> dict:
    summary_dir = ROOT / "outputs" / "run_summaries"
    if not summary_dir.exists():
        return {}
    matches = sorted(
        summary_dir.glob(f"run_summary_{ticker}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if matches:
        return _load_json(matches[0], {})
    latest = summary_dir / "run_summary_latest.json"
    data   = _load_json(latest, {})
    return data if str(data.get("ticker", "")).upper() == ticker else {}


# ── Helpers de cor / score ────────────────────────────────────────────────────

def _score_color(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "#64748B"
    if s >= 7:
        return "#22C55E"
    if s >= 5:
        return "#F59E0B"
    return "#EF4444"


def _upside_color(upside_pct: float | None) -> str:
    if upside_pct is None:
        return "#64748B"
    if upside_pct >= 15:
        return "#22C55E"
    if upside_pct >= 5:
        return "#F59E0B"
    return "#EF4444"


def _alert_badge(alert: dict) -> str:
    level = str(alert.get("level", "")).upper()
    if "ALTO" in level or "CRITICO" in level:
        return '<span class="badge b-alerta">🚨 ALERTA</span>'
    if "MEDIO" in level or "MODERADO" in level:
        return '<span class="badge b-obs">⚠️ OBSERVAR</span>'
    return '<span class="badge b-compra">✅ TESE OK</span>'


def _signal_badge(scorecard: dict, upside: float | None) -> tuple[str, str]:
    score = scorecard.get("overall_score")
    try:
        s = float(score)
    except (TypeError, ValueError):
        return '<span class="badge b-obs">⚠️ OBSERVAR</span>', "tp-card-obs"
    if s >= 7 and (upside or 0) >= 15:
        return '<span class="badge b-forte">🔥 FORTE</span>', "tp-card-forte"
    if s >= 5:
        return '<span class="badge b-obs">⚠️ OBSERVAR</span>', "tp-card-obs"
    return '<span class="badge b-alerta">⛔ ALERTA</span>', "tp-card-alerta"


# ── Texto humanizado ──────────────────────────────────────────────────────────

def generate_human_readable_text(data: dict) -> dict:
    """Gera leitura humanizada a partir dos dados qualitativos de uma empresa."""
    scorecard = data["scorecard"]
    alert     = data["alert"]
    events    = data["events"]
    ticker    = scorecard.get("ticker", "a empresa") or "a empresa"

    score = scorecard.get("overall_score")
    try:
        s = float(score)
        score_desc = (
            f"análise qualitativa sólida (nota {s:.1f}/10)"  if s >= 7.5 else
            f"fundamentos razoáveis (nota {s:.1f}/10)"       if s >= 5.5 else
            f"fundamentos fracos (nota {s:.1f}/10) — cautela"
        )
    except (TypeError, ValueError):
        score_desc = "fundamentos em avaliação (evidências insuficientes)"

    val_ref   = alert.get("valuation_reference") or {}
    preco     = val_ref.get("preco_justo_on")
    upside    = val_ref.get("upside_on")
    tir       = val_ref.get("tir_on")

    if preco and upside is not None:
        try:
            up_f = float(str(upside).replace("%", "").replace(",", "."))
            if up_f >= 20:
                upside_txt = f"upside atrativo de {upside} em relação ao preço atual"
            elif up_f >= 5:
                upside_txt = f"upside moderado de {upside}"
            else:
                upside_txt = f"pouco espaço de valorização ({upside} de upside)"
        except (ValueError, TypeError):
            upside_txt = f"preço-alvo de R$ {preco}"
    elif preco:
        upside_txt = f"preço justo estimado em R$ {preco}"
    else:
        upside_txt = "valuation ainda não calculado para este período"

    catalysts = [e for e in events if e.get("thesis_effect") == "melhora"]
    risks     = [e for e in events if str(e.get("event_type", "")).startswith("risco")]

    if catalysts:
        cat_desc = "; ".join(
            str(e.get("description", ""))[:80] for e in catalysts[:2]
        )
        cat_txt = f"Catalisadores identificados: {cat_desc}."
    else:
        cat_txt = "Nenhum catalisador de curto prazo mapeado."

    if risks:
        risk_desc = "; ".join(
            str(e.get("description", ""))[:80] for e in risks[:2]
        )
        risk_txt = f"Riscos monitorados: {risk_desc}."
    else:
        risk_txt = "Sem alertas de risco qualitativo relevante no momento."

    alert_msg  = alert.get("message", "")
    alert_level = str(alert.get("level", "")).upper()
    if "ALTO" in alert_level or "CRITICO" in alert_level:
        tese_txt = f"ATENÇÃO: {alert_msg}" if alert_msg else "Alerta de tese ativo — revisar posição."
    elif alert_msg:
        tese_txt = alert_msg
    else:
        tese_txt = "Tese de investimento dentro do esperado."

    return {
        "leitura_ativo": f"{ticker.upper()} apresenta {score_desc}, com {upside_txt}.",
        "leitura_fluxo": cat_txt,
        "interpretacao": f"{tese_txt} {risk_txt}",
        "justificativa": (
            f"TIR estimada de {tir}. " if tir else ""
        ) + (
            "Estrutura com margem de segurança adequada para posição direcional."
            if score_desc.startswith("análise qualitativa sólida") else
            "Aguardar confirmação de catalisadores antes de aumentar exposição."
        ),
    }


# ── TOP PICK CARD ─────────────────────────────────────────────────────────────

def _top_pick_card(ticker: str, data: dict, rank: int) -> str:
    scorecard = data["scorecard"]
    alert     = data["alert"]
    val_ref   = alert.get("valuation_reference") or {}

    score      = scorecard.get("overall_score")
    sc_color   = _score_color(score)
    sc_display = f"{float(score):.1f}" if score is not None else "—"
    sc_w       = min(int(float(score) * 10) if score else 0, 100)

    preco  = val_ref.get("preco_justo_on", "—")
    upside = val_ref.get("upside_on", "—")
    tir    = val_ref.get("tir_on", "—")

    try:
        up_f   = float(str(upside).replace("%", "").replace(",", "."))
        up_cls = "tp-val-g" if up_f >= 15 else ("tp-val-a" if up_f >= 5 else "tp-val-r")
    except (ValueError, TypeError):
        up_cls = "tp-val"

    badge_html, card_cls = _signal_badge(scorecard, None)
    alert_badge           = _alert_badge(alert)

    docs   = scorecard.get("documents_count", 0)
    events = scorecard.get("events_count", 0)

    return f"""
<div class="tp-card {card_cls}">
  <div class="tp-top">
    <div>
      <div class="tp-ativo">#{rank} {ticker}</div>
      <div class="tp-nome">{docs} docs · {events} eventos</div>
    </div>
    <div style="text-align:right">
      <div class="tp-score-val" style="color:{sc_color}">{sc_display}</div>
      <div class="tp-score-lbl">score/10</div>
    </div>
  </div>

  <div class="tp-badges">
    {badge_html}
    {alert_badge}
  </div>

  <div class="tp-divider"></div>

  <div class="tp-row">
    <span class="tp-key">Preço Justo</span>
    <span class="tp-val">R$ {preco}</span>
  </div>
  <div class="tp-row">
    <span class="tp-key">Upside</span>
    <span class="tp-val {up_cls}">{upside}</span>
  </div>
  <div class="tp-row">
    <span class="tp-key">TIR estimada</span>
    <span class="tp-val">{tir}</span>
  </div>
  <div class="tp-row">
    <span class="tp-key">Alerta de tese</span>
    <span class="tp-val">{alert.get('level', 'N/A')}</span>
  </div>

  <div class="tp-bar-bg">
    <div class="tp-bar" style="width:{sc_w}%;background:{sc_color}"></div>
  </div>
</div>
"""


# ── ANALYSIS CARD (visão completa) ────────────────────────────────────────────

def _analysis_card(ticker: str, data: dict) -> str:
    scorecard = data["scorecard"]
    alert     = data["alert"]
    val_ref   = alert.get("valuation_reference") or {}
    human     = generate_human_readable_text(data)

    score    = scorecard.get("overall_score")
    sc_color = _score_color(score)
    sc_w     = min(int(float(score) * 10) if score else 0, 100)
    sc_disp  = f"{float(score):.1f}" if score else "—"

    badge_html, _  = _signal_badge(scorecard, None)
    alert_badge    = _alert_badge(alert)
    alert_level    = str(alert.get("level", "")).upper()
    border_cls     = (
        "ac-alert" if ("ALTO" in alert_level or "CRITICO" in alert_level) else
        "ac-watch" if ("MEDIO" in alert_level or "MODERADO" in alert_level) else
        "ac-buy"
    )

    preco  = val_ref.get("preco_justo_on", "—")
    upside = val_ref.get("upside_on", "—")
    tir    = val_ref.get("tir_on", "—")
    docs   = scorecard.get("documents_count", 0)
    events = scorecard.get("events_count", 0)

    try:
        up_f   = float(str(upside).replace("%", "").replace(",", "."))
        up_cls = "ac-dv-g" if up_f >= 15 else ("" if up_f >= 5 else "ac-dv-r")
    except (ValueError, TypeError):
        up_cls = ""

    return f"""
<div class="ac {border_cls}">
  <div class="ac-head">
    <div class="ac-title-row">
      <div>
        <span class="ac-ativo">{ticker}</span>
      </div>
      <div class="ac-score-block">
        <span style="font-size:0.72rem;color:#334155">Score </span>
        <span class="ac-score-val" style="color:{sc_color}">{sc_disp}</span>
        <span style="font-size:0.65rem;color:#334155">/10</span>
      </div>
    </div>
    <div class="ac-meta">
      {badge_html}
      {alert_badge}
      <span style="font-size:0.72rem;color:#334155">
        {docs} docs &nbsp;·&nbsp; {events} eventos
      </span>
    </div>
    <div class="ac-prog">
      <div style="width:{sc_w}%;height:3px;border-radius:3px;background:{sc_color}"></div>
    </div>
  </div>

  <div class="ac-body" style="border-bottom:1px solid #162034">
    <div class="human-text">{human['leitura_ativo']}</div>
    <div style="font-size:0.76rem;color:#334155;margin-top:4px">{human['leitura_fluxo']}</div>
  </div>

  <div class="ac-body">
    <div class="ac-grid">
      <div>
        <div class="ac-col-head">💰 Valuation</div>
        <div class="ac-row"><span class="ac-dk">Preço justo</span><span class="ac-dv">R$ {preco}</span></div>
        <div class="ac-row"><span class="ac-dk">Upside</span><span class="ac-dv {up_cls}">{upside}</span></div>
        <div class="ac-row"><span class="ac-dk">TIR</span><span class="ac-dv">{tir}</span></div>
      </div>
      <div>
        <div class="ac-col-head">🎯 Tese</div>
        <div style="font-size:0.78rem;color:#64748B;line-height:1.5">{human['interpretacao']}</div>
      </div>
    </div>
  </div>

  <div class="ac-foot">{human['justificativa']}</div>
</div>
"""


# ── Score por dimensão ────────────────────────────────────────────────────────

def _dimensions_html(scorecard: dict) -> str:
    dims = scorecard.get("dimensions") or {}
    if not dims:
        return '<p style="color:#334155;font-size:0.8rem">Sem dimensões avaliadas.</p>'

    rows = []
    for dim_key, data in dims.items():
        name  = dim_key.replace("_", " ").title()
        score = data.get("score")
        conf  = data.get("confidence", "—")
        try:
            s    = float(score)
            color = _score_color(s)
            w     = min(int(s * 10), 100)
            s_str = f"{s:.1f}"
        except (TypeError, ValueError):
            color, w, s_str = "#64748B", 0, "—"

        rows.append(f"""
<div class="dim-row">
  <span class="dim-name">{name}</span>
  <span class="dim-score" style="color:{color}">{s_str}</span>
  <div class="dim-bar-wrap">
    <div class="dim-bar-bg">
      <div class="dim-bar-fill" style="width:{w}%;background:{color}"></div>
    </div>
  </div>
  <span class="dim-conf">{conf}</span>
</div>""")

    return "\n".join(rows)


# ── Eventos como pills ────────────────────────────────────────────────────────

def _events_html(events: list, max_items: int = 12) -> str:
    if not events:
        return '<p style="color:#334155;font-size:0.8rem">Nenhum evento extraído.</p>'

    pills = []
    for e in events[:max_items]:
        effect = e.get("thesis_effect", "neutro")
        cls    = "ev-melhora" if effect == "melhora" else ("ev-piora" if effect == "piora" else "ev-neutro")
        desc   = str(e.get("description", ""))[:90]
        pills.append(f'<span class="ev-pill {cls}">{desc}</span>')

    return " ".join(pills)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar(tickers: list[str]) -> tuple[str, float, str]:
    with st.sidebar:
        st.markdown("### 📊 Valuation Engine")
        st.markdown("---")

        st.markdown("**Empresa**")
        ticker = st.selectbox(
            "Ativo", tickers,
            label_visibility="collapsed",
        ) if tickers else st.text_input("Ticker", value="WEGE3").strip().upper()

        st.markdown("---")
        st.markdown("**Filtros de listagem**")

        score_min = st.slider("Score mínimo", 0.0, 10.0, 0.0, 0.5)

        alert_filter = st.multiselect(
            "Alerta de tese",
            ["SEM_ALERTA", "BAIXO", "MEDIO", "ALTO", "CRITICO"],
            default=[],
        )

        st.markdown("---")
        st.markdown(
            '<div style="font-size:0.7rem;color:#334155">'
            'Motor qualitativo B3<br>Análise fundamentalista autônoma'
            '</div>',
            unsafe_allow_html=True,
        )

    return ticker, score_min, alert_filter


# ── Tabs ──────────────────────────────────────────────────────────────────────

def _tab_visao_geral(tickers: list[str], score_min: float, alert_filter: list) -> None:
    all_data: list[tuple[str, dict, float | None]] = []

    for t in tickers:
        d = _load_ticker_data(t)
        sc = d["scorecard"].get("overall_score")
        try:
            s = float(sc)
        except (TypeError, ValueError):
            s = None
        all_data.append((t, d, s))

    # Filtros
    if score_min > 0:
        all_data = [(t, d, s) for t, d, s in all_data if s is not None and s >= score_min]
    if alert_filter:
        all_data = [
            (t, d, s) for t, d, s in all_data
            if str(d["alert"].get("level", "SEM_ALERTA")).upper()
            in [a.upper() for a in alert_filter]
        ]

    all_data.sort(key=lambda x: (x[2] or 0), reverse=True)

    # KPIs
    total    = len(tickers)
    analisados = len([s for _, _, s in all_data if s is not None])
    fortes   = sum(1 for _, d, s in all_data if s is not None and s >= 7)
    avg_sc   = (
        sum(s for _, _, s in all_data if s is not None) / analisados
        if analisados else 0
    )
    alertas  = sum(
        1 for _, d, _ in all_data
        if str(d["alert"].get("level", "")).upper() in ("ALTO", "CRITICO")
    )

    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-card kc-blue">
        <div class="kpi-label">Empresas</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub">na cobertura</div>
      </div>
      <div class="kpi-card kc-green">
        <div class="kpi-label">Analisadas</div>
        <div class="kpi-value" style="color:#22C55E">{analisados}</div>
        <div class="kpi-sub">com dados qualitativos</div>
      </div>
      <div class="kpi-card kc-amber">
        <div class="kpi-label">Score Médio</div>
        <div class="kpi-value">{avg_sc:.1f}</div>
        <div class="kpi-sub">de 10.0</div>
      </div>
      <div class="kpi-card kc-purple">
        <div class="kpi-label">Tese Forte</div>
        <div class="kpi-value" style="color:#22C55E">{fortes}</div>
        <div class="kpi-sub">score ≥ 7.0</div>
      </div>
      <div class="kpi-card kc-red">
        <div class="kpi-label">Alertas</div>
        <div class="kpi-value" style="color:#EF4444">{alertas}</div>
        <div class="kpi-sub">tese em risco</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not all_data:
        st.warning("Nenhuma empresa encontrada com os filtros atuais. Ajuste o score mínimo ou o filtro de alerta.")
        return

    # TOP PICKS
    top_picks = [x for x in all_data if (x[2] or 0) >= 5][:5]

    if top_picks:
        st.markdown(
            '<div class="sec-title">🔥 Top Picks — Melhores Oportunidades</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(top_picks))
        for i, (col, (t, d, _)) in enumerate(zip(cols, top_picks)):
            with col:
                st.markdown(_top_pick_card(t, d, i + 1), unsafe_allow_html=True)
                if st.button("▶ Ver análise", key=f"pick_btn_{i}", use_container_width=True):
                    st.session_state["detail_ticker"] = t

        if "detail_ticker" in st.session_state:
            sel_t = st.session_state["detail_ticker"]
            sel_d = _load_ticker_data(sel_t)
            st.markdown(
                f'<div class="sec-title">📋 Análise Completa — {sel_t}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_analysis_card(sel_t, sel_d), unsafe_allow_html=True)

    # Todas as empresas
    st.markdown(
        f'<div class="sec-title">📋 Todas as Empresas ({len(all_data)})</div>',
        unsafe_allow_html=True,
    )
    for t, d, _ in all_data:
        st.markdown(_analysis_card(t, d), unsafe_allow_html=True)


def _tab_qualitativa(ticker: str) -> None:
    data      = _load_ticker_data(ticker)
    scorecard = data["scorecard"]
    events    = data["events"]
    alert     = data["alert"]
    human     = generate_human_readable_text(data)

    report_path = QUAL_ROOT / "reports" / ticker / "RELATORIO_QUALITATIVO_EMPRESA.md"

    score    = scorecard.get("overall_score")
    sc_color = _score_color(score)
    sc_disp  = f"{float(score):.1f}" if score else "—"

    val_ref = alert.get("valuation_reference") or {}
    preco   = val_ref.get("preco_justo_on", "—")
    upside  = val_ref.get("upside_on", "—")
    tir     = val_ref.get("tir_on", "—")

    # Header da empresa
    badge_html, _ = _signal_badge(scorecard, None)
    alert_badge   = _alert_badge(alert)

    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-card kc-blue">
        <div class="kpi-label">Score Qualitativo</div>
        <div class="kpi-value" style="color:{sc_color}">{sc_disp}</div>
        <div class="kpi-sub">de 10.0</div>
      </div>
      <div class="kpi-card kc-green">
        <div class="kpi-label">Documentos</div>
        <div class="kpi-value">{scorecard.get('documents_count', 0)}</div>
        <div class="kpi-sub">analisados</div>
      </div>
      <div class="kpi-card kc-amber">
        <div class="kpi-label">Eventos</div>
        <div class="kpi-value">{scorecard.get('events_count', 0)}</div>
        <div class="kpi-sub">extraídos</div>
      </div>
      <div class="kpi-card kc-purple">
        <div class="kpi-label">Upside</div>
        <div class="kpi-value">{upside}</div>
        <div class="kpi-sub">P. justo R$ {preco}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Leitura humanizada
    st.markdown(f"""
    <div class="detail-box">
      <h4>Leitura do Ativo</h4>
      <p>{human['leitura_ativo']}</p>
      <h4 style="margin-top:14px">Fluxo de Catalisadores</h4>
      <p>{human['leitura_fluxo']}</p>
      <h4 style="margin-top:14px">Interpretação</h4>
      <p>{human['interpretacao']}</p>
      <h4 style="margin-top:14px">Justificativa da Operação</h4>
      <p>{human['justificativa']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Score por dimensão
    st.markdown(
        '<div class="sec-title">📊 Score por Dimensão</div>',
        unsafe_allow_html=True,
    )
    st.markdown(_dimensions_html(scorecard), unsafe_allow_html=True)

    # Eventos
    st.markdown(
        '<div class="sec-title">📰 Eventos Corporativos</div>',
        unsafe_allow_html=True,
    )
    st.markdown(_events_html(events), unsafe_allow_html=True)

    # Riscos x Catalisadores
    risks      = [e for e in events if str(e.get("event_type", "")).startswith("risco")]
    catalysts  = [e for e in events if e.get("thesis_effect") == "melhora"]

    col_r, col_c = st.columns(2)
    with col_r:
        st.markdown(
            '<div class="sec-title">⚠️ Riscos</div>',
            unsafe_allow_html=True,
        )
        if risks:
            for e in risks[:6]:
                relevancia = e.get("relevance", "")
                desc       = e.get("description", "")
                st.markdown(
                    f'<div class="ev-pill ev-piora"><strong>{relevancia}</strong> — {desc[:100]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p style="color:#334155;font-size:0.8rem">Nenhum risco qualitativo extraído.</p>',
                unsafe_allow_html=True,
            )

    with col_c:
        st.markdown(
            '<div class="sec-title">🚀 Catalisadores</div>',
            unsafe_allow_html=True,
        )
        if catalysts:
            for e in catalysts[:6]:
                relevancia = e.get("relevance", "")
                desc       = e.get("description", "")
                st.markdown(
                    f'<div class="ev-pill ev-melhora"><strong>{relevancia}</strong> — {desc[:100]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p style="color:#334155;font-size:0.8rem">Nenhum catalisador extraído.</p>',
                unsafe_allow_html=True,
            )

    # Relatório completo
    if report_path.exists():
        with st.expander("📄 Relatório qualitativo completo", expanded=False):
            st.markdown(report_path.read_text(encoding="utf-8"))


def _tab_valuation(ticker: str) -> None:
    summary = _latest_run_summary(ticker)

    if not summary:
        st.markdown("""
        <div style="background:#111827;border:1px solid #1E2D42;border-radius:10px;
                    padding:24px;text-align:center;color:#334155;font-size:0.9rem">
          Nenhum resumo numérico encontrado para <strong style="color:#94A3B8">{}</strong>.<br>
          <span style="font-size:0.78rem">Execute o pipeline para gerar os outputs.</span>
        </div>
        """.format(ticker), unsafe_allow_html=True)
        return

    # Mostra as métricas chave do summary de forma humanizada
    st.markdown(
        '<div class="sec-title">📈 Resumo Numérico</div>',
        unsafe_allow_html=True,
    )

    # Métricas principais (se existirem)
    keys_of_interest = ["ticker", "preco_justo", "upside", "tir", "ev_ebitda", "p_l", "dividend_yield"]
    cols_data = {k: summary.get(k) for k in keys_of_interest if k in summary}

    if cols_data:
        col_groups = list(cols_data.items())
        chunk_size = 4
        for i in range(0, len(col_groups), chunk_size):
            chunk = col_groups[i : i + chunk_size]
            cols  = st.columns(len(chunk))
            for col, (k, v) in zip(cols, chunk):
                col.metric(k.replace("_", " ").title(), v)

    # JSON completo em expander escuro
    with st.expander("🔍 Dados completos (JSON)", expanded=False):
        st.json(summary)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Valuation Engine",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    if "detail_ticker" not in st.session_state:
        st.session_state["detail_ticker"] = None

    tickers = _available_tickers()

    ticker, score_min, alert_filter = _render_sidebar(tickers)

    # Header
    n_tickers = len(tickers)
    st.markdown(f"""
    <div class="ve-header">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
        <div>
          <div class="ve-title">📊 <em>Valuation Engine</em></div>
          <div class="ve-sub">Análise fundamentalista autônoma · Motor qualitativo B3</div>
        </div>
        <div class="ve-meta">
          <span class="ve-pill">📋 {n_tickers} empresa{"s" if n_tickers != 1 else ""} na cobertura</span>
          <span class="ve-pill">🔎 {ticker} selecionada</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_geral, tab_qual, tab_num = st.tabs([
        "🔥 Visão Geral & Top Picks",
        "📋 Análise Qualitativa",
        "📈 Valuation Numérico",
    ])

    with tab_geral:
        _tab_visao_geral(tickers, score_min, alert_filter)

    with tab_qual:
        _tab_qualitativa(ticker)

    with tab_num:
        _tab_valuation(ticker)


if __name__ == "__main__":
    main()
