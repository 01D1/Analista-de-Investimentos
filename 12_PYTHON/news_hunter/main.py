# -*- coding: utf-8 -*-
"""
main.py — News Hunter
======================
Orquestrador central do sistema.

Comandos:
  python main.py --coletar               → executa um ciclo de coleta
  python main.py --gerar-boletim         → gera o boletim do dia
  python main.py --coletar-e-gerar       → coleta + gera boletim
  python main.py --testar-telegram       → envia mensagem de teste
  python main.py --enviar-telegram       → gera (ou lê último) boletim e envia
  python main.py --coletar-gerar-enviar  → pipeline completo com envio Telegram
"""

import argparse
import logging
import sys
from pathlib import Path

import banco
import config

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
logger = logging.getLogger("news_hunter.main")


def _ler_ultimo_boletim() -> str:
    """Lê o arquivo .txt do boletim mais recente em boletins/."""
    pasta = Path(__file__).parent / config.PASTA_BOLETINS
    if not pasta.exists():
        return ""
    arquivos = sorted(pasta.glob("boletim_*.txt"), reverse=True)
    if not arquivos:
        return ""
    return arquivos[0].read_text(encoding="utf-8")


def cmd_testar_telegram():
    """Envia uma mensagem de teste para verificar a conexão."""
    import telegram_client
    print("\n  🔌 Testando conexão com Telegram...\n")
    telegram_client.testar_conexao()


def cmd_enviar_telegram():
    """Gera (ou lê último) boletim e envia pelo Telegram."""
    import telegram_client

    if not telegram_client.telegram_configurado():
        print(
            "\n  ❌ Telegram não configurado.\n"
            "  Configure TELEGRAM_ATIVO, TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no config.py\n"
        )
        return

    # Tenta gerar boletim do dia; se falhar, usa o último salvo
    try:
        import gerar_boletim as gb
        _, caminho_txt = gb.gerar_boletim()
        conteudo = Path(caminho_txt).read_text(encoding="utf-8")
        print(f"  📋 Boletim gerado: {caminho_txt}")
    except Exception as exc:
        logger.warning("Não foi possível gerar novo boletim: %s — tentando último salvo.", exc)
        conteudo = _ler_ultimo_boletim()
        if not conteudo:
            print("  ❌ Nenhum boletim disponível para enviar.")
            return
        print("  📋 Usando último boletim salvo.")

    print("  📨 Enviando pelo Telegram...\n")
    telegram_client.enviar_boletim(conteudo)


def main():
    parser = argparse.ArgumentParser(
        description="News Hunter — orquestrador",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--coletar",
        action="store_true",
        help="Executa um ciclo completo de coleta de notícias",
    )
    parser.add_argument(
        "--gerar-boletim",
        action="store_true",
        dest="gerar_boletim",
        help="Gera o boletim diário (.md e .txt)",
    )
    parser.add_argument(
        "--coletar-e-gerar",
        action="store_true",
        dest="coletar_e_gerar",
        help="Executa coleta e em seguida gera o boletim",
    )
    parser.add_argument(
        "--testar-telegram",
        action="store_true",
        dest="testar_telegram",
        help="Envia mensagem de teste para verificar a conexão com Telegram",
    )
    parser.add_argument(
        "--enviar-telegram",
        action="store_true",
        dest="enviar_telegram",
        help="Gera (ou usa último) boletim e envia pelo Telegram",
    )
    parser.add_argument(
        "--coletar-gerar-enviar",
        action="store_true",
        dest="coletar_gerar_enviar",
        help="Pipeline completo: coleta → gera boletim → envia pelo Telegram",
    )

    args = parser.parse_args()

    # Inicializar banco (inclui migração segura)
    banco.inicializar()

    # ── Roteamento de comandos ─────────────────────────────────────────────────

    if args.testar_telegram:
        cmd_testar_telegram()

    elif args.enviar_telegram:
        cmd_enviar_telegram()

    elif args.coletar_gerar_enviar:
        import crawler
        import gerar_boletim as gb
        import telegram_client

        print("🔍 [1/3] Iniciando coleta de notícias...")
        resultado = crawler.ciclo_completo()
        print(f"✅ Coleta: {resultado['novas']} novas em {resultado['fontes']} fontes.\n")

        print("📋 [2/3] Gerando boletim...")
        caminho_md, caminho_txt = gb.gerar_boletim()

        if telegram_client.telegram_configurado():
            print("📨 [3/3] Enviando pelo Telegram...")
            conteudo = Path(caminho_txt).read_text(encoding="utf-8")
            ok = telegram_client.enviar_boletim(conteudo)
            if ok:
                print("✅ Boletim enviado com sucesso!\n")
            else:
                print("⚠️  Falha no envio pelo Telegram (arquivos locais preservados).\n")
        else:
            print(
                "⚠️  [3/3] Telegram não configurado — boletim salvo localmente apenas.\n"
                f"   📄 {caminho_md}\n"
            )

    elif args.coletar:
        import crawler
        print("🔍 Iniciando coleta de notícias...")
        resultado = crawler.ciclo_completo()
        print(f"✅ Coleta concluída: {resultado['novas']} novas notícias em {resultado['fontes']} fontes.\n")

    elif args.gerar_boletim:
        import gerar_boletim as gb
        gb.gerar_boletim()

    elif args.coletar_e_gerar:
        import crawler
        import gerar_boletim as gb
        print("🔍 Iniciando coleta...")
        resultado = crawler.ciclo_completo()
        print(f"✅ Coleta: {resultado['novas']} novas em {resultado['fontes']} fontes.\n")
        print("📋 Gerando boletim...")
        gb.gerar_boletim()

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
