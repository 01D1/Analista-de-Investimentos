"""
Historical Opportunity Scanner
===============================
Varre COTAHIST diário de opções para identificar oportunidades estratégicas
para o próximo pregão e horizontes maiores.

COTAHIST descobre oportunidade. RTD confirma execução.

Regras:
- Lê apenas de data/database/scanner_quant.db
- Não altera banco
- Não calcula valuation
- Não executa ordens
- market_type 070=CALL, 080=PUT; exclui 020 (termo)

Uso:
    python -m src.options.historical_opportunity_scanner
    python -m src.options.historical_opportunity_scanner --ativos PETR4 VALE3
    python -m src.options.historical_opportunity_scanner --output-dir /caminho/saida
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constantes ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "database" / "scanner_quant.db"
OUTPUT_DIR_DEFAULT = ROOT / "data" / "realtime"

ATIVOS_MONITORADOS: List[str] = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "B3SA3", "ABEV3", "WEGE3", "PRIO3", "SUZB3",
    "RENT3", "BPAC11", "GGBR4", "ENEV3", "CMIG4",
    "CPLE6", "TAEE11", "EGIE3", "RADL3", "HAPV3",
]

# Mapeamento ativo → prefixo das opções (primeiros 4 chars do ticker)
_PREFIXO_OPCAO: Dict[str, str] = {
    "PETR4": "PETR", "VALE3": "VALE", "ITUB4": "ITUB",
    "BBDC4": "BBDC", "BBAS3": "BBAS", "B3SA3": "B3SA",
    "ABEV3": "ABEV", "WEGE3": "WEGE", "PRIO3": "PRIO",
    "SUZB3": "SUZB", "RENT3": "RENT", "BPAC11": "BPAC",
    "GGBR4": "GGBR", "ENEV3": "ENEV", "CMIG4": "CMIG",
    "CPLE6": "CPLE", "TAEE11": "TAEE", "EGIE3": "EGIE",
    "RADL3": "RADL", "HAPV3": "HAPV",
}

# Parâmetros de liquidez
MIN_LIQUIDEZ_SCORE = 10
MIN_LIQUIDEZ_RTD = 30
MIN_LIQUIDEZ_CANDIDATA = 50

# Janelas de cálculo em pregões
JANELAS = [5, 10, 21]

# Colunas do CSV da watchlist de próxima sessão
WATCHLIST_COLS = [
    "ativo_objeto", "ticker_opcao", "tipo", "strike", "vencimento",
    "dte", "categoria_vencimento", "ultimo_preco", "liquidez_score",
    "cenario", "estruturas_sugeridas", "score", "status", "motivo",
]

# ── Enums ────────────────────────────────────────────────────────────────────


class CenarioHistorico(str, Enum):
    RECUPERACAO_APOS_QUEDA = "RECUPERACAO_APOS_QUEDA"
    CONTINUACAO_ALTA = "CONTINUACAO_ALTA"
    CONTINUACAO_BAIXA = "CONTINUACAO_BAIXA"
    PROTECAO_CARTEIRA = "PROTECAO_CARTEIRA"
    RENDA_COM_ATIVO = "RENDA_COM_ATIVO"
    VOLATILIDADE_EM_ALTA = "VOLATILIDADE_EM_ALTA"
    LATERALIDADE = "LATERALIDADE"
    SEM_ASSIMETRIA = "SEM_ASSIMETRIA"


class StatusOportunidade(str, Enum):
    ESTUDAR = "ESTUDAR"
    MONITORAR_NO_RTD = "MONITORAR_NO_RTD"
    CANDIDATA_PROXIMO_PREGAO = "CANDIDATA_PROXIMO_PREGAO"
    AGUARDAR_LIQUIDEZ = "AGUARDAR_LIQUIDEZ"
    DESCARTAR_ILIQUIDA = "DESCARTAR_ILIQUIDA"
    DESCARTAR_SEM_ASSIMETRIA = "DESCARTAR_SEM_ASSIMETRIA"


# ── Mapeamento cenário → estruturas ─────────────────────────────────────────

ESTRUTURAS_POR_CENARIO: Dict[CenarioHistorico, List[str]] = {
    CenarioHistorico.RECUPERACAO_APOS_QUEDA: ["Call Longa", "Trava de Alta", "Call Debit Spread"],
    CenarioHistorico.CONTINUACAO_ALTA:        ["Trava de Alta", "Call Debit Spread"],
    CenarioHistorico.CONTINUACAO_BAIXA:       ["Trava de Baixa", "Put Debit Spread"],
    CenarioHistorico.PROTECAO_CARTEIRA:       ["Protective Put", "Collar"],
    CenarioHistorico.RENDA_COM_ATIVO:         ["Covered Call", "Collar com Venda"],
    CenarioHistorico.VOLATILIDADE_EM_ALTA:    ["Monitorar — não estruturar no MVP"],
    CenarioHistorico.LATERALIDADE:            ["Monitorar — Iron Condor futuro"],
    CenarioHistorico.SEM_ASSIMETRIA:          [],
}

# ── Dataclass de resultado ───────────────────────────────────────────────────


@dataclass
class OportunidadeHistorica:
    # Identificação da opção
    ativo_objeto: str
    ticker_opcao: str
    tipo: str               # CALL ou PUT
    strike: float
    vencimento: str         # YYYY-MM-DD
    dte: int                # dias para vencimento
    categoria_vencimento: str   # CURTO/MEDIO/LONGO/EXTRA_LONGO

    # Métricas da opção
    ultimo_preco: float
    vol_media_5d: float
    vol_media_10d: float
    vol_media_21d: float
    negocios_media_5d: float
    variacao_volume: float     # vol_5d/vol_21d - 1
    variacao_preco: float      # close_last/close_5d_ago - 1

    # Moneyness
    moneyness: float           # valor numérico
    moneyness_cat: str         # ATM/OTM/ITM/DEEP_OTM/DEEP_ITM

    # Score de liquidez
    liquidez_score: float      # 0-100

    # Métricas do ativo objeto
    spot: float
    retorno_5d: float
    retorno_21d: float
    retorno_63d: float
    vol_hist_21d: float
    dist_max: float
    dist_min: float
    vol_relativa: float
    tendencia: str

    # Classificação estratégica
    cenario: str               # CenarioHistorico value
    estruturas_sugeridas: str  # comma-separated
    score: float               # 0-100
    status: str                # StatusOportunidade value
    motivo: str                # explicação textual
    risco_principal: str

    # Metadados
    data_analise: str          # data de hoje
    ultima_data_cotahist: str  # última data disponível no banco

    def to_dict(self) -> dict:
        return asdict(self)


# ── Funções auxiliares de classificação ─────────────────────────────────────


def _categorizar_vencimento(dte: int) -> str:
    """Classifica o vencimento por horizonte temporal."""
    if dte <= 0:
        return "EXPIRADO"
    if dte <= 30:
        return "CURTO"
    if dte <= 90:
        return "MEDIO"
    if dte <= 180:
        return "LONGO"
    return "EXTRA_LONGO"


def _classificar_moneyness(spot: float, strike: float, tipo: str) -> Tuple[float, str]:
    """
    Calcula o moneyness e classifica a opção.

    Returns:
        (moneyness_value, moneyness_cat)
    """
    if strike <= 0 or spot <= 0:
        return 0.0, "ATM"

    tipo_upper = tipo.upper()
    if tipo_upper == "CALL":
        moneyness = (spot - strike) / strike
    else:  # PUT
        moneyness = (strike - spot) / strike

    if moneyness > 0.10:
        cat = "DEEP_ITM"
    elif moneyness > 0.02:
        cat = "ITM"
    elif moneyness >= -0.02:
        cat = "ATM"
    elif moneyness >= -0.10:
        cat = "OTM"
    else:
        cat = "DEEP_OTM"

    return round(moneyness, 6), cat


def _liquidez_score(vol_5d: float, negocios_5d: float) -> float:
    """
    Score de liquidez 0-100.
    - Volume médio 5d: até 60 pts (normalizado em R$ 100 mil)
    - Negócios médios 5d: até 40 pts (normalizado em 10 negócios)
    """
    vol_score = min(vol_5d / 100_000, 1.0) * 60
    neg_score = min(negocios_5d / 10, 1.0) * 40
    return round(vol_score + neg_score, 1)


def _classificar_tendencia(
    retorno_5d: float,
    retorno_21d: float,
    vol_relativa: float,
) -> str:
    """
    Classifica a tendência do ativo objeto com base em retornos e volume relativo.
    """
    if retorno_5d > 0.03 and retorno_21d > 0.05:
        return "ALTA_FORTE"
    if retorno_5d > 0.01 and retorno_21d > 0.01:
        return "ALTA_MODERADA"
    if retorno_5d < -0.03 and retorno_21d < -0.05:
        return "BAIXA_FORTE"
    if retorno_5d < -0.01 and retorno_21d < -0.01:
        return "BAIXA_MODERADA"
    return "LATERAL"


def _classificar_cenario(
    retorno_5d: float,
    retorno_21d: float,
    vol_hist_21d: float,
    vol_relativa: float,
    tendencia: str,
) -> CenarioHistorico:
    """
    Classifica o cenário de mercado para o ativo objeto.
    Prioridade definida por ordem (primeiro match vence).
    """
    if retorno_21d < -0.08 and retorno_5d > -0.03:
        return CenarioHistorico.RECUPERACAO_APOS_QUEDA
    if retorno_5d > 0.02 and retorno_21d > 0.0:
        return CenarioHistorico.CONTINUACAO_ALTA
    if retorno_5d < -0.02 and retorno_21d < -0.04:
        return CenarioHistorico.CONTINUACAO_BAIXA
    if retorno_21d < -0.06:
        return CenarioHistorico.PROTECAO_CARTEIRA
    if tendencia == "LATERAL" and vol_hist_21d < 0.25:
        return CenarioHistorico.RENDA_COM_ATIVO
    if vol_relativa > 0.5 and vol_hist_21d > 0.35:
        return CenarioHistorico.VOLATILIDADE_EM_ALTA
    if tendencia == "LATERAL":
        return CenarioHistorico.LATERALIDADE
    return CenarioHistorico.SEM_ASSIMETRIA


def _classificar_status(
    liquidez_score: float,
    cenario: CenarioHistorico,
    categoria_vencimento: str,
) -> Tuple[StatusOportunidade, str]:
    """
    Determina o status da oportunidade e gera motivo explicativo.

    Returns:
        (status, motivo)
    """
    if liquidez_score < MIN_LIQUIDEZ_SCORE:
        return (
            StatusOportunidade.DESCARTAR_ILIQUIDA,
            f"Liquidez score {liquidez_score:.1f} < {MIN_LIQUIDEZ_SCORE} — volume insuficiente para estrutura.",
        )
    if cenario == CenarioHistorico.SEM_ASSIMETRIA:
        return (
            StatusOportunidade.DESCARTAR_SEM_ASSIMETRIA,
            "Sem cenário assimétrico identificado no ativo — aguardar definição de tendência.",
        )
    if (
        liquidez_score >= MIN_LIQUIDEZ_CANDIDATA
        and categoria_vencimento == "CURTO"
        and cenario != CenarioHistorico.SEM_ASSIMETRIA
    ):
        return (
            StatusOportunidade.CANDIDATA_PROXIMO_PREGAO,
            f"Liquidez score {liquidez_score:.1f} ≥ {MIN_LIQUIDEZ_CANDIDATA} com vencimento CURTO — candidata para próximo pregão.",
        )
    if liquidez_score >= MIN_LIQUIDEZ_RTD:
        return (
            StatusOportunidade.MONITORAR_NO_RTD,
            f"Liquidez score {liquidez_score:.1f} ≥ {MIN_LIQUIDEZ_RTD} — monitorar confirmação via RTD.",
        )
    if liquidez_score >= MIN_LIQUIDEZ_SCORE:
        return (
            StatusOportunidade.AGUARDAR_LIQUIDEZ,
            f"Liquidez score {liquidez_score:.1f} entre {MIN_LIQUIDEZ_SCORE} e {MIN_LIQUIDEZ_RTD} — aguardar aumento de liquidez.",
        )
    return (
        StatusOportunidade.ESTUDAR,
        "Condições parciais — estudar estrutura antes de monitorar.",
    )


def _calcular_score(
    liq_score: float,
    moneyness_cat: str,
    categoria_vencimento: str,
    cenario: CenarioHistorico,
    retorno_21d: float,
    vol_relativa: float,
) -> float:
    """
    Score de oportunidade histórica 0-100.

    Componentes:
    - Liquidez (max 30 pts)
    - Moneyness adequado (max 20 pts)
    - Vencimento adequado ao cenário (max 20 pts)
    - Assimetria do cenário (max 20 pts)
    - Volume relativo (max 10 pts)
    """
    score = 0.0

    # Liquidez (max 30 pts)
    score += min(liq_score * 0.30, 30.0)

    # Moneyness adequado — ATM e leve OTM valem mais
    moneyness_pts: Dict[str, float] = {
        "ATM": 20.0, "OTM": 15.0, "ITM": 10.0, "DEEP_OTM": 5.0, "DEEP_ITM": 5.0,
    }
    score += moneyness_pts.get(moneyness_cat, 0.0)

    # Vencimento adequado ao cenário
    venc_pts: Dict[str, float] = {
        "CURTO": 20.0, "MEDIO": 15.0, "LONGO": 10.0, "EXTRA_LONGO": 5.0,
    }
    score += venc_pts.get(categoria_vencimento, 0.0)

    # Assimetria do cenário
    cenarios_bons = {
        CenarioHistorico.RECUPERACAO_APOS_QUEDA,
        CenarioHistorico.CONTINUACAO_ALTA,
        CenarioHistorico.CONTINUACAO_BAIXA,
        CenarioHistorico.PROTECAO_CARTEIRA,
    }
    if cenario in cenarios_bons:
        score += 20.0
    elif cenario not in {CenarioHistorico.SEM_ASSIMETRIA}:
        score += 10.0

    # Volume relativo (max 10 pts)
    if vol_relativa > 0.5:
        score += 10.0
    elif vol_relativa > 0.2:
        score += 5.0

    return round(min(score, 100.0), 1)


def _risco_principal(cenario: CenarioHistorico, tipo: str, moneyness_cat: str) -> str:
    """Descreve o risco principal da posição em linguagem natural."""
    riscos = {
        CenarioHistorico.RECUPERACAO_APOS_QUEDA: "Tese de recuperação não se confirma — perda do prêmio pago.",
        CenarioHistorico.CONTINUACAO_ALTA: "Reversão de tendência antes do vencimento.",
        CenarioHistorico.CONTINUACAO_BAIXA: "Recuperação inesperada do ativo antes do vencimento.",
        CenarioHistorico.PROTECAO_CARTEIRA: "Decay temporal do prêmio caso o ativo não caia.",
        CenarioHistorico.RENDA_COM_ATIVO: "Ativo sobe acima do strike vendido — posição capped no upside.",
        CenarioHistorico.VOLATILIDADE_EM_ALTA: "Volatilidade pode reverter rapidamente — risco de posição direcional.",
        CenarioHistorico.LATERALIDADE: "Ruptura da faixa lateral invalida estrutura Iron Condor.",
        CenarioHistorico.SEM_ASSIMETRIA: "Sem assimetria clara — risco elevado de entrada sem edge.",
    }
    base = riscos.get(cenario, "Risco não mapeado — analisar contexto.")
    if moneyness_cat in ("DEEP_OTM", "DEEP_ITM"):
        base += f" Moneyness {moneyness_cat} aumenta risco de expiração sem valor."
    return base


# ── Carga de dados do banco ──────────────────────────────────────────────────


def _load_options_data(
    con: sqlite3.Connection,
    prefixo: str,
    n_pregoes: int = 63,
) -> pd.DataFrame:
    """
    Carrega dados de opções CALL/PUT para um prefixo de ativo.

    Args:
        con: Conexão SQLite
        prefixo: Prefixo do ativo (ex.: "PETR")
        n_pregoes: Número de pregões históricos a carregar

    Returns:
        DataFrame com colunas: trade_date, ticker, market_type, close, volume,
                               trades, strike, option_type, expiration_date
    """
    query = """
        SELECT trade_date, ticker, market_type, close, volume, trades,
               strike, option_type, expiration_date
        FROM cotahist_daily
        WHERE market_type IN ('070', '080')
          AND ticker LIKE :prefixo
        ORDER BY trade_date ASC, ticker ASC
    """
    try:
        df = pd.read_sql_query(
            query,
            con,
            params={"prefixo": f"{prefixo}%"},
        )
    except Exception as exc:
        logger.warning("Erro ao carregar opções para prefixo %s: %s", prefixo, exc)
        return pd.DataFrame()

    if df.empty:
        return df

    # Converter tipos
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce").fillna(0.0)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").fillna(0.0)
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce").fillna(0.0)

    # Filtrar para últimos n_pregoes por data
    if not df.empty:
        all_dates = sorted(df["trade_date"].dropna().unique())
        if len(all_dates) > n_pregoes:
            cutoff = all_dates[-n_pregoes]
            df = df[df["trade_date"] >= cutoff]

    return df


def _load_spot_data(
    con: sqlite3.Connection,
    ticker: str,
    n_pregoes: int = 252,
) -> pd.DataFrame:
    """
    Carrega dados históricos do ativo objeto (market_type='010').

    Returns:
        DataFrame com colunas: trade_date, close
    """
    query = """
        SELECT trade_date, close, volume, trades
        FROM cotahist_daily
        WHERE market_type = '010'
          AND ticker = :ticker
        ORDER BY trade_date ASC
    """
    try:
        df = pd.read_sql_query(query, con, params={"ticker": ticker})
    except Exception as exc:
        logger.warning("Erro ao carregar spot para %s: %s", ticker, exc)
        return pd.DataFrame()

    if df.empty:
        return df

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    df["trades"] = pd.to_numeric(df["trades"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["trade_date", "close"]).sort_values("trade_date").reset_index(drop=True)

    # Limitar ao histórico necessário
    if len(df) > n_pregoes:
        df = df.tail(n_pregoes).reset_index(drop=True)

    return df


# ── Cálculo de métricas do ativo objeto ─────────────────────────────────────


def _metricas_ativo_objeto(spot_df: pd.DataFrame) -> dict:
    """
    Calcula métricas históricas do ativo objeto.

    Returns:
        dict com retorno_5d, retorno_21d, retorno_63d, max_52w, min_52w,
             dist_max, dist_min, vol_hist_21d, vol_relativa, tendencia, spot
    """
    defaults = {
        "spot": float("nan"),
        "retorno_5d": 0.0,
        "retorno_21d": 0.0,
        "retorno_63d": 0.0,
        "max_52w": float("nan"),
        "min_52w": float("nan"),
        "dist_max": 0.0,
        "dist_min": 0.0,
        "vol_hist_21d": 0.0,
        "vol_relativa": 0.0,
        "tendencia": "SEM_DADOS",
    }

    if spot_df is None or spot_df.empty or len(spot_df) < 2:
        return defaults

    df = spot_df.sort_values("trade_date").reset_index(drop=True)
    closes = df["close"].values

    last_close = float(closes[-1])
    defaults["spot"] = last_close

    def _safe_retorno(n: int) -> float:
        if len(closes) <= n:
            return 0.0
        prev = closes[-(n + 1)]
        if prev == 0 or np.isnan(prev):
            return 0.0
        return float((closes[-1] / prev) - 1)

    retorno_5d = _safe_retorno(5)
    retorno_21d = _safe_retorno(21)
    retorno_63d = _safe_retorno(63)

    # 52 semanas = 252 pregões
    window_252 = closes[-252:] if len(closes) >= 252 else closes
    max_52w = float(np.nanmax(window_252)) if len(window_252) > 0 else last_close
    min_52w = float(np.nanmin(window_252)) if len(window_252) > 0 else last_close

    dist_max = (last_close / max_52w - 1) if max_52w > 0 else 0.0
    dist_min = (last_close / min_52w - 1) if min_52w > 0 else 0.0

    # Volatilidade histórica anualizada 21d
    window_closes = closes[-22:] if len(closes) >= 22 else closes
    if len(window_closes) >= 2:
        log_rets = np.diff(np.log(window_closes[window_closes > 0]))
        vol_hist_21d = float(np.std(log_rets, ddof=1) * np.sqrt(252)) if len(log_rets) > 0 else 0.0
    else:
        vol_hist_21d = 0.0

    # Volume relativo (vol_5d_acao / vol_21d_acao - 1)
    vols = df["volume"].values
    vol_5d_acao = float(np.mean(vols[-5:])) if len(vols) >= 5 else 0.0
    vol_21d_acao = float(np.mean(vols[-21:])) if len(vols) >= 21 else 0.0
    if vol_21d_acao > 0:
        vol_relativa = float(vol_5d_acao / vol_21d_acao - 1)
    else:
        vol_relativa = 0.0

    tendencia = _classificar_tendencia(retorno_5d, retorno_21d, vol_relativa)

    return {
        "spot": last_close,
        "retorno_5d": round(retorno_5d, 6),
        "retorno_21d": round(retorno_21d, 6),
        "retorno_63d": round(retorno_63d, 6),
        "max_52w": round(max_52w, 4),
        "min_52w": round(min_52w, 4),
        "dist_max": round(dist_max, 6),
        "dist_min": round(dist_min, 6),
        "vol_hist_21d": round(vol_hist_21d, 6),
        "vol_relativa": round(vol_relativa, 6),
        "tendencia": tendencia,
    }


# ── Cálculo de métricas da opção ────────────────────────────────────────────


def _metricas_opcao(ticker_df: pd.DataFrame) -> dict:
    """
    Calcula métricas temporais para uma opção individual.

    Args:
        ticker_df: DataFrame filtrado para um único ticker, ordenado por trade_date.

    Returns:
        dict com ultimo_preco, vol_media_5d/10d/21d, negocios_media_5d,
             variacao_volume, variacao_preco
    """
    if ticker_df is None or ticker_df.empty:
        return {
            "ultimo_preco": 0.0,
            "vol_media_5d": 0.0,
            "vol_media_10d": 0.0,
            "vol_media_21d": 0.0,
            "negocios_media_5d": 0.0,
            "variacao_volume": 0.0,
            "variacao_preco": 0.0,
        }

    df = ticker_df.sort_values("trade_date").reset_index(drop=True)
    closes = df["close"].values
    volumes = df["volume"].values
    trades_arr = df["trades"].values

    ultimo_preco = float(closes[-1]) if len(closes) > 0 else 0.0

    def _mean_n(arr: np.ndarray, n: int) -> float:
        if len(arr) == 0:
            return 0.0
        window = arr[-n:] if len(arr) >= n else arr
        val = np.mean(window)
        return float(val) if not np.isnan(val) else 0.0

    vol_media_5d = _mean_n(volumes, 5)
    vol_media_10d = _mean_n(volumes, 10)
    vol_media_21d = _mean_n(volumes, 21)
    negocios_media_5d = _mean_n(trades_arr, 5)

    # variacao_volume: vol_5d / vol_21d - 1
    if vol_media_21d > 0:
        variacao_volume = round(vol_media_5d / vol_media_21d - 1, 6)
    else:
        variacao_volume = 0.0

    # variacao_preco: close_last / close_5d_ago - 1
    if len(closes) >= 6:
        close_5d_ago = closes[-6]
    elif len(closes) >= 2:
        close_5d_ago = closes[0]
    else:
        close_5d_ago = closes[-1] if len(closes) > 0 else 0.0

    if close_5d_ago > 0:
        variacao_preco = round(float(closes[-1]) / float(close_5d_ago) - 1, 6)
    else:
        variacao_preco = 0.0

    return {
        "ultimo_preco": round(ultimo_preco, 4),
        "vol_media_5d": round(vol_media_5d, 2),
        "vol_media_10d": round(vol_media_10d, 2),
        "vol_media_21d": round(vol_media_21d, 2),
        "negocios_media_5d": round(negocios_media_5d, 2),
        "variacao_volume": variacao_volume,
        "variacao_preco": variacao_preco,
    }


# ── Processamento por ativo ──────────────────────────────────────────────────


def _processar_ativo(
    ativo: str,
    con: sqlite3.Connection,
    today: date,
    ultima_data_cotahist: str,
) -> List[OportunidadeHistorica]:
    """
    Processa um único ativo monitorado e retorna lista de oportunidades.
    """
    prefixo = _PREFIXO_OPCAO.get(ativo, ativo[:4])
    logger.debug("Processando ativo %s (prefixo=%s)", ativo, prefixo)

    # 1. Carregar spot data
    spot_df = _load_spot_data(con, ativo, n_pregoes=252)
    metr_spot = _metricas_ativo_objeto(spot_df)

    spot = metr_spot["spot"]
    if np.isnan(spot) or spot <= 0:
        logger.warning("Spot inválido para %s — pulando.", ativo)
        return []

    # 2. Carregar opções
    opcoes_df = _load_options_data(con, prefixo, n_pregoes=63)
    if opcoes_df.empty:
        logger.info("Sem opções para %s.", ativo)
        return []

    # 3. Filtrar opções com vencimento futuro
    opcoes_df["expiration_date"] = pd.to_datetime(opcoes_df["expiration_date"], errors="coerce")
    opcoes_df = opcoes_df[opcoes_df["expiration_date"] > pd.Timestamp(today)].copy()
    if opcoes_df.empty:
        logger.info("Sem opções com vencimento futuro para %s.", ativo)
        return []

    # 4. Classificar cenário do ativo objeto
    cenario = _classificar_cenario(
        metr_spot["retorno_5d"],
        metr_spot["retorno_21d"],
        metr_spot["vol_hist_21d"],
        metr_spot["vol_relativa"],
        metr_spot["tendencia"],
    )

    estruturas = ESTRUTURAS_POR_CENARIO.get(cenario, [])
    estruturas_str = ", ".join(estruturas) if estruturas else ""

    # 5. Para cada ticker de opção único, calcular métricas
    oportunidades: List[OportunidadeHistorica] = []

    # Pegar o último dado de cada ticker (strike, expiration, tipo)
    latest_by_ticker = (
        opcoes_df.sort_values("trade_date")
        .groupby("ticker")
        .last()
        .reset_index()
    )

    tickers_unicos = latest_by_ticker["ticker"].tolist()
    logger.debug("  %d tickers de opções para %s", len(tickers_unicos), ativo)

    for _, row_latest in latest_by_ticker.iterrows():
        ticker_opcao = row_latest["ticker"]
        strike = float(row_latest["strike"]) if not np.isnan(row_latest["strike"]) else 0.0
        expiration = row_latest["expiration_date"]
        market_type = row_latest["market_type"]
        option_type_raw = row_latest.get("option_type", "")

        # Determinar tipo CALL/PUT pelo market_type
        if market_type == "070":
            tipo = "CALL"
        elif market_type == "080":
            tipo = "PUT"
        else:
            continue

        # DTE — dias calendário a partir de hoje
        try:
            exp_date = expiration.date() if hasattr(expiration, "date") else expiration
            dte = (exp_date - today).days
        except Exception:
            dte = -1

        if dte <= 0:
            continue

        cat_venc = _categorizar_vencimento(dte)

        # Métricas da opção (série histórica completa do ticker)
        ticker_series = opcoes_df[opcoes_df["ticker"] == ticker_opcao].sort_values("trade_date")
        metr_opcao = _metricas_opcao(ticker_series)

        liq_score = _liquidez_score(metr_opcao["vol_media_5d"], metr_opcao["negocios_media_5d"])

        # Moneyness
        moneyness_val, moneyness_cat = _classificar_moneyness(spot, strike, tipo)

        # Score geral
        score = _calcular_score(
            liq_score,
            moneyness_cat,
            cat_venc,
            cenario,
            metr_spot["retorno_21d"],
            metr_spot["vol_relativa"],
        )

        # Status e motivo
        status, motivo = _classificar_status(liq_score, cenario, cat_venc)

        # Risco principal
        risco = _risco_principal(cenario, tipo, moneyness_cat)

        opp = OportunidadeHistorica(
            ativo_objeto=ativo,
            ticker_opcao=ticker_opcao,
            tipo=tipo,
            strike=round(strike, 4),
            vencimento=exp_date.strftime("%Y-%m-%d") if exp_date else "",
            dte=dte,
            categoria_vencimento=cat_venc,
            ultimo_preco=metr_opcao["ultimo_preco"],
            vol_media_5d=metr_opcao["vol_media_5d"],
            vol_media_10d=metr_opcao["vol_media_10d"],
            vol_media_21d=metr_opcao["vol_media_21d"],
            negocios_media_5d=metr_opcao["negocios_media_5d"],
            variacao_volume=metr_opcao["variacao_volume"],
            variacao_preco=metr_opcao["variacao_preco"],
            moneyness=moneyness_val,
            moneyness_cat=moneyness_cat,
            liquidez_score=liq_score,
            spot=round(spot, 4),
            retorno_5d=metr_spot["retorno_5d"],
            retorno_21d=metr_spot["retorno_21d"],
            retorno_63d=metr_spot["retorno_63d"],
            vol_hist_21d=metr_spot["vol_hist_21d"],
            dist_max=metr_spot["dist_max"],
            dist_min=metr_spot["dist_min"],
            vol_relativa=metr_spot["vol_relativa"],
            tendencia=metr_spot["tendencia"],
            cenario=cenario.value,
            estruturas_sugeridas=estruturas_str,
            score=score,
            status=status.value,
            motivo=motivo,
            risco_principal=risco,
            data_analise=today.strftime("%Y-%m-%d"),
            ultima_data_cotahist=ultima_data_cotahist,
        )
        oportunidades.append(opp)

    logger.info(
        "Ativo %s: %d oportunidades encontradas (cenário=%s)",
        ativo, len(oportunidades), cenario.value,
    )
    return oportunidades


# ── Função principal ─────────────────────────────────────────────────────────


def run_historical_scanner(
    db_path: Optional[Path] = None,
    ativos: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
    today: Optional[date] = None,
) -> pd.DataFrame:
    """
    Roda o scanner histórico e retorna DataFrame com oportunidades.
    Também salva os CSVs de output em output_dir.

    Args:
        db_path: Caminho para o banco SQLite (padrão: DB_PATH)
        ativos: Lista de ativos a processar (padrão: ATIVOS_MONITORADOS)
        output_dir: Diretório de saída para os CSVs (padrão: OUTPUT_DIR_DEFAULT)
        today: Data de referência (padrão: date.today())

    Returns:
        DataFrame com todas as oportunidades encontradas.
        DataFrame vazio se o banco não existir ou não houver dados.
    """
    _db_path = db_path or DB_PATH
    _ativos = ativos or ATIVOS_MONITORADOS
    _output_dir = output_dir or OUTPUT_DIR_DEFAULT
    _today = today or date.today()

    logger.info(
        "Iniciando Historical Opportunity Scanner | data=%s | ativos=%d | db=%s",
        _today.isoformat(), len(_ativos), _db_path,
    )

    # Verificar existência do banco
    if not Path(_db_path).exists():
        logger.error("Banco de dados não encontrado: %s", _db_path)
        return pd.DataFrame()

    try:
        con = sqlite3.connect(str(_db_path))
    except Exception as exc:
        logger.error("Falha ao conectar ao banco %s: %s", _db_path, exc)
        return pd.DataFrame()

    try:
        # Última data disponível no COTAHIST
        cur = con.cursor()
        cur.execute(
            "SELECT MAX(trade_date) FROM cotahist_daily WHERE market_type IN ('070','080')"
        )
        row = cur.fetchone()
        ultima_data_cotahist = row[0] if row and row[0] else _today.strftime("%Y-%m-%d")

        all_oportunidades: List[OportunidadeHistorica] = []

        for ativo in _ativos:
            try:
                opps = _processar_ativo(ativo, con, _today, ultima_data_cotahist)
                all_oportunidades.extend(opps)
            except Exception as exc:
                logger.error("Erro ao processar ativo %s: %s", ativo, exc, exc_info=True)
                continue

    finally:
        con.close()

    if not all_oportunidades:
        logger.warning("Nenhuma oportunidade encontrada para os ativos monitorados.")
        return pd.DataFrame()

    # Converter para DataFrame
    df_all = pd.DataFrame([o.to_dict() for o in all_oportunidades])
    df_all = df_all.sort_values("score", ascending=False).reset_index(drop=True)

    # Salvar CSVs
    _output_dir = Path(_output_dir)
    _output_dir.mkdir(parents=True, exist_ok=True)

    path_all = _output_dir / "options_historical_opportunities.csv"
    df_all.to_csv(path_all, index=False, encoding="utf-8")
    logger.info("CSV completo salvo: %s (%d linhas)", path_all, len(df_all))

    # Watchlist: apenas CANDIDATA_PROXIMO_PREGAO ou MONITORAR_NO_RTD
    watchlist_statuses = {
        StatusOportunidade.CANDIDATA_PROXIMO_PREGAO.value,
        StatusOportunidade.MONITORAR_NO_RTD.value,
    }
    df_watchlist = (
        df_all[df_all["status"].isin(watchlist_statuses)]
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )

    # Garantir que todas as colunas da watchlist existam
    available_cols = [c for c in WATCHLIST_COLS if c in df_watchlist.columns]
    df_watchlist = df_watchlist[available_cols]

    path_watchlist = _output_dir / "options_next_session_watchlist.csv"
    df_watchlist.to_csv(path_watchlist, index=False, encoding="utf-8")
    logger.info(
        "Watchlist próxima sessão salva: %s (%d linhas)", path_watchlist, len(df_watchlist)
    )

    return df_all


# ── CLI ──────────────────────────────────────────────────────────────────────


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Historical Options Opportunity Scanner — B3 COTAHIST",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ativos",
        nargs="+",
        default=None,
        metavar="TICKER",
        help="Ativos a processar (padrão: todos os 20 monitorados)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"Diretório de saída para CSVs (padrão: {OUTPUT_DIR_DEFAULT})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Caminho do banco SQLite (padrão: {DB_PATH})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Log nível DEBUG",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    df = run_historical_scanner(
        db_path=args.db,
        ativos=args.ativos,
        output_dir=args.output_dir,
    )

    if df.empty:
        print("Nenhuma oportunidade encontrada.")
        return

    # Resumo no console
    print(f"\n{'='*60}")
    print(f"HISTORICAL OPPORTUNITY SCANNER — {date.today().isoformat()}")
    print(f"{'='*60}")
    print(f"Total oportunidades: {len(df)}")

    watchlist_statuses = {
        StatusOportunidade.CANDIDATA_PROXIMO_PREGAO.value,
        StatusOportunidade.MONITORAR_NO_RTD.value,
    }
    df_watch = df[df["status"].isin(watchlist_statuses)]
    print(f"Candidatas próximo pregão / RTD: {len(df_watch)}")

    if not df_watch.empty:
        print("\nTop 10 por score:")
        top10_cols = ["ativo_objeto", "ticker_opcao", "tipo", "score", "status", "cenario"]
        available = [c for c in top10_cols if c in df_watch.columns]
        print(df_watch.head(10)[available].to_string(index=False))

    print(f"\nSaída em: {args.output_dir or OUTPUT_DIR_DEFAULT}")
    print("="*60)


if __name__ == "__main__":
    main()
