# -*- coding: utf-8 -*-
"""
market_agent.py — News Hunter
==============================
Orquestra a coleta de dados de mercado para o boletim diário.

Cadeia de fallback por seção:
  Câmbio       → BCB PTAX  →  investing.com  →  yfinance
  Bolsas       → investing.com  →  yfinance
  Altas/Baixas → Suno  →  Status Invest  →  yfinance (B3 batch)
  Commodities  → investing.com  →  yfinance
  Cripto       → CoinGecko API
  Indicadores  → BCB Time Series API
  Agenda       → investing.com (AJAX)  →  JSON manual

Uso:
    from market_agent import buscar_todos, buscar_agenda
    dados   = buscar_todos()       # dict para o template de mercado
    agenda  = buscar_agenda()      # lista de eventos do dia
"""

import logging
from datetime import date, datetime

import requests

logger = logging.getLogger("news_hunter.market")

# ── Formatação ────────────────────────────────────────────────────────────────

_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",    6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro",10: "Outubro",  11: "Novembro", 12: "Dezembro",
}


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


def _periodo_bcb(item: dict) -> str:
    try:
        d = datetime.strptime(item["data"], "%d/%m/%Y")
        return f"{_MESES_PT[d.month]} {d.year}"
    except Exception:
        return item.get("data", "")


# ── BCB Time Series ───────────────────────────────────────────────────────────

_BCB_ULTIMOS = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}"
    "/dados/ultimos/{n}?formato=json"
)
_BCB_PERIODO_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}"
    "/dados?dataInicial={inicio}&dataFinal={fim}&formato=json"
)


def _bcb_ultimo(serie: int) -> dict | None:
    try:
        r = requests.get(_BCB_ULTIMOS.format(serie=serie, n=1), timeout=10)
        r.raise_for_status()
        dados = r.json()
        return dados[-1] if dados else None
    except Exception as exc:
        logger.warning("BCB série %s: %s", serie, exc)
        return None


def _bcb_acumulado(serie: int, n: int) -> float | None:
    try:
        r = requests.get(_BCB_ULTIMOS.format(serie=serie, n=n), timeout=10)
        r.raise_for_status()
        acc = 1.0
        for d in r.json():
            acc *= 1 + float(d["valor"]) / 100
        return (acc - 1) * 100
    except Exception as exc:
        logger.warning("BCB acumulado %s/%d: %s", serie, n, exc)
        return None


def _bcb_ytd(serie: int) -> float | None:
    ano = date.today().year
    try:
        r = requests.get(
            _BCB_PERIODO_URL.format(
                serie=serie, inicio=f"01/01/{ano}", fim=f"31/12/{ano}"
            ),
            timeout=10,
        )
        r.raise_for_status()
        dados = r.json()
        if not dados:
            return None
        acc = 1.0
        for d in dados:
            acc *= 1 + float(d["valor"]) / 100
        return (acc - 1) * 100
    except Exception as exc:
        logger.warning("BCB YTD %s: %s", serie, exc)
        return None


# ── yfinance (fallback) ───────────────────────────────────────────────────────

def _yf_cotacao(ticker_id: str, decs: int = 2) -> dict | None:
    """Retorna {preco, pct} via yfinance. Retorna None se falhar."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker_id).history(period="5d")
        if len(hist) < 2:
            return None
        close = float(hist["Close"].iloc[-1])
        prev  = float(hist["Close"].iloc[-2])
        pct   = (close - prev) / prev * 100 if prev else 0.0
        return {"preco": close, "pct": pct}
    except Exception as exc:
        logger.debug("yfinance %s: %s", ticker_id, exc)
        return None


# ── B3 top movers via yfinance (último fallback) ──────────────────────────────

_B3_YF = [
    ("PETR4.SA", "Petrobras"),    ("VALE3.SA", "Vale"),
    ("ITUB4.SA", "Itaú"),         ("BBDC4.SA", "Bradesco"),
    ("BBAS3.SA", "Banco do Brasil"), ("ABEV3.SA", "Ambev"),
    ("WEGE3.SA", "WEG"),          ("RENT3.SA", "Localiza"),
    ("EMBR3.SA", "Embraer"),      ("JBSS3.SA", "JBS"),
    ("SUZB3.SA", "Suzano"),       ("RDOR3.SA", "Rede D'Or"),
    ("HAPV3.SA", "HapVida"),      ("BRKM5.SA", "Braskem"),
    ("USIM5.SA", "Usiminas"),     ("GGBR4.SA", "Gerdau"),
    ("PRIO3.SA", "PRIO"),         ("BRAV3.SA", "Brava"),
    ("VAMO3.SA", "Vamos"),        ("POSI3.SA", "Positivo"),
    ("AZUL4.SA", "Azul"),         ("GOLL4.SA", "Gol"),
    ("CYRE3.SA", "Cyrela"),       ("MRVE3.SA", "MRV"),
    ("MGLU3.SA", "Magalu"),       ("LREN3.SA", "Renner"),
    ("CSAN3.SA", "Cosan"),        ("RAIZ4.SA", "Raízen"),
    ("BEEF3.SA", "Minerva"),      ("CSNA3.SA", "CSN"),
]

_B3_YF_TICKERS = [
    ("PETR4.SA","Petrobras"),  ("VALE3.SA","Vale"),
    ("ITUB4.SA","Itaú"),       ("BBDC4.SA","Bradesco"),
    ("BBAS3.SA","Banco do Brasil"), ("ABEV3.SA","Ambev"),
    ("WEGE3.SA","WEG"),        ("RENT3.SA","Localiza"),
    ("SUZB3.SA","Suzano"),     ("RDOR3.SA","Rede D'Or"),
    ("HAPV3.SA","HapVida"),    ("BRKM5.SA","Braskem"),
    ("USIM5.SA","Usiminas"),   ("GGBR4.SA","Gerdau"),
    ("PRIO3.SA","PRIO"),       ("BRAV3.SA","Brava"),
    ("VAMO3.SA","Vamos"),      ("POSI3.SA","Positivo"),
    ("CYRE3.SA","Cyrela"),     ("MRVE3.SA","MRV"),
    ("MGLU3.SA","Magalu"),     ("LREN3.SA","Renner"),
    ("CSAN3.SA","Cosan"),      ("RAIZ4.SA","Raízen"),
    ("BEEF3.SA","Minerva"),    ("CSNA3.SA","CSN"),
    ("EGIE3.SA","Engie"),      ("SBSP3.SA","Sabesp"),
    ("TAEE11.SA","Taesa"),     ("VIVT3.SA","Telefônica"),
]


def _altas_baixas_yfinance(top_n: int = 3) -> tuple:
    try:
        import yfinance as yf
        tickers_str = " ".join(t for t, _ in _B3_YF_TICKERS)
        dados = yf.download(tickers_str, period="5d", progress=False, auto_adjust=True)
        closes = dados["Close"]
    except Exception as exc:
        logger.warning("yfinance B3 batch: %s", exc)
        return [], []

    movimentos = []
    for tid, nome in _B3_YF_TICKERS:
        try:
            serie = closes[tid].dropna()
            if len(serie) < 2:
                continue
            pct = (float(serie.iloc[-1]) - float(serie.iloc[-2])) / float(serie.iloc[-2]) * 100
            movimentos.append((pct, tid.replace(".SA", ""), nome))
        except Exception:
            continue

    if not movimentos:
        return [], []

    movimentos.sort(key=lambda x: x[0], reverse=True)
    to_item = lambda p, t, n: {"variacao": _fmt_pct_altas(p), "ticker": t, "nome": n}
    altas  = [to_item(*m) for m in movimentos[:top_n]]
    baixas = [to_item(*m) for m in movimentos[-top_n:][::-1]]
    return altas, baixas


# ══════════════════════════════════════════════════════════════════════════════
# CÂMBIO — BCB PTAX → investing.com → yfinance
# ══════════════════════════════════════════════════════════════════════════════

_YF_CAMBIO = [
    ("USDBRL=X", "🇺🇸Dólar Com.", "R$", 2),
    ("EURBRL=X", "🇪🇺Euro",       "R$", 2),
    ("GBPBRL=X", "🇬🇧Libra",      "R$", 2),
    ("ARSBRL=X", "🇦🇷Peso",       "R$", 4),
    ("CNYBRL=X", "🇨🇳Yuan",       "R$", 3),
    ("JPYBRL=X", "🇯🇵Iene",       "R$", 3),
]


def buscar_cambio() -> list:
    # 1ª tentativa: BCB PTAX (câmbio oficial)
    try:
        from scrapers import buscar_cambio_bcb
        resultado = buscar_cambio_bcb()
        if resultado:
            logger.info("Câmbio via BCB PTAX (%d pares)", len(resultado))
            return resultado
    except Exception as exc:
        logger.warning("BCB PTAX: %s", exc)

    # 2ª tentativa: investing.com
    try:
        from scrapers import scrape_cambio_investing
        resultado = scrape_cambio_investing()
        if resultado:
            logger.info("Câmbio via investing.com (%d pares)", len(resultado))
            return resultado
    except Exception as exc:
        logger.warning("Investing câmbio: %s", exc)

    # 3ª tentativa: yfinance
    resultado = []
    for tid, nome, moeda, decs in _YF_CAMBIO:
        cot = _yf_cotacao(tid)
        if cot:
            resultado.append({
                "nome":     nome,
                "valor":    f"{moeda} {_fmt_br(cot['preco'], decs)}",
                "variacao": _fmt_pct(cot["pct"]),
            })
    if resultado:
        logger.info("Câmbio via yfinance (%d pares)", len(resultado))
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# BOLSAS — investing.com → yfinance
# ══════════════════════════════════════════════════════════════════════════════

_YF_BOLSAS = [
    ("^BVSP",     "🇧🇷 Ibovespa",    0),
    ("^GSPC",     "🇺🇸 S&P 500",      2),
    ("^DJI",      "🇺🇸Dow Jones",     2),
    ("^IXIC",     "🇺🇸Nasdaq",        2),
    ("^GDAXI",    "🇩🇪Dax",           2),
    ("^STOXX50E", "🇪🇺Euro Stoxx 50", 2),
    ("000001.SS", "🇨🇳Shangai",       2),
]


def buscar_bolsas() -> list:
    # 1ª tentativa: investing.com
    try:
        from scrapers import scrape_bolsas_investing
        resultado = scrape_bolsas_investing()
        if resultado:
            logger.info("Bolsas via investing.com (%d índices)", len(resultado))
            return resultado
    except Exception as exc:
        logger.warning("Investing bolsas: %s", exc)

    # 2ª tentativa: yfinance
    resultado = []
    for tid, nome, decs in _YF_BOLSAS:
        cot = _yf_cotacao(tid)
        if cot:
            resultado.append({
                "nome":     nome,
                "valor":    _fmt_br(cot["preco"], decs),
                "variacao": _fmt_pct(cot["pct"]),
            })
    if resultado:
        logger.info("Bolsas via yfinance (%d índices)", len(resultado))
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# ALTAS E BAIXAS B3 — Suno → Status Invest → yfinance
# ══════════════════════════════════════════════════════════════════════════════

def buscar_maiores_movimentos(top_n: int = 3) -> tuple:
    # 1ª tentativa: Suno
    try:
        from scrapers import scrape_altas_baixas_suno
        altas, baixas = scrape_altas_baixas_suno(top_n)
        if altas and baixas:
            logger.info("Altas/baixas via Suno")
            return altas, baixas
    except Exception as exc:
        logger.warning("Suno altas/baixas: %s", exc)

    # 2ª tentativa: Status Invest
    try:
        from scrapers import scrape_altas_baixas_statusinvest
        altas, baixas = scrape_altas_baixas_statusinvest(top_n)
        if altas and baixas:
            logger.info("Altas/baixas via Status Invest")
            return altas, baixas
    except Exception as exc:
        logger.warning("Status Invest: %s", exc)

    # 3ª tentativa: yfinance batch
    altas, baixas = _altas_baixas_yfinance(top_n)
    if altas or baixas:
        logger.info("Altas/baixas via yfinance")
    return altas, baixas


# ══════════════════════════════════════════════════════════════════════════════
# COMMODITIES — investing.com → yfinance
# ══════════════════════════════════════════════════════════════════════════════

_YF_COMMODITIES = [
    ("GC=F",  "🥇 Ouro",        "US$", 2),
    ("CL=F",  "⛽ Petro WTI",   "US$", 2),
    ("BZ=F",  "⛽ Petro Brent", "US$", 2),
    ("ZW=F",  "🌾 Trigo",       "US$", 2),
    ("ZC=F",  "🌽 Milho",       "US$", 2),
    ("ZS=F",  "🥜 Soja",        "US$", 2),
    ("KC=F",  "☕ Café NY",     "US$", 2),
    ("GF=F",  "🐂 Boi Gordo",   "US$", 2),
]


def buscar_commodities() -> list:
    # 1ª tentativa: investing.com
    try:
        from scrapers import scrape_commodities_investing
        resultado = scrape_commodities_investing()
        if resultado:
            logger.info("Commodities via investing.com (%d itens)", len(resultado))
            return resultado
    except Exception as exc:
        logger.warning("Investing commodities: %s", exc)

    # 2ª tentativa: yfinance
    resultado = []
    for tid, nome, moeda, decs in _YF_COMMODITIES:
        cot = _yf_cotacao(tid)
        if cot:
            resultado.append({
                "nome":     nome,
                "valor":    f"{moeda} {_fmt_br(cot['preco'], decs)}",
                "variacao": _fmt_pct(cot["pct"]),
            })
    if resultado:
        logger.info("Commodities via yfinance (%d itens)", len(resultado))
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# CRIPTOMOEDAS — CoinGecko API
# ══════════════════════════════════════════════════════════════════════════════

_COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
)
_CRIPTO_NOMES = {"bitcoin": "🅱️ Bitcoin", "ethereum": "⏫️ Ethereum"}


def buscar_cripto() -> list:
    try:
        resp = requests.get(_COINGECKO_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("CoinGecko: %s", exc)
        return []

    resultado = []
    for coin_id, nome in _CRIPTO_NOMES.items():
        coin = data.get(coin_id, {})
        preco = coin.get("usd")
        var   = coin.get("usd_24h_change")
        if preco is None:
            continue
        resultado.append({
            "nome":     nome,
            "valor":    f"U$ {_fmt_br(preco, 2)}",
            "variacao": _fmt_pct(var),
        })
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# INDICADORES — BCB Time Series API
# ══════════════════════════════════════════════════════════════════════════════

def buscar_indicadores() -> list:
    resultado = []
    ano = date.today().year

    selic = _bcb_ultimo(432)
    if selic:
        resultado.append({"nome": "SELIC", "valor": f"{selic['valor'].replace('.', ',')}% a.a", "periodo": ""})

    cdi = _bcb_ultimo(12)
    if cdi:
        resultado.append({"nome": "CDI ", "valor": f"{cdi['valor'].replace('.', ',')}% a.a", "periodo": ""})

    igpm_m = _bcb_ultimo(189)
    if igpm_m:
        resultado.append({"nome": "IGPM ", "valor": _fmt_pct(igpm_m["valor"]), "periodo": _periodo_bcb(igpm_m)})

    igpm_12 = _bcb_acumulado(189, 12)
    if igpm_12 is not None:
        resultado.append({"nome": "IGPM ", "valor": _fmt_pct(igpm_12), "periodo": "12 meses"})

    igpm_ytd = _bcb_ytd(189)
    if igpm_ytd is not None:
        resultado.append({"nome": "IGPM ", "valor": _fmt_pct(igpm_ytd), "periodo": str(ano)})

    ipca_m = _bcb_ultimo(433)
    if ipca_m:
        resultado.append({"nome": "IPCA ", "valor": _fmt_pct(ipca_m["valor"]), "periodo": _periodo_bcb(ipca_m)})

    ipca_12 = _bcb_acumulado(433, 12)
    if ipca_12 is not None:
        resultado.append({"nome": "IPCA ", "valor": _fmt_pct(ipca_12), "periodo": "12 meses"})

    ipca_ytd = _bcb_ytd(433)
    if ipca_ytd is not None:
        resultado.append({"nome": "IPCA ", "valor": _fmt_pct(ipca_ytd), "periodo": str(ano)})

    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# AGENDA ECONÔMICA — investing.com → JSON manual
# ══════════════════════════════════════════════════════════════════════════════

def buscar_agenda(data_ref: date = None) -> list:
    """
    Retorna agenda econômica do dia.
    Tenta investing.com primeiro; se falhar, usa o JSON manual.
    """
    if data_ref is None:
        data_ref = date.today()

    # 1ª tentativa: investing.com
    try:
        from scrapers import scrape_calendario_investing
        eventos = scrape_calendario_investing(data_ref, importancia_minima="média")
        if eventos:
            logger.info("Agenda via investing.com (%d eventos)", len(eventos))
            # Mescla com eventos manuais do mesmo dia que não estejam duplicados
            eventos = _mesclar_com_manual(eventos, data_ref)
            return sorted(eventos, key=lambda e: e.get("horario", "99:99"))
    except Exception as exc:
        logger.warning("Agenda investing.com: %s", exc)

    # 2ª tentativa: JSON manual
    import calendario_economico
    eventos = calendario_economico.eventos_do_dia(data_ref)
    logger.info("Agenda via JSON manual (%d eventos)", len(eventos))
    return eventos


def _mesclar_com_manual(web_eventos: list, data_ref: date) -> list:
    """Adiciona eventos do JSON manual que não estejam já no resultado web."""
    import calendario_economico
    manuais = calendario_economico.eventos_do_dia(data_ref)
    if not manuais:
        return web_eventos

    chaves_web = {(e["horario"], e["indicador"][:20].lower()) for e in web_eventos}
    for ev in manuais:
        chave = (ev["horario"], ev["indicador"][:20].lower())
        if chave not in chaves_web:
            web_eventos.append(ev)

    return web_eventos


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def buscar_todos(data_ref: date = None) -> dict:
    """Retorna dicionário completo com dados de mercado para o template."""
    logger.info("Iniciando coleta de dados de mercado...")
    altas, baixas = buscar_maiores_movimentos()

    return {
        "cambio":               buscar_cambio(),
        "bolsas_cotacoes":      buscar_bolsas(),
        "maiores_altas":        altas,
        "maiores_baixas":       baixas,
        "commodities_cotacoes": buscar_commodities(),
        "cripto_cotacoes":      buscar_cripto(),
        "indicadores":          buscar_indicadores(),
    }
