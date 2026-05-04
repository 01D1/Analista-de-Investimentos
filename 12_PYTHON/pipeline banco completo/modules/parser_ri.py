"""
parser_ri.py — Extração de dados qualitativos de releases e documentos CVM.

Baixa e parseia documentos de RI (press releases de resultado, fatos relevantes,
notas explicativas) diretamente da API pública da CVM e extrai:
  - Guidance de crescimento / lucro
  - ROE recorrente (descontando não-recorrentes)
  - Eventos não recorrentes mencionados
  - CAPEX declarado
  - Inadimplência / NPL reportado
  - Basileia declarado (bancos)
  - Comentários de risco da administração
  - Premissas sugeridas para atualizar empresas.yaml

Uso standalone:
    from modules.parser_ri import extrair_dados_ri
    dados = extrair_dados_ri("BBDC4", codigo_cvm="906", cache_dir=Path("cache"))
    print(dados)

Integração com main.py (opcional — enriquece premissas antes do valuation):
    from modules.parser_ri import extrair_dados_ri
    ri = extrair_dados_ri(ticker, codigo_cvm=codigo_cvm, cache_dir=cfg.CACHE_DIR)
    # ri["premissas_sugeridas"] pode ser inspecionado ou logado
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger("pipeline.parser_ri")

_CVM_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
_CVM_DOC  = "https://www.rad.cvm.gov.br/ENET/frmGerenciaPaginaFRE.aspx"
_TIMEOUT  = 20

# ─────────────────────────────────────────────────────────────────────────────
# Padrões de extração por regex
# ─────────────────────────────────────────────────────────────────────────────

_PADROES: dict[str, list[str]] = {
    # Guidance de crescimento de carteira/receita
    "guidance_crescimento": [
        r"crescimento\s+(?:da\s+carteira|de\s+cr[eé]dito|da\s+receita)[^\d]*(\d[\d,.]+)\s*%",
        r"crescimento\s+(?:previsto|esperado|projetado)[^\d]*(\d[\d,.]+)\s*%",
        r"guidance[^\d]*crescimento[^\d]*(\d[\d,.]+)\s*%",
        r"projetamos?\s+crescimento[^\d]*(\d[\d,.]+)\s*%",
    ],
    # Guidance de lucro líquido
    "guidance_lucro": [
        r"lucro\s+l[ií]quido\s+(?:previsto|esperado|guidance)[^\d]*([\d,.]+)\s*(?:milh[õo]es|bilh[õo]es|MM|BN)",
        r"guidance\s+(?:de\s+)?lucro[^\d]*([\d,.]+)\s*(?:milh[õo]es|bilh[õo]es|MM|BN)",
        r"lucro\s+recorrente[^\d]*([\d,.]+)\s*(?:milh[õo]es|bilh[õo]es|MM)",
    ],
    # ROE recorrente
    "roe_recorrente": [
        r"roe\s+recorrente[^\d]*(\d[\d,.]+)\s*%",
        r"retorno\s+(?:sobre\s+)?(?:o\s+)?patrim[oô]nio\s+recorrente[^\d]*(\d[\d,.]+)\s*%",
        r"roe[^\d]*(\d[\d,.]+)\s*%\s*(?:\(recorrente\)|recorrente)",
    ],
    # Inadimplência / NPL
    "inadimplencia": [
        r"inadimpl[eê]ncia[^\d]*(\d[\d,.]+)\s*%",
        r"npl[^\d]*(\d[\d,.]+)\s*%",
        r"atraso\s+acima\s+de\s+90[^\d]*(\d[\d,.]+)\s*%",
        r"carteira\s+em\s+atraso[^\d]*(\d[\d,.]+)\s*%",
        r"pdp?[^\d]*(\d[\d,.]+)\s*%",  # PDP = portfólio em atraso
    ],
    # Basileia
    "basileia": [
        r"[íi]ndice\s+de\s+basil[eé]ia[^\d]*(\d[\d,.]+)\s*%",
        r"basil[eé]ia\s+(?:iii|3)?[^\d]*(\d[\d,.]+)\s*%",
        r"capital\s+principal[^\d]*(\d[\d,.]+)\s*%",
        r"capital\s+tier\s*1[^\d]*(\d[\d,.]+)\s*%",
    ],
    # CAPEX
    "capex": [
        r"capex[^\d]*([\d,.]+)\s*(?:milh[õo]es|bilh[õo]es|MM|BN)",
        r"investimentos?\s+(?:em\s+)?capital[^\d]*([\d,.]+)\s*(?:milh[õo]es|bilh[õo]es|MM|BN)",
        r"capex[^\d]*(\d[\d,.]+)\s*%\s*(?:da\s+receita|do\s+ativo)",
    ],
    # NIM
    "nim": [
        r"nim[^\d]*(\d[\d,.]+)\s*%",
        r"margem\s+financeira\s+(?:l[ií]quida|bruta)[^\d]*(\d[\d,.]+)\s*%",
        r"net\s+interest\s+margin[^\d]*(\d[\d,.]+)\s*%",
    ],
    # Payout
    "payout": [
        r"payout[^\d]*(\d[\d,.]+)\s*%",
        r"distribui[çc][aã]o\s+de\s+(?:resultado|lucro)[^\d]*(\d[\d,.]+)\s*%",
        r"dividendos?\s+(?:e\s+jcp?)[^\d]*(\d[\d,.]+)\s*%\s+do\s+lucro",
    ],
}

# Palavras de risco a rastrear
_PALAVRAS_RISCO = [
    "inadimplência crescendo", "provisão adicional", "cenário adverso",
    "incerteza", "risco fiscal", "volatilidade cambial", "headwind",
    "desaceleração", "pressão de margem", "custo de crédito elevado",
    "impacto não recorrente", "item extraordinário", "write-off",
    "reestruturação", "litigios", "litígios", "contingência",
]

# Palavras de não-recorrente
_PALAVRAS_NAO_RECORRENTE = [
    "não recorrente", "nao recorrente", "extraordinário", "one-off",
    "item especial", "efeito pontual", "ganho de capital", "alienação",
    "baixa contábil", "provisão extraordinária",
]


# ─────────────────────────────────────────────────────────────────────────────
# Download de documentos CVM
# ─────────────────────────────────────────────────────────────────────────────

def _buscar_documentos_cvm(codigo_cvm: str, categoria: str = "IPE") -> list[dict]:
    """
    Busca lista de documentos de uma empresa na CVM.
    categoria: IPE (press releases/fatos relevantes) | DFP | ITR
    """
    url = f"{_CVM_BASE}/{categoria}/CAD/{categoria}_CIA_ABERTA_{categoria}_{codigo_cvm}.csv"
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code != 200:
            # Fallback: busca geral
            url2 = f"{_CVM_BASE}/{categoria}/CAD/{categoria}_CIA_ABERTA.csv"
            resp = requests.get(url2, timeout=_TIMEOUT)
            if resp.status_code != 200:
                return []
        # Parsear CSV simples
        linhas = resp.content.decode("latin-1").splitlines()
        if len(linhas) < 2:
            return []
        headers = [h.strip() for h in linhas[0].split(";")]
        docs = []
        for linha in linhas[1:]:
            campos = [c.strip() for c in linha.split(";")]
            if len(campos) >= len(headers):
                doc = dict(zip(headers, campos))
                if codigo_cvm in doc.get("CD_CVM", ""):
                    docs.append(doc)
        return docs[-20:]  # últimos 20
    except Exception as e:
        logger.debug("Erro ao buscar documentos CVM: %s", e)
        return []


def _baixar_texto_documento(link: str, cache_dir: Path, timeout: int = _TIMEOUT) -> str:
    """
    Baixa um documento e extrai texto bruto.
    Tenta primeiro HTML, depois PDF via pdfplumber.
    """
    cache_key = re.sub(r"[^\w]", "_", link)[:120] + ".txt"
    cache_path = cache_dir / "ri_cache" / cache_key
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore")

    try:
        resp = requests.get(link, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; pipeline-valuation/1.0)"
        })
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        if "pdf" in content_type or link.lower().endswith(".pdf"):
            texto = _extrair_texto_pdf(resp.content)
        else:
            texto = _limpar_html(resp.text)

        if texto:
            cache_path.write_text(texto, encoding="utf-8")
        return texto

    except Exception as e:
        logger.debug("Erro ao baixar %s: %s", link, e)
        return ""


def _extrair_texto_pdf(conteudo: bytes) -> str:
    """Extrai texto de PDF via pdfplumber."""
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            paginas = []
            for page in pdf.pages[:30]:  # máximo 30 páginas
                t = page.extract_text()
                if t:
                    paginas.append(t)
        return "\n".join(paginas)
    except ImportError:
        logger.debug("pdfplumber não instalado — PDFs não serão processados")
        return ""
    except Exception as e:
        logger.debug("Erro ao extrair PDF: %s", e)
        return ""


def _limpar_html(html: str) -> str:
    """Remove tags HTML e retorna texto limpo."""
    texto = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r"<style[^>]*>.*?</style>", " ", texto, flags=re.DOTALL | re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"&[a-z]+;", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Extração de métricas por regex
# ─────────────────────────────────────────────────────────────────────────────

def _extrair_metricas(texto: str) -> dict:
    """Aplica todos os padrões regex ao texto e retorna os valores encontrados."""
    texto_lower = texto.lower()
    resultado = {}

    for campo, padroes in _PADROES.items():
        for padrao in padroes:
            m = re.search(padrao, texto_lower)
            if m:
                valor_str = m.group(1).replace(",", ".").replace(" ", "")
                try:
                    valor = float(valor_str)
                    # Converter % para decimal se > 1 (ex: "15.2%" → 0.152)
                    if campo not in ("capex", "guidance_lucro") and valor > 1:
                        valor = valor / 100
                    resultado[campo] = round(valor, 4)
                    break
                except ValueError:
                    continue

    return resultado


def _extrair_riscos(texto: str) -> list[str]:
    """Identifica menções a fatores de risco no texto."""
    texto_lower = texto.lower()
    encontrados = []
    for palavra in _PALAVRAS_RISCO:
        if palavra in texto_lower:
            # Pega o contexto ao redor
            idx = texto_lower.find(palavra)
            trecho = texto[max(0, idx - 30):idx + len(palavra) + 60].strip()
            trecho = re.sub(r"\s+", " ", trecho)
            encontrados.append(trecho[:120])
    return list(dict.fromkeys(encontrados))[:5]  # deduplicados, máx 5


def _extrair_nao_recorrentes(texto: str) -> list[str]:
    """Identifica menções a itens não recorrentes."""
    texto_lower = texto.lower()
    encontrados = []
    for palavra in _PALAVRAS_NAO_RECORRENTE:
        if palavra in texto_lower:
            idx = texto_lower.find(palavra)
            trecho = texto[max(0, idx - 20):idx + len(palavra) + 80].strip()
            trecho = re.sub(r"\s+", " ", trecho)
            encontrados.append(trecho[:130])
    return list(dict.fromkeys(encontrados))[:4]


# ─────────────────────────────────────────────────────────────────────────────
# Geração de premissas sugeridas
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_premissas_sugeridas(metricas: dict, tipo_empresa: str) -> dict:
    """
    Converte métricas extraídas em sugestões de premissas para empresas.yaml.
    Apenas campos encontrados são incluídos.
    """
    sugestoes = {}

    if "nim" in metricas:
        sugestoes["nim_alvo"] = metricas["nim"]
    if "inadimplencia" in metricas:
        sugestoes["pcld_pct_alvo"] = round(metricas["inadimplencia"] * 0.35, 4)  # provisão ≈ 35% da inadim
    if "payout" in metricas:
        sugestoes["payout"] = metricas["payout"]
    if "roe_recorrente" in metricas:
        sugestoes["roe_recorrente_observado"] = metricas["roe_recorrente"]
    if "guidance_crescimento" in metricas:
        sugestoes["crescimento_receita_guidance"] = metricas["guidance_crescimento"]
    if "basileia" in metricas:
        sugestoes["basileia_observado"] = metricas["basileia"]

    return sugestoes


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def extrair_dados_ri(
    ticker: str,
    codigo_cvm: str,
    cache_dir: Path,
    max_docs: int = 3,
) -> dict:
    """
    Extrai dados qualitativos dos documentos de RI mais recentes da empresa.

    Args:
        ticker:     Ticker B3 (ex: "BBDC4")
        codigo_cvm: Código CVM da empresa (ex: "906")
        cache_dir:  Diretório de cache do pipeline
        max_docs:   Máximo de documentos a processar

    Returns:
        dict com:
          metricas       — valores extraídos (nim, inadimplencia, roe_recorrente, etc.)
          riscos         — trechos com menção a riscos
          nao_recorrentes— trechos com itens não recorrentes
          premissas_sugeridas — sugestões para empresas.yaml
          documentos_processados — lista de links processados
          timestamp      — data da extração
    """
    logger.info("[parser_ri] Iniciando extração para %s (CVM=%s)", ticker, codigo_cvm)

    resultado = {
        "ticker": ticker,
        "codigo_cvm": codigo_cvm,
        "timestamp": datetime.now().isoformat(),
        "metricas": {},
        "riscos": [],
        "nao_recorrentes": [],
        "premissas_sugeridas": {},
        "documentos_processados": [],
        "erro": None,
    }

    if not codigo_cvm:
        resultado["erro"] = "Código CVM não informado"
        logger.warning("[parser_ri] %s: código CVM ausente", ticker)
        return resultado

    # 1. Buscar documentos recentes na CVM
    links_tentados = []

    # Tenta buscar press releases (IPE) — fatos relevantes e resultados
    docs_ipe = _buscar_documentos_cvm(codigo_cvm, "IPE")
    for doc in docs_ipe[:max_docs]:
        link = doc.get("LINK_DOC") or doc.get("LINK") or ""
        if link and link not in links_tentados:
            links_tentados.append(link)

    # Se não encontrou via catálogo, tenta URL direta dos últimos ITRs
    if not links_tentados:
        ano_atual = datetime.now().year
        for ano in [ano_atual, ano_atual - 1]:
            for trimestre in ["3T", "2T", "1T"]:
                # Padrão comum de URL de release CVM
                url_tentativa = (
                    f"{_CVM_BASE}/IPE/DOC/{codigo_cvm}/"
                    f"IPE_DFP_{codigo_cvm}_{ano}.zip"
                )
                links_tentados.append(url_tentativa)
                if len(links_tentados) >= max_docs:
                    break
            if len(links_tentados) >= max_docs:
                break

    # 2. Processar cada documento
    metricas_acumuladas: dict[str, list[float]] = {}
    riscos_total: list[str] = []
    nao_rec_total: list[str] = []

    for link in links_tentados[:max_docs]:
        if not link.startswith("http"):
            continue
        logger.info("[parser_ri] Processando: %s", link[:80])
        texto = _baixar_texto_documento(link, cache_dir)

        if len(texto) < 200:
            logger.debug("[parser_ri] Documento vazio ou muito curto")
            continue

        resultado["documentos_processados"].append(link)
        metricas_doc = _extrair_metricas(texto)

        for campo, valor in metricas_doc.items():
            metricas_acumuladas.setdefault(campo, []).append(valor)

        riscos_total.extend(_extrair_riscos(texto))
        nao_rec_total.extend(_extrair_nao_recorrentes(texto))

        time.sleep(0.5)  # delay cortês

    # 3. Consolidar métricas (média dos documentos)
    metricas_finais = {
        campo: round(sum(vals) / len(vals), 4)
        for campo, vals in metricas_acumuladas.items()
        if vals
    }

    # Deduplicar riscos e não-recorrentes
    riscos_total = list(dict.fromkeys(riscos_total))[:5]
    nao_rec_total = list(dict.fromkeys(nao_rec_total))[:4]

    # 4. Inferir tipo de empresa para premissas
    tipo_empresa = "bank" if any(
        p in ticker.upper() for p in ["BBDC", "ITUB", "BBAS", "SANB", "BPAC", "BRSR", "ABCB"]
    ) else "general"

    premissas = _gerar_premissas_sugeridas(metricas_finais, tipo_empresa)

    resultado.update({
        "metricas": metricas_finais,
        "riscos": riscos_total,
        "nao_recorrentes": nao_rec_total,
        "premissas_sugeridas": premissas,
    })

    n_docs = len(resultado["documentos_processados"])
    n_met = len(metricas_finais)
    logger.info(
        "[parser_ri] %s — %d doc(s) processado(s), %d métrica(s) extraída(s): %s",
        ticker, n_docs, n_met, list(metricas_finais.keys()),
    )

    return resultado


def resumo_ri(dados: dict) -> str:
    """Gera string de resumo legível dos dados extraídos."""
    linhas = [f"=== RI Parser — {dados['ticker']} ==="]
    m = dados.get("metricas", {})
    if m:
        linhas.append("Métricas extraídas:")
        for k, v in m.items():
            if k not in ("capex", "guidance_lucro"):
                linhas.append(f"  {k}: {v:.1%}")
            else:
                linhas.append(f"  {k}: {v:,.0f}")
    else:
        linhas.append("  Nenhuma métrica extraída")

    if dados.get("riscos"):
        linhas.append("Riscos mencionados:")
        for r in dados["riscos"][:3]:
            linhas.append(f"  — {r}")

    if dados.get("nao_recorrentes"):
        linhas.append("Itens nao recorrentes:")
        for n in dados["nao_recorrentes"][:2]:
            linhas.append(f"  — {n}")

    if dados.get("premissas_sugeridas"):
        linhas.append("Premissas sugeridas para empresas.yaml:")
        for k, v in dados["premissas_sugeridas"].items():
            linhas.append(f"  {k}: {v}")

    return "\n".join(linhas)
