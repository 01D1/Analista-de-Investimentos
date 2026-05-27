"""
RTD Live Reader — Unified RTD Reader
====================================
Lê data/realtime/RTD PROFIT.xlsx e retorna payload padronizado.

Regras de classificação (OPCAO tem PRIORIDADE sobre ACAO):
  1. Opções: ticker em watchlist OU padrão F/W/DIGIT no final OU em options_rtd_symbols
  2. Futuros: padrões WINFUT, WDOFUT, DOLFUT, DI1FUT, IND, DOL, WIN, WDO
  3. Índice: IBOV, IBOVX100 e similares
  4. Ação: terminam em 3/4/5/6/11 OU estão na watchlist de ações
  5. Outro: caso restante

Payload por instrumento:
  - ticker, classe, preço, variação, volume, negócios,
    bid, ask, spread, spread_pct, VWAP,
    RSI, MACD, ADX, Bollinger, HiLo,
    timestamp_leitura, status_dado, aba_origem

Uso:
    from src.dashboard.rtd_live_reader import RTDLiveReader
    reader = RTDLiveReader()
    payload = reader.read_all()
"""

from __future__ import annotations

import time
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[2]
RTD_PATH = SCANNER_ROOT / "data" / "realtime" / "RTD PROFIT.xlsx"
SHORTLIST_PATH = SCANNER_ROOT / "data" / "realtime" / "options_rtd_watchlist.csv"
SYMBOLS_PATH = SCANNER_ROOT / "data" / "realtime" / "options_rtd_symbols.csv"


# ── Enums ────────────────────────────────────────────────────────────────────


class InstrumentClass(str, Enum):
    ACAO = "ACAO"
    OPCAO = "OPCAO"
    FUTURO = "FUTURO"
    INDICE = "INDICE"
    OUTRO = "OUTRO"


class DataStatus(str, Enum):
    AO_VIVO = "AO_VIVO"
    SEM_PRECO = "SEM_PRECO"
    SEM_BID_ASK = "SEM_BID_ASK"
    STALE = "STALE"
    NAO_CONFIGURADO = "NAO_CONFIGURADO"
    ERRO_LEITURA = "ERRO_LEITURA"


# ── Payload ──────────────────────────────────────────────────────────────────


@dataclass
class InstrumentPayload:
    ticker: str
    classe: InstrumentClass = InstrumentClass.OUTRO
    nome: str = ""
    preco: Optional[float] = None
    variacao: Optional[float] = None  # pct
    volume: Optional[float] = None
    negocios: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    spread_pct: Optional[float] = None
    vwap: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    adx: Optional[float] = None
    boll_b: Optional[float] = None
    hilo: Optional[float] = None
    strike: Optional[float] = None
    vencimento: str = ""
    ativo_objeto: str = ""
    tipo_opcao: str = ""  # CALL / PUT
    timestamp: str = ""
    status: DataStatus = DataStatus.ERRO_LEITURA
    raw_row: dict = field(default_factory=dict)
    aba_origem: str = ""  # de qual aba veio

    def to_dict(self) -> dict:
        d = asdict(self)
        d["classe"] = self.classe.value
        d["status"] = self.status.value
        return d


# ── Parse helpers ─────────────────────────────────────────────────────────────


def _parse_br(value) -> Optional[float]:
    """Converte '53,00' ou '1.234,56' ou float/int para float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            v = float(value)
            return None if (v != v) else v
        except Exception:
            return None
    s = str(value).strip()
    if s in ("-", "", "nan", "None", "NaN"):
        return None
    s = s.replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


# ── Ticker classification ─────────────────────────────────────────────────────


class TickerClassifier:
    """
    Regras de classificação por ticker (OPCAO > FUTURO > INDICE > ACAO > OUTRO).
    A regra OPCAO é aplicadas ANTES de ACAO para evitar que PETRF469 vire ação.
    """

    # Padrões de sufixo de opção (F = opção normal, W = warrant, D = days)
    # Ex: PETRF469, ITUBF404, VALEF856, ENEVR250, BBASF123
    OPTION_SUFFIX_PATTERNS = (
        # LETRA(s) + F + 3 dígitos (padrão brasileiro)
        re.compile(r"^[A-Z]{2,5}F\d{3}$"),
        # LETRA(s) + W + 3 dígitos (warrant)
        re.compile(r"^[A-Z]{2,5}W\d{3}$"),
        # LETRA(s) + D + 3 dígitos
        re.compile(r"^[A-Z]{2,5}D\d{3}$"),
        # Ações brasileiras + F + strike (2-4 dígitos)
        re.compile(r"^[A-Z]{4,6}F\d{2,4}$"),
        # Ações americanas + F + strike
        re.compile(r"^[A-Z]{1,4}F\d{2,4}$"),
    )

    # Padrões de futuros (comum em RTD PROFIT brasileiro)
    FUTURO_PREFIXES = {"WDO", "DOL", "WIN", "IND", "DI1"}
    FUTURO_TOKENS = {
        "WDOFUT",
        "DOLFUT",
        "WINFUT",
        "DDI1FUT",
        "DI1FUT",
        "DOLFUTP",
        "DOLFWN",
    }

    # Índice
    INDICE_TOKERS = {
        "IBOV",
        "IBOVX100",
        "IBRA",
        "SMLL",
        "IFNC",
        "ICON",
        "IDIV",
        "IFIX",
        "IMOB",
        "UTIL",
        "MATER",
        "IBOVX250",
        "IBRXP",
        "IDIVX100",
    }
    INDICE_PREFIXES = (
        "IBOV",
        "IND",
        "SMLL",
        "IFIX",
        "IMOB",
        "UTIL",
        "MATER",
        "ICON",
        "IDIV",
    )

    # Ação: tickers que terminam com o número do tipo de ação na B3
    ACAO_TERMINATIONS = {"3", "4", "5", "6", "11"}

    def __init__(self, option_tickers: set[str], option_info: dict[str, dict]):
        self._opt_tickers = option_tickers
        self._opt_info = option_info

    def classify(self, ticker: str) -> InstrumentClass:
        t = str(ticker or "").strip().upper()

        # 1. shortlist de opções (prioridade máxima)
        if t in self._opt_tickers or t in self._opt_info:
            return InstrumentClass.OPCAO

        # 2. padrões de sufixo de opção (ANTES de ação)
        for pat in self.OPTION_SUFFIX_PATTERNS:
            if pat.match(t):
                return InstrumentClass.OPCAO

        # 3. futuros
        if t in self.FUTURO_TOKENS:
            return InstrumentClass.FUTURO
        if any(t.startswith(p) for p in self.FUTURO_PREFIXES):
            # WDO, DOL, WIN, IND, DI1 + sufixo (ex: WDOJ26, DOLM26, WINV26)
            if len(t) >= 5 and any(c.isalpha() for c in t):
                return InstrumentClass.FUTURO

        # 4. índices
        if t in self.INDICE_TOKERS:
            return InstrumentClass.INDICE
        if t.startswith(self.INDICE_PREFIXES):
            return InstrumentClass.INDICE

        # 5. ações: terminam em 3/4/5/6/11 (ações ON/PN na B3)
        if t[-2:] in ("11",) or t[-1:] in ("3", "4", "5", "6"):
            return InstrumentClass.ACAO

        # 6. prefixos conhecidos de ações (para segurança adicional)
        ACAO_PREFIXES = (
            "PETR",
            "VALE",
            "ITUB",
            "BBDC",
            "ABEV",
            "JBSS",
            "HAPV",
            "EGIE",
            "TAEE",
            "ALUP",
            "SAPR",
            "TRPL",
            "CPFE",
            "CMIG",
            "ENBR",
            "NEOE",
            "BBAS",
            "ITSA",
            "WEGE",
            "WEG",
            "KLBN",
            "CSNA",
            "USIM",
            "GGBR",
            "GOAU",
            "PNVL",
            "MGLU",
            "LWSA",
            "CASH",
            "FLRY",
            "HAPV",
            "RDOR",
            "DASA",
            "GNDI",
            "QUAL",
            "LREN",
            "MAGN",
            "VAMO",
            "PETZ",
            "CVCB",
            "COGN",
            "SEER",
            "CYRE",
            "MRVE",
            "TEND",
            "EVEN",
            "JZTL",
            "DIRR",
            "BSLI",
        )
        if any(t.startswith(p) for p in ACAO_PREFIXES):
            return InstrumentClass.ACAO

        # 7. restante = OUTRO
        return InstrumentClass.OUTRO


# ── RTD Live Reader ────────────────────────────────────────────────────────────


class RTDLiveReader:
    """
    Lê o RTD PROFIT.xlsx e retorna dict de InstrumentPayload por ticker.
    Leitura: ~0.5–1s para arquivo típico. Timeout: 10s.
    Classificação: OPCAO > FUTURO > INDICE > ACAO > OUTRO
    """

    def __init__(
        self,
        rtd_path: Path = RTD_PATH,
        shortlist: Optional[Path] = SHORTLIST_PATH,
        symbols_path: Optional[Path] = SYMBOLS_PATH,
        timeout: int = 10,
    ):
        self.rtd_path = rtd_path
        self.shortlist = shortlist
        self.symbols_path = symbols_path
        self.timeout = timeout
        self._option_tickers: set[str] = set()
        self._option_info: dict[str, dict] = {}
        self._symbols_tickers: set[str] = set()
        self._read_sheets: list[str] = []  # abas lidas com sucesso
        self._load_shortlist()

    # ── Load shortlist ───────────────────────────────────────────────────────

    def _load_shortlist(self) -> None:
        """Lê watchlist e symbols de opções uma vez."""
        # options_rtd_watchlist.csv
        if self.shortlist and self.shortlist.exists():
            try:
                df = pd.read_csv(self.shortlist, dtype=str)
                df.columns = [c.strip() for c in df.columns]
                self._option_tickers = set(
                    str(v).strip()
                    for v in df["ticker"].dropna().tolist()
                    if str(v).strip()
                )
                for _, row in df.iterrows():
                    t = str(row.get("ticker", "")).strip()
                    if t:
                        self._option_info[t] = {
                            "ativo_objeto": str(row.get("ativo_objeto", "")),
                            "tipo": str(row.get("tipo", "")),
                            "strike": _parse_br(row.get("strike")),
                            "vencimento": str(row.get("vencimento", "")),
                        }
            except Exception:
                self._option_tickers = set()
                self._option_info = {}

        # options_rtd_symbols.csv (extra source)
        if self.symbols_path and self.symbols_path.exists():
            try:
                df_s = pd.read_csv(self.symbols_path, dtype=str)
                df_s.columns = [c.strip() for c in df_s.columns]
                self._symbols_tickers = set(
                    str(v).strip()
                    for v in df_s["ticker"].dropna().tolist()
                    if str(v).strip()
                )
                # Unir com watchlist
                self._option_tickers.update(self._symbols_tickers)
            except Exception:
                pass

    # ── Classify ───────────────────────────────────────────────────────────

    def _classifier(self) -> TickerClassifier:
        return TickerClassifier(self._option_tickers, self._option_info)

    def _classify(self, ticker: str) -> InstrumentClass:
        return self._classifier().classify(ticker)

    # ── Data status ────────────────────────────────────────────────────────

    def _status(self, row: dict) -> DataStatus:
        preco = _parse_br(row.get("Último")) or _parse_br(row.get("Último"))
        bid = _parse_br(row.get("Of. Compra")) or _parse_br(row.get("Bid"))
        ask = _parse_br(row.get("Of. Venda")) or _parse_br(row.get("Ask"))

        if preco is None:
            return DataStatus.SEM_PRECO
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            return DataStatus.SEM_BID_ASK
        return DataStatus.AO_VIVO

    # ── Read all ───────────────────────────────────────────────────────────

    def read_all(self) -> dict[str, InstrumentPayload]:
        """
        Lê TODAS as abas do RTD e retorna dict {ticker: InstrumentPayload}.
        Classificação é feita por ticker, não por aba — opções podem estar
        na aba Ações junto com ações e futuros.
        """
        if not self.rtd_path.exists():
            return {}

        t0 = time.time()
        results: dict[str, InstrumentPayload] = {}
        self._read_sheets = []

        try:
            sheets = pd.read_excel(self.rtd_path, sheet_name=None, header=0)
            for sheet_name, df_raw in sheets.items():
                self._read_sheets.append(sheet_name)
                self._parse_sheet(df_raw, results, sheet_name, time.time() - t0)
        except Exception:
            try:
                df_raw = pd.read_excel(self.rtd_path, sheet_name=0, header=0)
                self._read_sheets.append("Planilha1")
                self._parse_sheet(df_raw, results, "Planilha1", time.time() - t0)
            except Exception:
                pass

        return results

    # ── Parse sheet ────────────────────────────────────────────────────────

    def _parse_sheet(
        self,
        df_raw: pd.DataFrame,
        results: dict[str, InstrumentPayload],
        sheet_name: str,
        read_time: float,
    ):
        """Parseia uma aba do RTD."""
        df = df_raw.copy()
        df.columns = [str(c).strip() for c in df.columns]

        # Identificar coluna de ticker
        ticker_col = None
        for col in ["Asset", "Ticker", "Ativo", "Código", "CODIGO"]:
            if col in df.columns:
                ticker_col = col
                break

        if ticker_col is None:
            ticker_col = df.columns[0]

        df = df[
            df[ticker_col].notna() & (df[ticker_col].astype(str).str.strip().ne(""))
        ]
        df[ticker_col] = df[ticker_col].astype(str).str.strip()

        col_idx = {c: i for i, c in enumerate(df.columns)}
        values = df.values
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clf = self._classifier()

        for row_vals in values:
            ticker = str(row_vals[col_idx.get(ticker_col, 0)]).strip()
            if not ticker or ticker == "nan":
                continue
            if ticker in results:
                # Atualizar aba_origem se a entrada já existe (sobrescrever
                # para marcar a aba mais relevante, mas nunca perder a orig.)
                existing = results[ticker]
                if not existing.aba_origem:
                    results[ticker] = InstrumentPayload(
                        **{**asdict(existing), "aba_origem": sheet_name}
                    )
                continue

            row = {
                c: row_vals[col_idx[c]] for c in col_idx if col_idx[c] < len(row_vals)
            }

            preco = _parse_br(row.get("Último"))
            bid = _parse_br(row.get("Of. Compra")) or _parse_br(row.get("Bid"))
            ask = _parse_br(row.get("Of. Venda")) or _parse_br(row.get("Ask"))
            spread = (
                round(ask - bid, 4) if (bid and ask and bid > 0 and ask > 0) else None
            )
            spread_pct = (
                round((ask - bid) / bid * 100, 4)
                if spread is not None and bid and bid > 0
                else None
            )

            variacao = _parse_br(row.get("Variação")) or _parse_br(
                row.get("Variação(pts)")
            )
            volume = _parse_br(row.get("Volume")) or _parse_br(row.get("Quantidade"))
            negocios = _parse_br(row.get("Negócios")) or _parse_br(row.get("Negocio"))
            vwap = _parse_br(row.get("VWAP"))
            rsi = _parse_br(row.get("IFR (RSI)"))
            macd = _parse_br(row.get("MACD Histograma"))
            adx = _parse_br(row.get("ADX"))
            boll = _parse_br(row.get("Bollinger b%"))
            hilo = _parse_br(row.get("HiLo Activator"))
            strike = _parse_br(row.get("Strike")) or _parse_br(row.get("strike"))
            nome = str(row.get("Nome do Ativo", ""))

            status = self._status(row)

            # Classificação (OPCAO tem prioridade sobre ACAO)
            classe = clf.classify(ticker)

            # Info de opção
            opt_info = self._option_info.get(ticker, {})
            ativo_objeto = opt_info.get("ativo_objeto", "")
            tipo_opcao = opt_info.get("tipo", "")
            vencimento = opt_info.get("vencimento", "")

            # Se não tem info da shortlist mas é OPCAO, derivar do ticker
            if not ativo_objeto and classe == InstrumentClass.OPCAO:
                ativo_objeto = ticker[:4]

            results[ticker] = InstrumentPayload(
                ticker=ticker,
                classe=classe,
                nome=nome,
                preco=preco,
                variacao=variacao,
                volume=volume,
                negocios=negocios,
                bid=bid,
                ask=ask,
                spread=spread,
                spread_pct=spread_pct,
                vwap=vwap,
                rsi=rsi,
                macd=macd,
                adx=adx,
                boll_b=boll,
                hilo=hilo,
                strike=strike,
                vencimento=vencimento,
                ativo_objeto=ativo_objeto,
                tipo_opcao=tipo_opcao,
                timestamp=timestamp_str,
                status=status,
                raw_row=row,
                aba_origem=sheet_name,
            )

    # ── Read by class ────────────────────────────────────────────────────

    def read_acoes(self) -> dict[str, InstrumentPayload]:
        return {
            t: p for t, p in self.read_all().items() if p.classe == InstrumentClass.ACAO
        }

    def read_opcoes(self) -> dict[str, InstrumentPayload]:
        return {
            t: p
            for t, p in self.read_all().items()
            if p.classe == InstrumentClass.OPCAO
        }

    def read_futuros(self) -> dict[str, InstrumentPayload]:
        return {
            t: p
            for t, p in self.read_all().items()
            if p.classe == InstrumentClass.FUTURO
        }

    def read_indices(self) -> dict[str, InstrumentPayload]:
        return {
            t: p
            for t, p in self.read_all().items()
            if p.classe == InstrumentClass.INDICE
        }

    # ── Summary ───────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Retorna KPIs agregados + diagnóstico por aba."""
        all_inst = self.read_all()
        if not all_inst:
            return {}

        by_class = {}
        for classe in InstrumentClass:
            insts = [p for p in all_inst.values() if p.classe == classe]
            by_class[classe.value] = {
                "total": len(insts),
                "ao_vivo": sum(1 for p in insts if p.status == DataStatus.AO_VIVO),
                "sem_preco": sum(1 for p in insts if p.status == DataStatus.SEM_PRECO),
                "sem_bidask": sum(
                    1 for p in insts if p.status == DataStatus.SEM_BID_ASK
                ),
            }

        # Origem das classes
        class_origins: dict[str, dict[str, int]] = {}
        for ticker, p in all_inst.items():
            aba = p.aba_origem or "desconhecida"
            cls_key = p.classe.value
            if cls_key not in class_origins:
                class_origins[cls_key] = {}
            class_origins[cls_key][aba] = class_origins[cls_key].get(aba, 0) + 1

        return {
            "total": len(all_inst),
            "by_class": by_class,
            "class_origins": class_origins,
            "ao_vivo": sum(
                1 for p in all_inst.values() if p.status == DataStatus.AO_VIVO
            ),
            "sem_preco": sum(
                1 for p in all_inst.values() if p.status == DataStatus.SEM_PRECO
            ),
            "sem_bidask": sum(
                1 for p in all_inst.values() if p.status == DataStatus.SEM_BID_ASK
            ),
            "option_count": len(self._option_tickers),
            "read_sheets": self._read_sheets,
        }


# ── Singleton accessor ────────────────────────────────────────────────────────

_reader: Optional[RTDLiveReader] = None


def get_reader() -> RTDLiveReader:
    global _reader
    if _reader is None:
        _reader = RTDLiveReader()
    return _reader


def read_all() -> dict[str, InstrumentPayload]:
    return get_reader().read_all()
