"""
Módulo 03 — Coletor de Dados Macroeconômicos
Fonte: API pública do Banco Central do Brasil (BCB/SGS)

Séries disponíveis:
  11   → DI Over (taxa Selic efetiva diária)
  432  → Selic meta
  433  → IPCA mensal
  13522→ IPCA acumulado 12 meses
  256  → TJLP
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
        "ipca_mensal":  433,    # IPCA mensal
        "ipca_12m":     13522,  # IPCA acumulado 12 meses
        "tjlp":         256,    # TJLP mensal (% a.a.)
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
        self.session.headers.update({
            "Accept": "*/*",
            "User-Agent": "PipelineValuacaoBancaria/1.0 (fins educacionais)",
        })

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_path(self, serie_cod: int) -> Path:
        return self.cache_dir / f"bcb_serie_{serie_cod}.csv"

    def _cache_valido(self, path: Path, ttl_horas: int = 12) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(hours=ttl_horas)

    def _ler_cache(self, path: Path) -> pd.Series:
        df = pd.read_csv(path)
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        serie = df.dropna().set_index("data")["valor"].sort_index()
        return serie.astype(float)

    def _gravar_cache(self, path: Path, serie: pd.Series) -> None:
        out = serie.sort_index().reset_index()
        out.columns = ["data", "valor"]
        out.to_csv(path, index=False)

    def _janelas_datas(self, inicio: str, fim: str) -> list[tuple[str, str]]:
        """Divide consultas longas para respeitar limite recente do SGS."""
        ini_dt = datetime.strptime(inicio, self.DATE_FMT)
        fim_dt = datetime.strptime(fim, self.DATE_FMT)
        janelas = []
        atual = ini_dt
        while atual <= fim_dt:
            fim_janela = min(atual + timedelta(days=3650), fim_dt)
            janelas.append((atual.strftime(self.DATE_FMT), fim_janela.strftime(self.DATE_FMT)))
            atual = fim_janela + timedelta(days=1)
        return janelas

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
                return self._ler_cache(cache_p)
            except Exception:
                pass

        url = self.BCB_URL.format(cod=codigo)

        logger.info(f"Baixando série BCB {codigo}...")
        try:
            dados = []
            for data_inicial, data_final in self._janelas_datas(inicio, fim):
                params = {
                    "formato": "json",
                    "dataInicial": data_inicial,
                    "dataFinal":   data_final,
                }
                resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                dados.extend(resp.json())

            if not dados:
                logger.warning(f"Série {codigo} vazia")
                return pd.Series(dtype=float)

            df = pd.DataFrame(dados)
            df["data"]  = pd.to_datetime(df["data"], format=self.DATE_FMT,
                                          errors="coerce")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            df = df.dropna().set_index("data")["valor"]
            df = df[~df.index.duplicated(keep="last")].sort_index()
            df.name = str(codigo)

            self._gravar_cache(cache_p, df)
            logger.info(f"  Série {codigo}: {len(df)} observações "
                        f"({df.index[0].date()} → {df.index[-1].date()})")
            return df

        except Exception as e:
            logger.error(f"Erro ao baixar série BCB {codigo}: {e}")
            if self.usar_cache and cache_p.exists():
                try:
                    logger.warning(f"Usando cache BCB expirado para série {codigo}")
                    return self._ler_cache(cache_p)
                except Exception:
                    pass
            return pd.Series(dtype=float)

    # ── Taxas anuais ──────────────────────────────────────────────────────────

    def _serie_tem_datetime_index(self, serie: pd.Series) -> bool:
        """Verifica se a série tem um DatetimeIndex válido (não RangeIndex)."""
        return hasattr(serie.index, "year")

    def selic_por_ano(self, anos: list[int]) -> dict[int, float]:
        """
        Retorna a Selic média anual (acumulada no ano / 252 dias úteis).
        Converte taxa diária → anual.
        """
        serie = self.baixar_serie(self.SERIES["selic_over"])  # Selic Over diária em % a.d.
        resultado = {}

        if not self._serie_tem_datetime_index(serie):
            logger.warning("Série Selic Over sem DatetimeIndex — usando fallback histórico")
            fallback = {2019: 0.0596, 2020: 0.0228, 2021: 0.0448,
                        2022: 0.1233, 2023: 0.1315, 2024: 0.1073}
            return {a: fallback.get(a, 0.105) for a in anos}

        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            taxa_diaria = dados_ano.mean() / 100
            taxa_anual  = (1 + taxa_diaria) ** 252 - 1
            resultado[ano] = float(round(taxa_anual, 6))
            logger.debug(f"  Selic {ano}: {taxa_anual:.4%}")

        return resultado

    def selic_meta_por_ano(self, anos: list[int]) -> dict[int, float]:
        """Meta da Selic (% a.a.) — valor de final de ano."""
        serie = self.baixar_serie(self.SERIES["selic_meta"])
        resultado = {}

        if not self._serie_tem_datetime_index(serie):
            logger.warning("Série Selic meta sem DatetimeIndex — usando fallback histórico")
            fallback = {2019: 0.0450, 2020: 0.0200, 2021: 0.0925,
                        2022: 0.1375, 2023: 0.1175, 2024: 0.1175}
            return {a: fallback.get(a, 0.10) for a in anos}

        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            resultado[ano] = round(float(dados_ano.iloc[-1]) / 100, 6)
        return resultado

    def ipca_por_ano(self, anos: list[int]) -> dict[int, float]:
        """IPCA acumulado no ano (% a.a.)."""
        # Fallback com valores históricos reais (fonte: IBGE via BCB)
        fallback = {2019: 0.0410, 2020: 0.0452, 2021: 0.1006,
                    2022: 0.0562, 2023: 0.0462, 2024: 0.0483}

        serie = self.baixar_serie(self.SERIES["ipca_mensal"])

        if not self._serie_tem_datetime_index(serie):
            logger.warning("Série IPCA sem DatetimeIndex — usando fallback histórico")
            return {a: fallback.get(a, 0.045) for a in anos}

        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = fallback.get(ano, 0.045)
                continue
            taxa_anual = 1.0
            for v in dados_ano.values:
                taxa_anual *= (1 + v / 100)
            # Sanidade: IPCA anual de 2% a 30% é plausível; fora disso usa fallback
            ipca_calc = taxa_anual - 1
            if 0.02 <= ipca_calc <= 0.30:
                resultado[ano] = float(round(ipca_calc, 6))
            else:
                logger.warning(f"IPCA calculado fora do intervalo plausível ({ipca_calc:.1%}) "
                               f"para {ano} — usando fallback")
                resultado[ano] = fallback.get(ano, 0.045)
        return resultado

    def tjlp_por_ano(self, anos: list[int]) -> dict[int, float]:
        """TJLP anual (média dos trimestres publicados)."""
        serie = self.baixar_serie(self.SERIES["tjlp"])
        resultado = {}

        if not self._serie_tem_datetime_index(serie):
            logger.warning("Série TJLP sem DatetimeIndex — usando fallback histórico")
            fallback = {2019: 0.0650, 2020: 0.0525, 2021: 0.0525,
                        2022: 0.0625, 2023: 0.0700, 2024: 0.0700}
            return {a: fallback.get(a, 0.065) for a in anos}

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

        if not self._serie_tem_datetime_index(serie):
            return {a: 0.0 for a in anos}

        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = 0.0
                continue
            resultado[ano] = float(dados_ano.iloc[-1])
        return resultado

    def cds_por_ano(self, anos: list[int]) -> dict[int, float]:
        """CDS Brasil 5Y — média anual em decimal (ex: 0.0040 = 40bp)."""
        fallback = {2019: 0.0041, 2020: 0.0065, 2021: 0.0090,
                    2022: 0.0120, 2023: 0.0085, 2024: 0.0070}
        try:
            serie = self.baixar_serie(self.SERIES["cds_br"])
        except Exception:
            logger.warning("CDS não disponível via BCB; usando aproximação histórica")
            return {a: fallback.get(a, 0.0050) for a in anos}

        if not self._serie_tem_datetime_index(serie):
            logger.warning("CDS sem DatetimeIndex — usando fallback histórico")
            return {a: fallback.get(a, 0.0050) for a in anos}

        resultado = {}
        for ano in anos:
            dados_ano = serie[serie.index.year == ano]
            if dados_ano.empty:
                resultado[ano] = fallback.get(ano, 0.0050)
                continue
            resultado[ano] = round(float(dados_ano.mean()) / 10_000, 6)
        return resultado

    def inflacao_implicita_por_ano(self, anos: list[int]) -> dict[int, float]:
        """
        Inflação implícita ≈ Selic - Taxa Real.
        Aproximação: IPCA esperado (Focus) ou acumulado 12M.
        """
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
        # TJLP projetada: usa último valor histórico com convergência gradual para 0.07
        tjlp_hist = hist.get("tjlp", {})
        tjlp_ultimo = (tjlp_hist.get(max(tjlp_hist)) if tjlp_hist else 0.07)
        tjlp_proj = {}
        for i, ano in enumerate(sorted(anos_projecao)):
            # Converge do último valor histórico para 0.07 em 5 anos
            alvo  = 0.07
            passos = min(i, 5)
            tjlp_proj[ano] = round(
                tjlp_ultimo + (alvo - tjlp_ultimo) * passos / 5, 6)

        proj = {
            "di":            premissas.get("di",    {}),
            "ipca":          premissas.get("ipca",  {}),
            "cds":           premissas.get("cds",   {a: 0.004 for a in anos_projecao}),
            "inflacao_impl": premissas.get("ipca",  {}),  # proxy
            "tjlp":          tjlp_proj,
        }

        # Log resumo
        logger.info("\nRESUMO MACRO HISTÓRICO:")
        for serie, dados in hist.items():
            valores = " | ".join(f"{a}: {v:.2%}" for a, v in
                                  sorted(dados.items())[-5:])
            logger.info(f"  {serie:15s}: {valores}")

        return {"historico": hist, "projecao": proj}

    # ── Focus/Expectativas (BCB) ──────────────────────────────────────────────

    def _focus_cache_path(self, indicador: str) -> Path:
        nome = f"focus_{indicador.lower().replace('-', '_').replace(' ', '_')}.json"
        return self.cache_dir / nome

    def expectativas_focus(self, indicador: str = "Selic",
                            n_periodos: int = 10) -> dict:
        """
        Busca expectativas do mercado (Relatório Focus) via API BCB.
        Disponível para: Selic, IPCA, IGP-M, PIB, Câmbio.

        Returns:
            dict {ano: mediana}
        """
        cache_p = self._focus_cache_path(indicador)

        if self.usar_cache and self._cache_valido(cache_p, ttl_horas=12):
            try:
                with open(cache_p, "r", encoding="utf-8") as f:
                    resultado = {int(k): v for k, v in json.load(f).items()}
                logger.debug(f"Cache Focus HIT: {indicador}")
                return resultado
            except Exception:
                pass

        url = (
            "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/"
            "odata/ExpectativasMercadoAnuais"
            f"?%24filter=Indicador%20eq%20'{indicador}'"
            "&%24top=5000&%24format=json"
            "&%24orderby=Data%20desc"
            "&%24select=Indicador,Data,DataReferencia,Mediana"
        )

        try:
            resp = self.session.get(url, timeout=self.TIMEOUT)
            resp.raise_for_status()
            dados = resp.json().get("value", [])

            if not dados:
                return {}

            df = pd.DataFrame(dados)
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
            ref_col = "DataReferencia" if "DataReferencia" in df.columns else "Ano"
            df["Ano"] = pd.to_numeric(df[ref_col], errors="coerce")
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

            if resultado and self.usar_cache:
                with open(cache_p, "w", encoding="utf-8") as f:
                    json.dump(resultado, f)

            logger.info(f"Expectativas Focus ({indicador}): "
                        f"{list(resultado.items())[:5]}")
            return resultado

        except Exception as e:
            logger.warning(f"Não foi possível obter Focus {indicador}: {e}")
            if self.usar_cache and cache_p.exists():
                try:
                    with open(cache_p, "r", encoding="utf-8") as f:
                        resultado = {int(k): v for k, v in json.load(f).items()}
                    logger.warning(f"Usando cache Focus expirado para {indicador}")
                    return resultado
                except Exception:
                    pass
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
