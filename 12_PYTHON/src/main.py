"""
Ponto de entrada único do Intelligence System.

Uso:
    python -m src.main --help
    python -m src.main ingest --ticker BBAS3
    python -m src.main ingest --all
    python -m src.main process --ticker BBAS3
    python -m src.main analyze --ticker BBAS3
    python -m src.main content morning-call
    python -m src.main add-ticker PETR4 --type oil_gas
    python -m src.main status
    python -m src.main daemon
"""

import argparse
import sys

from config.settings import settings
from src.utils.logger import configure_logging, get_logger

configure_logging(settings.logs_dir, level="DEBUG" if settings.env == "development" else "INFO")
log = get_logger(__name__)


# ── Subcomandos ───────────────────────────────────────────────────────────────


def cmd_ingest(args: argparse.Namespace) -> None:
    from src.ingestion.b3_scraper import B3Scraper
    from src.ingestion.cvm_downloader import ingest_ticker

    tickers = settings.active_tickers if args.all else [args.ticker]
    if not tickers:
        log.error("Informe --ticker TICKER ou --all")
        sys.exit(1)

    doc_types = (
        args.doc_types.upper().split(",")
        if hasattr(args, "doc_types") and args.doc_types
        else ["DFP", "ITR"]
    )
    force = getattr(args, "force", False)
    prices = getattr(args, "prices", True)

    scraper = B3Scraper()
    for ticker in tickers:
        log.info(f"[{ticker}] iniciando ingestão...")
        try:
            result = ingest_ticker(ticker, doc_types=doc_types, force=force)
            log.info(f"[{ticker}] CVM: {result['downloaded']}")
        except KeyError as exc:
            log.error(f"[{ticker}] {exc}")
        except Exception as exc:
            log.error(f"[{ticker}] falha na ingestão CVM: {exc}")

        if prices:
            try:
                df = scraper.fetch(ticker, force=force)
                if not df.empty:
                    log.info(
                        f"[{ticker}] preços: {len(df)} dias ({df.index.min().date()} → {df.index.max().date()})"
                    )
            except Exception as exc:
                log.error(f"[{ticker}] falha ao buscar preços: {exc}")


def cmd_process(args: argparse.Namespace) -> None:
    from src.processing.pipeline import process_ticker

    tickers = settings.active_tickers if getattr(args, "all", False) else [args.ticker]
    force = getattr(args, "force", False)
    years_arg = getattr(args, "years", None)
    years = list(map(int, years_arg.split(","))) if years_arg else None

    total_ok = total_fail = 0
    for ticker in tickers:
        result = process_ticker(ticker, years=years, force=force)
        total_ok += result.succeeded
        total_fail += result.failed

    log.info(f"Processamento concluído — ok={total_ok} falhas={total_fail}")


def cmd_analyze(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.table import Table

    from src.analysis.insight_engine import InsightEngine
    from src.analysis.metrics_engine import run_metrics
    from src.analysis.risk_engine import assess_risk
    from src.valuation.auto_dcf import run_valuation

    tickers = settings.active_tickers if getattr(args, "all", False) else [args.ticker]
    force = getattr(args, "force", False)
    console = Console()

    for ticker in tickers:
        log.info(f"[{ticker}] iniciando análise completa...")

        # 1. Métricas
        metrics = run_metrics(ticker, force=force)
        if not metrics:
            log.warning(f"[{ticker}] sem dados — execute 'process' primeiro")
            continue

        # 2. Risco
        risk = assess_risk(ticker, force=force)

        # 3. Valuation
        valuation = run_valuation(ticker, force=force)

        # 4. Insights
        engine = InsightEngine()
        insights = engine.generate(ticker, force=force)

        # ── Exibir resultado no terminal ──────────────────────────────────
        years = sorted(metrics.keys())
        last = metrics[years[-1]]

        from src.valuation.sector_config import SectorConfig

        cfg = SectorConfig.for_ticker(ticker)

        t = Table(title=f"{ticker} [{cfg.sector_type}] — Análise {last.get('year', '?')}")
        t.add_column("Métrica", style="cyan")
        t.add_column("Valor", style="green", justify="right")

        # Usar key_metrics definidas no sectors.yaml para o setor
        key_metrics = last.get("key_metrics") or cfg.key_metrics
        for metric in key_metrics:
            val = last.get(metric)
            fmt = _metric_fmt(metric)
            label = _metric_label(metric)
            _add_row(t, label, val, fmt=fmt)

        console.print(t)

        # Risco
        console.print(
            f"\n[bold]Risco:[/bold] {risk.overall_severity.upper()} ({len(risk.risks)} alertas)"
        )
        for r in risk.risks[:3]:
            console.print(f"  • {r}")

        # Valuation
        if valuation:
            console.print("\n[bold]Valuation:[/bold]")
            console.print(valuation.summary())

        # Insights
        if insights:
            console.print("\n[bold]Insights:[/bold]")
            for ins in insights:
                console.print(f"  {ins}")


_METRIC_LABELS: dict[str, str] = {
    "roe": "ROE",
    "roa": "ROA",
    "rote": "ROTE",
    "roic": "ROIC",
    "nii_margin": "NIM (NII/Ativos)",
    "efficiency_ratio": "Índice de Eficiência",
    "leverage": "Alavancagem (Ativos/PL)",
    "pdd_ratio": "PDD/Carteira",
    "cost_of_credit": "Custo de Crédito",
    "fee_share": "Fee Share",
    "ebitda_margin": "Margem EBITDA",
    "net_margin": "Margem Líquida",
    "gross_margin": "Margem Bruta",
    "ebit_margin": "Margem EBIT",
    "nd_ebitda": "DL/EBITDA",
    "interest_coverage": "Cobertura de Juros",
    "fcf": "FCF (R$ mi)",
    "fcf_conversion": "Conversão de FCF",
    "fcf_yield": "FCF Yield",
    "capex_to_revenue": "Capex/Receita",
    "revenue_growth": "Crescimento Receita",
    "ebitda_growth": "Crescimento EBITDA",
    "net_income_growth": "Crescimento Lucro",
    "nii_growth": "Crescimento NII",
    "asset_growth": "Crescimento Ativos",
    "loan_growth": "Crescimento Carteira",
    "pb_ratio": "P/VP",
    "pe_ratio": "P/L",
    "dividend_yield": "Dividend Yield",
    "ev_ebitda": "EV/EBITDA",
}

_METRIC_FMTS: dict[str, str] = {
    "roe": "pct",
    "roa": "pct",
    "rote": "pct",
    "roic": "pct",
    "nii_margin": "pct",
    "efficiency_ratio": "pct",
    "pdd_ratio": "pct",
    "cost_of_credit": "pct",
    "fee_share": "pct",
    "ebitda_margin": "pct",
    "net_margin": "pct",
    "gross_margin": "pct",
    "ebit_margin": "pct",
    "fcf_conversion": "pct",
    "fcf_yield": "pct",
    "capex_to_revenue": "pct",
    "revenue_growth": "pct",
    "ebitda_growth": "pct",
    "net_income_growth": "pct",
    "nii_growth": "pct",
    "asset_growth": "pct",
    "loan_growth": "pct",
    "dividend_yield": "pct",
    "leverage": "x",
    "nd_ebitda": "x",
    "interest_coverage": "x",
    "pb_ratio": "x",
    "pe_ratio": "x",
    "ev_ebitda": "x",
    "fcf": "r$mi",
}


def _metric_label(key: str) -> str:
    return _METRIC_LABELS.get(key, key.replace("_", " ").title())


def _metric_fmt(key: str) -> str:
    return _METRIC_FMTS.get(key, "")


def _add_row(table, label: str, value, fmt: str = "") -> None:
    if value is None:
        table.add_row(label, "—")
        return
    if fmt == "pct":
        table.add_row(label, f"{value:.1%}")
    elif fmt == "x":
        table.add_row(label, f"{value:.1f}x")
    elif fmt == "r$mi":
        table.add_row(label, f"R$ {value / 1000:,.0f} mi")
    else:
        table.add_row(label, str(value))


def cmd_content(args: argparse.Namespace) -> None:
    action = args.action
    ticker = getattr(args, "ticker", None)
    force = getattr(args, "force", False)
    log.info(f"Gerando conteúdo: {action}")

    if action == "morning-call":
        from src.content.morning_call import generate_morning_call

        path = generate_morning_call(force=force)
        log.success(f"Morning call salvo: {path}")

    elif action == "post":
        if not ticker:
            log.error("'post' requer --ticker TICKER")
            sys.exit(1)
        from src.content.post_generator import generate_post

        quarter = getattr(args, "quarter", None)
        year = getattr(args, "year", None)
        result_type = "quarterly" if quarter else "annual"
        path = generate_post(
            ticker, result_type=result_type, quarter=quarter, year=year, force=force
        )
        log.success(f"Post salvo: {path}")

    elif action == "thesis":
        if not ticker:
            # Gerar tese para todos os tickers ativos
            tickers = settings.active_tickers
        else:
            tickers = [ticker]
        from src.content.thesis_builder import build_thesis

        for t in tickers:
            path = build_thesis(t, force=force)
            log.success(f"[{t}] Tese salva: {path}")

    else:
        log.error(f"Ação desconhecida: {action}")
        sys.exit(1)


def cmd_add_ticker(args: argparse.Namespace) -> None:
    import yaml

    config_dir = settings.logs_dir.parent / "config"
    tickers_path = config_dir / "tickers.yaml"
    cvm_path = config_dir / "cvm_codes.yaml"

    # ── tickers.yaml ──────────────────────────────────────────────────────────
    with open(tickers_path) as f:
        data = yaml.safe_load(f)

    existing = [t["ticker"] for t in data["tickers"]]
    if args.ticker in existing:
        log.warning(f"{args.ticker} já está na lista de tickers")
    else:
        data["tickers"].append(
            {
                "ticker": args.ticker,
                "name": args.name or args.ticker,
                "type": args.type,
                "sector": args.sector or "unknown",
                "active": True,
                "priority": args.priority,
            }
        )
        with open(tickers_path, "w") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        log.info(f"{args.ticker} adicionado ao tickers.yaml")

    # ── cvm_codes.yaml ────────────────────────────────────────────────────────
    if args.cvm_code:
        with open(cvm_path) as f:
            cvm_data = yaml.safe_load(f)

        codes = cvm_data.get("cvm_codes", {})
        if args.ticker in codes:
            log.warning(f"{args.ticker} já tem código CVM: {codes[args.ticker]}")
        else:
            codes[args.ticker] = str(args.cvm_code).zfill(6)
            cvm_data["cvm_codes"] = codes
            with open(cvm_path, "w") as f:
                yaml.dump(cvm_data, f, allow_unicode=True, sort_keys=False)
            log.info(f"{args.ticker} → CVM {args.cvm_code} salvo em cvm_codes.yaml")
    else:
        log.warning(
            f"Código CVM não informado para {args.ticker}. "
            "Sem ele o sistema não consegue baixar documentos da CVM.\n"
            "  Descubra em: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/\n"
            f"  Depois execute: python3 -m src.main add-ticker {args.ticker} "
            f"--type {args.type} --cvm-code XXXXXX"
        )

    # ── Iniciar ingestão imediatamente se solicitado ──────────────────────────
    if getattr(args, "ingest_now", False) and args.cvm_code:
        log.info(f"Iniciando ingestão imediata para {args.ticker}...")
        from src.ingestion.b3_scraper import B3Scraper
        from src.ingestion.cvm_downloader import ingest_ticker

        try:
            result = ingest_ticker(args.ticker)
            log.info(f"[{args.ticker}] CVM: {result.get('downloaded', 0)} documentos")
        except Exception as exc:
            log.error(f"[{args.ticker}] falha na ingestão: {exc}")
        try:
            B3Scraper().fetch(args.ticker)
            log.info(f"[{args.ticker}] preços baixados")
        except Exception as exc:
            log.error(f"[{args.ticker}] falha nos preços: {exc}")

    log.success(
        f"{args.ticker} configurado. Para popular os dados:\n"
        f"  python3 -m src.main ingest  --ticker {args.ticker}\n"
        f"  python3 -m src.main process --ticker {args.ticker}\n"
        f"  python3 -m src.main analyze --ticker {args.ticker}"
    )


def cmd_status(_args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.table import Table

    from src.processing.storage import ProcessedStore

    console = Console()

    # Tabela de configuração
    cfg = Table(title="Intelligence System — Configuração")
    cfg.add_column("Item", style="cyan")
    cfg.add_column("Valor", style="green")
    cfg.add_row("Ambiente", settings.env)
    cfg.add_row("Tickers ativos", str(len(settings.active_tickers)))
    cfg.add_row("Supabase", "configurado" if settings.supabase_url else "não configurado")
    cfg.add_row("Telegram", "configurado" if settings.telegram_bot_token else "não configurado")
    cfg.add_row("Claude API", "configurada" if settings.anthropic_api_key else "não configurada")
    console.print(cfg)

    # Tabela de dados processados
    store = ProcessedStore()
    df = store.status()
    proc = Table(title="Dados Processados")
    proc.add_column("Ticker", style="cyan")
    proc.add_column("Anos", style="yellow", justify="right")
    proc.add_column("Períodos", style="green")
    for _, row in df.iterrows():
        color = "green" if row["years_processed"] > 0 else "red"
        proc.add_row(
            row["ticker"],
            f"[{color}]{row['years_processed']}[/{color}]",
            row["years"] or "—",
        )
    console.print(proc)


def cmd_daemon(_args: argparse.Namespace) -> None:
    from src.scheduler import start_scheduler

    log.info("Iniciando daemon do Intelligence System...")
    log.info("Tickers monitorados: " + ", ".join(settings.active_tickers))
    start_scheduler()  # bloqueante


def cmd_run_job(args: argparse.Namespace) -> None:
    from src.scheduler import IntelligenceScheduler

    scheduler = IntelligenceScheduler()
    log.info(f"Executando job '{args.job}' manualmente...")
    scheduler.run_job_now(args.job)
    log.success(f"Job '{args.job}' concluído.")


def cmd_jobs(_args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.table import Table

    from src.scheduler import IntelligenceScheduler

    console = Console()
    jobs = IntelligenceScheduler().list_jobs()

    t = Table(title="Jobs do Scheduler")
    t.add_column("ID", style="cyan")
    t.add_column("Próxima execução", style="green")
    t.add_column("Descrição", style="white")
    for j in jobs:
        t.add_row(j["id"], j["next_run"], j["name"])
    console.print(t)


def cmd_test(_args: argparse.Namespace) -> None:
    log.info("Teste de inicialização do sistema...")
    log.info(f"Ambiente: {settings.env}")
    log.info(f"Tickers ativos ({len(settings.active_tickers)}): {settings.active_tickers}")
    log.info(f"Data raw: {settings.data_raw}")
    log.success("Sistema inicializado com sucesso.")


# ── Parser ────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="intelligence",
        description="Intelligence System — análise financeira autônoma",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Baixar dados da CVM e preços da B3")
    group = p_ingest.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker", metavar="TICKER")
    group.add_argument("--all", action="store_true")
    p_ingest.add_argument(
        "--doc-types",
        metavar="DFP,ITR",
        default="DFP,ITR",
        help="Tipos de documento CVM (default: DFP,ITR)",
    )
    p_ingest.add_argument(
        "--no-prices",
        dest="prices",
        action="store_false",
        default=True,
        help="Pular download de preços via yfinance",
    )
    p_ingest.add_argument(
        "--force", action="store_true", help="Re-baixar mesmo se já existir localmente"
    )
    p_ingest.set_defaults(func=cmd_ingest)

    # process
    p_process = sub.add_parser(
        "process", help="Processar dados brutos (raw → validado → persistido)"
    )
    group2 = p_process.add_mutually_exclusive_group(required=True)
    group2.add_argument("--ticker", metavar="TICKER")
    group2.add_argument("--all", action="store_true")
    p_process.add_argument(
        "--years", metavar="2019,2020,...", help="Anos específicos (default: 2019 até hoje)"
    )
    p_process.add_argument("--force", action="store_true", help="Reprocessar mesmo se já existir")
    p_process.set_defaults(func=cmd_process)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Calcular métricas, risco, valuation e insights")
    group3 = p_analyze.add_mutually_exclusive_group(required=True)
    group3.add_argument("--ticker", metavar="TICKER")
    group3.add_argument("--all", action="store_true")
    p_analyze.add_argument("--force", action="store_true", help="Recalcular mesmo se cache existir")
    p_analyze.set_defaults(func=cmd_analyze)

    # content
    p_content = sub.add_parser("content", help="Gerar conteúdo com IA (morning call, posts, teses)")
    p_content.add_argument("action", choices=["morning-call", "post", "thesis"])
    p_content.add_argument(
        "--ticker",
        metavar="TICKER",
        help="Ticker alvo (obrigatório para 'post'; opcional para 'thesis')",
    )
    p_content.add_argument(
        "--quarter", metavar="1-4", type=int, help="Trimestre (somente para post trimestral)"
    )
    p_content.add_argument("--year", metavar="YYYY", type=int, help="Ano de referência")
    p_content.add_argument(
        "--force", action="store_true", help="Regerar mesmo se arquivo já existir"
    )
    p_content.set_defaults(func=cmd_content)

    # add-ticker
    p_add = sub.add_parser("add-ticker", help="Adicionar novo ticker ao sistema")
    p_add.add_argument("ticker", metavar="TICKER")
    p_add.add_argument(
        "--type",
        required=True,
        metavar="TYPE",
        help="Setor: bank, industrial, retail, oil_gas, utilities, telecom, etc.",
    )
    p_add.add_argument(
        "--cvm-code",
        metavar="XXXXXX",
        help="Código CVM da empresa (6 dígitos) — necessário para baixar documentos",
    )
    p_add.add_argument("--name", metavar="NOME", help="Nome da empresa (ex: 'Petrobras')")
    p_add.add_argument(
        "--sector", metavar="SECTOR", help="Setor macro (ex: energy, financials, industrials)"
    )
    p_add.add_argument("--priority", default="medium", choices=["low", "medium", "high"])
    p_add.add_argument(
        "--ingest-now",
        action="store_true",
        help="Iniciar download dos dados imediatamente após adicionar",
    )
    p_add.set_defaults(func=cmd_add_ticker)

    # status
    p_status = sub.add_parser("status", help="Exibir status do sistema")
    p_status.set_defaults(func=cmd_status)

    # daemon
    p_daemon = sub.add_parser("daemon", help="Executar em modo contínuo com scheduler (bloqueante)")
    p_daemon.set_defaults(func=cmd_daemon)

    # run-job
    p_runjob = sub.add_parser("run-job", help="Executar um job específico imediatamente")
    p_runjob.add_argument(
        "job",
        choices=[
            "news_fetcher",
            "morning_call",
            "b3_prices",
            "cvm_check",
            "pipeline",
            "analyze",
            "content",
            "health_check",
            "weekly_review",
        ],
        metavar="JOB",
    )
    p_runjob.set_defaults(func=cmd_run_job)

    # jobs
    p_jobs = sub.add_parser("jobs", help="Listar jobs e próximas execuções")
    p_jobs.set_defaults(func=cmd_jobs)

    # test
    p_test = sub.add_parser("test", help="Verificar se o sistema inicializa corretamente")
    p_test.set_defaults(func=cmd_test)

    return parser


def app() -> None:
    # Startup guard: only runs when CLI is invoked directly — never during import/pytest
    if settings.env == "production":
        _missing = [
            k for k in ("anthropic_api_key", "telegram_bot_token", "telegram_chat_id")
            if not getattr(settings, k, "")
        ]
        if _missing:
            log.error(f"[startup] variáveis obrigatórias ausentes: {_missing}")
            sys.exit(1)
        log.info("[startup] configuração de produção validada")

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    app()
