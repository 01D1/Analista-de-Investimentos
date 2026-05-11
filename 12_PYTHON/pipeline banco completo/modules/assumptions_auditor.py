"""
assumptions_auditor.py

Gera uma trilha auditavel das premissas usadas no valuation: valor, fonte,
tipo de premissa e observacoes. Isso separa dado numerico coletado, fallback e
input subjetivo do analista.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AssumptionRecord:
    chave: str
    valor: Any
    fonte: str
    categoria: str
    justificativa: str


def _add(records: list[AssumptionRecord], chave: str, valor: Any, fonte: str, categoria: str, justificativa: str):
    records.append(AssumptionRecord(chave, valor, fonte, categoria, justificativa))


def _classificar_premissa_efetiva(chave: str, valor: Any) -> tuple[str, str, str]:
    key = str(chave or "").lower()
    if key in {"anos_historicos", "anos_projecao", "metodologia_setorial", "motor", "setor", "tipo_acao", "classe_principal"}:
        return "pipeline/config", "metodologia", "Parametro estrutural que define escopo, classe de acao ou motor do modelo."
    if key in {"beta_usado", "g_perpetuidade", "payout", "nim_alvo", "margem_ebitda_alvo", "capex_pct_receita", "ncg_pct_receita", "custo_divida_spread"}:
        return "CLI/empresas.yaml/settings", "premissa_subjetiva", "Premissa economica escolhida pelo analista ou pelo cadastro setorial/empresa."
    if key.endswith("_fonte"):
        return "pipeline", "fonte", "Descricao da origem usada por outra premissa."
    if key.startswith("status"):
        return "quality_gate", "controle_qualidade", "Status de confiabilidade atribuido ao valuation."
    return "run/pipeline", "premissa_efetiva", "Valor efetivamente usado na execucao."


def gerar_relatorio_premissas(
    *,
    ticker: str,
    tipo_empresa: str,
    dados_empresa: dict,
    dados_mercado: dict,
    macro: dict,
    valuation: dict,
    premissas_efetivas: dict,
    output_dir: str | Path,
) -> dict[str, Any]:
    records: list[AssumptionRecord] = []
    premissas_yaml = (dados_empresa or {}).get("premissas", {})

    for chave, valor in sorted((premissas_efetivas or {}).items()):
        fonte, categoria, justificativa = _classificar_premissa_efetiva(chave, valor)
        _add(records, chave, valor, fonte, categoria, justificativa)

    for chave, valor in sorted((premissas_yaml or {}).items()):
        _add(records, chave, valor, "config/empresas.yaml", "input_empresa", "Premissa cadastrada especificamente para a empresa.")

    fonte_mercado = dados_mercado.get("fonte_mercado") or "yfinance/cache ou input CLI"
    _add(records, "cotacao_on", dados_mercado.get("preco"), fonte_mercado, "mercado", "Preco de mercado usado para upside.")
    _add(records, "cotacao_pn", dados_mercado.get("preco_pn"), fonte_mercado, "mercado", "Preco PN usado quando aplicavel.")
    _add(records, "beta_calc", dados_mercado.get("beta_calc"), "serie yfinance/cache", "mercado", "Beta estatistico calculado contra Ibovespa.")
    _add(records, "beta_usar", dados_mercado.get("beta_usar"), "CLI/settings/empresas.yaml", "premissa_subjetiva", "Beta final usado no custo de capital.")

    proj = (macro or {}).get("projecao", {})
    hist = (macro or {}).get("historico", {})
    for serie, valores in sorted(proj.items()):
        _add(records, f"macro_projecao_{serie}", valores, "Focus/BCB/settings/fallback", "macro", "Serie macro projetada usada nas premissas.")
    for serie, valores in sorted(hist.items()):
        _add(records, f"macro_historico_{serie}", valores, "BCB/cache/fallback", "macro", "Serie macro historica usada no modelo.")

    for chave in ["g_perpetuidade", "preco_justo_on", "preco_justo_pn", "tir_on", "tir_pn", "wacc_ultimo", "ke_ultimo"]:
        if chave in valuation:
            _add(records, chave, valuation.get(chave), "valuation_engine", "resultado_calculado", "Resultado derivado do motor de valuation.")

    payload = {
        "ticker": ticker,
        "tipo_empresa": tipo_empresa,
        "timestamp": datetime.now().isoformat(),
        "registros": [asdict(r) for r in records],
        "resumo_categorias": {},
    }
    for rec in records:
        payload["resumo_categorias"][rec.categoria] = payload["resumo_categorias"].get(rec.categoria, 0) + 1
    out_dir = Path(output_dir) / "assumptions"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"premissas_{ticker}.json"
    md_path = out_dir / f"premissas_{ticker}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# Premissas Auditaveis - {ticker}",
        "",
        f"Gerado em: {payload['timestamp']}",
        "",
        "## Resumo por categoria",
    ]
    for categoria, total in sorted(payload["resumo_categorias"].items()):
        lines.append(f"- {categoria}: {total}")
    lines.append("")
    for categoria in sorted({rec.categoria for rec in records}):
        lines.append(f"## {categoria}")
        for rec in [r for r in records if r.categoria == categoria]:
            lines.append(f"- **{rec.chave}** = `{rec.valor}` | fonte: {rec.fonte} | {rec.justificativa}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload
