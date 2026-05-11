"""
metodologias_setoriais.py

Perfis metodologicos para diferenciar a leitura do valuation por setor.
Nao muda premissas automaticamente de forma agressiva; registra qual motor,
drivers, riscos e checks devem ser priorizados para cada tipo de empresa.
"""

from __future__ import annotations


DEFAULT_PROFILE = {
    "metodo": "FCFF/WACC",
    "drivers": ["receita", "margem ebitda", "capex", "capital de giro", "wacc"],
    "checks": ["receita_liquida", "ebit", "fcff", "divida_liquida", "wacc"],
    "riscos_chave": ["execucao", "ciclo economico", "custo de capital"],
}


SECTOR_PROFILES = {
    "bancos": {
        "metodo": "FCFE/Ke",
        "drivers": ["carteira de credito", "nim", "inadimplencia", "payout", "ke"],
        "checks": ["margem_financeira_bruta", "lucro_liquido", "fcfe", "basileia", "roe"],
        "riscos_chave": ["credito", "liquidez", "regulatorio", "capital"],
    },
    "energia": {
        "metodo": "FCFF/WACC regulado",
        "drivers": ["rap", "energia vendida", "capex regulatorio", "wacc", "revisao tarifaria"],
        "checks": ["receita_liquida", "ebitda", "capex", "divida_liquida", "wacc"],
        "riscos_chave": ["regulatorio", "hidrologico", "capex", "alavancagem"],
    },
    "saneamento": {
        "metodo": "FCFF/WACC regulado",
        "drivers": ["tarifa", "base de ativos", "capex", "perdas", "wacc"],
        "checks": ["receita_liquida", "ebitda", "capex", "divida_liquida", "wacc"],
        "riscos_chave": ["regulatorio", "execucao de capex", "politico", "alavancagem"],
    },
    "petroleo": {
        "metodo": "FCFF/WACC cíclico",
        "drivers": ["brent", "cambio", "producao", "lifting cost", "capex"],
        "checks": ["receita_liquida", "ebitda", "capex", "divida_liquida", "fcff"],
        "riscos_chave": ["commodity", "reservas", "capex", "licencas"],
    },
    "varejo": {
        "metodo": "FCFF/WACC operacional",
        "drivers": ["vendas mesmas lojas", "margem bruta", "sg&a", "estoques", "capital de giro"],
        "checks": ["receita_liquida", "margem_bruta", "ebit", "ncg", "fcff"],
        "riscos_chave": ["demanda", "estoques", "credito ao consumidor", "competicao"],
    },
    "saude": {
        "metodo": "FCFF/WACC defensivo",
        "drivers": ["ticket medio", "ocupacao", "sinistralidade", "margem", "capex"],
        "checks": ["receita_liquida", "ebitda", "capex", "divida_liquida", "fcff"],
        "riscos_chave": ["regulatorio", "judicial", "sinistralidade", "integracao"],
    },
    "industrial": {
        "metodo": "FCFF/WACC industrial",
        "drivers": ["volume", "preco", "mix", "margem ebitda", "capex"],
        "checks": ["receita_liquida", "ebitda", "capex", "ncg", "fcff"],
        "riscos_chave": ["ciclo", "cambio", "insumos", "execucao"],
    },
    "locadoras": {
        "metodo": "FCFF/WACC intensivo em capital",
        "drivers": ["frota", "spread de compra/venda", "utilizacao", "custo da divida", "capex"],
        "checks": ["receita_liquida", "ebitda", "capex", "divida_liquida", "wacc"],
        "riscos_chave": ["valor residual", "alavancagem", "juros", "demanda"],
    },
}


def get_metodologia_setorial(setor: str | None, tipo_empresa: str | None = None) -> dict:
    if tipo_empresa == "bank":
        return dict(SECTOR_PROFILES["bancos"])
    key = str(setor or "").strip().lower()
    profile = SECTOR_PROFILES.get(key, DEFAULT_PROFILE)
    return dict(profile)
