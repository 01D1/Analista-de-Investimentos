"""
database.py — Persistência histórica de valuations em SQLite.

Salva cada run do pipeline e expõe funções de consulta:
  salvar_valuation()   — grava um run completo
  historico_ticker()   — últimos N runs de um ticker
  ranking()            — top N por score (último run por ticker)
  ultima_analise()     — run mais recente de um ticker
  comparar_runs()      — diferença entre dois runs do mesmo ticker

O banco fica em data/valuation.db, criado automaticamente se não existir.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pipeline.database")

_ROOT = Path(__file__).parent.parent
DB_PATH = _ROOT / "data" / "valuation.db"


# ─────────────────────────────────────────────────────────────────────────────
# Inicialização
# ─────────────────────────────────────────────────────────────────────────────

def _conexao() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _criar_tabelas(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS valuations (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id            TEXT    UNIQUE,
            timestamp         TEXT    NOT NULL,
            ticker            TEXT    NOT NULL,
            nome              TEXT,
            tipo_empresa      TEXT,

            -- Mercado
            preco_atual       REAL,
            beta_usado        REAL,

            -- Valuation
            equity_mm         REAL,
            preco_justo_on    REAL,
            preco_justo_pn    REAL,
            upside_on         REAL,
            tir_on            REAL,
            preco_teto_on     REAL,
            g_perpetuidade    REAL,

            -- Intelligence
            recomendacao      TEXT,
            score             INTEGER,
            risco             TEXT,
            confianca         TEXT,
            score_valuation   REAL,
            score_qualidade   REAL,

            -- Qualidade dos dados
            quality_score     INTEGER,
            quality_warnings  INTEGER,
            quality_critical  INTEGER,
            avisos_count      INTEGER,

            -- JSON completo para consultas futuras
            valuation_json    TEXT,
            analise_json      TEXT,
            avisos_json       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ticker_ts
            ON valuations (ticker, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_score
            ON valuations (score DESC);

        CREATE INDEX IF NOT EXISTS idx_recomendacao
            ON valuations (recomendacao, timestamp DESC);
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def salvar_valuation(
    ticker: str,
    nome: str,
    valuation: dict,
    mercado: dict,
    analise: dict,
    avisos: list[str],
    qualidade: dict,
    tipo_empresa: str = "general",
) -> Optional[int]:
    """
    Salva um run de valuation no banco.

    Returns:
        ID da linha inserida, ou None se falhou.
    """
    ts = datetime.now()
    run_id = f"{ticker}_{ts.strftime('%Y%m%d_%H%M%S')}"

    try:
        conn = _conexao()
        _criar_tabelas(conn)

        conn.execute(
            """
            INSERT OR REPLACE INTO valuations (
                run_id, timestamp, ticker, nome, tipo_empresa,
                preco_atual, beta_usado,
                equity_mm, preco_justo_on, preco_justo_pn,
                upside_on, tir_on, preco_teto_on, g_perpetuidade,
                recomendacao, score, risco, confianca,
                score_valuation, score_qualidade,
                quality_score, quality_warnings, quality_critical, avisos_count,
                valuation_json, analise_json, avisos_json
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                run_id,
                ts.isoformat(),
                ticker.upper(),
                nome,
                tipo_empresa,
                # mercado
                mercado.get("preco"),
                mercado.get("beta_usar"),
                # valuation
                valuation.get("equity_mm"),
                valuation.get("preco_justo_on"),
                valuation.get("preco_justo_pn"),
                valuation.get("upside_on"),
                valuation.get("tir_on"),
                valuation.get("preco_teto_on"),
                valuation.get("g_perpetuidade"),
                # intelligence
                analise.get("recomendacao"),
                analise.get("score"),
                analise.get("risco"),
                analise.get("confianca"),
                analise.get("detalhes", {}).get("score_valuation"),
                analise.get("detalhes", {}).get("score_qualidade"),
                # qualidade
                qualidade.get("score"),
                len(qualidade.get("warnings", [])),
                len(qualidade.get("critical", [])),
                len(avisos),
                # json
                json.dumps(valuation, ensure_ascii=False, default=str),
                json.dumps(analise, ensure_ascii=False, default=str),
                json.dumps(avisos, ensure_ascii=False),
            ),
        )
        conn.commit()
        row_id = conn.execute(
            "SELECT id FROM valuations WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        conn.close()

        logger.info("[database] %s salvo — id=%d | score=%s | rec=%s",
                    ticker, row_id, analise.get("score"), analise.get("recomendacao"))
        return row_id

    except Exception as exc:
        logger.error("[database] Erro ao salvar %s: %s", ticker, exc)
        return None


def historico_ticker(ticker: str, n: int = 10) -> list[dict]:
    """
    Retorna os últimos N runs de um ticker, do mais recente ao mais antigo.
    """
    try:
        conn = _conexao()
        _criar_tabelas(conn)
        rows = conn.execute(
            """
            SELECT * FROM valuations
            WHERE ticker = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (ticker.upper(), n),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("[database] Erro ao buscar histórico de %s: %s", ticker, exc)
        return []


def ranking(n: int = 20, min_score: int = 0, apenas_buy: bool = False) -> list[dict]:
    """
    Retorna o ranking dos tickers pelo score do último run.

    Args:
        n:          Número máximo de entradas.
        min_score:  Score mínimo para incluir.
        apenas_buy: Se True, filtra apenas recomendações BUY.
    """
    try:
        conn = _conexao()
        _criar_tabelas(conn)

        filtro_rec = "AND recomendacao LIKE 'BUY%'" if apenas_buy else ""
        rows = conn.execute(
            f"""
            WITH ultimo_por_ticker AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY ticker ORDER BY timestamp DESC
                ) AS rn
                FROM valuations
            )
            SELECT
                ticker, nome, tipo_empresa, timestamp,
                preco_atual, preco_justo_on, upside_on, tir_on,
                recomendacao, score, risco, confianca,
                quality_score, avisos_count
            FROM ultimo_por_ticker
            WHERE rn = 1
              AND score >= ?
              {filtro_rec}
            ORDER BY score DESC
            LIMIT ?
            """,
            (min_score, n),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("[database] Erro ao gerar ranking: %s", exc)
        return []


def ultima_analise(ticker: str) -> Optional[dict]:
    """Retorna o run mais recente de um ticker, ou None se não encontrado."""
    hist = historico_ticker(ticker, n=1)
    return hist[0] if hist else None


def comparar_runs(ticker: str, n: int = 2) -> Optional[dict]:
    """
    Compara os dois últimos runs de um ticker.

    Returns:
        dict com delta de upside, score, preco_justo; ou None se < 2 runs.
    """
    hist = historico_ticker(ticker, n=n)
    if len(hist) < 2:
        return None

    atual, anterior = hist[0], hist[1]

    def delta(campo):
        a = atual.get(campo)
        b = anterior.get(campo)
        if a is not None and b is not None:
            return round(a - b, 6)
        return None

    return {
        "ticker": ticker,
        "run_atual": atual.get("timestamp"),
        "run_anterior": anterior.get("timestamp"),
        "delta_upside": delta("upside_on"),
        "delta_score": delta("score"),
        "delta_preco_justo": delta("preco_justo_on"),
        "delta_tir": delta("tir_on"),
        "recomendacao_atual": atual.get("recomendacao"),
        "recomendacao_anterior": anterior.get("recomendacao"),
    }


def listar_tickers_com_historico() -> list[str]:
    """Lista todos os tickers que têm pelo menos um run salvo."""
    try:
        conn = _conexao()
        _criar_tabelas(conn)
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM valuations ORDER BY ticker"
        ).fetchall()
        conn.close()
        return [r["ticker"] for r in rows]
    except Exception as exc:
        logger.error("[database] Erro ao listar tickers: %s", exc)
        return []
