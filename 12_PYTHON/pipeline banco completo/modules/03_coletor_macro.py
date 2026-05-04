"""
Módulo 03 — Coletor de Dados Macroeconômicos
Fonte: API pública do Banco Central do Brasil (BCB/SGS)

Séries disponíveis:
  11   → DI Over (taxa Selic efetiva diária)
  432  → Selic meta
  433  → IPCA acumulado 12 meses
  13522→ IPCA mensal
  258  → TJLP
  12   → CDI diário
  4380 → PIB nominal
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger("pipeline.macro")


class ColetorMacro:
    """Coleta séries macroeconômicas do BCB e projeta valores futuros."""

    BCB_URL   = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"
    TIMEOUT   = 30
    DATE_FMT  = "%d/%m/%Y"

    # Séries do BCB
    SERIES = {
        "di":           12,     # CDI/DI Over diário (% a.d.)
        "selic_meta":   432,    # Selic meta anual
        "selic_over":   11,     # Selic Over diária
        "ipca_12m":     433,    # IPCA acumulado 12 meses
        "ipca_mensal":  13522,  # IPCA mensal
        "tjlp":         258,    # TJLP trimestral
        "pib_nominal":  4380,   # PIB nominal (R$ MM)
        "pib_variacao": 4385,   # PIB variação real %
        "cambio_dolar": 1,      # USD/BRL
        "cds_br":       29039,  # CDS Brasil 5Y (em pontos-base)
    }

    def __init__(self, cache_dir: Path, usar_cache: bool = True):
        self.cache_dir  = Path(cache_dir)
        self.usar_cache = usar_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session    = requests.Session()

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_path(self, serie_cod: int) -> Path:
        return self.cache_dir / f"bcb_serie_{serie_cod}.parquet"

    def _cache_valido(self, path: Path, ttl_horas: int = 12) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(hours=ttl_horas)

    # ── Download de série ─────────────────────────────────────────────────────

    def baixar_serie(self, codigo: int,
                     inicio: str = "01/01/2010",
                     fim: str = None) -> pd.Series:
        """
        Baixa uma série temporal do BCB.

        Args:
            codigo: Código SGS (ex: 432 para Selic meta)
            inicio: "dd/mm/yyyy"
            fim:    "dd/mm/yyyy" ou None (usa hoje)

        Returns:
            pd.Series com index DatetimeIndex e valores float
        """
        cache_p = self._cache_path(codigo)
        fim     = fim or datetime.now().strftime(self.DATE_FMT)

        if self.usar_cache and self._cache_valido(cache_p):
            logger.debug(f"Cache BCB HIT: série {codigo}")
            try:
                return pd.read_parquet(cache_p).squeeze()
            except Exception:
                pass

        url = self.BCB_URL.format(cod=codigo)
        params = {
            "formato": "json",
            "dataInicial": inicio,
            "dataFinal":   fim,
        }

        logger.info(f"Baixando série BCB {codigo}...")
        try:
            resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            dados = resp.json()

            if not dados:
                logger.warning(f"Série {codigo} vazia")
                return pd.Series(dtype=float)

            df = pd.DataFrame(dados)
            df["data"]  = pd.to_datetime(df["data"], format=self.DATE_FMT,
                                          errors="coerce")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            df = df.dropna().set_index("data")["valor"]
            df.name = str(codigo)

            df.to_frame().to_parquet(cache_p)
            logger.info(f"  Série {codigo}: {len(df)} observações "
                        f"({df.index[0].date()} → {df.index[-1].date()})")
            return df

        except Exception as e:
            logger.error(f"Erro ao baixar série BCB {codigo}: {e}")
            return pd.Series(dtype=float)

    # ── Taxas anuais ──────────────────────────────────────────────────────────

    def selic_por_ano(self, anos: list[int]) -> dict[int, float]:
        """
        Retorna a Selic média anual (acumulada no ano / 252 dias úteis).
        Converte taxa diária → anual.
        """
        serie = self.baixar_serie(self.SERIES["di"])  # CDI diário em % a.d.
        resultado = {}

        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue

            # Compor taxa anual: (1+r_dia)^252 - 1
            # O BCB publica em % ao dia (ex: 0.0327)
            taxa_diaria = dados_ano.mean() / 100   # converter de % para decimal
            taxa_anual  = (1 + taxa_diaria) ** 252 - 1
            resultado[ano] = round(taxa_anual, 6)
            logger.debug(f"  Selic {ano}: {taxa_anual:.4%}")

        return resultado

    def selic_meta_por_ano(self, anos: list[int]) -> dict[int, float]:
        """Meta da Selic (% a.a.) — valor de final de ano."""
        serie = self.baixar_serie(self.SERIES["selic_meta"])
        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            resultado[ano] = round(float(dados_ano.iloc[-1]) / 100, 6)
        return resultado

    def ipca_por_ano(self, anos: list[int]) -> dict[int, float]:
        """IPCA acumulado no ano (% a.a.)."""
        serie = self.baixar_serie(self.SERIES["ipca_mensal"])
        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            # Compor os 12 meses
            taxa_anual = 1.0
            for v in dados_ano.values:
                taxa_anual *= (1 + v / 100)
            resultado[ano] = round(taxa_anual - 1, 6)
        return resultado

    def tjlp_por_ano(self, anos: list[int]) -> dict[int, float]:
        """TJLP anual (média dos trimestres publicados)."""
        serie = self.baixar_serie(self.SERIES["tjlp"])
        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            resultado[ano] = round(float(dados_ano.mean()) / 100, 6)
        return resultado

    def pib_nominal_por_ano(self, anos: list[int]) -> dict[int, float]:
        """PIB nominal R$ MM — último valor do ano."""
        serie = self.baixar_serie(self.SERIES["pib_nominal"])
        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            resultado[ano] = float(dados_ano.iloc[-1])
        return resultado

    def cds_por_ano(self, anos: list[int]) -> dict[int, float]:
        """CDS Brasil 5Y — média anual em decimal (ex: 0.0040 = 40bp)."""
        try:
            serie = self.baixar_serie(self.SERIES["cds_br"])
        except Exception:
            # Fallback: valores aproximados históricos
            logger.warning("CDS não disponível via BCB; usando aproximação histórica")
            fallback = {2019: 0.0041, 2020: 0.0065, 2021: 0.0090,
                        2022: 0.0120, 2023: 0.0085, 2024: 0.0070}
            return {a: fallback.get(a, 0.0050) for a in anos}

        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0050
                continue
            # CDS em pontos-base → decimal
            resultado[ano] = round(float(dados_ano.mean()) / 10_000, 6)
        return resultado

    def inflacao_implicita_por_ano(self, anos: list[int]) -> dict[int, float]:
        """
        Inflação implícita ≈ Selic - Taxa Real.
        Aproximação: IPCA esperado (Focus) ou acumulado 12M.
        """
        # Usar IPCA acumulado como proxy da inflação implícita
        return self.ipca_por_ano(anos)

    # ── Pacote completo de dados macro ────────────────────────────────────────

    def dados_macro_completos(self, anos_historicos: list[int],
                               anos_projecao: list[int],
                               premissas_projecao: dict = None) -> dict:
        """
        Retorna um dicionário completo com todos os dados macro,
        históricos e projetados.

        Args:
            premissas_projecao: dict com taxas projetadas (do settings.py)
                {
                    "di":       {2025: 0.13, 2026: 0.11, ...},
                    "ipca":     {2025: 0.05, 2026: 0.045, ...},
                    "cds":      {2025: 0.004, ...},
                }

        Returns:
            {
                "historico": {
                    "selic":  {2019: 0.065, ...},
                    "ipca":   {2019: 0.040, ...},
                    "tjlp":   {2019: 0.062, ...},
                    "cds":    {2019: 0.004, ...},
                },
                "projecao": {
                    "di":   {2025: 0.13, ...},
                    "ipca": {2025: 0.05, ...},
                    ...
                },
            }
        """
        premissas = premissas_projecao or {}

        logger.info("\n=== Coletando dados macroeconômicos ===")

        hist = {
            "selic_meta": self.selic_meta_por_ano(anos_historicos),
            "selic_efet": self.selic_por_ano(anos_historicos),
            "ipca":       self.ipca_por_ano(anos_historicos),
            "tjlp":       self.tjlp_por_ano(anos_historicos),
            "cds":        self.cds_por_ano(anos_historicos),
            "inflacao_impl": self.inflacao_implicita_por_ano(anos_historicos),
        }

        # Projeções: vem das premissas do settings.py
        proj = {
            "di":           premissas.get("di",    {}),
            "ipca":         premissas.get("ipca",  {}),
            "cds":          premissas.get("cds",   {a: 0.004 for a in anos_projecao}),
            "inflacao_impl": premissas.get("ipca", {}),  # proxy
        }

        # Log resumo
        logger.info("\nRESUMO MACRO HISTÓRICO:")
        for serie, dados in hist.items():
            valores = " | ".join(f"{a}: {v:.2%}" for a, v in
                                  sorted(dados.items())[-5:])
            logger.info(f"  {serie:15s}: {valores}")

        return {"historico": hist, "projecao": proj}

    # ── Focus/Expectativas (BCB) ──────────────────────────────────────────────

    def expectativas_focus(self, indicador: str = "Selic",
                            n_periodos: int = 10) -> dict:
        """
        Busca expectativas do mercado (Relatório Focus) via API BCB.
        Disponível para: Selic, IPCA, IGP-M, PIB, Câmbio.

        Returns:
            dict {ano: mediana}
        """
        url = (f"https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/"
               f"odata/ExpectativasMercadoAnuais"
               f"?%24filter=Indicador%20eq%20'{indicador}'"
               f"&%24top=100&%24format=json&%24select=Indicador,Data,Ano,Mediana")

        try:
            resp = requests.get(url, timeout=self.TIMEOUT)
            resp.raise_for_status()
            dados = resp.json().get("value", [])

            if not dados:
                return {}

            df = pd.DataFrame(dados)
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
            # Pegar a expectativa mais recente por ano
            df = (df.sort_values("Data")
                    .groupby("Ano")["Mediana"]
                    .last()
                    .reset_index())

            ano_atual = datetime.now().year
            resultado = {}
            for _, row in df.iterrows():
                try:
                    ano = int(row["Ano"])
                    if ano >= ano_atual:
                        mediana = float(row["Mediana"]) / 100
                        resultado[ano] = mediana
                except Exception:
                    continue

            logger.info(f"Expectativas Focus ({indicador}): "
                        f"{list(resultado.items())[:5]}")
            return resultado

        except Exception as e:
            logger.warning(f"Não foi possível obter Focus {indicador}: {e}")
            return {}

    def selic_projetada(self, anos: list[int]) -> dict[int, float]:
        """
        Retorna Selic projetada combinando Focus e valores padrão.
        Prioridade: Focus > settings > fallback.
        """
        focus = self.expectativas_focus("Selic")
        resultado = {}
        for ano in anos:
            if ano in focus:
                resultado[ano] = focus[ano]
            else:
                # Fallback conservador
                resultado[ano] = 0.090
        return resultado
