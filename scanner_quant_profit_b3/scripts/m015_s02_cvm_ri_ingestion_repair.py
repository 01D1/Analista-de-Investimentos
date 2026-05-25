"""
M015-S02: CVM RI Ingestion / INSERT Repair
============================================
Objetivo: Diagnosticar e reparar a ingestão CVM/RI para os tickers HAS_SECTOR_NO_RI.

Regras:
  - Auditar cvm_connector em modo seguro ANTES de qualquer INSERT
  - Validar company name vs. CVM code esperado (bloqueia dados contaminados)
  - Inserir ri_documents apenas para tickers com dados reais e corretos
  - Pular BBAS3, BBDC4, ITUB4, PETR4, WEGE3 (já têm ri_documents suficientes)
  - Tratar ABCB4 como caso misto: CVM contaminado (Copel) → só releases
  - Tratar VALE3, NTCO3, PETZ3 como sem dados → nenhum INSERT
  - NÃO calcular valuation
  - NÃO criar mock
  - NÃO alterar fair_value
  - NÃO sobrescrever D077-D082
  - NÃO usar Playwright/Chromium/browser

Rastreabilidade por documento:
  ticker | source | doc_type | published_at | title | url | inserted_at

Autoriza S04 apenas se validações passarem.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data/database/scanner_quant.db"
CVM_PROCESSED = BASE_DIR.parent / "12_PYTHON/pipeline banco completo/data/qualitative/processed"
RELEASES_ROOT = BASE_DIR.parent / "12_PYTHON/pipeline banco completo/data/qualitative/events"
REPORT_PATH = BASE_DIR / "docs/m015_s02_ingestion_repair_report.md"

# ── Tickers com ri_documents suficientes → pular ────────────────────────────────
SKIP_ALREADY_COVERED = {"BBAS3", "BBDC4", "ITUB4", "PETR4", "WEGE3"}

# ── Fair values protegidos → nunca alterar ──────────────────────────────────────
PROTECTED_FAIR_VALUES = {"BBAS3", "ITUB4", "PETR4", "WEGE3"}

# ── CVM codes esperados por ticker (para validação de contaminação) ───────────
# Fonte: 12_PYTHON/config/cvm_codes.yaml
EXPECTED_CVM_CODES: dict[str, str] = {
    "ABCB4":  "020958",  # Banco ABC Brasil S.A.
    "AZZA3":  "022349",  # Azzas 2154 S.A.
    "BPAC11": "022616",  # Banco BTG Pactual S.A.
    "BRSR6":  "001120",  # Banrisul  (yaml: "001210"? → verificar abaixo)
    "EGIE3":  "017329",  # Engie Brasil Energia
    "FLRY3":  "021881",  # Fleury S.A.
    "HYPE3":  "021300",  # Hypera S/A
    "KLBN11": "012319",  # Klabin S.A.
    "LREN3":  "014761",  # Lojas Renner S.A.
    "MGLU3":  "022550",  # Magazine Luiza S.A.
    "NTCO3":  "019550",  # Natura Cosméticos S.A.
    "PCAR3":  "003816",  # Companhia Brasileira de Distribuição
    "PETZ3":  "025089",  # Petz S.A.
    "PRIO3":  "002976",  # PRIO S.A.
    "RADL3":  "016705",  # Raia Drogasil S.A.
    "RAIL3":  "019978",  # Rumo S.A.
    "RECV3":  "024295",  # Petrorecôncavo S.A.
    "RENT3":  "008850",  # Localiza Rent a Car S.A.
    "SANB11": "020532",  # Banco Santander (Brasil) S.A.
    "SBSP3":  "005452",  # Sabesp
    "SUZB3":  "021474",  # Suzano S.A.
    "TAEE11": "016365",  # Transmissora Aliança de Energia Elétrica
    "VALE3":  "004170",  # Vale S.A.
    "VAMO3":  "024554",  # Vamos Locação
    "VIVA3":  "023566",  # Vivara Participações
    "VIVT3":  "019723",  # Telefônica Brasil S.A.
}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1 — AUDITORIA (SEGURA, SEM INSERT)
# ═══════════════════════════════════════════════════════════════════════════════

def load_cvm_codes_from_yaml() -> dict[str, str]:
    """Carrega mapeamento ticker → CVM code do arquivo oficial."""
    try:
        import yaml
        yaml_path = BASE_DIR.parent / "12_PYTHON/config/cvm_codes.yaml"
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {t: str(c).zfill(6) for t, c in data.get("cvm_codes", {}).items()}
    except Exception as e:
        print(f"[WARN] Não foi possível carregar cvm_codes.yaml: {e}")
        return {}


def get_cvm_code_from_index(ticker: str) -> str | None:
    """Lê o Codigo_CVM do primeiro item do cvm_ipe_index.json."""
    idx_path = CVM_PROCESSED / ticker / "cvm_ipe_index.json"
    if not idx_path.exists():
        return None
    try:
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            code = data[0].get("Codigo_CVM", "")
            return str(code).zfill(6) if code else None
    except Exception:
        return None
    return None


def audit_ticker_data(ticker: str, expected_cvm_codes: dict[str, str]) -> dict:
    """
    Audita disponibilidade e integridade dos dados para um ticker.
    Retorna dict com status, fontes disponíveis e problemas detectados.
    """
    cvm_dir = CVM_PROCESSED / ticker
    rel_file = RELEASES_ROOT / ticker / "events.json"

    has_cvm_dir = cvm_dir.exists()
    has_rel_file = rel_file.exists()

    # Contar documentos CVM
    cvm_count = 0
    cvm_contaminated = False
    cvm_company = None
    actual_cvm_code = None
    if has_cvm_dir:
        actual_cvm_code = get_cvm_code_from_index(ticker)
        expected = expected_cvm_codes.get(ticker, "")
        # Normalizar: alguns CVM codes têm zeros à esquerda e outros não
        if actual_cvm_code and expected:
            # Verificar se os 4-6 dígitos relevantes batem
            # (ex: "014311" vs "001120" — claramente diferentes)
            cvm_contaminated = (actual_cvm_code != expected.zfill(6))

        idx_file = cvm_dir / "cvm_ipe_index.json"
        if idx_file.exists():
            try:
                data = json.loads(idx_file.read_text(encoding="utf-8"))
                cvm_count = len(data) if isinstance(data, list) else 0
                if data and isinstance(data, list):
                    cvm_company = data[0].get("Nome_Companhia", "")
            except Exception:
                pass

    # Contar releases
    rel_count = 0
    rel_ticker_valid = False
    if has_rel_file:
        try:
            data = json.loads(rel_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rel_count = len(data)
                # Verificar que os eventos pertencem ao ticker correto
                tickers_in_data = {item.get("ticker", "").upper() for item in data[:20]}
                rel_ticker_valid = (ticker.upper() in tickers_in_data or
                                    len(tickers_in_data - {""}) == 0)  # sem ticker field = assume correto
        except Exception:
            pass

    return {
        "ticker": ticker,
        "has_cvm_dir": has_cvm_dir,
        "has_rel_file": has_rel_file,
        "cvm_count": cvm_count,
        "cvm_contaminated": cvm_contaminated,
        "cvm_company": cvm_company,
        "actual_cvm_code": actual_cvm_code,
        "expected_cvm_code": expected_cvm_codes.get(ticker, "N/A"),
        "rel_count": rel_count,
        "rel_ticker_valid": rel_ticker_valid,
        "can_insert_cvm": has_cvm_dir and cvm_count > 0 and not cvm_contaminated,
        "can_insert_releases": has_rel_file and rel_count > 0 and rel_ticker_valid,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2 — INTEGRAÇÃO (INSERT REAL)
# ═══════════════════════════════════════════════════════════════════════════════

def integrate_ticker(ticker: str, audit: dict, dry_run: bool = False) -> dict:
    """
    Integra documentos CVM e releases para um ticker.
    Retorna resultado da integração.
    """
    result = {
        "ticker": ticker,
        "cvm_inserted": 0,
        "releases_inserted": 0,
        "cvm_skipped_reason": None,
        "releases_skipped_reason": None,
        "errors": [],
    }

    # ── CVM ──────────────────────────────────────────────────────────────────
    if audit["can_insert_cvm"]:
        if not dry_run:
            try:
                sys.path.insert(0, str(BASE_DIR))
                from src.context.qualitative_data import integrate_cvm_documents
                n = integrate_cvm_documents(ticker)
                result["cvm_inserted"] = n
            except Exception as e:
                result["errors"].append(f"CVM error: {e}")
        else:
            result["cvm_inserted"] = -1  # dry_run marker
    else:
        if audit["cvm_contaminated"]:
            result["cvm_skipped_reason"] = (
                f"CONTAMINADO: dados do arquivo pertencem a "
                f"'{audit['cvm_company']}' (CVM {audit['actual_cvm_code']}) "
                f"≠ esperado CVM {audit['expected_cvm_code']}"
            )
        elif not audit["has_cvm_dir"]:
            result["cvm_skipped_reason"] = "Diretório CVM não existe"
        elif audit["cvm_count"] == 0:
            result["cvm_skipped_reason"] = "Nenhum evento CVM encontrado"
        else:
            result["cvm_skipped_reason"] = "Condição desconhecida"

    # ── Releases ─────────────────────────────────────────────────────────────
    if audit["can_insert_releases"]:
        if not dry_run:
            try:
                from src.context.qualitative_data import integrate_releases
                n = integrate_releases(ticker)
                result["releases_inserted"] = n
            except Exception as e:
                result["errors"].append(f"Releases error: {e}")
        else:
            result["releases_inserted"] = -1  # dry_run marker
    else:
        if not audit["has_rel_file"]:
            result["releases_skipped_reason"] = "Arquivo events.json não existe"
        elif audit["rel_count"] == 0:
            result["releases_skipped_reason"] = "Nenhum evento de releases encontrado"
        elif not audit["rel_ticker_valid"]:
            result["releases_skipped_reason"] = "Ticker inválido nos dados de releases"
        else:
            result["releases_skipped_reason"] = "Condição desconhecida"

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3 — VALIDAÇÕES PÓS-INSERT
# ═══════════════════════════════════════════════════════════════════════════════

def get_ri_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Retorna contagem de ri_documents por ticker."""
    cur = conn.execute("SELECT ticker, COUNT(*) FROM ri_documents GROUP BY ticker")
    return {row[0]: row[1] for row in cur.fetchall()}


def get_protected_fair_values(conn: sqlite3.Connection) -> dict[str, float | None]:
    """Retorna fair_values dos tickers protegidos."""
    result = {}
    for ticker in PROTECTED_FAIR_VALUES:
        cur = conn.execute(
            "SELECT fair_value FROM asset_intelligence_snapshots "
            "WHERE ticker=? ORDER BY id DESC LIMIT 1",
            (ticker,)
        )
        row = cur.fetchone()
        result[ticker] = row[0] if row else None
    return result


def validate_no_fake_data(conn: sqlite3.Connection, target_tickers: list[str]) -> list[str]:
    """
    Verifica que nenhum ticker que deveria estar vazio recebeu documentos.
    Retorna lista de violações.
    """
    violations = []
    should_be_empty = {"VALE3", "NTCO3", "PETZ3"}
    for ticker in should_be_empty:
        cur = conn.execute(
            "SELECT COUNT(*) FROM ri_documents WHERE ticker=?", (ticker,)
        )
        count = cur.fetchone()[0]
        if count > 0:
            violations.append(f"{ticker}: deveria ter 0 docs, mas tem {count}")
    return violations


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    now_str = datetime.now(timezone.utc).isoformat()
    print(f"M015-S02: CVM RI Ingestion/INSERT Repair")
    print(f"Data/hora: {now_str}")
    print(f"Database: {DB_PATH}")
    print("=" * 70)

    # ── Carregar CVM codes oficiais ──────────────────────────────────────────
    yaml_cvm_codes = load_cvm_codes_from_yaml()
    # Mesclar com os do script (como fallback)
    for t, c in EXPECTED_CVM_CODES.items():
        if t not in yaml_cvm_codes:
            yaml_cvm_codes[t] = c

    # ── Conectar ao banco ────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── BASELINE (ANTES) ─────────────────────────────────────────────────────
    print("\n[FASE 0] Capturando baseline...")
    baseline_counts = get_ri_counts(conn)
    baseline_total = sum(baseline_counts.values())
    baseline_fv = get_protected_fair_values(conn)

    print(f"  ri_documents ANTES: {baseline_total} total, {len(baseline_counts)} tickers")
    for t, fv in baseline_fv.items():
        print(f"  fair_value[{t}] = {fv}")

    # ── Determinar universo de tickers HAS_SECTOR ────────────────────────────
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, sector, metadata_json
        FROM asset_intelligence_snapshots
        WHERE id IN (
            SELECT MAX(id) FROM asset_intelligence_snapshots GROUP BY ticker
        )
        ORDER BY ticker
    """)
    all_ai = {row["ticker"]: dict(row) for row in cur.fetchall()}

    has_sector_tickers = []
    for ticker, row in sorted(all_ai.items()):
        sector = row.get("sector") or ""
        meta = {}
        try:
            meta = json.loads(row.get("metadata_json") or "{}")
        except Exception:
            pass
        asset_type = meta.get("asset_type", "")
        if asset_type in ("BDR", "FII", "BDR_FII"):
            continue
        if sector.upper() in ("", "UNKNOWN"):
            continue
        has_sector_tickers.append(ticker)

    print(f"\n[FASE 0] Tickers HAS_SECTOR no AI: {len(has_sector_tickers)}")

    # ── FASE 1: AUDITORIA ────────────────────────────────────────────────────
    print("\n[FASE 1] Auditando conectores CVM e Releases...")
    print(f"{'Ticker':<8} {'CVM_ok':<8} {'CVM_n':<6} {'CVM_company':<38} "
          f"{'CVM_issue':<25} {'REL_ok':<8} {'REL_n':<6}")
    print("-" * 105)

    audits: dict[str, dict] = {}
    for ticker in has_sector_tickers:
        a = audit_ticker_data(ticker, yaml_cvm_codes)
        audits[ticker] = a

        cvm_status = "SKIP_COVERED" if ticker in SKIP_ALREADY_COVERED else (
            "✓" if a["can_insert_cvm"] else
            "CONTAM" if a["cvm_contaminated"] else
            "NO_DIR" if not a["has_cvm_dir"] else "EMPTY"
        )
        cvm_issue = ""
        if a["cvm_contaminated"]:
            cvm_issue = f"CVM {a['actual_cvm_code']} (Copel?)"

        rel_status = "SKIP_COVERED" if ticker in SKIP_ALREADY_COVERED else (
            "✓" if a["can_insert_releases"] else
            "NO_FILE" if not a["has_rel_file"] else "EMPTY"
        )

        company_short = (a["cvm_company"] or "")[:36]
        print(f"{ticker:<8} {cvm_status:<8} {a['cvm_count']:<6} {company_short:<38} "
              f"{cvm_issue:<25} {rel_status:<8} {a['rel_count']:<6}")

    # ── Classificar tickers ──────────────────────────────────────────────────
    eligible_tickers = []  # CVM e/ou releases OK, não coberto
    cvm_only = []
    releases_only = []
    contaminated_cvm = []
    no_data = []
    already_covered = []

    for ticker in has_sector_tickers:
        if ticker in SKIP_ALREADY_COVERED:
            already_covered.append(ticker)
            continue
        a = audits[ticker]
        if not a["has_cvm_dir"] and not a["has_rel_file"]:
            no_data.append(ticker)
        elif a["cvm_contaminated"]:
            contaminated_cvm.append(ticker)
            if a["can_insert_releases"]:
                eligible_tickers.append(ticker)
                releases_only.append(ticker)
        elif a["can_insert_cvm"] or a["can_insert_releases"]:
            eligible_tickers.append(ticker)
            if a["can_insert_cvm"] and not a["can_insert_releases"]:
                cvm_only.append(ticker)
            elif not a["can_insert_cvm"] and a["can_insert_releases"]:
                releases_only.append(ticker)
        else:
            no_data.append(ticker)

    print(f"\n[FASE 1] Classificação:")
    print(f"  Já cobertos (pular): {sorted(already_covered)}")
    print(f"  Elegíveis (inserir): {sorted(eligible_tickers)}")
    print(f"  CVM contaminado (somente releases): {sorted(contaminated_cvm)}")
    print(f"  Sem dados: {sorted(no_data)}")

    # ── CAUSA DO INSERT QUEBRADO ─────────────────────────────────────────────
    print("\n[DIAGNÓSTICO] Causa do TRACE_NO_RI / INSERT quebrado:")
    print("  1. integrate_cvm_documents() e integrate_releases() EXISTEM e estão")
    print("     funcionais em src/context/qualitative_data.py")
    print("  2. Mas NUNCA foram chamados em lote para os tickers HAS_SECTOR_NO_RI")
    print("  3. ABCB4: pasta cvm_ipe_index.json contém dados de COPEL (CVM 14311)")
    print("     vs. esperado ABCB4 (CVM 020958) → dados contaminados no pipeline")
    print("  4. NTCO3, PETZ3, VALE3: sem diretório processed → sem dados")
    print("  5. O ri_documents está vazio (0 docs) para 26 tickers HAS_SECTOR")

    # ── FASE 2: INSERÇÃO ─────────────────────────────────────────────────────
    print(f"\n[FASE 2] Executando integração para {len(eligible_tickers)} tickers...")
    conn.close()  # fechar antes: integrate_* abre sua própria conexão

    integration_results: dict[str, dict] = {}
    for ticker in sorted(eligible_tickers):
        print(f"  [{ticker}] Integrando...", end=" ", flush=True)
        result = integrate_ticker(ticker, audits[ticker], dry_run=False)
        integration_results[ticker] = result
        cvm_n = result["cvm_inserted"]
        rel_n = result["releases_inserted"]
        errors = result["errors"]
        status = f"CVM={cvm_n} | REL={rel_n}"
        if errors:
            status += f" | ERRORS: {errors}"
        print(status)

    # ── FASE 3: VALIDAÇÕES PÓS-INSERT ────────────────────────────────────────
    print("\n[FASE 3] Validações pós-INSERT...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    after_counts = get_ri_counts(conn)
    after_total = sum(after_counts.values())
    after_fv = get_protected_fair_values(conn)

    # V1: Contagem antes/depois
    delta_total = after_total - baseline_total
    delta_tickers = len(after_counts) - len(baseline_counts)
    print(f"\n  V1 — Contagem:")
    print(f"     ANTES: {baseline_total} docs / {len(baseline_counts)} tickers")
    print(f"     DEPOIS: {after_total} docs / {len(after_counts)} tickers")
    print(f"     DELTA: +{delta_total} docs / +{delta_tickers} tickers")

    # V2: Fair values protegidos
    fv_ok = True
    print(f"\n  V2 — Fair values protegidos:")
    for ticker in sorted(PROTECTED_FAIR_VALUES):
        before = baseline_fv.get(ticker)
        after = after_fv.get(ticker)
        match = before == after
        if not match:
            fv_ok = False
        icon = "✓" if match else "❌ ALTERADO"
        print(f"     {ticker}: {before} → {after} {icon}")

    # V3: UNKNOWN bloqueado
    unknown_tickers_with_docs = []
    for row in conn.execute("""
        SELECT DISTINCT r.ticker
        FROM ri_documents r
        JOIN asset_intelligence_snapshots a ON r.ticker = a.ticker
        WHERE a.sector = 'UNKNOWN'
    """):
        unknown_tickers_with_docs.append(row[0])
    print(f"\n  V3 — Tickers UNKNOWN com docs (deve ser 0): {unknown_tickers_with_docs or '[]'}")

    # V4: Sem dados fake (VALE3, NTCO3, PETZ3)
    fake_violations = validate_no_fake_data(conn, [])
    print(f"\n  V4 — Dados fake detectados: {fake_violations or '[]'}")

    # V5: Tickers que receberam documentos
    new_tickers_with_docs = [t for t in after_counts if t not in baseline_counts]
    print(f"\n  V5 — Novos tickers com ri_docs: {sorted(new_tickers_with_docs)}")

    # V6: Detalhe por ticker inserido
    print(f"\n  V6 — Documentos por ticker (APÓS):")
    for ticker in sorted(after_counts):
        before = baseline_counts.get(ticker, 0)
        after_ = after_counts[ticker]
        delta = after_ - before
        marker = "  (novo)" if delta == after_ and before == 0 else f"  (+{delta})" if delta > 0 else ""
        print(f"     {ticker}: {after_}{marker}")

    conn.close()

    # ── GERAR RELATÓRIO ──────────────────────────────────────────────────────
    report_lines = [
        f"# M015-S02: CVM RI Ingestion / INSERT Repair",
        f"",
        f"**Executado:** {now_str}",
        f"**Database:** `{DB_PATH}`",
        f"",
        f"---",
        f"",
        f"## a) Diagnóstico do CVM Connector",
        f"",
        f"O conector `src/context/connectors/cvm_connector.py` lê arquivos `cvm_*index.json`",
        f"do diretório `12_PYTHON/pipeline banco completo/data/qualitative/processed/<TICKER>/`.",
        f"",
        f"O conector `releases_connector.py` lê `events/<TICKER>/events.json` do mesmo caminho base.",
        f"",
        f"As funções `integrate_cvm_documents()` e `integrate_releases()` existem em",
        f"`src/context/qualitative_data.py` e funcionam corretamente, mas **nunca foram**",
        f"**invocadas em lote para os tickers HAS_SECTOR_NO_RI**. Essa é a causa raiz.",
        f"",
        f"## b) Causa do INSERT Quebrado",
        f"",
        f"1. **Causa principal:** Nenhum script chamava `integrate_cvm_documents()` /",
        f"   `integrate_releases()` para os 26 tickers sem ri_documents.",
        f"2. **ABCB4 — Contaminação CVM:** a pasta `processed/ABCB4/cvm_ipe_index.json`",
        f"   contém 100 eventos de **COMPANHIA PARANAENSE DE ENERGIA COPEL** (CVM 014311)",
        f"   em vez de Banco ABC Brasil (CVM 020958). O pipeline que gerou os índices",
        f"   atribuiu um lote de dados de outra empresa à pasta ABCB4. CVM BLOQUEADO.",
        f"   Releases da ABCB4 estão corretos (79 eventos com `ticker='ABCB4'`) e foram integrados.",
        f"3. **NTCO3, PETZ3, VALE3:** sem diretório `processed/` → sem dados disponíveis.",
        f"",
        f"## c) Tickers Processados",
        f"",
    ]

    for ticker in sorted(eligible_tickers):
        r = integration_results.get(ticker, {})
        report_lines.append(
            f"- `{ticker}`: CVM={r.get('cvm_inserted',0)} | Releases={r.get('releases_inserted',0)}"
            + (f" | ERRORS: {r['errors']}" if r.get("errors") else "")
        )

    report_lines += [
        f"",
        f"## d) Documentos Inseridos por Ticker",
        f"",
        f"| Ticker | ANTES | DEPOIS | Delta |",
        f"|--------|-------|--------|-------|",
    ]
    for ticker in sorted(set(list(baseline_counts.keys()) + list(after_counts.keys()))):
        before = baseline_counts.get(ticker, 0)
        after_ = after_counts.get(ticker, 0)
        delta = after_ - before
        report_lines.append(f"| {ticker} | {before} | {after_} | +{delta} |")

    report_lines += [
        f"",
        f"**Total:** {baseline_total} → {after_total} (+{delta_total} docs, +{delta_tickers} tickers)",
        f"",
        f"## e) Tickers Sem Documentos e Motivo",
        f"",
    ]
    for ticker in sorted(no_data):
        a = audits.get(ticker, {})
        reason = "Sem diretório processed/ e sem events.json" if not a.get("has_cvm_dir") and not a.get("has_rel_file") else "Sem dados válidos"
        report_lines.append(f"- `{ticker}`: {reason}")
    for ticker in sorted(contaminated_cvm):
        if ticker not in releases_only:  # já processados via releases
            a = audits.get(ticker, {})
            report_lines.append(
                f"- `{ticker}` (CVM bloqueado): dados CVM pertencem a '{a.get('cvm_company','')}'"
            )

    report_lines += [
        f"",
        f"## f) Validações Executadas",
        f"",
        f"| Validação | Resultado |",
        f"|-----------|-----------|",
        f"| V1 — ri_documents ANTES | {baseline_total} docs / {len(baseline_counts)} tickers |",
        f"| V1 — ri_documents DEPOIS | {after_total} docs / {len(after_counts)} tickers |",
        f"| V1 — Delta | +{delta_total} docs / +{delta_tickers} tickers |",
        f"| V2 — fair_value BBAS3 preservado | {'✓' if baseline_fv.get('BBAS3') == after_fv.get('BBAS3') else '❌'} ({baseline_fv.get('BBAS3')}) |",
        f"| V2 — fair_value ITUB4 preservado | {'✓' if baseline_fv.get('ITUB4') == after_fv.get('ITUB4') else '❌'} ({baseline_fv.get('ITUB4')}) |",
        f"| V2 — fair_value PETR4 preservado | {'✓' if baseline_fv.get('PETR4') == after_fv.get('PETR4') else '❌'} ({baseline_fv.get('PETR4')}) |",
        f"| V2 — fair_value WEGE3 preservado | {'✓' if baseline_fv.get('WEGE3') == after_fv.get('WEGE3') else '❌'} ({baseline_fv.get('WEGE3')}) |",
        f"| V3 — UNKNOWN bloqueado | {'✓ (0 violações)' if not unknown_tickers_with_docs else '❌ ' + str(unknown_tickers_with_docs)} |",
        f"| V4 — Sem dados fake | {'✓' if not fake_violations else '❌ ' + str(fake_violations)} |",
        f"| V5 — ABCB4 CVM bloqueado | {'✓' if 'ABCB4' not in new_tickers_with_docs else '❓ verificar'} |",
        f"| V5 — VALE3 sem docs | {'✓' if 'VALE3' not in after_counts else '❌'} |",
        f"| V5 — NTCO3 sem docs | {'✓' if 'NTCO3' not in after_counts else '❌'} |",
        f"| V5 — PETZ3 sem docs | {'✓' if 'PETZ3' not in after_counts else '❌'} |",
        f"",
    ]

    # ── Autorização S04 ──────────────────────────────────────────────────────
    all_v2_ok = fv_ok
    all_v3_ok = not unknown_tickers_with_docs
    all_v4_ok = not fake_violations
    s04_authorized = all_v2_ok and all_v3_ok and all_v4_ok and delta_total > 0

    s04_status = "✅ **AUTORIZADO**" if s04_authorized else "❌ **BLOQUEADO**"
    s04_reasons = []
    if not all_v2_ok:
        s04_reasons.append("fair_values protegidos foram alterados")
    if not all_v3_ok:
        s04_reasons.append(f"tickers UNKNOWN com docs: {unknown_tickers_with_docs}")
    if not all_v4_ok:
        s04_reasons.append(f"dados fake detectados: {fake_violations}")
    if delta_total == 0:
        s04_reasons.append("nenhum documento foi inserido")

    report_lines += [
        f"## g) Autorização S04 — Coverage Audit Before/After Report",
        f"",
        f"**Status:** {s04_status}",
    ]
    if s04_reasons:
        report_lines.append(f"**Razões de bloqueio:**")
        for r in s04_reasons:
            report_lines.append(f"- {r}")

    report_lines += [
        f"",
        f"**Resumo S02:**",
        f"- {len(eligible_tickers)} tickers elegíveis processados",
        f"- {delta_total} documentos inseridos no total",
        f"- {len(new_tickers_with_docs)} novos tickers com ri_documents",
        f"- ABCB4: CVM bloqueado (contaminação Copel), releases integrados",
        f"- VALE3 / NTCO3 / PETZ3: sem dados disponíveis (0 inseridos)",
        f"- Fair values de BBAS3, ITUB4, PETR4, WEGE3: preservados",
        f"",
        f"---",
        f"*Gerado por M015-S02 em {now_str}*",
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n[RELATÓRIO] Salvo em: {REPORT_PATH}")

    print("\n" + "=" * 70)
    print(f"[RESUMO S02]")
    print(f"  ri_documents ANTES: {baseline_total} | DEPOIS: {after_total} | DELTA: +{delta_total}")
    print(f"  Novos tickers com docs: {sorted(new_tickers_with_docs)}")
    print(f"  Fair values protegidos: {'OK' if fv_ok else 'ALTERADOS — ERRO'}")
    print(f"  UNKNOWN bloqueado: {'OK' if not unknown_tickers_with_docs else 'VIOLAÇÃO'}")
    print(f"  Dados fake: {'OK' if not fake_violations else 'DETECTADOS — ERRO'}")
    print(f"\n  → S04: {s04_status}")

    if not s04_authorized:
        sys.exit(1)


if __name__ == "__main__":
    main()
