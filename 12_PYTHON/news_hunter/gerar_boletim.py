# -*- coding: utf-8 -*-
"""
gerar_boletim.py — News Hunter
================================
Gera o boletim diário "Resumão do Mercado" em .md e .txt.
Envia pelo Telegram automaticamente se configurado.

Uso:
  python gerar_boletim.py
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import banco
import calendario_economico
import config
import market_agent

logger = logging.getLogger("news_hunter.boletim")

# Forçar UTF-8 no Windows
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)

# ── Meses e dias em português ─────────────────────────────────────────────────
_MESES = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]
_DIAS_SEMANA = [
    "Segunda", "Terça", "Quarta", "Quinta",
    "Sexta", "Sábado", "Domingo"
]


# ── Funções auxiliares ────────────────────────────────────────────────────────

def data_extenso_ptbr(data_ref: date = None) -> str:
    """Ex: 27 de abril 2026, Segunda"""
    if data_ref is None:
        data_ref = date.today()
    dia_semana = _DIAS_SEMANA[data_ref.weekday()]
    mes = _MESES[data_ref.month]
    return f"{data_ref.day} de {mes} {data_ref.year}, {dia_semana}"


def dias_copa_mundo(data_ref: date = None) -> int:
    """Dias até o início da Copa do Mundo 2026 (11/06/2026)."""
    if data_ref is None:
        data_ref = date.today()
    copa = date(2026, 6, 11)
    return max((copa - data_ref).days, 0)


def dias_restantes_ano(data_ref: date = None) -> int:
    """Calcula quantos dias faltam até 31/12 do ano corrente."""
    if data_ref is None:
        data_ref = date.today()
    fim_ano = date(data_ref.year, 12, 31)
    return (fim_ano - data_ref).days


def carregar_template():
    """Carrega o template Jinja2."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        logger.error("Jinja2 não instalado. Execute: pip install jinja2")
        sys.exit(1)

    pasta_templates = Path(__file__).parent / config.PASTA_TEMPLATES
    if not pasta_templates.exists():
        logger.error("Pasta de templates não encontrada: %s", pasta_templates)
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(pasta_templates)),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
    )
    return env.get_template(config.TEMPLATE_BOLETIM)


# ── Conteúdo editorial (frases, dicas, efemérides) ───────────────────────────

def _ler_json(nome_arquivo: str, fallback):
    """Lê um JSON de dados/ com fallback seguro."""
    caminho = Path(__file__).parent / "dados" / nome_arquivo
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Não foi possível ler %s: %s", nome_arquivo, exc)
        return fallback


def get_frase_do_dia(data_ref: date = None) -> str:
    if data_ref is None:
        data_ref = date.today()
    frases = _ler_json("frases.json", [])
    if not frases:
        return "O mercado premia a paciência e pune a impulsividade."
    return frases[(data_ref.day - 1) % len(frases)]


def get_dica_do_mes(data_ref: date = None) -> str:
    if data_ref is None:
        data_ref = date.today()
    dicas = _ler_json("dicas.json", [])
    if not dicas:
        return "Invista regularmente, mesmo em pequenos valores."
    return dicas[(data_ref.month - 1) % len(dicas)]


def get_efemerides(data_ref: date = None) -> list:
    if data_ref is None:
        data_ref = date.today()
    todas = _ler_json("efemerides.json", {})
    chave = f"{data_ref.month:02d}-{data_ref.day:02d}"
    return todas.get(chave, [])


def separar_por_categoria(noticias: list) -> dict:
    """Separa notícias por grupo temático."""
    limite = config.LIMITE_NOTICIAS_POR_CATEGORIA

    cats_macro = {
        "economia_brasil", "economia_global", "bancos_centrais",
        "politica_economica", "calendario_economico",
    }

    grupos = {
        "empresas":        [],
        "tecnologia":      [],
        "macro":           [],
        "commodities":     [],
        "bolsas_noticias": [],
        "criptomoedas":    [],
    }

    for n in noticias:
        cat = (n.get("categoria") or "").lower()
        if cat == "empresas"       and len(grupos["empresas"])        < limite:
            grupos["empresas"].append(n)
        elif cat == "tecnologia"   and len(grupos["tecnologia"])      < limite:
            grupos["tecnologia"].append(n)
        elif cat in cats_macro     and len(grupos["macro"])           < limite:
            grupos["macro"].append(n)
        elif cat == "commodities"  and len(grupos["commodities"])     < limite:
            grupos["commodities"].append(n)
        elif cat == "bolsas"       and len(grupos["bolsas_noticias"]) < limite:
            grupos["bolsas_noticias"].append(n)
        elif cat == "criptomoedas" and len(grupos["criptomoedas"])    < limite:
            grupos["criptomoedas"].append(n)

    return grupos


def gerar_leitura_mercado(destaques: list, agenda: list) -> str:
    """
    Gera texto de leitura de mercado determinístico, sem inventar dados.
    Baseia-se nas categorias mais presentes nas notícias do dia.
    """
    contagem = {}
    for n in destaques:
        cat = (n.get("categoria") or "geral").replace("_", " ")
        contagem[cat] = contagem.get(cat, 0) + 1

    if contagem:
        top_cats = sorted(contagem, key=contagem.get, reverse=True)[:3]
        cats_str = ", ".join(top_cats)
        return (
            f"Até o momento, o fluxo de notícias está concentrado em {cats_str}. "
            "Os principais pontos de atenção são os temas ligados a juros, inflação, "
            "bancos centrais, commodities e resultados corporativos. "
            "A leitura deve ser atualizada conforme novos dados forem divulgados."
        )
    elif agenda:
        return (
            "Nenhuma notícia de destaque identificada até o momento. "
            "Há eventos na agenda econômica que podem movimentar os mercados ao longo do dia. "
            "Acompanhe as atualizações."
        )
    else:
        return (
            "Nenhuma notícia de destaque ou evento de agenda identificado até o momento. "
            "O boletim será atualizado conforme novas informações forem coletadas."
        )


def _limpar_fonte(fonte: str) -> str:
    """Normaliza nomes de fonte: URLs → domínio, títulos longos → primeira parte."""
    if not fonte:
        return ""
    # URL completa → extrai domínio legível
    if fonte.startswith("http"):
        try:
            domain = urlparse(fonte).netloc.replace("www.", "")
            nome = domain.split(".")[0].capitalize()
            _MAPA = {
                "Exame": "Exame", "Infomoney": "InfoMoney", "Valor": "Valor Econômico",
                "Folha": "Folha de S.Paulo", "Estadao": "Estadão", "G1": "G1",
                "Cnn": "CNN Brasil", "Uol": "UOL", "Moneyti": "Money Times",
            }
            return _MAPA.get(nome, nome)
        except Exception:
            return fonte
    # Nome longo com separadores → pega só a primeira parte
    for sep in [" – ", " - ", " | "]:
        if sep in fonte:
            return fonte.split(sep)[0].strip()
    return fonte


def _limpar_noticias(noticias: list) -> list:
    """Aplica limpeza de fonte em lista de notícias."""
    for n in noticias:
        n["fonte"] = _limpar_fonte(n.get("fonte", ""))
    return noticias


def _e_financeiramente_relevante(noticia: dict) -> bool:
    """Descarta notícias que contenham tópicos claramente não-financeiros."""
    excluir = getattr(config, "PALAVRAS_EXCLUIR_BOLETIM", [])
    if not excluir:
        return True
    texto = (noticia.get("titulo", "") + " " + noticia.get("resumo_curto", "")).lower()
    return not any(p.lower() in texto for p in excluir)


def _listar_fontes_ativas() -> list:
    """Retorna nomes de fontes com notícias hoje (até 20)."""
    noticias_hoje = banco.buscar_hoje(limite=200)
    fontes = sorted({n.get("fonte", "") for n in noticias_hoje if n.get("fonte")})
    return fontes[:20]


# ── Gerador principal ─────────────────────────────────────────────────────────

def gerar_boletim(data_ref: date = None) -> tuple:
    """
    Gera o boletim do dia e salva em .md e .txt.
    Se Telegram estiver configurado, envia automaticamente.
    Retorna (caminho_md, caminho_txt).
    """
    if data_ref is None:
        data_ref = date.today()

    logger.info("Gerando boletim para %s...", data_ref)

    # 1. Banco
    banco.inicializar()

    # 2. Notícias
    todas_hoje = banco.buscar_top_noticias_hoje(
        limite=100,
        score_minimo=config.SCORE_MINIMO_BOLETIM
    )
    todas_hoje = [n for n in todas_hoje if _e_financeiramente_relevante(n)]
    todas_hoje = _limpar_noticias(todas_hoje)

    # 3. Destaques (top 3 por score para VOCÊ PRECISA SABER)
    destaques = todas_hoje[:config.LIMITE_DESTAQUES]

    # 4. Top 8 notícias por score para PRINCIPAIS NOTÍCIAS (sem repetir destaques)
    limite_boletim = getattr(config, "LIMITE_NOTICIAS_BOLETIM", 8)
    noticias_boletim = todas_hoje[:limite_boletim]

    # 5. Categorias (mantido para compatibilidade)
    grupos = separar_por_categoria(todas_hoje)

    # 6a. Alertas
    alertas = banco.buscar_urgentes(limite=config.LIMITE_ALERTAS)

    # 6. Agenda (investing.com → JSON manual)
    agenda = market_agent.buscar_agenda(data_ref)

    # 7. Dados de mercado (câmbio, bolsas, altas/baixas, commodities, cripto, indicadores)
    dados_mercado = market_agent.buscar_todos(data_ref)

    # 8. Leitura de mercado
    leitura = gerar_leitura_mercado(destaques, agenda)

    # 9. Fontes ativas
    fontes_ativas = _listar_fontes_ativas()

    # 10. Contexto do template
    contexto = {
        # ── Cabeçalho ──────────────────────────────────────────────────────────
        "nome_boletim":   config.NOME_BOLETIM,
        "data_extenso":   data_extenso_ptbr(data_ref),
        "dias_restantes": dias_restantes_ano(data_ref),
        "dias_copa":      dias_copa_mundo(data_ref),
        # ── Conteúdo editorial ─────────────────────────────────────────────────
        "efemerides":     get_efemerides(data_ref),
        "frase_do_dia":   get_frase_do_dia(data_ref),
        "dica_do_mes":    get_dica_do_mes(data_ref),
        # ── Notícias ───────────────────────────────────────────────────────────
        "destaques":        destaques,
        "alertas":          alertas,
        "noticias_boletim": noticias_boletim,
        "agenda":           agenda,
        "empresas":         grupos["empresas"],
        "tecnologia":       grupos["tecnologia"],
        "macro":            grupos["macro"],
        "commodities":      grupos["commodities"],
        "bolsas_noticias":  grupos["bolsas_noticias"],
        "criptomoedas":     grupos["criptomoedas"],
        # ── Cotações de mercado ────────────────────────────────────────────────
        "clima":                  [],   # weather_agent (futuro)
        "cambio":                 dados_mercado.get("cambio",               []),
        "bolsas_cotacoes":        dados_mercado.get("bolsas_cotacoes",      []),
        "maiores_altas":          dados_mercado.get("maiores_altas",        []),
        "maiores_baixas":         dados_mercado.get("maiores_baixas",       []),
        "commodities_cotacoes":   dados_mercado.get("commodities_cotacoes", []),
        "cripto_cotacoes":        dados_mercado.get("cripto_cotacoes",      []),
        "indicadores":            dados_mercado.get("indicadores",          []),
        # ── Rodapé ─────────────────────────────────────────────────────────────
        "fontes":           fontes_ativas,
    }

    # 10. Renderizar
    template = carregar_template()
    conteudo_boletim = template.render(**contexto)

    # 11. Salvar arquivos
    pasta_boletins = Path(__file__).parent / config.PASTA_BOLETINS
    pasta_boletins.mkdir(parents=True, exist_ok=True)

    data_str    = data_ref.strftime("%Y-%m-%d")
    caminho_md  = pasta_boletins / f"boletim_{data_str}.md"
    caminho_txt = pasta_boletins / f"boletim_{data_str}.txt"

    caminho_md.write_text(conteudo_boletim, encoding="utf-8")
    caminho_txt.write_text(conteudo_boletim, encoding="utf-8")

    # 12. Console
    print("\n" + "=" * 60)
    print("  ✅  Boletim gerado com sucesso!")
    print("=" * 60)
    print(f"  📄  Markdown : {caminho_md}")
    print(f"  📄  Texto    : {caminho_txt}")
    print(f"  📰  Destaques: {len(destaques)}")
    print(f"  📅  Agenda   : {len(agenda)} eventos")
    print(f"  🚨  Alertas  : {len(alertas)}")
    print("=" * 60 + "\n")

    logger.info("Boletim salvo: %s | %s", caminho_md, caminho_txt)

    # 13. Envio pelo Telegram (opcional, não bloqueia em caso de falha)
    if config.TELEGRAM_ATIVO and config.TELEGRAM_ENVIAR_BOLETIM:
        try:
            import telegram_client
            logger.info("Enviando boletim pelo Telegram...")
            ok = telegram_client.enviar_boletim(conteudo_boletim)
            if ok:
                print("  📨  Boletim enviado pelo Telegram!\n")
            else:
                print("  ⚠️   Falha no envio pelo Telegram (ver log).\n")
        except Exception as exc:
            logger.error("Falha ao enviar boletim pelo Telegram: %s", exc)
            print(f"  ⚠️   Falha no Telegram: {exc}\n")

    return str(caminho_md), str(caminho_txt)


if __name__ == "__main__":
    gerar_boletim()
