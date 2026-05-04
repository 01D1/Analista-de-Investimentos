# -*- coding: utf-8 -*-
"""
classificador.py — News Hunter
================================
Classifica noticias por regras deterministicas, sem depender de IA externa.
Atribui categoria, subcategoria, score de relevancia e flag de urgencia.

Uso:
    from classificador import classificar_noticia
    resultado = classificar_noticia(titulo, conteudo, fonte, link)
"""

import re
import config

# Mapa de categorias e seus pesos
_REGRAS = [
    ("empresas",             config.PALAVRAS_EMPRESAS,             3, "empresas",            "resultados"),
    ("tecnologia",           config.PALAVRAS_TECNOLOGIA,           3, "tecnologia",           "big_tech"),
    ("macro",                config.PALAVRAS_MACRO,                4, "bancos_centrais",      "juros"),
    ("commodities",          config.PALAVRAS_COMMODITIES,          3, "commodities",          "energia"),
    ("bolsas",               config.PALAVRAS_BOLSAS,               3, "bolsas",               "indices"),
    ("criptomoedas",         config.PALAVRAS_CRIPTO,               2, "criptomoedas",         "bitcoin"),
    ("calendario_economico", config.PALAVRAS_CALENDARIO_ECONOMICO, 4, "calendario_economico", "agenda"),
    ("alerta_forte",         config.PALAVRAS_ALERTA_FORTE,         5, None,                   "alerta"),
]

_BRASIL = ["brasil", "brasileiro", "selic", "copom", "ipca", "bovespa",
           "ibovespa", "real", "brl", "b3", "governo federal", "ministerio"]
_GLOBAL = ["eua", "federal reserve", "fed", "fomc", "bce", "boe", "boj",
           "pboc", "china", "europa", "wall street", "dollar", "usd",
           "s&p", "nasdaq", "dow jones"]


def _contar_hits(texto, palavras):
    """
    Conta quantas palavras da lista aparecem no texto.
    Para palavras curtas (<= 3 chars), usa word boundary para evitar
    falsos positivos (ex: 'ia' dentro de 'seria').
    """
    count = 0
    for p in palavras:
        pl = p.lower()
        if len(pl) <= 3:
            pat = r'(?<![a-zA-Z0-9])' + re.escape(pl) + r'(?![a-zA-Z0-9])'
            if re.search(pat, texto):
                count += 1
        else:
            if pl in texto:
                count += 1
    return count


def _refinar_subcategoria(categoria, texto):
    """Retorna subcategoria especifica com base no texto."""
    mapa = {
        "empresas": [
            ("resultado",   ["resultado", "lucro", "ebitda", "balanco"]),
            ("dividendos",  ["dividendos", "jcp", "provento"]),
            ("corporativo", ["fusao", "aquisicao", "ipo", "follow-on", "fato relevante"]),
        ],
        "tecnologia": [
            ("ia",          ["inteligencia artificial", "openai", "llm", "nvidia"]),
            ("semis",       ["semicondutores", "chips"]),
            ("big_tech",    ["apple", "google", "microsoft", "meta", "amazon"]),
        ],
        "commodities": [
            ("petroleo",    ["petroleo", "brent", "wti", "opep"]),
            ("minerio",     ["minerio", "ferro", "cobre"]),
            ("agro",        ["soja", "milho", "trigo", "cafe", "boi gordo"]),
            ("metais",      ["ouro", "prata"]),
        ],
        "bolsas": [
            ("brasil",      ["ibovespa", "b3", "bovespa"]),
            ("eua",         ["s&p", "nasdaq", "dow jones", "wall street"]),
            ("asia",        ["nikkei", "shanghai", "hang seng"]),
        ],
        "bancos_centrais": [
            ("copom",       ["copom", "selic"]),
            ("fed",         ["fed", "fomc", "federal reserve"]),
            ("outros",      ["bce", "boe", "boj", "pboc"]),
        ],
    }
    for subcat, palavras in mapa.get(categoria, []):
        if any(p in texto for p in palavras):
            return subcat
    return ""


def classificar_noticia(titulo, conteudo="", fonte="", link=""):
    """
    Classifica uma noticia e retorna dict com:
        categoria, subcategoria, score, urgente, motivo_score
    """
    texto = (titulo + " " + conteudo + " " + fonte + " " + link).lower()

    score = 0
    motivos = []
    hits_por_tema = {}
    alerta_forte = False

    # Bonus por fonte prioritaria
    fonte_norm = fonte.lower()
    for fp in config.FONTES_PRIORITARIAS:
        if fp.lower() in fonte_norm:
            score += 3
            motivos.append("fonte_prioritaria:" + fp)
            break

    # Varredura por tema
    for nome, palavras, pts, cat, subcat in _REGRAS:
        hits = _contar_hits(texto, palavras)
        if hits > 0:
            score += pts
            motivos.append(nome + ":" + str(hits) + "hits+" + str(pts) + "pts")
            if cat:
                hits_por_tema[cat] = hits_por_tema.get(cat, 0) + hits
            if nome == "alerta_forte":
                alerta_forte = True

    # Categoria principal
    if hits_por_tema:
        categoria = max(hits_por_tema, key=hits_por_tema.get)
        if categoria == "bancos_centrais":
            hits_br = _contar_hits(texto, _BRASIL)
            hits_gl = _contar_hits(texto, _GLOBAL)
            if hits_br > hits_gl:
                categoria = "economia_brasil"
            elif hits_gl > hits_br:
                categoria = "economia_global"
        subcategoria = _refinar_subcategoria(categoria, texto)
    else:
        categoria = "geral"
        subcategoria = ""

    urgente = 1 if (alerta_forte or score >= 8) else 0

    return {
        "categoria":    categoria,
        "subcategoria": subcategoria,
        "score":        score,
        "urgente":      urgente,
        "motivo_score": "; ".join(motivos) if motivos else "sem_match",
    }
