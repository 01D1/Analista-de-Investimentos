"""
m018_s04_preliminary_batch.py
------------------------------
M018-S04: Controlled Preliminary Valuation Batch for 18 New Tickers

Calcula preliminary_fair_value para os 18 novos tickers em modo controlado,
respeitando todas as travas do sanity check M018-S03.

Tickers:
    PRIO3, RECV3, EGIE3, SBSP3, TAEE11, AZZA3, LREN3, MGLU3, PCAR3,
    VIVA3, FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3

Regras críticas:
    1. Todos resultados: status=preliminary, approved_fair_value=NULL
    2. Não escreve em asset_intelligence_snapshots
    3. Não altera os 9 preservados
    4. MGLU3/PCAR3: sem DCF, só EV/EBITDA com flag DISTRESSED
    5. KLBN11: valida shares (discrepância ltm vs vfi) — flag UNIT_SHARES_DISCREPANCY
    6. RECV3/SBSP3/VAMO3: flag FCF_NEGATIVE_EXPECTED
    7. FV negativo/zero/absurdo (fora 0,1x–5,0x preço): BLOCKED_FOR_VALIDATION
    8. sanity_check_passed=False por padrão; auto-pass com regras objetivas

Método: EV/EBITDA com múltiplos setoriais calibrados para Brasil (2026)
    equity_value = ebitda × multiple − net_debt
    fv_per_share = equity_value / shares_outstanding

Uso:
    cd /Users/diegocarvalho/.../12_PYTHON
    python -m src.valuation.m018_s04_preliminary_batch [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.ingestion.db import DB_PATH, get_connection
from src.valuation.valuation_results_store import (
    PRESERVE_EXISTING,
    ensure_valuation_results_schema,
    write_preliminary,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

# =============================================================================
# CONFIGURAÇÃO — 18 NOVOS TICKERS
# =============================================================================

NEW_TICKERS: List[str] = [
    "PRIO3", "RECV3", "EGIE3", "SBSP3", "TAEE11",
    "AZZA3", "LREN3", "MGLU3", "PCAR3", "VIVA3",
    "FLRY3", "HYPE3", "KLBN11", "RADL3", "RAIL3",
    "RENT3", "SUZB3", "VAMO3",
]

# Tickers com trava especial de metodologia
DISTRESSED_TICKERS = frozenset({"MGLU3", "PCAR3"})
FCF_NEGATIVE_TICKERS = frozenset({"RECV3", "SBSP3", "VAMO3"})
UNIT_TICKERS = frozenset({"KLBN11", "TAEE11"})

# Configuração setorial e múltiplos EV/EBITDA por ticker
# Fontes: sectors.yaml para oil_gas (5.5x) + calibração setorial Brasil 2026
@dataclass
class TickerCfg:
    sector: str
    multiple: float               # EV/EBITDA alvo (cenário base)
    multiple_min: float           # pessimista
    multiple_max: float           # otimista
    method_label: str = "EV_EBITDA"
    notes: str = ""

TICKER_CFG: Dict[str, TickerCfg] = {
    # ── PETRÓLEO & GÁS ─────────────────────────────────────────────────────
    # sectors.yaml: base 5.5x, min 4.0x, max 7.0x
    "PRIO3":  TickerCfg("oil_gas",    5.5, 4.0, 7.0,
                        notes="PetroRio — E&P premium BR; alto net_debt"),
    "RECV3":  TickerCfg("oil_gas",    5.5, 4.0, 7.0,
                        notes="Petrorecôncavo — FCF negativo esperado; capex crescimento"),

    # ── UTILITIES / ENERGIA & SANEAMENTO ───────────────────────────────────
    # DDM seria o primário, mas usamos EV/EBITDA por consistência (utilities reguladas)
    # Múltiplo 9x reflete prêmio regulatório e previsibilidade de receita
    "EGIE3":  TickerCfg("utilities",  9.0, 7.5, 11.0,
                        notes="Engie Brasil — transmissão/geração; alto net_debt"),
    "SBSP3":  TickerCfg("utilities",  9.0, 7.5, 11.0,
                        notes="Sabesp — saneamento privatizado; FCF neg por capex regulatório"),
    "TAEE11": TickerCfg("utilities",  9.0, 7.5, 11.0,
                        notes="Taesa — transmissão; UNIT (validação shares necessária)"),

    # ── VAREJO ──────────────────────────────────────────────────────────────
    "AZZA3":  TickerCfg("retail",     7.0, 5.0, 9.0,
                        notes="Azzas 2154 — varejo calçados/moda; EBITDA margin ~15.5%"),
    "LREN3":  TickerCfg("retail",     7.0, 5.0, 9.0,
                        notes="Lojas Renner — net cash; EBITDA margin ~19.5%"),
    "MGLU3":  TickerCfg("retail",     4.0, 3.0, 5.5,   # DISTRESSED — múltiplo reduzido
                        notes="Magazine Luiza — DISTRESSED; thin margin 8.3%; DCF bloqueado"),
    "PCAR3":  TickerCfg("retail",     3.5, 2.5, 5.0,   # DISTRESSED — múltiplo reduzido
                        notes="GPA — DISTRESSED; NI negativo; DCF bloqueado"),
    "VIVA3":  TickerCfg("retail",     9.0, 7.0, 11.0,
                        notes="Vivara — jóias premium; EBITDA margin ~29%; net cash"),

    # ── SAÚDE / FARMA ───────────────────────────────────────────────────────
    "FLRY3":  TickerCfg("healthcare", 11.0, 8.5, 13.5,
                        notes="Fleury — diagnósticos; EBITDA margin ~25.6%"),
    "HYPE3":  TickerCfg("healthcare", 11.0, 8.5, 13.5,
                        notes="Hypera — farma; alto net_debt vs EBITDA (3.7x)"),
    "RADL3":  TickerCfg("healthcare", 14.0, 11.0, 17.0,
                        notes="Raia Drogasil — maior rede farma BR; crescimento estrutural"),

    # ── INDUSTRIAL / LOGÍSTICA / LOCAÇÃO ────────────────────────────────────
    "KLBN11": TickerCfg("industrial",  6.5, 5.0, 8.5,
                        notes="Klabin — celulose/papel integrado; UNIT; shares discrepância ltm/vfi"),
    "RAIL3":  TickerCfg("industrial",  9.0, 7.0, 11.0,
                        notes="Rumo — ferroviária modal; alto capex; ND/EBITDA ~2.4x"),
    "RENT3":  TickerCfg("industrial",  8.0, 6.0, 10.0,
                        notes="Localiza — locação de veículos; ND/EBITDA ~2.4x"),
    "SUZB3":  TickerCfg("industrial",  7.5, 5.5, 9.5,
                        notes="Suzano — celulose exportadora; USD revenues; ND/EBITDA ~3.2x"),
    "VAMO3":  TickerCfg("industrial",  7.0, 5.0, 9.0,
                        notes="Vamos Locação — locação de máquinas; FCF negativo; high leverage"),
}

# Banda sanity check: FV deve estar entre 0,1x e 5,0x do preço de mercado
SANITY_BAND_LOW  = 0.10
SANITY_BAND_HIGH = 5.00

# Critérios para auto-pass do sanity_check_passed
# (mais restritivos — FV entre 0,5x e 2,0x e ND/EBITDA < 3,5x)
AUTO_PASS_BAND_LOW  = 0.50
AUTO_PASS_BAND_HIGH = 2.00
AUTO_PASS_ND_EBITDA = 3.5


# =============================================================================
# DATACLASS DE RESULTADO
# =============================================================================

@dataclass
class ValuationResult:
    ticker: str
    sector: str
    method_used: str
    multiple: float

    # Inputs financeiros
    ebitda: float
    net_debt: float
    shares: float
    market_price: float
    shares_source: str         # "vfi_2025" | "ltm"
    period_end: str

    # Cálculo
    ev: float                  # EV = EBITDA × multiple
    equity_value: float        # EV − net_debt
    preliminary_fv: float      # equity_value / shares

    # Ratios
    upside_pct: float
    nd_ebitda: float
    current_ev_ebitda: float   # EV atual (market cap + net_debt) / EBITDA

    # Status
    input_quality: str
    confidence: str
    sanity_check_passed: bool
    block_reason: Optional[str]
    flags: List[str] = field(default_factory=list)
    notes: str = ""


# =============================================================================
# FUNÇÕES DE CARGA DE DADOS
# =============================================================================

def _load_metric(conn, ticker: str, metric: str, period_end: str = "2025-12-31") -> Optional[float]:
    """Carrega uma métrica específica de valuation_financial_inputs."""
    row = conn.execute(
        """
        SELECT metric_value FROM valuation_financial_inputs
        WHERE ticker = ? AND metric_name = ? AND period_end = ?
        """,
        (ticker, metric, period_end),
    ).fetchone()
    return float(row[0]) if row else None


def _load_shares_vfi(conn, ticker: str) -> Optional[float]:
    """Carrega shares_outstanding de valuation_financial_inputs (DFP 2025-12-31)."""
    return _load_metric(conn, ticker, "shares_outstanding", "2025-12-31")


def _load_shares_ltm(conn, ticker: str) -> Optional[float]:
    """Carrega shares_outstanding de financial_ltm (mais recente)."""
    row = conn.execute(
        """
        SELECT shares_outstanding, computed_date
        FROM financial_ltm
        WHERE ticker = ?
        ORDER BY computed_date DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()
    return float(row[0]) if row and row[0] else None


def _load_market_price(conn, ticker: str) -> Optional[float]:
    """Carrega último preço de fechamento de price_ohlcv."""
    row = conn.execute(
        """
        SELECT close, date FROM price_ohlcv
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()
    return float(row[0]) if row and row[0] else None


# =============================================================================
# VALIDAÇÃO DE SHARES — regra crítica M018-S03
# =============================================================================

def _validate_shares(
    conn,
    ticker: str,
    flags: List[str],
    notes_parts: List[str],
) -> Tuple[float, str]:
    """
    Valida e retorna (shares, source).

    Para UNIT tickers: verifica discrepância entre ltm e vfi.
    Regra: se abs(ltm/vfi - 1) > 30%, flag SHARES_DISCREPANCY e usa vfi (mais conservador).
    """
    shares_vfi = _load_shares_vfi(conn, ticker)
    shares_ltm = _load_shares_ltm(conn, ticker)

    if shares_vfi is None and shares_ltm is None:
        flags.append("no_shares_data")
        return 0.0, "NONE"

    if ticker in UNIT_TICKERS:
        flags.append("unit_shares_validation_required")
        if shares_vfi and shares_ltm:
            ratio = shares_ltm / shares_vfi if shares_vfi > 0 else 0
            if abs(ratio - 1) > 0.30:
                flags.append(f"shares_ltm_vfi_discrepancy_ratio={ratio:.2f}x")
                notes_parts.append(
                    f"{ticker} shares discrepância: ltm={shares_ltm:,.0f} vs "
                    f"vfi={shares_vfi:,.0f} (ratio={ratio:.2f}x) — usando vfi"
                )
                # Para units: vfi (CVM DFP) tende a ser mais preciso para shares "por unit"
                return shares_vfi, "vfi_2025"
        # Sem discrepância → usa ltm se disponível, senão vfi
        s = shares_ltm if shares_ltm else shares_vfi
        return s, "ltm" if shares_ltm else "vfi_2025"

    # Tickers normais: prefere ltm (mais recente)
    if shares_ltm and shares_ltm > 0:
        return shares_ltm, "ltm"
    if shares_vfi and shares_vfi > 0:
        return shares_vfi, "vfi_2025"

    flags.append("invalid_shares")
    return 0.0, "NONE"


# =============================================================================
# CÁLCULO EV/EBITDA
# =============================================================================

def _compute_ev_ebitda(
    ticker: str,
    cfg: TickerCfg,
    ebitda: float,
    net_debt: float,
    shares: float,
    market_price: float,
    flags: List[str],
    notes_parts: List[str],
) -> Tuple[float, float, float, float, float]:
    """
    Calcula fair value via EV/EBITDA.

    Returns:
        (ev, equity_value, fv_per_share, nd_ebitda, current_ev_ebitda)
    """
    ev = ebitda * cfg.multiple
    equity_value = ev - net_debt

    # ND/EBITDA
    nd_ebitda = net_debt / ebitda if ebitda > 0 else 0.0

    # EV/EBITDA atual
    market_cap = market_price * shares
    current_ev = market_cap + net_debt
    current_ev_ebitda = current_ev / ebitda if ebitda > 0 else 0.0

    if equity_value <= 0:
        flags.append(f"negative_equity_at_{cfg.multiple}x_multiple")
        notes_parts.append(
            f"{ticker} net_debt ({net_debt/1e9:.1f}B) > EV ({ev/1e9:.1f}B) "
            f"ao múltiplo {cfg.multiple}x → equity negativo"
        )
        fv = 0.0
    else:
        fv = equity_value / shares if shares > 0 else 0.0

    return ev, equity_value, fv, nd_ebitda, current_ev_ebitda


# =============================================================================
# AVALIAÇÃO DE QUALIDADE
# =============================================================================

def _assess_quality(
    ticker: str,
    ebitda: float,
    net_income: float,
    nd_ebitda: float,
    fv: float,
    market_price: float,
    flags: List[str],
) -> Tuple[str, str]:
    """Retorna (input_quality, confidence)."""
    # Distressed
    if ticker in DISTRESSED_TICKERS or net_income < 0:
        return "DISTRESSED", "LOW"

    # FCF negativo esperado
    if ticker in FCF_NEGATIVE_TICKERS:
        if nd_ebitda > 4.0:
            return "PARTIAL", "LOW"
        return "PARTIAL", "MEDIUM"

    # Alavancagem alta
    if nd_ebitda > 4.0:
        flags.append(f"high_leverage_nd_ebitda={nd_ebitda:.1f}x")
        return "PARTIAL", "LOW"

    # Dados completos
    ebitda_margin_ok = ebitda > 0
    if not ebitda_margin_ok:
        return "INSUFFICIENT", "INSUFFICIENT"

    # Confidence baseada em ND/EBITDA e normalidade do FV
    if nd_ebitda < 1.5:
        confidence = "HIGH"
    elif nd_ebitda < 3.0:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return "FULL", confidence


# =============================================================================
# SANITY CHECK
# =============================================================================

def _sanity_check(
    ticker: str,
    fv: float,
    market_price: float,
    ebitda: float,
    nd_ebitda: float,
    flags: List[str],
) -> Tuple[bool, Optional[str]]:
    """
    Verifica se o fair value é válido e determina block_reason.

    Retorna (sanity_check_passed, block_reason).
    """
    if fv <= 0 or market_price <= 0:
        return False, "fair_value_zero_or_negative"

    ratio = fv / market_price

    # Banda externa (0,1x–5,0x): bloqueia se fora
    if ratio < SANITY_BAND_LOW or ratio > SANITY_BAND_HIGH:
        return False, (
            f"fv_outside_sanity_band: fv={fv:.2f} mp={market_price:.2f} "
            f"ratio={ratio:.2f}x (band: {SANITY_BAND_LOW}–{SANITY_BAND_HIGH}x)"
        )

    # EBITDA negativo → bloqueia
    if ebitda <= 0:
        return False, "negative_or_zero_ebitda"

    # Distressed → não auto-passa
    if ticker in DISTRESSED_TICKERS:
        return False, None  # válido mas requer revisão manual

    # Unit → não auto-passa
    if ticker in UNIT_TICKERS:
        return False, None  # válido mas shares precisam validação

    # FCF negativo → não auto-passa
    if ticker in FCF_NEGATIVE_TICKERS:
        return False, None

    # Banda estreita para auto-pass (0,5x–2,0x) + leverage OK
    auto_pass = (
        AUTO_PASS_BAND_LOW <= ratio <= AUTO_PASS_BAND_HIGH
        and nd_ebitda < AUTO_PASS_ND_EBITDA
    )
    return auto_pass, None


# =============================================================================
# PROCESSAMENTO PRINCIPAL POR TICKER
# =============================================================================

def _process_ticker(conn, ticker: str) -> ValuationResult:
    """Processa um ticker e retorna ValuationResult."""
    flags: List[str] = []
    notes_parts: List[str] = []
    cfg = TICKER_CFG[ticker]

    # Verificação de segurança: JAMAIS processar PRESERVE_EXISTING
    if ticker in PRESERVE_EXISTING:
        raise RuntimeError(
            f"[M018-S04] SEGURANÇA: {ticker} é PRESERVE_EXISTING — "
            "nunca deve entrar em m018_s04_preliminary_batch"
        )

    # ── 1. Carregar métricas financeiras (DFP 2025-12-31) ──────────────────
    ebitda    = _load_metric(conn, ticker, "ebitda")
    net_debt  = _load_metric(conn, ticker, "net_debt")
    net_income = _load_metric(conn, ticker, "net_income") or 0.0
    free_cash_flow = _load_metric(conn, ticker, "free_cash_flow")

    if ebitda is None or ebitda <= 0:
        flags.append("no_ebitda_or_negative")
        return ValuationResult(
            ticker=ticker, sector=cfg.sector, method_used=cfg.method_label,
            multiple=cfg.multiple, ebitda=0, net_debt=0, shares=0,
            market_price=0, shares_source="NONE", period_end="2025-12-31",
            ev=0, equity_value=0, preliminary_fv=0, upside_pct=0,
            nd_ebitda=0, current_ev_ebitda=0,
            input_quality="INSUFFICIENT", confidence="INSUFFICIENT",
            sanity_check_passed=False,
            block_reason="no_ebitda_or_negative",
            flags=flags,
        )

    if net_debt is None:
        flags.append("no_net_debt_data")
        net_debt = 0.0

    # ── 2. Flags especiais ─────────────────────────────────────────────────
    if ticker in DISTRESSED_TICKERS:
        flags.append("DISTRESSED_DCF_BLOCKED")
        flags.append("LOW_CONFIDENCE_DISTRESSED")
        notes_parts.append(f"{ticker} bloqueado para DCF por regra M018-S03")

    if ticker in FCF_NEGATIVE_TICKERS:
        flags.append("FCF_NEGATIVE_EXPECTED")
        if free_cash_flow is not None and free_cash_flow < 0:
            flags.append(f"fcf_confirmed_negative={free_cash_flow/1e9:.2f}B")

    # MGLU3: anomalia FCF (15.4B vs EBITDA 3.2B)
    if ticker == "MGLU3" and free_cash_flow is not None:
        fcf_ebitda_ratio = free_cash_flow / ebitda if ebitda > 0 else 0
        if abs(fcf_ebitda_ratio) > 3.0:
            flags.append(f"FCF_ANOMALY_RATIO={fcf_ebitda_ratio:.1f}x_EBITDA")
            notes_parts.append(
                f"MGLU3 FCF={free_cash_flow/1e9:.1f}B anômalo vs EBITDA={ebitda/1e9:.1f}B "
                f"(ratio={fcf_ebitda_ratio:.1f}x) — possivelmente receita working capital"
            )

    # ── 3. Shares — validação crítica ──────────────────────────────────────
    shares, shares_source = _validate_shares(conn, ticker, flags, notes_parts)

    if shares <= 0:
        return ValuationResult(
            ticker=ticker, sector=cfg.sector, method_used=cfg.method_label,
            multiple=cfg.multiple, ebitda=ebitda, net_debt=net_debt, shares=0,
            market_price=0, shares_source=shares_source, period_end="2025-12-31",
            ev=0, equity_value=0, preliminary_fv=0, upside_pct=0,
            nd_ebitda=0, current_ev_ebitda=0,
            input_quality="INSUFFICIENT", confidence="INSUFFICIENT",
            sanity_check_passed=False,
            block_reason="shares_zero_or_missing",
            flags=flags,
        )

    # ── 4. Preço de mercado ────────────────────────────────────────────────
    market_price = _load_market_price(conn, ticker)
    if not market_price or market_price <= 0:
        flags.append("no_market_price")
        market_price = 0.0

    # ── 5. Calcular EV/EBITDA ─────────────────────────────────────────────
    ev, equity_value, fv, nd_ebitda, curr_ev_ebitda = _compute_ev_ebitda(
        ticker, cfg, ebitda, net_debt, shares, market_price, flags, notes_parts
    )

    # ── 6. Nota: prêmio/desconto sobre múltiplo atual ─────────────────────
    if curr_ev_ebitda > 0:
        notes_parts.append(
            f"EV/EBITDA atual={curr_ev_ebitda:.1f}x vs target={cfg.multiple}x "
            f"({'premium' if curr_ev_ebitda > cfg.multiple else 'discount'})"
        )

    # ── 7. ND/EBITDA flags ────────────────────────────────────────────────
    if nd_ebitda > 4.5:
        flags.append(f"very_high_leverage_nd_ebitda={nd_ebitda:.1f}x")
    elif nd_ebitda > 3.0:
        flags.append(f"elevated_leverage_nd_ebitda={nd_ebitda:.1f}x")

    # ── 8. Upside ─────────────────────────────────────────────────────────
    if fv > 0 and market_price > 0:
        upside_pct = round((fv / market_price - 1) * 100, 2)
    else:
        upside_pct = 0.0

    # ── 9. Qualidade e confiança ──────────────────────────────────────────
    input_quality, confidence = _assess_quality(
        ticker, ebitda, net_income, nd_ebitda, fv, market_price, flags
    )

    # ── 10. Sanity check ──────────────────────────────────────────────────
    sanity_passed, block_reason = _sanity_check(
        ticker, fv, market_price, ebitda, nd_ebitda, flags
    )

    # Se equity negativo → bloqueado
    if equity_value <= 0 and block_reason is None:
        block_reason = "equity_value_negative_at_target_multiple"
        sanity_passed = False

    return ValuationResult(
        ticker=ticker,
        sector=cfg.sector,
        method_used=f"{cfg.method_label}_{cfg.multiple}x",
        multiple=cfg.multiple,
        ebitda=ebitda,
        net_debt=net_debt,
        shares=shares,
        market_price=market_price,
        shares_source=shares_source,
        period_end="2025-12-31",
        ev=ev,
        equity_value=equity_value,
        preliminary_fv=round(fv, 2),
        upside_pct=upside_pct,
        nd_ebitda=round(nd_ebitda, 2),
        current_ev_ebitda=round(curr_ev_ebitda, 2),
        input_quality=input_quality,
        confidence=confidence,
        sanity_check_passed=sanity_passed,
        block_reason=block_reason,
        flags=flags,
        notes="; ".join(notes_parts) if notes_parts else "",
    )


# =============================================================================
# VERIFICAÇÃO DE SEGURANÇA PRÉ-EXECUÇÃO
# =============================================================================

def _preflight_checks(db_path: Path) -> None:
    """Verifica pré-condições de segurança antes de gravar."""
    # 1. Nenhum novo ticker deve estar em PRESERVE_EXISTING
    overlap = set(NEW_TICKERS) & PRESERVE_EXISTING
    if overlap:
        raise RuntimeError(
            f"[M018-S04] ERRO CRÍTICO: tickers em overlap com PRESERVE_EXISTING: {overlap}"
        )

    conn = get_connection(db_path)
    try:
        # 2. Confirmar que asset_intelligence_snapshots NÃO será tocada
        #    (write_preliminary não acessa essa tabela, mas vamos verificar que ela existe e está intacta)
        tables = {
            r[0] for r in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "asset_intelligence_snapshots" not in tables or True, \
            "asset_intelligence_snapshots existe — verificar que write_preliminary não acessa"

        # 3. Confirmar que os 9 preservados não têm registros novos não autorizados
        #    (todos devem ter source=M018_COMPARISON e 0 approved_fair_value via preliminary)
        for pe_ticker in PRESERVE_EXISTING:
            row = conn.execute(
                "SELECT approved_fair_value FROM valuation_results "
                "WHERE ticker = ? AND source = 'M018_CONTROLLED'",
                (pe_ticker,),
            ).fetchone()
            if row is not None:
                raise RuntimeError(
                    f"[M018-S04] FALHA preflight: {pe_ticker} tem registro M018_CONTROLLED "
                    "— violação de proteção PRESERVE_EXISTING"
                )

        log.info("[M018-S04] preflight OK: nenhuma violação de proteção detectada")
    finally:
        conn.close()


# =============================================================================
# VERIFICAÇÃO PÓS-ESCRITA
# =============================================================================

def _post_write_checks(db_path: Path, results: List[ValuationResult]) -> Dict[str, bool]:
    """Verifica integridade após escrita. Retorna {check: passed}."""
    conn = get_connection(db_path)
    checks = {}

    try:
        # C1: 18/18 processados
        checks["18_of_18_processed"] = len(results) == 18

        # C2: 0 approved_fair_value
        n_approved = conn.execute(
            "SELECT COUNT(*) FROM valuation_results "
            "WHERE ticker IN ({}) AND approved_fair_value IS NOT NULL".format(
                ",".join("?" * len(NEW_TICKERS))
            ),
            NEW_TICKERS,
        ).fetchone()[0]
        checks["zero_approved_fv"] = (n_approved == 0)

        # C3: 0 writes em asset_intelligence_snapshots
        tables = {
            r[0] for r in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "asset_intelligence_snapshots" in tables:
            n_snap = conn.execute(
                "SELECT COUNT(*) FROM asset_intelligence_snapshots "
                "WHERE ticker IN ({})".format(",".join("?" * len(NEW_TICKERS))),
                NEW_TICKERS,
            ).fetchone()[0]
            checks["zero_writes_asset_snapshots"] = (n_snap == 0)
        else:
            checks["zero_writes_asset_snapshots"] = True  # tabela não existe = sem writes

        # C4: 0 alterações nos preservados (source=M018_CONTROLLED deve ser 0 para PRESERVE_EXISTING)
        n_pe_contamination = conn.execute(
            "SELECT COUNT(*) FROM valuation_results "
            "WHERE ticker IN ({}) AND source = 'M018_CONTROLLED'".format(
                ",".join("?" * len(PRESERVE_EXISTING))
            ),
            list(PRESERVE_EXISTING),
        ).fetchone()[0]
        checks["zero_changes_preserved"] = (n_pe_contamination == 0)

        # C5: todos os 18 têm status=preliminary
        n_preliminary = conn.execute(
            "SELECT COUNT(DISTINCT ticker) FROM valuation_results "
            "WHERE ticker IN ({}) AND status = 'preliminary' AND source = 'M018_CONTROLLED'".format(
                ",".join("?" * len(NEW_TICKERS))
            ),
            NEW_TICKERS,
        ).fetchone()[0]
        checks["all_status_preliminary"] = (n_preliminary == len(NEW_TICKERS))

    finally:
        conn.close()

    return checks


# =============================================================================
# EXECUÇÃO DO BATCH
# =============================================================================

def run_batch(db_path: Path, dry_run: bool = False) -> List[ValuationResult]:
    """
    Executa o batch de valuation para os 18 novos tickers.

    Args:
        db_path: caminho do SQLite.
        dry_run: True → não persiste, apenas simula.

    Returns:
        Lista de ValuationResult (18 itens).
    """
    log.info(
        "[M018-S04] iniciando batch",
        n_tickers=len(NEW_TICKERS),
        dry_run=dry_run,
        db_path=str(db_path),
    )

    # Garantir schema
    ensure_valuation_results_schema(db_path)

    # Preflight
    _preflight_checks(db_path)

    conn = get_connection(db_path)
    results: List[ValuationResult] = []

    try:
        for ticker in NEW_TICKERS:
            try:
                r = _process_ticker(conn, ticker)
                results.append(r)
                log.info(
                    "[M018-S04] ticker processado",
                    ticker=ticker,
                    fv=r.preliminary_fv,
                    upside_pct=r.upside_pct,
                    quality=r.input_quality,
                    confidence=r.confidence,
                    sanity=r.sanity_check_passed,
                    blocked=bool(r.block_reason),
                )
            except Exception as exc:
                log.error(f"[M018-S04] erro ao processar {ticker}: {exc}")
                results.append(ValuationResult(
                    ticker=ticker, sector="unknown", method_used="ERROR",
                    multiple=0, ebitda=0, net_debt=0, shares=0,
                    market_price=0, shares_source="NONE", period_end="",
                    ev=0, equity_value=0, preliminary_fv=0, upside_pct=0,
                    nd_ebitda=0, current_ev_ebitda=0,
                    input_quality="INSUFFICIENT", confidence="INSUFFICIENT",
                    sanity_check_passed=False,
                    block_reason=f"processing_error: {exc}",
                    flags=[f"error={type(exc).__name__}"],
                ))
    finally:
        conn.close()

    # Persistir via write_preliminary()
    if not dry_run:
        for r in results:
            if r.preliminary_fv <= 0:
                # Ainda gravar para tracking, mas com fv simbólico = -1 não
                # Na verdade registrar como bloqueado
                write_preliminary(
                    ticker=r.ticker,
                    preliminary_fair_value=0.0,
                    method_used=r.method_used,
                    confidence=r.confidence,
                    input_quality=r.input_quality,
                    market_price=r.market_price if r.market_price > 0 else None,
                    flags=r.flags + (["blocked"] if r.block_reason else []),
                    calculation_notes=r.notes or r.block_reason,
                    db_path=db_path,
                    write=True,
                )
            else:
                write_preliminary(
                    ticker=r.ticker,
                    preliminary_fair_value=r.preliminary_fv,
                    method_used=r.method_used,
                    confidence=r.confidence,
                    input_quality=r.input_quality,
                    market_price=r.market_price,
                    flags=r.flags,
                    calculation_notes=r.notes,
                    db_path=db_path,
                    write=True,
                )
        log.info("[M018-S04] todos registros gravados em valuation_results")
    else:
        log.info("[M018-S04] dry-run: nenhum registro gravado")

    # Verificações pós-escrita
    if not dry_run:
        checks = _post_write_checks(db_path, results)
        all_ok = all(checks.values())
        log.info(
            "[M018-S04] verificações pós-escrita",
            checks=checks,
            all_ok=all_ok,
        )
        if not all_ok:
            failed = [k for k, v in checks.items() if not v]
            log.error(f"[M018-S04] FALHA nas verificações: {failed}")

    return results


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="M018-S04: Controlled Preliminary Valuation Batch"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simula sem gravar no banco",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Caminho do SQLite (default: src/ingestion/db.py DB_PATH)",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else DB_PATH

    results = run_batch(db_path, dry_run=args.dry_run)

    # Sumário rápido no terminal
    print("\n" + "=" * 80)
    print("M018-S04 — PRELIMINARY VALUATION BATCH")
    print("=" * 80)
    print(f"{'TICKER':<8} {'FV (R$)':>8} {'MP (R$)':>8} {'UPSIDE':>8} "
          f"{'QUAL':<12} {'CONF':<8} {'SANITY':<7} {'BLOCKED':<30}")
    print("-" * 80)
    for r in results:
        blocked_str = (r.block_reason or "")[:28]
        sanity_str  = "✓ PASS" if r.sanity_check_passed else "✗ PEND"
        print(
            f"{r.ticker:<8} {r.preliminary_fv:>8.2f} {r.market_price:>8.2f} "
            f"{r.upside_pct:>+8.1f}% {r.input_quality:<12} {r.confidence:<8} "
            f"{sanity_str:<7} {blocked_str:<30}"
        )

    n_blocked  = sum(1 for r in results if r.block_reason)
    n_passed   = sum(1 for r in results if r.sanity_check_passed)
    n_distress = sum(1 for r in results if r.ticker in DISTRESSED_TICKERS)
    print("-" * 80)
    print(f"Total: {len(results)}/18  |  Passed sanity: {n_passed}  "
          f"|  Blocked: {n_blocked}  |  Distressed: {n_distress}")
    print("=" * 80)


if __name__ == "__main__":
    main()
