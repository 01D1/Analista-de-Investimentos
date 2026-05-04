"""
report_writer.py — Gerador de tese de investimento em Markdown.

Produz um relatório estruturado combinando:
  - Decisão de intelligence (BUY/HOLD/SELL, score, tese)
  - Tabela de valuation (preço justo, upside, TIR)
  - Indicadores históricos (ROE, NIM, inadimplência, margens)
  - Projeções resumidas
  - Premissas utilizadas
  - Avisos e limitações

Output: outputs/reports/TICKER_NOME_DATA.md
        outputs/reports/TICKER_NOME_DATA_latest.md (atalho sempre atualizado)

Uso:
    from modules.report_writer import gerar_relatorio_tese
    caminho = gerar_relatorio_tese(
        ticker, nome, analise, valuation, ind_hist, dados_empresa, cfg.OUTPUT_DIR
    )
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger("pipeline.report_writer")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de formatação
# ─────────────────────────────────────────────────────────────────────────────

def _pct(v, casas: int = 1) -> str:
    try:
        return f"{float(v):.{casas}%}"
    except (TypeError, ValueError):
        return "—"


def _brl(v, casas: int = 2) -> str:
    try:
        return f"R$ {float(v):,.{casas}f}"
    except (TypeError, ValueError):
        return "—"


def _mm(v) -> str:
    try:
        return f"R$ {float(v):,.0f} MM"
    except (TypeError, ValueError):
        return "—"


def _last(df: pd.DataFrame, row: str, n: int = 3) -> list[tuple]:
    """Retorna [(ano, valor), ...] das últimas N colunas de uma linha."""
    if df is None or df.empty or row not in df.index:
        return []
    serie = pd.to_numeric(df.loc[row], errors="coerce").dropna()
    return [(str(col), float(val)) for col, val in serie.tail(n).items()]


def _icone_rec(rec: str) -> str:
    if rec.startswith("BUY"):
        return "COMPRA"
    if rec == "HOLD":
        return "NEUTRO"
    if rec == "SELL":
        return "VENDA"
    return "EVITAR"


def _barra_score(score: int, largura: int = 20) -> str:
    """Gera barra de progresso textual para o score."""
    preenchido = round(score / 100 * largura)
    return "[" + "█" * preenchido + "░" * (largura - preenchido) + f"] {score}/100"


# ─────────────────────────────────────────────────────────────────────────────
# Seções do relatório
# ─────────────────────────────────────────────────────────────────────────────

def _cabecalho(ticker, nome, analise, valuation, dados_empresa) -> str:
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    rec = analise.get("recomendacao", "—")
    setor = (dados_empresa or {}).get("setor", "—")
    motor = (dados_empresa or {}).get("motor_valuation", "wacc").upper()

    return f"""# Tese de Investimento — {nome} ({ticker})

**Data:** {ts}
**Setor:** {setor}
**Motor de Valuation:** {motor}
**Recomendação:** {_icone_rec(rec)} ({rec})

---
"""


def _resumo_executivo(analise) -> str:
    score = analise.get("score", 0)
    risco = analise.get("risco", "—")
    confianca = analise.get("confianca", "—")
    tese = analise.get("tese", "—")
    barra = _barra_score(score)

    det = analise.get("detalhes", {})
    sv = det.get("score_valuation", 0)
    sq = det.get("score_qualidade", 0)
    pen = det.get("penalidade_risco", 0)

    fatores = det.get("fatores_risco", [])
    fatores_txt = "\n".join(f"- {f}" for f in fatores) if fatores else "- Nenhum identificado"

    return f"""## Resumo Executivo

{tese}

### Score de Investimento

{barra}

| Dimensão | Pontuação |
|---|---|
| Valuation (upside + TIR) | {sv:.0f}/100 × 50% |
| Qualidade Fundamental | {sq:.0f}/100 × 35% |
| Bônus Qualidade de Dados | — × 15% |
| Penalidade de Risco | −{pen:.0f} pts |

**Risco:** {risco}
**Confiança:** {confianca} ({analise.get("motivo_confianca", "")})

### Fatores de Risco Identificados

{fatores_txt}

---
"""


def _tabela_valuation(valuation, mercado) -> str:
    pa  = _brl(mercado.get("preco"))
    pj  = _brl(valuation.get("preco_justo_on"))
    pjpn = _brl(valuation.get("preco_justo_pn"))
    pt  = _brl(valuation.get("preco_teto_on"))
    up  = _pct(valuation.get("upside_on"))
    tir = _pct(valuation.get("tir_on"))
    eq  = _mm(valuation.get("equity_mm"))
    ev  = _mm(valuation.get("ev_mm")) if valuation.get("ev_mm") else "—"
    g   = _pct(valuation.get("g_perpetuidade"), casas=1)
    beta = f"{mercado.get('beta_usar', '—'):.2f}" if mercado.get("beta_usar") else "—"

    return f"""## Valuation

| Métrica | Valor |
|---|---|
| Cotação Atual (ON) | {pa} |
| **Preço Justo ON** | **{pj}** |
| Preço Justo PN | {pjpn} |
| Preço Teto ON | {pt} |
| **Upside ON** | **{up}** |
| **TIR** | **{tir}** |
| Valor do Equity | {eq} |
| Enterprise Value | {ev} |
| G Perpetuidade | {g} |
| Beta Utilizado | {beta} |

---
"""


def _indicadores_historicos(ind_hist: pd.DataFrame, tipo_empresa: str) -> str:
    if ind_hist is None or ind_hist.empty:
        return "## Indicadores Históricos\n\n*Dados não disponíveis.*\n\n---\n"

    if tipo_empresa == "bank":
        campos = [
            ("roe", "ROE", True),
            ("nim", "NIM", True),
            ("inadimplencia", "Inadimplência", True),
            ("basileia", "Basileia", True),
            ("payout", "Payout", True),
        ]
    else:
        campos = [
            ("roe", "ROE", True),
            ("margem_ebitda", "Margem EBITDA", True),
            ("margem_liquida", "Margem Líquida", True),
            ("divida_liquida_ebitda", "Dívida Líq./EBITDA", False),
            ("roic", "ROIC", True),
        ]

    linhas_tabela = []
    for campo, label, is_pct in campos:
        vals = _last(ind_hist, campo, n=4)
        if not vals:
            continue
        cols = " | ".join(
            _pct(v) if is_pct else f"{v:.1f}x" for _, v in vals
        )
        anos = " | ".join(a for a, _ in vals)
        linhas_tabela.append((label, anos, cols))

    if not linhas_tabela:
        return "## Indicadores Históricos\n\n*Nenhum indicador disponível.*\n\n---\n"

    # Cabeçalho da tabela com os anos
    anos_header = linhas_tabela[0][1] if linhas_tabela else ""
    header = f"| Indicador | {anos_header} |"
    sep = "|---|" + "---|" * len(anos_header.split("|"))

    rows = "\n".join(f"| {label} | {cols} |" for label, _, cols in linhas_tabela)

    return f"""## Indicadores Históricos

{header}
{sep}
{rows}

---
"""


def _dre_resumida(dre: pd.DataFrame, tipo_empresa: str) -> str:
    if dre is None or dre.empty:
        return ""

    if tipo_empresa == "bank":
        campos = [
            ("margem_financeira_bruta", "Margem Financeira Bruta"),
            ("resultado_servicos", "Resultado de Serviços"),
            ("lucro_liquido", "Lucro Líquido"),
        ]
    else:
        campos = [
            ("receita_liquida", "Receita Líquida"),
            ("ebitda", "EBITDA"),
            ("ebit", "EBIT"),
            ("lucro_liquido", "Lucro Líquido"),
        ]

    linhas = []
    for campo, label in campos:
        vals = _last(dre, campo, n=4)
        if not vals:
            continue
        cols = " | ".join(f"{v:,.0f}" for _, v in vals)
        anos = " | ".join(a for a, _ in vals)
        linhas.append((label, anos, cols))

    if not linhas:
        return ""

    anos_h = linhas[0][1] if linhas else ""
    header = f"| Linha (R$ MM) | {anos_h} |"
    sep = "|---|" + "---|" * len(anos_h.split("|"))
    rows = "\n".join(f"| {label} | {cols} |" for label, _, cols in linhas)

    return f"""## DRE Resumida (R$ MM)

{header}
{sep}
{rows}

---
"""


def _premissas_utilizadas(dados_empresa, valuation, mercado) -> str:
    tipo = (dados_empresa or {}).get("tipo_empresa", "general")
    prem = (dados_empresa or {}).get("premissas", {})

    g = _pct(valuation.get("g_perpetuidade"))
    beta = f"{mercado.get('beta_usar', '—'):.2f}" if mercado.get("beta_usar") else "—"

    linhas = [
        f"| G Perpetuidade | {g} |",
        f"| Beta Utilizado | {beta} |",
    ]

    if tipo == "bank":
        if prem.get("nim_alvo"):
            linhas.append(f"| NIM Alvo | {_pct(prem['nim_alvo'])} |")
        if prem.get("payout"):
            linhas.append(f"| Payout | {_pct(prem['payout'])} |")
        if prem.get("pcld_pct_alvo"):
            linhas.append(f"| PCLD % Carteira Alvo | {_pct(prem['pcld_pct_alvo'])} |")
    else:
        if prem.get("margem_ebitda_alvo"):
            linhas.append(f"| Margem EBITDA Alvo | {_pct(prem['margem_ebitda_alvo'])} |")
        if prem.get("capex_pct_receita"):
            linhas.append(f"| CAPEX % Receita | {_pct(prem['capex_pct_receita'])} |")

    rows = "\n".join(linhas)

    return f"""## Premissas Utilizadas

| Premissa | Valor |
|---|---|
{rows}

---
"""


def _avisos_limitacoes(avisos: list[str], qualidade: dict) -> str:
    if not avisos and not qualidade.get("warnings") and not qualidade.get("critical"):
        return ""

    linhas = ["## Avisos e Limitações\n"]

    criticos = qualidade.get("critical", [])
    if criticos:
        linhas.append("**Problemas críticos nos dados:**")
        for c in criticos:
            linhas.append(f"- {c}")
        linhas.append("")

    warnings_q = qualidade.get("warnings", [])
    if warnings_q:
        linhas.append("**Alertas de qualidade:**")
        for w in warnings_q:
            linhas.append(f"- {w}")
        linhas.append("")

    if avisos:
        linhas.append("**Avisos de valuation:**")
        for av in avisos:
            linhas.append(f"- {av}")
        linhas.append("")

    linhas.append("---\n")
    return "\n".join(linhas)


def _rodape(ticker) -> str:
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    return (
        f"*Gerado automaticamente pelo Pipeline de Valuation em {ts}.*  \n"
        f"*Uso exclusivamente educacional e analítico. "
        f"Não constitui recomendação de investimento.*\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def gerar_relatorio_tese(
    ticker: str,
    nome: str,
    analise: dict,
    valuation: dict,
    ind_hist: pd.DataFrame,
    dados_empresa: Optional[dict],
    output_dir: Path,
    dre: Optional[pd.DataFrame] = None,
    mercado: Optional[dict] = None,
    avisos: Optional[list[str]] = None,
    qualidade: Optional[dict] = None,
) -> Path:
    """
    Gera relatório de tese de investimento em Markdown.

    Returns:
        Path do arquivo gerado.
    """
    mercado = mercado or {}
    avisos = avisos or []
    qualidade = qualidade or {"score": 100, "warnings": [], "critical": []}
    tipo_empresa = (dados_empresa or {}).get("tipo_empresa", "general")

    # Montar seções
    secoes = [
        _cabecalho(ticker, nome, analise, valuation, dados_empresa),
        _resumo_executivo(analise),
        _tabela_valuation(valuation, mercado),
        _indicadores_historicos(ind_hist, tipo_empresa),
    ]

    dre_section = _dre_resumida(dre, tipo_empresa)
    if dre_section:
        secoes.append(dre_section)

    secoes += [
        _premissas_utilizadas(dados_empresa, valuation, mercado),
        _avisos_limitacoes(avisos, qualidade),
        _rodape(ticker),
    ]

    conteudo = "\n".join(secoes)

    # Salvar
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"Tese_{ticker}_{nome.replace(' ', '_')}_{ts}.md"
    caminho = reports_dir / nome_arquivo
    caminho.write_text(conteudo, encoding="utf-8")

    # Atalho "latest" para automações
    latest = reports_dir / f"Tese_{ticker}_latest.md"
    latest.write_text(conteudo, encoding="utf-8")

    logger.info("[report_writer] %s — relatório gerado: %s", ticker, caminho.name)
    return caminho
