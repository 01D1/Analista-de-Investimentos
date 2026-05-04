"""
Signal Enricher — enriquece os setups da CALL_CONTINUIDADE
com dados de valuation (upside DCF) e notícias (headline).

Lê a seção `integracao:` do config_quant.yaml para localizar
os outputs dos projetos externos.  Se os diretórios não estiverem
configurados ou não existirem, retorna o DataFrame original sem
modificações — nunca falha silenciosamente nem interrompe o scanner.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.integration.valuation_bridge import get_valuations_batch
from src.integration.news_bridge import get_news_batch


def enrich_setups(df: pd.DataFrame, qcfg: dict) -> pd.DataFrame:
    """
    Adiciona colunas de enriquecimento ao DataFrame de setups.

    Colunas adicionadas (quando disponíveis):
        preco_alvo       — preço-alvo do DCF (R$)
        upside_pct       — upside em relação ao preço atual (%)
        data_valuation   — data do último valuation
        headline         — manchete mais recente
        headline_date    — data da manchete
        headline_source  — veículo da manchete

    Args:
        df:    DataFrame retornado por run_strategy
        qcfg:  configuração quant (config_quant.yaml já carregado)

    Returns:
        DataFrame com as colunas de enriquecimento (preenchidas com
        None/string vazia quando os dados não estão disponíveis).
    """
    if df.empty:
        return df

    integracao = qcfg.get("integracao", {})
    df = df.copy()

    # ---- Valuation (pipeline_banco_completo) --------------------------------
    val_dir_str = integracao.get("pipeline_banco_completo", {}).get("outputs_dir", "")
    if integracao.get("ativar_valuation", False) and val_dir_str:
        val_dir = Path(val_dir_str)
        tickers_ativo = df["underlying"].dropna().unique().tolist()
        valuations = get_valuations_batch(tickers_ativo, val_dir)

        def _upside(row: pd.Series) -> float | None:
            v = valuations.get(row["underlying"], {})
            return v.get("upside_pct")

        def _preco_alvo(row: pd.Series) -> float | None:
            v = valuations.get(row["underlying"], {})
            return v.get("preco_alvo")

        def _data_val(row: pd.Series) -> str:
            v = valuations.get(row["underlying"], {})
            return v.get("data_valuation", "")

        df["preco_alvo"] = df.apply(_preco_alvo, axis=1)
        df["upside_pct"] = df.apply(_upside, axis=1)
        df["data_valuation"] = df.apply(_data_val, axis=1)
    else:
        if "preco_alvo" not in df.columns:
            df["preco_alvo"] = None
        if "upside_pct" not in df.columns:
            df["upside_pct"] = None
        if "data_valuation" not in df.columns:
            df["data_valuation"] = ""

    # ---- Notícias (news_hunter) ----------------------------------------------
    news_dir_str = integracao.get("news_hunter", {}).get("outputs_dir", "")
    if integracao.get("ativar_noticias", False) and news_dir_str:
        news_dir = Path(news_dir_str)
        tickers_ativo = df["underlying"].dropna().unique().tolist()
        news_map = get_news_batch(tickers_ativo, news_dir)

        def _headline(row: pd.Series) -> str:
            return news_map.get(row["underlying"], {}).get("headline", "")

        def _headline_date(row: pd.Series) -> str:
            return news_map.get(row["underlying"], {}).get("headline_date", "")

        def _headline_source(row: pd.Series) -> str:
            return news_map.get(row["underlying"], {}).get("headline_source", "")

        df["headline"] = df.apply(_headline, axis=1)
        df["headline_date"] = df.apply(_headline_date, axis=1)
        df["headline_source"] = df.apply(_headline_source, axis=1)
    else:
        if "headline" not in df.columns:
            df["headline"] = ""
        if "headline_date" not in df.columns:
            df["headline_date"] = ""
        if "headline_source" not in df.columns:
            df["headline_source"] = ""

    return df
