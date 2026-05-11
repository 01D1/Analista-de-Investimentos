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

    def _zip_cache_path(self, url: str) -> Path:
        nome = hashlib.md5(url.encode()).hexdigest() + ".zip"
        return self.cache_dir / "cvm_zips" / nome

    def _cache_valido(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < self.cache_ttl

    def _ler_cache(self, chave: str):
        p = self._cache_path(chave)
        if self.usar_cache and self._cache_valido(p):
            logger.debug(f"Cache HIT: {chave[:60]}")
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Cache corrompido ({p.name}): {e} — re-baixando")
                try:
                    p.unlink()
                except OSError:
                    pass  # sem permissão para apagar
        return None

    def _salvar_cache(self, chave: str, dados):
        p = self._cache_path(chave)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, default=str)

    def _baixar_zip_bytes(self, url: str) -> Optional[bytes]:
        zip_path = self._zip_cache_path(url)
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if self.usar_cache and self._cache_valido(zip_path):
            logger.debug(f"Cache ZIP CVM HIT: {url}")
            return zip_path.read_bytes()

        logger.info(f"Baixando: {url}")
        try:
            resp = self.session.get(url, timeout=self.TIMEOUT, stream=True)
            resp.raise_for_status()
            conteudo = b"".join(resp.iter_content(chunk_size=self.CHUNK_SIZE))
            zip_path.write_bytes(conteudo)
            return conteudo
        except requests.RequestException as e:
            logger.error(f"Erro ao baixar {url}: {e}")
            return None

    # ── Download genérico ─────────────────────────────────────────────────────

    def _baixar_zip_csv(self, url: str, nome_arquivo: str) -> Optional[pd.DataFrame]:
        """Baixa um ZIP da CVM e extrai o CSV interno."""
        # A chave inclui nome_arquivo porque o mesmo ZIP anual contém múltiplos CSVs
        # (DRE, BPA, BPP, DFC_MI, DFC_MD) — cada um precisa de cache separado.
        chave = f"zip:{url}:{nome_arquivo}"
        cached = self._ler_cache(chave)
        if cached is not None:
            return pd.DataFrame(cached)

        try:
            conteudo = self._baixar_zip_bytes(url)
            if not conteudo:
                return None

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
        """Baixa DFPs para múltiplos anos e retorna um dict por ano.
        Anos cujo DFP não existe na CVM são retornados com dict vazio (não crasham)."""
        dados = {}
        for ano in anos:
            logger.info(f"\n{'='*50}")
            logger.info(f"Baixando DFP {ano}...")
            try:
                dados[ano] = self.baixar_dfp(codigo_cvm, ano, tipo)
            except Exception as e:
                logger.warning(f"  DFP {ano} indisponível: {e}")
                dados[ano] = {}
        return dados

    def baixar_dfp_multiplos_anos_auto(self, codigo_cvm: str,
                                        anos: list[int]) -> dict[int, dict]:
        """
        Baixa DFPs preferindo consolidado (con) e usando individual (ind)
        apenas quando o consolidado nao traz DRE, BPA e BPP completos.
        """
        dados = {}
        for ano in anos:
            logger.info(f"\n{'='*50}")
            logger.info(f"Baixando DFP {ano} (preferencia: con, fallback: ind)...")
            try:
                dados_con = self.baixar_dfp(codigo_cvm, ano, tipo="con")
                if self._tem_docs_minimos(dados_con):
                    dados[ano] = dados_con
                    logger.info(f"  DFP {ano}: usando consolidado (con)")
                    continue

                logger.warning(
                    f"  DFP {ano} consolidado incompleto — tentando individual (ind)"
                )
                dados_ind = self.baixar_dfp(codigo_cvm, ano, tipo="ind")
                if self._tem_docs_minimos(dados_ind):
                    dados[ano] = dados_ind
                    logger.info(f"  DFP {ano}: usando individual (ind)")
                else:
                    dados[ano] = dados_con or dados_ind or {}
            except Exception as e:
                logger.warning(f"  DFP {ano} indisponível: {e}")
                dados[ano] = {}
        return dados

    @staticmethod
    def _tem_docs_minimos(dados: dict[str, pd.DataFrame]) -> bool:
        if not dados:
            return False
        for doc in ["dre", "bpa", "bpp"]:
            df = dados.get(doc)
            if df is None or (hasattr(df, "empty") and df.empty):
                return False
        return True

    # ── ITR (trimestral) ──────────────────────────────────────────────────────

    def baixar_itr(self, codigo_cvm: str, ano: int,
                   trimestre: int = None,
                   tipo: str = "con") -> dict[str, pd.DataFrame]:
        """
        Baixa ITRs (dados trimestrais).

        Args:
            trimestre: 1, 2 ou 3 (o 4T é coberto pela DFP anual).
                       None = todos os trimestres disponíveis.
        """
        resultado = {}
        ano_str   = str(ano)

        docs = {
            "dre":    f"itr_cia_aberta_DRE_{tipo}_{ano_str}.csv",
            "bpa":    f"itr_cia_aberta_BPA_{tipo}_{ano_str}.csv",
            "bpp":    f"itr_cia_aberta_BPP_{tipo}_{ano_str}.csv",
            "dfc_mi": f"itr_cia_aberta_DFC_MI_{tipo}_{ano_str}.csv",
            "dfc_md": f"itr_cia_aberta_DFC_MD_{tipo}_{ano_str}.csv",
        }

        for chave_doc, nome_csv in docs.items():
            url = f"{self.BASE_URL}/DOC/ITR/DADOS/itr_cia_aberta_{ano_str}.zip"
            df  = self._baixar_zip_csv(url, nome_csv)
            if df is None:
                continue
            if "CD_CVM" not in df.columns:
                logger.warning(
                    f"  ITR {chave_doc} {ano} sem coluna CD_CVM — arquivo ignorado"
                )
                continue

            df_empresa = df[df["CD_CVM"].astype(str) == str(codigo_cvm)].copy()
            if df_empresa.empty:
                logger.debug(f"  Empresa {codigo_cvm} não encontrada em ITR {chave_doc} {ano}")
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

    def _detectar_ultimo_trimestre(self, df_itr: pd.DataFrame, ano: int) -> int:
        """Detecta o último trimestre disponível no ITR para o ano dado."""
        if df_itr is None or df_itr.empty:
            return 0
        df_work = df_itr.copy()
        df_work["DT_FIM_EXERC"] = pd.to_datetime(df_work["DT_FIM_EXERC"], errors="coerce")
        # Filtrar: ORDEM_EXERC == 'ÚLTIMO' e ano correto
        mask = (
            (df_work["ORDEM_EXERC"] == "ÚLTIMO") &
            (df_work["DT_FIM_EXERC"].dt.year == ano)
        )
        datas = df_work.loc[mask, "DT_FIM_EXERC"].dropna().unique()
        if len(datas) == 0:
            return 0
        ultimo_mes = max(pd.Timestamp(d).month for d in datas)
        return {3: 1, 6: 2, 9: 3}.get(ultimo_mes, 0)

    def anualizar_via_itr(self, codigo_cvm: str, ano_alvo: int,
                           dados_dfp_anterior: dict,
                           tipo: str = "con") -> dict[str, pd.DataFrame]:
        """
        Constrói dados anualizados (LTM) a partir de ITRs quando o DFP ainda
        não foi publicado.

        Lógica para contas de FLUXO (DRE, DFC):
          LTM = Acum_N_meses_atual + (DFP_ano_anterior - Acum_N_meses_anterior)
          Ex: se temos 3T (9 meses de 2025):
              LTM = Acum_9m_2025 + (DFP_2024 - Acum_9m_2024)
              = jan-set 2025 + out-dez 2024

        Lógica para contas de ESTOQUE (BPA, BPP):
          Usar a posição mais recente diretamente.

        Args:
            codigo_cvm: Código CVM da empresa
            ano_alvo: Ano que queremos anualizar (ex: 2025)
            dados_dfp_anterior: Dict com DFP do ano anterior (ex: 2024)
                                no formato {dre: DataFrame, bpa: DataFrame, ...}
            tipo: "con" ou "ind"

        Returns:
            Dict no mesmo formato que baixar_dfp() retorna,
            com DataFrames sintéticos representando o LTM.
            Retorna dict vazio se não for possível anualizar.
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"Tentando anualizar {ano_alvo} via ITR (LTM)...")

        # 1. Baixar ITRs do ano-alvo
        itr_atual = self.baixar_itr(codigo_cvm, ano_alvo, trimestre=None, tipo=tipo)
        if not itr_atual or "dre" not in itr_atual:
            logger.warning(f"  ITR {ano_alvo} não disponível — não é possível anualizar")
            return {}

        # 2. Detectar último trimestre disponível
        ult_tri = self._detectar_ultimo_trimestre(itr_atual["dre"], ano_alvo)
        if ult_tri == 0:
            logger.warning(f"  Nenhum trimestre detectado para {ano_alvo}")
            return {}

        meses_acum = {1: 3, 2: 6, 3: 9}[ult_tri]
        dt_fim_atual = f"{ano_alvo}-{meses_acum:02d}-{[0,31,30,30][ult_tri]:02d}"
        dt_fim_anterior = f"{ano_alvo - 1}-{meses_acum:02d}-{[0,31,30,30][ult_tri]:02d}"

        logger.info(f"  Último trimestre: {ult_tri}T{ano_alvo} ({meses_acum} meses)")
        logger.info(f"  LTM = Acum {meses_acum}m/{ano_alvo} + (DFP {ano_alvo-1} - Acum {meses_acum}m/{ano_alvo-1})")

        # 3. Verificar que temos DFP do ano anterior
        if not dados_dfp_anterior:
            logger.warning(f"  DFP {ano_alvo - 1} não disponível — usando apenas ITR parcial")
            # Fallback: extrapolar linearmente
            return self._extrapolar_itr(itr_atual, ano_alvo, ult_tri)

        resultado = {}

        # ── 4a. Anualizar contas de FLUXO (DRE, DFC) ─────────────────────
        for doc_tipo in ["dre", "dfc_mi", "dfc_md"]:
            df_itr = itr_atual.get(doc_tipo)
            df_dfp = dados_dfp_anterior.get(doc_tipo)

            if df_itr is None or df_itr.empty:
                continue

            df_ltm = self._anualizar_fluxo(
                df_itr, df_dfp, ano_alvo, ult_tri, doc_tipo)

            if df_ltm is not None and not df_ltm.empty:
                resultado[doc_tipo] = df_ltm
                logger.info(f"  LTM {doc_tipo}: {len(df_ltm)} linhas")

        # ── 4b. Balanço: usar posição mais recente ────────────────────────
        for doc_tipo in ["bpa", "bpp"]:
            df_itr = itr_atual.get(doc_tipo)
            if df_itr is None or df_itr.empty:
                continue

            df_bal = self._extrair_posicao_mais_recente(
                df_itr, ano_alvo, doc_tipo)

            if df_bal is not None and not df_bal.empty:
                resultado[doc_tipo] = df_bal
                logger.info(f"  Balanço {doc_tipo} (posição {ult_tri}T{ano_alvo}): {len(df_bal)} linhas")

        if resultado:
            logger.info(f"  Anualização {ano_alvo} concluída com sucesso ({ult_tri}T LTM)")
        else:
            logger.warning(f"  Anualização {ano_alvo} falhou — sem dados suficientes")

        return resultado

    def _anualizar_fluxo(self, df_itr: pd.DataFrame,
                          df_dfp: Optional[pd.DataFrame],
                          ano_alvo: int, ult_tri: int,
                          doc_tipo: str) -> Optional[pd.DataFrame]:
        """
        Anualiza uma demonstração de fluxo (DRE ou DFC).

        LTM = Acum_N_meses_atual + (DFP_anterior - Acum_N_meses_anterior)
        """
        meses_acum = {1: 3, 2: 6, 3: 9}[ult_tri]
        ultimo_dia = {3: 31, 6: 30, 9: 30}[meses_acum]

        df_work = df_itr.copy()
        df_work["DT_FIM_EXERC"] = pd.to_datetime(df_work["DT_FIM_EXERC"], errors="coerce")
        df_work["DT_INI_EXERC"] = pd.to_datetime(df_work["DT_INI_EXERC"], errors="coerce")

        # Acumulado do ano atual: ORDEM='ÚLTIMO', DT_INI=01/01/ano_alvo, DT_FIM=último tri
        dt_fim_atual = pd.Timestamp(f"{ano_alvo}-{meses_acum:02d}-{ultimo_dia:02d}")
        dt_ini_atual = pd.Timestamp(f"{ano_alvo}-01-01")

        mask_atual = (
            (df_work["ORDEM_EXERC"] == "ÚLTIMO") &
            (df_work["DT_INI_EXERC"] == dt_ini_atual) &
            (df_work["DT_FIM_EXERC"] == dt_fim_atual)
        )
        acum_atual = df_work[mask_atual].copy()

        if acum_atual.empty:
            logger.debug(f"  Acumulado {meses_acum}m/{ano_alvo} vazio para {doc_tipo}")
            return None

        # Acumulado do mesmo período do ano anterior: ORDEM='PENÚLTIMO'
        dt_fim_ant = pd.Timestamp(f"{ano_alvo - 1}-{meses_acum:02d}-{ultimo_dia:02d}")
        dt_ini_ant = pd.Timestamp(f"{ano_alvo - 1}-01-01")

        mask_ant = (
            (df_work["ORDEM_EXERC"] == "PENÚLTIMO") &
            (df_work["DT_INI_EXERC"] == dt_ini_ant) &
            (df_work["DT_FIM_EXERC"] == dt_fim_ant)
        )
        acum_anterior = df_work[mask_ant].copy()

        # Montar LTM
        # Criar dict {CD_CONTA: valor} para cada parte
        val_col = "VL_CONTA"
        cd_col  = "CD_CONTA"

        acum_at = acum_atual.set_index(cd_col)[val_col].apply(
            lambda x: float(x) if pd.notna(x) else 0.0)
        acum_an = acum_anterior.set_index(cd_col)[val_col].apply(
            lambda x: float(x) if pd.notna(x) else 0.0) if not acum_anterior.empty else pd.Series(dtype=float)

        # DFP anterior: pegar valores de 31/12
        dfp_vals = pd.Series(dtype=float)
        if df_dfp is not None and not df_dfp.empty:
            df_dfp_c = df_dfp.copy()
            # DFP já tem o acumulado anual completo
            # Pegar a versão mais recente (última VERSAO)
            if "VERSAO" in df_dfp_c.columns:
                max_ver = df_dfp_c["VERSAO"].max()
                df_dfp_c = df_dfp_c[df_dfp_c["VERSAO"] == max_ver]
            dfp_vals = df_dfp_c.set_index(cd_col)[val_col].apply(
                lambda x: float(x) if pd.notna(x) else 0.0)
            # Remover duplicatas (pegar primeiro)
            dfp_vals = dfp_vals[~dfp_vals.index.duplicated(keep='first')]

        # LTM = acum_atual + (dfp_anterior - acum_anterior)
        # Alinhar todas as contas
        todas_contas = set(acum_at.index)
        if not dfp_vals.empty:
            todas_contas |= set(dfp_vals.index)

        ltm_values = {}
        for conta in todas_contas:
            v_at  = acum_at.get(conta, 0.0)
            v_dfp = dfp_vals.get(conta, 0.0) if not dfp_vals.empty else 0.0
            v_an  = acum_an.get(conta, 0.0) if not acum_an.empty else 0.0
            ltm_values[conta] = v_at + (v_dfp - v_an)

        # Reconstruir DataFrame no formato CVM (para compatibilidade com normalizador)
        # Usar o acum_atual como template
        df_ltm = acum_atual.copy()
        df_ltm[val_col] = df_ltm[cd_col].map(ltm_values)
        # Ajustar datas para simular DFP anual
        df_ltm["DT_FIM_EXERC"] = f"{ano_alvo}-12-31"
        df_ltm["DT_INI_EXERC"] = f"{ano_alvo}-01-01"
        df_ltm["ORDEM_EXERC"]  = "ÚLTIMO"

        return df_ltm

    def _extrair_posicao_mais_recente(self, df_itr: pd.DataFrame,
                                       ano_alvo: int,
                                       doc_tipo: str) -> Optional[pd.DataFrame]:
        """Extrai a posição patrimonial mais recente do ITR."""
        df_work = df_itr.copy()
        df_work["DT_FIM_EXERC"] = pd.to_datetime(df_work["DT_FIM_EXERC"], errors="coerce")

        # Filtrar: ORDEM='ÚLTIMO' e ano correto
        mask = (
            (df_work["ORDEM_EXERC"] == "ÚLTIMO") &
            (df_work["DT_FIM_EXERC"].dt.year == ano_alvo)
        )
        df_filtrado = df_work[mask]

        if df_filtrado.empty:
            return None

        # Pegar a data mais recente
        dt_max = df_filtrado["DT_FIM_EXERC"].max()
        df_pos = df_filtrado[df_filtrado["DT_FIM_EXERC"] == dt_max].copy()

        # Ajustar para formato compatível com DFP (simular 31/12)
        df_pos["DT_FIM_EXERC"] = f"{ano_alvo}-12-31"
        df_pos["DT_INI_EXERC"] = f"{ano_alvo}-01-01"

        return df_pos

    def _extrapolar_itr(self, itr_atual: dict, ano_alvo: int,
                         ult_tri: int) -> dict:
        """
        Fallback: extrapola ITR parcial para anual (quando DFP anterior não existe).
        Método simples: (acum_N_meses / N) × 12 para DRE.
        """
        meses = {1: 3, 2: 6, 3: 9}[ult_tri]
        fator = 12.0 / meses
        resultado = {}

        for doc_tipo in ["dre", "dfc_mi", "dfc_md"]:
            df_itr = itr_atual.get(doc_tipo)
            if df_itr is None or df_itr.empty:
                continue

            df_work = df_itr.copy()
            df_work["DT_FIM_EXERC"] = pd.to_datetime(df_work["DT_FIM_EXERC"], errors="coerce")
            df_work["DT_INI_EXERC"] = pd.to_datetime(df_work["DT_INI_EXERC"], errors="coerce")

            dt_ini = pd.Timestamp(f"{ano_alvo}-01-01")
            ultimo_dia = {3: 31, 6: 30, 9: 30}[meses]
            dt_fim = pd.Timestamp(f"{ano_alvo}-{meses:02d}-{ultimo_dia:02d}")

            mask = (
                (df_work["ORDEM_EXERC"] == "ÚLTIMO") &
                (df_work["DT_INI_EXERC"] == dt_ini) &
                (df_work["DT_FIM_EXERC"] == dt_fim)
            )
            df_acum = df_work[mask].copy()
            if df_acum.empty:
                continue

            df_acum["VL_CONTA"] = pd.to_numeric(df_acum["VL_CONTA"], errors="coerce") * fator
            df_acum["DT_FIM_EXERC"] = f"{ano_alvo}-12-31"
            df_acum["DT_INI_EXERC"] = f"{ano_alvo}-01-01"
            resultado[doc_tipo] = df_acum
            logger.info(f"  Extrapolado {doc_tipo} ({meses}m × {fator:.1f}): {len(df_acum)} linhas")

        # Balanço: posição mais recente
        for doc_tipo in ["bpa", "bpp"]:
            df_itr = itr_atual.get(doc_tipo)
            if df_itr is None or df_itr.empty:
                continue
            df_bal = self._extrair_posicao_mais_recente(df_itr, ano_alvo, doc_tipo)
            if df_bal is not None and not df_bal.empty:
                resultado[doc_tipo] = df_bal

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
