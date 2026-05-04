# -*- coding: utf-8 -*-
"""
scrapers.py — News Hunter
==========================
Coletores de dados de mercado via web scraping.

Fontes:
  • investing.com  — calendário econômico (AJAX) + cotações de mercado
  • suno.com.br    — maiores altas e baixas da B3
  • BCB PTAX API   — câmbio oficial do Banco Central do Brasil

Cada função retorna lista/tupla vazia em caso de falha, sem travar o boletim.
"""

import logging
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger("news_hunter.scrapers")

# ── Sessão HTTP com headers realistas ─────────────────────────────────────────

def _criar_sessao() -> requests.Session:
    """Cria sessão com headers que imitam navegador real."""
    try:
        import cloudscraper
        sess = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except ImportError:
        sess = requests.Session()

    sess.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    })
    return sess


# ── Formatação auxiliar ────────────────────────────────────────────────────────

def _fmt_br(value, decimais=2) -> str:
    try:
        s = f"{float(value):,.{decimais}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _fmt_pct(pct) -> str:
    try:
        v = float(pct)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%".replace(".", ",")
    except Exception:
        return "—"


def _fmt_pct_altas(pct) -> str:
    try:
        v = float(pct)
        sign = "+" if v >= 0 else "-"
        return f"{sign} {abs(v):.2f}%".replace(".", ",")
    except Exception:
        return "—"


# ══════════════════════════════════════════════════════════════════════════════
# BANCO CENTRAL DO BRASIL — PTAX (câmbio oficial)
# ══════════════════════════════════════════════════════════════════════════════

_BCB_PTAX_DIA = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
    "?@moeda='{moeda}'&@dataCotacao='{data}'"
    "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
    "&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
)

_CAMBIO_PTAX_CFG = [
    ("USD", "🇺🇸Dólar Com.", 2),
    ("EUR", "🇪🇺Euro",       2),
    ("GBP", "🇬🇧Libra",      2),
    ("ARS", "🇦🇷Peso",       4),
    ("CNY", "🇨🇳Yuan",       3),
    ("JPY", "🇯🇵Iene",       3),
]


def _ptax_data_util(data_ref: date) -> str:
    """Retorna a última data útil anterior no formato MM-DD-YYYY para o BCB."""
    d = data_ref
    # Voltar até dia útil (seg–sex)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    # Se for muito cedo (antes das 13h), pega o dia útil anterior
    now_hour = datetime.now().hour
    if d == date.today() and now_hour < 13:
        d -= timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
    return d.strftime("%m-%d-%Y")


def buscar_cambio_bcb(data_ref: date = None) -> list:
    """
    Retorna câmbio oficial (PTAX) do Banco Central do Brasil.
    Formato: lista de {nome, valor, variacao}.
    """
    if data_ref is None:
        data_ref = date.today()

    data_hoje   = _ptax_data_util(data_ref)
    data_ontem  = _ptax_data_util(data_ref - timedelta(days=1))

    resultado = []

    for moeda, nome, decs in _CAMBIO_PTAX_CFG:
        try:
            def _get(data_str):
                url  = _BCB_PTAX_DIA.format(moeda=moeda, data=data_str)
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                valores = resp.json().get("value", [])
                if not valores:
                    return None
                v = valores[0]
                return (float(v["cotacaoCompra"]) + float(v["cotacaoVenda"])) / 2

            hoje_val   = _get(data_hoje)
            ontem_val  = _get(data_ontem)

            if hoje_val is None:
                continue

            pct = (hoje_val - ontem_val) / ontem_val * 100 if ontem_val else None

            resultado.append({
                "nome":     nome,
                "valor":    f"R$ {_fmt_br(hoje_val, decs)}",
                "variacao": _fmt_pct(pct),
            })
        except Exception as exc:
            logger.warning("BCB PTAX %s: %s", moeda, exc)

    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# INVESTING.COM — Calendário Econômico
# ══════════════════════════════════════════════════════════════════════════════

_INVESTING_CALENDAR_URL = (
    "https://br.investing.com/economic-calendar/Service/getCalendarFilteredData"
)

_INVESTING_CALENDAR_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://br.investing.com/economic-calendar/",
    "Accept": "*/*",
    "Origin": "https://br.investing.com",
}

_PAISES_INVESTING = {
    # Português (PT-BR)
    "Brasil":             "Brasil",
    "EUA":                "EUA",
    "Estados Unidos":     "EUA",
    "Zona Euro":          "Europa",
    "Japão":              "Japao",
    "Japan":              "Japao",
    "China":              "China",
    "Reino Unido":        "UK",
    "Alemanha":           "Europa",
    "França":             "Europa",
    "Itália":             "Europa",
    "Espanha":            "Europa",
    "Suíça":              "Europa",
    "Canadá":             "Global",
    "Austrália":          "Global",
    "Nova Zelândia":      "Global",
    "Índia":              "Global",
    "México":             "Global",
    "Suécia":             "Global",
    "Noruega":            "Global",
    "Dinamarca":          "Global",
    "Global":             "Global",
    # Inglês (fallback)
    "United States":      "EUA",
    "Euro Zone":          "Europa",
    "Germany":            "Europa",
    "France":             "Europa",
    "United Kingdom":     "UK",
    "Australia":          "Global",
}

# Países que queremos exibir no boletim
_PAISES_RELEVANTES = {"Brasil", "EUA", "Europa", "Japao", "China", "UK"}


def _parse_calendar_html(html: str, data_str: str) -> list:
    """Parseia o HTML retornado pelo endpoint do investing.com."""
    soup = BeautifulSoup(html, "html.parser")
    eventos = []

    for row in soup.select("tr.js-event-item"):
        try:
            # Horário
            time_td = row.select_one("td.time")
            if not time_td:
                continue
            horario = time_td.get_text(strip=True)
            if not horario or ":" not in horario:
                continue

            # País
            flag_td  = row.select_one("td.flagCur")
            pais_raw = ""
            if flag_td:
                span = flag_td.select_one("span[title]")
                pais_raw = span["title"] if span else flag_td.get_text(strip=True)
            pais = _PAISES_INVESTING.get(pais_raw, pais_raw or "Global")

            # Importância
            imp_td   = row.select_one("td.sentiment i")
            cls_list = " ".join(imp_td.get("class", [])) if imp_td else ""
            if "grayFullBullishIcon" in cls_list or "fullBullishIcon" in cls_list:
                importancia = "alta"
            elif "halfBullishIcon" in cls_list:
                importancia = "média"
            else:
                importancia = "baixa"

            # Indicador
            evento_td = row.select_one("td.event a") or row.select_one("td.event")
            indicador = evento_td.get_text(strip=True) if evento_td else ""
            if not indicador:
                continue

            # Projeção / Anterior / Atual
            bold_tds = row.select("td.bold")
            atual    = bold_tds[0].get_text(strip=True) if len(bold_tds) > 0 else "—"
            projecao = bold_tds[1].get_text(strip=True) if len(bold_tds) > 1 else "—"
            anterior = bold_tds[2].get_text(strip=True) if len(bold_tds) > 2 else "—"

            def _limpar(v):
                return v if v and v not in ("—", "", "N/A") else "não disponível"

            eventos.append({
                "data":        data_str,
                "horario":     horario,
                "pais":        pais,
                "indicador":   indicador,
                "importancia": importancia,
                "projecao":    _limpar(projecao),
                "anterior":    _limpar(anterior),
                "atual":       _limpar(atual),
                "fonte":       "investing.com",
            })
        except Exception:
            continue

    return eventos


def scrape_calendario_investing(data_ref: date = None, importancia_minima: str = "média") -> list:
    """
    Retorna eventos do calendário econômico de investing.com (PT-BR).

    importancia_minima: 'alta' → só alta | 'média' → alta+média | 'baixa' → tudo
    """
    if data_ref is None:
        data_ref = date.today()

    data_str = data_ref.strftime("%Y-%m-%d")

    imp_levels = {"alta": ["3"], "média": ["2", "3"], "baixa": ["1", "2", "3"]}
    imp_valores = imp_levels.get(importancia_minima, ["2", "3"])

    payload = [
        ("dateFrom",    data_str),
        ("dateTo",      data_str),
        ("timeZone",    "55"),          # BRT (UTC-3)
        ("timeFilter",  "timeRemain"),
        ("currentTab",  "today"),
        ("limit_from",  "0"),
    ]
    for v in imp_valores:
        payload.append(("importance[]", v))

    try:
        sess = _criar_sessao()
        # Visita a página primeiro para obter cookies
        sess.get("https://br.investing.com/economic-calendar/", timeout=10)
        resp = sess.post(
            _INVESTING_CALENDAR_URL,
            headers=_INVESTING_CALENDAR_HEADERS,
            data=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data_json = resp.json()
        html = data_json.get("data", "")
        if not html:
            logger.warning("Investing.com: resposta vazia.")
            return []
    except Exception as exc:
        logger.warning("Investing.com calendar: %s", exc)
        return []

    eventos = _parse_calendar_html(html, data_str)
    logger.info("Investing.com: %d eventos para %s", len(eventos), data_str)
    return eventos


# ── Cotações gerais do investing.com ──────────────────────────────────────────
# Pares de moedas, índices e commodities via páginas públicas do investing.com

_INV_CAMBIO_URLS = {
    "🇺🇸Dólar Com.": "https://br.investing.com/currencies/usd-brl",
    "🇪🇺Euro":        "https://br.investing.com/currencies/eur-brl",
    "🇬🇧Libra":       "https://br.investing.com/currencies/gbp-brl",
    "🇨🇳Yuan":        "https://br.investing.com/currencies/cny-brl",
    "🇯🇵Iene":        "https://br.investing.com/currencies/jpy-brl",
}

_INV_BOLSAS_URLS = {
    "🇧🇷 Ibovespa":    "https://br.investing.com/indices/bovespa",
    "🇺🇸 S&P 500":     "https://br.investing.com/indices/us-spx-500",
    "🇺🇸Nasdaq":       "https://br.investing.com/indices/nasdaq-composite",
    "🇩🇪Dax":          "https://br.investing.com/indices/germany-30",
    "🇨🇳Shangai":      "https://br.investing.com/indices/shanghai-composite",
}

_INV_COMMODITIES_URLS = {
    "🥇 Ouro":        "https://br.investing.com/commodities/gold",
    "⛽ Petro WTI":   "https://br.investing.com/commodities/crude-oil",
    "⛽ Petro Brent": "https://br.investing.com/commodities/brent-oil",
    "🌾 Trigo":       "https://br.investing.com/commodities/us-wheat",
    "🌽 Milho":       "https://br.investing.com/commodities/us-corn",
    "🥜 Soja":        "https://br.investing.com/commodities/us-soybeans",
    "☕ Café NY":     "https://br.investing.com/commodities/us-coffee-c",
}


def _scrape_investing_cotacao(url: str, sess: requests.Session) -> dict:
    """
    Extrai preço e variação de uma página de cotação do investing.com.
    Retorna {valor_raw, variacao_raw} ou {} se falhar.
    """
    try:
        resp = sess.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Seletor principal: div[data-test="instrument-price-last"]
        preco_el = (
            soup.select_one('[data-test="instrument-price-last"]')
            or soup.select_one(".instrument-price_last__KQzyA")
            or soup.select_one("#last_last")
            or soup.select_one(".top_rounded .arial_26")
        )
        var_el = (
            soup.select_one('[data-test="instrument-price-change-percent"]')
            or soup.select_one(".instrument-price_change-percent__6YGVU")
            or soup.select_one("#change_percent")
        )

        if not preco_el:
            return {}

        preco_raw = preco_el.get_text(strip=True).replace(",", ".")
        var_raw   = var_el.get_text(strip=True) if var_el else ""

        # Remove caracteres não numéricos do preço
        preco_limpo = "".join(c for c in preco_raw if c.isdigit() or c == ".")
        if not preco_limpo:
            return {}

        # Normaliza variação: "(+0.10%)" → "+0,10%"
        var_limpo = var_raw.replace("(", "").replace(")", "").replace("+", "+").strip()
        var_num = "".join(c for c in var_limpo if c.isdigit() or c in "+-.,")
        try:
            v = float(var_num.replace(",", "."))
            sign = "+" if v >= 0 else ""
            var_fmt = f"{sign}{v:.2f}%".replace(".", ",")
        except Exception:
            var_fmt = var_limpo

        return {"preco": float(preco_limpo), "variacao": var_fmt}
    except Exception as exc:
        logger.debug("Investing.com cotação %s: %s", url, exc)
        return {}


def scrape_cambio_investing() -> list:
    """Câmbio via páginas do investing.com (PT-BR)."""
    sess = _criar_sessao()
    resultado = []
    decs_map = {"🇯🇵Iene": 3, "🇨🇳Yuan": 3}

    for nome, url in _INV_CAMBIO_URLS.items():
        cot = _scrape_investing_cotacao(url, sess)
        if not cot:
            continue
        decs = decs_map.get(nome, 2)
        resultado.append({
            "nome":     nome,
            "valor":    f"R$ {_fmt_br(cot['preco'], decs)}",
            "variacao": cot["variacao"],
        })
    return resultado


def scrape_bolsas_investing() -> list:
    """Índices de bolsas via páginas do investing.com (PT-BR)."""
    sess = _criar_sessao()
    resultado = []
    decs_map = {"🇧🇷 Ibovespa": 0}

    for nome, url in _INV_BOLSAS_URLS.items():
        cot = _scrape_investing_cotacao(url, sess)
        if not cot:
            continue
        decs = decs_map.get(nome, 2)
        resultado.append({
            "nome":     nome,
            "valor":    _fmt_br(cot["preco"], decs),
            "variacao": cot["variacao"],
        })
    return resultado


def scrape_commodities_investing() -> list:
    """Commodities via páginas do investing.com (PT-BR)."""
    sess = _criar_sessao()
    resultado = []

    for nome, url in _INV_COMMODITIES_URLS.items():
        cot = _scrape_investing_cotacao(url, sess)
        if not cot:
            continue
        resultado.append({
            "nome":     nome,
            "valor":    f"US$ {_fmt_br(cot['preco'], 2)}",
            "variacao": cot["variacao"],
        })
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# SUNO.COM.BR — Maiores altas e baixas da B3
# ══════════════════════════════════════════════════════════════════════════════

_SUNO_URLS_ALTAS = [
    "https://www.suno.com.br/acoes/maiores-altas/",
    "https://www.suno.com.br/b3/acoes/maiores-altas/",
    "https://www.suno.com.br/acoes/?orderBy=variacao_dia&order=desc",
]
_SUNO_URLS_BAIXAS = [
    "https://www.suno.com.br/acoes/maiores-baixas/",
    "https://www.suno.com.br/b3/acoes/maiores-baixas/",
    "https://www.suno.com.br/acoes/?orderBy=variacao_dia&order=asc",
]


def _parse_suno_movers(html: str, top_n: int = 3) -> list:
    """Extrai tickers de páginas de altas/baixas do Suno."""
    soup = BeautifulSoup(html, "html.parser")
    movers = []

    rows = (
        soup.select("table tbody tr")
        or soup.select(".stock-table tr")
        or soup.select("[class*='ranking'] tr")
        or soup.select("[class*='table'] tr")
    )

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        ticker, variacao_raw, nome = "", "", ""
        for td in cols:
            txt = td.get_text(strip=True)
            if not ticker and 5 <= len(txt) <= 6 and txt[:4].isupper():
                ticker = txt.replace(".SA", "").strip()
            if not variacao_raw and "%" in txt:
                variacao_raw = txt
            if not nome and len(txt) > 6 and "%" not in txt and not txt[:4].isupper():
                nome = txt

        if not ticker or not variacao_raw:
            continue

        try:
            v = float(variacao_raw.replace("%", "").replace(",", ".").replace("+", "").strip())
            variacao_fmt = _fmt_pct_altas(v)
        except Exception:
            variacao_fmt = variacao_raw

        movers.append({"variacao": variacao_fmt, "ticker": ticker, "nome": nome})
        if len(movers) >= top_n:
            break

    return movers


def scrape_altas_baixas_suno(top_n: int = 3) -> tuple:
    """Retorna (altas, baixas) do suno.com.br, tentando múltiplas URLs."""
    sess  = _criar_sessao()
    altas, baixas = [], []

    for tipo, url_list in [("altas", _SUNO_URLS_ALTAS), ("baixas", _SUNO_URLS_BAIXAS)]:
        for url in url_list:
            try:
                resp = sess.get(url, timeout=15)
                resp.raise_for_status()
                movers = _parse_suno_movers(resp.text, top_n)
                if movers:
                    if tipo == "altas":
                        altas = movers
                    else:
                        baixas = movers
                    logger.info("Suno %s via %s: %d itens", tipo, url, len(movers))
                    break
            except Exception as exc:
                logger.debug("Suno %s (%s): %s", tipo, url, exc)

    return altas, baixas


# ══════════════════════════════════════════════════════════════════════════════
# STATUS INVEST — Maiores altas e baixas B3 (fallback)
# ══════════════════════════════════════════════════════════════════════════════

_STATUS_INVEST_URLS = [
    "https://statusinvest.com.br/home/highlow",
    "https://statusinvest.com.br/home/getmaioreshighlow",
    "https://statusinvest.com.br/acao/highlow",
]


def scrape_altas_baixas_statusinvest(top_n: int = 3) -> tuple:
    """Fallback: busca maiores altas e baixas do Status Invest."""
    sess = _criar_sessao()
    sess.headers.update({"Referer": "https://statusinvest.com.br/"})

    for url in _STATUS_INVEST_URLS:
        try:
            resp = sess.get(url, timeout=15)
            resp.raise_for_status()

            # Tenta JSON
            try:
                data = resp.json()
            except Exception:
                continue

            altas_raw  = (
                data.get("highList") or data.get("altas") or
                data.get("high")     or data.get("data", {}).get("highList", [])
            )
            baixas_raw = (
                data.get("lowList")  or data.get("baixas") or
                data.get("low")      or data.get("data", {}).get("lowList", [])
            )

            if not altas_raw and not baixas_raw:
                continue

            def _converter(items):
                resultado = []
                for item in (items or [])[:top_n]:
                    ticker = item.get("ticker", item.get("code", item.get("t", "")))
                    nome   = item.get("name",   item.get("companyName", item.get("n", "")))
                    var    = item.get("variation", item.get("var", item.get("v", 0)))
                    if not ticker:
                        continue
                    resultado.append({
                        "variacao": _fmt_pct_altas(var),
                        "ticker":   ticker.replace(".SA", ""),
                        "nome":     nome,
                    })
                return resultado

            altas  = _converter(altas_raw)
            baixas = _converter(baixas_raw)
            if altas or baixas:
                logger.info("Status Invest via %s: %d altas, %d baixas", url, len(altas), len(baixas))
                return altas, baixas

        except Exception as exc:
            logger.debug("Status Invest (%s): %s", url, exc)

    logger.warning("Status Invest: nenhuma URL funcionou.")
    return [], []
