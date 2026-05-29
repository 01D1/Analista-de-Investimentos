"""
valuation_results_store.py
--------------------------
Store canônico para resultados de valuation com ciclo de vida explícito (M018-S01).

Tabela: valuation_results
  Lifecycle: preliminary → validated → approved
  Campos chave: preliminary_fair_value, recalculated_fair_value, preserved_fair_value,
                approved_fair_value, sanity_check_passed, preservation_status, flags

Regras de proteção OBRIGATÓRIAS:
  RULE-01  Nunca sobrescrever preserved_fair_value de PRESERVE_EXISTING sem force_recalc=True
  RULE-02  preliminary_fair_value ≠ approved_fair_value (ciclo de vida)
  RULE-03  Nenhuma escrita em asset_intelligence_snapshots em M018
  RULE-04  PRESERVE_EXISTING usam write_comparison() — nunca write_preliminary()
  RULE-20  Promoção para approved exige sanity_check_passed=True — sem exceções automáticas

Uso:
    from src.valuation.valuation_results_store import (
        ensure_valuation_results_schema,
        write_preliminary,
        write_comparison,
        promote_to_approved,
        get_valuation_results,
        get_latest_valuation_result,
        list_valuation_results_summary,
    )

    # Ou via classe:
    writer = ValuationResultsWriter(db_path=db_path)
    writer.write_preliminary(ticker='EGIE3', ...)
    writer.write_comparison(ticker='ITUB4', ...)
    writer.promote_to_approved(ticker='EGIE3', force=True)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.ingestion.db import DB_PATH, get_connection
from src.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes de proteção
# ---------------------------------------------------------------------------

#: 9 tickers com fair_values preservados de origem legada (M016).
#: Nunca recebem write_preliminary() — somente write_comparison().
#: Nunca têm approved_fair_value sobrescrito sem force=True E force_recalc=True explícitos.
PRESERVE_EXISTING: Set[str] = {
    "ABCB4",
    "BBAS3",
    "BBDC4",
    "BPAC11",
    "BRSR6",
    "ITUB4",
    "SANB11",
    "PETR4",
    "WEGE3",
}

#: Valores legados preservados de M016 (referência imutável).
LEGACY_FAIR_VALUES: Dict[str, float] = {
    "ABCB4":  210.50,
    "BBAS3":   64.84,
    "BBDC4":   34.63,
    "BPAC11":   8.46,
    "BRSR6":    4.66,
    "ITUB4":   73.69,
    "SANB11":  86.79,
    "PETR4":   81.12,
    "WEGE3":   40.16,
}

# Source constants
SOURCE_CONTROLLED  = "M018_CONTROLLED"    # novos tickers — write_preliminary()
SOURCE_COMPARISON  = "M018_COMPARISON"    # PRESERVE_EXISTING — write_comparison()
SOURCE_LEGACY      = "M016_LEGACY"        # legado (read-only)

# Lifecycle statuses
STATUS_PRELIMINARY = "preliminary"
STATUS_VALIDATED   = "validated"
STATUS_APPROVED    = "approved"

# Preservation statuses
PRESERVATION_KEEP        = "KEEP_PRESERVED"
PRESERVATION_REVIEW      = "REVIEW_PRESERVED"
PRESERVATION_REPLACE     = "REPLACE_CANDIDATE"
PRESERVATION_INSUFFICIENT = "INSUFFICIENT_DATA"

# ---------------------------------------------------------------------------
# Schema DDL (mesma SQL do migration file 002_valuation_results.sql)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS valuation_results (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT    NOT NULL,
    valuation_date          DATE    NOT NULL,
    status                  TEXT    NOT NULL DEFAULT 'preliminary',
    preserved_fair_value    REAL,
    recalculated_fair_value REAL,
    preliminary_fair_value  REAL,
    validated_fair_value    REAL,
    approved_fair_value     REAL,
    market_price            REAL,
    upside_pct              REAL,
    upside_preserved        REAL,
    upside_recalculated     REAL,
    difference_pct          REAL,
    method_used             TEXT    NOT NULL,
    confidence              TEXT    NOT NULL,
    input_quality           TEXT    NOT NULL,
    source                  TEXT    NOT NULL,
    preservation_status     TEXT,
    sanity_check_passed     INTEGER,
    block_reason            TEXT,
    flags                   TEXT,
    recommendation          TEXT,
    calculation_notes       TEXT,
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at             DATETIME,
    UNIQUE(ticker, valuation_date, source)
);

CREATE INDEX IF NOT EXISTS idx_vr_ticker
    ON valuation_results(ticker);

CREATE INDEX IF NOT EXISTS idx_vr_ticker_date
    ON valuation_results(ticker, valuation_date DESC);

CREATE INDEX IF NOT EXISTS idx_vr_status
    ON valuation_results(status);

CREATE INDEX IF NOT EXISTS idx_vr_source
    ON valuation_results(source);

CREATE INDEX IF NOT EXISTS idx_vr_sanity
    ON valuation_results(sanity_check_passed);
"""

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Timestamp UTC em ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    """Data de hoje em YYYY-MM-DD."""
    return datetime.now(timezone.utc).date().isoformat()


def _encode_flags(flags: Optional[List[str]]) -> Optional[str]:
    """Serializa lista de flags como JSON string."""
    if flags is None:
        return None
    return json.dumps(flags)


def _decode_flags(raw: Optional[str]) -> Optional[List[str]]:
    """Desserializa JSON string de flags."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _calc_upside(fair_value: Optional[float], market_price: Optional[float]) -> Optional[float]:
    """Calcula upside percentual: (fair_value / market_price - 1) × 100."""
    if fair_value and market_price and market_price != 0:
        return round((fair_value / market_price - 1) * 100, 2)
    return None


def _calc_difference_pct(recalculated: Optional[float], preserved: Optional[float]) -> Optional[float]:
    """Calcula diferença percentual: (recalculated / preserved - 1) × 100."""
    if recalculated and preserved and preserved != 0:
        return round((recalculated / preserved - 1) * 100, 2)
    return None


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...]) -> Dict[str, Any]:
    """Converte sqlite3.Row ou tuple para dict com flags decodificadas.

    Handles both sqlite3.Row (when row_factory is set) and plain tuples
    (when get_connection returns row_factory=None).
    """
    if hasattr(row, "keys"):
        # sqlite3.Row or dict-like — safe conversion
        d = dict(row)
    else:
        # Plain tuple — need column names from connection context
        # Called from write_preliminary/write_comparison which use get_connection()
        # with NO row_factory. We reconstruct from the SELECT query.
        # Since this is called right after a SELECT * ... WHERE ..., we use
        # the column order from the valuation_results schema.
        _COLUMNS = [
            "id", "ticker", "valuation_date", "status",
            "preserved_fair_value", "recalculated_fair_value",
            "preliminary_fair_value", "validated_fair_value", "approved_fair_value",
            "market_price", "upside_pct", "upside_preserved", "upside_recalculated",
            "difference_pct", "method_used", "confidence", "input_quality",
            "source", "preservation_status", "sanity_check_passed",
            "block_reason", "flags", "recommendation", "calculation_notes",
            "created_at", "updated_at", "promoted_at",
        ]
        d = dict(zip(_COLUMNS, row))
    d["flags"] = _decode_flags(d.get("flags"))
    return d


# ---------------------------------------------------------------------------
# 1. Schema management
# ---------------------------------------------------------------------------


def ensure_valuation_results_schema(db_path: Optional[Path] = None) -> None:
    """Cria a tabela valuation_results e índices se não existirem.

    Idempotente — seguro chamar múltiplas vezes sem efeito colateral.
    NÃO altera nenhuma tabela pré-existente (asset_intelligence_snapshots etc.).

    Args:
        db_path: caminho do SQLite. Usa data/ingestion.db se None.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        log.info(
            "[valuation_results_store] schema garantido",
            db_path=str(db_path),
        )
    finally:
        conn.close()


def backup_db(db_path: Optional[Path] = None) -> Path:
    """Cria backup do banco antes de migrations destrutivas.

    Returns:
        Path do arquivo de backup criado.

    Raises:
        FileNotFoundError: se db_path não existir.
    """
    db_path = db_path or DB_PATH
    if not db_path.exists():
        raise FileNotFoundError(f"[backup_db] banco não encontrado: {db_path}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".{ts}.bak")
    shutil.copy2(db_path, backup_path)
    log.info(
        "[valuation_results_store] backup criado",
        original=str(db_path),
        backup=str(backup_path),
    )
    return backup_path


# ---------------------------------------------------------------------------
# 2. write_preliminary — novos tickers apenas (BLOQUEIA PRESERVE_EXISTING)
# ---------------------------------------------------------------------------


def write_preliminary(
    ticker: str,
    preliminary_fair_value: float,
    method_used: str,
    confidence: str,
    input_quality: str,
    *,
    valuation_date: Optional[str] = None,
    market_price: Optional[float] = None,
    flags: Optional[List[str]] = None,
    calculation_notes: Optional[str] = None,
    db_path: Optional[Path] = None,
    write: bool = True,
) -> Dict[str, Any]:
    """Persiste fair value preliminar para um novo ticker (não-PRESERVE_EXISTING).

    Regras de proteção:
      - BLOQUEIA se ticker in PRESERVE_EXISTING → usar write_comparison()
      - BLOQUEIA se approved_fair_value já existe para este ticker/date
      - Nunca define approved_fair_value
      - Nunca escreve em asset_intelligence_snapshots

    Args:
        ticker: código do ativo (ex: 'EGIE3').
        preliminary_fair_value: fair value calculado (não validado).
        method_used: 'DDM' | 'DCF' | 'EV_EBITDA' | 'HYBRID'.
        confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT'.
        input_quality: 'FULL' | 'PARTIAL' | 'DISTRESSED' | 'MANUAL_REVIEW'.
        valuation_date: data do cálculo (default: hoje).
        market_price: preço de mercado no momento do cálculo.
        flags: lista de flags de qualidade ['distressed_risk', 'qualidade_media', ...].
        calculation_notes: observações sobre o cálculo.
        db_path: caminho do SQLite. Usa ingestion.db se None.
        write: False → dry-run (não persiste, retorna dict simulado).

    Returns:
        Dict com os dados do registro criado/simulado.

    Raises:
        ValueError: se ticker in PRESERVE_EXISTING.
        ValueError: se approved_fair_value já existe para este ticker/date.
    """
    ticker = ticker.upper().strip()

    # PROTEÇÃO CRÍTICA: PRESERVE_EXISTING nunca via write_preliminary()
    if ticker in PRESERVE_EXISTING:
        raise ValueError(
            f"[write_preliminary] BLOQUEADO — {ticker} é PRESERVE_EXISTING. "
            f"Use write_comparison() para tickers preservados. "
            f"PRESERVE_EXISTING: {sorted(PRESERVE_EXISTING)}"
        )

    valuation_date = valuation_date or _today_iso()
    upside_pct = _calc_upside(preliminary_fair_value, market_price)
    now = _now_iso()

    record = {
        "ticker":                 ticker,
        "valuation_date":         valuation_date,
        "status":                 STATUS_PRELIMINARY,
        "preliminary_fair_value": preliminary_fair_value,
        "market_price":           market_price,
        "upside_pct":             upside_pct,
        "method_used":            method_used,
        "confidence":             confidence,
        "input_quality":          input_quality,
        "source":                 SOURCE_CONTROLLED,
        "flags":                  _encode_flags(flags),
        "calculation_notes":      calculation_notes,
        "created_at":             now,
        "updated_at":             now,
        # Nunca definidos em write_preliminary
        "approved_fair_value":    None,
        "preserved_fair_value":   None,
        "recalculated_fair_value": None,
        "sanity_check_passed":    None,
        "block_reason":           None,
        "preservation_status":    None,
        "recommendation":         None,
    }

    if not write:
        log.info(
            "[write_preliminary] dry-run — sem persistência",
            ticker=ticker,
            fair_value=preliminary_fair_value,
        )
        result = dict(record)
        result["flags"] = flags
        return result

    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        # PROTEÇÃO CRÍTICA: bloquear se approved_fair_value já existe
        existing = conn.execute(
            "SELECT approved_fair_value FROM valuation_results "
            "WHERE ticker = ? AND valuation_date = ? AND source = ?",
            (ticker, valuation_date, SOURCE_CONTROLLED),
        ).fetchone()
        if existing and existing["approved_fair_value"] is not None:
            raise ValueError(
                f"[write_preliminary] BLOQUEADO — {ticker} já tem approved_fair_value "
                f"({existing['approved_fair_value']}) para {valuation_date}. "
                "Não é possível sobrescrever valor aprovado via write_preliminary()."
            )

        conn.execute(
            """
            INSERT INTO valuation_results (
                ticker, valuation_date, status,
                preliminary_fair_value, market_price, upside_pct,
                method_used, confidence, input_quality, source,
                flags, calculation_notes, created_at, updated_at
            ) VALUES (
                :ticker, :valuation_date, :status,
                :preliminary_fair_value, :market_price, :upside_pct,
                :method_used, :confidence, :input_quality, :source,
                :flags, :calculation_notes, :created_at, :updated_at
            )
            ON CONFLICT(ticker, valuation_date, source) DO UPDATE SET
                preliminary_fair_value = excluded.preliminary_fair_value,
                market_price           = excluded.market_price,
                upside_pct             = excluded.upside_pct,
                method_used            = excluded.method_used,
                confidence             = excluded.confidence,
                input_quality          = excluded.input_quality,
                flags                  = excluded.flags,
                calculation_notes      = excluded.calculation_notes,
                updated_at             = excluded.updated_at
            -- NUNCA sobrescreve approved_fair_value via ON CONFLICT
            """,
            record,
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM valuation_results WHERE ticker = ? AND valuation_date = ? AND source = ?",
            (ticker, valuation_date, SOURCE_CONTROLLED),
        ).fetchone()
        result = _row_to_dict(row)
        log.info(
            "[write_preliminary] salvo",
            ticker=ticker,
            fair_value=preliminary_fair_value,
            id=result.get("id"),
        )
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. write_comparison — PRESERVE_EXISTING apenas (não toca preserved_fair_value)
# ---------------------------------------------------------------------------


def write_comparison(
    ticker: str,
    recalculated_fair_value: float,
    method_used: str,
    confidence: str,
    input_quality: str,
    *,
    valuation_date: Optional[str] = None,
    market_price: Optional[float] = None,
    preservation_status: Optional[str] = None,
    flags: Optional[List[str]] = None,
    recommendation: Optional[str] = None,
    calculation_notes: Optional[str] = None,
    db_path: Optional[Path] = None,
    write: bool = True,
) -> Dict[str, Any]:
    """Persiste cálculo comparativo para PRESERVE_EXISTING — não toca preserved_fair_value.

    Regras de proteção:
      - BLOQUEIA se ticker NOT in PRESERVE_EXISTING → usar write_preliminary()
      - NUNCA define approved_fair_value
      - NUNCA altera preserved_fair_value existente
      - Calcula difference_pct = (recalculated / preserved - 1) × 100
      - Calcula upside_preserved e upside_recalculated
      - Nunca escreve em asset_intelligence_snapshots

    Args:
        ticker: código do ativo PRESERVE_EXISTING (ex: 'ITUB4').
        recalculated_fair_value: valor recalculado em M018 (comparação).
        method_used: 'DDM' | 'DCF' | 'EV_EBITDA' | 'HYBRID'.
        confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT'.
        input_quality: 'FULL' | 'PARTIAL' | 'DISTRESSED' | 'MANUAL_REVIEW'.
        valuation_date: data do cálculo (default: hoje).
        market_price: preço de mercado no momento do cálculo.
        preservation_status: 'KEEP_PRESERVED'|'REVIEW_PRESERVED'|'REPLACE_CANDIDATE'|'INSUFFICIENT_DATA'.
        flags: lista de flags de qualidade.
        calculation_notes: observações sobre o cálculo.
        db_path: caminho do SQLite.
        write: False → dry-run.

    Returns:
        Dict com os dados do registro criado/simulado.

    Raises:
        ValueError: se ticker NOT in PRESERVE_EXISTING.
    """
    ticker = ticker.upper().strip()

    # PROTEÇÃO CRÍTICA: write_comparison() exclusivo para PRESERVE_EXISTING
    if ticker not in PRESERVE_EXISTING:
        raise ValueError(
            f"[write_comparison] BLOQUEADO — {ticker} não é PRESERVE_EXISTING. "
            f"Use write_preliminary() para novos tickers. "
            f"PRESERVE_EXISTING: {sorted(PRESERVE_EXISTING)}"
        )

    valuation_date = valuation_date or _today_iso()
    preserved_value = LEGACY_FAIR_VALUES.get(ticker)

    difference_pct = _calc_difference_pct(recalculated_fair_value, preserved_value)
    upside_preserved = _calc_upside(preserved_value, market_price)
    upside_recalculated = _calc_upside(recalculated_fair_value, market_price)
    now = _now_iso()

    record = {
        "ticker":                  ticker,
        "valuation_date":          valuation_date,
        "status":                  STATUS_PRELIMINARY,
        "preserved_fair_value":    preserved_value,           # legado — imutável
        "recalculated_fair_value": recalculated_fair_value,   # comparação M018
        "market_price":            market_price,
        "upside_preserved":        upside_preserved,
        "upside_recalculated":     upside_recalculated,
        "difference_pct":          difference_pct,
        "method_used":             method_used,
        "confidence":              confidence,
        "input_quality":           input_quality,
        "source":                  SOURCE_COMPARISON,
        "preservation_status":     preservation_status,
        "flags":                   _encode_flags(flags),
        "calculation_notes":       calculation_notes,
        "created_at":              now,
        "updated_at":              now,
        # Nunca definidos em write_comparison
        "approved_fair_value":     None,
        "preliminary_fair_value":  None,
        "sanity_check_passed":     None,
        "block_reason":            None,
        # recommendation: opcional — registrado quando M018-S02 classifica o ticker
        "recommendation":          recommendation,
    }

    if not write:
        log.info(
            "[write_comparison] dry-run — sem persistência",
            ticker=ticker,
            preserved=preserved_value,
            recalculated=recalculated_fair_value,
            difference_pct=difference_pct,
        )
        result = dict(record)
        result["flags"] = flags
        return result

    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO valuation_results (
                ticker, valuation_date, status,
                preserved_fair_value, recalculated_fair_value,
                market_price, upside_preserved, upside_recalculated, difference_pct,
                method_used, confidence, input_quality, source,
                preservation_status, flags, recommendation, calculation_notes,
                created_at, updated_at
            ) VALUES (
                :ticker, :valuation_date, :status,
                :preserved_fair_value, :recalculated_fair_value,
                :market_price, :upside_preserved, :upside_recalculated, :difference_pct,
                :method_used, :confidence, :input_quality, :source,
                :preservation_status, :flags, :recommendation, :calculation_notes,
                :created_at, :updated_at
            )
            ON CONFLICT(ticker, valuation_date, source) DO UPDATE SET
                recalculated_fair_value = excluded.recalculated_fair_value,
                market_price            = excluded.market_price,
                upside_preserved        = excluded.upside_preserved,
                upside_recalculated     = excluded.upside_recalculated,
                difference_pct          = excluded.difference_pct,
                method_used             = excluded.method_used,
                confidence              = excluded.confidence,
                input_quality           = excluded.input_quality,
                preservation_status     = excluded.preservation_status,
                flags                   = excluded.flags,
                recommendation          = excluded.recommendation,
                calculation_notes       = excluded.calculation_notes,
                updated_at              = excluded.updated_at
            -- NUNCA sobrescreve preserved_fair_value nem approved_fair_value
            """,
            record,
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM valuation_results WHERE ticker = ? AND valuation_date = ? AND source = ?",
            (ticker, valuation_date, SOURCE_COMPARISON),
        ).fetchone()
        result = _row_to_dict(row)
        log.info(
            "[write_comparison] salvo",
            ticker=ticker,
            preserved=preserved_value,
            recalculated=recalculated_fair_value,
            difference_pct=difference_pct,
            preservation_status=preservation_status,
        )
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. promote_to_approved — exige sanity_check_passed=True, force=True
# ---------------------------------------------------------------------------


def promote_to_approved(
    ticker: str,
    *,
    valuation_date: Optional[str] = None,
    source: Optional[str] = None,
    force: bool = False,
    force_recalc: bool = False,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Promove fair value preliminar/validado para approved.

    Regras de proteção:
      - BLOQUEIA se sanity_check_passed IS NOT TRUE (valor 1)
      - BLOQUEIA se ticker in PRESERVE_EXISTING e force=False
      - BLOQUEIA se ticker in PRESERVE_EXISTING e force_recalc=False
      - NUNCA escreve em asset_intelligence_snapshots (escopo M019)
      - Escopo M018: registra promoted_at e status='approved'

    Args:
        ticker: código do ativo.
        valuation_date: data do cálculo. Default: registro mais recente.
        source: source do registro. Default: detecta automaticamente.
        force: True obrigatório para qualquer promoção.
        force_recalc: True obrigatório ADICIONALMENTE para PRESERVE_EXISTING.
        db_path: caminho do SQLite.

    Returns:
        Dict com o registro promovido.

    Raises:
        ValueError: se qualquer proteção for violada.
        ValueError: se nenhum registro elegível for encontrado.
    """
    ticker = ticker.upper().strip()

    # PROTEÇÃO CRÍTICA 1: force obrigatório
    if not force:
        raise ValueError(
            f"[promote_to_approved] BLOQUEADO — force=True é obrigatório. "
            f"Chame promote_to_approved('{ticker}', force=True)."
        )

    # PROTEÇÃO CRÍTICA 2: PRESERVE_EXISTING exige force_recalc=True adicional
    if ticker in PRESERVE_EXISTING and not force_recalc:
        raise ValueError(
            f"[promote_to_approved] BLOQUEADO — {ticker} é PRESERVE_EXISTING. "
            f"Exige force_recalc=True explícito além de force=True. "
            f"Decisão D126: promoção de preservados requer validação humana explícita."
        )

    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        # Localizar o registro alvo
        query = "SELECT * FROM valuation_results WHERE ticker = ?"
        params: list = [ticker]

        if valuation_date:
            query += " AND valuation_date = ?"
            params.append(valuation_date)

        if source:
            query += " AND source = ?"
            params.append(source)
        elif ticker in PRESERVE_EXISTING:
            query += " AND source = ?"
            params.append(SOURCE_COMPARISON)
        else:
            query += " AND source = ?"
            params.append(SOURCE_CONTROLLED)

        query += " ORDER BY valuation_date DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()

        if row is None:
            raise ValueError(
                f"[promote_to_approved] Nenhum registro encontrado para {ticker} "
                f"(valuation_date={valuation_date}, source={source})."
            )

        record = _row_to_dict(row)

        # PROTEÇÃO CRÍTICA 3: sanity_check_passed obrigatório
        if record.get("sanity_check_passed") != 1:
            block = record.get("block_reason") or "sanity_check_passed não é True"
            raise ValueError(
                f"[promote_to_approved] BLOQUEADO — {ticker} não passou no sanity check. "
                f"sanity_check_passed={record.get('sanity_check_passed')}. "
                f"block_reason='{block}'. "
                f"Execute S04 (Sanity Check) antes de promover."
            )

        now = _now_iso()
        effective_fv = (
            record.get("recalculated_fair_value")
            if ticker in PRESERVE_EXISTING
            else record.get("preliminary_fair_value")
        )

        conn.execute(
            """
            UPDATE valuation_results
            SET approved_fair_value = ?,
                status              = ?,
                promoted_at         = ?,
                updated_at          = ?
            WHERE id = ?
            """,
            (effective_fv, STATUS_APPROVED, now, now, record["id"]),
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT * FROM valuation_results WHERE id = ?",
            (record["id"],),
        ).fetchone()
        result = _row_to_dict(updated_row)
        log.info(
            "[promote_to_approved] promovido",
            ticker=ticker,
            approved_fair_value=result.get("approved_fair_value"),
            id=result.get("id"),
        )
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Leitura
# ---------------------------------------------------------------------------


def get_valuation_results(
    ticker: str,
    *,
    source: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retorna todos os registros de valuation_results para um ticker.

    Args:
        ticker: código do ativo.
        source: filtra por source ('M018_CONTROLLED' | 'M018_COMPARISON' | 'M016_LEGACY').
        db_path: caminho do SQLite.

    Returns:
        Lista de dicts ordenada por valuation_date DESC.
    """
    ticker = ticker.upper().strip()
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM valuation_results WHERE ticker = ?"
        params: list = [ticker]
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY valuation_date DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_valuation_result(
    ticker: str,
    *,
    source: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Retorna o registro mais recente de valuation_results para um ticker.

    Args:
        ticker: código do ativo.
        source: filtra por source (opcional).
        db_path: caminho do SQLite.

    Returns:
        Dict do registro mais recente, ou None se não encontrado.
    """
    results = get_valuation_results(ticker, source=source, db_path=db_path)
    return results[0] if results else None


def list_valuation_results_summary(
    *,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retorna resumo de todos os tickers em valuation_results.

    Inclui por ticker: último valuation_date, status, sources disponíveis,
    se tem approved, se passou sanity check.

    Args:
        db_path: caminho do SQLite.

    Returns:
        Lista de dicts de resumo, ordenada por ticker.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                ticker,
                MAX(valuation_date)                                AS latest_date,
                GROUP_CONCAT(DISTINCT source)                      AS sources,
                SUM(CASE WHEN approved_fair_value IS NOT NULL THEN 1 ELSE 0 END) AS has_approved,
                SUM(CASE WHEN sanity_check_passed = 1 THEN 1 ELSE 0 END)        AS passed_sanity,
                COUNT(*)                                            AS total_records,
                MAX(CASE WHEN source = ? THEN preserved_fair_value END) AS preserved_fair_value,
                MAX(CASE WHEN source = ? THEN recalculated_fair_value END) AS recalculated_fair_value,
                MAX(CASE WHEN source = ? THEN preliminary_fair_value END) AS preliminary_fair_value,
                MAX(CASE WHEN source = ? THEN preservation_status END) AS preservation_status,
                MAX(confidence) AS confidence
            FROM valuation_results
            GROUP BY ticker
            ORDER BY ticker
            """,
            (SOURCE_COMPARISON, SOURCE_COMPARISON, SOURCE_CONTROLLED, SOURCE_COMPARISON),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 6. Classe ValuationResultsWriter (API orientada a objeto — opcional)
# ---------------------------------------------------------------------------


class ValuationResultsWriter:
    """API orientada a objeto do valuation_results_store.

    Encapsula db_path e fornece interface idêntica às funções standalone.
    As funções standalone são preferidas para uso direto em scripts/testes.
    """

    PRESERVE_EXISTING: Set[str] = PRESERVE_EXISTING

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH

    def ensure_schema(self) -> None:
        ensure_valuation_results_schema(self.db_path)

    def write_preliminary(self, ticker: str, preliminary_fair_value: float, **kwargs) -> Dict[str, Any]:
        return write_preliminary(
            ticker=ticker,
            preliminary_fair_value=preliminary_fair_value,
            db_path=self.db_path,
            **kwargs,
        )

    def write_comparison(self, ticker: str, recalculated_fair_value: float, **kwargs) -> Dict[str, Any]:  # noqa: E501
        return write_comparison(
            ticker=ticker,
            recalculated_fair_value=recalculated_fair_value,
            db_path=self.db_path,
            **kwargs,
        )

    def promote_to_approved(self, ticker: str, **kwargs) -> Dict[str, Any]:
        return promote_to_approved(ticker=ticker, db_path=self.db_path, **kwargs)

    def get_valuation_results(self, ticker: str, **kwargs) -> List[Dict[str, Any]]:
        return get_valuation_results(ticker=ticker, db_path=self.db_path, **kwargs)

    def get_latest_valuation_result(self, ticker: str, **kwargs) -> Optional[Dict[str, Any]]:
        return get_latest_valuation_result(ticker=ticker, db_path=self.db_path, **kwargs)

    def list_summary(self) -> List[Dict[str, Any]]:
        return list_valuation_results_summary(db_path=self.db_path)
