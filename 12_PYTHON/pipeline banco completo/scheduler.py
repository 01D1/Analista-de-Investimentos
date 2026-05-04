"""
scheduler.py — Automação do pipeline de valuation bancário
===========================================================

Executa o pipeline para todos os bancos configurados em dois modos:

  Modo 1 — Loop contínuo (schedule):
      python scheduler.py
      → roda às 07:30 e 18:00 de seg–sex, mantém processo em background

  Modo 2 — Execução imediata:
      python scheduler.py --agora
      → roda uma vez agora e encerra

  Modo 3 — Banco único imediato:
      python scheduler.py --agora --ticker BBDC4

Variáveis para configurar abaixo:
  TICKERS_AGENDADOS  — lista de tickers a processar
  HORARIOS           — horários diários (formato "HH:MM")
  NOTIFICAR_EMAIL    — True para enviar e-mail ao terminar
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Configuração ─────────────────────────────────────────────────────────────

TICKERS_AGENDADOS = ["BBDC4", "BBAS3", "ITUB4", "SANB11", "BPAC11"]

HORARIOS = ["07:30", "18:00"]   # executar nestes horários em dias úteis

# Email (opcional — requer smtplib configurado)
NOTIFICAR_EMAIL = False
EMAIL_DESTINO   = "voce@email.com"
EMAIL_ORIGEM    = "pipeline@email.com"
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
SMTP_SENHA      = ""   # use variável de ambiente na produção

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "scheduler.log",
                            encoding="utf-8", mode="a"),
    ]
)
logger = logging.getLogger("scheduler")


# ── Utilitários ───────────────────────────────────────────────────────────────

def _e_dia_util() -> bool:
    return datetime.today().weekday() < 5   # seg=0 … sex=4


def _rodar_pipeline(tickers: list[str], sem_cache: bool = False) -> dict:
    """
    Executa main.py --batch em subprocess e retorna resumo dos resultados.
    """
    if not tickers:
        return {}

    cmd = [sys.executable, str(ROOT / "main.py"), "--batch"] + tickers
    if sem_cache:
        cmd.append("--sem-cache")

    logger.info(f"Executando: {' '.join(cmd)}")
    t0 = datetime.now()

    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,   # 30 min máximo
        )
    except subprocess.TimeoutExpired:
        logger.error("Pipeline excedeu 30 min — processo encerrado")
        return {"erro": "timeout"}
    except Exception as e:
        logger.error(f"Erro ao chamar pipeline: {e}")
        return {"erro": str(e)}

    duracao = (datetime.now() - t0).seconds
    logger.info(f"Pipeline concluído em {duracao}s | returncode={proc.returncode}")

    if proc.returncode != 0:
        logger.error("Saída de erro:\n" + proc.stderr[-3000:])

    # Extrai resumo das últimas linhas do stdout
    linhas = proc.stdout.splitlines()
    resumo = [l for l in linhas if any(k in l for k in
              ["Preço Justo", "Upside", "TIR:", "Empresa:", "Arquivo gerado",
               "ERRO", "BATCH", "Sucesso", "Erros"])]

    logger.info("Resumo:\n" + "\n".join(resumo[-30:]))

    return {
        "returncode": proc.returncode,
        "duracao_s":  duracao,
        "resumo":     resumo,
        "stdout":     proc.stdout,
    }


def _enviar_email(assunto: str, corpo: str):
    """Envia e-mail de notificação (requer configuração SMTP acima)."""
    if not NOTIFICAR_EMAIL or not EMAIL_DESTINO:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg       = MIMEText(corpo, "plain", "utf-8")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_ORIGEM
        msg["To"]      = EMAIL_DESTINO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_ORIGEM, SMTP_SENHA)
            s.send_message(msg)
        logger.info(f"E-mail enviado para {EMAIL_DESTINO}")
    except Exception as e:
        logger.warning(f"Falha ao enviar e-mail: {e}")


# ── Tarefa agendada ───────────────────────────────────────────────────────────

def tarefa_diaria(tickers: list[str] | None = None):
    tickers = tickers or TICKERS_AGENDADOS
    if not _e_dia_util():
        logger.info("Final de semana — pulando execução")
        return

    logger.info(f"{'='*60}")
    logger.info(f"ATUALIZAÇÃO AGENDADA — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Bancos: {', '.join(tickers)}")
    logger.info(f"{'='*60}")

    resultado = _rodar_pipeline(tickers)

    assunto = (f"[Pipeline Valuation] Atualização {datetime.now().strftime('%d/%m/%Y')} "
               + ("✓ OK" if resultado.get("returncode") == 0 else "⚠ ERRO"))
    corpo = "\n".join(resultado.get("resumo", ["(sem resumo)"])) + (
        f"\n\nDuração: {resultado.get('duracao_s', '?')}s"
    )
    _enviar_email(assunto, corpo)


# ── Loop principal ────────────────────────────────────────────────────────────

def loop_agendado(tickers: list[str] | None = None):
    """Loop contínuo que verifica os horários configurados."""
    try:
        import schedule
    except ImportError:
        logger.error("Biblioteca 'schedule' não instalada. Execute: pip install schedule")
        sys.exit(1)

    for horario in HORARIOS:
        schedule.every().day.at(horario).do(tarefa_diaria, tickers=tickers)
        logger.info(f"Agendado: {horario} (dias úteis)")

    logger.info(f"Scheduler ativo. Próximas janelas: {', '.join(HORARIOS)}")
    logger.info("Pressione Ctrl+C para parar.\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Scheduler do pipeline de valuation bancário")
    p.add_argument("--agora",    action="store_true",
                   help="Executar imediatamente (sem aguardar horário)")
    p.add_argument("--ticker",   default=None, nargs="+",
                   help="Processar tickers específicos (padrão: todos)")
    p.add_argument("--sem-cache", action="store_true",
                   help="Forçar re-download de todos os dados")
    args = p.parse_args()

    tickers = args.ticker or TICKERS_AGENDADOS

    # Garante que o diretório de logs existe
    (ROOT / "logs").mkdir(exist_ok=True)

    if args.agora:
        logger.info("Modo: execução imediata")
        resultado = _rodar_pipeline(tickers, sem_cache=args.sem_cache)
        sys.exit(0 if resultado.get("returncode") == 0 else 1)
    else:
        loop_agendado(tickers)


if __name__ == "__main__":
    main()
