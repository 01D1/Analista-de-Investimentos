"""Radar Quant — Diagnostic Dashboard (S01.5)."""
from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# ── Block pipeline shadow: remove 12_PYTHON from sys.path to prevent
#    src.dashboard.data / src.utils / etc. from resolving to the wrong copy.
#    Keep scanner_quant as canonical.
_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
from src.ui.styles import PREMIUM_CSS
from src.ui.components import section_title, status_chip, alert_block
from src.dashboard.data import _db_path
from src.integration.valuation_bridge import list_valid_valuations, get_valuation as _bridge_valuation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_all() -> dict:
    """Load all available data from scanner_quant.db."""
    import sqlite3
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        # 1. Asset intelligence snapshots
        ais = conn.execute("""
            SELECT ticker, integrated_score, integrated_status, integrated_confidence,
                   technical_score_final, quant_score, data_quality_score,
                   governance_blocked, fair_value, upside_pct, market_price,
                   risk_status, option_structure_score, created_at
            FROM asset_intelligence_snapshots
            GROUP BY ticker
            ORDER BY ticker
        """).fetchall()
        # 2. Source health checks
        sh = conn.execute("""
            SELECT source_name, status, records_count, age_days, message, checked_at
            FROM source_health_checks
            ORDER BY checked_at DESC
            LIMIT 10
        """).fetchall()
        # 3. Risk snapshots
        rs = conn.execute("""
            SELECT ticker, trade_date, price, risk_status, parametric_var_95,
                   expected_shortfall_95, recommended_size, limiting_factor
            FROM risk_snapshots
            ORDER BY created_at DESC
        """).fetchall()
        # 4. Option candidates (may be empty)
        oc_count = conn.execute("SELECT COUNT(*) FROM option_structure_candidates").fetchone()[0]
        # 5. Market regime (regime_governance_status column does not exist in schema)
        reg = conn.execute("""
            SELECT trade_date, primary_regime, trend_regime, volatility_regime,
                   metadata_json
            FROM market_regime_daily
            ORDER BY trade_date DESC
            LIMIT 1
        """).fetchall()
        conn.close()
        return {
            "asset_intelligence": [dict(zip(
                ["ticker","integrated_score","integrated_status","integrated_confidence",
                 "technical_score_final","quant_score","data_quality_score",
                 "governance_blocked","fair_value","upside_pct","market_price",
                 "risk_status","option_structure_score","created_at"], r))
                for r in ais],
            "source_health": [dict(zip(
                ["source_name","status","records_count","age_days","message","checked_at"], r))
                for r in sh],
            "risk_snapshots": [dict(zip(
                ["ticker","trade_date","price","risk_status","parametric_var_95",
                 "expected_shortfall_95","recommended_size","limiting_factor"], r))
                for r in rs],
            "option_candidates_count": oc_count,
            "market_regime": [dict(zip(
                ["trade_date","primary_regime","trend_regime","volatility_regime",
                 "regime_metadata"], r))
                for r in reg] if reg else [],
        }
    except Exception as e:
        return {"error": str(e)}


def _status_badge(status: str) -> str:
    s = str(status or "").upper()
    if "BLOQUEADO" in s or "CRITICAL" in s:
        return "CRITICAL"
    if "WARNING" in s or "DEGRADED" in s:
        return "WARNING"
    if "OK" in s or "ALTA" in s or "GREEN" in s:
        return "OK"
    return "UNKNOWN"


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def _render_ticker_row(ticker: str, row: dict) -> None:
    gov_blocked = row.get("governance_blocked", 0)
    score = row.get("integrated_score", 0)
    status = row.get("integrated_status", "SEM_DADOS")
    tech = row.get("technical_score_final")
    quant = row.get("quant_score")
    dq = row.get("data_quality_score")
    fair_val = row.get("fair_value")
    upside = row.get("upside_pct")
    price = row.get("market_price")

    score_color = "var(--neg-500)" if gov_blocked else "var(--pos-500)"
    score_val = f"{score:.0f}" if score else "—"

    # Use status_chip() for governance status. Empty status → EMPTY chip.
    chip_html = status_chip(status if status and str(status).strip() else "EMPTY")

    st.markdown(f"""
    <div class="panel" style="padding: 12px 16px; margin-bottom: 8px;">
        <div style="display: grid; grid-template-columns: 80px 60px 1fr 1fr 80px; gap: 12px; align-items: center;">
            <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.1rem; color: var(--fg-1); letter-spacing: -0.3px;">{ticker}</div>
            <div style="text-align: center;">
                <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.4rem; color: {score_color};">{score_val}</div>
                <div style="font-family: var(--font-mono); font-size: 0.58rem; color: var(--fg-6);">SCORE</div>
            </div>
            <div>
                <div style="margin-bottom: 3px;">{chip_html}</div>
                <div style="font-size: 0.7rem; color: var(--fg-4);">conf: {row.get('integrated_confidence', '—')}</div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; font-family: var(--font-mono); font-size: 0.62rem;">
                <div>TEC<span style="color: var(--fg-2); font-weight: 700;">{f'{tech:.1f}' if tech else '—'}</span></div>
                <div>QNT<span style="color: var(--fg-2); font-weight: 700;">{f'{quant:.1f}' if quant else '—'}</span></div>
                <div>DQ<span style="color: var(--fg-2); font-weight: 700;">{f'{dq:.0f}' if dq else '—'}</span></div>
            </div>
            <div style="text-align: right;">
                <div style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">FV</div>
                <div style="font-family: var(--font-mono); font-size: 0.74rem; font-weight: 700; color: var(--fg-1);">{'R$ '+f'{fair_val:.2f}' if fair_val else '—'}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">Radar Quant — Diagnostic</div>
      <div class="page-header-sub">S01.5 Data Flow Integration Fix · real data · honest state</div>
    </div>""", unsafe_allow_html=True)

    data = _load_all()

    if "error" in data:
        st.error(f"Erro ao carregar dados: {data['error']}")
        st.stop()

    ais = data.get("asset_intelligence", [])
    sh = data.get("source_health", [])
    rs = data.get("risk_snapshots", [])
    reg = data.get("market_regime", [])
    oc_count = data.get("option_candidates_count", 0)

    # ── Header stats ────────────────────────────────────────────────────────
    from src.ui.components import kpi_card as _kpi_card
    blocked = sum(1 for r in ais if r.get("governance_blocked"))
    ok_count = len(ais) - blocked

    cols = st.columns(5)
    kpi_items = [
        {"label": "ATIVOS MONITORADOS", "value": str(len(ais)), "color": "cyan"},
        {"label": "SEM BLOQUEIO",       "value": str(ok_count), "color": "pos"},
        {"label": "BLOQUEADOS",         "value": str(blocked),  "color": "neg"},
        {"label": "FONTES (HEALTH)",     "value": str(len(sh)),   "color": "warn" if len(sh) == 0 else "cyan"},
        {"label": "OPTION CANDIDATES",   "value": str(oc_count), "color": "cyan"},
    ]
    for col, item in zip(cols, kpi_items):
        with col:
            _kpi_card(item["label"], item["value"], color=item["color"])

    # ── Asset Intelligence Snapshot table ───────────────────────────────────
    section_title("Asset Intelligence Snapshots", icon="")
    if ais:
        for row in ais:
            _render_ticker_row(row["ticker"], row)
    else:
        st.markdown(alert_block("warn",
            "Nenhum snapshot de inteligência de ativo encontrado",
            "Execute build_asset_intelligence_snapshot() para populer a base."),
            unsafe_allow_html=True)

    # ── Source Health ───────────────────────────────────────────────────────
    section_title("Source Health Checks", icon="")
    if sh:
        for h in sh:
            status_upper = str(h["status"] or "").lower()
            if status_upper == "ok":
                chip_html = status_chip("APPROVED_FOR_STUDY", label="OK")
            elif status_upper == "warning":
                chip_html = status_chip("DEGRADED", label="WARNING")
            elif status_upper == "stale":
                chip_html = status_chip("STALE")
            else:
                chip_html = status_chip("EMPTY", label=h["status"].upper() if h["status"] else "UNKNOWN")
            st.markdown(f"""
            <div class="panel" style="padding: 8px 14px; margin-bottom: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; color: var(--fg-1);">{h['source_name']}</span>
                    {chip_html}
                    <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">recs: {h['records_count'] or '—'} age: {h['age_days'] or '?'}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn", "Sem fontes verificadas",
            "Execute o pipeline de ingestão para verificar as fontes de dados."),
            unsafe_allow_html=True)

    # ── Market Regime ────────────────────────────────────────────────────────
    section_title("Market Regime", icon="")
    if reg:
        r = reg[0]
        gov_status = r.get("regime_governance_status", "")
        gov_chip = status_chip(gov_status if gov_status else "EMPTY")
        st.markdown(f"""
        <div class="panel" style="padding: 12px 16px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px;">
                <div><div style="font-family: var(--font-mono); font-size: 0.58rem; color: var(--fg-6);">REGIME</div><div style="font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; color: var(--fg-1);">{r['primary_regime']}</div></div>
                <div><div style="font-family: var(--font-mono); font-size: 0.58rem; color: var(--fg-6);">TREND</div><div style="font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; color: var(--fg-1);">{r['trend_regime']}</div></div>
                <div><div style="font-family: var(--font-mono); font-size: 0.58rem; color: var(--fg-6);">VOLATILIDADE</div><div style="font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; color: var(--fg-1);">{r['volatility_regime']}</div></div>
                <div><div style="font-family: var(--font-mono); font-size: 0.58rem; color: var(--fg-6);">GOV STATUS</div><div style="margin-top: 3px;">{gov_chip}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn", "Regime de mercado não disponível",
            "Execute o pipeline de ingestão para obter dados de regime de mercado."),
            unsafe_allow_html=True)

    # ── Risk Snapshots ───────────────────────────────────────────────────────
    section_title(f"Risk Snapshots ({len(rs)} ativos)", icon="")
    if rs:
        for r in rs:
            var95 = r.get("var_95")
            es95 = r.get("expected_shortfall_95")
            risk_status = str(r.get("risk_status") or "").upper()
            if risk_status == "RISK_OK":
                risk_chip = status_chip("APPROVED_FOR_STUDY", label="RISK OK")
            elif risk_status in ("RISK_HIGH", "RISK_CRITICAL"):
                risk_chip = status_chip("BLOCKED", label=risk_status)
            elif risk_status in ("RISK_WARNING", "RISK_DEGRADED"):
                risk_chip = status_chip("DEGRADED", label=risk_status)
            else:
                risk_chip = status_chip("EMPTY", label=risk_status if risk_status else "—")
            st.markdown(f"""
            <div class="panel" style="padding: 8px 14px; margin-bottom: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-family: var(--font-display); font-weight: 900; color: var(--fg-1);">{r['ticker']}</span>
                    {risk_chip}
                    <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">VaR95: {'R$ '+f'{var95:.2f}' if var95 else '—'}</span>
                    <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">ES95: {'R$ '+f'{es95:.2f}' if es95 else '—'}</span>
                    <span style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6);">{r['limiting_factor'] or ''}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn", "Nenhum snapshot de risco disponível",
            "Execute o pipeline de ingestão para calcular métricas de risco."),
            unsafe_allow_html=True)

    # ── Valuation Coverage (S04) ────────────────────────────────────────────
    section_title("Valuation Coverage", icon="")
    valid_tickers = list_valid_valuations()
    total_valid = len(valid_tickers)

    # ── Header stats ────────────────────────────────────────────────────────
    bridge_tickers = set(valid_tickers)
    sq_tickers = set(r["ticker"] for r in ais)
    bridge_in_sq = bridge_tickers & sq_tickers
    sq_only = sq_tickers - bridge_tickers
    diverged = []

    for ticker in bridge_in_sq:
        sq_row = next((r for r in ais if r["ticker"] == ticker), None)
        if sq_row:
            sq_fv = sq_row.get("fair_value")
            vd = _bridge_valuation(ticker)
            if sq_fv and sq_fv > 0 and vd and vd.is_complete and vd.fair_value:
                div_pct = round((vd.fair_value - sq_fv) / sq_fv * 100, 1)
                if abs(div_pct) >= 0.5:
                    diverged.append({
                        "ticker": ticker,
                        "sq_fv": sq_fv,
                        "pipe_fv": vd.fair_value,
                        "div_pct": div_pct,
                    })

    # ── Valuation stats (kpi_card) ─────────────────────────────────────────
    valuation_kpi_items = [
        {"label": "VALUATIONS VÁLIDOS (PIPELINE)", "value": str(total_valid), "color": "pos"},
        {"label": "BRIDGE + SQ DB",                  "value": str(len(bridge_in_sq)), "color": "cyan"},
        {"label": "SQ DB ONLY (SEM VALUATION)",       "value": str(len(sq_only)),     "color": "warn"},
        {"label": "DIVERGÊNCIAS (>0.5%)",             "value": str(len(diverged)),    "color": "neg"},
    ]
    vcols = st.columns(4)
    for col, item in zip(vcols, valuation_kpi_items):
        with col:
            _kpi_card(item["label"], item["value"], color=item["color"])

    # ── Divergences detail ──────────────────────────────────────────────────
    if diverged:
        body_lines = "\n".join(
            f"<b>{d['ticker']}</b>: SQ R$ {d['sq_fv']:.2f} vs Pipe R$ {d['pipe_fv']:.2f} ({d['div_pct']:+.1f}%)"
            for d in diverged
        )
        st.markdown(alert_block("warn",
            f"⚠ {len(diverged)} divergência(s): scanner_quant vs pipeline",
            body_lines), unsafe_allow_html=True)

    # ── Tickers with pipeline bridge ─────────────────────────────────────────
    if bridge_in_sq:
        section_title("Tickers com Valuation Pipeline Bridge", icon="")
        bridge_list = sorted(bridge_in_sq)
        for chunk in _chunks(bridge_list, 8):
            chips = " ".join(
                f'<span class="chip chip-approved" style="margin:2px;">{t}</span>'
                for t in chunk
            )
            st.markdown(chips, unsafe_allow_html=True)

    # ── SQ DB only (no bridge) ──────────────────────────────────────────────
    if sq_only:
        section_title("Scanner Quant DB — Sem Valuation Pipeline", icon="")
        sq_list = sorted(sq_only)
        for chunk in _chunks(sq_list, 8):
            chips = " ".join(
                f'<span class="chip chip-stale" style="margin:2px;">{t}</span>'
                for t in chunk
            )
            st.markdown(chips, unsafe_allow_html=True)

    # ── Data availability summary ───────────────────────────────────────────
    section_title("Data Availability", icon="")
    avail_items = [
        ("asset_intelligence_snapshots", len(ais) > 0, f"{len(ais)} tickers monitorados"),
        ("source_health_checks", len(sh) > 0, f"{len(sh)} fontes verificadas"),
        ("risk_snapshots", len(rs) > 0, f"{len(rs)} tickers com risco calculado"),
        ("option_structure_candidates", oc_count > 0, f"{oc_count} candidatos (vazio = nao executado)"),
        ("market_regime_daily", len(reg) > 0, f"regime: {reg[0]['primary_regime'] if reg else 'sem dados'}"),
    ]
    unavailable = [l for l, avail, _ in avail_items if not avail]
    if unavailable:
        st.markdown(alert_block("warn",
            f"{len(unavailable)} fonte(s) indisponível(is)",
            ", ".join(unavailable)), unsafe_allow_html=True)
    for label, available, detail in avail_items:
        icon = "✅" if available else "❌"
        color = "var(--pos-500)" if available else "var(--neg-500)"
        st.markdown(
            f'<div class="panel" style="padding: 6px 14px; margin-bottom: 4px;">'
            f'<span style="color: {color}; font-weight: 700;">{icon}</span> '
            f'<span style="color: var(--fg-2); font-size: .72rem;">{label}</span> '
            f'<span style="color: var(--fg-5); font-size: .68rem;">— {detail}</span>'
            f'</div>',
            unsafe_allow_html=True)


main()