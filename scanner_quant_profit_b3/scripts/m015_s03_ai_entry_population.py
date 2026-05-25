"""
M015-S03: AI Entry Creation and Metadata Population
=====================================================
Objetivo: Criar/atualizar AI entries mínimas para 64 tickers (63 CSV + VALE3).

Regras:
  - company_name ← cotahist_daily.company_name (última trade_date com market_type='010')
  - market_price  ← cotahist_daily.close (última trade_date)
  - sector        ← tickers.yaml se ticker presente, senão 'UNKNOWN' (placeholder técnico)
  - subsector     ← tickers.yaml type se presente, senão 'UNKNOWN'
  - sector='UNKNOWN' → coverage_status=NEEDS_SECTOR, NÃO desbloqueia router, NÃO permite valuation
  - BDRs → market_classification='BDR_FII' no metadata_json
  - Preservar fair_value de: PETR4, BBAS3, ITUB4, WEGE3
  - NÃO calcular DCF/DDM/COSIF/fair_value novo
  - NÃO criar dados mockados
  - NÃO alterar opções/OOS/paper/scheduler
  - NÃO alterar política D077-D082

Fonte de setor rastreável: ../12_PYTHON/config/tickers.yaml
Fonte de preços/nome: cotahist_daily (market_type='010')
"""

import sqlite3
import yaml
import json
import csv
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data/database/scanner_quant.db"
TICKERS_YAML = BASE_DIR.parent / "12_PYTHON/config/tickers.yaml"
AUDIT_CSV = BASE_DIR / "docs/m015_traceability_audit_20260524.csv"

# Tickers com fair_value a preservar — NUNCA sobrescrever
PRESERVE_FAIR_VALUE = {"PETR4", "BBAS3", "ITUB4", "WEGE3"}

# ── Tickers legados (S03.5 — corporate action patch) ──────────────────────────
# Carregado de config/ticker_aliases.yaml via src/utils/ticker_aliases
# Fallback inline para resiliência se módulo não estiver no path
try:
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from src.utils.ticker_aliases import LEGACY_TICKERS as _LEGACY_TICKERS
    LEGACY_TICKERS: set[str] = set(_LEGACY_TICKERS)
except Exception:
    # Fallback hardcoded — manter sincronizado com config/ticker_aliases.yaml
    LEGACY_TICKERS = {"PETZ3"}

print(f"Tickers legados (corporate action): {sorted(LEGACY_TICKERS)}")

# ── Carregar tickers.yaml (fonte rastreável de setor) ─────────────────────────
with open(TICKERS_YAML, encoding="utf-8") as f:
    ticker_config = yaml.safe_load(f)

sector_map: dict[str, str] = {}
subsector_map: dict[str, str] = {}
for t in ticker_config["tickers"]:
    sector_map[t["ticker"]] = t.get("sector", "UNKNOWN")
    subsector_map[t["ticker"]] = t.get("type", "UNKNOWN")

# ── Carregar CSV do S01 (63 tickers do universo auditado) ─────────────────────
audit_rows: dict[str, dict] = {}
with open(AUDIT_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        audit_rows[row["ticker"]] = row

# BDRs identificados no S01 (classificação BDR_UNSUPPORTED)
bdr_tickers: set[str] = {
    r["ticker"] for r in audit_rows.values()
    if "BDR_UNSUPPORTED" in r.get("probable_root_cause", "")
}

# Universo S03: 63 CSV + VALE3 (extra, fora do traceability mas presente no AI)
all_tickers_s03 = list(audit_rows.keys())
if "VALE3" not in all_tickers_s03:
    all_tickers_s03.append("VALE3")  # VALE3 é caso manual/from-scratch

print(f"Universo S03: {len(all_tickers_s03)} tickers ({len(audit_rows)} CSV + VALE3)")
print(f"BDRs no universo: {sorted(bdr_tickers)}")
print()

# ── Conectar ao DB ─────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ── Ler cotahist: último close válido por ticker (market_type='010') ───────────
cur.execute("""
    SELECT c.ticker, c.company_name, c.close, c.trade_date
    FROM cotahist_daily c
    INNER JOIN (
        SELECT ticker, MAX(trade_date) AS max_date
        FROM cotahist_daily
        WHERE market_type = '010' AND close IS NOT NULL AND close > 0
        GROUP BY ticker
    ) m ON c.ticker = m.ticker AND c.trade_date = m.max_date
    WHERE c.market_type = '010'
""")
cotahist_data: dict[str, dict] = {row["ticker"]: dict(row) for row in cur.fetchall()}
print(f"Tickers com cotahist disponível: {len(cotahist_data)}")

# ── Ler AI entries existentes ──────────────────────────────────────────────────
cur.execute("""
    SELECT ticker, fair_value, valuation_available, metadata_json
    FROM asset_intelligence_snapshots
""")
existing_ai: dict[str, dict] = {row["ticker"]: dict(row) for row in cur.fetchall()}
print(f"AI entries existentes antes do S03: {len(existing_ai)}")
print()

# ── Execução S03 ───────────────────────────────────────────────────────────────
now_iso = datetime.now(timezone.utc).isoformat()

stats = {
    "inserted": [],
    "updated": [],
    "sector_traceable": [],
    "sector_unknown": [],
    "fair_value_preserved": [],
    "errors": [],
    "skipped_no_cotahist": [],
    "skipped_legacy_ticker": [],      # S03.5: tickers extintos por corporate action
}

for ticker in all_tickers_s03:
    # ── S03.5: skip de tickers legados (corporate action / ticker alias) ──
    if ticker in LEGACY_TICKERS:
        stats["skipped_legacy_ticker"].append(ticker)
        print(f"  [LEGACY_TICKER] {ticker} — ticker extinto por corporate action; pulando AI entry")
        print(f"    → Usar successor: ver config/ticker_aliases.yaml")
        continue

    cotahist = cotahist_data.get(ticker)
    if cotahist is None:
        stats["skipped_no_cotahist"].append(ticker)
        continue

    # ── Setor ──
    sector = sector_map.get(ticker, "UNKNOWN")
    subsector = subsector_map.get(ticker, "UNKNOWN")
    sector_source = "tickers_yaml" if ticker in sector_map else "UNKNOWN"

    if sector != "UNKNOWN":
        stats["sector_traceable"].append(ticker)
    else:
        stats["sector_unknown"].append(ticker)

    # ── Coverage status (não desbloqueia router/valuation com UNKNOWN) ──
    # NEEDS_SECTOR → ainda bloqueado para router e valuation
    # HAS_SECTOR_NO_RI → setor rastreável, mas sem ri_documents (S02 vai resolver)
    coverage_status = "NEEDS_SECTOR" if sector == "UNKNOWN" else "HAS_SECTOR_NO_RI"

    is_bdr = ticker in bdr_tickers
    market_classification = "BDR_FII" if is_bdr else "equity"

    # ── Metadata S03 ──
    s03_meta = {
        "s03_executed_at": now_iso,
        "s03_source_company_name": "cotahist_daily",
        "s03_source_market_price": "cotahist_daily",
        "s03_price_date": cotahist["trade_date"],
        "s03_source_sector": sector_source,
        "s03_coverage_status": coverage_status,
        "s03_market_classification": market_classification,
        "s03_sector_is_placeholder": sector == "UNKNOWN",
        # Restrições explícitas para sector='UNKNOWN':
        "s03_router_eligible": sector != "UNKNOWN",
        "s03_valuation_eligible": False,  # S03 nunca desbloqueia valuation
    }

    company_name = cotahist["company_name"]
    market_price = cotahist["close"]

    if ticker in existing_ai:
        # ── UPDATE — preservar fair_value se aplicável ──
        existing = existing_ai[ticker]

        # Merge metadata: preservar governance existente, adicionar s03 fields
        existing_meta = {}
        if existing["metadata_json"]:
            try:
                existing_meta = json.loads(existing["metadata_json"])
            except json.JSONDecodeError:
                existing_meta = {}
        merged_meta = {**existing_meta, **s03_meta}

        if ticker in PRESERVE_FAIR_VALUE and existing["fair_value"] is not None:
            stats["fair_value_preserved"].append((ticker, existing["fair_value"]))
            # UPDATE sem tocar em fair_value
            cur.execute("""
                UPDATE asset_intelligence_snapshots SET
                    company_name    = ?,
                    sector          = ?,
                    subsector       = ?,
                    market_price    = ?,
                    metadata_json   = ?
                WHERE ticker = ?
            """, (
                company_name, sector, subsector, market_price,
                json.dumps(merged_meta, ensure_ascii=False),
                ticker
            ))
        else:
            # UPDATE normal — fair_value não existe ou ticker não está na lista
            cur.execute("""
                UPDATE asset_intelligence_snapshots SET
                    company_name    = ?,
                    sector          = ?,
                    subsector       = ?,
                    market_price    = ?,
                    metadata_json   = ?
                WHERE ticker = ?
            """, (
                company_name, sector, subsector, market_price,
                json.dumps(merged_meta, ensure_ascii=False),
                ticker
            ))

        stats["updated"].append(ticker)
        action = "UPDATE"

    else:
        # ── INSERT novo AI entry mínimo ──
        # Não inserir fair_value, valuation_available, technical_status, etc.
        cur.execute("""
            INSERT INTO asset_intelligence_snapshots (
                created_at,
                trade_date,
                ticker,
                company_name,
                sector,
                subsector,
                market_price,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now_iso,
            cotahist["trade_date"],  # trade_date = data do preço
            ticker,
            company_name,
            sector,
            subsector,
            market_price,
            json.dumps(s03_meta, ensure_ascii=False),
        ))
        stats["inserted"].append(ticker)
        action = "INSERT"

    price_age_note = " [STALE]" if cotahist["trade_date"] < "2026-01-01" else ""
    print(f"  {action:6s} {ticker:10s} | {company_name:25s} | price={market_price:8.2f} ({cotahist['trade_date']}{price_age_note}) | sector={sector:30s} | {market_classification}")

# ── Commit ─────────────────────────────────────────────────────────────────────
conn.commit()
conn.close()

# ── Relatório final ────────────────────────────────────────────────────────────
print()
print("=" * 80)
print("RELATÓRIO S03 — AI Entry Creation and Metadata Population")
print("=" * 80)

print(f"\n[A] AI ENTRIES CRIADAS (INSERT): {len(stats['inserted'])}")
for t in sorted(stats["inserted"]):
    print(f"     {t}")

print(f"\n[B] AI ENTRIES ATUALIZADAS (UPDATE): {len(stats['updated'])}")
for t in sorted(stats["updated"]):
    print(f"     {t}")

print(f"\n[C] FAIR VALUES PRESERVADOS: {len(stats['fair_value_preserved'])}")
for t, fv in sorted(stats["fair_value_preserved"]):
    print(f"     {t}: R$ {fv:.2f} (intocado)")

print(f"\n[D] SETOR RASTREÁVEL (tickers.yaml): {len(stats['sector_traceable'])}")
for t in sorted(stats["sector_traceable"]):
    sec = sector_map.get(t, "?")
    typ = subsector_map.get(t, "?")
    print(f"     {t:10s} → {sec} / {typ}")

print(f"\n[E] SETOR UNKNOWN (placeholder — NEEDS_SECTOR): {len(stats['sector_unknown'])}")
for t in sorted(stats["sector_unknown"]):
    r = audit_rows.get(t, {})
    print(f"     {t:10s} | {r.get('cotahist_company_name','VALE3 (manual)'):25s} | router_eligible=False | valuation_eligible=False")

print(f"\n[F] SEM COTAHIST (skipped): {len(stats['skipped_no_cotahist'])}")
for t in stats["skipped_no_cotahist"]:
    print(f"     {t}")

print(f"\n[G] ERROS: {len(stats['errors'])}")
for e in stats["errors"]:
    print(f"     {e}")

print()
total = len(stats["inserted"]) + len(stats["updated"])
print(f"TOTAL OPERAÇÕES: {total} ({len(stats['inserted'])} INSERT + {len(stats['updated'])} UPDATE)")
print(f"Cobertura S03: {total}/64 tickers")
print(f"  Setor rastreável : {len(stats['sector_traceable'])} tickers ({len(stats['sector_traceable'])/total*100:.0f}%)")
print(f"  Setor UNKNOWN    : {len(stats['sector_unknown'])} tickers ({len(stats['sector_unknown'])/total*100:.0f}%)")
print()
print("RESTRIÇÕES APLICADAS:")
print("  ✅ fair_value de PETR4/BBAS3/ITUB4/WEGE3 — PRESERVADOS")
print("  ✅ sector='UNKNOWN' → coverage_status=NEEDS_SECTOR (router/valuation bloqueados)")
print("  ✅ BDRs marcados como BDR_FII no metadata_json")
print("  ✅ Nenhum DCF/DDM/COSIF/fair_value calculado")
print("  ✅ Nenhum dado mockado criado")
print("  ✅ D077-D082 policy: stores não calculam valuation")
