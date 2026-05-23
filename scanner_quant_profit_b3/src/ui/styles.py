"""
Premium CSS for Plataforma Quant B3.

Canonical source: src/ui/design_tokens.css
This module embeds design_tokens.css + component styles into PREMIUM_CSS.

Tokens are loaded from design_tokens.css at import time and must never be
duplicated in this file.
"""

from pathlib import Path

# Resolve design_tokens.css relative to this file
_DESIGN_TOKENS_CSS = Path(__file__).parent / "design_tokens.css"

# Fallback to tokens.css if design_tokens.css doesn't exist yet
if _DESIGN_TOKENS_CSS.exists():
    _TOKENS: str = _DESIGN_TOKENS_CSS.read_text(encoding="utf-8")
else:
    _TOKENS: str = (Path(__file__).parent / "tokens.css").read_text(encoding="utf-8")

# ── Component styles (Streamlit-specific overrides) ───────────────────────────
_COMPONENT_CSS: str = """
/* ════════════════════════════════════════════════════════════════════
   BASE RESET & STREAMLIT OVERRIDES
   ════════════════════════════════════════════════════════════════════ */
html, body, [data-testid="stAppViewContainer"] {
    font-family: var(--font-body) !important;
    background-color: var(--bg-0) !important;
    color: var(--fg-1) !important;
    -webkit-font-smoothing: antialiased;
}
section.main > div { padding-top: 0.2rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stHeader"] { background: transparent !important; }

/* ════════════════════════════════════════════════════════════════════
   ANIMATIONS
   ════════════════════════════════════════════════════════════════════ */
.fade-in { animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

/* ════════════════════════════════════════════════════════════════════
   UTILITY CLASSES (RADAR MACRO)
   ════════════════════════════════════════════════════════════════════ */
.live-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px;
  border-radius: var(--r-pill); background: rgba(34,211,238,0.10);
  border: 1px solid var(--brand-600); color: var(--brand-300);
  font-family: var(--font-mono); font-size: 0.6rem; font-weight: 700;
  letter-spacing: 0.6px; text-transform: uppercase;
}
.live-pill .dot {
  width: 5px; height: 5px; border-radius: 50%; background: var(--brand-300);
  box-shadow: 0 0 6px var(--brand-300); animation: breathe 1.4s ease-in-out infinite;
}

.card-base {
  background: var(--bg-3); border: 1px solid var(--border-1);
  border-radius: var(--r-xl); padding: 16px 18px;
  transition: all 0.2s ease-in-out; animation: fadeInUp 0.4s ease;
}
.card-base:hover { border-color: var(--border-focus); box-shadow: var(--shadow-2); transform: translateY(-2px); }

/* KPI Strip */
.kpi-card {
  flex: 1; min-width: 140px; background: var(--bg-3); border: 1px solid var(--border-1);
  border-radius: var(--r-xl); padding: 14px 16px; border-top: 2px solid var(--brand-500);
  transition: all 0.2s ease;
}
.kpi-card:hover { border-color: var(--border-focus); transform: translateY(-2px); }
.kpi-card.green { border-top-color: var(--pos-500); }
.kpi-card.red { border-top-color: var(--neg-500); }
.kpi-card.amber { border-top-color: var(--warn-500); }
.kpi-card.violet { border-top-color: var(--violet-500); }
.kpi-label {
  font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--fg-6); font-weight: 800; margin-bottom: 4px;
}
.kpi-value {
  font-family: var(--font-display); font-size: 1.6rem; font-weight: 900;
  color: var(--fg-1); letter-spacing: -0.5px; line-height: 1.05;
}

/* Badge */
.badge {
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px;
  border-radius: var(--r-pill); font-size: 0.66rem; font-weight: 800;
  letter-spacing: 0.4px; text-transform: uppercase; font-family: var(--font-body);
  white-space: nowrap; border: 1px solid transparent;
}
.badge-buy    { background: var(--pos-tint); color: var(--pos-500); border-color: var(--pos-border); }
.badge-hold   { background: var(--warn-tint); color: var(--warn-500); border-color: var(--warn-border); }
.badge-sell   { background: var(--neg-tint); color: var(--neg-500); border-color: var(--neg-border); }
.badge-cyan   { background: rgba(34,211,238,0.14); color: var(--brand-300); border-color: rgba(34,211,238,0.40); }
.badge-violet { background: var(--violet-tint); color: var(--violet-500); border-color: rgba(167,139,250,0.35); }

/* Hero */
.hero-section {
  background: linear-gradient(135deg, var(--bg-2) 0%, var(--bg-3) 60%, var(--bg-elevated) 100%);
  border: 1px solid var(--border-1); border-radius: var(--r-3xl); padding: 24px 28px;
  margin-bottom: 18px; position: relative; overflow: hidden; animation: fadeInUp 0.4s ease;
}
.hero-section::before {
  content: ""; position: absolute; inset: 0 0 auto 0; height: 2px;
  background: linear-gradient(90deg, var(--brand-500), var(--brand-400), var(--brand-500));
}

/* Tables */
.tbl-wrap { background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-xl); overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 0.82rem; }
.tbl th { background: var(--bg-2); color: var(--fg-5); font-family: var(--font-body); font-size: 0.66rem; font-weight: 800; text-transform: uppercase; text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--border-1); }
.tbl td { padding: 12px 14px; border-bottom: 1px solid var(--border-1); color: var(--fg-2); }
.tbl tr:hover { background: var(--bg-2); }

/* ════════════════════════════════════════════════════════════════════
   NAV  (page_link)
   ════════════════════════════════════════════════════════════════════ */
[data-testid="stPageLink"] a {
    display: flex !important; align-items: center !important; justify-content: center !important;
    background: transparent !important; border: 1px solid var(--border-1) !important;
    border-radius: 8px !important; color: var(--fg-5) !important;
    font-family: var(--font-body) !important; font-weight: 700 !important;
    font-size: 0.7rem !important; text-transform: uppercase !important;
    letter-spacing: 0.4px !important; padding: 6px 10px !important;
    text-decoration: none !important; transition: all 0.15s ease !important;
}
[data-testid="stPageLink"] a:hover {
    background: var(--bg-tint-cyan) !important; color: var(--brand-300) !important;
    border-color: var(--brand-600) !important; box-shadow: var(--shadow-glow-c) !important;
}
[data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stPageLink"] a[aria-current="page"] {
    background: var(--bg-tint-cyan) !important; color: var(--brand-300) !important;
    border-color: var(--brand-600) !important; box-shadow: var(--shadow-glow-c) !important;
}

/* ════════════════════════════════════════════════════════════════════
   WIDGET OVERRIDES
   ════════════════════════════════════════════════════════════════════ */
h1, h2, h3, h4 { font-family: var(--font-display) !important; color: var(--fg-1) !important; letter-spacing: -0.5px !important; }
h1 { font-size: 2rem !important; font-weight: 900 !important; }
h2 { font-size: 1.4rem !important; font-weight: 900 !important; }

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background-color: var(--bg-3) !important; border-color: var(--border-1) !important;
}
input { color: var(--fg-2) !important; font-family: var(--font-body) !important; }

.stButton > button {
    background: transparent !important; color: var(--fg-4) !important;
    border: 1px solid var(--border-1) !important; border-radius: 8px !important;
    font-family: var(--font-body) !important; font-weight: 700 !important;
    font-size: 0.76rem !important; transition: all 0.15s ease !important;
}
.stButton > button:hover { border-color: var(--brand-600) !important; color: var(--brand-300) !important; }

/* ── Radar AI / Intelligence components ────────────────────────────── */
.stage-running { animation: pulseGlow 2.2s ease-in-out infinite; }
.trace-row-enter { animation: tickerEnter 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
.caret::after {
  content: "▍"; color: var(--brand-300); margin-left: 2px;
  animation: blinkCaret 1.05s steps(1) infinite;
}
.radar-shell {
    max-width: 1680px; margin: 0 auto; padding: 8px 12px 32px;
}
.panel-shell {
    background: linear-gradient(180deg, rgba(15,23,42,.96), rgba(8,13,23,.98));
    border: 1px solid var(--border-1); border-radius: 14px;
    padding: 14px 16px; overflow: hidden; position: relative;
}
.panel-shell::before {
    content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(34,211,238,.45), transparent);
}
.block-container {
    max-width: 1680px !important; padding-top: .8rem !important; padding-bottom: 2rem !important;
}

/* ── Page header (used by intelligence pages) ─────────────────────── */
.page-header {
  margin-bottom: 18px; animation: fadeInUp var(--t-slow) var(--ease-out);
}
.page-header-title {
  font-family: var(--font-display); font-size: 1.4rem; font-weight: 900;
  letter-spacing: -0.5px; color: var(--fg-1); margin: 0 0 4px 0;
}
.page-header-sub {
  font-size: var(--fs-caption); color: var(--fg-5); margin: 0;
}
.summary-header { display: flex; gap: 16px; margin-bottom: 18px; align-items: center; }
.summary-kpi { display: flex; flex-direction: column; align-items: center; min-width: 80px; }
.summary-kpi-num {
  font-family: var(--font-display); font-size: 2rem; font-weight: 900; line-height: 1;
  letter-spacing: -1px;
}
.summary-kpi-num.blue { color: var(--brand-400); }
.summary-kpi-num.green { color: var(--pos-500); }
.summary-kpi-num.amber { color: var(--warn-500); }
.summary-kpi-num.red { color: var(--neg-500); }
.summary-kpi-label {
  font-size: var(--fs-eyebrow); font-weight: 800; text-transform: uppercase;
  letter-spacing: var(--ls-uppercase); color: var(--fg-6); margin-top: 4px;
}

/* ── Watchlist card ────────────────────────────────────────────── */
.wl-card {
  background: var(--bg-3); border: 1px solid var(--border-1);
  border-radius: var(--r-xl); padding: 16px 18px;
  position: relative; overflow: hidden; cursor: pointer;
  transition: all var(--t-base) var(--ease-in-out);
  animation: fadeInUp var(--t-slow) var(--ease-out);
}
.wl-card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
.wl-card.buy::before { background: var(--pos-500); }
.wl-card.hold::before { background: var(--warn-500); }
.wl-card.sell::before { background: var(--neg-500); }
.wl-card:hover {
  border-color: var(--border-focus); box-shadow: var(--shadow-3);
  transform: translateY(-2px);
}
.wl-card .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.wl-card .tk {
  font-family: var(--font-display); font-size: 1.3rem; font-weight: var(--fw-black);
  color: var(--fg-1); letter-spacing: -0.5px;
}
.wl-card .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin-top: 10px; }
.wl-card .grid .item { font-size: var(--fs-eyebrow); color: var(--fg-5); }
.wl-card .grid .item .v { display: block; font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: var(--fg-3); }
.wl-card .meta { margin-top: 10px; font-size: var(--fs-eyebrow); color: var(--fg-6); font-family: var(--font-mono); }

/* ── Section title ────────────────────────────────────────────── */
.section-title {
  display: flex; align-items: center; justify-content: space-between;
  font-size: var(--fs-label); text-transform: uppercase;
  letter-spacing: var(--ls-uppercase-l); font-weight: var(--fw-extra);
  color: var(--fg-6); margin: 22px 0 12px 0; padding-bottom: 8px;
  border-bottom: 1px solid var(--border-1);
}

/* ── Score bars ────────────────────────────────────────────────── */
.score-bar { margin-bottom: 12px; animation: fadeInUp var(--t-slow) var(--ease-out); }
.score-bar:last-child { margin-bottom: 0; }
.score-bar .head {
  display: flex; justify-content: space-between; margin-bottom: 4px;
  font-size: var(--fs-label); color: var(--fg-4); font-weight: 600; gap: 8px;
}
.score-bar .head > span:first-child {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 1;
}
.score-bar .head .val { font-family: var(--font-mono); color: var(--fg-2); }
.score-bar .track { background: var(--border-1); border-radius: var(--r-pill); height: 7px; overflow: hidden; }
.score-bar .fill { height: 100%; border-radius: var(--r-pill); animation: fillBar 0.9s ease-out; }
.score-bar.blue .fill   { background: linear-gradient(90deg, var(--brand-600), var(--brand-400)); }
.score-bar.green .fill { background: linear-gradient(90deg, var(--pos-600), var(--pos-500)); }
.score-bar.amber .fill  { background: linear-gradient(90deg, var(--warn-600), var(--warn-500)); }
.score-bar.red .fill    { background: linear-gradient(90deg, #B91C1C, var(--neg-500)); }
.score-bar.violet .fill { background: linear-gradient(90deg, var(--violet-600), var(--violet-500)); }

/* ── KPI delta helpers (used by kpi_card component) ─────────────── */
.kpi-delta-pos { font-family: var(--font-mono); font-size: var(--fs-label); color: var(--pos-500); font-weight: 700; margin-top: 4px; }
.kpi-delta-neg { font-family: var(--font-mono); font-size: var(--fs-label); color: var(--neg-500); font-weight: 700; margin-top: 4px; }
.kpi-sub { font-size: var(--fs-caption); color: var(--fg-5); margin-top: 4px; }

/* ── Panel shell ──────────────────────────────────────────────── */
.panel {
  background: var(--bg-3); border: 1px solid var(--border-1);
  border-radius: var(--r-xl); padding: 16px 18px; margin-bottom: 14px;
  position: relative; overflow: hidden;
  transition: border-color var(--t-fast) var(--ease-in-out);
}
.panel:hover { border-color: var(--border-2); }
.panel.elevated {
  background: linear-gradient(160deg, var(--bg-elevated) 0%, var(--bg-3) 100%);
}

/* ── Status chips (data health & governance states) ─────────────── */
.chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: var(--r-pill);
  font-family: var(--font-mono); font-size: 0.6rem; font-weight: 800;
  letter-spacing: 0.5px; text-transform: uppercase;
  border: 1px solid transparent; white-space: nowrap;
}
.chip .dot {
  width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0;
}

/* DEGRADED — fonte com problema, dado pode estar comprometido (amber/warn) */
.chip-degraded {
  background: var(--warn-tint); border-color: var(--warn-border);
  color: var(--warn-500);
}
.chip-degraded .dot { background: var(--warn-500); animation: pulseDot 2s infinite; }

/* REVIEW — precisa atenção manual (violet) */
.chip-review {
  background: var(--violet-tint); border-color: var(--violet-border);
  color: var(--violet-500);
}
.chip-review .dot { background: var(--violet-500); }

/* MONITOR_ONLY — estrutura válida mas requer validação contínua (amber/warn) */
.chip-monitor {
  background: var(--warn-tint); border-color: var(--warn-border);
  color: var(--warn-500);
}
.chip-monitor .dot { background: var(--warn-500); animation: breathe 1.8s ease-in-out infinite; }

/* MANUAL_REVIEW_READY — pronto para análise manual (cyan/brand) */
.chip-manual {
  background: rgba(34,211,238,0.12); border-color: rgba(34,211,238,0.35);
  color: var(--brand-300);
}
.chip-manual .dot { background: var(--brand-300); }

/* PAPER_ONLY — não operacional, apenas para papel (neutral) */
.chip-paper {
  background: var(--neutral-tint); border-color: var(--neutral-border);
  color: var(--fg-4);
}
.chip-paper .dot { background: var(--fg-4); }

/* BLOCKED — rejeitado por regra (neg/red) */
.chip-blocked {
  background: var(--neg-tint); border-color: var(--neg-border);
  color: var(--neg-500);
}
.chip-blocked .dot { background: var(--neg-500); }

/* STALE — dados desatualizados (amber) */
.chip-stale {
  background: var(--warn-tint-soft); border-color: rgba(245,158,11,0.22);
  color: var(--warn-600);
}
.chip-stale .dot { background: var(--warn-600); animation: breathe 3s ease-in-out infinite; }

/* EMPTY — sem dados disponíveis (neutral) */
.chip-empty {
  background: rgba(100,116,139,0.08); border-color: var(--border-1);
  color: var(--fg-5);
}
.chip-empty .dot { background: var(--fg-5); }

/* APPROVED_FOR_STUDY — válido para análise (pos/green) */
.chip-approved {
  background: var(--pos-tint); border-color: var(--pos-border);
  color: var(--pos-500);
}
.chip-approved .dot { background: var(--pos-500); }

/* ── Risk item base ───────────────────────────────────────────── */
.risk-item-base {
  background: var(--bg-2); border: 1px solid var(--border-1);
  border-radius: var(--r-md); padding: 10px 14px; margin-bottom: 8px;
}

/* ── Alert blocks ─────────────────────────────────────────────── */
.alert {
  border-radius: var(--r-lg); padding: 12px 16px;
  border-left: 3px solid; margin-bottom: 12px;
  font-size: var(--fs-body); line-height: var(--lh-snug);
}
.alert-info    { background: var(--blue-tint); border-color: var(--blue-500); color: var(--blue-300); }
.alert-warn    { background: var(--warn-tint); border-color: var(--warn-500); color: var(--warn-500); }
.alert-error   { background: var(--neg-tint); border-color: var(--neg-500); color: var(--neg-500); }
.alert-success { background: var(--pos-tint); border-color: var(--pos-500); color: var(--pos-500); }
.alert-title { font-weight: 800; font-size: var(--fs-label); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.alert-body  { font-size: var(--fs-body); color: var(--fg-3); }

/* ── Metric card (returns HTML string) ────────────────────────── */
.metric-card {
  background: var(--bg-3); border: 1px solid var(--border-1);
  border-top: 3px solid var(--brand-500);
  border-radius: var(--r-lg); padding: 12px 16px; margin-bottom: 10px;
}
.metric-card-brand { border-top-color: var(--brand-500); }
.metric-card-pos   { border-top-color: var(--pos-500); }
.metric-card-neg   { border-top-color: var(--neg-500); }
.metric-card-warn  { border-top-color: var(--warn-500); }
.metric-card-violet{ border-top-color: var(--violet-500); }
.metric-card .mc-label {
  font-size: var(--fs-eyebrow); text-transform: uppercase;
  letter-spacing: var(--ls-uppercase); color: var(--fg-5);
  font-weight: var(--fw-extra); margin-bottom: 5px;
}
.metric-card .mc-value {
  font-family: var(--font-display); font-size: 1.5rem; font-weight: 900;
  color: var(--fg-1); letter-spacing: -0.5px; line-height: 1;
}
.metric-card .mc-delta { font-family: var(--font-mono); font-size: var(--fs-label); margin-top: 3px; }
.metric-card .mc-sub   { font-size: var(--fs-caption); color: var(--fg-5); margin-top: 3px; }
"""

# ── Assemble ──────────────────────────────────────────────────────────────────
PREMIUM_CSS: str = f"<style>\n{_TOKENS}\n{_COMPONENT_CSS}\n</style>"