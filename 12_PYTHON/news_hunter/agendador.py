# -*- coding: utf-8 -*-
"""
agendador.py — News Hunter
============================
Executa automaticamente: coleta → geração de boletim → envio Telegram.

Usa a biblioteca `schedule` para gerenciar os horários.
Roda em loop contínuo (Ctrl+C para parar).

Horários e dias configurados em config.py:
  HORARIOS_ENVIO_TELEGRAM  = ["07:30", "12:00", "18:00"]
  RODAR_DIAS_UTEIS_APENAS  = True

Uso:
  python agendador.py
  python agendador.py --simular    (executa o job imediatamente para teste)
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
        logging.FileHandler(config.ARQUIVO_LOG, encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger("news_hunter.agendador")


# ── Utilitários ───────────────────────────────────────────────────────────────

def eh_dia_util() -> bool:
    """Retorna True se hoje é de segunda (0) a sexta (4)."""
    return datetime.now().weekday() < 5


# ── Job principal ─────────────────────────────────────────────────────────────

def job():
    """
    Executa o pipeline completo:
      1. Coleta de notícias via RSS
      2. Geração do boletim diário
      3. Envio pelo Telegram (se configurado)
    """
    if config.RODAR_DIAS_UTEIS_APENAS and not eh_dia_util():
        dia = datetime.now().strftime("%A %d/%m/%Y")
        logger.info("Hoje é fim de semana (%s). Execução ignorada.", dia)
        return

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logger.info("=" * 55)
    logger.info("Execução automática iniciada — %s", agora)
    logger.info("=" * 55)

    erros = []

    # 1. Coleta
    try:
        import banco
        import crawler
        banco.inicializar()
        resultado = crawler.ciclo_completo()
        logger.info(
            "Coleta: %d novas notícias em %d fontes.",
            resultado["novas"], resultado["fontes"]
        )
    except Exception as exc:
        logger.error("Erro na coleta: %s", exc, exc_info=True)
        erros.append(f"coleta: {exc}")

    # 2. Gerar boletim
    caminho_txt = None
    try:
        import gerar_boletim as gb
        # Desativa envio automático aqui — vamos controlar manualmente abaixo
        _ativo_orig = config.TELEGRAM_ATIVO
        config.TELEGRAM_ATIVO = False

        caminho_md, caminho_txt = gb.gerar_boletim()

        config.TELEGRAM_ATIVO = _ativo_orig
        logger.info("Boletim gerado: %s", caminho_md)
    except Exception as exc:
        logger.error("Erro ao gerar boletim: %s", exc, exc_info=True)
        erros.append(f"boletim: {exc}")
        config.TELEGRAM_ATIVO = getattr(config, "_ativo_orig_bkp", config.TELEGRAM_ATIVO)

    # 3. Envio pelo Telegram
    try:
        import telegram_client
        if telegram_client.telegram_configurado() and caminho_txt:
            conteudo = Path(caminho_txt).read_text(encoding="utf-8")
            ok = telegram_client.enviar_boletim(conteudo)
            if ok:
                logger.info("Boletim enviado pelo Telegram com sucesso.")
            else:
                logger.warning("Falha no envio pelo Telegram.")
                erros.append("telegram: falha no envio")
        elif not telegram_client.telegram_configurado():
            logger.info("Telegram não configurado — envio ignorado.")
    except Exception as exc:
        logger.error("Erro no envio Telegram: %s", exc, exc_info=True)
        erros.append(f"telegram: {exc}")

    if erros:
        logger.warning("Execução concluída com erros: %s", " | ".join(erros))
    else:
        logger.info("Execução automática concluída sem erros.")
    logger.info("-" * 55)


# ── Configuração dos agendamentos ─────────────────────────────────────────────

def configurar_agendamentos():
    """Registra os horários definidos em config.HORARIOS_ENVIO_TELEGRAM."""
    try:
        import schedule
    except ImportError:
        logger.error(
            "Biblioteca 'schedule' não instalada. "
            "Execute: pip install schedule>=1.2.0"
        )
        sys.exit(1)

    horarios = getattr(config, "HORARIOS_ENVIO_TELEGRAM", ["07:30", "12:00", "18:00"])

    if not horarios:
        logger.warning("Nenhum horário configurado em HORARIOS_ENVIO_TELEGRAM.")
        return schedule

    for horario in horarios:
        schedule.every().day.at(horario).do(job)
        logger.info("Agendamento registrado: %s", horario)

    return schedule


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="News Hunter — agendador automático"
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Executa o job imediatamente (útil para testar sem aguardar o horário)",
    )
    args = parser.parse_args()

    if args.simular:
        logger.info("Modo simulação: executando job agora...")
        job()
        return

    # ── Loop de agendamento ───────────────────────────────────────────────────
    schedule = configurar_agendamentos()

    logger.info("=" * 55)
    logger.info("NEWS HUNTER — Agendador ativo")
    logger.info("Dias úteis apenas: %s", config.RODAR_DIAS_UTEIS_APENAS)
    logger.info("Telegram ativo: %s", config.TELEGRAM_ATIVO)
    logger.info("Ctrl+C para parar.")
    logger.info("=" * 55)

    # Mostra próximas execuções
    proximos = schedule.jobs
    if proximos:
        logger.info("Próximas execuções agendadas:")
        for j in proximos:
            logger.info("  → %s", j.next_run)

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Agendador interrompido pelo usuário.")
            break
        except Exception as exc:
            logger.error("Erro inesperado no agendador: %s", exc, exc_info=True)
            time.sleep(60)   # aguarda 1 min antes de tentar novamente


if __name__ == "__main__":
    main()
