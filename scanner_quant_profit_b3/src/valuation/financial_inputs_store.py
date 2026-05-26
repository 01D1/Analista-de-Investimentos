"""
financial_inputs_store.py
--------------------------
Store canônico para inputs financeiros estruturados do valuation engine (M017).

Tabela: valuation_financial_inputs
  - Fonte primária (Track B): CVM CSV em data/raw/cvm/2025/
      source_type='CVM_CSV', source_priority=1
  - Fonte suplementar (Track A): Excel pipeline banco completo/outputs/
      source_type='EXCEL_PIPELINE', source_priority=2
  - Fallback manual: source_type='MANUAL', source_priority=3
  - VAMO3 e similares sem fonte: MANUAL_REVIEW (não armazenado aqui)

Unicidade lógica:
  (ticker, period_end, period_type, metric_name, source_type)
  → ON CONFLICT DO UPDATE (último write vence por campo)

Regras de segurança:
  - write=False por padrão em TODAS as funções de mutação (upsert, delete)
  - Nenhum cálculo de fair_value, DCF, DDM ou COSIF realizado aqui
  - Não altera asset_intelligence_snapshots nem valuation_results
  - Não altera nenhuma tabela existente do ingestion.db (apenas cria nova)

Uso:
    from src.valuation.financial_inputs_store import (
        ensure_financial_inputs_schema,
        upsert_financial_input,
        get_financial_inputs,
        get_latest_financial_inputs,
        list_financial_input_coverage,
        delete_financial_inputs_for_source,
    )
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ingestion.db import DB_PATH, get_connection
from src.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS valuation_financial_inputs (
    id                TEXT    PRIMARY KEY,
    ticker            TEXT    NOT NULL,
    period_type       TEXT    NOT NULL,    -- 'DFP' | 'ITR' | 'LTM'
    period_end        TEXT    NOT NULL,    -- YYYY-MM-DD (data-fim do período)
    fiscal_year       INTEGER NOT NULL,    -- ano fiscal (ex: 2024)
    fiscal_quarter    INTEGER,             -- trimestre 1–4; NULL para DFP anual
    metric_name       TEXT    NOT NULL,    -- 'net_revenue' | 'ebitda' | 'net_income' | ...
    metric_value      REAL    NOT NULL,    -- valor numérico extraído
    currency          TEXT    NOT NULL DEFAULT 'BRL',
    unit              TEXT    NOT NULL DEFAULT 'thousands', -- 'units'|'thousands'|'millions'|'billions'
    source_type       TEXT    NOT NULL,    -- 'CVM_CSV' | 'EXCEL_PIPELINE' | 'MANUAL'
    source_priority   INTEGER NOT NULL DEFAULT 1, -- 1=CVM (mais confiável), 2=Excel, 3=Manual
    source_path       TEXT,               -- caminho absoluto do arquivo-fonte
    source_doc_id     TEXT,               -- ID CVM do documento ou nome da aba Excel
    statement_type    TEXT,               -- 'BPA'|'BPP'|'DRE'|'DFC'|'DVA'|'DMPL'
    account_code      TEXT,               -- código da conta CVM (ex: '3.01')
    account_name      TEXT,               -- descrição da conta CVM
    confidence        REAL    NOT NULL DEFAULT 1.0,  -- 0.0–1.0
    extraction_method TEXT    NOT NULL DEFAULT 'structured', -- 'structured'|'derived'|'manual'
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
);

-- Unicidade lógica: um valor por (ticker, período, tipo de período, métrica, fonte)
-- ON CONFLICT DO UPDATE permite atualizar o valor sem gerar duplicata
CREATE UNIQUE INDEX IF NOT EXISTS idx_vfi_dedup
    ON valuation_financial_inputs(ticker, period_end, period_type, metric_name, source_type);

-- Performance: leitura por ticker
CREATE INDEX IF NOT EXISTS idx_vfi_ticker
    ON valuation_financial_inputs(ticker);

-- Performance: leitura por ticker + período
CREATE INDEX IF NOT EXISTS idx_vfi_ticker_period
    ON valuation_financial_inputs(ticker, period_end, period_type);

-- Performance: leitura por ticker + métrica
CREATE INDEX IF NOT EXISTS idx_vfi_metric
    ON valuation_financial_inputs(ticker, metric_name);
"""

# Campos obrigatórios para upsert — ausência gera ValueError (não silencia)
_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "ticker",
    "period_type",
    "period_end",
    "fiscal_year",
    "metric_name",
    "metric_value",
    "source_type",
    "source_priority",
})


def _now_iso() -> str:
    """Timestamp UTC em ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 1. Schema management
# ---------------------------------------------------------------------------

def ensure_financial_inputs_schema(db_path: Optional[Path] = None) -> None:
    """Cria a tabela valuation_financial_inputs e seus índices se não existirem.

    Idempotente — seguro chamar múltiplas vezes sem efeito colateral.
    Não altera nenhuma tabela pré-existente no banco.

    Args:
        db_path: caminho do arquivo SQLite. Usa data/ingestion.db se None.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        log.info(f"[financial_inputs_store] schema garantido — {db_path}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. Upsert (write=False por padrão)
# ---------------------------------------------------------------------------

def upsert_financial_input(
    record: Dict[str, Any],
    db_path: Optional[Path] = None,
    write: bool = False,
) -> Dict[str, Any]:
    """Insere ou atualiza um input financeiro na tabela valuation_financial_inputs.

    A unicidade lógica é garantida pelo índice UNIQUE em
    (ticker, period_end, period_type, metric_name, source_type).
    Em conflito, atualiza: metric_value, confidence, source_path, source_doc_id,
    account_code, account_name, extraction_method e updated_at.

    Modo seguro:
        write=False (padrão) → loga a intenção, NÃO persiste nenhum dado.
        write=True           → executa INSERT ... ON CONFLICT DO UPDATE.

    Args:
        record: dict com os campos da tabela. Campos obrigatórios definidos em
                _REQUIRED_FIELDS. Campos opcionais assumem defaults da tabela.
        db_path: caminho do SQLite. Usa ingestion.db se None.
        write: habilitar persistência. Default=False (dry-run).

    Returns:
        dict com:
            - action: "dry_run" | "upserted"
            - id: UUID do registro
            - ticker: str
            - metric_name: str
            - period_end: str

    Raises:
        ValueError: se algum campo de _REQUIRED_FIELDS estiver ausente.
    """
    db_path = db_path or DB_PATH

    # --- Validação de campos obrigatórios ---
    missing = _REQUIRED_FIELDS - set(record.keys())
    if missing:
        raise ValueError(
            f"[upsert_financial_input] Campos obrigatórios ausentes: {sorted(missing)}"
        )

    row_id = record.get("id") or str(uuid.uuid4())
    now = _now_iso()

    row: Dict[str, Any] = {
        "id":               row_id,
        "ticker":           str(record["ticker"]).upper(),
        "period_type":      str(record["period_type"]).upper(),
        "period_end":       record["period_end"],
        "fiscal_year":      int(record["fiscal_year"]),
        "fiscal_quarter":   record.get("fiscal_quarter"),
        "metric_name":      record["metric_name"],
        "metric_value":     float(record["metric_value"]),
        "currency":         record.get("currency", "BRL"),
        "unit":             record.get("unit", "thousands"),
        "source_type":      str(record["source_type"]).upper(),
        "source_priority":  int(record["source_priority"]),
        "source_path":      record.get("source_path"),
        "source_doc_id":    record.get("source_doc_id"),
        "statement_type":   record.get("statement_type"),
        "account_code":     record.get("account_code"),
        "account_name":     record.get("account_name"),
        "confidence":       float(record.get("confidence", 1.0)),
        "extraction_method": record.get("extraction_method", "structured"),
        "created_at":       record.get("created_at", now),
        "updated_at":       now,
    }

    result: Dict[str, Any] = {
        "action":      "dry_run",
        "id":          row_id,
        "ticker":      row["ticker"],
        "metric_name": row["metric_name"],
        "period_end":  row["period_end"],
    }

    if not write:
        log.info(
            f"[financial_inputs_store] DRY-RUN upsert — "
            f"ticker={row['ticker']} metric={row['metric_name']} "
            f"period={row['period_end']} source={row['source_type']} "
            f"value={row['metric_value']} (write=False, nada persistido)"
        )
        return result

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO valuation_financial_inputs
                (id, ticker, period_type, period_end, fiscal_year, fiscal_quarter,
                 metric_name, metric_value, currency, unit,
                 source_type, source_priority, source_path, source_doc_id,
                 statement_type, account_code, account_name,
                 confidence, extraction_method, created_at, updated_at)
            VALUES
                (:id, :ticker, :period_type, :period_end, :fiscal_year, :fiscal_quarter,
                 :metric_name, :metric_value, :currency, :unit,
                 :source_type, :source_priority, :source_path, :source_doc_id,
                 :statement_type, :account_code, :account_name,
                 :confidence, :extraction_method, :created_at, :updated_at)
            ON CONFLICT(ticker, period_end, period_type, metric_name, source_type)
            DO UPDATE SET
                metric_value      = excluded.metric_value,
                confidence        = excluded.confidence,
                source_path       = excluded.source_path,
                source_doc_id     = excluded.source_doc_id,
                account_code      = excluded.account_code,
                account_name      = excluded.account_name,
                extraction_method = excluded.extraction_method,
                updated_at        = excluded.updated_at
            """,
            row,
        )
        conn.commit()
        result["action"] = "upserted"
        log.info(
            f"[financial_inputs_store] upsert OK — "
            f"ticker={row['ticker']} metric={row['metric_name']} "
            f"period={row['period_end']} source={row['source_type']}"
        )
    finally:
        conn.close()

    return result


# ---------------------------------------------------------------------------
# 3. Read — get_financial_inputs
# ---------------------------------------------------------------------------

def get_financial_inputs(
    ticker: str,
    period_end: Optional[str] = None,
    period_type: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retorna inputs financeiros de um ticker com filtros opcionais.

    Args:
        ticker: código do ativo B3 (ex: 'ITUB4'). Case-insensitive.
        period_end: filtra por data fim do período (YYYY-MM-DD). Opcional.
        period_type: filtra por tipo ('DFP', 'ITR', 'LTM'). Opcional.
        db_path: caminho do SQLite.

    Returns:
        Lista de dicts com todos os campos da tabela, ordenada por
        period_end DESC, metric_name ASC.
        Lista vazia se o ticker não existir na tabela.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM valuation_financial_inputs WHERE ticker = ?"
        params: List[Any] = [ticker.upper()]

        if period_end is not None:
            query += " AND period_end = ?"
            params.append(period_end)

        if period_type is not None:
            query += " AND period_type = ?"
            params.append(period_type.upper())

        query += " ORDER BY period_end DESC, metric_name ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Read — get_latest_financial_inputs
# ---------------------------------------------------------------------------

def get_latest_financial_inputs(
    ticker: str,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retorna os inputs do período mais recente para cada metric_name.

    Para cada (ticker, metric_name), seleciona a linha com o maior period_end.
    Em caso de empate de period_end, prioriza menor source_priority
    (CVM_CSV=1 > EXCEL_PIPELINE=2 > MANUAL=3).

    Args:
        ticker: código do ativo B3. Case-insensitive.
        db_path: caminho do SQLite.

    Returns:
        Lista de dicts — uma linha por metric_name com período mais recente.
        Lista vazia se o ticker não existir na tabela.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY ticker, metric_name
                           ORDER BY period_end DESC, source_priority ASC
                       ) AS _rn
                FROM valuation_financial_inputs
                WHERE ticker = ?
            )
            SELECT
                id, ticker, period_type, period_end, fiscal_year, fiscal_quarter,
                metric_name, metric_value, currency, unit,
                source_type, source_priority, source_path, source_doc_id,
                statement_type, account_code, account_name,
                confidence, extraction_method, created_at, updated_at
            FROM ranked
            WHERE _rn = 1
            ORDER BY metric_name ASC
            """,
            (ticker.upper(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Read — list_financial_input_coverage
# ---------------------------------------------------------------------------

def list_financial_input_coverage(
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Resume a cobertura de inputs financeiros por ticker.

    Retorna uma linha por ticker com:
      - ticker: código do ativo
      - total_metrics: quantidade de metric_name distintos presentes
      - latest_period: período mais recente disponível (YYYY-MM-DD)
      - sources: source_types distintos, separados por vírgula
      - min_confidence: menor valor de confidence registrado

    Útil para diagnóstico de quais tickers têm inputs prontos e quais
    ainda precisam de parser (S02).

    Args:
        db_path: caminho do SQLite.

    Returns:
        Lista de dicts ordenada por ticker ASC. Lista vazia se tabela vazia.
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                ticker,
                COUNT(DISTINCT metric_name)  AS total_metrics,
                MAX(period_end)              AS latest_period,
                GROUP_CONCAT(DISTINCT source_type) AS sources,
                MIN(confidence)              AS min_confidence
            FROM valuation_financial_inputs
            GROUP BY ticker
            ORDER BY ticker ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 6. Delete (write=False por padrão — NÃO usar automaticamente)
# ---------------------------------------------------------------------------

def delete_financial_inputs_for_source(
    source_path: str,
    db_path: Optional[Path] = None,
    write: bool = False,
) -> Dict[str, Any]:
    """Remove todos os registros associados a um source_path específico.

    ATENÇÃO:
        - write=False por padrão. Nenhuma linha é removida sem autorização explícita.
        - Use apenas para limpeza manual de uma fonte com dados incorretos.
        - Nunca chamar automaticamente em pipelines ou schedulers.

    Args:
        source_path: valor exato do campo source_path na tabela.
        db_path: caminho do SQLite.
        write: habilitar deleção real. Default=False (dry-run).

    Returns:
        dict com:
            - action: "dry_run" | "deleted"
            - rows_affected: número de linhas que seriam/foram removidas
            - source_path: caminho informado
    """
    db_path = db_path or DB_PATH
    conn = get_connection(db_path)

    result: Dict[str, Any] = {
        "action":       "dry_run",
        "rows_affected": 0,
        "source_path":  source_path,
    }

    try:
        count_row = conn.execute(
            "SELECT COUNT(*) FROM valuation_financial_inputs WHERE source_path = ?",
            (source_path,),
        ).fetchone()
        count = int(count_row[0]) if count_row else 0
        result["rows_affected"] = count

        if not write:
            log.warning(
                f"[financial_inputs_store] DRY-RUN delete — "
                f"source_path={source_path!r} "
                f"rows_would_delete={count} (write=False, nenhuma linha removida)"
            )
            return result

        conn.execute(
            "DELETE FROM valuation_financial_inputs WHERE source_path = ?",
            (source_path,),
        )
        conn.commit()
        result["action"] = "deleted"
        log.warning(
            f"[financial_inputs_store] DELETE executado — "
            f"source_path={source_path!r} rows_deleted={count}"
        )
    finally:
        conn.close()

    return result
