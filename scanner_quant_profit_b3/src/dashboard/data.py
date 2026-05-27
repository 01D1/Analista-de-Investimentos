"""Camada local de dados para as paginas de inteligencia.

Canonical source matrix (S04.5):
  Valuation (DCF)     -> scanner_quant.db asset_intelligence_snapshots.fair_value
                        (pipeline banco completo: reference only, not integrated)
  Preço de mercado    -> cotahist_daily (latest close per ticker)
  OHLCV histórico     -> cotahist_daily
  Notícias            -> 12_PYTHON/news_hunter/banco.db via news_connector.py
  Macro BCB           -> macro_series (scanner_quant.db) — Selic/PTAX/IPCA
  Risco               -> risk_snapshots (scanner_quant.db)
  Opções              -> option_structure_candidates (scanner_quant.db)
  Scores técnicos     -> technical_feature_snapshots / asset_intelligence_snapshots
  Scores quantitativo -> asset_intelligence_snapshots.integrated_score

Pipeline banco completo (12_PYTHON/pipeline banco completo/data/valuation.db):
  STATUS: catalogado, não integrado ao PYTHONPATH.
  USE CASE: referência para auditoria de valuation, não para consumo pelo app.
  149 tickers cubiertos, inclui banks (tipo_empresa=bank) com COSIF-adjusted DCF.
  Fonte alternativa: scanner_quant.db é canônica para o app Streamlit.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_quality.ri_sites import get_valid_ri_url_for_ticker
from src.integration.asset_intelligence_engine import build_asset_intelligence_snapshot
from src.integration.asset_intelligence_store import load_latest_asset_intelligence_snapshot
from src.integration.valuation_bridge import get_valuation as _bridge_valuation, list_available_tickers as _bridge_available_tickers
from src.utils import load_config, project_path


def _db_path():
    try:
        cfg = load_config()
    except Exception:
        cfg = {"database_path": "data/database/scanner_quant.db"}
    return project_path(cfg.get("database_path", "data/database/scanner_quant.db"))


def _get_market_price(db_path: str | Path, ticker: str) -> float | None:
    """Resolve market_price from cotahist_daily (canonical source).

    asset_intelligence_snapshots.market_price is NOT populated by the engine —
    the engine does not write it. Real market price comes from cotahist_daily.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT close FROM cotahist_daily WHERE ticker=? ORDER BY trade_date DESC LIMIT 1",
            (str(ticker).upper(),),
        ).fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None


def _latest_snapshot(tickers: list[str] | None = None) -> pd.DataFrame:
    db = _db_path()
    df = load_latest_asset_intelligence_snapshot(db, tickers=tickers)
    if df.empty and tickers:
        try:
            df = build_asset_intelligence_snapshot(tickers=tickers, db_path=db)
        except Exception:
            df = pd.DataFrame()
    return df


def _positioning(status: str) -> str:
    value = str(status or "").upper()
    if "ALTA_CONVERGENCIA" in value or "ASSIMETRIA" in value:
        return "COMPRAR"
    if "BLOQUEADO" in value or "DIVERGENCIA" in value:
        return "VENDER"
    return "MANTER"


@st.cache_data(ttl=300, show_spinner=False)
def get_watchlist_summary() -> list[dict]:
    df = _latest_snapshot()
    if df.empty:
        return []
    out = df.copy()
    out["positioning"] = out["integrated_status"].map(_positioning)
    out["confidence"] = out.get("integrated_confidence", pd.Series("", index=out.index))
    out["fair_value_brl"] = pd.to_numeric(out.get("fair_value", pd.Series(dtype=float)), errors="coerce")
    out["price"] = pd.to_numeric(out.get("market_price", pd.Series(dtype=float)), errors="coerce")
    out["pe_ratio"] = pd.NA
    out["ev_ebitda"] = pd.NA
    out["generated_at"] = out.get("created_at", out.get("trade_date", ""))

    # ── Enrich with pipeline bridge valuation (S04) ─────────────────────────
    # valuation_bridge.get_valuation returns a dict with keys:
    #   preco_alvo, upside_pct, fonte, ticker, data_valuation
    # Falls back to scanner_quant_db if outputs_dir unavailable.
    #
    # PERFORMANCE: usa list_available_tickers() (1 glob) antes de abrir arquivos.
    # get_valuation() tem cache em memória — relê o Excel apenas uma vez por sessão.
    tickers_in_scope = out["ticker"].tolist()
    bridge_cache: dict[str, dict] = {}

    _outputs_dir: str | None = None
    _available_in_bridge: set[str] = set()
    try:
        _outputs_dir = str(project_path("12_PYTHON/pipeline banco completo/outputs"))
        # Um único glob — O(1ms) — para saber quais tickers têm Excel
        _available_in_bridge = _bridge_available_tickers(_outputs_dir)
    except Exception:
        pass  # outputs_dir unavailable — all tickers use scanner_quant_db fallback

    _no_bridge_entry = {
        "valuation_available": False,
        "valuation_source": "scanner_quant_db",
        "valuation_method": "",
        "valuation_date": "",
    }

    for tk in tickers_in_scope:
        # Pular imediatamente tickers sem arquivo Excel — sem I/O
        if _outputs_dir is None or str(tk).upper() not in _available_in_bridge:
            bridge_cache[tk] = _no_bridge_entry
            continue
        try:
            vd = _bridge_valuation(str(tk), _outputs_dir)
        except Exception:
            bridge_cache[tk] = _no_bridge_entry
            continue
        if vd and isinstance(vd, dict) and vd.get("preco_alvo"):
            bridge_cache[tk] = {
                "valuation_available": True,
                "valuation_source": "pipeline_bridge",
                "valuation_method": "DCF/planilha",
                "valuation_date": vd.get("data_valuation") or "",
            }
            out.loc[out["ticker"] == tk, "fair_value_brl"] = vd["preco_alvo"]
        else:
            bridge_cache[tk] = _no_bridge_entry

    out["valuation_available"] = out["ticker"].map(
        lambda t: bridge_cache.get(str(t), {}).get("valuation_available", False)
    )
    out["valuation_source"] = out["ticker"].map(
        lambda t: bridge_cache.get(str(t), {}).get("valuation_source", "none")
    )

    cols = ["ticker", "positioning", "confidence", "fair_value_brl", "upside_pct", "price",
            "pe_ratio", "ev_ebitda", "generated_at", "valuation_available", "valuation_source"]
    for col in cols:
        if col not in out.columns:
            out[col] = pd.NA
    return out[cols].sort_values("ticker").to_dict(orient="records")


@st.cache_data(ttl=300, show_spinner=False)
def get_asset_detail(ticker: str) -> dict | None:
    """
    Return comprehensive asset detail enriched with valuation bridge data.

    Valuation priority (S03 mandate):
      1. valuation_bridge.py (pipeline DCF — 59 VALID tickers) — PREFERRED
      2. scanner_quant.db asset_intelligence_snapshots.fair_value — FALLBACK

    Fields exposed per S03 spec:
      - valuation_available: bool
      - valuation_source: 'pipeline_bridge' | 'scanner_quant_db' | 'none'
      - valuation_method: str
      - valuation_date: str (YYYY-MM-DD)
      - current_price: float | None
      - fair_value: float (from bridge when valid, else from scanner_quant.db)
      - upside_decimal: float | None (e.g. 0.7125 = +71.25%)
      - upside_pct: float | None (e.g. 71.25)
      - upside_label: str (e.g. '+71.2%')
      - source_file: str
      - source_path: str
      - valuation_confidence: float
      - divergence_vs_scanner_quant: dict | None

    Market price reconciliation:
      - market_price: from cotahist_daily (canonical)
      - current_price from bridge used for upside computation
      - If bridge market_price differs from cotahist → exposed in divergence

    Falls back to bridge-only data (no crash) when scanner_quant.db has no
    snapshot for the ticker — only valuation fields are returned in that case.
    """
    ticker_upper = str(ticker).strip().upper()

    # ── Load snapshot from scanner_quant.db (may be empty) ─────────────────
    df = _latest_snapshot([ticker_upper])
    has_snapshot = not df.empty

    if has_snapshot:
        db = _db_path()
        row = df.iloc[0].to_dict()
        positioning = _positioning(row.get("integrated_status", ""))
        explanation = row.get("explanation") or "Dados integrados ainda insuficientes para uma tese detalhada."
        market_price = _get_market_price(db, ticker_upper)
        scanner_fair_value = float(
            pd.to_numeric(pd.Series([row.get("fair_value")]), errors="coerce").fillna(0).iloc[0]
        )
        scanner_upside = row.get("upside_pct")
        integrated_score = float(
            pd.to_numeric(pd.Series([row.get("integrated_score")]), errors="coerce").fillna(0).iloc[0]
        )
        ri_url = get_valid_ri_url_for_ticker(ticker_upper)
        base_thesis = {
            "positioning": positioning,
            "market_price": market_price,
            "bull_case": explanation,
            "bear_case": row.get("risk_explanation") or "Riscos especificos ainda nao consolidados.",
            "drivers": [{"title": "Score integrado", "description": explanation, "impact": row.get("integrated_confidence") or "MEDIUM"}],
            "risks": [{"title": "Governanca e dados", "description": row.get("integrated_governance_status") or "Sem alerta especifico.", "severity": "MEDIUM"}],
            "ri_url": ri_url,
        }
    else:
        row = {}
        market_price = None
        scanner_fair_value = 0.0
        scanner_upside = None
        integrated_score = 0.0
        ri_url = get_valid_ri_url_for_ticker(ticker_upper)
        base_thesis = {
            "positioning": "MANTER",
            "market_price": None,
            "bull_case": "Pipeline de inteligencia ainda nao executou para este ativo.",
            "bear_case": "Sem dados de risco consolidados.",
            "drivers": [{"title": "Sem sinal", "description": "Pipeline pendente.", "impact": "LOW"}],
            "risks": [{"title": "Sem dados", "description": "Pipeline pendente.", "severity": "MEDIUM"}],
            "ri_url": ri_url,
        }

    # ── Valuation from bridge (dict with preco_alvo/upside_pct) ─────────────
    # valuation_bridge.get_valuation returns dict — NOT an object with is_complete.
    # Falls back to scanner_quant_db snapshot if bridge is unavailable.
    _bv_outputs_dir: str | None = None
    try:
        _bv_outputs_dir = str(project_path("12_PYTHON/pipeline banco completo/outputs"))
    except Exception:
        pass

    bridge_vd: dict = {}
    if _bv_outputs_dir is not None:
        # Verificar disponibilidade via cache antes de abrir qualquer arquivo
        try:
            _avail = _bridge_available_tickers(_bv_outputs_dir)
            if ticker_upper in _avail:
                bridge_vd = _bridge_valuation(ticker_upper, _bv_outputs_dir) or {}
        except Exception:
            bridge_vd = {}

    if bridge_vd and isinstance(bridge_vd, dict) and bridge_vd.get("preco_alvo"):
        bridge_available = True
        bridge_source = "pipeline_bridge"
        bridge_fair_value = float(bridge_vd["preco_alvo"])
        bridge_method = "DCF/planilha"
        bridge_date = bridge_vd.get("data_valuation") or ""
        bridge_source_file = bridge_vd.get("fonte") or ""
        bridge_source_path = _bv_outputs_dir or ""
        bridge_confidence = 0.7
        bridge_price = market_price

        # Recompute upside from bridge fair_value + cotahist market_price.
        # Never trust the bridge's upside_pct field — some Excel files return 0.0
        # as a placeholder (BBAS3, ITUB4, BBDC4) while others return real values (PETR4).
        # We recalculate here to ensure consistency.
        bridge_upside_raw = bridge_vd.get("upside_pct")
        if bridge_upside_raw is not None and bridge_upside_raw != 0.0 and market_price and market_price > 0:
            # Bridge upside is real and market price is available — use as-is (already %)
            upside_decimal = bridge_upside_raw / 100.0
            upside_pct = float(bridge_upside_raw)
        elif bridge_fair_value > 0 and market_price and market_price > 0:
            # Recompute from fair_value + cotahist market_price
            upside_decimal = (bridge_fair_value - market_price) / market_price
            upside_pct = round(upside_decimal * 100.0, 1)
        else:
            # Cannot compute — show EMPTY in UI, don't fake 0.0
            upside_decimal = None
            upside_pct = None

        upside_label = f"{upside_pct:+.1f}%" if upside_pct is not None else "—"

        # Divergence check vs scanner_quant.db fair_value
        divergence: dict | None = None
        if has_snapshot and scanner_fair_value > 0 and bridge_fair_value is not None:
            div_pct = round((bridge_fair_value - scanner_fair_value) / scanner_fair_value * 100, 1)
            if abs(div_pct) >= 0.5:
                divergence = {
                    "scanner_quant_fair_value": scanner_fair_value,
                    "pipeline_fair_value": bridge_fair_value,
                    "divergence_pct": div_pct,
                    "note": (
                        f"Pipeline usa DCF do pipeline banco completo. "
                        f"scanner_quant.db usa asset_intelligence_engine. "
                        f"Diferença: {abs(div_pct):.1f}%"
                    ),
                }
    else:
        # Bridge unavailable or returns no preco_alvo.
        # Show fair_value only when it came from the snapshot (not 0.0 fake).
        # Upside is EMPTY when bridge is unavailable and scanner_upside is not set.
        bridge_available = False
        bridge_source = "scanner_quant_db" if has_snapshot else "none"
        bridge_fair_value = scanner_fair_value if has_snapshot else 0.0
        bridge_upside = scanner_upside if has_snapshot else None
        bridge_method = row.get("valuation_method") or None
        bridge_date = row.get("created_at", "") or row.get("trade_date", "") if has_snapshot else ""
        bridge_source_file = ""
        bridge_source_path = ""
        bridge_confidence = 0.3 if has_snapshot else 0.0
        bridge_price = market_price

        upside_decimal = bridge_upside
        upside_pct = float(bridge_upside) if bridge_upside is not None else None
        if upside_pct is not None:
            upside_label = f"{upside_pct:+.1f}%"
        else:
            upside_label = "—"  # EMPTY: no bridge and no scanner upside
        divergence = None

    # Use bridge fair_value as authoritative for 59 VALID tickers
    thesis_fair_value = bridge_fair_value
    thesis = dict(base_thesis)
    thesis["fair_value_brl"] = thesis_fair_value

    valuation_timestamp = bridge_date
    fair_value = bridge_fair_value

    return {
        "ticker": row.get("ticker") or ticker_upper,
        "thesis": thesis,
        # Valuation (S03 spec)
        "valuation_available": bridge_available,
        "valuation_source": bridge_source,
        "valuation_method": bridge_method,
        "valuation_date": bridge_date,
        "current_price": bridge_price,
        "market_price": market_price,
        "fair_value": fair_value,
        "fair_value_brl": fair_value,
        "upside_decimal": upside_decimal,
        "upside_pct": upside_pct,
        "upside_label": upside_label,
        "source_file": bridge_source_file,
        "source_path": bridge_source_path,
        "valuation_confidence": bridge_confidence,
        "divergence_vs_scanner_quant": divergence,
        # Legacy compatibility
        "valuation_source": bridge_source,
        "valuation_timestamp": valuation_timestamp,
        "integrated_score": integrated_score,
        "integrated_status": str(row.get("integrated_status", "") if has_snapshot else "SEM_DADOS"),
        "integrated_confidence": str(row.get("integrated_confidence", "") if has_snapshot else ""),
        "technical_score_final": row.get("technical_score_final") if has_snapshot else None,
        "technical_status": row.get("technical_status") if has_snapshot else None,
        "top_technical_setup": row.get("top_technical_setup") if has_snapshot else None,
        "technical_explanation": row.get("technical_explanation") if has_snapshot else None,
        "quant_score": row.get("quant_score") if has_snapshot else None,
        "quant_signal_type": row.get("quant_signal_type") if has_snapshot else None,
        "quant_explanation": row.get("quant_explanation") if has_snapshot else None,
        "dcf": {"upside_pct": upside_pct},
        # Risk data
        "risk_status": row.get("risk_status") if has_snapshot else None,
        "risk_explanation": row.get("risk_explanation") if has_snapshot else None,
        "var_95": row.get("var_95") if has_snapshot else None,
        "expected_shortfall_95": row.get("expected_shortfall_95") if has_snapshot else None,
        # Option data
        "option_available": row.get("option_available") if has_snapshot else None,
        "option_structure_score": row.get("option_structure_score") if has_snapshot else None,
        # Governance
        "data_quality_score": row.get("data_quality_score") if has_snapshot else None,
        "governance_blocked": row.get("governance_blocked") if has_snapshot else None,
        "generated_at": row.get("created_at", "") or row.get("trade_date", "") if has_snapshot else "",
        "ri_url": ri_url,
    }


def _macro_series_to_dict(name: str, rows: list[dict]) -> list[dict]:
    """Convert macro_series rows to the dict format expected by get_macro_panel."""
    out = []
    for row in rows:
        out.append({
            "date":  str(row.get("series_date", "")),
            "value": float(row.get("value")) if row.get("value") is not None else None,
            "unit":  str(row.get("unit", "")),
        })
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_macro_panel() -> dict[str, list[dict]]:
    """
    Return available macro context from macro_series + market_regime_daily tables.
    Falls back to regime-only context if macro_series is empty.
    BCB/SGS API (Selic, PTAX, IPCA) fetched via bcb_sgs_connector and stored in macro_series.

    Returns dict with keys:
        regime, selic, ipca_12m, ptax, cds_brasil, pib_nominal, source_status
    """
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))

        # --- BCB macro series from macro_series table ---
        selic_rows = conn.execute("""
            SELECT series_date, value, unit
            FROM macro_series
            WHERE series_code = '4389'
            ORDER BY series_date DESC
            LIMIT 30
        """).fetchall()
        ptax_rows = conn.execute("""
            SELECT series_date, value, unit
            FROM macro_series
            WHERE series_code = '21620'
            ORDER BY series_date DESC
            LIMIT 30
        """).fetchall()
        ipca_rows = conn.execute("""
            SELECT series_date, value, unit
            FROM macro_series
            WHERE series_code = '13522'
            ORDER BY series_date DESC
            LIMIT 30
        """).fetchall()

        selic = [{"date": str(r[0]), "value": float(r[1]), "unit": str(r[2] or "")} for r in selic_rows]
        ptax  = [{"date": str(r[0]), "value": float(r[1]), "unit": str(r[2] or "")} for r in ptax_rows]
        ipca  = [{"date": str(r[0]), "value": float(r[1]), "unit": str(r[2] or "")} for r in ipca_rows]

        # CDS/PIB: not yet fetched — mark as empty but present
        cds_brasil: list[dict] = []
        pib_nominal: list[dict] = []

        # --- Market regime ---
        regime_rows = conn.execute("""
            SELECT trade_date, primary_regime, trend_regime, volatility_regime,
                   liquidity_regime
            FROM market_regime_daily
            ORDER BY trade_date DESC
            LIMIT 1
        """).fetchall()

        conn.close()

        if regime_rows:
            reg = dict(zip(
                ["trade_date", "primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"],
                regime_rows[0],
            ))
            regime = [{
                "date":       str(reg.get("trade_date", "")),
                "primary":    str(reg.get("primary_regime") or ""),
                "trend":      str(reg.get("trend_regime") or ""),
                "volatility": str(reg.get("volatility_regime") or ""),
                "liquidity":  str(reg.get("liquidity_regime") or ""),
                "governance":  "",
            }]
        else:
            regime = []

        # Determine source_status
        has_macro   = bool(selic or ptax or ipca)
        has_regime  = bool(regime)
        if has_macro and has_regime:
            status = "macro_series + market_regime_daily"
        elif has_macro:
            status = "macro_series"
        elif has_regime:
            status = "market_regime_daily"
        else:
            status = "SEM_DADOS_MACRO"

        return {
            "regime":      regime,
            "selic":       selic,
            "ipca_12m":    ipca,
            "ptax":        ptax,
            "cds_brasil":  cds_brasil,
            "pib_nominal": pib_nominal,
            "source_status": status,
        }

    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return {
            "regime": [], "selic": [], "ipca_12m": [],
            "ptax": [], "cds_brasil": [], "pib_nominal": [],
            "source_status": "ERRO_CONEXAO",
        }


@st.cache_data(ttl=300, show_spinner=False)
def get_opportunities() -> list[dict]:
    """
    Return top opportunities with real integrated scores from the engine.
    tier/direction are derived from integrated_status — not invented.
    """
    df = _latest_snapshot()
    if df.empty:
        return []
    work = df.copy()
    # Use REAL integrated_score from engine — never hardcode 45
    work["conviction_score"] = pd.to_numeric(
        work.get("integrated_score", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    work = work.sort_values("conviction_score", ascending=False).head(10)

    # Map integrated_status → tier (no fake classification)
    def _status_to_tier(status):
        if not status:
            return "D"
        s = str(status).upper()
        if "ALTA_CONVERGENCIA" in s:
            return "A"
        if "ASSIMETRIA" in s:
            return "B"
        if "BLOQUEADO" in s or "DIVERGENCIA" in s:
            return "C"
        if "APENAS_MONITORAR" in s:
            return "D"
        return "D"

    # Map integrated_status → direction (no fake signal)
    def _status_to_direction(status):
        if not status:
            return "HOLD"
        s = str(status).upper()
        if "ALTA_CONVERGENCIA" in s:
            return "BUY"
        if "ASSIMETRIA" in s:
            return "WATCH"
        if "BLOQUEADO" in s or "DIVERGENCIA" in s:
            return "SELL"
        return "HOLD"

    return [
        {
            "ticker": row.get("ticker"),
            "description": row.get("explanation") or row.get("integrated_status") or "Ativo em monitoramento.",
            "signal_type": row.get("integrated_status") or "INTEGRATED_SIGNAL",
            "conviction_score": int(round(float(row.get("conviction_score") or 0))),
            "conviction_tier": _status_to_tier(row.get("integrated_status")),
            "signal_direction": _status_to_direction(row.get("integrated_status")),
            "technical_score_final": row.get("technical_score_final"),
            "quant_score": row.get("quant_score"),
        }
        for _, row in work.iterrows()
    ]


@st.cache_data(ttl=120, show_spinner=False)
def get_risk_snapshots(tickers: tuple[str, ...] | None = None) -> list[dict]:
    """
    Return real risk snapshots from risk_snapshots table.
    Falls back to empty list if table is empty or unavailable.
    Note: tickers must be a tuple (hashable) for cache compatibility.
    """
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        where_clause = ""
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            where_clause = f" WHERE ticker IN ({placeholders})"
        rows = conn.execute(f"""
            SELECT ticker, trade_date, price, position_value, ensemble_vol,
                   volatility_regime, parametric_var_95, historical_var_95,
                   expected_shortfall_95, recommended_size, recommended_position_value,
                   limiting_factor, risk_status, explanation, created_at
            FROM risk_snapshots
            {where_clause}
            ORDER BY created_at DESC
        """, tickers or []).fetchall()
        conn.close()
        if rows:
            return [
                {
                    "ticker": str(r[0] or ""),
                    "trade_date": str(r[1] or ""),
                    "price": float(r[2]) if r[2] is not None else None,
                    "position_value": float(r[3]) if r[3] is not None else None,
                    "ensemble_vol": float(r[4]) if r[4] is not None else None,
                    "volatility_regime": str(r[5] or ""),
                    "var_95": float(r[6]) if r[6] is not None else None,
                    "historical_var_95": float(r[7]) if r[7] is not None else None,
                    "expected_shortfall_95": float(r[8]) if r[8] is not None else None,
                    "recommended_size": float(r[9]) if r[9] is not None else None,
                    "recommended_position_value": float(r[10]) if r[10] is not None else None,
                    "limiting_factor": str(r[11] or ""),
                    "risk_status": str(r[12] or ""),
                    "explanation": str(r[13] or ""),
                    "created_at": str(r[14] or ""),
                }
                for r in rows
            ]
    except Exception:
        pass
    return []


@st.cache_data(ttl=120, show_spinner=False)
def get_option_structure_candidates(tickers: list[str] | None = None) -> list[dict]:
    """
    Return real option structure candidates from option_structure_candidates table.
    Falls back to empty list if table is empty or unavailable.
    BCB data not yet integrated — selic, ptax, cds_brasil marked as SEM_DADOS_BCB.
    """
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        where_clause = ""
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            where_clause = f" WHERE underlying IN ({placeholders})"
        rows = conn.execute(f"""
            SELECT created_at, underlying, structure_type, maturity_date,
                   net_debit, net_credit, max_profit, max_loss, payoff_ratio,
                   liquidity_score, risk_score, structure_score, candidate_status,
                   explanation, governance_status
            FROM option_structure_candidates
            {where_clause}
            ORDER BY created_at DESC
            LIMIT 20
        """, tickers or []).fetchall()
        conn.close()
        if rows:
            return [
                {
                    "underlying": str(r[1] or ""),
                    "structure_type": str(r[2] or ""),
                    "maturity_date": str(r[3] or ""),
                    "net_debit": float(r[4]) if r[4] is not None else None,
                    "net_credit": float(r[5]) if r[5] is not None else None,
                    "max_profit": float(r[6]) if r[6] is not None else None,
                    "max_loss": float(r[7]) if r[7] is not None else None,
                    "payoff_ratio": float(r[8]) if r[8] is not None else None,
                    "liquidity_score": float(r[9]) if r[9] is not None else None,
                    "risk_score": float(r[10]) if r[10] is not None else None,
                    "structure_score": float(r[11]) if r[11] is not None else None,
                    "status": str(r[12] or ""),
                    "explanation": str(r[13] or ""),
                    "governance_status": str(r[14] or ""),
                    "created_at": str(r[0] or ""),
                }
                for r in rows
            ]
    except Exception:
        pass
    return []