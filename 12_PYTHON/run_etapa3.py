"""
run_etapa3.py
--------------
Runner orquestrador da ETAPA 3: Validação, Correção de Período e Market Cap.

Executa em sequência:
  1. Seleciona melhor período para amostra de 10 tickers
  2. Constrói snapshots corretos a partir de valuation_financial_inputs
  3. Executa validação de plausibilidade
  4. Gera série histórica (2019-2025) para cada ticker da amostra
  5. Executa auditoria de cobertura completa
  6. Apresenta relatório antes/depois

Uso:
    cd /path/to/12_PYTHON
    python run_etapa3.py [--all-tickers] [--output-json]
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Garantir que o src/ seja encontrado
sys.path.insert(0, str(Path(__file__).parent))

from src.fundamentals.historical_series import (
    build_historical_series,
    format_series_table,
)
from src.fundamentals.period_selector import select_best_period
from src.fundamentals.plausibility import (
    PlausibilityChecker,
    classify_alerts,
    format_alert_report,
    has_critical_issues,
)
from src.fundamentals.snapshot_from_vfi import build_snapshot_from_vfi
from src.ingestion.db import DB_PATH, get_connection
from src.scanners.audit_fundamentals_coverage import print_coverage_report, run_coverage_audit
from src.utils.logger import get_logger
from src.valuation.financial_inputs_store import get_financial_inputs

log = get_logger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────────

SAMPLE_TICKERS = [
    "PETR4", "VALE3", "ITUB4", "BBAS3", "BBDC4",
    "WEGE3", "EGIE3", "ABEV3", "RENT3", "PRIO3",
]

BANK_TICKERS = {"ITUB4", "BBAS3", "BBDC4"}

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_b(val):
    if val is None:
        return "N/A"
    return f"R$ {val/1e9:.1f}B"


def _fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val:.1%}"


def _fmt_x(val):
    if val is None:
        return "N/A"
    return f"{val:.1f}x"


def _fmt_mult(val):
    if val is None:
        return "N/A"
    return f"{val:.1f}x"


# ── Tarefa 1: Seleção de período ──────────────────────────────────────────────

def task1_period_selection(tickers: list[str]) -> dict:
    """Analisa qual período seria selecionado para cada ticker."""
    print("\n" + "="*70)
    print("  TAREFA 1 — SELEÇÃO DE PERÍODO")
    print("="*70)

    results = {}
    for ticker in tickers:
        rows = get_financial_inputs(ticker, db_path=DB_PATH)
        sel = select_best_period(rows) if rows else None

        if sel:
            status = f"{sel.period_basis:12} FY{sel.fiscal_year} ({sel.period_end})"
        else:
            status = "SEM DADOS"

        results[ticker] = {
            "selection": sel,
            "rows_count": len(rows),
        }

        print(f"  {ticker:8}: {status}")
        if sel and sel.warnings:
            for w in sel.warnings:
                print(f"            ⚠️  {w}")

    return results


# ── Tarefa 2: Recalcular snapshots ────────────────────────────────────────────

def task2_recalculate_snapshots(tickers: list[str]) -> dict:
    """Constrói snapshots corretos a partir de VFI para a amostra."""
    print("\n" + "="*70)
    print("  TAREFA 2 — SNAPSHOTS CORRIGIDOS (via valuation_financial_inputs)")
    print("="*70)
    print(f"  {'TICKER':8} {'PERÍODO':6} {'FY':6} {'RECEITA':12} {'EBITDA':12} {'LUCRO':12} {'MKTCAP':12} {'PE':6} {'PB':6} {'EVEB':6}")
    print(f"  {'-'*95}")

    results = {}
    checker = PlausibilityChecker()

    for ticker in tickers:
        snap = build_snapshot_from_vfi(ticker)
        if snap is None:
            print(f"  {ticker:8}: SEM DADOS")
            results[ticker] = None
            continue

        vm = snap.valuation_multiples or {}
        pe = vm.get("pe")
        pb = vm.get("pb")
        ev_eb = vm.get("ev_ebitda")

        # Para bancos: EV/EBITDA = N/A
        ev_str = "N/A" if (snap.industry or "").lower() in {"bank", "banco"} else _fmt_mult(ev_eb)

        print(
            f"  {ticker:8} {snap.period_type:6} {snap.fiscal_year:4}  "
            f"{_fmt_b(snap.revenue):12} {_fmt_b(snap.ebitda):12} {_fmt_b(snap.net_income):12} "
            f"{_fmt_b(snap.market_cap):12} {_fmt_mult(pe):6} {_fmt_mult(pb):6} {ev_str:6}"
        )

        # Plausibilidade
        alerts = checker.check(snap)
        if has_critical_issues(alerts):
            print(f"           ⚠️  {len(alerts)} alertas CRÍTICOS/ERROS")
            for a in alerts:
                if a.severity in ("CRITICAL", "ERROR"):
                    print(f"              [{a.severity}] {a.check_name}: {a.message}")

        results[ticker] = snap

    return results


# ── Tarefa 3: Market cap e shares ─────────────────────────────────────────────

def task3_market_cap_check(tickers: list[str]) -> dict:
    """Verifica disponibilidade de market cap e shares para cada ticker."""
    print("\n" + "="*70)
    print("  TAREFA 3 — MARKET CAP E SHARES_OUTSTANDING")
    print("="*70)
    print(f"  {'TICKER':8} {'SHARES':12} {'FONTE':20} {'PREÇO':8} {'MKTCAP':12} {'OK':5}")
    print(f"  {'-'*70}")

    conn = get_connection(DB_PATH)
    results = {}

    for ticker in tickers:
        price_row = conn.execute(
            "SELECT adj_close, date FROM price_ohlcv WHERE ticker=? AND is_gap=0 AND adj_close IS NOT NULL ORDER BY date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        shares_row = conn.execute(
            "SELECT shares_outstanding, shares_source FROM financial_ltm WHERE ticker=? AND shares_outstanding IS NOT NULL ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()

        price = float(price_row[0]) if price_row else None
        price_date = price_row[1] if price_row else "N/A"
        shares = float(shares_row[0]) if shares_row else None
        shares_source = shares_row[1] if shares_row else "AUSENTE"

        mktcap = price * shares if price and shares else None
        ok = "✅" if mktcap else "❌"

        shares_str = f"{shares/1e6:.0f}M" if shares else "NULL"
        price_str = f"R${price:.2f}" if price else "NULL"
        mkt_str = f"R${mktcap/1e9:.1f}B" if mktcap else "NULL"

        print(f"  {ticker:8} {shares_str:12} {shares_source:20} {price_str:8} {mkt_str:12} {ok}")
        results[ticker] = {"shares": shares, "price": price, "market_cap": mktcap}

    conn.close()

    # Tickers sem shares
    missing = [t for t, d in results.items() if not d["shares"]]
    if missing:
        print(f"\n  ⚠️  Tickers sem shares_outstanding: {missing}")
        print("     → Buscar via yfinance: ticker.info['sharesOutstanding']")

    return results


# ── Tarefa 4: Banco sem EV/EBITDA ────────────────────────────────────────────

def task4_bank_multiples_check(tickers: list[str]) -> None:
    """Verifica que bancos não usam EV/EBITDA e têm P/L e P/VP."""
    print("\n" + "="*70)
    print("  TAREFA 4 — MÚLTIPLOS SETORIAIS (bancos vs industriais)")
    print("="*70)
    print(f"  {'TICKER':8} {'TIPO':10} {'P/L':8} {'P/VP':8} {'EV/EBITDA':12} {'STATUS':30}")
    print(f"  {'-'*75}")

    for ticker in tickers:
        snap = build_snapshot_from_vfi(ticker)
        if snap is None:
            print(f"  {ticker:8}: SEM SNAPSHOT")
            continue

        is_bank = str(snap.industry or "").lower() in {"bank", "banco"}
        vm = snap.valuation_multiples or {}
        pe = vm.get("pe")
        pb = vm.get("pb")
        ev_ebitda = vm.get("ev_ebitda")

        tipo = "BANCO" if is_bank else "INDUSTRIAL"

        if is_bank:
            ev_str = "N/A (correto)"
            if ev_ebitda is not None and ev_ebitda != 0:
                status = "❌ EV/EBITDA indevido!"
            elif pe is not None and pb is not None:
                status = "✅ P/L e P/VP ok"
            else:
                status = "⚠️  Faltam P/L ou P/VP"
        else:
            ev_str = _fmt_mult(ev_ebitda) or "NULL"
            if ev_ebitda is not None:
                status = "✅ EV/EBITDA disponível"
            else:
                status = "⚠️  EV/EBITDA ausente (checar EBITDA)"

        print(f"  {ticker:8} {tipo:10} {_fmt_mult(pe):8} {_fmt_mult(pb):8} {ev_str:12} {status}")


# ── Tarefa 5: Plausibilidade ──────────────────────────────────────────────────

def task5_plausibility_check(tickers: list[str]) -> dict:
    """Executa validação de plausibilidade para todos os tickers da amostra."""
    print("\n" + "="*70)
    print("  TAREFA 5 — VALIDAÇÃO DE PLAUSIBILIDADE")
    print("="*70)

    checker = PlausibilityChecker()
    results = {}

    for ticker in tickers:
        snap = build_snapshot_from_vfi(ticker)
        if snap is None:
            print(f"  {ticker}: SEM DADOS")
            results[ticker] = []
            continue

        alerts = checker.check(snap)
        results[ticker] = alerts

        if not alerts:
            print(f"  {ticker:8}: ✅ Sem alertas")
        else:
            classified = classify_alerts(alerts)
            critical = len(classified.get("CRITICAL", []))
            errors = len(classified.get("ERROR", []))
            warnings = len(classified.get("WARNING", []))
            info = len(classified.get("INFO", []))
            print(f"  {ticker:8}: 🚨{critical} ❌{errors} ⚠️{warnings} ℹ️{info}")
            for a in alerts:
                if a.severity in ("CRITICAL", "ERROR"):
                    print(f"             [{a.severity}] {a.check_name}: {a.message[:60]}")

    return results


# ── Tarefa 7+8: Histórico fundamentalista ─────────────────────────────────────

def task7_8_historical_series(tickers: list[str]) -> dict:
    """Gera série histórica fundamentalista para tickers da amostra."""
    print("\n" + "="*70)
    print("  TAREFA 7+8 — SÉRIE HISTÓRICA FUNDAMENTALISTA (2019-2025)")
    print("="*70)

    all_series = {}
    for ticker in tickers:
        is_bank = ticker in BANK_TICKERS
        series = build_historical_series(ticker, is_bank=is_bank)
        all_series[ticker] = series

        if not series:
            print(f"\n  {ticker}: sem dados históricos")
            continue

        print(format_series_table(
            series,
            ticker,
            metrics=[
                "revenue", "ebitda", "net_income",
                "ebitda_margin", "net_margin", "roe",
                "nd_ebitda" if not is_bank else "roe",
            ],
        ))

    return all_series


# ── Tarefa 6: Cobertura ───────────────────────────────────────────────────────

def task6_coverage_audit(tickers: list[str] | None = None) -> dict:
    """Executa auditoria de cobertura completa."""
    print("\n" + "="*70)
    print("  TAREFA 6 — AUDITORIA DE COBERTURA")
    print("="*70)

    output = REPORTS_DIR / f"coverage_audit_{date.today().isoformat()}.json"
    result = run_coverage_audit(tickers=tickers, output_file=output)
    print_coverage_report(result, verbose=(tickers is not None and len(tickers) <= 20))
    return result


# ── Runner principal ──────────────────────────────────────────────────────────

def main():
    all_tickers = "--all-tickers" in sys.argv
    output_json = "--output-json" in sys.argv

    tickers = None if all_tickers else SAMPLE_TICKERS

    print("\n" + "█"*70)
    print("  ETAPA 3 — VALIDAÇÃO, CORREÇÃO DE PERÍODO E MARKET CAP")
    print(f"  Data: {date.today().isoformat()}")
    print(f"  Tickers: {'TODOS' if all_tickers else str(SAMPLE_TICKERS)}")
    print("█"*70)

    # T1: Seleção de período
    period_results = task1_period_selection(SAMPLE_TICKERS)

    # T2: Snapshots corretos
    snapshots = task2_recalculate_snapshots(SAMPLE_TICKERS)

    # T3: Market cap
    market_data = task3_market_cap_check(SAMPLE_TICKERS)

    # T4: Bancos
    task4_bank_multiples_check(SAMPLE_TICKERS)

    # T5: Plausibilidade
    plausibility = task5_plausibility_check(SAMPLE_TICKERS)

    # T7+8: Histórico (somente PETR4 e VALE3 para demo rápida)
    task7_8_historical_series(["PETR4", "VALE3", "ITUB4"])

    # T6: Cobertura completa
    coverage = task6_coverage_audit(tickers=tickers)

    # ── Entregáveis finais ─────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("  ENTREGÁVEIS DA ETAPA 3")
    print("="*70)

    # Causa do Q1 2023
    print("""
  📌 CAUSA DO BUG DE SELEÇÃO DE PERÍODO (Q1 2023):
     O snapshot_builder.py original usava FinancialStatementMapper que:
     1. Aplicava regex muito ampla (r"receita") → capturava Receitas Financeiras,
        Outras Receitas Operacionais etc. → revenue inflado de 497B para 1261B
     2. Somava contas-pai E contas-filhas (ex: 2.03 + 2.03.01 + 2.03.02 → equity 2x)
     3. Mapeava 3.09+3.11+3.11.01+4.01 todos como net_income → inflação 4x
     O pipeline de fundamental_snapshots usava essa fonte corrompida.
     O period_selector não existia → nenhuma hierarquia DFP > LTM > ITR.

  📌 NOVA REGRA DE SELEÇÃO DE PERÍODO:
     1. DFP anual mais recente (preferred)
     2. LTM = DFP(N-1) + ITR_YTD(N) - ITR_YTD(N-1)
     3. ITR_PARTIAL = ITR mais recente, marcado como parcial
     Implementado em: src/fundamentals/period_selector.py
""")

    # Contagem de tickers
    s = coverage["summary"]
    pb = s["by_period_basis"]
    md = s["by_market_data"]

    print(f"  📊 COBERTURA (amostra de {len(SAMPLE_TICKERS)} tickers):")
    print(f"     Com DFP anual:         {pb['dfp_annual']}/{len(SAMPLE_TICKERS)}")
    print(f"     Com market cap:        {md['with_market_cap']}/{len(SAMPLE_TICKERS)}")
    print(f"     Com P/L:               {md['with_pe']}/{len(SAMPLE_TICKERS)}")
    print(f"     Com P/VP:              {md['with_pb']}/{len(SAMPLE_TICKERS)}")
    print(f"     Com EV/EBITDA:         {md['with_ev_ebitda']}/{len(SAMPLE_TICKERS)}")

    print(f"""
  📁 ARQUIVOS CRIADOS/MODIFICADOS:
     src/fundamentals/period_selector.py   — seleção de período hierárquica
     src/fundamentals/snapshot_from_vfi.py — builder correto (usa VFI, não mapper)
     src/fundamentals/plausibility.py      — validação de plausibilidade
     src/fundamentals/historical_series.py — série histórica anual
     src/scanners/audit_fundamentals_coverage.py — relatório de cobertura
     tests/test_period_selection.py        — testes de seleção de período
     tests/test_plausibility.py            — testes de plausibilidade
     reports/coverage_audit_*.json         — relatório JSON de cobertura

  🔄 PARA REEXECUTAR:
     python run_etapa3.py                  # amostra 10 tickers
     python run_etapa3.py --all-tickers    # todos os tickers ativos

  🔜 PRÓXIMOS PASSOS (para expansão):
     1. Migrar pipeline.py para usar snapshot_from_vfi.py em produção
     2. Corrigir FinancialStatementMapper para evitar double-counting
     3. Adicionar shares_outstanding via yfinance para IGTI11 e INTR4
     4. Expandir série histórica para todos os tickers
     5. Implementar API endpoints para UI consumir dados históricos
""")

    if output_json:
        out = REPORTS_DIR / f"etapa3_results_{date.today().isoformat()}.json"
        data = {
            "computed_date": date.today().isoformat(),
            "sample_tickers": SAMPLE_TICKERS,
            "coverage_summary": coverage["summary"],
            "period_selections": {
                t: {
                    "basis": r["selection"].period_basis if r["selection"] else None,
                    "period_end": r["selection"].period_end if r["selection"] else None,
                    "fiscal_year": r["selection"].fiscal_year if r["selection"] else None,
                }
                for t, r in period_results.items()
            },
        }
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  💾 Resultados salvos em: {out}")


if __name__ == "__main__":
    main()
