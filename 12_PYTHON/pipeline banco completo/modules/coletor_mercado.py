"""
Módulo 02 — Coletor de Dados de Mercado
Busca preços, cotações, volumes e dados para cálculo de beta.

Fonte principal: COTAHIST local (SQLite — scanner_quant.db)
Fonte alternativa: yfinance (Yahoo Finance)
Terceira opção: B3 (scraping público via Fundamentus)
"""

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

logger = logging.getLogger("pipeline.mercado")

# Caminho padrão para o banco COTAHIST do scanner_quant.
# Resolvido em relação ao diretório deste arquivo:
# modules/ → pipeline banco completo/ → 12_PYTHON/ → OBSIDIAN/ → scanner_quant_profit_b3/
_DEFAULT_COTAHIST_DB = (
    Path(__file__).parent.parent.parent.parent
    / "scanner_quant_profit_b3"
    / "data"
    / "database"
    / "scanner_quant.db"
)

# Máximo de dias úteis de atraso tolerados antes de considerar dado COTAHIST como stale.
_COTAHIST_MAX_STALE_BDAYS = 5


class ColetorMercado:
    """Coleta dados de mercado: preços, beta, market cap, múltiplos."""

    IBOV_TICKER   = "^BVSP"
    SUFIXO_B3     = ".SA"
    JANELA_BETA   = 252   # dias úteis (1 ano)
    MIN_PONTOS    = 60    # mínimo de pontos para calcular beta

    def __init__(self, cache_dir: Path, usar_cache: bool = True,
                 cotahist_db: Optional[Path] = None):
        self.cache_dir  = Path(cache_dir)
        self.usar_cache = usar_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict = {}
        # Resolve COTAHIST DB path — falls back to default if not supplied.
        self.cotahist_db = Path(cotahist_db) if cotahist_db else _DEFAULT_COTAHIST_DB

    # ── COTAHIST (SQLite local) ───────────────────────────────────────────────

    @staticmethod
    def _strip_sa(ticker: str) -> str:
        """Remove .SA suffix so COTAHIST tickers match (e.g. WEGE3.SA → WEGE3)."""
        t = ticker.upper().strip()
        if t.endswith(".SA"):
            t = t[:-3]
        return t

    @staticmethod
    def _bdays_since(trade_date_str: str) -> int:
        """Return the number of business days between trade_date_str and today."""
        try:
            last = datetime.strptime(trade_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return 9999
        today = datetime.today().date()
        if last >= today:
            return 0
        # Count weekdays only (no holiday calendar — conservative approximation)
        bdays = 0
        current = last
        while current < today:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Mon–Fri
                bdays += 1
        return bdays

    def _get_price_from_cotahist(
        self, ticker_b3: str
    ) -> Optional[Tuple[float, str]]:
        """
        Query COTAHIST SQLite for the latest close price of *ticker_b3*.

        Args:
            ticker_b3: B3 ticker with or without .SA suffix.

        Returns:
            (close_price, trade_date_str) if data exists and is not stale,
            None otherwise.
        """
        if not self.cotahist_db.exists():
            logger.debug("[cotahist_local] DB não encontrado: %s", self.cotahist_db)
            return None

        ticker_plain = self._strip_sa(ticker_b3)
        # Índices (^BVSP) não existem no COTAHIST — skip.
        if ticker_plain.startswith("^"):
            return None

        try:
            with sqlite3.connect(str(self.cotahist_db)) as con:
                cur = con.execute(
                    """
                    SELECT close, trade_date
                    FROM   cotahist_daily
                    WHERE  ticker = ?
                      AND  market_type = '010'   -- mercado à vista
                    ORDER  BY trade_date DESC
                    LIMIT  1
                    """,
                    (ticker_plain,),
                )
                row = cur.fetchone()
        except Exception as exc:
            logger.debug("[cotahist_local] Erro ao consultar DB: %s", exc)
            return None

        if not row:
            logger.debug("[cotahist_local] Ticker não encontrado: %s", ticker_plain)
            return None

        close_price, trade_date = row
        stale_bdays = self._bdays_since(trade_date)
        if stale_bdays > _COTAHIST_MAX_STALE_BDAYS:
            logger.debug(
                "[cotahist_local] Dado antigo (%d dias úteis) para %s — usando yfinance",
                stale_bdays, ticker_plain,
            )
            return None

        logger.info(
            "[cotahist_local] Preço %s: %.2f em %s (%d bd atrás)",
            ticker_plain, close_price, trade_date, stale_bdays,
        )
        return (float(close_price), trade_date)

    def _get_history_from_cotahist(
        self, ticker_b3: str, start_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Return a price history DataFrame from COTAHIST for use in beta calculation.

        Args:
            ticker_b3:  B3 ticker (with or without .SA).
            start_date: ISO date string "YYYY-MM-DD" — inclusive lower bound.

        Returns:
            DataFrame indexed by date with columns matching yfinance output
            (Open, High, Low, Close, Volume) or None if unavailable/stale.
        """
        if not self.cotahist_db.exists():
            return None

        ticker_plain = self._strip_sa(ticker_b3)
        if ticker_plain.startswith("^"):
            return None

        try:
            with sqlite3.connect(str(self.cotahist_db)) as con:
                df = pd.read_sql_query(
                    """
                    SELECT trade_date, open, high, low, close, volume, trades
                    FROM   cotahist_daily
                    WHERE  ticker     = ?
                      AND  market_type = '010'
                      AND  trade_date >= ?
                    ORDER  BY trade_date ASC
                    """,
                    con,
                    params=(ticker_plain, start_date),
                )
        except Exception as exc:
            logger.debug("[cotahist_local] Erro ao buscar histórico: %s", exc)
            return None

        if df.empty:
            return None

        # Check freshness — last row must not be stale
        last_date = df["trade_date"].iloc[-1]
        if self._bdays_since(last_date) > _COTAHIST_MAX_STALE_BDAYS:
            logger.debug(
                "[cotahist_local] Histórico de %s desatualizado (%s) — usando yfinance",
                ticker_plain, last_date,
            )
            return None

        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        df.index.name = "Date"
        df.columns = [c.capitalize() for c in df.columns]   # open→Open, close→Close …
        df = df.rename(columns={"Trades": "Trades"})         # keep Trades as-is
        logger.info(
            "[cotahist_local] Histórico %s: %d dias (desde %s)",
            ticker_plain, len(df), start_date,
        )
        return df

    def _ticker_yahoo(self, ticker_b3: str) -> str:
        """Converte ticker B3 para formato Yahoo Finance."""
        t = ticker_b3.upper().strip()
        # Índices (^BVSP, ^DJI, etc.) não recebem sufixo .SA
        if t.startswith("^"):
            return t
        if not t.endswith(self.SUFIXO_B3):
            t += self.SUFIXO_B3
        return t

    def _cache_path(self, chave: str) -> Path:
        nome = chave.replace("/", "_").replace("^", "") + ".parquet"
        return self.cache_dir / nome

    def _ler_cache_precos(self, chave: str) -> Optional[pd.DataFrame]:
        p = self._cache_path(chave)
        if self.usar_cache and p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if datetime.now() - mtime < timedelta(hours=6):
                logger.debug(f"Cache preços HIT: {chave}")
                try:
                    return pd.read_parquet(p)
                except Exception:
                    pass
        return None

    def _salvar_cache_precos(self, chave: str, df: pd.DataFrame):
        try:
            df.to_parquet(self._cache_path(chave))
        except Exception as e:
            logger.debug(f"Não foi possível salvar cache de preços: {e}")

    # ── Preços históricos ─────────────────────────────────────────────────────

    def _cache_json_path(self, chave: str) -> Path:
        nome = chave.replace("/", "_").replace("^", "") + ".json"
        return self.cache_dir / nome

    def _ler_cache_json(self, chave: str, ttl_minutos: int = 30) -> Optional[dict]:
        p = self._cache_json_path(chave)
        if not (self.usar_cache and p.exists()):
            return None
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        if datetime.now() - mtime > timedelta(minutes=ttl_minutos):
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _salvar_cache_json(self, chave: str, payload: dict):
        try:
            self._cache_json_path(chave).write_text(
                json.dumps(payload, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.debug(f"Nao foi possivel salvar cache json mercado: {e}")

    @staticmethod
    def _parse_numero_br(valor: str) -> float:
        texto = str(valor or "").strip().replace("%", "")
        if not texto or texto in {"-", "N/D"}:
            return 0.0
        texto = texto.replace(".", "").replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            return 0.0

    def _fundamentus_snapshot(self, ticker_b3: str) -> dict:
        cache_key = f"fundamentus_{ticker_b3.upper()}"
        cached = self._ler_cache_json(cache_key, ttl_minutos=60 * 24)
        if cached:
            return cached

        url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker_b3.upper().strip()}"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
            with urlopen(req, timeout=20) as resp:
                html = resp.read().decode("iso-8859-1", "replace")

            cells = re.findall(r"<td[^>]*>(.*?)</td>", html, flags=re.S | re.I)
            cleaned = []
            for cell in cells:
                text = re.sub(r"<.*?>", "", cell)
                text = unescape(text).replace("\n", " ").replace("\t", " ").strip()
                if text:
                    cleaned.append(text)

            dados = {}
            for idx, label in enumerate(cleaned[:-1]):
                chave = label.replace("?", "").strip().lower()
                if "cotação" in chave or "cotacao" in chave:
                    dados["preco"] = self._parse_numero_br(cleaned[idx + 1])
                elif "valor de mercado" in chave:
                    dados["market_cap"] = self._parse_numero_br(cleaned[idx + 1]) / 1e6
                elif "nro. ações" in chave or "nro. acoes" in chave:
                    dados["acoes_total"] = self._parse_numero_br(cleaned[idx + 1]) / 1e3

            if dados:
                dados["fonte"] = "fundamentus"
                dados["ticker"] = ticker_b3.upper()
                self._salvar_cache_json(cache_key, dados)
            return dados
        except Exception as exc:
            logger.debug("Fundamentus indisponivel para %s: %s", ticker_b3, exc)
            return {}

    def baixar_precos(self, ticker_b3: str,
                      inicio: str = "2019-01-01",
                      fim: str = None) -> pd.DataFrame:
        """
        Baixa série histórica de preços ajustados.

        Tenta COTAHIST local primeiro; cai para yfinance se indisponível.

        Returns:
            DataFrame com colunas: Open, High, Low, Close, Volume (+ Adj Close via yfinance)
        """
        ticker_yf = self._ticker_yahoo(ticker_b3)
        fim       = fim or datetime.today().strftime("%Y-%m-%d")
        chave     = f"precos_{ticker_yf}_{inicio}_{fim}"

        cached = self._ler_cache_precos(chave)
        if cached is not None:
            return cached

        # ── Tentativa 1: COTAHIST local ───────────────────────────────────────
        df_cotahist = self._get_history_from_cotahist(ticker_b3, inicio)
        if df_cotahist is not None and not df_cotahist.empty:
            self._salvar_cache_precos(chave, df_cotahist)
            logger.info(
                "[cotahist_local] %d dias de preços carregados para %s",
                len(df_cotahist), ticker_b3,
            )
            return df_cotahist

        # ── Tentativa 2: yfinance ─────────────────────────────────────────────
        logger.info(f"[yfinance] Baixando preços: {ticker_yf} ({inicio} → {fim})")
        try:
            df = yf.download(ticker_yf, start=inicio, end=fim,
                             progress=False, auto_adjust=True)
            if df.empty:
                logger.warning(f"Sem dados de preços para {ticker_yf}")
                return pd.DataFrame()

            # Flatten multi-index se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            self._salvar_cache_precos(chave, df)
            logger.info(f"  [yfinance] {len(df)} dias de preços carregados")
            return df

        except Exception as e:
            logger.error(f"Erro ao baixar preços {ticker_yf}: {e}")
            return pd.DataFrame()

    def preco_atual(self, ticker_b3: str) -> dict:
        """
        Retorna cotação atual, market cap e dados básicos.

        Ordem de preferência:
          1. COTAHIST local (SQLite)
          2. yfinance
          3. Fundamentus (fallback para market cap / shares)
        """
        ticker_yf = self._ticker_yahoo(ticker_b3)
        cache_key = f"quote_{ticker_yf}"
        cached = self._ler_cache_json(cache_key, ttl_minutos=20)
        if cached and cached.get("preco", 0):
            return cached

        # ── Tentativa 1: COTAHIST local ───────────────────────────────────────
        preco: Optional[float] = None
        fonte_preco = "[yfinance]"
        cotahist_result = self._get_price_from_cotahist(ticker_b3)
        if cotahist_result is not None:
            preco, _trade_date = cotahist_result
            fonte_preco = "[cotahist_local]"
            logger.info("%s Preço %s: %.2f", fonte_preco, ticker_b3, preco)

        # ── Tentativa 2: yfinance (sempre busca market_cap/shares) ────────────
        logger.info(f"[yfinance] Buscando dados de mercado: {ticker_yf}")
        try:
            t    = yf.Ticker(ticker_yf)
            info = t.info or {}
            fast = getattr(t, "fast_info", {}) or {}

            def fast_get(*keys, default=0):
                for key in keys:
                    try:
                        value = fast.get(key) if hasattr(fast, "get") else getattr(fast, key)
                    except Exception:
                        value = None
                    if value:
                        return value
                return default

            # Use COTAHIST price if already found; otherwise take yfinance price
            if not preco:
                preco = (info.get("currentPrice") or
                         info.get("regularMarketPrice") or
                         info.get("previousClose") or
                         fast_get("last_price", "lastPrice", "regular_market_price", "previous_close"))
                if not preco:
                    hist = t.history(period="5d")
                    if not hist.empty and "Close" in hist.columns:
                        preco = float(hist["Close"].dropna().iloc[-1])

            market_cap = info.get("marketCap") or fast_get("market_cap", "marketCap")
            shares = info.get("sharesOutstanding") or fast_get("shares", "shares_outstanding")
            if not shares and market_cap and preco:
                shares = market_cap / preco
            if not preco or not shares:
                fund = self._fundamentus_snapshot(ticker_b3)
                if fund:
                    preco = preco or fund.get("preco")
                    market_cap = market_cap or (fund.get("market_cap", 0) * 1e6)
                    shares = shares or (fund.get("acoes_total", 0) * 1e3)

            payload = {
                "ticker":           ticker_b3,
                "preco":            preco or 0,
                "market_cap":       (market_cap or 0) / 1e6,   # em R$ MM
                "acoes_total":      (shares or 0) / 1e3,   # em mil
                "volume_medio":     info.get("averageVolume", 0),
                "52w_high":         info.get("fiftyTwoWeekHigh", 0),
                "52w_low":          info.get("fiftyTwoWeekLow", 0),
                "pl":               info.get("trailingPE", 0),
                "pvp":              info.get("priceToBook", 0),
                "dy":               info.get("dividendYield", 0),
                "nome":             info.get("longName", ticker_b3),
                "setor":            info.get("sector", "Financeiro"),
                "data_consulta":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fonte_preco":      fonte_preco,
            }
            self._salvar_cache_json(cache_key, payload)
            return payload
        except Exception as e:
            logger.error(f"Erro ao buscar cotação {ticker_yf}: {e}")
            return {"ticker": ticker_b3, "preco": preco or 0, "market_cap": 0,
                    "fonte_preco": fonte_preco}

    # ── Beta ──────────────────────────────────────────────────────────────────

    def calcular_beta(self, ticker_b3: str,
                      janela_dias: int = None,
                      inicio: str = "2019-01-01") -> dict:
        """
        Calcula o beta estatístico da ação vs. Ibovespa.

        Returns:
            dict com: beta, r_quadrado, n_observacoes, periodo
        """
        janela = janela_dias or self.JANELA_BETA
        logger.info(f"Calculando beta: {ticker_b3} ({janela} dias úteis)")

        # Baixar preços da ação e do índice
        df_acao = self.baixar_precos(ticker_b3, inicio=inicio)
        df_ibov = self.baixar_precos("^BVSP",   inicio=inicio)

        if df_acao.empty or df_ibov.empty:
            logger.warning("Dados insuficientes para calcular beta")
            return {"beta": None, "r_quadrado": None, "n": 0}

        # Alinhar datas
        col_acao = "Close" if "Close" in df_acao.columns else df_acao.columns[0]
        col_ibov = "Close" if "Close" in df_ibov.columns else df_ibov.columns[0]

        precos = pd.DataFrame({
            "acao": df_acao[col_acao],
            "ibov": df_ibov[col_ibov],
        }).dropna()

        if len(precos) < self.MIN_PONTOS:
            logger.warning(f"Poucos pontos ({len(precos)}) para beta confiável")

        # Pegar apenas os últimos N dias
        precos = precos.tail(janela)

        # Retornos diários
        rets = precos.pct_change().dropna()

        if rets.empty or len(rets) < 20:
            return {"beta": None, "r_quadrado": None, "n": 0}

        # Regressão linear: ret_acao = α + β × ret_ibov
        try:
            from numpy.polynomial import polynomial as P
            import numpy as np

            x   = rets["ibov"].values
            y   = rets["acao"].values
            cov = np.cov(x, y)
            beta_estatistico = cov[0][1] / cov[0][0]

            # R²
            correlacao = np.corrcoef(x, y)[0][1]
            r2 = correlacao ** 2

            logger.info(f"  Beta estatístico: {beta_estatistico:.4f} "
                        f"| R²: {r2:.3f} | n={len(rets)}")

            # Série de dados para a planilha (últimos 60 dias úteis)
            serie_diaria = rets.tail(60).reset_index()
            serie_diaria.columns = ["data", "ibov_var", "acao_var"]

            return {
                "beta":           round(beta_estatistico, 4),
                "r_quadrado":     round(r2, 4),
                "n_observacoes":  len(rets),
                "periodo_inicio": str(precos.index[0].date()),
                "periodo_fim":    str(precos.index[-1].date()),
                "serie_diaria":   serie_diaria,
                "precos_acao":    precos[["acao"]].reset_index(),
                "precos_ibov":    precos[["ibov"]].reset_index(),
            }

        except Exception as e:
            logger.error(f"Erro no cálculo do beta: {e}")
            return {"beta": None, "r_quadrado": None, "n": 0}

    # ── Série de preços anual ─────────────────────────────────────────────────

    def precos_por_ano(self, ticker_b3: str,
                       anos: list[int]) -> dict[int, dict]:
        """
        Retorna preço médio, abertura e fechamento do ano
        para uma lista de anos.
        """
        inicio = f"{min(anos)-1}-12-01"
        df     = self.baixar_precos(ticker_b3, inicio=inicio)

        if df.empty:
            return {}

        col = "Close" if "Close" in df.columns else df.columns[0]
        resultado = {}

        for ano in anos:
            df_ano = df[df.index.year == ano]
            if df_ano.empty:
                resultado[ano] = {"medio": 0, "abertura": 0, "fechamento": 0}
                continue
            resultado[ano] = {
                "medio":      float(df_ano[col].mean()),
                "abertura":   float(df_ano[col].iloc[0]),
                "fechamento": float(df_ano[col].iloc[-1]),
                "min":        float(df_ano[col].min()),
                "max":        float(df_ano[col].max()),
                "volume_med": float(df_ano.get("Volume", pd.Series([0])).mean()),
            }

        return resultado

    # ── Pares ON/PN ──────────────────────────────────────────────────────────

    def relacao_pn_on(self, ticker_on: str, ticker_pn: str,
                      janela_dias: int = 63) -> float:
        """
        Calcula a relação histórica média PN/ON (últimos ~3 meses).
        Útil para BBDC3/BBDC4, SANB3/SANB11, etc.
        """
        inicio = (datetime.now() - timedelta(days=janela_dias * 2)).strftime("%Y-%m-%d")
        df_on  = self.baixar_precos(ticker_on, inicio=inicio)
        df_pn  = self.baixar_precos(ticker_pn, inicio=inicio)

        if df_on.empty or df_pn.empty:
            return 1.10   # default

        col = "Close"
        precos = pd.DataFrame({
            "on": df_on[col], "pn": df_pn[col]
        }).dropna().tail(janela_dias)

        if precos.empty:
            return 1.10

        relacao = (precos["pn"] / precos["on"]).mean()
        logger.info(f"Relação PN/ON ({ticker_pn}/{ticker_on}): {relacao:.4f}")
        return round(float(relacao), 4)

    # ── Ações em circulação ───────────────────────────────────────────────────

    def acoes_emitidas(self, ticker_b3: str) -> dict:
        """Retorna número de ações total, ON e PN (quando disponível)."""
        ticker_yf = self._ticker_yahoo(ticker_b3)
        try:
            t    = yf.Ticker(ticker_yf)
            info = t.info or {}
            fast = getattr(t, "fast_info", {}) or {}

            def fast_get(*keys, default=0):
                for key in keys:
                    try:
                        value = fast.get(key) if hasattr(fast, "get") else getattr(fast, key)
                    except Exception:
                        value = None
                    if value:
                        return value
                return default

            preco = (info.get("currentPrice") or
                     info.get("regularMarketPrice") or
                     info.get("previousClose") or
                     fast_get("last_price", "lastPrice", "regular_market_price", "previous_close"))
            market_cap = info.get("marketCap") or fast_get("market_cap", "marketCap")
            shares = info.get("sharesOutstanding") or fast_get("shares", "shares_outstanding")
            if not shares and market_cap and preco:
                shares = market_cap / preco
            if not shares:
                fund = self._fundamentus_snapshot(ticker_b3)
                shares = fund.get("acoes_total", 0) * 1e3 if fund else 0
                market_cap = market_cap or (fund.get("market_cap", 0) * 1e6 if fund else 0)
            return {
                "total":       (shares or 0) / 1e3,   # mil
                "float":       info.get("floatShares", 0) / 1e3,
                "market_cap":  (market_cap or 0) / 1e6,
            }
        except Exception as e:
            logger.error(f"Erro ao buscar ações emitidas: {e}")
            return {"total": 0, "float": 0, "market_cap": 0}

    # ── Múltiplos históricos ──────────────────────────────────────────────────

    def multiplos_historicos(self, ticker_b3: str,
                              anos: list[int],
                              lucro_por_ano: dict[int, float],
                              pl_por_ano: dict[int, float]) -> dict[int, dict]:
        """
        Calcula P/L e P/VP históricos combinando preço e dados fundamentais.

        Args:
            lucro_por_ano: {ano: lucro_liquido_R$_MM}
            pl_por_ano:    {ano: patrimonio_liquido_R$_MM}
        """
        precos_anuais = self.precos_por_ano(ticker_b3, anos)
        info_acoes    = self.acoes_emitidas(ticker_b3)
        n_acoes       = info_acoes.get("total", 0)   # em mil

        resultado = {}
        for ano in anos:
            preco_info = precos_anuais.get(ano, {})
            preco_med  = preco_info.get("medio", 0)
            market_cap = preco_med * n_acoes / 1000   # MM (mil ações × preço / 1000)

            lucro = lucro_por_ano.get(ano, 0)
            pl    = pl_por_ano.get(ano, 0)

            resultado[ano] = {
                "preco_medio":  round(preco_med, 2),
                "market_cap":   round(market_cap, 0),
                "pl":           round(market_cap / lucro, 1) if lucro > 0 else 0,
                "pvp":          round(market_cap / pl, 2)    if pl > 0    else 0,
                "dy":           0,   # será calculado com dividendos
            }

        return resultado
