"""
Options Market Service — Fonte canônica de dados de opções
==========================================================

Regras:
  - Lê options CSVs (histórico, watchlist, símbolos RTD)
  - Lê RTD PROFIT.xlsx aba Opções para dados ao vivo por strike/Greeks
  - Não calcula nada — expõe dados existentes
  - Não escreve no banco
  - Retorna sempre status/timestamp/source/diagnostic

API pública:
  get_options_chain_payload(underlying, expiration?)
  get_option_history_payload(option_ticker, period?)
  get_options_radar_payload(underlying?)

Fontes:
  data/realtime/options_historical_opportunities.csv
  data/realtime/options_next_session_watchlist.csv
  data/realtime/options_rtd_symbols.csv
  data/realtime/RTD PROFIT.xlsx (aba Opções)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

def _scanner_root() -> Path:
    p = Path(__file__).resolve().parents[2]
    if (p / "src").is_dir():
        return p
    return Path.cwd()


RTD_PATH = _scanner_root() / "data" / "realtime" / "RTD PROFIT.xlsx"
HISTORICAL_OPP_PATH = _scanner_root() / "data" / "realtime" / "options_historical_opportunities.csv"
WATCHLIST_PATH = _scanner_root() / "data" / "realtime" / "options_next_session_watchlist.csv"
SYMBOLS_PATH = _scanner_root() / "data" / "realtime" / "options_rtd_symbols.csv"
DIAGNOSTIC_PATH = _scanner_root() / "data" / "realtime" / "options_rtd_diagnostic.csv"


# ── Parse helpers ────────────────────────────────────────────────────────────

def _parse_br(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return None if (v != v) else v
    s = str(value).strip()
    if s in ("-", "", "nan", "None", "NaN"):
        return None
    s_clean = s.replace("R$", "").replace("%", "").strip()
    # Try standard US float first ("24.5", "124356.2", "0.62")
    try:
        return float(s_clean)
    except ValueError:
        pass
    # Fall back to Brazilian format: "1.234,56" → 1234.56
    try:
        return float(s_clean.replace(".", "").replace(",", "."))
    except Exception:
        return None


def _parse_int(value) -> Optional[int]:
    v = _parse_br(value)
    return int(v) if v is not None else None


def _parse_date(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if s in ("nan", "None", ""):
        return None
    return s[:10]


# ── Underlying normalization ──────────────────────────────────────────────

def _normalize_underlying(u: str) -> str:
    """Normaliza ticker de ativo objeto: PETR4→PETR, VALE3→VALE, ITUB→ITUB."""
    u = str(u or "").strip().upper()
    suffix = u[-1] if len(u) > 0 else ""
    if suffix in ("3", "4", "5", "6", "11"):
        return u[:-1]
    return u


def _ticker_to_underlying(ticker: str) -> str:
    """Deriva ativo objeto de ticker de opção: BBDCF17→BBDC, ENEVR250→ENEV."""
    t = str(ticker or "").strip().upper()
    # Padrão: prefixo de 3-5 letras + letra de tipo (F/G/T/R) + strike
    m = re.match(r"^([A-Z]{2,5})([FGTR])([0-9]+)", t)
    if m:
        return m.group(1)
    # Padrão WAR (warrant)
    m2 = re.match(r"^([A-Z]{2,5})W([0-9]+)", t)
    if m2:
        return m2.group(1)
    return t[:4]


def _is_option_ticker(ticker: str) -> bool:
    """Detecta se ticker é opção (sufixo F/G/R/T + dígitos)."""
    t = str(ticker or "").strip().upper()
    return bool(re.match(r"^[A-Z]{2,5}[FGTR][0-9]+", t)) or bool(
        re.match(r"^[A-Z]{2,5}W[0-9]+", t)
    )


def _derive_option_type(ticker: str) -> str:
    """Deriva CALL/PUT do ticker de opção."""
    t = str(ticker or "").strip().upper()
    # T=G/T/U = CALL (T para calls no padrão Profit)
    # R/F/G = PUT
    if len(t) >= 6:
        letter = t[5] if t[5].isalpha() else ""
        if letter in ("G", "F"):
            return "PUT"
        if letter in ("T", ) or letter == "U":
            return "CALL"
        # Se não consiga, usar vencimento
    if "R" in t:
        return "PUT"
    return "CALL"


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_historical() -> pd.DataFrame:
    """Carrega oportunidades históricas de opções."""
    if not HISTORICAL_OPP_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(HISTORICAL_OPP_PATH, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        logger.warning(f"[options_market] historical: {e}")
        return pd.DataFrame()


def _load_watchlist() -> pd.DataFrame:
    """Carrega watchlist de opções para próximo pregão."""
    if not WATCHLIST_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(WATCHLIST_PATH, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        logger.warning(f"[options_market] watchlist: {e}")
        return pd.DataFrame()


def _load_symbols() -> pd.DataFrame:
    """Carrega símbolos RTD de opções."""
    if not SYMBOLS_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(SYMBOLS_PATH, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        logger.warning(f"[options_market] symbols: {e}")
        return pd.DataFrame()


def _load_rtd_options() -> pd.DataFrame:
    """Lê aba Opções do RTD PROFIT.xlsx."""
    if not RTD_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(RTD_PATH, sheet_name="Opções", header=0)
        df.columns = [str(c).strip() for c in df.columns]
        if "Asset" in df.columns:
            df["_ticker"] = df["Asset"].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        logger.warning(f"[options_market] RTD options: {e}")
        return pd.DataFrame()


def _load_rtd_diagnostic() -> pd.DataFrame:
    if not DIAGNOSTIC_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(DIAGNOSTIC_PATH, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        logger.warning(f"[options_market] diagnostic: {e}")
        return pd.DataFrame()


# ── DTE computation ──────────────────────────────────────────────────────────

def _compute_dte(vencimento: str) -> Optional[int]:
    if not vencimento:
        return None
    try:
        exp = datetime.strptime(str(vencimento)[:10], "%Y-%m-%d").date()
        delta = (exp - date.today()).days
        return max(0, delta)
    except Exception:
        return None


def _dte_category(dte: int) -> str:
    if dte <= 7:
        return "INTRA_SEMANA"
    if dte <= 23:
        return "CURTO"
    if dte <= 45:
        return "MEDIO"
    if dte <= 90:
        return "LONGO"
    return "MUITO_LONGO"


def _moneyness_cat(spot: float, strike: float) -> str:
    if spot is None or strike is None or strike == 0:
        return "N/A"
    ratio = spot / strike
    if ratio > 1.05:
        return "ITM"
    if ratio < 0.95:
        return "OTM"
    return "ATM"


def _spread_pct(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid and ask and bid > 0 and ask >= bid:
        return round((ask - bid) / bid * 100, 4)
    return None


# ── Option entry normalizer ─────────────────────────────────────────────────

def _normalize_option_entry(opt: dict[str, Any]) -> dict[str, Any]:
    """Normaliza campos legados (tipo/vencimento/ultimo_preco/ativo_objeto)
    para nomes padronizados (option_type/expiration_date/last_price/underlying).
    Mantém compatibilidade com ambas as convenções."""
    return {
        "ticker": opt.get("ticker", "") or opt.get("ticker_opcao", "") or "",
        "underlying": (
            opt.get("underlying", "")
            or opt.get("ativo_objeto", "")
            or opt.get("spot", "")
        ),
        "option_type": opt.get("option_type", "") or opt.get("tipo", "CALL"),
        "strike": _parse_br(opt.get("strike")),
        "expiration_date": opt.get("expiration_date") or opt.get("vencimento") or None,
        "dte": _parse_int(opt.get("dte")),
        "last_price": _parse_br(opt.get("last_price")) or _parse_br(opt.get("ultimo_preco")),
        "bid": _parse_br(opt.get("bid")),
        "ask": _parse_br(opt.get("ask")),
        "spread_pct": _parse_br(opt.get("spread_pct")),
        "volume": _parse_br(opt.get("volume")),
        "trades": opt.get("trades") or opt.get("negocios") or opt.get("negocios_media_5d"),
        "open_interest": _parse_br(opt.get("open_interest")),
        "implied_volatility": _parse_br(opt.get("implied_volatility")),
        "delta": _parse_br(opt.get("delta")),
        "gamma": _parse_br(opt.get("gamma")),
        "theta": _parse_br(opt.get("theta")),
        "rho": _parse_br(opt.get("rho")),
        "vega": _parse_br(opt.get("vega")),
        "moneyness": opt.get("moneyness", "") or opt.get("moneyness_cat", "N/A"),
        "liquidity_score": _parse_br(opt.get("liquidity_score")),
        "score": _parse_br(opt.get("score")),
        "cenario": opt.get("cenario") or None,
        "estruturas_sugeridas": opt.get("estruturas_sugeridas") or None,
        "status": opt.get("status", "UNKNOWN"),
        "motivo": opt.get("motivo") or None,
        "source": opt.get("source", "unknown"),
        "data_analise": opt.get("data_analise") or None,
    }


# ── Main functions ──────────────────────────────────────────────────────────

def get_options_chain_payload(
    underlying: str,
    expiration: str | None = None,
) -> dict[str, Any]:
    """
    Retorna cadeia de opções para um ativo objeto.

    Args:
        underlying: ticker do ativo objeto, ex: "PETR4", "PETR"
        expiration: vencimento específico YYYY-MM-DD (opcional)

    Returns:
        dict com: status, underlying, spot_price, expirations, calls, puts,
                 source, timestamp, diagnostic
    """
    underlying = _normalize_underlying(str(underlying or "").strip().upper())

    errors: list[str] = []
    for path, name in [
        (HISTORICAL_OPP_PATH, "historical"),
        (WATCHLIST_PATH, "watchlist"),
        (SYMBOLS_PATH, "symbols"),
        (RTD_PATH, "RTD"),
    ]:
        if not path.exists():
            errors.append(f"{name}: arquivo não encontrado ({path})")

    calls_data: list[dict[str, Any]] = []
    puts_data: list[dict[str, Any]] = []
    expirations_found: list[str] = []
    spot_price: Optional[float] = None

    # ── 1. Dados do RTD (Opções) — dados ao vivo ─────────────────────────
    df_rtd = _load_rtd_options()
    if not df_rtd.empty:
        # Filtrar por ativo objeto
        rtd_rows = df_rtd[
            df_rtd["_ticker"].str.startswith(underlying, na=False)
        ]
        for _, row in rtd_rows.iterrows():
            ticker = str(row.get("_ticker", "")).strip()
            strike = _parse_br(row.get("Strike"))
            venc_str = _parse_date(row.get("Validade") or row.get("Vencimento"))
            dte = _compute_dte(venc_str)
            bid = _parse_br(row.get("Of. Compra"))
            ask = _parse_br(row.get("Of. Venda"))
            ultimo = _parse_br(row.get("Último"))

            opt_entry = {
                "ticker": ticker,
                "option_type": _derive_option_type(ticker),
                "strike": strike,
                "expiration_date": venc_str,
                "dte": dte,
                "dte_category": _dte_category(dte) if dte else None,
                "last_price": ultimo,
                "bid": bid,
                "ask": ask,
                "spread_pct": _spread_pct(bid, ask),
                "volume": _parse_br(row.get("Volume")),
                "trades": _parse_int(row.get("Negócios")),
                "open_interest": None,
                "implied_volatility": _parse_br(row.get("Volt. Implícita")),
                "delta": _parse_br(row.get("Delta")),
                "gamma": _parse_br(row.get("Gama")),
                "theta": _parse_br(row.get("Theta")),
                "rho": _parse_br(row.get("Rho")),
                "vega": _parse_br(row.get("Vega")),
                "moneyness": _moneyness_cat(spot_price, strike) if spot_price and strike else "N/A",
                "liquidity_score": None,
                "status": "RTD_AO_VIVO" if (bid and ask) else "SEM_BIDASK",
                "source": "RTD PROFIT.xlsx",
                "raw_ticker": str(row.get("Asset", "")),
            }

            if venc_str and venc_str not in expirations_found:
                expirations_found.append(venc_str)

            if opt_entry["option_type"] == "CALL":
                calls_data.append(opt_entry)
            else:
                puts_data.append(opt_entry)

        # Obter spot do RTD (ação correspondente)
        if spot_price is None:
            spot_price = _parse_br(rtd_rows.iloc[0].get("Fechamento Anterior")) if len(rtd_rows) > 0 else None

    # ── 2. symbols CSV — mapeamento strike/vencimento ─────────────────────
    df_sym = _load_symbols()
    if not df_sym.empty:
        sym_rows = df_sym[
            df_sym["ativo_objeto"].str.upper() == underlying
        ]
        for _, row in sym_rows.iterrows():
            ticker = str(row.get("ticker", "")).strip()
            if any(t["ticker"] == ticker for t in calls_data + puts_data):
                continue  # já existe do RTD

            strike = _parse_br(row.get("strike"))
            venc_str = _parse_date(row.get("vencimento"))
            dte = _compute_dte(venc_str)
            opt_type = str(row.get("tipo", "")).upper()
            if opt_type not in ("CALL", "PUT"):
                opt_type = _derive_option_type(ticker)

            opt_entry = {
                "ticker": ticker,
                "option_type": opt_type,
                "strike": strike,
                "expiration_date": venc_str,
                "dte": dte,
                "dte_category": _dte_category(dte) if dte else None,
                "last_price": None,
                "bid": None,
                "ask": None,
                "spread_pct": None,
                "volume": None,
                "trades": None,
                "open_interest": None,
                "implied_volatility": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "rho": None,
                "vega": None,
                "moneyness": _moneyness_cat(spot_price, strike) if spot_price and strike else "N/A",
                "liquidity_score": None,
                "status": "SEM_DADOS_RTD",
                "source": "options_rtd_symbols.csv",
            }

            if venc_str and venc_str not in expirations_found:
                expirations_found.append(venc_str)

            if opt_type == "CALL":
                calls_data.append(opt_entry)
            else:
                puts_data.append(opt_entry)

    # ── 3. watchlist CSV — candidatas próximo pregão ─────────────────────
    df_wl = _load_watchlist()
    if not df_wl.empty:
        # normalizar ativo objeto na watchlist
        df_wl["_underlying"] = df_wl["ativo_objeto"].apply(
            lambda u: _normalize_underlying(str(u)) if str(u) not in ("nan", "") else ""
        )
        wl_rows = df_wl[df_wl["_underlying"] == underlying]
        for _, row in wl_rows.iterrows():
            ticker = str(row.get("ticker_opcao", "")).strip()
            if any(t["ticker"] == ticker for t in calls_data + puts_data):
                continue

            strike = _parse_br(row.get("strike"))
            venc_str = _parse_date(row.get("vencimento"))
            dte = _parse_int(row.get("dte"))
            opt_type = str(row.get("tipo", "")).upper()
            if opt_type not in ("CALL", "PUT"):
                opt_type = _derive_option_type(ticker)

            price = _parse_br(row.get("ultimo_preco"))
            liquidity = _parse_br(row.get("liquidez_score"))
            score = _parse_br(row.get("score"))
            status = str(row.get("status", ""))
            cenario = str(row.get("cenario", ""))
            estrategias = str(row.get("estruturas_sugeridas", ""))

            opt_entry = {
                "ticker": ticker,
                "option_type": opt_type,
                "strike": strike,
                "expiration_date": venc_str,
                "dte": dte,
                "dte_category": _dte_category(dte) if dte else None,
                "last_price": price,
                "bid": None,
                "ask": None,
                "spread_pct": None,
                "volume": None,
                "trades": None,
                "open_interest": None,
                "implied_volatility": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "rho": None,
                "vega": None,
                "moneyness": _moneyness_cat(spot_price, strike) if spot_price and strike else "N/A",
                "liquidity_score": liquidity,
                "score": score,
                "cenario": cenario,
                "estruturas_sugeridas": estrategias,
                "status": status or "MONITORAR_NO_RTD",
                "motivo": str(row.get("motivo", "")),
                "source": "options_next_session_watchlist.csv",
            }

            if venc_str and venc_str not in expirations_found:
                expirations_found.append(venc_str)

            if opt_type == "CALL":
                calls_data.append(opt_entry)
            else:
                puts_data.append(opt_entry)

    # ── 4. historical CSV — oportunidades históricas ─────────────────
    df_hist = _load_historical()
    if not df_hist.empty:
        df_hist["_underlying"] = df_hist["ativo_objeto"].apply(
            lambda u: _normalize_underlying(str(u)) if str(u) not in ("nan", "") else ""
        )
        hist_rows = df_hist[df_hist["_underlying"] == underlying]
        for _, row in hist_rows.iterrows():
            ticker = str(row.get("ticker_opcao", "")).strip()
            if any(t["ticker"] == ticker for t in calls_data + puts_data):
                continue

            strike = _parse_br(row.get("strike"))
            venc_str = _parse_date(row.get("vencimento"))
            dte = _parse_int(row.get("dte"))
            opt_type = str(row.get("tipo", "")).upper()
            if opt_type not in ("CALL", "PUT"):
                opt_type = _derive_option_type(ticker)

            opt_entry = {
                "ticker": ticker,
                "option_type": opt_type,
                "strike": strike,
                "expiration_date": venc_str,
                "dte": dte,
                "dte_category": _dte_category(dte) if dte else None,
                "last_price": _parse_br(row.get("ultimo_preco")),
                "bid": None,
                "ask": None,
                "spread_pct": None,
                "volume": _parse_br(row.get("vol_media_5d")),
                "trades": _parse_int(row.get("negocios_media_5d")),
                "open_interest": None,
                "implied_volatility": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "rho": None,
                "vega": None,
                "moneyness": str(row.get("moneyness_cat", "")),
                "liquidity_score": _parse_br(row.get("liquidez_score")),
                "score": _parse_br(row.get("score")),
                "cenario": str(row.get("cenario", "")),
                "estruturas_sugeridas": str(row.get("estruturas_sugeridas", "")),
                "status": str(row.get("status", "")),
                "motivo": str(row.get("motivo", "")),
                "data_analise": _parse_date(row.get("data_analise")),
                "source": "options_historical_opportunities.csv",
            }

            if venc_str and venc_str not in expirations_found:
                expirations_found.append(venc_str)

            if opt_type == "CALL":
                calls_data.append(opt_entry)
            else:
                puts_data.append(opt_entry)

    # Filtrar por vencimento se solicitado
    if expiration:
        calls_data = [c for c in calls_data if c["expiration_date"] and expiration in c["expiration_date"]]
        puts_data = [p for p in puts_data if p["expiration_date"] and expiration in p["expiration_date"]]
        expirations_found = [e for e in expirations_found if e and expiration in e]
    else:
        # Ordenar por vencimento
        calls_data.sort(key=lambda x: x.get("expiration_date") or "")
        puts_data.sort(key=lambda x: x.get("expiration_date") or "")

    expirations_found.sort()

    total_options = len(calls_data) + len(puts_data)
    has_live_data = any(c.get("bid") is not None for c in calls_data + puts_data) or any(
        p.get("bid") is not None for p in puts_data
    )

    return {
        "status": "ok" if total_options > 0 else "empty",
        "underlying": underlying,
        "spot_price": spot_price,
        "expirations": expirations_found,
        "calls_count": len(calls_data),
        "puts_count": len(puts_data),
        "calls": calls_data,
        "puts": puts_data,
        "total_options": total_options,
        "has_live_data": has_live_data,
        "source": "RTD PROFIT.xlsx + options CSVs",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_path": str(RTD_PATH),
            "rtd_exists": RTD_PATH.exists(),
            "historical_path": str(HISTORICAL_OPP_PATH),
            "historical_exists": HISTORICAL_OPP_PATH.exists(),
            "historical_rows": len(df_hist) if not df_hist.empty else 0,
            "watchlist_path": str(WATCHLIST_PATH),
            "watchlist_exists": WATCHLIST_PATH.exists(),
            "watchlist_rows": len(df_wl) if not df_wl.empty else 0,
            "symbols_path": str(SYMBOLS_PATH),
            "symbols_exists": SYMBOLS_PATH.exists(),
            "symbols_rows": len(df_sym) if not df_sym.empty else 0,
            "calls_found": len(calls_data),
            "puts_found": len(puts_data),
            "expirations_found": expirations_found,
            "data_type": "mixed_rtd_csv",
            "limitations": [
                "Dados RTD são do último pregão",
                "Historical CSVs são snapshots pontuais, não séries temporais",
                "Bid/ask só disponível para instrumentos no RTD",
                "Greeks só disponíveis para opções no RTD",
            ],
        },
    }


def get_option_history_payload(
    option_ticker: str,
    period: str = "6m",
) -> dict[str, Any]:
    """
    Retorna histórico de preço para uma opção específica.

    Como o histórico de opções não é uma série temporal contínua,
    retorna os dados disponíveis mais recentes para o ticker.

    Args:
        option_ticker: código da opção, ex: "ENEVR245", "BBDCF17"
        period: período desejado (1m/3m/6m/ytd) — usado como filtro se houver datas

    Returns:
        dict com: status, ticker, underlying, option_type, strike,
                  ohlcv_history, volume_history, summary, source, diagnostic
    """
    ticker = str(option_ticker or "").strip().upper()
    if not ticker:
        return _empty_option_payload("ticker vazio")

    underlying = _ticker_to_underlying(ticker)
    option_type = _derive_option_type(ticker)

    # Buscar em histórico CSV
    df_hist = _load_historical()
    records: list[dict[str, Any]] = []

    if not df_hist.empty:
        hist_rows = df_hist[df_hist["ticker_opcao"].str.upper() == ticker]
        for _, row in hist_rows.iterrows():
            strike = _parse_br(row.get("strike"))
            venc_str = _parse_date(row.get("vencimento"))
            dte = _parse_int(row.get("dte"))
            price = _parse_br(row.get("ultimo_preco"))
            vol_5d = _parse_br(row.get("vol_media_5d"))
            vol_10d = _parse_br(row.get("vol_media_10d"))
            vol_21d = _parse_br(row.get("vol_media_21d"))
            negocios = _parse_int(row.get("negocios_media_5d"))
            variacao_preco = _parse_br(row.get("variacao_preco"))
            retorno_5d = _parse_br(row.get("retorno_5d"))
            retorno_21d = _parse_br(row.get("retorno_21d"))
            retorno_63d = _parse_br(row.get("retorno_63d"))
            spot = _parse_br(row.get("spot"))
            data_analise = _parse_date(row.get("data_analise"))
            score = _parse_br(row.get("score"))
            status_val = str(row.get("status", ""))
            cenario = str(row.get("cenario", ""))
            estrategias = str(row.get("estruturas_sugeridas", ""))

            records.append({
                "date": data_analise,
                "last_price": price,
                "spot": spot,
                "strike": strike,
                "moneyness": _moneyness_cat(spot, strike) if spot and strike else "N/A",
                "dte": dte,
                "volume_5d": vol_5d,
                "volume_10d": vol_10d,
                "volume_21d": vol_21d,
                "negocios_5d": negocios,
                "variacao_preco": variacao_preco,
                "retorno_5d": retorno_5d,
                "retorno_21d": retorno_21d,
                "retorno_63d": retorno_63d,
                "score": score,
                "status": status_val,
                "cenario": cenario,
                "estruturas_sugeridas": estrategias,
            })

    # Buscar em watchlist
    df_wl = _load_watchlist()
    if not df_wl.empty:
        wl_rows = df_wl[df_wl["ticker_opcao"].str.upper() == ticker]
        for _, row in wl_rows.iterrows():
            strike = _parse_br(row.get("strike"))
            venc_str = _parse_date(row.get("vencimento"))
            dte = _parse_int(row.get("dte"))
            price = _parse_br(row.get("ultimo_preco"))
            spot = None  # não disponível na watchlist
            liquidity = _parse_br(row.get("liquidez_score"))
            score = _parse_br(row.get("score"))
            status_val = str(row.get("status", ""))
            cenario = str(row.get("cenario", ""))
            estrategias = str(row.get("estruturas_sugeridas", ""))

            records.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "last_price": price,
                "spot": spot,
                "strike": strike,
                "moneyness": _moneyness_cat(spot, strike) if spot and strike else "N/A",
                "dte": dte,
                "volume_5d": None,
                "volume_10d": None,
                "volume_21d": None,
                "negocios_5d": None,
                "variacao_preco": None,
                "retorno_5d": None,
                "retorno_21d": None,
                "retorno_63d": None,
                "score": score,
                "liquidity_score": liquidity,
                "status": status_val,
                "cenario": cenario,
                "estruturas_sugeridas": estrategias,
            })

    # Buscar em RTD
    df_rtd = _load_rtd_options()
    if not df_rtd.empty:
        rtd_rows = df_rtd[df_rtd["_ticker"].str.upper() == ticker]
        if not rtd_rows.empty:
            row = rtd_rows.iloc[0]
            strike = _parse_br(row.get("Strike"))
            venc_str = _parse_date(row.get("Validade") or row.get("Vencimento"))
            ultimo = _parse_br(row.get("Último"))
            bid = _parse_br(row.get("Of. Compra"))
            ask = _parse_br(row.get("Of. Venda"))
            volume = _parse_br(row.get("Volume"))
            negocios = _parse_int(row.get("Negócios"))
            iv = _parse_br(row.get("Volt. Implícita"))
            delta = _parse_br(row.get("Delta"))
            gamma = _parse_br(row.get("Gama"))
            theta = _parse_br(row.get("Theta"))
            vega = _parse_br(row.get("Vega"))

            records.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "last_price": ultimo,
                "bid": bid,
                "ask": ask,
                "strike": strike,
                "vencimento": venc_str,
                "dte": _compute_dte(venc_str),
                "volume": volume,
                "trades": negocios,
                "implied_volatility": iv,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "status": "RTD_AO_VIVO",
            })

    # Deduplicar por data (manter o mais recente)
    seen_dates: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for rec in reversed(records):
        d = rec.get("date", "")
        if d not in seen_dates:
            seen_dates.add(d)
            deduped.append(rec)
    deduped.sort(key=lambda x: x.get("date") or "")

    if not deduped:
        return _empty_option_payload(f"ticker {ticker} não encontrado em nenhuma fonte")

    # Summary
    prices_for_summary = [r["last_price"] for r in deduped if r.get("last_price") is not None]
    summary = {
        "record_count": len(deduped),
        "earliest_date": deduped[0].get("date") if deduped else None,
        "latest_date": deduped[-1].get("date") if deduped else None,
        "current_price": deduped[-1].get("last_price") if deduped else None,
        "max_price": max(prices_for_summary) if prices_for_summary else None,
        "min_price": min(prices_for_summary) if prices_for_summary else None,
        "avg_price": round(sum(prices_for_summary) / len(prices_for_summary), 4) if prices_for_summary else None,
        "latest_score": deduped[-1].get("score") if deduped else None,
        "latest_status": deduped[-1].get("status") if deduped else None,
    }

    return {
        "status": "ok",
        "ticker": ticker,
        "underlying": underlying,
        "option_type": option_type,
        "period": period,
        "records": deduped,
        "summary": summary,
        "source": "RTD PROFIT.xlsx + options CSVs",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "ticker": ticker,
            "records_found": len(deduped),
            "sources_used": [
                "options_historical_opportunities.csv" if not df_hist.empty else "",
                "options_next_session_watchlist.csv" if not df_wl.empty else "",
                "RTD PROFIT.xlsx" if not df_rtd.empty else "",
            ],
            "data_type": "mixed_snapshot",
            "note": "Registros são snapshots de datas diferentes. Não é série temporal contínua.",
        },
    }


def get_options_radar_payload(
    underlying: str | None = None,
    limit_candidates: int = 200,
    limit_monitor: int = 100,
) -> dict[str, Any]:
    """
    Retorna radar de oportunidades de opções.

    Args:
        underlying: filtro por ativo objeto (opcional)

    Returns:
        dict com: status, total, candidates, monitor_rtd, next_session,
                  by_status, by_underlying, source, timestamp, diagnostic
    """
    df_hist = _load_historical()
    df_wl = _load_watchlist()
    df_sym = _load_symbols()
    df_diag = _load_rtd_diagnostic()

    # ── Unificar em uma lista plana ───────────────────────────────
    all_options: list[dict[str, Any]] = []

    def _safe_row(row: dict, *keys) -> Any:
        for k in keys:
            if k in row:
                return row[k]
        return None

    # Historical
    if not df_hist.empty:
        for _, row in df_hist.iterrows():
            u = str(row.get("ativo_objeto", "")).strip()
            if underlying and _normalize_underlying(u) != underlying.upper() and u.upper() != underlying.upper():
                continue
            all_options.append({
                "ativo_objeto": u,
                "ticker": str(row.get("ticker_opcao", "")).strip(),
                "tipo": str(row.get("tipo", "")).upper(),
                "strike": _parse_br(row.get("strike")),
                "vencimento": _parse_date(row.get("vencimento")),
                "dte": _parse_int(row.get("dte")),
                "ultimo_preco": _parse_br(row.get("ultimo_preco")),
                "spot": _parse_br(row.get("spot")),
                "moneyness": str(row.get("moneyness_cat", "N/A")),
                "liquidez_score": _parse_br(row.get("liquidez_score")),
                "score": _parse_br(row.get("score")),
                "status": str(row.get("status", "")),
                "cenario": str(row.get("cenario", "")),
                "estruturas_sugeridas": str(row.get("estruturas_sugeridas", "")),
                "motivo": str(row.get("motivo", "")),
                "data_analise": _parse_date(row.get("data_analise")),
                "source": "historical",
            })

    # Watchlist
    if not df_wl.empty:
        for _, row in df_wl.iterrows():
            u = str(row.get("ativo_objeto", "")).strip()
            if underlying and _normalize_underlying(u) != underlying.upper() and u.upper() != underlying.upper():
                continue
            all_options.append({
                "ativo_objeto": u,
                "ticker": str(row.get("ticker_opcao", "")).strip(),
                "tipo": str(row.get("tipo", "")).upper(),
                "strike": _parse_br(row.get("strike")),
                "vencimento": _parse_date(row.get("vencimento")),
                "dte": _parse_int(row.get("dte")),
                "ultimo_preco": _parse_br(row.get("ultimo_preco")),
                "spot": None,
                "moneyness": "N/A",
                "liquidez_score": _parse_br(row.get("liquidez_score")),
                "score": _parse_br(row.get("score")),
                "status": str(row.get("status", "")),
                "cenario": str(row.get("cenario", "")),
                "estruturas_sugeridas": str(row.get("estruturas_sugeridas", "")),
                "motivo": str(row.get("motivo", "")),
                "data_analise": None,
                "source": "watchlist",
            })

    # Symbols
    if not df_sym.empty:
        for _, row in df_sym.iterrows():
            u = str(row.get("ativo_objeto", "")).strip()
            ticker = str(row.get("ticker", "")).strip()
            if underlying and u.upper() != underlying.upper():
                continue
            all_options.append({
                "ativo_objeto": u,
                "ticker": ticker,
                "tipo": str(row.get("tipo", "")).upper(),
                "strike": _parse_br(row.get("strike")),
                "vencimento": _parse_date(row.get("vencimento")),
                "dte": _compute_dte(_parse_date(row.get("vencimento"))),
                "ultimo_preco": None,
                "spot": None,
                "moneyness": "N/A",
                "liquidez_score": None,
                "score": None,
                "status": "NA_RTD",
                "cenario": None,
                "estruturas_sugeridas": None,
                "motivo": f"Disponível no RTD: {ticker}",
                "data_analise": None,
                "source": "symbols",
            })

    if not all_options:
        return {
            "status": "ok",
            "total": 0,
            "underlying_filter": underlying,
            "options": [],
            "by_status": {},
            "by_underlying": {},
            "source": "options CSVs",
            "timestamp": datetime.utcnow().isoformat(),
            "diagnostic": {
                "note": "Nenhuma opção encontrada nas fontes disponíveis",
                "underlying_filter": underlying,
                "data_available": bool(df_hist.empty and df_wl.empty and df_sym.empty),
            },
        }

    # Aggregations
    by_status: dict[str, int] = {}
    by_underlying: dict[str, dict] = {}
    candidates_next: list[dict] = []
    monitor_rtd: list[dict] = []
    aguardare: list[dict] = []

    for opt in all_options:
        status = opt.get("status", "")
        u_actual = opt.get("ativo_objeto", "")

        # Normalize before aggregation so filters/consumption use standardized fields
        normed = _normalize_option_entry(opt)

        # By status
        if status not in by_status:
            by_status[status] = 0
        by_status[status] += 1

        # By underlying
        if u_actual not in by_underlying:
            by_underlying[u_actual] = {"total": 0, "calls": 0, "puts": 0, "calls_list": [], "puts_list": []}
        by_underlying[u_actual]["total"] += 1
        if normed.get("option_type") == "CALL":
            by_underlying[u_actual]["calls"] += 1
            by_underlying[u_actual]["calls_list"].append(normed)
        else:
            by_underlying[u_actual]["puts"] += 1
            by_underlying[u_actual]["puts_list"].append(normed)

        if status == "CANDIDATA_PROXIMO_PREGAO":
            candidates_next.append(normed)
        elif status == "MONITORAR_NO_RTD":
            monitor_rtd.append(normed)
        elif status in ("AGUARDAR_LIQUIDEZ", "DESCARTAR"):
            aguardare.append(normed)

    # Diagnostic CSV
    diag_info: dict[str, Any] = {}
    if not df_diag.empty:
        for _, row in df_diag.iterrows():
            ativo = str(row.get("ativo", "")).strip().upper()
            diag_info[ativo] = {
                "spot": _parse_br(row.get("spot")),
                "limite": _parse_int(row.get("limite")),
                "com_liquidez": _parse_int(row.get("com_liquidez")),
                "oportunidades": _parse_int(row.get("oportunidades")),
                "status": str(row.get("status", "")),
            }

    # Sort candidates by score desc, then limit
    candidates_next.sort(key=lambda x: x.get("score") or 0, reverse=True)
    monitor_rtd.sort(key=lambda x: x.get("score") or 0, reverse=True)

    # Limit by_underlying lists for payload size
    by_underlying_limited: dict[str, dict] = {}
    for u_key, u_data in by_underlying.items():
        by_underlying_limited[u_key] = {
            "total":      u_data["total"],
            "calls":      u_data["calls"],
            "puts":       u_data["puts"],
            "calls_list": u_data["calls_list"][:10],
            "puts_list":  u_data["puts_list"][:10],
        }

    return {
        "status": "ok",
        "total": len(all_options),
        "underlying_filter": underlying,
        "by_status": by_status,
        "by_underlying": by_underlying_limited,
        "candidates_next_session": candidates_next[:limit_candidates],
        "monitor_rtd": monitor_rtd[:limit_monitor],
        "aguardar_liquidez": aguardare[:50],
        "total_candidates": len(candidates_next),
        "total_monitor_rtd": len(monitor_rtd),
        "rtd_diagnostic": diag_info,
        "source": "options CSVs",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {
            "rtd_exists": RTD_PATH.exists(),
            "historical_exists": HISTORICAL_OPP_PATH.exists(),
            "watchlist_exists": WATCHLIST_PATH.exists(),
            "symbols_exists": SYMBOLS_PATH.exists(),
            "total_raw_records": len(all_options),
            "unique_underlyings": list(by_underlying.keys()),
            "limit_candidates": limit_candidates,
            "limit_monitor": limit_monitor,
            "data_type": "mixed_snapshot",
            "limitations": [
                "Dados são snapshots pontuais, não séries temporais",
                "Bid/ask só disponível para opções no RTD",
                "Spot price pode ser None para registros watchlist/symbols",
                "Listas limitadas para performance — total_candidates/total_monitor_rtd refletem contagem real",
            ],
        },
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_option_payload(reason: str) -> dict[str, Any]:
    return {
        "status": "error",
        "ticker": "",
        "underlying": "",
        "option_type": "",
        "period": "",
        "records": [],
        "summary": {},
        "error": reason,
        "source": "options CSVs",
        "timestamp": datetime.utcnow().isoformat(),
        "diagnostic": {"reason": reason},
    }
