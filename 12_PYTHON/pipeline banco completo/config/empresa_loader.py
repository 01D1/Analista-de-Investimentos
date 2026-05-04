"""
Loader centralizado de empresas e setores.
Carrega config/empresas.yaml e fornece:
  - Dados cadastrais da empresa (nome, código CVM, ações, etc.)
  - Premissas de projeção (merge: empresa > setor > global)
  - Tipo de empresa (bank/general) → define qual pipeline usar
  - Mapeamento de contas correto (bancário vs. IFRS geral)

Substitui o antigo config/bancos.py como fonte única de verdade.
Mantém retrocompatibilidade: get_banco() continua funcionando.
"""

import logging
from pathlib import Path
from typing import Optional
import copy

import yaml

logger = logging.getLogger("pipeline.empresa_loader")

# Caminho do YAML
_CONFIG_DIR = Path(__file__).parent
_YAML_PATH  = _CONFIG_DIR / "empresas.yaml"

# Cache em memória (carregado uma vez)
_cache: dict = {}


def _carregar_yaml() -> dict:
    """Carrega e valida o YAML de empresas."""
    global _cache
    if _cache:
        return _cache

    if not _YAML_PATH.exists():
        logger.warning(f"empresas.yaml não encontrado em {_YAML_PATH}")
        return {}

    with open(_YAML_PATH, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    _cache = dados or {}
    return _cache


def _resolver_alias(ticker: str, empresas: dict) -> Optional[str]:
    """
    Se o ticker é um alias, retorna o ticker principal.
    Ex: BBDC3 → BBDC4, ITUB3 → ITUB4
    Busca é case-insensitive.
    """
    t = ticker.upper().strip()

    # Lookup direto (case-insensitive nas chaves)
    chave_map = {k.upper(): k for k in empresas}
    if t in chave_map:
        return chave_map[t]

    # Procurar nos aliases de cada empresa
    for ticker_principal, dados in empresas.items():
        aliases = dados.get("aliases", [])
        if t in [a.upper() for a in aliases]:
            return ticker_principal

    return None


def _merge_premissas(defaults: dict, setor_premissas: dict,
                     empresa_premissas: dict) -> dict:
    """
    Merge hierárquico: empresa > setor > global.
    Valores da empresa sobrescrevem os do setor, que sobrescrevem os globais.
    """
    resultado = copy.deepcopy(defaults)

    # Merge setor
    for k, v in setor_premissas.items():
        if isinstance(v, dict) and isinstance(resultado.get(k), dict):
            resultado[k].update(v)
        else:
            resultado[k] = v

    # Merge empresa (prevalece)
    for k, v in empresa_premissas.items():
        if isinstance(v, dict) and isinstance(resultado.get(k), dict):
            resultado[k].update(v)
        else:
            resultado[k] = v

    return resultado


# ═══════════════════════════════════════════════════════════════════════════════
# API pública
# ═══════════════════════════════════════════════════════════════════════════════

def get_empresa(ticker: str) -> Optional[dict]:
    """
    Retorna os dados completos de uma empresa, com premissas já mescladas.

    Returns:
        dict com:
            - nome, setor, codigo_cvm, ticker_on, ticker_pn, tipo_acao, etc.
            - tipo_empresa: "bank" ou "general"
            - motor_projecao: "fcfe" ou "fcff"
            - motor_valuation: "ke" ou "wacc"
            - premissas: dict mesclado (empresa > setor > global)
            - mapa_override: dict (se definido, para bancos com estrutura diferente)
        ou None se não encontrado
    """
    dados = _carregar_yaml()
    if not dados:
        return None

    empresas = dados.get("empresas", {})
    setores  = dados.get("setores", {})
    defaults = dados.get("defaults", {})

    # Resolver alias
    ticker_principal = _resolver_alias(ticker, empresas)
    if not ticker_principal:
        logger.info(f"Ticker {ticker} não encontrado no empresas.yaml")
        return None

    empresa_raw = empresas[ticker_principal]
    setor_nome  = empresa_raw.get("setor", "")
    setor_cfg   = setores.get(setor_nome, {})

    # Merge premissas
    premissas = _merge_premissas(
        defaults,
        setor_cfg.get("premissas", {}),
        empresa_raw.get("premissas", {}),
    )

    # Montar resultado
    resultado = {
        # Cadastro
        "ticker":        ticker_principal,
        "nome":          empresa_raw.get("nome", ticker_principal),
        "setor":         setor_nome,
        "codigo_cvm":    empresa_raw.get("codigo_cvm"),
        "ticker_on":     empresa_raw.get("ticker_on"),
        "ticker_pn":     empresa_raw.get("ticker_pn"),
        "acoes_on_mil":  empresa_raw.get("acoes_on_mil", 0),
        "acoes_pn_mil":  empresa_raw.get("acoes_pn_mil", 0),
        "tipo_acao":     empresa_raw.get("tipo_acao", "ON_ONLY"),
        "relacao_pn_on": empresa_raw.get("relacao_pn_on", 1.0),
        "aliases":       empresa_raw.get("aliases", []),

        # Pipeline config (vem do setor)
        "tipo_empresa":     setor_cfg.get("tipo_empresa", "general"),
        "motor_projecao":   setor_cfg.get("motor_projecao", "fcff"),
        "motor_valuation":  setor_cfg.get("motor_valuation", "wacc"),
        "template":         setor_cfg.get("template"),

        # Premissas mescladas
        "premissas":     premissas,

        # Override de mapeamento de contas (para bancos com estrutura diferente)
        "mapa_override": empresa_raw.get("mapa_override", {}),

        # Divisor CVM (override por empresa quando ESCALA_MOEDA != MIL)
        "divisor_cvm":   empresa_raw.get("divisor_cvm", None),
    }

    return resultado


def get_setor(nome_setor: str) -> Optional[dict]:
    """Retorna a configuração de um setor."""
    dados = _carregar_yaml()
    return dados.get("setores", {}).get(nome_setor)


def listar_tickers(setor: str = None, ativos: bool = True) -> list[str]:
    """
    Lista tickers cadastrados.

    Args:
        setor: filtrar por setor (None = todos)
        ativos: se True, ignora empresas marcadas como ativo=false

    Returns:
        Lista de tickers principais (sem aliases)
    """
    dados = _carregar_yaml()
    empresas = dados.get("empresas", {})

    resultado = []
    for ticker, cfg in empresas.items():
        if setor and cfg.get("setor") != setor:
            continue
        if ativos and cfg.get("ativo") is False:
            continue
        resultado.append(ticker)

    return resultado


def listar_setores() -> list[str]:
    """Lista todos os setores cadastrados."""
    dados = _carregar_yaml()
    return list(dados.get("setores", {}).keys())


def get_defaults() -> dict:
    """Retorna as premissas globais default."""
    dados = _carregar_yaml()
    return dados.get("defaults", {})


# ═══════════════════════════════════════════════════════════════════════════════
# Retrocompatibilidade com config/bancos.py
# ═══════════════════════════════════════════════════════════════════════════════

def get_banco(ticker: str) -> Optional[dict]:
    """
    Retrocompatível com bancos.py: retorna dados do banco no formato antigo.
    Usado pelo main.py e projecoes.py até a refatoração completa.
    """
    empresa = get_empresa(ticker)
    if empresa is None:
        return None

    if empresa["tipo_empresa"] != "bank":
        return None  # não é banco

    premissas = empresa["premissas"]

    # Converter para o formato que main.py/projecoes.py esperam
    resultado = {
        "nome":             empresa["nome"],
        "codigo_cvm":       empresa["codigo_cvm"],
        "ticker_on":        empresa["ticker_on"],
        "ticker_pn":        empresa.get("ticker_pn"),
        "acoes_on_mil":     empresa["acoes_on_mil"],
        "acoes_pn_mil":     empresa["acoes_pn_mil"],
        "tipo":             empresa["tipo_acao"],
        "relacao_pn_on":    empresa["relacao_pn_on"],

        # Premissas no formato antigo
        "nim_alvo":             premissas.get("nim_alvo", 0.055),
        "nim_maximo":           premissas.get("nim_maximo", float("inf")),
        "pcld_pct_alvo":        premissas.get("pcld_pct_alvo", 0.035),
        "payout_projetado":     premissas.get("payout", 0.45),
        "g_perpetuidade":       premissas.get("g_perpetuidade", 0.055),
        "beta_utilizado":       premissas.get("beta", 0.90),

        # Crescimentos (pode ser dict por ano ou valor default)
        "crescimento_credito":  premissas.get("crescimento_receita", {}),
        "crescimento_servicos": premissas.get("crescimento_servicos", {}),

        # Override de mapeamento
        "mapa_override":        empresa.get("mapa_override", {}),
    }

    return resultado


def invalidar_cache():
    """Força recarga do YAML na próxima chamada."""
    global _cache
    _cache = {}
