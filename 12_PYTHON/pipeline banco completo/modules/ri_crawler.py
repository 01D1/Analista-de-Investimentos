"""
ri_crawler.py

Crawler leve e configuravel para sites de Relações com Investidores.

Ele nao tenta "adivinhar" todos os portais da internet. A fonte inicial deve vir
de `empresas.yaml` (`ri_url`, `ri_urls`, `fontes_ri`) ou do CLI (`--ri-url`).
Depois disso, navega links internos relevantes, baixa HTML/PDF legivel e salva
metadados preservados em data/qualitative/raw/<TICKER>/auto_ri.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

from modules.qualitative_engine import _http_get, _is_usable_text, _safe_name

logger = logging.getLogger("pipeline.ri_crawler")

RELEVANT_TERMS = [
    "resultado", "resultados", "release", "apresentacao", "apresentação",
    "itr", "dfp", "demonstracoes", "demonstrações", "fato-relevante",
    "fato relevante", "comunicado", "assembleia", "ata", "governanca",
    "governança", "formulario-de-referencia", "formulário de referência",
    "transcricao", "transcrição", "teleconferencia", "teleconferência",
    "earnings", "results", "presentation", "financial", "reference-form",
]

DOC_EXTS = (".pdf", ".html", ".htm", ".txt", ".docx")
SKIP_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".mp4", ".mp3", ".zip")

PORTAL_ADAPTERS = {
    "mz_group": {
        "patterns": ["mzgroup", "mziq", "mz-sites", "mz-filemanager"],
        "paths": ["resultados-e-comunicados", "central-de-resultados", "informacoes-financeiras", "documentos-cvm"],
    },
    "riweb": {
        "patterns": ["riweb", "riweb.com.br"],
        "paths": ["resultados-e-comunicados", "central-de-resultados", "servicos-aos-investidores"],
    },
    "empresas_net_cvm": {
        "patterns": ["empresas.net", "cvm", "dados.cvm.gov.br"],
        "paths": ["fatos-relevantes", "comunicados", "assembleias", "documentos-cvm"],
    },
    "portal_proprio": {
        "patterns": [],
        "paths": [
            "ri", "investidores", "relacoes-com-investidores", "resultados",
            "central-de-resultados", "comunicados-e-fatos-relevantes",
            "governanca-corporativa", "informacoes-financeiras",
        ],
    },
}


@dataclass
class RICrawlResult:
    ticker: str
    started_at: str
    source_urls: list[str]
    visited_pages: int
    saved_documents: int
    saved_paths: list[str]
    adapters: list[str]
    errors: list[str]


def _normalize_sources(sources: Iterable[str] | str | None) -> list[str]:
    if not sources:
        return []
    if isinstance(sources, str):
        sources = [sources]
    out = []
    for src in sources:
        src = str(src or "").strip()
        if not src:
            continue
        if not src.startswith(("http://", "https://")):
            src = "https://" + src
        out.append(src)
    return list(dict.fromkeys(out))


def _same_domain_or_child(base_url: str, candidate: str) -> bool:
    base = urlparse(base_url)
    cand = urlparse(candidate)
    if not cand.netloc:
        return True
    return cand.netloc == base.netloc or cand.netloc.endswith("." + base.netloc)


def _looks_relevant(url: str, text: str = "") -> bool:
    haystack = f"{url} {text}".lower()
    if any(haystack.split("?")[0].endswith(ext) for ext in DOC_EXTS):
        return True
    return any(term in haystack for term in RELEVANT_TERMS)


def _extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag.get("href", "")
            text = tag.get_text(" ", strip=True)
            links.append((urljoin(base_url, href), text))
    except Exception:
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
            links.append((urljoin(base_url, match.group(1)), ""))
    clean = []
    seen = set()
    for url, text in links:
        url = url.split("#")[0].strip()
        if not url or url in seen or url.startswith(("mailto:", "tel:", "javascript:")):
            continue
        seen.add(url)
        clean.append((url, text))
    return clean


def _detect_adapters(url: str, html: str = "") -> list[str]:
    haystack = f"{url} {html[:5000]}".lower()
    adapters = []
    for name, cfg in PORTAL_ADAPTERS.items():
        patterns = cfg.get("patterns") or []
        if name == "portal_proprio" or any(pat in haystack for pat in patterns):
            adapters.append(name)
    return adapters


def _adapter_seed_urls(source_url: str, adapters: list[str]) -> list[tuple[str, str]]:
    base = source_url.rstrip("/") + "/"
    seeds: list[tuple[str, str]] = []
    for adapter in adapters:
        for path in PORTAL_ADAPTERS.get(adapter, {}).get("paths", []):
            seeds.append((urljoin(base, path.strip("/") + "/"), f"adapter {adapter}: {path}"))
    dedup = []
    seen = set()
    for url, label in seeds:
        if url not in seen:
            seen.add(url)
            dedup.append((url, label))
    return dedup


def _extract_api_links(html: str, base_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in re.finditer(r'["\']([^"\']*(?:api|wp-json|graphql)[^"\']*)["\']', html, flags=re.I):
        raw = match.group(1)
        if not raw or raw.startswith(("data:", "javascript:")):
            continue
        url = urljoin(base_url, raw)
        if _looks_relevant(url, "api resultados documentos ri"):
            links.append((url, "api/json RI"))
    return links[:20]


def _html_to_text(html: str) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _save_content(ticker: str, out_dir: Path, url: str, content: bytes, content_type: str, label: str = "") -> Path | None:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    name = _safe_name(label or Path(urlparse(url).path).name or "documento_ri")
    base = out_dir / f"{digest}_{name}"
    content_type = (content_type or "").lower()

    if content.startswith(b"%PDF") or "pdf" in content_type or urlparse(url).path.lower().endswith(".pdf"):
        dest = base.with_suffix(".pdf")
        dest.write_bytes(content)
        return dest

    decoded = content.decode("utf-8", errors="ignore")
    text = _html_to_text(decoded)
    if _is_usable_text(text):
        dest = base.with_suffix(".html")
        dest.write_text(decoded, encoding="utf-8", errors="ignore")
        return dest

    meta = base.with_suffix(".txt")
    meta.write_text(
        f"Fonte: Site RI\nTicker: {ticker}\nURL: {url}\nTitulo: {label}\nConteudo nao textual ou nao legivel para extracao automatica.\n",
        encoding="utf-8",
    )
    return meta


def crawl_ri_sources(
    *,
    ticker: str,
    source_urls: Iterable[str] | str | None,
    base_dir: str | Path,
    max_docs: int = 25,
    max_pages: int = 40,
    depth: int = 1,
) -> dict:
    ticker = ticker.upper()
    sources = _normalize_sources(source_urls)
    paths: list[str] = []
    errors: list[str] = []
    adapters_detected: set[str] = set()
    visited: set[str] = set()
    queue: list[tuple[str, int, str]] = [(url, 0, "pagina inicial RI") for url in sources]
    out_dir = Path(base_dir) / "data" / "qualitative" / "raw" / ticker / "auto_ri"
    out_dir.mkdir(parents=True, exist_ok=True)

    while queue and len(visited) < max_pages and len(paths) < max_docs:
        url, level, label = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        parsed_path = urlparse(url).path.lower()
        if any(parsed_path.endswith(ext) for ext in SKIP_EXTS):
            continue
        try:
            content, headers = _http_get(url, timeout=25)
            content_type = headers.get("content-type", "")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue

        saved = None
        if _looks_relevant(url, label):
            saved = _save_content(ticker, out_dir, url, content, content_type, label)
            if saved:
                paths.append(str(saved))
                if len(paths) >= max_docs:
                    break

        is_html = (
            "html" in content_type.lower()
            or parsed_path.endswith((".html", ".htm"))
            or b"<html" in content[:2000].lower()
        )
        if level >= depth or not is_html:
            continue
        html = content.decode("utf-8", errors="ignore")
        adapters = _detect_adapters(url, html)
        adapters_detected.update(adapters)
        if level == 0:
            for seed_url, seed_label in _adapter_seed_urls(url, adapters):
                if seed_url not in visited and _same_domain_or_child(url, seed_url):
                    queue.append((seed_url, level + 1, seed_label))
        for link, text in _extract_links(html, url):
            if link in visited or not _same_domain_or_child(url, link):
                continue
            if _looks_relevant(link, text):
                queue.append((link, level + 1, text or "documento RI"))
        for link, text in _extract_api_links(html, url):
            if link not in visited and _same_domain_or_child(url, link):
                queue.append((link, level + 1, text))

    result = RICrawlResult(
        ticker=ticker,
        started_at=datetime.now().isoformat(),
        source_urls=sources,
        visited_pages=len(visited),
        saved_documents=len(paths),
        saved_paths=paths,
        adapters=sorted(adapters_detected),
        errors=errors[:50],
    )
    index_path = out_dir / "ri_crawl_index.json"
    index_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[ri_crawler] %s: fontes=%d visitadas=%d salvos=%d", ticker, len(sources), len(visited), len(paths))
    return asdict(result)
