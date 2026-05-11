"""
scheduler.py
------------
Daemon de orquestração do Intelligence System com APScheduler.

Executa todos os jobs definidos em config/schedules.yaml nas janelas certas,
notifica via Telegram e mantém estado de execução.

Pipeline diário completo (dias úteis):
  06:00 → news_fetcher      (notícias overnight)
  06:30 → morning_call      (morning call com Claude)
  07:00 → b3_prices         (atualizar preços)
  19:00 → cvm_check         (verificar novos docs na CVM)
  19:30 → pipeline          (processar dados novos)
  20:00 → analyze           (recalcular métricas + risco + valuation)
  20:30 → content           (gerar posts/teses se análise nova)
  */hora → health_check     (monitoramento)

Semanal:
  Domingo 10:00 → weekly_review

Uso:
    from src.scheduler import start_scheduler
    start_scheduler()          # bloqueante (daemon)

    # Via CLI:
    python -m src.main daemon
"""

from __future__ import annotations

import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


# ── Jobs ──────────────────────────────────────────────────────────────────────


def job_news_fetcher() -> str:
    """Coleta notícias financeiras overnight (placeholder até news_fetcher.py)."""
    from config.settings import settings

    tickers = settings.active_tickers
    # TODO: implementar src/ingestion/news_fetcher.py
    log.info(f"[news_fetcher] verificando notícias para {len(tickers)} tickers...")
    return f"{len(tickers)} tickers verificados (news stub)"


def job_morning_call() -> str:
    """Gera morning call diário."""
    from src.content.morning_call import generate_morning_call

    path = generate_morning_call()
    return str(path)


def job_b3_prices() -> str:
    """Atualiza preços OHLCV em ingestion.db para todos os tickers ativos — ING-05.
    Replaces the previous Parquet-based stub."""
    from config.settings import settings
    from src.ingestion.b3_scraper import B3Scraper
    from src.ingestion.db import init_db, get_connection
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("ingest") as run_id:
        _log.info(f"[b3_prices] iniciado — run_id={run_id}")
        init_db()
        t0 = time.time()
        conn = get_connection()
        try:
            scraper = B3Scraper()
            total_inserted = 0
            total_gaps = 0
            failed = []

            for ticker in settings.active_tickers:
                try:
                    res = scraper.fetch_and_store(ticker, conn)
                    total_inserted += res.get("inserted", 0)
                    total_gaps += res.get("gaps", 0)
                    if res.get("error"):
                        failed.append(ticker)
                except Exception as exc:
                    _log.warning(f"[{ticker}] b3_prices falhou: {exc}")
                    failed.append(ticker)
        finally:
            conn.close()  # WR-06: always close connection even on exception
        duration_ms = int((time.time() - t0) * 1000)
        status = "ok" if not failed else "partial"

        # D-15: structured summary log
        _log.info(
            "[b3_prices] summary",
            source="b3_prices",
            records_inserted=total_inserted,
            records_updated=0,
            duration_ms=duration_ms,
            status=status,
            last_ingested_at=datetime.utcnow().isoformat(),
            gap_rows_inserted=total_gaps,
            failed_tickers=failed,
        )
        return f"b3_prices: inserted={total_inserted} gaps={total_gaps} failed={len(failed)}"


def job_cvm_check() -> str:
    """Verifica novos documentos na CVM para todos os tickers."""
    from config.settings import settings
    from src.ingestion.cvm_downloader import ingest_ticker

    downloaded = 0
    for ticker in settings.active_tickers:
        try:
            result = ingest_ticker(ticker, doc_types=["DFP", "ITR"], force=False)
            # WR-02: "downloaded" is dict[str, list[int]] — count total years downloaded
            dl = result.get("downloaded", {})
            downloaded += sum(len(v) for v in dl.values() if isinstance(v, list))
        except Exception as exc:
            log.warning(f"[cvm_check] [{ticker}] {exc}")
    return f"documentos novos: {downloaded}"


def job_pipeline() -> str:
    """Processa dados brutos para todos os tickers com dados novos."""
    from config.settings import settings
    from src.processing.pipeline import process_ticker

    total_ok = total_fail = 0
    for ticker in settings.active_tickers:
        try:
            result = process_ticker(ticker, force=False)
            total_ok += result.succeeded
            total_fail += result.failed
        except Exception as exc:
            log.warning(f"[pipeline] [{ticker}] {exc}")
            total_fail += 1
    return f"pipeline: ok={total_ok} falhas={total_fail}"


def job_analyze() -> str:
    """Recalcula métricas, risco, valuation e insights para todos os tickers."""
    from config.settings import settings
    from src.analysis.insight_engine import InsightEngine
    from src.analysis.metrics_engine import run_metrics
    from src.analysis.risk_engine import assess_risk
    from src.valuation.auto_dcf import run_valuation

    engine = InsightEngine()
    ok = fail = 0
    for ticker in settings.active_tickers:
        try:
            metrics = run_metrics(ticker, force=False)
            if metrics:
                assess_risk(ticker, force=False)
                run_valuation(ticker, force=False)
                engine.generate(ticker, force=False)
                ok += 1
            else:
                log.debug(f"[analyze] [{ticker}] sem dados novos — pulando")
        except Exception as exc:
            log.warning(f"[analyze] [{ticker}] {exc}")
            fail += 1
    return f"análise: ok={ok} falhas={fail}"


def job_content() -> str:
    """Gera morning call já foi feito às 06:30. Aqui gera posts/teses se análise nova."""
    from config.settings import settings
    from src.content.post_generator import generate_post

    generated = 0
    for ticker in settings.active_tickers:
        try:
            # Gerar post apenas se houve análise nova hoje
            output_dir = settings.data_output / ticker
            metrics_files = sorted(output_dir.glob("metrics_*.json"))
            if not metrics_files:
                continue
            mtime = datetime.fromtimestamp(metrics_files[-1].stat().st_mtime).date()
            if mtime == date.today():
                generate_post(ticker, force=False)
                generated += 1
        except Exception as exc:
            log.debug(f"[content] [{ticker}] {exc}")
    return f"posts gerados: {generated}"


def job_health_check() -> dict:
    """Verifica saúde do sistema e retorna relatório."""
    from config.settings import settings

    report: dict[str, dict] = {}

    # Vault acessível?
    vault_ok = settings.vault_path.exists()
    report["Vault Obsidian"] = {
        "ok": vault_ok,
        "msg": str(settings.vault_path) if vault_ok else "não encontrado",
    }

    # Data de última análise
    latest_analysis = None
    for ticker in settings.active_tickers[:3]:
        files = sorted((settings.data_output / ticker).glob("metrics_*.json"))
        if files:
            mtime = datetime.fromtimestamp(files[-1].stat().st_mtime)
            if latest_analysis is None or mtime > latest_analysis:
                latest_analysis = mtime
    report["Última Análise"] = {
        "ok": latest_analysis is not None,
        "msg": latest_analysis.strftime("%Y-%m-%d %H:%M") if latest_analysis else "nenhuma",
    }

    # Dados de preços
    price_dir = settings.data_raw / "prices"
    n_prices = len(list(price_dir.glob("*.parquet"))) if price_dir.exists() else 0
    report["Preços (parquet)"] = {
        "ok": n_prices > 0,
        "msg": f"{n_prices} arquivos",
    }

    # APIs configuradas
    report["Claude API"] = {
        "ok": bool(settings.anthropic_api_key),
        "msg": "configurada" if settings.anthropic_api_key else "não configurada",
    }
    report["Telegram"] = {
        "ok": bool(settings.telegram_bot_token),
        "msg": "configurado" if settings.telegram_bot_token else "não configurado",
    }

    return report


def job_weekly_review() -> str:
    """Gera resumo semanal com performance do portfólio."""
    import json

    from config.settings import settings
    from src.delivery.telegram_bot import get_bot

    lines = [f"Semana {date.today().isocalendar()[1]} / {date.today().year}", ""]
    lines.append("**Portfólio Monitorado**")

    for ticker in settings.active_tickers:
        output_dir = settings.data_output / ticker
        risk_path = output_dir / "risk_report.json"
        val_path = output_dir / "valuation.json"

        risk_sev = "?"
        upside = None

        if risk_path.exists():
            try:
                risk_sev = json.loads(risk_path.read_text()).get("overall_severity", "?")
            except Exception:
                pass
        if val_path.exists():
            try:
                val = json.loads(val_path.read_text())
                upside = val.get("scenarios", {}).get("base", {}).get("upside")
            except Exception:
                pass

        upside_str = f"upside {upside:+.1%}" if upside is not None else "sem valuation"
        lines.append(f"• {ticker}: risco={risk_sev.upper()} | {upside_str}")

    summary = "\n".join(lines)
    get_bot().send_weekly_review(summary)
    return summary


def job_cvm_ingest() -> str:
    """Ingestão CVM DFP/ITR/IPE para todos os tickers ativos — ING-01/02/03."""
    from config.settings import settings
    from src.ingestion.cvm_downloader import CVMDownloader
    from src.ingestion.db import init_db, get_connection
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("ingest") as run_id:
        _log.info(f"[cvm_ingest] iniciado — run_id={run_id}")
        init_db()
        t0 = time.time()
        conn = get_connection()
        try:
            downloader = CVMDownloader()
            raw_dir = settings.data_raw / "cvm"
            inserted = 0
            failed = []

            for ticker in settings.active_tickers:
                for year in [datetime.now().year, datetime.now().year - 1]:
                    for period_type in ("DFP", "ITR"):
                        try:
                            n = downloader.parse_and_store(
                                ticker, year, period_type, conn, raw_dir
                            )
                            inserted += n
                        except Exception as exc:
                            _log.warning(f"[{ticker}] {period_type} {year} falhou: {exc}")
                            failed.append(f"{ticker}/{period_type}/{year}")
                    try:
                        n = downloader.parse_and_store_ipe(ticker, year, conn)
                        inserted += n
                    except Exception as exc:
                        _log.warning(f"[{ticker}] IPE {year} falhou: {exc}")
                        failed.append(f"{ticker}/IPE/{year}")
        finally:
            conn.close()  # WR-06: always close connection even on exception
        duration_ms = int((time.time() - t0) * 1000)
        status = "ok" if not failed else "partial"

        # D-15: structured summary log
        _log.info(
            "[cvm_ingest] summary",
            source="cvm_ingest",
            records_inserted=inserted,
            records_updated=0,
            duration_ms=duration_ms,
            status=status,
            last_ingested_at=datetime.utcnow().isoformat(),
            failed_jobs=failed,
        )
        return f"cvm_ingest: inserted={inserted} failed={len(failed)}"


def job_bcb_macro() -> str:
    """Ingestão séries macro BCB SGS (Selic, IPCA, PTAX, CDS Brasil, PIB) — ING-04."""
    from src.ingestion.bcb import ingest_all_series
    from src.ingestion.db import init_db, get_connection
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("ingest") as run_id:
        _log.info(f"[bcb_macro] iniciado — run_id={run_id}")
        init_db()
        t0 = time.time()
        conn = get_connection()
        try:
            result = ingest_all_series(conn)
        finally:
            conn.close()  # WR-06: always close connection even on exception
        duration_ms = int((time.time() - t0) * 1000)
        status = "ok" if not result["failed"] else "partial"

        # D-15: structured summary log
        _log.info(
            "[bcb_macro] summary",
            source="bcb_macro",
            records_inserted=result["inserted"],
            records_updated=result["updated"],
            duration_ms=duration_ms,
            status=status,
            last_ingested_at=result.get("last_ingested_at", datetime.utcnow().isoformat()),
            failed_series=result["failed"],
            stale_series=result.get("stale", []),
        )
        return f"bcb_macro: inserted={result['inserted']} failed={result['failed']}"


def job_news_ingest() -> str:
    """Coleta notícias via news_hunter subprocess + sincroniza para ingestion.db — ING-06/07.
    D-01: news_hunter internals not modified. D-02: agendador.py not launched."""
    from src.ingestion.db import init_db, get_connection
    from src.ingestion.news_sync import sync_news_to_ingestion_db
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    news_hunter_dir = Path(__file__).parent.parent / "news_hunter"

    with bind_run_id("ingest") as run_id:
        _log.info(f"[news_ingest] iniciado — run_id={run_id}")
        t0 = time.time()

        # Step 1: Run news_hunter crawler as subprocess (list form, not shell=True)
        # SECURITY: list form prevents shell injection; cwd isolates news_hunter imports
        result = subprocess.run(
            [sys.executable, "main.py", "--coletar"],
            cwd=news_hunter_dir,
            timeout=300,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _log.warning(
                f"[news_ingest] subprocess terminou com código {result.returncode}: "
                f"{result.stderr[:500]}"
            )

        # Step 2: Sync from banco.db to ingestion.db
        init_db()
        conn = get_connection()
        inserted = sync_news_to_ingestion_db(conn)
        conn.close()

        duration_ms = int((time.time() - t0) * 1000)
        status = "ok" if result.returncode == 0 else "partial"

        # D-15: structured summary log
        _log.info(
            "[news_ingest] summary",
            source="news_ingest",
            records_inserted=inserted,
            records_updated=0,
            duration_ms=duration_ms,
            status=status,
            last_ingested_at=datetime.utcnow().isoformat(),
            subprocess_returncode=result.returncode,
        )
        return f"news_ingest: inserted={inserted} subprocess_rc={result.returncode}"


def job_financial_engine() -> str:
    """Calcula LTM, múltiplos, DCF e sinais técnicos para todos os tickers — FIN-01..06.
    D-03: daily scheduled job; D-12: public job API.
    """
    from src.financial_engine import run_all
    from src.utils.logger import bind_run_id, get_logger as _get
    from datetime import datetime

    _log = _get(__name__)
    with bind_run_id("financial") as run_id:
        _log.info(f"[financial_engine] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        duration_ms = int((time.time() - t0) * 1000)
        _log.info(
            "[financial_engine] summary",
            source="financial_engine",
            records_inserted=ok,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
            last_ingested_at=datetime.utcnow().isoformat(),
            failed_tickers=fail,
        )
        return f"financial_engine: ok={ok} failed={fail}"


# ── Registro de jobs ──────────────────────────────────────────────────────────

_JOB_REGISTRY: dict[str, Callable] = {
    "news_fetcher": job_news_fetcher,
    "morning_call": job_morning_call,
    "b3_prices":    job_b3_prices,    # updated to DB-writing version (ING-05)
    "cvm_check":    job_cvm_check,
    "pipeline":     job_pipeline,
    "analyze":      job_analyze,
    "content":      job_content,
    "health_check": job_health_check,
    "weekly_review": job_weekly_review,
    "cvm_ingest":        job_cvm_ingest,         # ING-01/02/03
    "bcb_macro":         job_bcb_macro,          # ING-04
    "news_ingest":       job_news_ingest,        # ING-06/07
    "financial_engine":  job_financial_engine,   # FIN-01..06
}


# ── Wrapper com notificação ───────────────────────────────────────────────────


def _run_job(name: str, fn: Callable, notify: bool = True) -> None:
    """Executa um job com timing, log e notificação Telegram."""
    from src.delivery.telegram_bot import get_bot

    log.info(f"[scheduler] ▶ {name}")
    t0 = time.time()
    success = False
    detail = ""

    try:
        result = fn()
        success = True
        if isinstance(result, dict):
            # health_check retorna dict — enviar via send_health_report
            get_bot().send_health_report(result)
            detail = f"{sum(1 for v in result.values() if v.get('ok'))} / {len(result)} OK"
        else:
            detail = str(result)[:200] if result else ""
    except Exception:
        detail = traceback.format_exc(limit=3)
        log.error(f"[scheduler] ✗ {name}:\n{detail}")

    duration = time.time() - t0
    log.info(f"[scheduler] {'✓' if success else '✗'} {name} ({duration:.1f}s)")

    if notify:
        get_bot().send_job_result(
            job_name=name,
            success=success,
            detail=detail,
            duration_s=duration,
        )

    # Após morning call → enviar arquivo para Telegram
    if name == "morning_call" and success:
        try:
            from config.settings import settings

            today = date.today()
            mc_path = settings.vault_path / "14_OUTPUTS" / f"morning_call_{today}.md"
            if mc_path.exists():
                get_bot().send_morning_call_summary(mc_path)
        except Exception as exc:
            log.warning(f"[scheduler] falha ao enviar morning call: {exc}")

    # Após análise com riscos altos → alertar
    if name == "analyze" and success:
        _check_and_alert_risks()


def _check_and_alert_risks() -> None:
    """Verifica se algum ticker tem risco HIGH/CRITICAL e notifica."""
    import json

    from config.settings import settings
    from src.delivery.telegram_bot import get_bot

    for ticker in settings.active_tickers:
        risk_path = settings.data_output / ticker / "risk_report.json"
        if not risk_path.exists():
            continue
        try:
            risk = json.loads(risk_path.read_text())
            severity = risk.get("overall_severity", "low")
            if severity in ("high", "critical"):
                risks = [
                    r["description"]
                    for r in risk.get("risks", [])
                    if r.get("severity") in ("high", "critical")
                ]
                get_bot().send_risk_alert(ticker, severity, risks)
        except Exception:
            pass


# ── Scheduler ─────────────────────────────────────────────────────────────────


class IntelligenceScheduler:
    """
    APScheduler configurado com os jobs do Intelligence System.

    Carrega cron expressions de config/schedules.yaml e mapeia
    cada job_name → função Python.
    """

    def __init__(self):
        from config.settings import settings

        self.settings = settings

    def _load_schedules(self) -> list[dict]:
        import yaml

        path = Path(__file__).parent.parent / "config" / "schedules.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return data.get("schedules", [])

    def build(self):
        """Constrói e retorna o scheduler APScheduler configurado."""
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            raise ImportError("APScheduler não instalado. Execute: pip install apscheduler>=3.10.0")

        scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
        schedules = self._load_schedules()
        registered = 0

        for entry in schedules:
            job_name = entry.get("job")
            cron = entry.get("cron")
            desc = entry.get("description", "")

            if not job_name or not cron:
                log.warning(f"[scheduler] entrada inválida no schedules.yaml: {entry}")
                continue

            fn = _JOB_REGISTRY.get(job_name)
            if fn is None:
                log.warning(f"[scheduler] job '{job_name}' não encontrado no registry")
                continue

            # Parsear cron expression (min hora dom mes dow)
            parts = cron.strip().split()
            if len(parts) != 5:
                log.warning(f"[scheduler] cron inválido para {job_name}: {cron!r}")
                continue

            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="America/Sao_Paulo",
            )

            # Closure para capturar job_name e fn corretamente
            def make_wrapper(n, f):
                def wrapper():
                    _run_job(n, f, notify=True)

                wrapper.__name__ = n
                return wrapper

            scheduler.add_job(
                func=make_wrapper(job_name, fn),
                trigger=trigger,
                id=job_name,
                name=f"{job_name} — {desc}",
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,  # 5 min de tolerância
            )

            log.info(f"[scheduler] registrado: {job_name!r} @ {cron!r} ({desc})")
            registered += 1

        log.success(f"[scheduler] {registered} jobs registrados")
        return scheduler

    def start(self) -> None:
        """
        Inicia o daemon scheduler (bloqueante).

        Envia notificação de startup no Telegram.
        """
        from src.delivery.telegram_bot import get_bot

        log.info("=" * 60)
        log.info("Intelligence System — Daemon iniciando")
        log.info(f"Ambiente: {self.settings.env}")
        log.info(f"Tickers: {', '.join(self.settings.active_tickers)}")
        log.info(f"Vault: {self.settings.vault_path}")
        log.info("=" * 60)

        scheduler = self.build()

        # Notificar startup
        next_jobs = []
        for job in scheduler.get_jobs()[:5]:
            next_run = job.next_run_time
            if next_run:
                next_jobs.append(f"• {job.id}: {next_run.strftime('%H:%M')}")

        startup_msg = (
            "🤖 *Intelligence System — Online*\n"
            f"Ambiente: `{self.settings.env}`\n"
            f"Tickers: `{len(self.settings.active_tickers)}`\n\n"
            "*Próximas execuções:*\n" + "\n".join(next_jobs)
        )
        get_bot().send(startup_msg)

        log.info("[scheduler] iniciando loop (Ctrl+C para parar)...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("[scheduler] daemon encerrado pelo usuário")
            get_bot().send("🛑 *Intelligence System — Offline*\nDaemon encerrado.")

    def run_job_now(self, job_name: str) -> None:
        """Executa um job imediatamente (para testes/CLI)."""
        fn = _JOB_REGISTRY.get(job_name)
        if fn is None:
            raise ValueError(
                f"Job não encontrado: {job_name!r}. Disponíveis: {list(_JOB_REGISTRY)}"
            )
        _run_job(job_name, fn, notify=False)

    def list_jobs(self) -> list[dict]:
        """Lista todos os jobs com próxima execução."""
        scheduler = self.build()
        result = []
        for job in scheduler.get_jobs():
            result.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else "?",
                }
            )
        scheduler.shutdown(wait=False)
        return result


# ── Função de alto nível ──────────────────────────────────────────────────────


def start_scheduler() -> None:
    """Inicia o daemon do Intelligence System (bloqueante)."""
    IntelligenceScheduler().start()
