"""Diagnóstico Técnico — Pipeline, Fontes e Saúde do Sistema.

Centraliza informações técnicas do pipeline:
  - Saúde das fontes de dados
  - Snapshots de risco por ativo
  - Status do pipeline de opções
  - Regime de mercado detalhado
  - Caminhos e versões do banco

Regras:
  - Nenhuma escrita no banco
  - Nenhum cálculo novo
  - Nenhum mock
  - Esta página é o destino correto para informações técnicas
    removidas das páginas de produto
"""
from __future__ import annotations

import sqlite3
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
from src.ui.components import section_title, status_chip, alert_block, kpi_card
from src.dashboard.data import _db_path


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def _load_diagnostic() -> dict:
    db = _db_path()
    result: dict = {
        "db_path": str(db),
        "db_exists": Path(db).exists(),
        "asset_intelligence": [],
        "source_health": [],
        "risk_snapshots": [],
        "market_regime": [],
        "option_candidates_count": 0,
        "error": None,
    }
    if not result["db_exists"]:
        result["error"] = f"Banco não encontrado: {db}"
        return result
    try:
        conn = sqlite3.connect(str(db))

        # Asset intelligence snapshots (all tickers)
        ais = conn.execute("""
            SELECT ticker, integrated_score, integrated_status, integrated_confidence,
                   technical_score_final, quant_score, data_quality_score,
                   governance_blocked, fair_value, upside_pct, market_price,
                   risk_status, option_structure_score, created_at
            FROM asset_intelligence_snapshots
            GROUP BY ticker
            ORDER BY ticker
        """).fetchall()
        result["asset_intelligence"] = [
            dict(zip([
                "ticker", "integrated_score", "integrated_status", "integrated_confidence",
                "technical_score_final", "quant_score", "data_quality_score",
                "governance_blocked", "fair_value", "upside_pct", "market_price",
                "risk_status", "option_structure_score", "created_at",
            ], r))
            for r in ais
        ]

        # Source health
        sh = conn.execute("""
            SELECT source_name, status, records_count, age_days, message, checked_at
            FROM source_health_checks
            ORDER BY checked_at DESC
            LIMIT 20
        """).fetchall()
        result["source_health"] = [
            dict(zip(["source_name", "status", "records_count", "age_days", "message", "checked_at"], r))
            for r in sh
        ]

        # Risk snapshots
        rs = conn.execute("""
            SELECT ticker, trade_date, price, risk_status, parametric_var_95,
                   expected_shortfall_95, recommended_size, limiting_factor
            FROM risk_snapshots
            ORDER BY created_at DESC
        """).fetchall()
        result["risk_snapshots"] = [
            dict(zip([
                "ticker", "trade_date", "price", "risk_status",
                "parametric_var_95", "expected_shortfall_95",
                "recommended_size", "limiting_factor",
            ], r))
            for r in rs
        ]

        # Option candidates
        result["option_candidates_count"] = conn.execute(
            "SELECT COUNT(*) FROM option_structure_candidates"
        ).fetchone()[0]

        # Market regime
        reg = conn.execute("""
            SELECT trade_date, primary_regime, trend_regime, volatility_regime, metadata_json
            FROM market_regime_daily
            ORDER BY trade_date DESC
            LIMIT 1
        """).fetchall()
        result["market_regime"] = [
            dict(zip([
                "trade_date", "primary_regime", "trend_regime",
                "volatility_regime", "metadata_json",
            ], r))
            for r in reg
        ] if reg else []

        conn.close()
    except Exception as e:
        result["error"] = str(e)
    return result


# ── Page ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header">
      <div class="page-header-title">Diagnóstico Técnico</div>
      <div class="page-header-sub">
        Saúde do pipeline — fontes de dados, snapshots, regime e infraestrutura
      </div>
    </div>
    """, unsafe_allow_html=True)

    data = _load_diagnostic()

    if data.get("error"):
        st.markdown(alert_block(
            "error",
            "Erro ao acessar banco de dados",
            data["error"],
        ), unsafe_allow_html=True)
        return

    ais     = data["asset_intelligence"]
    sh      = data["source_health"]
    rs      = data["risk_snapshots"]
    reg     = data["market_regime"]
    oc      = data["option_candidates_count"]

    # ── Header KPIs ────────────────────────────────────────────────────────────
    blocked = sum(1 for r in ais if r.get("governance_blocked"))
    ok_cnt  = len(ais) - blocked
    sh_ok   = sum(1 for s in sh if (s.get("status") or "").lower() == "ok")
    sh_warn = len(sh) - sh_ok

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("ATIVOS NO BANCO", str(len(ais)), color="cyan")
    with c2:
        kpi_card("SEM BLOQUEIO", str(ok_cnt), color="green")
    with c3:
        kpi_card("BLOQUEADOS", str(blocked), color="red")
    with c4:
        kpi_card("FONTES OK", str(sh_ok), color="green")
    with c5:
        kpi_card("CANDIDATOS OPÇÕES", str(oc), color="violet")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── DB Info ────────────────────────────────────────────────────────────────
    section_title("Banco de Dados", icon="")
    st.markdown(f"""
    <div class="panel" style="padding:10px 16px;font-family:var(--font-mono);
         font-size:.65rem;color:var(--fg-4);">
      <span style="color:var(--fg-6);">PATH:</span>&nbsp;
      <span style="color:var(--fg-2);">{data['db_path']}</span>
      &nbsp;·&nbsp;
      <span style="color:var(--fg-6);">STATUS:</span>&nbsp;
      <span style="color:{'var(--pos-500)' if data['db_exists'] else 'var(--neg-500)'};">
        {'Existe' if data['db_exists'] else 'NÃO ENCONTRADO'}
      </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Saúde das Fontes ────────────────────────────────────────────────────────
    section_title(f"Saúde das Fontes de Dados ({len(sh)} verificações)", icon="")
    if sh:
        for h in sh:
            s = (h.get("status") or "").lower()
            if s == "ok":
                chip = status_chip("APPROVED_FOR_STUDY", label="OK")
            elif s in ("warning", "degraded"):
                chip = status_chip("DEGRADED", label=s.upper())
            elif s == "stale":
                chip = status_chip("STALE")
            else:
                chip = status_chip("EMPTY", label=h.get("status", "—").upper() if h.get("status") else "UNKNOWN")
            st.markdown(f"""
            <div class="panel" style="padding:8px 14px;margin-bottom:4px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
                <span style="font-family:var(--font-mono);font-size:.72rem;font-weight:700;
                             color:var(--fg-1);">{h['source_name']}</span>
                {chip}
                <span style="font-family:var(--font-mono);font-size:.62rem;color:var(--fg-5);">
                  recs: {h.get('records_count') or '—'}
                  &nbsp;·&nbsp;
                  idade: {h.get('age_days') or '?'} dias
                </span>
                <span style="font-family:var(--font-mono);font-size:.6rem;color:var(--fg-6);
                             flex:1;text-align:right;">{h.get('checked_at', '')[:16]}</span>
              </div>
              {f'<div style="font-size:.62rem;color:var(--fg-5);margin-top:4px;">{h["message"]}</div>' if h.get('message') else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn",
            "Nenhuma verificação de fontes registrada",
            "Execute o pipeline de ingestão para registrar saúde das fontes."),
            unsafe_allow_html=True)

    # ── Regime de Mercado (técnico) ─────────────────────────────────────────────
    section_title("Regime de Mercado (detalhado)", icon="")
    if reg:
        r = reg[0]
        st.markdown(f"""
        <div class="panel" style="padding:12px 16px;">
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;
                      font-family:var(--font-mono);font-size:.68rem;">
            <div>
              <div style="font-size:.55rem;color:var(--fg-6);margin-bottom:2px;">DATA</div>
              <div style="color:var(--fg-2);font-weight:700;">{r.get('trade_date','—')}</div>
            </div>
            <div>
              <div style="font-size:.55rem;color:var(--fg-6);margin-bottom:2px;">REGIME PRIMÁRIO</div>
              <div style="color:var(--fg-1);font-weight:700;">{r.get('primary_regime','—')}</div>
            </div>
            <div>
              <div style="font-size:.55rem;color:var(--fg-6);margin-bottom:2px;">TENDÊNCIA</div>
              <div style="color:var(--fg-1);font-weight:700;">{r.get('trend_regime','—')}</div>
            </div>
            <div>
              <div style="font-size:.55rem;color:var(--fg-6);margin-bottom:2px;">VOLATILIDADE</div>
              <div style="color:var(--fg-1);font-weight:700;">{r.get('volatility_regime','—')}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn",
            "Regime de mercado não disponível",
            "Execute o pipeline de ingestão para calcular o regime atual."),
            unsafe_allow_html=True)

    # ── Snapshots de Risco ──────────────────────────────────────────────────────
    section_title(f"Snapshots de Risco ({len(rs)} ativos)", icon="")
    if rs:
        for r in rs:
            var95 = r.get("parametric_var_95") or r.get("var_95")
            es95  = r.get("expected_shortfall_95")
            risk_s = str(r.get("risk_status") or "").upper()
            if "OK" in risk_s:
                risk_chip = status_chip("APPROVED_FOR_STUDY", label="RISCO OK")
            elif "HIGH" in risk_s or "CRITICAL" in risk_s:
                risk_chip = status_chip("BLOCKED", label=risk_s)
            elif "WARNING" in risk_s or "DEGRADED" in risk_s:
                risk_chip = status_chip("DEGRADED", label=risk_s)
            else:
                risk_chip = status_chip("EMPTY", label=risk_s or "—")

            st.markdown(f"""
            <div class="panel" style="padding:8px 14px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
                <span style="font-family:var(--font-display);font-weight:900;
                             color:var(--fg-1);">{r['ticker']}</span>
                {risk_chip}
                <span style="font-family:var(--font-mono);font-size:.62rem;color:var(--fg-5);">
                  VaR95: {'R$ '+f'{var95:.2f}' if var95 else '—'}
                  &nbsp;·&nbsp;
                  ES95: {'R$ '+f'{es95:.2f}' if es95 else '—'}
                </span>
                <span style="font-family:var(--font-mono);font-size:.6rem;
                             color:var(--fg-6);">{r.get('limiting_factor') or ''}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(alert_block("warn",
            "Nenhum snapshot de risco disponível",
            "Execute o pipeline para calcular métricas de risco por ativo."),
            unsafe_allow_html=True)

    # ── Asset Intelligence Raw ──────────────────────────────────────────────────
    with st.expander(f"Snapshots de Inteligência de Ativos ({len(ais)} ativos)", expanded=False):
        if ais:
            import pandas as pd
            df = pd.DataFrame([{
                "Ticker": r["ticker"],
                "Score": f"{r['integrated_score']:.0f}" if r.get("integrated_score") else "—",
                "Status": (r.get("integrated_status") or "—").replace("_", " "),
                "Conf.": r.get("integrated_confidence") or "—",
                "Técnico": f"{r['technical_score_final']:.1f}" if r.get("technical_score_final") else "—",
                "Quant": f"{r['quant_score']:.1f}" if r.get("quant_score") else "—",
                "DQ": f"{r['data_quality_score']:.0f}" if r.get("data_quality_score") else "—",
                "Bloqueado": "Sim" if r.get("governance_blocked") else "Não",
                "Atualizado": (r.get("created_at") or "")[:10],
            } for r in ais])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum snapshot disponível.")


main()
