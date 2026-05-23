"""
Options Paper Trading Robust — M010 S04.

Integra validate_options_entry no lifecycle de posições paper.
Oferece diário de operações paper com estatísticas por estrutura.

Funções principais:
  paper_entry(candidate_id, size_lots=1, notes=None)
  paper_update(position_id)
  paper_exit(position_id, exit_type, reason, notes=None)
  paper_journal_entry(position_id, entry_type, details)
  get_paper_stats(structure_type=None)
  ensure_paper_journal_schema()

Regras:
  - Não executa ordens reais.
  - source_type='PAPER', is_simulated=1 sempre.
  - Validação via validate_options_entry antes de entrada.
  - Dados reais do DB — nada falsificado.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from src.dashboard.data import _db_path
from src.options.options_entry_validator import (
    STATUS_BLOCKED,
    STATUS_MONITOR_ONLY,
    STATUS_PAPER_READY,
    validate_options_entry,
)
from src.integration.connectors.options_position_lifecycle_connector import (
    close_options_position,
    create_options_position,
    get_options_position_detail,
    update_options_position_snapshot,
)


# ── Exception ──────────────────────────────────────────────────────────────────

class PaperTradingError(Exception):
    """Raised when a paper entry fails validation or a lifecycle operation errors."""

    def __init__(self, reason: str, candidate_id: int | None = None, status: str | None = None):
        self.reason = reason
        self.candidate_id = candidate_id
        self.status = status
        super().__init__(reason)


# ── Schema ─────────────────────────────────────────────────────────────────────

JOURNAL_TABLE = "options_paper_journal"

JOURNAL_COLUMNS = [
    "journal_id INTEGER PRIMARY KEY AUTOINCREMENT",
    "position_id INTEGER",
    "candidate_id INTEGER",
    "structure_type TEXT",
    "underlying TEXT",
    "entry_type TEXT",
    "entry_price REAL",
    "exit_price REAL",
    "pnl_reais REAL",
    "pnl_pct REAL",
    "dte_entry INTEGER",
    "holding_days INTEGER",
    "exit_type TEXT",
    "exit_reason TEXT",
    "notes TEXT",
    "validated_at TEXT",
    "created_at TEXT",
]


# ── Schema management ─────────────────────────────────────────────────────────

def ensure_paper_journal_schema() -> bool:
    """
    Creates or verifies the options_paper_journal table.

    Returns True if table exists (was created or already present).
    """
    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            cur = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (JOURNAL_TABLE,),
            )
            if cur.fetchone():
                return True

            cols_sql = ",\n  ".join(JOURNAL_COLUMNS)
            con.execute(f"CREATE TABLE {JOURNAL_TABLE} (\n  {cols_sql}\n)")
            con.execute(
                f"CREATE INDEX IF NOT EXISTS idx_paper_journal_underlying "
                f"ON {JOURNAL_TABLE}(underlying)"
            )
            con.execute(
                f"CREATE INDEX IF NOT EXISTS idx_paper_journal_structure "
                f"ON {JOURNAL_TABLE}(structure_type)"
            )
            con.execute(
                f"CREATE INDEX IF NOT EXISTS idx_paper_journal_exit_type "
                f"ON {JOURNAL_TABLE}(exit_type)"
            )
            con.commit()
            return True
    except sqlite3.Error:
        return False


# ── Internal helpers ─────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def _load_candidate(candidate_id: int) -> dict[str, Any] | None:
    """Load candidate from option_structure_candidates by id."""
    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT * FROM option_structure_candidates WHERE id = ?",
                (int(candidate_id),),
            ).fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def _load_position(position_id: int) -> dict[str, Any] | None:
    """Load position detail from options_positions."""
    return get_options_position_detail(int(position_id))


def _parse_dte_from_candidate(candidate: dict[str, Any]) -> int | None:
    """Extract DTE from candidate maturity_date."""
    mat = candidate.get("maturity_date")
    if not mat:
        return None
    try:
        expiry = datetime.strptime(str(mat)[:10], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return max(0, (expiry - today).days)
    except ValueError:
        return None


def _compute_holding_days(entry_date: str | None) -> int | None:
    """Compute holding days from entry_date to today."""
    if not entry_date:
        return None
    try:
        entry = datetime.strptime(str(entry_date)[:10], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return max(0, (today - entry).days)
    except ValueError:
        return None


def _journal_insert(
    position_id: int | None,
    candidate_id: int | None,
    structure_type: str | None,
    underlying: str | None,
    entry_type: str,
    entry_price: float | None,
    exit_price: float | None,
    pnl_reais: float | None,
    pnl_pct: float | None,
    dte_entry: int | None,
    holding_days: int | None,
    exit_type: str | None,
    exit_reason: str | None,
    notes: str | None,
    validated_at: str | None,
) -> int | None:
    """Insert a row into options_paper_journal. Returns journal_id or None."""
    if not ensure_paper_journal_schema():
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            cur = con.execute(
                f"""
                INSERT INTO {JOURNAL_TABLE} (
                    position_id, candidate_id, structure_type, underlying,
                    entry_type, entry_price, exit_price, pnl_reais, pnl_pct,
                    dte_entry, holding_days, exit_type, exit_reason,
                    notes, validated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    candidate_id,
                    structure_type,
                    underlying,
                    entry_type,
                    entry_price,
                    exit_price,
                    pnl_reais,
                    pnl_pct,
                    dte_entry,
                    holding_days,
                    exit_type,
                    exit_reason,
                    notes,
                    validated_at,
                    now,
                ),
            )
            con.commit()
            return cur.lastrowid
    except sqlite3.Error:
        return None


# ── Core functions ─────────────────────────────────────────────────────────────

def paper_entry(
    candidate_id: int,
    size_lots: int = 1,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Valida candidato e cria posição paper.

    Args:
        candidate_id: ID do candidato em option_structure_candidates.
        size_lots: múltiplo de lotes (1 lote = 100 contratos).
        notes: anotações opcionais.

    Returns:
        dict com entry details:
        {
            "ok": True,
            "position_id": int,
            "candidate_id": int,
            "validation": {status, overall_reason, ...},
            "entry_price": float,
            "max_risk": float,
            "dte_entry": int,
            "structure_type": str,
            "underlying": str,
            "journal_id": int,
            "notes": str,
        }

    Raises:
        PaperTradingError: se validação falhar (BLOCKED) ou
                          candidato não for PAPER_READY.
    """
    # ── 1. Validate via options_entry_validator ─────────────────────────────
    validation = validate_options_entry(int(candidate_id))

    if validation["status"] == STATUS_BLOCKED:
        reason = (
            f"[PAPER TRADING BLOCKED] candidate_id={candidate_id}. "
            f"Status={validation['status']}. "
            f"Reason: {validation['overall_reason']}"
        )
        # Log ERROR to journal
        _journal_insert(
            position_id=None,
            candidate_id=int(candidate_id),
            structure_type=None,
            underlying=None,
            entry_type="ERROR",
            entry_price=None,
            exit_price=None,
            pnl_reais=None,
            pnl_pct=None,
            dte_entry=None,
            holding_days=None,
            exit_type=None,
            exit_reason=reason,
            notes=notes,
            validated_at=validation.get("validated_at"),
        )
        raise PaperTradingError(reason, candidate_id=candidate_id, status=validation["status"])

    if validation["status"] == STATUS_MONITOR_ONLY:
        reason = (
            f"[PAPER TRADING MONITOR] candidate_id={candidate_id}. "
            f"Status={validation['status']}. "
            f"Reason: {validation['overall_reason']}. "
            f"Entry allowed but requires active monitoring."
        )
        # Log ERROR (monitoring alert) to journal
        _journal_insert(
            position_id=None,
            candidate_id=int(candidate_id),
            structure_type=None,
            underlying=None,
            entry_type="ERROR",
            entry_price=None,
            exit_price=None,
            pnl_reais=None,
            pnl_pct=None,
            dte_entry=None,
            holding_days=None,
            exit_type=None,
            exit_reason=reason,
            notes=notes,
            validated_at=validation.get("validated_at"),
        )
        # MONITOR_ONLY is allowed — proceed with warning logged

    # ── 2. Load candidate data for entry ───────────────────────────────────
    candidate = _load_candidate(int(candidate_id))
    if not candidate:
        raise PaperTradingError(
            f"Candidate id={candidate_id} not found in option_structure_candidates.",
            candidate_id=candidate_id,
        )

    structure_type = candidate.get("structure_type") or "UNKNOWN"
    underlying = candidate.get("underlying") or "UNKNOWN"
    dte_entry = _parse_dte_from_candidate(candidate)
    entry_price = candidate.get("net_debit") or abs(candidate.get("max_loss", 0))
    max_risk = abs(candidate.get("max_loss", 0)) if candidate.get("max_loss") else None

    # ── 3. Create position via lifecycle connector ─────────────────────────
    result = create_options_position(
        candidate_id=int(candidate_id),
        source_type="PAPER",
        notes=f"{notes or ''} [S04 paper_entry]".strip(),
    )

    if not result.get("ok"):
        raise PaperTradingError(
            f"Failed to create position for candidate_id={candidate_id}: {result.get('error')}",
            candidate_id=candidate_id,
        )

    position_id = result["position_id"]

    # ── 4. Take initial snapshot ─────────────────────────────────────────
    snapshot = update_options_position_snapshot(position_id)
    snapshot_pnl = snapshot["pnl_reais"] if snapshot else None
    snapshot_pnl_pct = snapshot["pnl_pct"] if snapshot else None

    # ── 5. Log ENTRY to journal ───────────────────────────────────────────
    journal_id = _journal_insert(
        position_id=position_id,
        candidate_id=int(candidate_id),
        structure_type=structure_type,
        underlying=underlying,
        entry_type="ENTRY",
        entry_price=entry_price,
        exit_price=None,
        pnl_reais=snapshot_pnl,
        pnl_pct=snapshot_pnl_pct,
        dte_entry=dte_entry,
        holding_days=0,
        exit_type=None,
        exit_reason=None,
        notes=notes,
        validated_at=validation.get("validated_at"),
    )

    return {
        "ok": True,
        "position_id": position_id,
        "candidate_id": int(candidate_id),
        "validation": validation,
        "entry_price": entry_price,
        "max_risk": max_risk,
        "dte_entry": dte_entry,
        "structure_type": structure_type,
        "underlying": underlying,
        "journal_id": journal_id,
        "notes": notes,
    }


def paper_update(position_id: int) -> dict[str, Any]:
    """
    Atualiza snapshot da posição e registra evento no journal.

    Args:
        position_id: ID da posição em options_positions.

    Returns:
        dict com snapshot atual:
        {
            "ok": True,
            "position_id": int,
            "snapshot": {snapshot fields...},
            "journal_id": int,
        }

    Raises:
        PaperTradingError: se posição não existir.
    """
    position = _load_position(int(position_id))
    if not position:
        raise PaperTradingError(f"Position {position_id} not found.", position_id=position_id)

    # Load snapshot before update for delta
    prev_snapshot = position.get("latest_snapshot")

    # Update snapshot
    snapshot = update_options_position_snapshot(int(position_id))
    if not snapshot:
        raise PaperTradingError(
            f"Failed to update snapshot for position {position_id}.",
            position_id=position_id,
        )

    # Log UPDATE to journal
    candidate_id = position.get("candidate_id")
    structure_type = position.get("structure_type")
    underlying = position.get("ticker")
    dte_entry = position.get("dte_initial")
    entry_price = position.get("cost_total") or position.get("net_debit")

    journal_id = _journal_insert(
        position_id=int(position_id),
        candidate_id=int(candidate_id) if candidate_id else None,
        structure_type=structure_type,
        underlying=underlying,
        entry_type="UPDATE",
        entry_price=entry_price,
        exit_price=None,
        pnl_reais=snapshot.get("pnl_reais"),
        pnl_pct=snapshot.get("pnl_pct"),
        dte_entry=dte_entry,
        holding_days=_compute_holding_days(position.get("entry_date")),
        exit_type=None,
        exit_reason=None,
        notes=None,
        validated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    return {
        "ok": True,
        "position_id": int(position_id),
        "snapshot": dict(snapshot),
        "journal_id": journal_id,
    }


def paper_exit(
    position_id: int,
    exit_type: str,
    reason: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Fecha posição e registra saída no journal.

    Args:
        position_id: ID da posição em options_positions.
        exit_type: MANUAL | STOP_LOSS | TAKE_PROFIT | EXPIRED | ADJUSTED
        reason: justificativa da saída.
        notes: anotações opcionais.

    Returns:
        dict com resultado do exit:
        {
            "ok": True,
            "position_id": int,
            "exit_type": str,
            "exit_snapshot": {snapshot fields...},
            "pnl_reais": float,
            "pnl_pct": float,
            "holding_days": int,
            "journal_id": int,
        }

    Raises:
        PaperTradingError: se posição não existir ou close falhar.
    """
    position = _load_position(int(position_id))
    if not position:
        raise PaperTradingError(f"Position {position_id} not found.", position_id=position_id)

    # Take final snapshot before closing
    snapshot = update_options_position_snapshot(int(position_id))
    pnl_reais = snapshot["pnl_reais"] if snapshot else None
    pnl_pct = snapshot["pnl_pct"] if snapshot else None
    holding_days = _compute_holding_days(position.get("entry_date"))

    # Close via lifecycle connector
    close_result = close_options_position(
        position_id=int(position_id),
        reason=f"[S04 paper_exit] {exit_type}: {reason}",
        close_type=exit_type,
    )

    if not close_result.get("ok"):
        raise PaperTradingError(
            f"Failed to close position {position_id}: {close_result.get('error')}",
            position_id=position_id,
        )

    # Log EXIT to journal
    candidate_id = position.get("candidate_id")
    structure_type = position.get("structure_type")
    underlying = position.get("ticker")
    dte_entry = position.get("dte_initial")
    entry_price = position.get("cost_total") or position.get("net_debit")

    journal_id = _journal_insert(
        position_id=int(position_id),
        candidate_id=int(candidate_id) if candidate_id else None,
        structure_type=structure_type,
        underlying=underlying,
        entry_type="EXIT",
        entry_price=entry_price,
        exit_price=pnl_reais,  # structure_value at exit
        pnl_reais=pnl_reais,
        pnl_pct=pnl_pct,
        dte_entry=dte_entry,
        holding_days=holding_days,
        exit_type=exit_type,
        exit_reason=reason,
        notes=notes,
        validated_at=None,
    )

    return {
        "ok": True,
        "position_id": int(position_id),
        "exit_type": exit_type,
        "exit_snapshot": dict(snapshot) if snapshot else {},
        "pnl_reais": pnl_reais,
        "pnl_pct": pnl_pct,
        "holding_days": holding_days,
        "journal_id": journal_id,
    }


def paper_journal_entry(
    position_id: int | None,
    entry_type: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    """
    Cria entrada arbitrária no diário paper (ROLL, ERROR genérico, etc.).

    Args:
        position_id: ID da posição (opcional).
        entry_type: ENTRY | UPDATE | EXIT | ROLL | ERROR
        details: dict com campos opcionais:
            candidate_id, structure_type, underlying, entry_price,
            exit_price, pnl_reais, pnl_pct, dte_entry, holding_days,
            exit_type, exit_reason, notes, validated_at

    Returns:
        {"ok": True, "journal_id": int}
    """
    journal_id = _journal_insert(
        position_id=int(position_id) if position_id else None,
        candidate_id=details.get("candidate_id"),
        structure_type=details.get("structure_type"),
        underlying=details.get("underlying"),
        entry_type=entry_type,
        entry_price=details.get("entry_price"),
        exit_price=details.get("exit_price"),
        pnl_reais=details.get("pnl_reais"),
        pnl_pct=details.get("pnl_pct"),
        dte_entry=details.get("dte_entry"),
        holding_days=details.get("holding_days"),
        exit_type=details.get("exit_type"),
        exit_reason=details.get("exit_reason"),
        notes=details.get("notes"),
        validated_at=details.get("validated_at"),
    )

    if journal_id is None:
        return {"ok": False, "error": "Failed to insert journal entry."}
    return {"ok": True, "journal_id": journal_id}


# ── Statistics ────────────────────────────────────────────────────────────────

def get_paper_stats(structure_type: str | None = None) -> dict[str, Any]:
    """
    Agrega estatísticas do diário paper.

    Args:
        structure_type: filtro opcional por tipo de estrutura.

    Returns:
        {
            "n_operations": int,
            "win_rate": float,
            "avg_pnl": float,
            "median_pnl": float,
            "max_gain": float,
            "max_loss": float,
            "avg_duration": float,
            "avg_dte_entry": float,
            "by_structure": {structure_type: stats},
            "by_exit_type": {exit_type: count},
            "total_pnl": float,
        }
    """
    if not ensure_paper_journal_schema():
        return _empty_stats()

    db = _db_path()
    with sqlite3.connect(str(db)) as con:
        con.row_factory = sqlite3.Row

        base_query = f"SELECT * FROM {JOURNAL_TABLE} WHERE entry_type = 'EXIT'"
        params: list[Any] = []
        if structure_type:
            base_query += " AND structure_type = ?"
            params.append(structure_type)

        rows = con.execute(base_query, params).fetchall()

        if not rows:
            stats = _empty_stats()
            if structure_type:
                stats["filter"] = structure_type
            return stats

        # Aggregate overall
        pnls = [r["pnl_reais"] for r in rows if r["pnl_reais"] is not None]
        pnl_pcts = [r["pnl_pct"] for r in rows if r["pnl_pct"] is not None]
        durations = [r["holding_days"] for r in rows if r["holding_days"] is not None]
        dtes = [r["dte_entry"] for r in rows if r["dte_entry"] is not None]

        n = len(rows)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)

        total_pnl = sum(pnls) if pnls else 0.0
        avg_pnl = total_pnl / n if n else 0.0

        sorted_pnls = sorted(pnls)
        if len(sorted_pnls) == 1:
            median_pnl = sorted_pnls[0]
        elif len(sorted_pnls) > 1:
            mid = len(sorted_pnls) // 2
            median_pnl = (
                sorted_pnls[mid]
                if len(sorted_pnls) % 2 == 1
                else (sorted_pnls[mid - 1] + sorted_pnls[mid]) / 2
            )
        else:
            median_pnl = 0.0

        max_gain = max(pnls) if pnls else 0.0
        max_loss = min(pnls) if pnls else 0.0
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        avg_dte_entry = sum(dtes) / len(dtes) if dtes else 0.0

        # By structure
        by_structure: dict[str, dict[str, Any]] = {}
        for row in rows:
            st = row["structure_type"] or "UNKNOWN"
            if st not in by_structure:
                by_structure[st] = {"n": 0, "wins": 0, "total_pnl": 0.0, "pnls": []}
            by_structure[st]["n"] += 1
            if row["pnl_reais"] is not None:
                by_structure[st]["total_pnl"] += row["pnl_reais"]
                by_structure[st]["pnls"].append(row["pnl_reais"])
                if row["pnl_reais"] > 0:
                    by_structure[st]["wins"] += 1

        for st, st_stats in by_structure.items():
            n_st = st_stats["n"]
            st_stats["win_rate"] = st_stats["wins"] / n_st if n_st else 0.0
            st_stats["avg_pnl"] = st_stats["total_pnl"] / n_st if n_st else 0.0
            del st_stats["pnls"]  # reduce payload

        # By exit type
        by_exit_type: dict[str, int] = {}
        for row in rows:
            et = row["exit_type"] or "UNKNOWN"
            by_exit_type[et] = by_exit_type.get(et, 0) + 1

        return {
            "n_operations": n,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / n if n else 0.0,
            "avg_pnl": avg_pnl,
            "median_pnl": median_pnl,
            "max_gain": max_gain,
            "max_loss": max_loss,
            "avg_duration": round(avg_duration, 1),
            "avg_dte_entry": round(avg_dte_entry, 1),
            "total_pnl": round(total_pnl, 2),
            "by_structure": by_structure,
            "by_exit_type": by_exit_type,
            "filter": structure_type,
        }


def _empty_stats() -> dict[str, Any]:
    return {
        "n_operations": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "avg_pnl": 0.0,
        "median_pnl": 0.0,
        "max_gain": 0.0,
        "max_loss": 0.0,
        "avg_duration": 0.0,
        "avg_dte_entry": 0.0,
        "total_pnl": 0.0,
        "by_structure": {},
        "by_exit_type": {},
    }


# ── Query helpers ─────────────────────────────────────────────────────────────

def get_paper_journal(
    position_id: int | None = None,
    entry_type: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retorna entradas do diário paper.

    Args:
        position_id: filtro opcional por posição.
        entry_type: filtro opcional por tipo (ENTRY/UPDATE/EXIT/ROLL/ERROR).
        limit: limite de resultados (padrão 50, máx 200).

    Returns:
        Lista de registros do diário, mais recentes primeiro.
    """
    if not ensure_paper_journal_schema():
        return []

    db = _db_path()
    limit = min(limit, 200)

    try:
        with sqlite3.connect(str(db)) as con:
            con.row_factory = sqlite3.Row
            query = f"SELECT * FROM {JOURNAL_TABLE}"
            conditions = []
            params: list[Any] = []

            if position_id is not None:
                conditions.append("position_id = ?")
                params.append(int(position_id))
            if entry_type:
                conditions.append("entry_type = ?")
                params.append(entry_type)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = con.execute(query, params).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error:
        return []