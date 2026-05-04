# -*- coding: utf-8 -*-
"""
banco.py — Camada de acesso ao banco de dados SQLite
Separado do crawler para facilitar consultas externas.

Migração segura: adiciona colunas novas sem apagar dados existentes.
"""

import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta, date

import config

logger = logging.getLogger("news_hunter.banco")


def _conectar():
    conn = sqlite3.connect(config.ARQUIVO_BANCO)
    conn.row_factory = sqlite3.Row
    return conn


# ── Migração segura ───────────────────────────────────────────────────────────

def _coluna_existe(conn, tabela: str, coluna: str) -> bool:
    """Verifica se uma coluna já existe na tabela."""
    rows = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(row[1] == coluna for row in rows)


def _adicionar_coluna_se_nao_existe(conn, tabela: str, coluna: str, definicao: str):
    """Adiciona coluna apenas se ainda não existir (idempotente)."""
    if not _coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
        logger.info("Coluna adicionada: %s.%s", tabela, coluna)


def inicializar():
    """Cria as tabelas se ainda não existirem e migra colunas novas."""
    conn = _conectar()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS noticias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hash        TEXT    UNIQUE NOT NULL,
            titulo      TEXT    NOT NULL,
            link        TEXT    NOT NULL,
            fonte       TEXT,
            categoria   TEXT,
            data_coleta TEXT    NOT NULL,
            data_pub    TEXT,
            conteudo    TEXT,
            alertado    INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_hash      ON noticias(hash);
        CREATE INDEX IF NOT EXISTS idx_data      ON noticias(data_coleta);
        CREATE INDEX IF NOT EXISTS idx_categoria ON noticias(categoria);

        CREATE TABLE IF NOT EXISTS erros_fonte (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fonte     TEXT,
            erro      TEXT,
            data      TEXT
        );
    """)

    # ── Migração segura: colunas do boletim ──────────────────────────────────
    _adicionar_coluna_se_nao_existe(conn, "noticias", "score",         "INTEGER DEFAULT 0")
    _adicionar_coluna_se_nao_existe(conn, "noticias", "subcategoria",  "TEXT")
    _adicionar_coluna_se_nao_existe(conn, "noticias", "urgente",       "INTEGER DEFAULT 0")
    _adicionar_coluna_se_nao_existe(conn, "noticias", "resumo_curto",  "TEXT")
    _adicionar_coluna_se_nao_existe(conn, "noticias", "motivo_score",  "TEXT")

    # Índice adicional para score (usado nas queries do boletim)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_score ON noticias(score)"
    )

    conn.commit()
    conn.close()
    logger.info("Banco inicializado: %s", config.ARQUIVO_BANCO)


def gerar_hash(titulo: str, link: str) -> str:
    return hashlib.sha256(f"{titulo}{link}".encode()).hexdigest()


# ── Inserção ──────────────────────────────────────────────────────────────────

def salvar(hash_: str, titulo: str, link: str, fonte: str,
           categoria: str, data_pub: str, conteudo: str,
           score: int = 0, subcategoria: str = "",
           urgente: int = 0, resumo_curto: str = "",
           motivo_score: str = "") -> bool:
    """
    Insere notícia. Retorna True se era nova, False se já existia (duplicata).
    Parâmetros do boletim são opcionais para manter compatibilidade.
    """
    conn = _conectar()
    try:
        conn.execute(
            """INSERT INTO noticias
               (hash, titulo, link, fonte, categoria, data_coleta, data_pub,
                conteudo, score, subcategoria, urgente, resumo_curto, motivo_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (hash_, titulo, link, fonte, categoria,
             datetime.now().isoformat(), data_pub, conteudo,
             score, subcategoria, urgente, resumo_curto, motivo_score),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def registrar_erro(fonte: str, erro: str):
    conn = _conectar()
    conn.execute(
        "INSERT INTO erros_fonte (fonte, erro, data) VALUES (?, ?, ?)",
        (fonte, str(erro)[:500], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def marcar_alertado(hash_: str):
    conn = _conectar()
    conn.execute("UPDATE noticias SET alertado=1 WHERE hash=?", (hash_,))
    conn.commit()
    conn.close()


def atualizar_resumo(hash_: str, resumo_curto: str):
    """Atualiza o resumo_curto de uma notícia já salva."""
    conn = _conectar()
    conn.execute(
        "UPDATE noticias SET resumo_curto=? WHERE hash=?",
        (resumo_curto, hash_),
    )
    conn.commit()
    conn.close()


def limpar_antigos():
    """Remove notícias com mais de MANTER_DIAS dias (se configurado)."""
    if config.MANTER_DIAS <= 0:
        return
    limite = (datetime.now() - timedelta(days=config.MANTER_DIAS)).isoformat()
    conn = _conectar()
    cursor = conn.execute(
        "DELETE FROM noticias WHERE data_coleta < ?", (limite,)
    )
    removidos = cursor.rowcount
    conn.commit()
    conn.close()
    if removidos:
        logger.info("Limpeza: %d notícias antigas removidas.", removidos)


# ── Consultas padrão (mantidas intactas) ──────────────────────────────────────

def buscar(palavras: list = None, categoria: str = None,
           limite: int = 50, offset: int = 0) -> list:
    """Busca notícias com filtros opcionais."""
    conn = _conectar()
    condicoes = []
    params = []

    if palavras:
        for p in palavras:
            condicoes.append("(titulo LIKE ? OR conteudo LIKE ?)")
            params += [f"%{p}%", f"%{p}%"]
    if categoria:
        condicoes.append("categoria = ?")
        params.append(categoria)

    where = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    sql = f"""
        SELECT id, titulo, link, fonte, categoria, data_coleta, data_pub,
               alertado, score, urgente
        FROM noticias
        {where}
        ORDER BY data_coleta DESC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(sql, params + [limite, offset]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_por_id(id_: int) -> list:
    """Retorna a notícia com o id especificado."""
    conn = _conectar()
    rows = conn.execute(
        "SELECT * FROM noticias WHERE id = ?", (id_,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_hoje(limite: int = 50) -> list:
    """Retorna notícias coletadas hoje."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT id, titulo, link, fonte, categoria, data_coleta, data_pub,
                  alertado, score, urgente, resumo_curto
           FROM noticias
           WHERE date(data_coleta) = date('now')
           ORDER BY data_coleta DESC
           LIMIT ?""",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_alertados(limite: int = 50) -> list:
    """Retorna notícias que dispararam alerta imediato."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT id, titulo, link, fonte, categoria, data_coleta, data_pub,
                  alertado, score, urgente
           FROM noticias
           WHERE alertado = 1
           ORDER BY data_coleta DESC
           LIMIT ?""",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Consultas do boletim ──────────────────────────────────────────────────────

def buscar_top_noticias_hoje(limite: int = 20, score_minimo: int = 0) -> list:
    """Retorna as melhores notícias de hoje ordenadas por score DESC."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT id, titulo, link, fonte, categoria, subcategoria,
                  data_coleta, data_pub, score, urgente, resumo_curto
           FROM noticias
           WHERE date(data_coleta) = date('now')
             AND score >= ?
           ORDER BY score DESC, data_coleta DESC
           LIMIT ?""",
        (score_minimo, limite),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_por_categoria(categoria: str, limite: int = 20,
                         score_minimo: int = 0) -> list:
    """Retorna notícias de hoje por categoria, ordenadas por score."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT id, titulo, link, fonte, categoria, subcategoria,
                  data_coleta, data_pub, score, urgente, resumo_curto
           FROM noticias
           WHERE date(data_coleta) = date('now')
             AND categoria = ?
             AND score >= ?
           ORDER BY score DESC, data_coleta DESC
           LIMIT ?""",
        (categoria, score_minimo, limite),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_urgentes(limite: int = 20) -> list:
    """Retorna notícias urgentes de hoje."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT id, titulo, link, fonte, categoria, data_coleta, data_pub,
                  score, urgente, resumo_curto
           FROM noticias
           WHERE date(data_coleta) = date('now')
             AND urgente = 1
           ORDER BY score DESC, data_coleta DESC
           LIMIT ?""",
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def estatisticas_por_categoria() -> list:
    """Retorna contagem e score médio por categoria (dados de hoje)."""
    conn = _conectar()
    rows = conn.execute(
        """SELECT categoria,
                  COUNT(*) as total,
                  ROUND(AVG(score), 1) as score_medio
           FROM noticias
           WHERE date(data_coleta) = date('now')
           GROUP BY categoria
           ORDER BY total DESC""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def total() -> int:
    conn = _conectar()
    n = conn.execute("SELECT COUNT(*) FROM noticias").fetchone()[0]
    conn.close()
    return n


def estatisticas() -> dict:
    conn = _conectar()
    stats = {
        "total":      conn.execute("SELECT COUNT(*) FROM noticias").fetchone()[0],
        "hoje":       conn.execute(
                          "SELECT COUNT(*) FROM noticias WHERE date(data_coleta)=date('now')"
                      ).fetchone()[0],
        "por_categoria": dict(conn.execute(
                          "SELECT categoria, COUNT(*) FROM noticias GROUP BY categoria"
                      ).fetchall()),
        "erros_hoje": conn.execute(
                          "SELECT COUNT(*) FROM erros_fonte WHERE date(data)=date('now')"
                      ).fetchone()[0],
    }
    conn.close()
    return stats
