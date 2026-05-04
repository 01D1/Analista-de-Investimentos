"""
Módulo 01 — Coletor CVM
Baixa DFPs (Demonstrações Financeiras Padronizadas) e ITRs
diretamente da API pública da CVM.

Endpoints usados:
  - https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/
  - https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/
  - https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/

Documentação: https://dados.cvm.gov.br/
"""

import os
import json
import zipfile
import io
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger("pipeline.cvm")


class ColetorCVM:
    """
    Baixa e processa demonstrações financeiras da CVM.
    Faz cache local dos arquivos para evitar re-downloads.
    """

    BASE_URL   = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
    TIMEOUT    = 60
    CHUNK_SIZE = 1024 * 1024   # 1 MB

    def __init__(self, cache_dir: Path, usar_cache: bool = True,
                 cache_ttl_horas: int = 24):
        self.cache_dir    = Path(cache_dir)
        self.usar_cache   = usar_cache
        self.cache_ttl    = timedelta(hours=cache_ttl_horas)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session      = requests.Session()
        self.session.headers.update({
            "User-Agent": "PipelineValuacaoBancaria/1.0 (fins educacionais)"
        })

    # ── Helpers de cache ──────────────────────────────────────────────────────

    def _cache_path(self, chave: str) -> Path:
        nome = hashlib.md5(chave.encode()).hexdigest() + ".json"
        return self.cache_dir / nome

    def _cache_valido(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < self.cache_ttl

    def _ler_cache(self, chave: str):
        p = self._cache_path(chave)
        if self.usar_cache and self._cache_valido(p):
            logger.debug(f"Cache HIT: {chave[:60]}")
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _salvar_cache(self, chave: str, dados):
        p = self._cache_path(chave)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, default=str)

    # ── Download genérico ─────────────────────────────────────────────────────

    def _baixar_zip_csv(self, url: str, nome_arquivo: str) -> Optional[pd.DataFrame]:
        """Baixa um ZIP da CVM e extrai o CSV interno."""
        chave = f"zip:{url}"
        cached = self._ler_cache(chave)
        if cached is not None:
            return pd.DataFrame(cached)

        logger.info(f"Baixando: {url}")
        try:
            resp = self.session.get(url, timeout=self.TIMEOUT, stream=True)
            resp.raise_for_status()

            conteudo = b""
            for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                conteudo += chunk

            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                # Procura o arquivo correto dentro do ZIP
                nomes = z.namelist()
                alvo = next((n for n in nomes if nome_arquivo in n), nomes[0])
                logger.debug(f"  Extraindo: {alvo}")
                with z.open(alvo) as f:
                    df = pd.read_csv(f, sep=";", encoding="latin-1",
                                     low_memory=False)

            self._salvar_cache(chave, df.to_dict("records"))
            return df

        except requests.RequestException as e:
            logger.error(f"Erro ao baixar {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao processar ZIP {url}: {e}")
            return None

    # ── Cadastro da empresa ───────────────────────────────────────────────────

    def buscar_codigo_cvm(self, ticker_b3: str) -> Optional[str]:
        """
        Busca o código CVM a partir do ticker da B3.
        Retorna o CD_CVM (ex: "906" para Bradesco).
        """
        url    = f"{self.BASE_URL}/CAD/DADOS/cad_cia_aberta.csv"
        chave  = f"cad:{ticker_b3}"
        cached = self._ler_cache(chave)
        if cached is not None:
            return cached.get("cd_cvm")

        logger.info(f"Buscando código CVM para {ticker_b3}...")
        try:
            resp = self.session.get(url, timeout=self.TIMEOUT)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), sep=";", encoding="latin-1")

            # Normaliza ticker: remove dígito de classe se necessário
            ticker_base = ticker_b3.upper()[:4]
            mask = df["CD_CVM"].notna() & (
                df.get("SG_ATIVO", pd.Series()).astype(str).str.contains(
                    ticker_base, case=False, na=False
                ) |
                df.get("NM_PREGAO", pd.Series()).astype(str).str.contains(
                    ticker_base, case=False, na=False
                )
            )
            resultado = df[mask]
            if resultado.empty:
                logger.warning(f"Ticker {ticker_b3} não encontrado no cadastro CVM")
                return None

            cd_cvm = str(int(resultado.iloc[0]["CD_CVM"]))
            logger.info(f"  Código CVM: {cd_cvm}")
            self._salvar_cache(chave, {"cd_cvm": cd_cvm,
                                       "nome": resultado.iloc[0].get("NM_PREGAO", "")})
            return cd_cvm

        except Exception as e:
            logger.error(f"Erro ao buscar código CVM: {e}")
            return None

    # ── DFP (anual) ───────────────────────────────────────────────────────────

    def baixar_dfp(self, codigo_cvm: str, ano: int,
                   tipo: str = "con") -> dict[str, pd.DataFrame]:
        """
        Baixa as DFPs de um ano específico.

        Args:
            codigo_cvm: Ex: "906"
            ano:        Ex: 2023
            tipo:       "con" (consolidado) ou "ind" (individual)

        Returns:
            dict com DataFrames: {
                "dre": ...,
                "bpa": ...,   # ativo
                "bpp": ...,   # passivo
                "dfc_mi": ... # fluxo de caixa método indireto
            }
        """
        resultado = {}
        ano_str   = str(ano)

        # Mapeamento de tipo de documento → nome do arquivo no ZIP
        docs = {
            "dre":    f"dfp_cia_aberta_DRE_{tipo}_{ano_str}.csv",
            "bpa":    f"dfp_cia_aberta_BPA_{tipo}_{ano_str}.csv",
            "bpp":    f"dfp_cia_aberta_BPP_{tipo}_{ano_str}.csv",
            "dfc_mi": f"dfp_cia_aberta_DFC_MI_{tipo}_{ano_str}.csv",
            "dfc_md": f"dfp_cia_aberta_DFC_MD_{tipo}_{ano_str}.csv",
        }

        for chave_doc, nome_csv in docs.items():
            url = (f"{self.BASE_URL}/DOC/DFP/DADOS/"
                   f"dfp_cia_aberta_{ano_str}.zip")
            df  = self._baixar_zip_csv(url, nome_csv)
            if df is None:
                continue

            # Filtrar pela empresa
            df_empresa = df[df["CD_CVM"].astype(str) == str(codigo_cvm)].copy()
            if df_empresa.empty:
                logger.warning(f"  Empresa {codigo_cvm} não encontrada em {chave_doc} {ano}")
                continue

            resultado[chave_doc] = df_empresa
            logger.info(f"  DFP {chave_doc} {ano}: {len(df_empresa)} linhas")

        return resultado

    def baixar_dfp_multiplos_anos(self, codigo_cvm: str,
                                   anos: list[int],
                                   tipo: str = "con") -> dict[int, dict]:
        """Baixa DFPs para múltiplos anos e retorna um dict por ano."""
        dados = {}
        for ano in anos:
            logger.info(f"\n{'='*50}")
            logger.info(f"Baixando DFP {ano}...")
            dados[ano] = self.baixar_dfp(codigo_cvm, ano, tipo)
        return dados

    # ── ITR (trimestral) ──────────────────────────────────────────────────────

    def baixar_itr(self, codigo_cvm: str, ano: int,
                   trimestre: int = None,
                   tipo: str = "con") -> dict[str, pd.DataFrame]:
        """
        Baixa ITRs (dados trimestrais).

        Args:
            trimestre: 1, 2 ou 3 (o 4T é coberto pela DFP anual)
        """
        resultado = {}
        ano_str   = str(ano)

        docs = {
            "dre":    f"itr_cia_aberta_DRE_{tipo}_{ano_str}.csv",
            "bpa":    f"itr_cia_aberta_BPA_{tipo}_{ano_str}.csv",
            "bpp":    f"itr_cia_aberta_BPP_{tipo}_{ano_str}.csv",
        }

        for chave_doc, nome_csv in docs.items():
            url = f"{self.BASE_URL}/DOC/ITR/DADOS/itr_cia_aberta_{ano_str}.zip"
            df  = self._baixar_zip_csv(url, nome_csv)
            if df is None:
                continue

            df_empresa = df[df["CD_CVM"].astype(str) == str(codigo_cvm)].copy()
            if df_empresa.empty:
                continue

            # Filtrar por trimestre se especificado
            if trimestre and "DT_FIM_EXERC" in df_empresa.columns:
                df_empresa["DT_FIM_EXERC"] = pd.to_datetime(
                    df_empresa["DT_FIM_EXERC"], errors="coerce")
                meses_alvo = {1: 3, 2: 6, 3: 9}
                mes = meses_alvo.get(trimestre)
                if mes:
                    df_empresa = df_empresa[
                        df_empresa["DT_FIM_EXERC"].dt.month == mes]

            resultado[chave_doc] = df_empresa
            logger.info(f"  ITR {chave_doc} {ano} T{trimestre or 'todos'}: "
                        f"{len(df_empresa)} linhas")

        return resultado

    # ── Parser de demonstrações ───────────────────────────────────────────────

    def extrair_valores(self, df: pd.DataFrame,
                        codigos: list[str],
                        periodo: str = None) -> float:
        """
        Extrai e soma valores de contas específicas de um DataFrame CVM.

        Args:
            df:      DataFrame retornado pelas funções de download
            codigos: Lista de códigos de conta (ex: ["3.01", "3.01.01"])
            periodo: Data de referência (ex: "2023-12-31") ou None para o mais recente

        Returns:
            Soma dos valores encontrados
        """
        if df is None or df.empty:
            return 0.0

        # Coluna de código da conta
        col_cd = next((c for c in df.columns if "CD_CONTA" in c.upper()), None)
        col_vl = next((c for c in df.columns if "VL_CONTA" in c.upper()), None)
        col_dt = next((c for c in df.columns if "DT_FIM" in c.upper() or
                       "DT_REFER" in c.upper()), None)

        if not col_cd or not col_vl:
            logger.warning("Colunas CD_CONTA ou VL_CONTA não encontradas")
            return 0.0

        df_work = df.copy()

        # Filtrar período
        if periodo and col_dt:
            df_work[col_dt] = pd.to_datetime(df_work[col_dt], errors="coerce")
            target = pd.to_datetime(periodo, errors="coerce")
            if pd.notna(target):
                df_work = df_work[df_work[col_dt] == target]
            else:
                # Pegar o período mais recente
                df_work = df_work[
                    df_work[col_dt] == df_work[col_dt].max()]

        # Filtrar contas
        mask = df_work[col_cd].astype(str).isin([str(c) for c in codigos])

        # Evitar dupla contagem: preferir a linha mais específica (código mais longo)
        df_filtrado = df_work[mask].copy()
        if df_filtrado.empty:
            # Tenta busca parcial (conta pai)
            for cod in codigos:
                partial = df_work[df_work[col_cd].astype(str).str.startswith(str(cod))]
                df_filtrado = pd.concat([df_filtrado, partial])
            df_filtrado = df_filtrado.drop_duplicates(subset=[col_cd])

        if df_filtrado.empty:
            return 0.0

        try:
            total = pd.to_numeric(df_filtrado[col_vl], errors="coerce").sum()
            return float(total) if pd.notna(total) else 0.0
        except Exception:
            return 0.0

    def montar_serie_historica(self, dados_por_ano: dict[int, dict],
                                mapa_contas: dict,
                                tipo_doc: str = "dre") -> pd.DataFrame:
        """
        Monta uma série histórica de contas a partir dos dados baixados.

        Returns:
            DataFrame com índice = nome_conta e colunas = anos
        """
        anos   = sorted(dados_por_ano.keys())
        resultado = {}

        for nome_conta, config in mapa_contas.items():
            if config.get("calculado"):
                continue   # será calculado depois

            serie = {}
            for ano in anos:
                dfs = dados_por_ano.get(ano, {})
                df  = dfs.get(tipo_doc)
                if df is None:
                    serie[ano] = 0.0
                    continue

                # Determinar período (31/12 para DFP)
                periodo = f"{ano}-12-31"
                valor   = self.extrair_valores(df, config["codigos"], periodo)
                sinal   = config.get("sinal", 1)
                serie[ano] = valor * sinal

            resultado[nome_conta] = serie

        return pd.DataFrame(resultado).T  # contas × anos

    def salvar_dados_brutos(self, dados: dict, caminho: Path):
        """Salva dados brutos em JSON para debugging."""
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            # Converter DataFrames para dict antes de serializar
            serializavel = {}
            for k, v in dados.items():
                if isinstance(v, dict):
                    serializavel[k] = {
                        str(k2): vv.to_dict("records")
                        if isinstance(vv, pd.DataFrame) else vv
                        for k2, vv in v.items()
                    }
                else:
                    serializavel[k] = v
            json.dump(serializavel, f, ensure_ascii=False, default=str, indent=2)
        logger.info(f"Dados brutos salvos em: {caminho}")
