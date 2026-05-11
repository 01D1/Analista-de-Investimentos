"""
main.py — Ponto de entrada do Pipeline de Valuation
====================================================

Suporta QUALQUER empresa cadastrada em config/empresas.yaml.
Detecta automaticamente o tipo (banco vs. não-financeira) e aplica
o pipeline correto: FCFE/Ke para bancos, FCFF/WACC para as demais.

Uso individual:
    python main.py --ticker BBAS3                   # banco
    python main.py --ticker WEGE3                   # industrial
    python main.py --ticker SUZB3                   # papel e celulose
    python main.py --ticker BBDC4 --sem-cvm         # pula download CVM
    python main.py --ticker SANB11 --cotacao-on 25.50 --cotacao-pn 28.00

Modo batch (múltiplas empresas de uma vez):
    python main.py --batch BBDC4 BBAS3 WEGE3 SUZB3
    python main.py --batch-setor bancos             # todos de um setor
    python main.py --batch-setor energia industrial  # múltiplos setores

Exemplo completo:
    python main.py \\
        --ticker BBDC4 \\
        --nome Bradesco \\
        --cotacao-on 12.55 \\
        --cotacao-pn 14.01 \\
        --acoes-on 5294213 \\
        --acoes-pn 5279802
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Adicionar o diretório raiz ao path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import settings as cfg
from config.empresa_loader import get_empresa, get_banco, listar_tickers
from modules._helpers import setup_logging

logger = None  # será inicializado após configurar logging


def parse_args():
    p = argparse.ArgumentParser(
        description="Pipeline de Valuation — suporta bancos e empresas não-financeiras",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Empresa (individual)
    p.add_argument("--ticker", default=cfg.TICKER_B3, help=f"Ticker B3 (padrão: {cfg.TICKER_B3})")
    p.add_argument("--nome", default=None, help=f"Nome da empresa (padrão: detectado pelo ticker)")
    p.add_argument(
        "--codigo-cvm",
        default=None,
        type=str,
        help="Código CVM (será buscado automaticamente se omitido)",
    )

    # Modo batch
    p.add_argument(
        "--batch",
        default=None,
        nargs="+",
        metavar="TICKER",
        help="Processa múltiplos tickers em sequência (ex: BBDC4 WEGE3 SUZB3)",
    )
    p.add_argument(
        "--batch-setor",
        default=None,
        nargs="+",
        metavar="SETOR",
        help="Processa todos os tickers de um ou mais setores (ex: bancos energia)",
    )
    p.add_argument(
        "--auditar-dados",
        action="store_true",
        help="Audita completude CVM/B3 sem rodar valuation nem escrever Excel",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help=(
            "Com --auditar-dados, audita todos os tickers cadastrados; "
            "sem --auditar-dados, roda valuation para todos os tickers cadastrados"
        ),
    )
    p.add_argument(
        "--audit-excel",
        default=None,
        help="Caminho de Excel final para comparar com os DataFrames normalizados",
    )
    p.add_argument(
        "--sem-itr-audit",
        action="store_true",
        help="Com --auditar-dados, pula checagem ITR para acelerar a auditoria",
    )
    p.add_argument(
        "--sem-qualitativo",
        action="store_true",
        help="Pula o motor qualitativo integrado ao valuation",
    )
    p.add_argument(
        "--qualitativo-only",
        action="store_true",
        help="Gera apenas a analise qualitativa do ticker, sem rodar valuation numerico",
    )
    p.add_argument(
        "--qualitativo-cvm",
        action="store_true",
        help="Mantido por compatibilidade; o motor qualitativo ja busca CVM/IPE automaticamente quando possivel",
    )
    p.add_argument(
        "--sem-ri-crawler",
        action="store_true",
        help="Pula crawler configuravel de sites de RI no motor qualitativo",
    )
    p.add_argument(
        "--ri-url",
        action="append",
        default=None,
        help="URL inicial de RI para crawler qualitativo. Pode repetir para mais de uma fonte.",
    )
    p.add_argument(
        "--ri-depth",
        default=1,
        type=int,
        help="Profundidade do crawler de RI a partir da URL inicial (padrao: 1)",
    )
    p.add_argument(
        "--ri-max-docs",
        default=25,
        type=int,
        help="Numero maximo de documentos salvos pelo crawler de RI por empresa",
    )

    # Cotações
    p.add_argument("--cotacao-on", default=0.0, type=float, help="Cotação atual da ação ON (R$)")
    p.add_argument("--cotacao-pn", default=0.0, type=float, help="Cotação atual da ação PN (R$)")

    # Ações
    p.add_argument(
        "--acoes-on",
        default=0.0,
        type=float,
        help="Número de ações ON emitidas (ex-treasury, em mil)",
    )
    p.add_argument(
        "--acoes-pn",
        default=0.0,
        type=float,
        help="Número de ações PN emitidas (ex-treasury, em mil)",
    )

    # Períodos
    p.add_argument(
        "--anos", default=None, nargs="+", type=int, help="Anos históricos (padrão: 2019-2024)"
    )

    # Premissas
    p.add_argument(
        "--beta",
        default=cfg.BETA_UTILIZADO,
        type=float,
        help=f"Beta arbitrado (padrão: {cfg.BETA_UTILIZADO})",
    )
    p.add_argument(
        "--g",
        default=cfg.G_PERPETUIDADE,
        type=float,
        help=f"Taxa de crescimento na perpetuidade (padrao: {cfg.G_PERPETUIDADE * 100:.1f}%%)",
    )

    # Controles
    p.add_argument(
        "--sem-cvm", action="store_true", help="Pular download da CVM (usa apenas mercado + macro)"
    )
    p.add_argument("--sem-cache", action="store_true", help="Ignorar cache e re-baixar tudo")
    p.add_argument("--template", default=None, help="Caminho do template Excel")
    p.add_argument(
        "--output", default=None, help="Caminho do arquivo de saída (ignorado no modo batch)"
    )
    p.add_argument(
        "--snapshot-excel",
        action="store_true",
        help="Gera uma copia datada do valuation em vez de atualizar o arquivo canonico do ticker",
    )
    p.add_argument("--debug", action="store_true", help="Ativar log de debug")

    return p.parse_args()


def _nome_arquivo_seguro(valor: str) -> str:
    """Remove caracteres invalidos do Windows para nome de arquivo."""
    texto = str(valor or "").strip()
    for ch in '<>:"/\\|?*':
        texto = texto.replace(ch, "_")
    return texto.strip(" .") or "Empresa"


def _caminho_valuation_canonico(ticker: str) -> Path:
    """Arquivo vivo do valuation: uma pasta de trabalho por ticker."""
    ticker_safe = _nome_arquivo_seguro(ticker.upper())
    return cfg.OUTPUT_DIR / "valuations" / ticker_safe / f"Valuation_{ticker_safe}.xlsx"


def _caminho_valuation_snapshot(ticker: str, nome: str) -> Path:
    """Copia datada opcional para arquivamento manual."""
    ticker_safe = _nome_arquivo_seguro(ticker.upper())
    nome_safe = _nome_arquivo_seguro(nome)
    data = datetime.now().strftime("%Y%m%d")
    return cfg.OUTPUT_DIR / "valuations" / ticker_safe / f"Valuation_{ticker_safe}_{nome_safe}_{data}.xlsx"


def _coletar_ri_urls(dados_empresa: dict | None, args) -> list[str]:
    """Coleta fontes de RI cadastradas na empresa e/ou passadas no CLI."""
    dados_empresa = dados_empresa or {}
    urls: list[str] = []

    for key in ("ri_url", "url_ri", "site_ri"):
        value = dados_empresa.get(key)
        if value:
            urls.append(str(value))

    for key in ("ri_urls", "fontes_ri"):
        value = dados_empresa.get(key)
        if isinstance(value, (list, tuple, set)):
            urls.extend(str(item) for item in value if item)
        elif value:
            urls.append(str(value))

    urls.extend(str(item) for item in (getattr(args, "ri_url", None) or []) if item)

    cleaned = []
    for url in urls:
        url = str(url or "").strip()
        if url and url not in cleaned:
            cleaned.append(url)
    return cleaned


def _carregar_market_overrides() -> dict:
    """Carrega overrides manuais de mercado, se existirem."""
    path = ROOT / "config" / "market_overrides.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
        return dados.get("overrides", {}) or {}
    except Exception as exc:
        if logger:
            logger.warning("Nao foi possivel carregar market_overrides.yaml: %s", exc)
        return {}


def _market_override_for(ticker: str, dados_empresa: dict | None) -> dict:
    """Retorna override de cotacao/base acionaria para o ticker."""
    dados_empresa = dados_empresa or {}
    candidatos = [ticker.upper(), str(dados_empresa.get("ticker") or "").upper()]
    candidatos.extend(str(a).upper() for a in dados_empresa.get("aliases", []) or [])

    override = {}
    for key in ("mercado_manual", "market_overrides"):
        valor = dados_empresa.get(key)
        if isinstance(valor, dict):
            override.update(valor)

    externos = _carregar_market_overrides()
    for cand in candidatos:
        if cand and isinstance(externos.get(cand), dict):
            override.update(externos[cand])
            break
    return override


def _float_positivo(valor) -> float:
    try:
        numero = float(valor)
        return numero if numero > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def _aplicar_market_override(
    *,
    ticker: str,
    dados_empresa: dict | None,
    cotacao_on: float,
    cotacao_pn: float,
    acoes_on: float,
    acoes_pn: float,
) -> tuple[float, float, float, float, dict]:
    """Preenche lacunas de mercado com dados manuais auditaveis."""
    override = _market_override_for(ticker, dados_empresa)
    if not override:
        return cotacao_on, cotacao_pn, acoes_on, acoes_pn, {}

    force = bool(override.get("forcar", False))
    aplicados = {
        "fonte": override.get("fonte") or "market_overrides.yaml/empresas.yaml",
        "data": override.get("data"),
        "forcar": force,
        "campos": [],
    }

    def maybe(current, *keys):
        for key in keys:
            val = _float_positivo(override.get(key))
            if val and (force or not current):
                aplicados["campos"].append(key)
                return val
        return current

    cotacao_on = maybe(cotacao_on, "cotacao_on", "preco_on", "preco")
    cotacao_pn = maybe(cotacao_pn, "cotacao_pn", "preco_pn")
    acoes_on = maybe(acoes_on, "acoes_on_mil", "acoes_total_mil", "acoes_on")
    acoes_pn = maybe(acoes_pn, "acoes_pn_mil", "acoes_pn")

    if aplicados["campos"] and logger:
        logger.warning(
            "  Mercado manual aplicado para %s (%s): %s",
            ticker,
            aplicados["fonte"],
            ", ".join(aplicados["campos"]),
        )
    return cotacao_on, cotacao_pn, acoes_on, acoes_pn, aplicados if aplicados["campos"] else {}


def _classe_principal_acao(ticker: str, dados_acao: dict | None) -> str:
    dados_acao = dados_acao or {}
    ticker_up = ticker.upper()
    tipo_acao = str(dados_acao.get("tipo_acao") or "").upper()
    ticker_pn = str(dados_acao.get("ticker_pn") or "").upper()
    ticker_on = str(dados_acao.get("ticker_on") or "").upper()
    if tipo_acao == "UNITS":
        return "UNIT"
    if ticker_pn and ticker_up == ticker_pn:
        return "PN"
    if ticker_on and ticker_up == ticker_on:
        return "ON"
    if ticker_up.endswith("4") and tipo_acao == "ON_PN":
        return "PN"
    return "ON"


def _enriquecer_valuation_classe_acao(
    valuation: dict,
    *,
    ticker: str,
    dados_acao: dict | None,
    cotacao_on: float,
    cotacao_pn: float,
    acoes_on: float,
    acoes_pn: float,
) -> list[str]:
    """Adiciona campos explicitos para ON/PN/UNIT sem quebrar chaves antigas."""
    dados_acao = dados_acao or {}
    tipo_acao = str(dados_acao.get("tipo_acao") or "ON_ONLY").upper()
    classe = _classe_principal_acao(ticker, dados_acao)
    relacao = valuation.get("relacao_pn_on") or dados_acao.get("relacao_pn_on") or 1.0
    avisos: list[str] = []

    if classe == "PN":
        preco = valuation.get("preco_justo_pn")
        upside = valuation.get("upside_pn")
        tir = valuation.get("tir_pn")
        cotacao = cotacao_pn or cotacao_on
    elif classe == "UNIT":
        preco = valuation.get("preco_justo_on")
        upside = valuation.get("upside_on")
        tir = valuation.get("tir_on")
        cotacao = cotacao_on
        valuation["preco_justo_unit"] = preco
        valuation["cotacao_unit"] = cotacao
        valuation["upside_unit"] = upside
        valuation["tir_unit"] = tir
        valuation["acoes_units_mil"] = acoes_on or acoes_pn
        if acoes_pn:
            avisos.append("Ticker UNIT com acoes_pn_mil preenchido; revisar se a base representa units ou classes subjacentes.")
    else:
        preco = valuation.get("preco_justo_on")
        upside = valuation.get("upside_on")
        tir = valuation.get("tir_on")
        cotacao = cotacao_on

    valuation.update(
        {
            "tipo_acao": tipo_acao,
            "classe_principal": classe,
            "ticker_principal": ticker.upper(),
            "preco_justo_principal": preco,
            "cotacao_principal": cotacao,
            "upside_principal": upside,
            "tir_principal": tir,
            "acoes_on_mil": valuation.get("acoes_on_mil", acoes_on),
            "acoes_pn_mil": valuation.get("acoes_pn_mil", acoes_pn),
            "relacao_pn_on": relacao,
            "possui_pn": bool(tipo_acao == "ON_PN" and acoes_pn),
            "possui_unit": classe == "UNIT",
        }
    )
    return avisos


def _verificar_excel_livre(caminho: Path) -> bool:
    """Falha cedo se o arquivo canonico estiver aberto/bloqueado."""
    caminho = Path(caminho)
    if not caminho.exists():
        return True
    try:
        with open(caminho, "r+b"):
            return True
    except PermissionError:
        logger.error(
            "Arquivo Excel bloqueado: %s\n"
            "Feche a planilha no Excel e aguarde o OneDrive terminar a sincronizacao. "
            "Depois rode o comando novamente.",
            caminho,
        )
        return False
    except OSError as exc:
        logger.error("Nao foi possivel acessar o Excel %s: %s", caminho, exc)
        return False


def _localizar_template(
    template_arg,
    ticker: str = None,
    setor: str = None,
    tipo_empresa: str = "general",
    caminho_incremental: Path | None = None,
) -> Optional[Path]:
    """
    Localiza a base Excel a ser atualizada.

    Ordem de busca:
      1. Argumento explícito (--template)
      2. Arquivo canônico já existente do ticker, para atualização incremental
      3. Output antigo do mesmo ticker, somente para migrar bancos

    Para empresas não-financeiras sem template explícito, retorna None e o
    EscritorExcelGeral cria/atualiza o arquivo canônico com o layout interno.
    """
    # ── 1. Argumento explícito ───────────────────────────────────────────
    if template_arg:
        p = Path(template_arg)
        if p.exists():
            return p
        for base in [ROOT.parent, ROOT, ROOT.parent.parent, Path.home() / "Downloads"]:
            candidato = base / template_arg
            if candidato.exists():
                return candidato

    # ── 2. Arquivo canônico já existente ─────────────────────────────────
    # Para bancos, o escritor ainda precisa de uma base de layout. Usar o
    # próprio arquivo canônico preserva ajustes manuais/branding entre rodadas.
    if tipo_empresa == "bank" and caminho_incremental and Path(caminho_incremental).exists():
        if logger:
            logger.info(f"  Atualizando valuation existente: {Path(caminho_incremental).name}")
        return Path(caminho_incremental)

    # ── 3. Migração bancária ─────────────────────────────────────────────
    if tipo_empresa == "bank":
        # Usado uma vez para alimentar o novo arquivo canônico.
        output_dir = cfg.OUTPUT_DIR
        if output_dir.exists() and ticker:
            candidatos_output = sorted(
                output_dir.glob(f"Valuation_{ticker.upper()}_*.xlsx"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidatos_output:
                if logger:
                    logger.warning(
                        f"  Migrando output anterior para arquivo canonico: "
                        f"{candidatos_output[0].name}"
                )
                return candidatos_output[0]

        # Fallback interno: se ainda nao existe arquivo canonico para este banco,
        # usa uma planilha bancaria canonica ja criada como base de layout.
        # O escritor sobrescreve dados, premissas e identidade da empresa.
        candidatos_base = []
        for ticker_base in ["BBDC4", "BBAS3", "ITUB4", "SANB11", "BPAC11"]:
            base = cfg.OUTPUT_DIR / "valuations" / ticker_base / f"Valuation_{ticker_base}.xlsx"
            if base.exists() and (not caminho_incremental or base.resolve() != Path(caminho_incremental).resolve()):
                candidatos_base.append(base)
        if candidatos_base:
            if logger:
                logger.info(
                    f"  Usando base bancaria interna: {candidatos_base[0].name} "
                    f"para iniciar {ticker}"
                )
            return candidatos_base[0]

        raise FileNotFoundError(
            f"Base bancária não encontrada para {ticker}.\n"
            f"  Rode uma vez com --template apontando para sua base bancária própria\n"
            f"  ou coloque uma base inicial em {ROOT.parent}."
        )

    # Não-financeira sem template próprio → retorna None (criar do zero)
    if logger:
        logger.info(f"  Usando layout interno para {ticker}")
    return None


def _validar_dados(dre_hist, bp_hist, projecoes, valuation) -> list[str]:
    """
    Valida os dados antes de escrever no Excel.
    Retorna lista de avisos (não bloqueia a execução).
    """
    avisos = []

    # DRE histórica
    if dre_hist.empty:
        avisos.append("DRE histórica vazia — planilha terá apenas projeções")
    elif "lucro_liquido" in dre_hist.index:
        anos_com_zero = [
            a for a in dre_hist.columns if float(dre_hist.loc["lucro_liquido", a] or 0) == 0
        ]
        if anos_com_zero:
            avisos.append(f"Lucro Líquido = 0 para os anos: {anos_com_zero}")

    # Projeções (FCFE para bancos, FCFF para não-financeiras)
    fcf = projecoes.get("fcfe", projecoes.get("fcff", {}))
    fcf_label = "FCFE" if "fcfe" in projecoes else "FCFF"
    if not fcf:
        avisos.append(f"{fcf_label} projetado vazio — valuation será zero")
    elif all(v == 0 for v in fcf.values()):
        avisos.append(f"{fcf_label} projetado é zero em todos os anos — verificar dados históricos")

    # Valuation
    equity = valuation.get("equity_mm", 0)
    if equity <= 0:
        avisos.append(f"Valor do Equity negativo ou zero: R$ {equity:,.0f} MM")

    preco_on = valuation.get("preco_justo_on", 0)
    if preco_on <= 0:
        avisos.append("Preço Justo ON inválido (≤ 0)")

    return avisos


def _hash_premissas(premissas: dict) -> str:
    """Gera hash estável das premissas efetivas usadas no run."""
    payload = json.dumps(premissas, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _escrever_run_summary(
    *,
    ticker: str,
    nome: str,
    tipo_empresa: str,
    anos_hist: list[int],
    anos_proj: list[int],
    args,
    qualidade: dict,
    avisos: list[str],
    dados_mercado: dict,
    macro: dict,
    valuation: dict,
    premissas_efetivas: dict,
    caminho_arquivo: str,
    analise: dict = None,
    qualitativo: dict = None,
    post_excel_quality: dict = None,
    premissas_audit: dict = None,
) -> Path:
    """Persiste resumo estruturado da execução para auditoria e automação."""
    ts = datetime.now()
    summary_dir = cfg.OUTPUT_DIR / "run_summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)

    mercado_disponivel = bool(dados_mercado.get("preco", 0) and dados_mercado.get("acoes_total", 0))
    macro_hist = (macro or {}).get("historico", {})
    macro_disponivel = any(bool(v) for v in macro_hist.values()) if isinstance(macro_hist, dict) else False

    summary = {
        "run_id": f"{ticker}_{ts.strftime('%Y%m%d_%H%M%S')}",
        "timestamp": ts.isoformat(),
        "ticker": ticker,
        "nome": nome,
        "tipo_empresa": tipo_empresa,
        "modo_execucao": {
            "sem_cvm": bool(args.sem_cvm),
            "sem_cache": bool(args.sem_cache),
            "debug": bool(args.debug),
            "batch": bool(args.batch or getattr(args, "batch_setor", None)),
        },
        "periodos": {
            "anos_historicos": anos_hist,
            "anos_projecao": anos_proj,
        },
        "qualidade": qualidade,
        "avisos_validacao": avisos,
        "fontes_dados": {
            "mercado": {"disponivel": mercado_disponivel},
            "macro": {"disponivel": macro_disponivel},
            "cvm": {"habilitado": not args.sem_cvm},
        },
        "premissas": {
            "hash": _hash_premissas(premissas_efetivas),
            "valores": premissas_efetivas,
        },
        "resultado_valuation": {
            "equity_mm": valuation.get("equity_mm"),
            "preco_justo_on": valuation.get("preco_justo_on"),
            "preco_justo_pn": valuation.get("preco_justo_pn"),
            "upside_on": valuation.get("upside_on"),
            "upside_pn": valuation.get("upside_pn"),
            "tir_on": valuation.get("tir_on"),
            "tir_pn": valuation.get("tir_pn"),
            "g_perpetuidade": valuation.get("g_perpetuidade"),
        },
        "output_excel": caminho_arquivo,
        "intelligence": analise,
        "qualitativo": qualitativo,
        "post_excel_quality": post_excel_quality,
        "premissas_audit": premissas_audit,
    }

    summary_path = summary_dir / f"run_summary_{ticker}_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Atalho para a última execução (útil para automações simples).
    latest_path = summary_dir / "run_summary_latest.json"
    latest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Índice histórico resumido para consultas rápidas.
    index_path = summary_dir / "run_index.json"
    if index_path.exists():
        try:
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            index_payload = {"runs": []}
    else:
        index_payload = {"runs": []}

    run_stub = {
        "run_id": summary["run_id"],
        "timestamp": summary["timestamp"],
        "ticker": summary["ticker"],
        "nome": summary["nome"],
        "tipo_empresa": summary["tipo_empresa"],
        "score_qualidade": summary["qualidade"]["score"],
        "critical_count": len(summary["qualidade"]["critical"]),
        "warning_count": len(summary["qualidade"]["warnings"]),
        "equity_mm": summary["resultado_valuation"]["equity_mm"],
        "preco_justo_on": summary["resultado_valuation"]["preco_justo_on"],
        "upside_on": summary["resultado_valuation"]["upside_on"],
        "output_excel": summary["output_excel"],
        "summary_file": summary_path.name,
    }
    runs = index_payload.get("runs", [])
    runs.append(run_stub)
    # Mantém histórico limitado para evitar crescimento indefinido.
    index_payload["runs"] = runs[-1000:]
    index_payload["updated_at"] = ts.isoformat()
    index_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return summary_path


def run_single(args, ticker: str, nome: str, codigo_cvm_override: str = None) -> dict:
    """
    Executa o pipeline para uma única empresa.
    Detecta automaticamente o tipo (banco vs. geral) e aplica o fluxo correto.

    Returns:
        dict com {caminho_arquivo, valuation, avisos} ou None em caso de erro grave
    """
    import pandas as pd

    # ── Carregar dados da empresa via YAML (fonte de verdade) ──────────
    dados_empresa = get_empresa(ticker)

    if not dados_empresa:
        # Listar tickers parecidos para sugerir correção
        from config.empresa_loader import listar_tickers as _lt

        todos = _lt()
        parecidos = [t for t in todos if ticker.upper()[:3] in t.upper()]
        sugestao = f" Você quis dizer: {', '.join(parecidos)}?" if parecidos else ""
        logger.error("=" * 70)
        logger.error(f"ERRO: Ticker '{ticker}' não encontrado no empresas.yaml.{sugestao}")
        logger.error(f"Para cadastrar, adicione a entrada em config/empresas.yaml")
        logger.error("=" * 70)
        return None

    tipo_empresa = dados_empresa.get("tipo_empresa", "general")
    ticker = dados_empresa["ticker"]  # usar o ticker canônico (case correto)
    nome = nome or dados_empresa["nome"]
    from config.metodologias_setoriais import get_metodologia_setorial

    metodologia_setorial = get_metodologia_setorial(
        dados_empresa.get("setor"), tipo_empresa
    )
    logger.info("=" * 70)
    tipo_label = (
        "BANCÁRIO" if tipo_empresa == "bank" else dados_empresa.get("setor", "GERAL").upper()
    )
    logger.info(f"PIPELINE DE VALUATION [{tipo_label}] — {ticker} — {nome}")
    logger.info(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(
        f"  Setor: {dados_empresa.get('setor')} | Motor: {dados_empresa.get('motor_valuation', 'wacc').upper()}"
    )
    logger.info("=" * 70)

    usar_cache = not args.sem_cache
    anos_hist = args.anos or cfg.ANOS_HISTORICOS
    anos_proj = cfg.ANOS_PROJECAO

    # ── Retrocompatibilidade: dados_banco para o fluxo bancário existente ──
    # get_banco() agora lê do YAML via empresa_loader (retrocompatível)
    dados_banco = get_banco(ticker) if tipo_empresa == "bank" else None
    if dados_banco:
        logger.info(
            f"  Banco cadastrado: {dados_banco['nome']} | tipo: {dados_banco.get('tipo', '-')}"
        )

    # ── 1. Coletor de Dados de Mercado ─────────────────────────────────────
    if args.output and not args.batch:
        output_preflight = Path(args.output)
    elif getattr(args, "snapshot_excel", False):
        output_preflight = _caminho_valuation_snapshot(ticker, nome)
    else:
        output_preflight = _caminho_valuation_canonico(ticker)
    if not _verificar_excel_livre(output_preflight):
        return None

    logger.info("\n[1/6] Coletando dados de mercado...")
    from modules.coletor_mercado import ColetorMercado

    coletor_merc = ColetorMercado(cfg.CACHE_DIR, usar_cache)

    dados_acao = dados_banco or dados_empresa or {}
    ticker_upper = ticker.upper()
    ticker_on_cfg = (dados_acao.get("ticker_on") or "").upper()
    ticker_pn_cfg = (dados_acao.get("ticker_pn") or "").upper()
    tipo_acao_cfg = str(dados_acao.get("tipo_acao") or "ON_ONLY").upper()
    eh_unit = tipo_acao_cfg == "UNITS"
    relacao_acao = dados_acao.get("relacao_pn_on", cfg.RELACAO_PN_ON) or 1.0
    try:
        relacao_acao = float(relacao_acao)
    except (TypeError, ValueError):
        relacao_acao = float(cfg.RELACAO_PN_ON)
    relacao_acao = relacao_acao if relacao_acao > 0 else 1.0
    if eh_unit:
        relacao_acao = 1.0

    par_ticker = None
    if not eh_unit and (ticker_on_cfg or ticker_pn_cfg):
        if ticker_upper == ticker_pn_cfg and ticker_on_cfg:
            par_ticker = ticker_on_cfg
        elif ticker_upper == ticker_on_cfg and ticker_pn_cfg:
            par_ticker = ticker_pn_cfg
        elif ticker_on_cfg and ticker_on_cfg != ticker_upper:
            par_ticker = ticker_on_cfg
        elif ticker_pn_cfg and ticker_pn_cfg != ticker_upper:
            par_ticker = ticker_pn_cfg

    eh_pn = False if eh_unit else (
        ticker_upper == ticker_pn_cfg
        if ticker_pn_cfg
        else ticker_upper.endswith("4")
    )

    cotacao_on = args.cotacao_on
    cotacao_pn = args.cotacao_pn

    if cotacao_on == 0 or cotacao_pn == 0:
        logger.info("  Buscando cotação via yfinance...")
        info_atual = coletor_merc.preco_atual(ticker)
        preco_ticker = info_atual.get("preco", 0)
        if not preco_ticker and dados_empresa:
            for alias in dados_empresa.get("aliases", []) or []:
                info_alias = coletor_merc.preco_atual(alias)
                preco_alias = info_alias.get("preco", 0)
                if preco_alias:
                    logger.warning(
                        "  Cotacao principal indisponivel para %s; usando alias de mercado %s.",
                        ticker,
                        alias,
                    )
                    info_atual = info_alias
                    preco_ticker = preco_alias
                    break

        if eh_pn and par_ticker:
            info_on = coletor_merc.preco_atual(par_ticker)
            preco_on_yf = info_on.get("preco", 0)
            cotacao_pn = cotacao_pn or preco_ticker
            cotacao_on = cotacao_on or preco_on_yf or (preco_ticker / relacao_acao)
        elif not eh_pn and par_ticker:
            info_pn = coletor_merc.preco_atual(par_ticker)
            preco_pn_yf = info_pn.get("preco", 0)
            cotacao_on = cotacao_on or preco_ticker
            cotacao_pn = cotacao_pn or preco_pn_yf or (preco_ticker * relacao_acao)
        else:
            cotacao_on = cotacao_on or preco_ticker

        if eh_unit:
            logger.info(f"  Cotação UNIT: R$ {cotacao_on:.2f}")
        else:
            logger.info(f"  Cotação ON: R$ {cotacao_on:.2f}  |  Cotação PN: R$ {cotacao_pn:.2f}")

    # ── Ações emitidas — fonte: config/bancos.py (override Yahoo Finance) ──
    acoes_on = args.acoes_on
    acoes_pn = args.acoes_pn

    if acoes_on == 0 and dados_banco:
        # Usa total emitido oficial (Yahoo retorna float; para BBAS3 retorna ~50% do total)
        acoes_on = dados_banco["acoes_on_mil"]
        acoes_pn = dados_banco.get("acoes_pn_mil", 0) if acoes_pn == 0 else acoes_pn
        logger.info(f"  Ações (fonte: bancos.py): ON={acoes_on:,.0f} mil | PN={acoes_pn:,.0f} mil")
    elif acoes_on == 0 and dados_empresa and dados_empresa.get("acoes_on_mil", 0) > 0:
        # Ações do YAML (fonte de verdade para empresas cadastradas)
        acoes_on = dados_empresa["acoes_on_mil"]
        acoes_pn = dados_empresa.get("acoes_pn_mil", 0) if acoes_pn == 0 else acoes_pn
        logger.info(
            f"  Ações (fonte: empresas.yaml): ON={acoes_on:,.0f} mil | PN={acoes_pn:,.0f} mil"
        )
    elif acoes_on == 0:
        # Fallback: Yahoo Finance (menos confiável para ON+PN separados)
        info_acoes = coletor_merc.acoes_emitidas(ticker)
        acoes_total_yf = info_acoes.get("total", 1_000_000)
        if acoes_total_yf <= 0 and dados_empresa:
            for alias in dados_empresa.get("aliases", []) or []:
                info_alias = coletor_merc.acoes_emitidas(alias)
                acoes_alias = info_alias.get("total", 0)
                if acoes_alias > 0:
                    logger.warning(
                        "  Base acionaria principal indisponivel para %s; usando alias de mercado %s.",
                        ticker,
                        alias,
                    )
                    info_acoes = info_alias
                    acoes_total_yf = acoes_alias
                    break
        if par_ticker and acoes_pn == 0:
            info_par = coletor_merc.acoes_emitidas(par_ticker)
            acoes_par = info_par.get("total", acoes_total_yf)
            if eh_pn:
                acoes_pn, acoes_on = acoes_total_yf, acoes_par
            else:
                acoes_on, acoes_pn = acoes_total_yf, acoes_par
            logger.info(f"  Ações (Yahoo): ON={acoes_on:,.0f} | PN={acoes_pn:,.0f} mil")
        else:
            acoes_on = acoes_total_yf

    cotacao_on, cotacao_pn, acoes_on, acoes_pn, mercado_manual = _aplicar_market_override(
        ticker=ticker,
        dados_empresa=dados_empresa,
        cotacao_on=cotacao_on,
        cotacao_pn=cotacao_pn,
        acoes_on=acoes_on,
        acoes_pn=acoes_pn,
    )

    beta_dados = coletor_merc.calcular_beta(ticker)
    beta_calc = beta_dados.get("beta") or args.beta
    premissas_cadastro = (dados_empresa or {}).get("premissas", {}) or {}
    beta_config = premissas_cadastro.get("beta_utilizado", premissas_cadastro.get("beta"))
    if args.beta == cfg.BETA_UTILIZADO and beta_config is not None:
        beta_usar = beta_config
        beta_fonte = "empresas.yaml/setor"
    else:
        beta_usar = args.beta
        beta_fonte = "CLI/settings"
    logger.info(f"  Beta estatístico: {beta_calc:.3f} | Beta utilizado: {beta_usar:.3f} ({beta_fonte})")

    dados_mercado = {
        "preco": cotacao_on,
        "preco_pn": cotacao_pn or cotacao_on * relacao_acao,
        "preco_principal": cotacao_on if not eh_pn else (cotacao_pn or cotacao_on),
        "classe_principal": _classe_principal_acao(ticker, dados_acao),
        "tipo_acao": tipo_acao_cfg,
        "acoes_total": acoes_on + acoes_pn,
        "beta_calc": beta_calc,
        "beta_usar": beta_usar,
        "beta_fonte": beta_fonte,
        "fonte_mercado": mercado_manual.get("fonte") if mercado_manual else "B3/yfinance/cache/CLI",
        "mercado_manual": mercado_manual,
        **beta_dados,
    }

    # ── 2. Coletor Macroeconômico ──────────────────────────────────────────
    logger.info("\n[2/6] Coletando dados macroeconômicos (BCB)...")
    from modules.coletor_macro import ColetorMacro

    coletor_macro = ColetorMacro(cfg.CACHE_DIR, usar_cache)

    premissas_proj = {
        "di": dict(cfg.DI_PROJETADO),
        "ipca": dict(cfg.INFLACAO_IMPLICITA),
        "cds": {a: cfg.CDS_PROJETADO for a in anos_proj},
    }

    try:
        selic_focus = coletor_macro.expectativas_focus("Selic")
        ipca_focus = coletor_macro.expectativas_focus("IPCA")
        if selic_focus:
            logger.info(f"  Focus Selic: {dict(list(selic_focus.items())[:3])}")
            premissas_proj["di"].update(selic_focus)
        if ipca_focus:
            premissas_proj["ipca"].update(ipca_focus)
    except Exception as e:
        logger.warning(f"  Focus não disponível: {e}")

    macro = coletor_macro.dados_macro_completos(anos_hist, anos_proj, premissas_proj)

    # ── 3. Coletor CVM ─────────────────────────────────────────────────────
    dre_hist = None
    bp_hist = None
    dfc_hist = None  # novo: DFC para empresas não-financeiras
    ind_hist = None  # será calculado no passo 4 ou no fallback abaixo

    if not args.sem_cvm:
        logger.info("\n[3/6] Baixando demonstrações financeiras (CVM)...")
        from modules.coletor_cvm import ColetorCVM

        coletor_cvm = ColetorCVM(cfg.CACHE_DIR, usar_cache)

        # Fonte de verdade: CLI override → YAML → busca automática
        codigo_cvm = (
            codigo_cvm_override or args.codigo_cvm or (dados_empresa or {}).get("codigo_cvm")
        )

        if not codigo_cvm:
            codigo_cvm = coletor_cvm.buscar_codigo_cvm(ticker)

        if codigo_cvm:
            # DFP é anual e normalmente só existe até o último exercício fechado.
            # O ano corrente fica fora daqui para evitar 404 em dfp_cia_aberta_<ano_atual>.zip.
            from datetime import datetime as _dt_check

            _ano_atual = _dt_check.now().year
            _ultimo_ano_dfp = _ano_atual - 1
            anos_hist_expandido = sorted(
                {int(a) for a in anos_hist if int(a) <= _ultimo_ano_dfp} | {_ultimo_ano_dfp}
            )
            if any(int(a) > _ultimo_ano_dfp for a in anos_hist):
                logger.info(
                    f"  Ano corrente removido da coleta DFP: usando até {_ultimo_ano_dfp}"
                )

            if hasattr(coletor_cvm, "baixar_dfp_multiplos_anos_auto"):
                dados_brutos_raw = coletor_cvm.baixar_dfp_multiplos_anos_auto(
                    codigo_cvm, anos_hist_expandido
                )
            else:
                dados_brutos_raw = coletor_cvm.baixar_dfp_multiplos_anos(
                    codigo_cvm, anos_hist_expandido
                )

            # Filtrar anos que realmente retornaram dados via DFP
            dados_brutos = {}
            anos_sem_dfp = []
            for ano, conteudo in dados_brutos_raw.items():
                if conteudo and any(
                    v is not None and not (hasattr(v, "empty") and v.empty)
                    for v in conteudo.values()
                ):
                    dados_brutos[ano] = conteudo
                else:
                    anos_sem_dfp.append(ano)

            # ── Fallback ITR: anualizar anos sem DFP via dados trimestrais ──
            for ano_falta in sorted(anos_sem_dfp):
                ano_anterior = ano_falta - 1
                dfp_anterior = dados_brutos.get(ano_anterior, {})
                logger.info(f"  DFP {ano_falta} indisponível — tentando anualizar via ITR...")
                try:
                    dados_itr = coletor_cvm.anualizar_via_itr(codigo_cvm, ano_falta, dfp_anterior)
                    if dados_itr and any(
                        v is not None and not (hasattr(v, "empty") and v.empty)
                        for v in dados_itr.values()
                    ):
                        dados_brutos[ano_falta] = dados_itr
                        logger.info(f"  ✓ {ano_falta} anualizado via ITR (LTM)")
                    else:
                        logger.warning(
                            f"  DFP {ano_falta} e ITR indisponíveis — removido do histórico"
                        )
                except Exception as e:
                    logger.warning(f"  Erro ao anualizar {ano_falta} via ITR: {e}")

            # Atualizar anos_hist com base nos dados realmente obtidos
            anos_com_dados = sorted(dados_brutos.keys())
            if anos_com_dados != sorted(anos_hist):
                anos_hist = anos_com_dados
                # Recalcular anos de projeção: começam após o último ano histórico
                ultimo_hist = anos_hist[-1] if anos_hist else cfg.ANOS_HISTORICOS[-1]
                anos_proj = list(range(ultimo_hist + 1, ultimo_hist + 1 + len(cfg.ANOS_PROJECAO)))
                if anos_hist:
                    logger.info(
                        f"  Anos ajustados → Histórico: {anos_hist[0]}-{anos_hist[-1]} | Projeção: {anos_proj[0]}-{anos_proj[-1]}"
                    )
                else:
                    logger.warning(
                        "  Nenhum ano com dados históricos — continuando sem histórico CVM"
                    )

            # ── 4. Normalização ────────────────────────────────────────────
            logger.info("\n[4/6] Normalizando dados...")
            from modules.normalizador import Normalizador
            from config.mapeamento_contas_geral import get_mapeamento
            import copy

            _div = (dados_empresa or {}).get("divisor_cvm") or cfg.DIVISOR_VALORES
            norm = Normalizador(divisor=_div)

            # Selecionar mapeamento correto pelo tipo de empresa
            mapas = get_mapeamento(tipo_empresa)
            mapa_dre = mapas["dre"]
            mapa_ativo = copy.deepcopy(mapas["ativo"])
            mapa_passivo = copy.deepcopy(mapas["passivo"])
            mapa_dfc = mapas.get("dfc", {})

            # Aplicar overrides de contas por empresa (ex: BTG com estrutura diferente)
            mapa_override = (dados_empresa or dados_banco or {}).get("mapa_override", {})
            if mapa_override:
                nome_log = (dados_empresa or dados_banco or {}).get("nome", ticker)
                logger.info(f"  Aplicando overrides de contas para {nome_log}:")
                for conta, override in mapa_override.items():
                    if conta in mapa_ativo:
                        mapa_ativo[conta].update(override)
                        logger.info(f"    {conta}: {override['codigos']}")
                    elif conta in mapa_passivo:
                        mapa_passivo[conta].update(override)
                        logger.info(f"    {conta}: {override['codigos']}")

            dre_hist = norm.normalizar_dre(dados_brutos, mapa_dre)
            bp_hist = norm.normalizar_balanco(dados_brutos, mapa_ativo, mapa_passivo)

            # DFC + EBITDA para empresas não-financeiras
            if tipo_empresa != "bank" and mapa_dfc:
                dfc_hist = norm.normalizar_dfc(dados_brutos, mapa_dfc)
                dre_hist = norm.inject_da(dre_hist, bp_hist)
                if not dfc_hist.empty:
                    logger.info(f"  DFC normalizada: {len(dfc_hist)} linhas")

            if tipo_empresa == "bank":
                ind_hist = norm.calcular_indicadores(dre_hist, bp_hist, dados_mercado, macro)
            else:
                ind_hist = norm.calcular_indicadores_geral(
                    dre_hist,
                    bp_hist,
                    dados_mercado,
                    macro,
                    dfc=dfc_hist if dfc_hist is not None else None,
                )

            # Log de verificação
            logger.info("  DRE normalizada:")
            if not dre_hist.empty:
                linhas_check = (
                    ["margem_financeira_bruta", "lucro_liquido"]
                    if tipo_empresa == "bank"
                    else ["receita_liquida", "ebit", "lucro_liquido"]
                )
                for linha in linhas_check:
                    if linha in dre_hist.index:
                        vals = " | ".join(
                            f"{a}: {v:,.0f}" for a, v in dre_hist.loc[linha].items() if v
                        )
                        logger.info(f"    {linha}: {vals}")
        else:
            logger.warning("  Código CVM não encontrado — pulando dados CVM")
    else:
        logger.info("\n[3/6] Download CVM pulado (--sem-cvm)")

    # Fallback: DataFrames vazios se CVM não disponível
    if dre_hist is None:
        dre_hist = pd.DataFrame()
    if bp_hist is None:
        bp_hist = pd.DataFrame()

    # ind_hist: só calcula se não veio do passo 4 (evita recalcular e perder o resultado)
    if ind_hist is None:
        if not dre_hist.empty:
            from modules.normalizador import Normalizador as _Norm

            _div2 = (dados_empresa or {}).get("divisor_cvm") or cfg.DIVISOR_VALORES
            ind_hist = _Norm(divisor=_div2).calcular_indicadores(
                dre_hist, bp_hist, dados_mercado, macro
            )
        else:
            ind_hist = pd.DataFrame()

    # ── Quality gate (dados/escala) antes do valuation ───────────────────
    from modules.quality_gate import avaliar_qualidade, gerar_relatorio_quality_gate_pre

    qualidade = avaliar_qualidade(
        dre_hist=dre_hist,
        bp_hist=bp_hist,
        tipo_empresa=tipo_empresa,
        permitir_sem_historico=args.sem_cvm,
    )

    preco_principal = float(dados_mercado.get("preco_principal") or dados_mercado.get("preco") or 0)
    acoes_total = float(dados_mercado.get("acoes_total") or 0)
    if acoes_total <= 0:
        qualidade["critical"].append(
            "Base acionaria total ausente ou zerada; preco justo por acao nao e auditavel."
        )
        qualidade["score"] = max(0, qualidade.get("score", 100) - 35)
        qualidade["status_valuation"] = "BLOQUEADO"
        qualidade["valuation_preliminar"] = False
        qualidade["bloqueia_valuation"] = True
        qualidade["decisao"] = "bloquear"
        qualidade["motivo_status"] = "Dados de mercado/base acionaria insuficientes para valuation por acao."
    elif preco_principal <= 0:
        qualidade["warnings"].append(
            "Cotacao de mercado ausente ou zerada; upside e TIR devem ser tratados como preliminares."
        )
        qualidade["score"] = max(0, qualidade.get("score", 100) - 15)
        if not qualidade.get("bloqueia_valuation"):
            qualidade["status_valuation"] = "PRELIMINAR"
            qualidade["valuation_preliminar"] = True
            qualidade["decisao"] = "preliminar"
            qualidade["motivo_status"] = "Cotacao de mercado indisponivel no momento da execucao."

    logger.info(
        f"  Qualidade dos dados: score={qualidade['score']}/100 | "
        f"status={qualidade.get('status_valuation')} | "
        f"warnings={len(qualidade['warnings'])} | critical={len(qualidade['critical'])}"
    )
    for alerta in qualidade["warnings"]:
        logger.warning(f"  [quality] {alerta}")
    for falha in qualidade["critical"]:
        logger.error(f"  [quality] {falha}")

    pre_quality_report = gerar_relatorio_quality_gate_pre(
        ticker=ticker,
        qualidade=qualidade,
        output_dir=cfg.OUTPUT_DIR,
    )
    qualidade["pre_valuation_report"] = pre_quality_report

    if qualidade["bloqueia_valuation"]:
        logger.error(
            "Quality gate pre-valuation bloqueou o valuation. Relatorio: %s",
            pre_quality_report.get("markdown_path"),
        )
        return None
    if qualidade.get("valuation_preliminar"):
        logger.warning(
            "Valuation marcado como PRELIMINAR pelo quality gate pre-valuation. Relatorio: %s",
            pre_quality_report.get("markdown_path"),
        )

    # ── 5. Projeções ───────────────────────────────────────────────────────
    logger.info("\n[5/6] Calculando projeções...")
    from modules.valuation import MotorValuation

    # Mescla settings.py com premissas
    cfg_proj = dict(vars(cfg))
    cfg_proj["_ticker"] = ticker  # para log do valuation
    cfg_proj["TICKER_B3"] = ticker  # garante que valuation.py loga o ticker correto

    # Premissas da empresa (via YAML) — alimentam ambos os motores
    premissas_emp = (dados_empresa or {}).get("premissas", {})
    premissas_metodologia = dict(premissas_emp)
    if tipo_empresa == "bank":
        for campo in [
            "nim_alvo",
            "nim_maximo",
            "pcld_pct_alvo",
            "payout_projetado",
            "g_perpetuidade",
            "beta_utilizado",
            "crescimento_credito",
            "crescimento_servicos",
            "relacao_pn_on",
        ]:
            if dados_banco and campo in dados_banco:
                premissas_metodologia[campo] = dados_banco[campo]

    di_proj = premissas_proj["di"]
    cds_proj = premissas_proj["cds"]
    infl_proj = premissas_proj["ipca"]

    if tipo_empresa == "bank":
        # ── Fluxo bancário: FCFE / Ke ──────────────────────────────────
        from modules.projecoes import MotorProjecoes

        if dados_banco:
            CAMPOS_OVERRIDE = [
                "nim_alvo",
                "nim_maximo",
                "pcld_pct_alvo",
                "payout_projetado",
                "g_perpetuidade",
                "beta_utilizado",
                "crescimento_credito",
                "crescimento_servicos",
            ]
            ALIAS_CAMPOS = {
                "crescimento_credito": "CRESCIMENTO_CARTEIRA_CREDITO",
                "crescimento_servicos": "CRESCIMENTO_SERVICOS",
            }
            for campo in CAMPOS_OVERRIDE:
                if campo in dados_banco:
                    cfg_key = ALIAS_CAMPOS.get(campo, campo.upper())
                    cfg_proj[cfg_key] = dados_banco[campo]
                    cfg_proj[campo] = dados_banco[campo]
            relacao = dados_banco.get("relacao_pn_on", relacao_acao)
            cfg_proj["RELACAO_PN_ON"] = relacao
            logger.info(
                f"  Premissas banco: NIM={dados_banco.get('nim_alvo', '-'):.1%} | "
                f"Payout={dados_banco.get('payout_projetado', '-'):.0%} | "
                f"g={dados_banco.get('g_perpetuidade', '-'):.1%}"
            )

        motor_proj = MotorProjecoes(cfg_proj)
        dados_norm = {"dre": dre_hist, "balanco": bp_hist, "indicadores": ind_hist}
        projecoes = motor_proj.projetar_tudo(dados_norm, macro, anos_proj)

        motor_val = MotorValuation(cfg_proj)
        beta_banco = (dados_banco or {}).get("beta_utilizado", beta_usar)
        ke_proj = motor_val.calcular_ke_por_ano(
            di_proj, cds_proj, infl_proj, beta=beta_banco, erp=cfg.PREMIO_RISCO
        )
        macro["projecao"]["ke"] = ke_proj

        # ── 6. Valuation FCFE / Ke ────────────────────────────────────
        logger.info("\n[6/6] Calculando valuation (FCFE / Ke)...")
        fcfe_proj = projecoes.get("fcfe", {})
        g_banco = (dados_banco or {}).get("g_perpetuidade", args.g or cfg.G_PERPETUIDADE)
        relacao_banco = (dados_banco or {}).get("relacao_pn_on", relacao_acao)
        try:
            relacao_banco = float(relacao_banco)
        except (TypeError, ValueError):
            relacao_banco = relacao_acao
        cfg_proj["RELACAO_PN_ON"] = relacao_banco

        valuation = motor_val.calcular_tudo(
            fcfe_proj=fcfe_proj,
            ke_proj=ke_proj,
            cotacao_on=cotacao_on,
            cotacao_pn=cotacao_pn or cotacao_on * relacao_banco,
            acoes_on_mil=acoes_on,
            acoes_pn_mil=acoes_pn,
            g=g_banco,
        )

    else:
        # ── Fluxo geral: FCFF / WACC ──────────────────────────────────
        from modules.projecoes import MotorProjecoesGeral

        motor_proj = MotorProjecoesGeral(cfg_proj, premissas_emp)
        dados_norm = {
            "dre": dre_hist,
            "balanco": bp_hist,
            "indicadores": ind_hist,
            "dfc": dfc_hist if dfc_hist is not None else pd.DataFrame(),
        }
        projecoes = motor_proj.projetar_tudo(dados_norm, macro, anos_proj)

        relacao_emp = (dados_empresa or {}).get("relacao_pn_on", relacao_acao)
        try:
            relacao_emp = float(relacao_emp)
        except (TypeError, ValueError):
            relacao_emp = relacao_acao
        cfg_proj["RELACAO_PN_ON"] = relacao_emp

        motor_val = MotorValuation(cfg_proj)
        beta_emp = premissas_emp.get("beta", args.beta)
        ke_proj = motor_val.calcular_ke_por_ano(
            di_proj, cds_proj, infl_proj, beta=beta_emp, erp=cfg.PREMIO_RISCO
        )
        macro["projecao"]["ke"] = ke_proj

        # Estrutura de capital para WACC
        divida_liq_atual = 0
        if bp_hist is not None and not bp_hist.empty and "divida_liquida" in bp_hist.index:
            divida_liq_atual = float(bp_hist.loc["divida_liquida"].iloc[-1])

        cotacao_pn_wacc = cotacao_pn or (cotacao_on * relacao_emp if cotacao_on else 0)
        market_cap = (
            (cotacao_on * acoes_on + cotacao_pn_wacc * acoes_pn) / 1000
            if cotacao_on else 0
        )

        aliquota_ef = projecoes.get("aliquota_efetiva", 0.34)
        spread_div = premissas_emp.get(
            "custo_divida_spread", cfg_proj.get("CUSTO_DIVIDA_SPREAD", 0.02)
        )

        wacc_proj = motor_val.calcular_wacc_dinamico(
            ke_proj,
            di_proj,
            divida_liq=divida_liq_atual,
            market_cap=market_cap,
            spread_divida=spread_div,
            aliquota_ir=aliquota_ef,
        )
        macro["projecao"]["wacc"] = wacc_proj

        # ── 6. Valuation FCFF / WACC ──────────────────────────────────
        logger.info("\n[6/6] Calculando valuation (FCFF / WACC)...")
        fcff_proj = projecoes.get("fcff", {})
        g_emp = premissas_emp.get("g_perpetuidade", args.g or cfg.G_PERPETUIDADE)
        valuation = motor_val.calcular_tudo_fcff(
            fcff_proj=fcff_proj,
            wacc_proj=wacc_proj,
            divida_liquida=divida_liq_atual,
            cotacao_on=cotacao_on,
            cotacao_pn=cotacao_pn or cotacao_on * relacao_emp,
            acoes_on_mil=acoes_on,
            acoes_pn_mil=acoes_pn,
            g=g_emp,
        )

    avisos_classe_acao = _enriquecer_valuation_classe_acao(
        valuation,
        ticker=ticker,
        dados_acao=dados_acao,
        cotacao_on=cotacao_on,
        cotacao_pn=cotacao_pn,
        acoes_on=acoes_on,
        acoes_pn=acoes_pn,
    )
    valuation["status_valuation"] = qualidade.get("status_valuation", "CONFIAVEL")
    valuation["valuation_preliminar"] = bool(qualidade.get("valuation_preliminar"))
    valuation["motivo_status"] = qualidade.get("motivo_status")

    # ── Validação ─────────────────────────────────────────────────────────
    avisos = _validar_dados(dre_hist, bp_hist, projecoes, valuation)
    avisos.extend(avisos_classe_acao)
    avisos_modelo = list((projecoes or {}).get("_avisos_modelo") or [])
    if avisos_modelo:
        avisos.extend(avisos_modelo)
        qualidade.setdefault("warnings", [])
        qualidade["warnings"].extend(avisos_modelo)
        if not qualidade.get("bloqueia_valuation"):
            qualidade["status_valuation"] = "PRELIMINAR"
            qualidade["valuation_preliminar"] = True
            qualidade["motivo_status"] = "Modelo usou fallback de projecao; revisar premissas antes de confiar na recomendacao."
            valuation["status_valuation"] = "PRELIMINAR"
            valuation["valuation_preliminar"] = True
            valuation["motivo_status"] = qualidade["motivo_status"]
    if avisos:
        logger.warning("\n[!] AVISOS DE VALIDACAO:")
        for av in avisos:
            logger.warning(f"  - {av}")

    # ── Intelligence — camada de decisão ──────────────────────────────────
    from modules.intelligence import analisar_valuation as _analisar
    analise = _analisar(
        ticker=ticker,
        nome=nome,
        dados_empresa=dados_empresa,
        dre=dre_hist,
        balanco=bp_hist,
        indicadores=ind_hist,
        mercado=dados_mercado,
        valuation=valuation,
        avisos=avisos,
        qualidade=qualidade,
        sem_cvm=args.sem_cvm,
    )

    qualitativo = None
    if not getattr(args, "sem_qualitativo", False):
        try:
            from modules.qualitative_engine import run_qualitative_analysis

            ri_urls = _coletar_ri_urls(dados_empresa, args)
            qualitativo = run_qualitative_analysis(
                ticker=ticker,
                nome=nome,
                codigo_cvm=str((dados_empresa or {}).get("codigo_cvm") or codigo_cvm_override or ""),
                base_dir=ROOT,
                valuation_context=valuation,
                collect_cvm=bool(not args.sem_cvm),
                ri_urls=ri_urls,
                collect_ri=bool(not getattr(args, "sem_ri_crawler", False)),
                ri_depth=max(0, int(getattr(args, "ri_depth", 1) or 0)),
                ri_max_docs=max(0, int(getattr(args, "ri_max_docs", 25) or 0)),
            )
            logger.info(
                "  Qualitativo:       score=%s | eventos=%s | ri_docs=%s | relatorio=%s",
                qualitativo.get("overall_score"),
                qualitativo.get("events_count"),
                qualitativo.get("ri_documents_count"),
                qualitativo.get("report_path"),
            )
        except Exception as e:
            logger.warning("[qualitative] Falha na analise qualitativa: %s", e)

    # ── Escrever Excel ────────────────────────────────────────────────────
    # Arquivo de valuation: por padrão atualiza uma pasta de trabalho canônica
    # por ticker. Snapshots datados só são gerados quando pedidos.
    if args.output and not args.batch:
        output_path = Path(args.output)
    elif getattr(args, "snapshot_excel", False):
        output_path = _caminho_valuation_snapshot(ticker, nome)
    else:
        output_path = _caminho_valuation_canonico(ticker)

    # Template/base: só usa --template explícito ou, para bancos, o arquivo
    # canônico existente. Os exemplos externos não são mais base automática.
    template_arg = args.template
    setor_empresa = (dados_empresa or {}).get("setor", "")
    try:
        template_path = _localizar_template(
            template_arg,
            ticker=ticker,
            setor=setor_empresa,
            tipo_empresa=tipo_empresa,
            caminho_incremental=output_path,
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        return None

    # Selecionar escritor correto pelo tipo de empresa
    if tipo_empresa == "bank":
        from modules.escritor_excel import EscritorExcel

        escritor = EscritorExcel(
            caminho_template=template_path,
            ticker=ticker,
            anos_historicos=anos_hist,
            anos_projecao=anos_proj,
        )
    else:
        from modules.escritor_excel_geral import EscritorExcelGeral

        escritor = EscritorExcelGeral(
            caminho_template=template_path,  # None → cria do zero
            ticker=ticker,
            anos_historicos=anos_hist,
            anos_projecao=anos_proj,
        )

    premissas_efetivas = {
        "beta_usado": beta_usar,
        "beta_fonte": beta_fonte,
        "metodologia_setorial": metodologia_setorial,
        "g_perpetuidade": (
            (dados_banco or {}).get("g_perpetuidade", args.g or cfg.G_PERPETUIDADE)
            if tipo_empresa == "bank"
            else premissas_emp.get("g_perpetuidade", args.g or cfg.G_PERPETUIDADE)
        ),
        "anos_historicos": anos_hist,
        "anos_projecao": anos_proj,
        "status_valuation": valuation.get("status_valuation"),
        "classe_principal": valuation.get("classe_principal"),
        "tipo_acao": valuation.get("tipo_acao"),
    }
    if tipo_empresa == "bank":
        premissas_efetivas.update(
            {
                "payout": (dados_banco or {}).get("payout_projetado") or premissas_emp.get("payout"),
                "nim_alvo": (dados_banco or {}).get("nim_alvo") or premissas_emp.get("nim_alvo"),
            }
        )
    else:
        premissas_efetivas.update(
            {
                "motor": "fcff_wacc",
                "setor": (dados_empresa or {}).get("setor"),
                "margem_ebitda_alvo": premissas_emp.get("margem_ebitda_alvo"),
                "capex_pct_receita": premissas_emp.get("capex_pct_receita"),
                "ncg_pct_receita": premissas_emp.get("ncg_pct_receita"),
                "custo_divida_spread": premissas_emp.get("custo_divida_spread"),
            }
        )

    from modules.sector_operational_drivers import carregar_drivers_operacionais

    drivers_operacionais = carregar_drivers_operacionais(
        ticker=ticker,
        setor=(dados_empresa or {}).get("setor"),
        tipo_empresa=tipo_empresa,
        root_dir=cfg.ROOT_DIR,
    )

    dados_completos = {
        "dre": dre_hist,
        "balanco": bp_hist,
        "indicadores": ind_hist,
        "dfc": dfc_hist if dfc_hist is not None else pd.DataFrame(),
        "macro": macro,
        "mercado": dados_mercado,
        "projecoes": projecoes,
        "valuation": valuation,
        "qualidade": qualidade,
        "qualitativo": qualitativo,
        "drivers_operacionais": drivers_operacionais,
        "metodologia": {
            "ticker": ticker,
            "nome": nome,
            "setor": (dados_empresa or {}).get("setor"),
            "tipo_empresa": tipo_empresa,
            "motor_projecao": (dados_empresa or {}).get("motor_projecao"),
            "motor_valuation": (dados_empresa or {}).get("motor_valuation"),
            "tipo_acao": (dados_empresa or {}).get("tipo_acao"),
            "perfil_setorial": metodologia_setorial,
            "premissas": premissas_metodologia,
            "premissas_efetivas": premissas_efetivas,
        },
        "_trimestre": cfg.TRIMESTRE_ATUAL,
    }

    caminho_final = escritor.escrever(
        dados_completos,
        nome_empresa=nome,
        destino=output_path,
    )

    from modules.assumptions_auditor import gerar_relatorio_premissas
    from modules.post_excel_quality_gate import executar_quality_gate_excel

    premissas_audit = gerar_relatorio_premissas(
        ticker=ticker,
        tipo_empresa=tipo_empresa,
        dados_empresa=dados_empresa,
        dados_mercado=dados_mercado,
        macro=macro,
        valuation=valuation,
        premissas_efetivas=premissas_efetivas,
        output_dir=cfg.OUTPUT_DIR,
    )

    post_excel_quality = executar_quality_gate_excel(
        ticker=ticker,
        excel_path=caminho_final,
        tipo_empresa=tipo_empresa,
        anos_hist=anos_hist,
        anos_proj=anos_proj,
        output_dir=cfg.OUTPUT_DIR,
    )
    if post_excel_quality.get("bloqueia"):
        logger.error(
            "Quality gate final bloqueou o valuation. Relatorio: %s",
            post_excel_quality.get("markdown_path"),
        )
        return None
    if post_excel_quality.get("status") != "aprovado":
        valuation["status_valuation"] = "PRELIMINAR_EXCEL"
        valuation["valuation_preliminar"] = True
        valuation["motivo_status"] = (
            "Planilha final exige revisao: "
            + str(post_excel_quality.get("markdown_path"))
        )
        qualidade["status_valuation"] = "PRELIMINAR_EXCEL"
        qualidade["valuation_preliminar"] = True
        logger.warning(
            "Valuation marcado como PRELIMINAR_EXCEL pelo quality gate final. Relatorio: %s",
            post_excel_quality.get("markdown_path"),
        )
        analise = _analisar(
            ticker=ticker,
            nome=nome,
            dados_empresa=dados_empresa,
            dre=dre_hist,
            balanco=bp_hist,
            indicadores=ind_hist,
            mercado=dados_mercado,
            valuation=valuation,
            avisos=avisos,
            qualidade=qualidade,
            sem_cvm=args.sem_cvm,
        )

    summary_path = _escrever_run_summary(
        ticker=ticker,
        nome=nome,
        tipo_empresa=tipo_empresa,
        anos_hist=anos_hist,
        anos_proj=anos_proj,
        args=args,
        qualidade=qualidade,
        avisos=avisos,
        dados_mercado=dados_mercado,
        macro=macro,
        valuation=valuation,
        premissas_efetivas=premissas_efetivas,
        caminho_arquivo=str(caminho_final),
        analise=analise,
        qualitativo=qualitativo,
        post_excel_quality=post_excel_quality,
        premissas_audit=premissas_audit,
    )
    logger.info(f"  Run summary:       {summary_path}")

    # ── Banco de dados + Alertas ──────────────────────────────────────────
    from modules.database import salvar_valuation as _salvar_db, comparar_runs as _comparar
    from modules.alerts import verificar_e_alertar as _alertar

    _salvar_db(
        ticker=ticker,
        nome=nome,
        valuation=valuation,
        mercado=dados_mercado,
        analise=analise,
        avisos=avisos,
        qualidade=qualidade,
        tipo_empresa=tipo_empresa,
    )

    delta_score = None
    comp = _comparar(ticker)
    if comp and comp.get("delta_score") is not None:
        delta_score = int(comp["delta_score"])

    _alertar(analise, valuation, dados_mercado, delta_score=delta_score)

    # ── Relatório Markdown ────────────────────────────────────────────────
    from modules.report_writer import gerar_relatorio_tese as _gerar_tese
    caminho_tese = _gerar_tese(
        ticker=ticker,
        nome=nome,
        analise=analise,
        valuation=valuation,
        ind_hist=ind_hist,
        dados_empresa=dados_empresa,
        output_dir=cfg.OUTPUT_DIR,
        dre=dre_hist,
        mercado=dados_mercado,
        avisos=avisos,
        qualidade=qualidade,
    )

    # ── Parser RI (opcional — não bloqueia se falhar) ─────────────────────
    if not args.sem_cvm and (dados_empresa or {}).get("codigo_cvm"):
        try:
            from modules.parser_ri import extrair_dados_ri as _extrair_ri, resumo_ri
            dados_ri = _extrair_ri(
                ticker=ticker,
                codigo_cvm=str((dados_empresa or {}).get("codigo_cvm", "")),
                cache_dir=cfg.CACHE_DIR,
            )
            if dados_ri.get("metricas"):
                logger.info("\n[RI] %s", resumo_ri(dados_ri))
        except Exception as e:
            logger.debug("[parser_ri] Ignorado: %s", e)

    # ── Relatório final ───────────────────────────────────────────────────
    motor_label = "FCFF/WACC" if tipo_empresa != "bank" else "FCFE/Ke"
    logger.info("\n" + "=" * 70)
    logger.info(f"RESUMO DO VALUATION ({motor_label})")
    logger.info("=" * 70)
    logger.info(f"  Empresa:           {nome} ({ticker})")
    logger.info(f"  Status Valuation:  {valuation.get('status_valuation', 'CONFIAVEL')}")
    if tipo_empresa != "bank" and "ev_mm" in valuation:
        logger.info(f"  Enterprise Value:  R$ {valuation['ev_mm']:>12,.0f} MM")
    logger.info(f"  Cotação ON:        R$ {cotacao_on:.2f}")
    logger.info(f"  Preço Justo ON:    R$ {valuation['preco_justo_on']:.2f}")
    logger.info(f"  Upside ON:            {valuation['upside_on']:.1%}")
    logger.info(f"  TIR:                  {valuation['tir_on']:.1%}")
    logger.info(f"  Preço Teto ON:     R$ {valuation['preco_teto_on']:.2f}")
    logger.info(f"\n  ── Intelligence ──────────────────────────────────────")
    logger.info(f"  Recomendação:      {analise['recomendacao']}")
    logger.info(f"  Score:             {analise['score']}/100")
    logger.info(f"  Risco:             {analise['risco']}")
    logger.info(f"  Confiança:         {analise['confianca']} ({analise['motivo_confianca']})")
    logger.info(f"  Tese:              {analise['tese']}")
    if avisos:
        logger.info(f"\n  [!] {len(avisos)} aviso(s) de validacao — verifique os logs")
    logger.info(f"\n  Arquivo gerado:    {caminho_final}")
    logger.info(f"  Tese Markdown:     {caminho_tese}")
    logger.info("=" * 70)

    return {
        "ticker": ticker,
        "nome": nome,
        "caminho": caminho_final,
        "valuation": valuation,
        "cotacao_on": cotacao_on,
        "avisos": avisos,
        "qualidade": qualidade,
        "analise": analise,
        "qualitativo": qualitativo,
        "tese_markdown": str(caminho_tese),
        "run_summary": str(summary_path),
    }


def run_batch(args) -> list[dict]:
    """Executa o pipeline em modo batch para múltiplos tickers."""
    # Montar lista de tickers: --batch OU --batch-setor
    tickers = []
    if args.batch:
        tickers = [t.upper() for t in args.batch]
    elif getattr(args, "batch_setor", None):
        for setor in args.batch_setor:
            tickers_setor = listar_tickers(setor=setor)
            if tickers_setor:
                logger.info(f"  Setor '{setor}': {len(tickers_setor)} tickers")
                tickers.extend(tickers_setor)
            else:
                logger.warning(f"  Setor '{setor}' não encontrado ou sem tickers")
    elif getattr(args, "all", False):
        tickers = listar_tickers()

    if not tickers:
        logger.error("Nenhum ticker para processar no batch")
        return []

    resultados = []

    logger.info("=" * 70)
    logger.info(f"MODO BATCH — {len(tickers)} empresa(s): {', '.join(tickers)}")
    logger.info("=" * 70)

    erros = []
    for ticker in tickers:
        ticker = ticker.upper()

        # Fonte de verdade: empresas.yaml
        empresa_info = get_empresa(ticker)
        if not empresa_info:
            erros.append(ticker)
            logger.error(
                f"✗ {ticker}: não encontrado em config/empresas.yaml (cadastre antes de rodar batch)"
            )
            continue

        nome = empresa_info["nome"]
        codigo = empresa_info.get("codigo_cvm")

        logger.info(f"\n{'─' * 70}")
        logger.info(f"Processando: {ticker} ({nome})")
        logger.info(f"{'─' * 70}")

        try:
            resultado = run_single(args, ticker=ticker, nome=nome, codigo_cvm_override=codigo)
            if resultado:
                resultados.append(resultado)
                logger.info(f"✓ {ticker}: arquivo gerado → {resultado['caminho']}")
            else:
                erros.append(ticker)
                logger.error(f"✗ {ticker}: falhou (sem arquivo gerado)")
        except Exception as e:
            erros.append(ticker)
            logger.error(f"✗ {ticker}: erro inesperado — {e}", exc_info=True)

    # Resumo do batch
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO DO BATCH")
    logger.info("=" * 70)
    logger.info(f"  Total:     {len(tickers)}")
    logger.info(f"  Sucesso:   {len(resultados)}")
    logger.info(f"  Erros:     {len(erros)}")
    if erros:
        logger.info(f"  Tickers com erro: {', '.join(erros)}")
    logger.info("")
    logger.info(
        f"  {'Ticker':<10} {'Cotação ON':>12} {'Preço Justo ON':>15} {'Upside':>8} {'TIR':>8} {'Score':>6} {'Rec':>16}"
    )
    logger.info(f"  {'─' * 10} {'─' * 12} {'─' * 15} {'─' * 8} {'─' * 8} {'─' * 6} {'─' * 16}")
    for r in resultados:
        v = r["valuation"]
        a = r.get("analise") or {}
        logger.info(
            f"  {r['ticker']:<10} "
            f"  R${r['cotacao_on']:>8.2f}   "
            f"  R${v['preco_justo_on']:>8.2f}   "
            f"  {v['upside_on']:>7.1%}  "
            f"  {v['tir_on']:>7.1%}  "
            f"  {a.get('score', '-'):>5}  "
            f"  {a.get('recomendacao', '-'):>16}"
        )
    logger.info("=" * 70)

    return resultados


def run_auditoria_dados(args) -> dict:
    """Executa somente a auditoria de completude CVM/B3."""
    from modules.data_completeness_auditor import (
        executar_auditoria_completude,
        gerar_indice_csv,
        listar_tickers_auditoria,
    )

    tickers = listar_tickers_auditoria(args.all, args.ticker)
    if not tickers:
        logger.error("Nenhum ticker para auditar.")
        return {}

    logger.info("=" * 70)
    logger.info(f"AUDITORIA CVM/B3 — {len(tickers)} ticker(s): {', '.join(tickers)}")
    logger.info("=" * 70)

    auditorias = []
    erros = []
    for ticker in tickers:
        logger.info(f"\nAuditorando {ticker}...")
        try:
            audit = executar_auditoria_completude(
                ticker=ticker,
                anos=args.anos or cfg.ANOS_HISTORICOS,
                excel_path=args.audit_excel,
                usar_cache=not args.sem_cache,
                incluir_itr=not args.sem_itr_audit,
            )
            auditorias.append(audit)
            logger.info(
                f"  {ticker}: score={audit.get('score')}/100 | "
                f"critical={len(audit.get('critical', []))} | "
                f"warnings={len(audit.get('warnings', []))}"
            )
            logger.info(f"  Relatorio: {audit.get('arquivos', {}).get('markdown')}")
        except Exception as e:
            erros.append(ticker)
            logger.error(f"  {ticker}: erro na auditoria — {e}", exc_info=True)

    csv_path = gerar_indice_csv(auditorias) if auditorias else None
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO DA AUDITORIA")
    logger.info("=" * 70)
    logger.info(f"  Auditados: {len(auditorias)}")
    logger.info(f"  Erros:     {len(erros)}")
    if csv_path:
        logger.info(f"  CSV:       {csv_path}")
    if erros:
        logger.info(f"  Tickers com erro: {', '.join(erros)}")

    return {"auditorias": auditorias, "csv": str(csv_path) if csv_path else None, "erros": erros}


def run_qualitativo_only(args) -> dict:
    empresa_info = get_empresa(args.ticker)
    if not empresa_info:
        logger.error(
            f"Ticker '{args.ticker}' nao encontrado em config/empresas.yaml. "
            "Cadastre a empresa antes de executar."
        )
        return {}

    from modules.qualitative_engine import run_qualitative_analysis

    nome = args.nome or empresa_info.get("nome") or args.ticker
    codigo = args.codigo_cvm or empresa_info.get("codigo_cvm")
    logger.info("=" * 70)
    logger.info(f"ANALISE QUALITATIVA — {args.ticker.upper()} — {nome}")
    logger.info("=" * 70)
    ri_urls = _coletar_ri_urls(empresa_info, args)
    result = run_qualitative_analysis(
        ticker=args.ticker,
        nome=nome,
        codigo_cvm=str(codigo or ""),
        base_dir=ROOT,
        valuation_context={},
        collect_cvm=bool(not args.sem_cvm),
        ri_urls=ri_urls,
        collect_ri=bool(not getattr(args, "sem_ri_crawler", False)),
        ri_depth=max(0, int(getattr(args, "ri_depth", 1) or 0)),
        ri_max_docs=max(0, int(getattr(args, "ri_max_docs", 25) or 0)),
    )
    logger.info("  Relatorio: %s", result.get("report_path"))
    logger.info("  Scorecard: %s", result.get("scorecard_path"))
    logger.info("  Documentos RI: %s", result.get("ri_documents_count"))
    return result


def run(args):
    global logger
    log_level = "DEBUG" if args.debug else cfg.LOG_LEVEL
    logger = setup_logging(cfg.LOG_DIR, log_level)

    if getattr(args, "auditar_dados", False):
        return run_auditoria_dados(args)
    if getattr(args, "qualitativo_only", False):
        return run_qualitativo_only(args)
    if args.batch or getattr(args, "batch_setor", None) or getattr(args, "all", False):
        return run_batch(args)
    else:
        # Fonte de verdade: empresas.yaml
        empresa_info = get_empresa(args.ticker)
        if not empresa_info:
            logger.error(
                f"Ticker '{args.ticker}' não encontrado em config/empresas.yaml. "
                "Cadastre a empresa antes de executar."
            )
            return None

        nome = args.nome or empresa_info.get("nome") or args.ticker
        codigo = args.codigo_cvm or empresa_info.get("codigo_cvm")
        return run_single(args, ticker=args.ticker, nome=nome, codigo_cvm_override=codigo)


def main():
    args = parse_args()
    result = run(args)

    if getattr(args, "auditar_dados", False):
        if result and result.get("auditorias"):
            print(f"\n[OK] Auditoria concluida: {len(result['auditorias'])} ticker(s)")
            for audit in result["auditorias"]:
                print(
                    f"   {audit['ticker']:10s}  score={audit.get('score')}/100  "
                    f"-> {audit.get('arquivos', {}).get('markdown')}"
                )
            if result.get("csv"):
                print(f"   CSV consolidado -> {result['csv']}")
        else:
            print("\n[ERRO] Auditoria: nenhum ticker auditado. Verifique os logs.")
            sys.exit(1)
    elif getattr(args, "qualitativo_only", False):
        if result:
            print("\n[OK] Analise qualitativa concluida")
            print(f"   Relatorio:  {result.get('report_path')}")
            print(f"   Scorecard:  {result.get('scorecard_path')}")
        else:
            print("\n[ERRO] Analise qualitativa concluida com erros. Verifique os logs.")
            sys.exit(1)
    elif args.batch or getattr(args, "batch_setor", None) or getattr(args, "all", False):
        if result:
            print(f"\n[OK] Batch concluido: {len(result)} arquivo(s) gerado(s)")
            for r in result:
                print(f"   {r['ticker']:10s}  ->  {r['caminho']}")
        else:
            print("\n[ERRO] Batch: nenhum arquivo gerado. Verifique os logs.")
            sys.exit(1)
    else:
        if result:
            print(f"\n[OK] Arquivo gerado com sucesso: {result['caminho']}")
        else:
            print("\n[ERRO] Pipeline concluido com erros. Verifique os logs.")
            sys.exit(1)


if __name__ == "__main__":
    main()
