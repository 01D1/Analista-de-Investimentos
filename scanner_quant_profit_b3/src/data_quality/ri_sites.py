"""Cadastro, validacao e descoberta de sites de RI das empresas B3."""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import yaml

_SCANNER_ROOT = Path(__file__).resolve().parents[2]


def project_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else _SCANNER_ROOT / p


RI_SITE_COLUMNS = [
    "ticker",
    "company_name",
    "cnpj",
    "ri_url",
    "ri_url_final",
    "source",
    "status_code",
    "is_valid",
    "confidence_score",
    "last_checked_at",
    "notes",
]

DEFAULT_RI_SITES_PATH = project_path("data/qualitative/ri_sites.csv")
DEFAULT_REVIEW_PATH = project_path("data/qualitative/ri_sites_review_needed.csv")

RI_TERMS = (
    "ri",
    "investidor",
    "investidores",
    "investor",
    "investors",
    "investor-relations",
    "relacoes-com-investidores",
    "relacao-com-investidores",
    "relações-com-investidores",
    "relação-com-investidores",
)

GENERIC_DOMAINS = (
    "google.",
    "bing.",
    "duckduckgo.",
    "statusinvest.",
    "investidor10.",
    "fundamentus.",
    "tradingview.",
    "yahoo.",
    "b3.com.br",
    "cvm.gov.br",
)

CURATED_RI_REGISTRY: dict[str, dict[str, str]] = {
    "BBAS3": {
        "company_name": "Banco do Brasil S.A.",
        "cnpj": "00.000.000/0001-91",
        "ri_url": "https://ri.bb.com.br/",
    },
    "BBDC4": {
        "company_name": "Banco Bradesco S.A.",
        "cnpj": "60.746.948/0001-12",
        "ri_url": "https://www.bradescori.com.br/",
    },
    "BPAC11": {
        "company_name": "Banco BTG Pactual S.A.",
        "cnpj": "30.306.294/0001-45",
        "ri_url": "https://ri.btgpactual.com/",
    },
    "ITUB4": {
        "company_name": "Itau Unibanco Holding S.A.",
        "cnpj": "60.872.504/0001-23",
        "ri_url": "https://www.itau.com.br/relacoes-com-investidores/",
    },
    "PETR4": {
        "company_name": "Petroleo Brasileiro S.A. - Petrobras",
        "cnpj": "33.000.167/0001-01",
        "ri_url": "https://www.investidorpetrobras.com.br/",
    },
    "SANB11": {
        "company_name": "Banco Santander (Brasil) S.A.",
        "cnpj": "90.400.888/0001-42",
        "ri_url": "https://ri.santander.com.br/",
    },
    "SUZB3": {
        "company_name": "Suzano S.A.",
        "cnpj": "16.404.287/0001-55",
        "ri_url": "https://ri.suzano.com.br/",
    },
    "VALE3": {
        "company_name": "Vale S.A.",
        "cnpj": "33.592.510/0001-54",
        "ri_url": "https://www.vale.com/pt/investidores",
    },
    "WEGE3": {
        "company_name": "WEG S.A.",
        "cnpj": "84.429.695/0001-11",
        "ri_url": "http://ri.weg.net/",
    },
}


@dataclass(frozen=True)
class UrlFetchResult:
    status_code: int | None
    final_url: str
    text: str = ""
    error: str = ""


class _SearchLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href") or ""
        if not href:
            return
        parsed = urllib.parse.urlparse(href)
        if parsed.path.startswith("/l/") and "uddg=" in parsed.query:
            query = urllib.parse.parse_qs(parsed.query)
            href = query.get("uddg", [""])[0]
        if href.startswith("http"):
            self.links.append(urllib.parse.unquote(href))


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_ticker(ticker: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(ticker or "").upper())


def _ticker_issuer(ticker: str) -> str:
    return re.sub(r"[^A-Z]", "", str(ticker or "").upper())


def _digits(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _format_cnpj(value: str) -> str:
    digits = _digits(value)
    if len(digits) != 14:
        return str(value or "")
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _normalize_text(value: str) -> str:
    return (
        str(value or "")
        .lower()
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("õ", "o")
        .replace("ô", "o")
        .replace("ú", "u")
    )


def _url_has_ri_signal(url: str) -> bool:
    parsed = urllib.parse.urlparse(str(url or ""))
    haystack = _normalize_text(f"{parsed.netloc} {parsed.path}")
    tokens = {token for token in re.split(r"[^a-z0-9]+", haystack) if token}
    if "ri" in tokens:
        return True
    return any(_normalize_text(term).replace(" ", "-") in haystack for term in RI_TERMS if len(term) > 2)


def _page_has_ri_signal(text: str) -> bool:
    haystack = _normalize_text(text[:50000])
    return any(_normalize_text(term).replace("-", " ") in haystack for term in RI_TERMS)


def _looks_generic(url: str) -> bool:
    parsed = urllib.parse.urlparse(str(url or ""))
    host = parsed.netloc.lower()
    path = parsed.path.strip("/").lower()
    if not host:
        return True
    if any(domain in host for domain in GENERIC_DOMAINS):
        return True
    return path in {"", "pt", "pt-br", "br", "home"} and not _url_has_ri_signal(url)


def _domain_from_email(email: str) -> str:
    match = re.search(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", str(email or ""))
    return match.group(1).lower().strip(".") if match else ""


def _base_domain_from_url_or_domain(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "@" in raw:
        raw = _domain_from_email(raw)
    parsed = urllib.parse.urlparse(raw if "://" in raw else f"https://{raw}")
    return parsed.netloc.lower().strip(".")


def _candidate_urls_from_domain(domain: str) -> list[str]:
    domain = _base_domain_from_url_or_domain(domain)
    if not domain:
        return []
    if domain.startswith("www."):
        bare = domain[4:]
    else:
        bare = domain
    domains = [domain]
    if not bare.startswith("ri."):
        domains.append(f"ri.{bare}")
    urls: list[str] = []
    for host in dict.fromkeys(domains):
        urls.append(f"https://{host}/")
    for host in dict.fromkeys([domain, bare, f"www.{bare}"]):
        urls.extend(
            [
                f"https://{host}/ri",
                f"https://{host}/relacoes-com-investidores",
                f"https://{host}/relacao-com-investidores",
                f"https://{host}/investidores",
                f"https://{host}/investor-relations",
            ]
        )
    return list(dict.fromkeys(urls))


def _fetch_url(url: str, timeout: int = 10) -> UrlFetchResult:
    headers = {
        "User-Agent": "Mozilla/5.0 scanner-quant-ri-sites/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read(60000)
            encoding = resp.headers.get_content_charset() or "utf-8"
            return UrlFetchResult(int(resp.status), resp.url, content.decode(encoding, errors="ignore"))
    except urllib.error.HTTPError as exc:
        return UrlFetchResult(int(exc.code), exc.url or url, error=f"HTTP {exc.code}")
    except Exception as exc:
        return UrlFetchResult(None, url, error=str(exc))


def validate_ri_url(
    url: str,
    *,
    timeout: int = 10,
    fetcher: Callable[[str, int], UrlFetchResult] | None = None,
    checked_at: str | None = None,
) -> dict[str, object]:
    """Valida uma URL de RI e retorna campos prontos para o CSV final."""
    checked = checked_at or _now_iso()
    clean_url = str(url or "").strip()
    if not clean_url:
        return {
            "ri_url_final": "",
            "status_code": pd.NA,
            "is_valid": False,
            "confidence_score": 0.0,
            "last_checked_at": checked,
            "notes": "URL ausente.",
        }
    parsed = urllib.parse.urlparse(clean_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {
            "ri_url_final": clean_url,
            "status_code": pd.NA,
            "is_valid": False,
            "confidence_score": 0.0,
            "last_checked_at": checked,
            "notes": "URL malformada.",
        }

    fetch = fetcher or _fetch_url
    result = fetch(clean_url, timeout)
    final_url = result.final_url or clean_url
    status_code = result.status_code
    status_ok = bool(status_code is not None and 200 <= int(status_code) < 400)
    signal = _url_has_ri_signal(final_url) or _page_has_ri_signal(result.text)
    generic = _looks_generic(final_url) and not _page_has_ri_signal(result.text)
    valid = bool(status_ok and signal and not generic)

    score = 0.0
    if status_ok:
        score += 0.35
    if _url_has_ri_signal(final_url):
        score += 0.35
    if _page_has_ri_signal(result.text):
        score += 0.2
    if not generic:
        score += 0.1
    score = round(min(score, 1.0), 2)

    notes: list[str] = []
    if result.error:
        notes.append(result.error)
    if not status_ok:
        notes.append("Status HTTP invalido ou indisponivel.")
    if generic:
        notes.append("URL parece generica.")
    if not signal:
        notes.append("Sem sinal claro de RI/investidores na URL ou pagina.")
    if clean_url != final_url:
        notes.append("Redirecionamento validado; URL final salva.")

    return {
        "ri_url_final": final_url,
        "status_code": status_code if status_code is not None else pd.NA,
        "is_valid": valid,
        "confidence_score": score,
        "last_checked_at": checked,
        "notes": " ".join(notes) if notes else "URL de RI validada.",
    }


def _read_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=RI_SITE_COLUMNS)
    try:
        df = pd.read_csv(p, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame(columns=RI_SITE_COLUMNS)
    for col in RI_SITE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[RI_SITE_COLUMNS]


def load_ri_sites(path: str | Path | None = None) -> pd.DataFrame:
    return _read_csv(path or DEFAULT_RI_SITES_PATH)


def save_ri_sites(df: pd.DataFrame, path: str | Path | None = None) -> Path:
    target = Path(path or DEFAULT_RI_SITES_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in RI_SITE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out[RI_SITE_COLUMNS].to_csv(target, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return target


def save_review_needed(df: pd.DataFrame, path: str | Path | None = None) -> Path:
    target = Path(path or DEFAULT_REVIEW_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in RI_SITE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    mask = (
        ~out["is_valid"].astype(str).str.lower().isin({"true", "1", "sim"})
        | (pd.to_numeric(out["confidence_score"], errors="coerce").fillna(0) < 0.7)
        | out["notes"].astype(str).str.contains("generica|conflito|HTTP|ausente|malformada", case=False, na=False)
    )
    out.loc[mask, RI_SITE_COLUMNS].to_csv(target, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return target


def _load_yaml_ri_urls(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame(columns=["ticker", "company_name", "cnpj", "ri_url"])
    p = Path(path)
    if not p.is_absolute():
        p = project_path(str(path))
    if not p.exists():
        return pd.DataFrame(columns=["ticker", "company_name", "cnpj", "ri_url"])
    try:
        payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return pd.DataFrame(columns=["ticker", "company_name", "cnpj", "ri_url"])
    if isinstance(payload, dict) and isinstance(payload.get("empresas"), dict):
        payload = payload["empresas"]
    items = payload.items() if isinstance(payload, dict) else enumerate(payload if isinstance(payload, list) else [])
    rows = []
    for key, value in items:
        if not isinstance(value, dict):
            continue
        ticker = _normalize_ticker(value.get("ticker") or key)
        if not ticker or not any(ch.isdigit() for ch in ticker):
            continue
        ri_url = str(value.get("ri_url") or value.get("site_ri") or value.get("url_ri") or "").strip()
        rows.append(
            {
                "ticker": ticker,
                "company_name": str(value.get("company_name") or value.get("nome") or value.get("name") or ""),
                "cnpj": str(value.get("cnpj") or ""),
                "ri_url": ri_url,
            }
        )
    return pd.DataFrame(rows, columns=["ticker", "company_name", "cnpj", "ri_url"])


def load_monitored_tickers(config_paths: Iterable[str | Path] | None = None) -> list[str]:
    tickers: list[str] = []
    paths = list(config_paths or ["config.yaml", "config_quant.yaml", "config.example.yaml"])
    for path in paths:
        p = Path(path)
        if not p.is_absolute():
            p = project_path(str(path))
        if not p.exists():
            continue
        try:
            payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for key in ("ativos_base", "ativos_permitidos", "tickers"):
            values = payload.get(key) or []
            if isinstance(values, list):
                tickers.extend(_normalize_ticker(v) for v in values)
    tickers.extend(load_ri_sites()["ticker"].astype(str).tolist())
    tickers.extend(CURATED_RI_REGISTRY)
    return sorted({t for t in tickers if t and any(ch.isdigit() for ch in t)})


def load_b3_equity_universe(db_path: str | Path | None = None, latest_date: str | None = None) -> pd.DataFrame:
    """Carrega acoes/units negociadas no ultimo pregao local do COTAHIST."""
    db = Path(db_path or project_path("data/database/scanner_quant.db"))
    columns = ["ticker", "company_name", "cnpj", "source_url", "source", "trades", "volume", "last_trade_date"]
    if not db.exists():
        return pd.DataFrame(columns=columns)
    with sqlite3.connect(db) as con:
        date = latest_date or con.execute(
            "select max(trade_date) from cotahist_daily where market_type='010' and option_type is null"
        ).fetchone()[0]
        df = pd.read_sql_query(
            """
            select ticker, company_name, specification, trades, volume, trade_date as last_trade_date
            from cotahist_daily
            where trade_date=?
              and market_type='010'
              and option_type is null
              and bdi_code='02'
            order by ticker
            """,
            con,
            params=[date],
        )
    if df.empty:
        return pd.DataFrame(columns=columns)
    df["ticker"] = df["ticker"].astype(str).map(_normalize_ticker)
    df["company_name"] = df["company_name"].astype(str).str.strip()
    df["cnpj"] = ""
    df["source_url"] = ""
    df["source"] = "b3_cotahist_local"
    return df[columns]


def fetch_b3_listed_companies(timeout: int = 20) -> pd.DataFrame:
    """Consulta a API publica usada pela pagina de empresas listadas da B3."""
    rows: list[dict[str, str]] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = {"language": "pt-br", "pageNumber": page, "pageSize": 100}
        encoded = urllib.parse.quote(
            __import__("base64").b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
        )
        url = f"https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        page_info = data.get("page") or {}
        total_pages = int(page_info.get("totalPages") or total_pages)
        for item in data.get("results") or []:
            rows.append(
                {
                    "issuer": _ticker_issuer(item.get("issuingCompany", "")),
                    "company_name": str(item.get("companyName") or item.get("tradingName") or ""),
                    "trading_name": str(item.get("tradingName") or ""),
                    "cnpj": _format_cnpj(str(item.get("cnpj") or "")),
                    "code_cvm": str(item.get("codeCVM") or ""),
                    "source": "b3_listed_companies_api",
                }
            )
        page += 1
    return pd.DataFrame(rows).drop_duplicates(subset=["issuer", "cnpj", "company_name"])


def fetch_cvm_company_registry(timeout: int = 30) -> pd.DataFrame:
    """Baixa o cadastro oficial de companhias abertas da CVM."""
    url = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 scanner-quant-ri-sites/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    df = pd.read_csv(io.BytesIO(payload), sep=";", encoding="latin1", dtype=str).fillna("")
    out = pd.DataFrame(
        {
            "cnpj": df.get("CNPJ_CIA", pd.Series(dtype=str)).map(_format_cnpj),
            "company_name_cvm": df.get("DENOM_SOCIAL", pd.Series(dtype=str)),
            "trading_name_cvm": df.get("DENOM_COMERC", pd.Series(dtype=str)),
            "cvm_status": df.get("SIT", pd.Series(dtype=str)),
            "ri_email": df.get("EMAIL", pd.Series(dtype=str)),
            "ri_email_resp": df.get("EMAIL_RESP", pd.Series(dtype=str)),
            "cvm_code": df.get("CD_CVM", pd.Series(dtype=str)),
        }
    )
    out["source_url"] = out["ri_email"].map(_domain_from_email)
    out.loc[out["source_url"].eq(""), "source_url"] = out.loc[out["source_url"].eq(""), "ri_email_resp"].map(_domain_from_email)
    return out.drop_duplicates(subset=["cnpj"])


def build_b3_ri_research_universe(
    *,
    db_path: str | Path | None = None,
    exclude_valid_existing: bool = True,
    timeout: int = 30,
) -> pd.DataFrame:
    """Combina COTAHIST local, B3 e CVM para pesquisar RI dos tickers restantes."""
    universe = load_b3_equity_universe(db_path)
    if universe.empty:
        return universe
    try:
        b3 = fetch_b3_listed_companies(timeout=timeout)
    except Exception:
        b3 = pd.DataFrame(columns=["issuer", "company_name", "trading_name", "cnpj", "source"])
    if not b3.empty:
        universe["issuer"] = universe["ticker"].map(_ticker_issuer)
        b3 = b3.sort_values(["issuer", "company_name"]).drop_duplicates(subset=["issuer"], keep="first")
        universe = universe.merge(b3[["issuer", "company_name", "trading_name", "cnpj", "source"]], on="issuer", how="left", suffixes=("", "_b3"))
        universe["company_name"] = universe["company_name_b3"].fillna("").where(universe["company_name_b3"].fillna("").ne(""), universe["company_name"])
        universe["cnpj"] = universe["cnpj_b3"].fillna("").where(universe["cnpj_b3"].fillna("").ne(""), universe["cnpj"])
        universe["source"] = universe["source_b3"].fillna("").where(universe["source_b3"].fillna("").ne(""), universe["source"])
        universe = universe.drop(columns=[c for c in ["issuer", "company_name_b3", "cnpj_b3", "source_b3"] if c in universe.columns])
    try:
        cvm = fetch_cvm_company_registry(timeout=timeout)
    except Exception:
        cvm = pd.DataFrame(columns=["cnpj", "company_name_cvm", "source_url"])
    if not cvm.empty and "cnpj" in universe.columns:
        universe = universe.merge(cvm, on="cnpj", how="left")
        universe["company_name"] = universe.get("company_name_cvm", "").fillna("").where(
            universe.get("company_name_cvm", "").fillna("").ne(""), universe["company_name"]
        )
        universe["source_url"] = universe.get("source_url_y", "").fillna("").where(
            universe.get("source_url_y", "").fillna("").ne(""), universe.get("source_url_x", "")
        )
        universe = universe.drop(columns=[c for c in ["source_url_x", "source_url_y", "company_name_cvm"] if c in universe.columns])
    for col in ["source_url", "cnpj", "source"]:
        if col not in universe.columns:
            universe[col] = ""
    if exclude_valid_existing:
        existing = load_ri_sites()
        valid = set(
            existing[
                existing["is_valid"].astype(str).str.lower().isin({"true", "1", "sim"})
            ]["ticker"].astype(str).str.upper()
        )
        universe = universe[~universe["ticker"].isin(valid)].copy()
    return universe[["ticker", "company_name", "cnpj", "source_url", "source", "trades", "volume", "last_trade_date"]]


def _duckduckgo_links(query: str, timeout: int = 10) -> list[str]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    result = _fetch_url(url, timeout=timeout)
    if result.status_code != 200 or not result.text:
        return []
    parser = _SearchLinkParser()
    parser.feed(result.text)
    return parser.links[:10]


def search_ri_candidates(company_name: str, ticker: str, cnpj: str = "", *, timeout: int = 10) -> list[dict[str, str]]:
    queries = [
        f"{company_name} RI",
        f"{company_name} relacoes com investidores",
        f"{ticker} RI",
        f"{cnpj} RI" if cnpj else "",
    ]
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in [q for q in queries if q.strip()]:
        for link in _duckduckgo_links(query, timeout=timeout):
            if link in seen:
                continue
            seen.add(link)
            if _looks_generic(link):
                continue
            if _url_has_ri_signal(link):
                candidates.append({"ri_url": link, "source": f"web_search:{query}"})
    return candidates


def _best_existing(existing: pd.DataFrame, ticker: str) -> dict[str, str]:
    if existing.empty:
        return {}
    rows = existing[existing["ticker"].astype(str).str.upper() == ticker]
    if rows.empty:
        return {}
    row = rows.iloc[0].to_dict()
    return {str(k): "" if pd.isna(v) else str(v) for k, v in row.items()}


def _candidate_registry(ticker: str) -> dict[str, str]:
    payload = CURATED_RI_REGISTRY.get(ticker, {})
    if not payload:
        return {}
    return {**payload, "source": "curated_official_ri_registry"}


def _registry_row(registry: pd.DataFrame | None, ticker: str) -> dict[str, str]:
    if registry is None or registry.empty or "ticker" not in registry.columns:
        return {}
    rows = registry[registry["ticker"].astype(str).str.upper() == ticker]
    if rows.empty:
        return {}
    row = rows.iloc[0].to_dict()
    return {str(k): "" if pd.isna(v) else str(v) for k, v in row.items()}


def _build_base_row(ticker: str, existing: pd.DataFrame, legacy: pd.DataFrame, registry: pd.DataFrame | None = None) -> dict[str, str]:
    row = _best_existing(existing, ticker)
    if not row and not legacy.empty:
        match = legacy[legacy["ticker"].astype(str).str.upper() == ticker]
        if not match.empty:
            row = match.iloc[0].to_dict()
            row["source"] = "legacy_empresas_yaml"
    reg = _registry_row(registry, ticker)
    curated = CURATED_RI_REGISTRY.get(ticker, {})
    return {
        "ticker": ticker,
        "company_name": str(row.get("company_name") or reg.get("company_name") or curated.get("company_name") or ticker),
        "cnpj": str(row.get("cnpj") or reg.get("cnpj") or curated.get("cnpj") or ""),
        "ri_url": str(row.get("ri_url") or ""),
        "ri_url_final": str(row.get("ri_url_final") or ""),
        "source": str(row.get("source") or reg.get("source") or ""),
        "source_url": str(reg.get("source_url") or ""),
    }


def _append_domain_candidates(candidates: list[dict[str, str]], source_url: str, source: str) -> None:
    for url in _candidate_urls_from_domain(source_url):
        candidates.append({"ri_url": url, "source": source})


def update_ri_sites(
    *,
    tickers: list[str] | None = None,
    ri_sites_path: str | Path | None = None,
    review_path: str | Path | None = None,
    empresas_yaml: str | Path | None = None,
    company_registry: pd.DataFrame | None = None,
    search_online: bool = True,
    timeout: int = 10,
    fetcher: Callable[[str, int], UrlFetchResult] | None = None,
) -> dict[str, object]:
    """Atualiza a base local de sites de RI e salva pendencias para revisao."""
    existing = load_ri_sites(ri_sites_path)
    legacy = _load_yaml_ri_urls(empresas_yaml)
    ticker_list = sorted({_normalize_ticker(t) for t in (tickers or load_monitored_tickers()) if _normalize_ticker(t)})
    rows: list[dict[str, object]] = []
    corrected: list[str] = []

    for ticker in ticker_list:
        base = _build_base_row(ticker, existing, legacy, company_registry)
        candidates: list[dict[str, str]] = []
        if base.get("ri_url"):
            candidates.append({"ri_url": str(base["ri_url"]), "source": str(base.get("source") or "existing_ri_sites_csv")})
        curated = _candidate_registry(ticker)
        if curated and curated.get("ri_url") != base.get("ri_url"):
            candidates.append(curated)
        if base.get("source_url"):
            _append_domain_candidates(candidates, str(base["source_url"]), "cvm_b3_domain_candidates")

        best: dict[str, object] | None = None
        seen_candidates: set[str] = set()

        def evaluate(candidate_rows: list[dict[str, str]]) -> None:
            nonlocal best
            for candidate in candidate_rows:
                candidate_url = str(candidate.get("ri_url") or "")
                if not candidate_url or candidate_url in seen_candidates:
                    continue
                seen_candidates.add(candidate_url)
                validation = validate_ri_url(candidate_url, timeout=timeout, fetcher=fetcher)
                candidate_score = float(validation["confidence_score"] or 0)
                if candidate.get("source") == "curated_official_ri_registry":
                    candidate_score = min(1.0, candidate_score + 0.1)
                current = {
                    **base,
                    "ri_url": candidate_url,
                    "ri_url_final": validation["ri_url_final"],
                    "source": candidate.get("source", ""),
                    "status_code": validation["status_code"],
                    "is_valid": validation["is_valid"],
                    "confidence_score": round(candidate_score, 2),
                    "last_checked_at": validation["last_checked_at"],
                    "notes": validation["notes"],
                }
                if best is None or (
                    bool(current["is_valid"]) > bool(best["is_valid"])
                    or float(current["confidence_score"] or 0) > float(best["confidence_score"] or 0)
                ):
                    best = current
                if current["is_valid"]:
                    break

        evaluate(candidates)
        if search_online and not bool(best and best.get("is_valid")):
            evaluate(search_ri_candidates(base["company_name"], ticker, base["cnpj"], timeout=timeout))

        # Optional convention fallback after web search: some issuers publish at ri.<ticker-prefix>.com.br.
        if search_online and not bool(best and best.get("is_valid")):
            issuer = _ticker_issuer(ticker).lower()
            evaluate([{"ri_url": f"https://ri.{issuer}.com.br/", "source": "ticker_domain_guess"}])

        if best is None:
            validation = validate_ri_url("", timeout=timeout, fetcher=fetcher)
            best = {
                **base,
                "status_code": validation["status_code"],
                "is_valid": False,
                "confidence_score": 0.0,
                "last_checked_at": validation["last_checked_at"],
                "notes": "RI nao encontrado; revisar manualmente.",
            }
        if str(base.get("ri_url") or "") and str(best.get("ri_url_final") or "") and str(base.get("ri_url") or "") != str(best.get("ri_url_final") or ""):
            corrected.append(ticker)
        elif not str(base.get("ri_url") or "") and str(best.get("ri_url_final") or ""):
            corrected.append(ticker)
        rows.append(best)
        time.sleep(0.05 if fetcher is None else 0)

    final = pd.DataFrame(rows, columns=RI_SITE_COLUMNS)
    save_path = save_ri_sites(final, ri_sites_path)
    review_save_path = save_review_needed(final, review_path)
    valid_count = int(final["is_valid"].astype(bool).sum()) if not final.empty else 0
    pending = final[~final["is_valid"].astype(bool)]["ticker"].astype(str).tolist() if not final.empty else []
    summary = {
        "analyzed_count": len(final),
        "valid_count": valid_count,
        "corrected_count": len(set(corrected)),
        "pending_count": len(pending),
        "pending_tickers": pending,
        "error_tickers": pending,
        "ri_sites_path": str(save_path),
        "review_path": str(review_save_path),
    }
    print(
        "RI sites update: "
        f"{summary['analyzed_count']} analisados, "
        f"{summary['valid_count']} validos, "
        f"{summary['corrected_count']} corrigidos, "
        f"{summary['pending_count']} pendentes."
    )
    if pending:
        print("Pendentes: " + ", ".join(pending))
    return {"summary": summary, "ri_sites": final, "review_needed": load_ri_sites(review_save_path)}


def get_valid_ri_url_for_ticker(ticker: str, path: str | Path | None = None) -> str:
    df = load_ri_sites(path)
    if df.empty:
        return ""
    rows = df[df["ticker"].astype(str).str.upper() == _normalize_ticker(ticker)]
    if rows.empty:
        return ""
    row = rows.iloc[0]
    is_valid = str(row.get("is_valid", "")).lower() in {"true", "1", "sim"}
    if not is_valid:
        return ""
    return str(row.get("ri_url_final") or row.get("ri_url") or "").strip()
