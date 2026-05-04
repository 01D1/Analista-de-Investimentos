"""
Módulo 02 — Coletor de Dados de Mercado
Busca preços, cotações, volumes e dados para cálculo de beta.

Fonte principal: yfinance (Yahoo Finance)
Fonte alternativa: B3 (scraping público)
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger("pipeline.mercado")


class ColetorMercado:
    """Coleta dados de mercado: preços, beta, market cap, múltiplos."""

    IBOV_TICKER   = "^BVSP"
    SUFIXO_B3     = ".SA"
    JANELA_BETA   = 252   # dias úteis (1 ano)
    MIN_PONTOS    = 60    # mínimo de pontos para calcular beta

    def __init__(self, cache_dir: Path, usar_cache: bool = True):
        self.cache_dir  = Path(cache_dir)
        self.usar_cache = usar_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict = {}

    def _ticker_yahoo(self, ticker_b3: str) -> str:
        """Converte ticker B3 para formato Yahoo Finance."""
        t = ticker_b3.upper().strip()
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

    def baixar_precos(self, ticker_b3: str,
                      inicio: str = "2019-01-01",
                      fim: str = None) -> pd.DataFrame:
        """
        Baixa série histórica de preços ajustados.

        Returns:
            DataFrame com colunas: Open, High, Low, Close, Volume, Adj Close
        """
        ticker_yf = self._ticker_yahoo(ticker_b3)
        fim       = fim or datetime.today().strftime("%Y-%m-%d")
        chave     = f"precos_{ticker_yf}_{inicio}_{fim}"

        cached = self._ler_cache_precos(chave)
        if cached is not None:
            return cached

        logger.info(f"Baixando preços: {ticker_yf} ({inicio} → {fim})")
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
            logger.info(f"  {len(df)} dias de preços carregados")
            return df

        except Exception as e:
            logger.error(f"Erro ao baixar preços {ticker_yf}: {e}")
            return pd.DataFrame()

    def preco_atual(self, ticker_b3: str) -> dict:
        """Retorna cotação atual, market cap e dados básicos."""
        ticker_yf = self._ticker_yahoo(ticker_b3)
        logger.info(f"Buscando cotação atual: {ticker_yf}")
        try:
            t    = yf.Ticker(ticker_yf)
            info = t.info or {}
            preco = (info.get("currentPrice") or
                     info.get("regularMarketPrice") or
                     info.get("previousClose", 0))
            return {
                "ticker":           ticker_b3,
                "preco":            preco,
                "market_cap":       info.get("marketCap", 0) / 1e6,   # em R$ MM
                "acoes_total":      info.get("sharesOutstanding", 0) / 1e3,   # em mil
                "volume_medio":     info.get("averageVolume", 0),
                "52w_high":         info.get("fiftyTwoWeekHigh", 0),
                "52w_low":          info.get("fiftyTwoWeekLow", 0),
                "pl":               info.get("trailingPE", 0),
                "pvp":              info.get("priceToBook", 0),
                "dy":               info.get("dividendYield", 0),
                "nome":             info.get("longName", ticker_b3),
                "setor":            info.get("sector", "Financeiro"),
                "data_consulta":    datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            logger.error(f"Erro ao buscar cotação {ticker_yf}: {e}")
            return {"ticker": ticker_b3, "preco": 0, "market_cap": 0}

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
            return {
                "total":       info.get("sharesOutstanding", 0) / 1e3,   # mil
                "float":       info.get("floatShares", 0) / 1e3,
                "market_cap":  info.get("marketCap", 0) / 1e6,
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
