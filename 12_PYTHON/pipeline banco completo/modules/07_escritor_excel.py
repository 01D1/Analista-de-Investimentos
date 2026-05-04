"""
Módulo 07 — Escritor Excel
Popula o template Template_Valuation_Banco.xlsx com os dados
coletados, normalizados e projetados.

Estratégia:
  - Localiza cada aba pelo nome
  - Mapeia linhas pelo label na coluna D
  - Preenche colunas de anos históricos (azul → sobescreve com dado real)
  - Preenche colunas de projeção (verde → fórmula que pode ser editada)
  - Preserva toda a formatação original
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Union
import re

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter, column_index_from_string

logger = logging.getLogger("pipeline.excel")


# ── Constantes de formatação ────────────────────────────────────────────────
C_BLUE   = "0000FF"   # inputs / dados reais
C_GREEN  = "008000"   # links / projeções
C_BLACK  = "000000"   # fórmulas
NUM_FMT  = '#,##0;(#,##0);"-"'
PCT_FMT2 = '0.00%;(0.00%);"-"'
PCT_FMT1 = '0.0%;(0.0%);"-"'


def _font(color=C_BLACK, bold=False, size=9):
    return Font(color=color, bold=bold, size=size, name="Arial")

def _thin_bottom():
    s = Side(style="thin", color="BFBFBF")
    return Border(bottom=s)


class EscritorExcel:
    """Escreve dados no template Excel."""

    # Mapeamento: label no template → chave nos dados normalizados
    MAPA_LINHAS_DRE = {
        "Margem Financeira Bruta":                   "margem_financeira_bruta",
        "  Margem Financeira com Clientes":          "margem_clientes",
        "  Margem Financeira com Mercado":           "margem_mercado",
        "Despesa de Provisão Expandida":             "provisao_credito",
        "Margem Financeira Líquida":                 "margem_financeira_liquida",
        "Resultado de Operações de Seguros":         "resultado_seguros",
        "Receitas de Prestação de Serviços":         "receita_servicos",
        "Despesas de Pessoal":                       "despesa_pessoal",
        "Outras Despesas Operacionais":              "outras_despesas_operacionais",
        "Resultado de Participações (Previ)":        "resultado_participacoes",
        "RESULTADO OPERACIONAL":                     "resultado_operacional",
        "RESULTADO ANTES DO IR":                     "resultado_antes_ir",
        "Imposto de Renda e CSLL":                   "ir_csll",
        "RESULTADO ANTES DE MINORITÁRIOS":           "resultado_antes_minoritarios",
        "Participações Estatutárias":                "participacoes_estatutarias",
        "Participações Minoritárias":                "participacoes_minoritarias",
        "LUCRO LÍQUIDO (CONTROLADORES)":             "lucro_liquido",
    }

    MAPA_LINHAS_DCF = {
        "Lucro Líquido (Controladores)":             "lucro_liquido",
        "(+) Depreciação e Amortização":             "da",
        "(-) CAPEX":                                 "capex",
        "(-) Variação Capital Regulatório":          "capital_regulatorio",
        "FCFE (Fluxo de Caixa ao Acionista)":        "fcfe",
    }

    MAPA_LINHAS_BP_ATIVO = {
        "Ativos Remuneráveis":                       "ativos_remuneraveis",
        "  Carteira de Crédito Expandida":           "carteira_credito_bruta",
        "  TVM e Instrumentos Financeiros Derivativos": "tvm_derivativos",
        "  Aplicações Interfinanceiras de Liquidez": "aplicacoes_interfinanceiras",
        "Provisões para Perdas de Crédito":          "provisao_pdd",
        "Créditos Tributários":                      "creditos_tributarios",
        "ATIVO TOTAL":                               "ativo_total",
    }

    MAPA_LINHAS_BP_PASSIVO = {
        "  Depósitos à Vista":                       "depositos_vista",
        "  Depósitos de Poupança":                   "depositos_poupanca",
        "  Depósitos a Prazo":                       "depositos_prazo",
        "Depósitos Total":                           "depositos_total",
        "Captações no Mercado Aberto":               "captacoes_mercado_aberto",
        "Recursos de Emissão de Títulos":            "recursos_emissao_titulos",
        "Obrigações por Empréstimos e Repasses":     "obrigacoes_emprestimos",
        "Dívidas Subordinadas":                      "dividas_subordinadas",
        "PATRIMÔNIO LÍQUIDO":                        "patrimonio_liquido",
    }

    MAPA_LINHAS_NIM = {
        "Selic Média (% a.a.)":                      "selic_efet",
        "IPCA (% a.a.)":                             "ipca",
        "TJLP (% a.a.)":                             "tjlp",
        "DI (% a.a.)":                               "di",
        "Net Interest Margin — NIM (% a.a.)":        "nim",
        "Margem Financeira Bruta":                   "margem_financeira_bruta",
        "  Margem com Clientes":                     "margem_clientes",
        "  Margem com Mercado":                      "margem_mercado",
        "Despesa de Provisão":                       "provisao_credito",
        "Margem Financeira Líquida":                 "margem_financeira_liquida",
        "Total Ativos Rentáveis":                    "ativos_remuneraveis",
        "  Carteira de Crédito Expandida":           "carteira_credito_bruta",
    }

    MAPA_INDICADORES = {
        "ROE (Lucro/PL Médio)":                      "roe",
        "ROA (Lucro/Ativo Médio)":                   "roa",
        "NIM (Margem Financeira/Ativos Rent.)":      "nim",
        "Margem Líquida (Lucro/Receita Total)":      "margem_liquida",
        "Spread Global (Rent. Ativo − Custo Pass.)": "spread_global",
        "Independência Financeira (PL/Ativo)":       "independencia_financeira",
        "Alavancagem (Ativo/PL)":                    "alavancagem",
        "Índice Empréstimos/Depósitos":              "emp_depositos",
        "Participação dos Empréstimos nos Ativos":   "part_emprestimos",
        "Provisão/Carteira de Crédito (%)":          "pcld_carteira",
    }

    def __init__(self, caminho_template: Path, ticker: str,
                 anos_historicos: list[int], anos_projecao: list[int]):
        self.template      = Path(caminho_template)
        self.ticker        = ticker
        self.anos_hist     = sorted(anos_historicos)
        self.anos_proj     = sorted(anos_projecao)
        self.todos_anos    = self.anos_hist + self.anos_proj

    def _abrir_template(self, destino: Path):
        """Copia o template e abre para edição."""
        shutil.copy2(self.template, destino)
        return load_workbook(destino)

    # ── Mapeamento de colunas ─────────────────────────────────────────────────

    def _mapear_colunas_anos(self, ws) -> dict[Union[int, str], int]:
        """
        Percorre a linha 4 da aba e retorna {ano_ou_str: col_index}.
        Ex: {2019: 5, 2020: 6, ..., "1T25": 10, 2025: 11, ...}
        """
        mapa = {}
        for col in range(1, ws.max_column + 1):
            val = ws.cell(row=4, column=col).value
            if val is None:
                continue
            try:
                mapa[int(str(val))] = col
            except (ValueError, TypeError):
                # Strings como "1T25", "YTD25", etc.
                if isinstance(val, str) and re.match(r'\dT\d{2}|YTD|YTG', val):
                    mapa[val] = col
        return mapa

    def _mapear_linhas_por_label(self, ws, col_label: int = 4) -> dict[str, int]:
        """
        Percorre a coluna D e retorna {label_normalizado: row_index}.
        Normaliza espaços e capitalização para matching tolerante.
        """
        mapa = {}
        for row in range(1, ws.max_row + 1):
            val = ws.cell(row=row, column=col_label).value
            if val and isinstance(val, str):
                # Chave normalizada: strip, lower
                chave = val.strip().lower()
                mapa[chave] = row
                # Também mapeia versão original
                mapa[val.strip()] = row
        return mapa

    def _match_label(self, labels_ws: dict, label_procurado: str) -> Optional[int]:
        """Tenta encontrar label com matching tolerante."""
        # Exact match
        if label_procurado in labels_ws:
            return labels_ws[label_procurado]
        # Lowercase match
        chave_lower = label_procurado.strip().lower()
        if chave_lower in labels_ws:
            return labels_ws[chave_lower]
        # Partial match (remove espaços duplos, acentos alternativos)
        for k, v in labels_ws.items():
            if isinstance(k, str) and label_procurado.strip().lower() in k.lower():
                return v
        return None

    # ── Escrita de valores ────────────────────────────────────────────────────

    def _escrever_valor(self, ws, row: int, col: int,
                         valor, eh_historico: bool = True,
                         num_fmt: str = NUM_FMT):
        """Escreve um valor na célula com formatação correta."""
        cell = ws.cell(row=row, column=col)
        if isinstance(valor, str) and valor.startswith("="):
            cell.value = valor
            cell.font  = _font(C_GREEN if not eh_historico else C_BLACK)
        elif isinstance(valor, (int, float)):
            cell.value         = round(valor, 3)
            cell.font          = _font(C_BLUE if eh_historico else C_GREEN)
            cell.number_format = num_fmt
        else:
            cell.value = valor
            cell.font  = _font()

        cell.alignment = Alignment(horizontal="right", vertical="center")
        cell.border    = _thin_bottom()

    def _preencher_linha(self, ws, row: int,
                          dados_hist: dict[int, float],
                          dados_proj: dict[int, float],
                          col_mapa: dict,
                          num_fmt: str = NUM_FMT):
        """Preenche uma linha completa com histórico e projeção."""
        for ano, valor in dados_hist.items():
            col = col_mapa.get(ano)
            if col:
                self._escrever_valor(ws, row, col, valor,
                                      eh_historico=True, num_fmt=num_fmt)

        for ano, valor in dados_proj.items():
            col = col_mapa.get(ano)
            if col:
                self._escrever_valor(ws, row, col, valor,
                                      eh_historico=False, num_fmt=num_fmt)

    # ── Cabeçalho da empresa ──────────────────────────────────────────────────

    def _atualizar_cabecalho(self, wb, nome: str, ticker: str):
        """Atualiza o nome da empresa em todas as abas."""
        texto = f"{ticker} — {nome}"
        for ws in wb.worksheets:
            for row in ws.iter_rows(max_row=3):
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if "[TICKER]" in cell.value:
                            cell.value = cell.value.replace(
                                "[TICKER]", ticker).replace(
                                "Banco [Nome]", nome)

    # ── Populadores por aba ───────────────────────────────────────────────────

    def popular_dashboard(self, wb, dados: dict):
        """Popula a aba Dashboard."""
        ws     = wb["Dashboard"]
        mercado = dados.get("mercado", {})

        campos = {
            "Ticker":                 self.ticker,
            "Valor do Equity (R$ MM)": dados.get("equity_mm", 0),
            "Preço Justo por Ação ON (R$)": dados.get("preco_justo_on", 0),
            "Preço Justo por Ação PN (R$)": dados.get("preco_justo_pn", 0),
            "Cotação ON":             mercado.get("preco", 0),
        }

        labels_ws = self._mapear_linhas_por_label(ws, col_label=4)
        for label, valor in campos.items():
            row = self._match_label(labels_ws, label)
            if row:
                ws.cell(row=row, column=5, value=valor)

        # Ações emitidas
        acoes = mercado.get("acoes_total", 0)
        row_acoes = self._match_label(labels_ws, "Ações Emitidas ON")
        if row_acoes:
            ws.cell(row=row_acoes, column=5, value=acoes)

    def popular_ke(self, wb, macro: dict):
        """Popula a aba Ke com taxas históricas e projetadas."""
        ws       = wb["Ke"]
        hist     = macro.get("historico", {})
        proj     = macro.get("projecao", {})

        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        def linha(label, chave_hist, chave_proj, fmt=PCT_FMT2):
            row = self._match_label(labels, label)
            if not row:
                return
            h = hist.get(chave_hist, {})
            p = proj.get(chave_proj, {})
            self._preencher_linha(ws, row, h, p, col_mapa, fmt)

        linha("DI (% a.a.)",                "selic_efet",    "di")
        linha("CDS Brasil (% a.a.)",         "cds",           "cds")
        linha("Inflação Implícita (% a.a.)", "inflacao_impl", "inflacao_impl")
        linha("TJLP (% a.a.)",               "tjlp",          "tjlp")

        # Beta — histórico
        beta_data = macro.get("beta", {})
        if beta_data.get("serie_diaria") is not None:
            serie = beta_data["serie_diaria"]
            # Encontrar início da tabela de beta
            for start_row in range(15, ws.max_row):
                v = ws.cell(row=start_row, column=4).value
                if v and "data" in str(v).lower():
                    for i, (_, r) in enumerate(serie.iterrows()):
                        rr = start_row + 1 + i
                        ws.cell(row=rr, column=4).value = r.get("data", "")
                        ws.cell(row=rr, column=5).value = round(
                            float(r.get("ibov_var", 0)), 6)
                        ws.cell(row=rr, column=6).value = round(
                            float(r.get("acao_var", 0)), 6)
                    break

    def popular_dre(self, wb, dre_hist: pd.DataFrame,
                     projecoes: dict):
        """Popula a aba DRE Recorrente."""
        ws       = wb["DRE Recorrente"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        for label_template, chave_dados in self.MAPA_LINHAS_DRE.items():
            row = self._match_label(labels, label_template)
            if not row:
                logger.debug(f"  Label não encontrado na DRE: {label_template}")
                continue

            # Histórico: do DataFrame normalizado
            hist_serie = {}
            if chave_dados in dre_hist.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(dre_hist.loc[chave_dados, ano])
                    except Exception:
                        pass

            # Projeção: do dict de projeções
            proj_serie = projecoes.get(chave_dados, {})

            # Formato: % para crescimento, R$ MM para valores
            fmt = PCT_FMT1 if "crescimento" in label_template.lower() else NUM_FMT

            self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa, fmt)

            # Linha de crescimento YoY (logo abaixo)
            row_yoy = self._match_label(labels, f"  Crescimento YoY (%)")
            if row_yoy and row_yoy == row + 1:
                todos_dados = {**hist_serie, **proj_serie}
                anos_sorted = sorted(todos_dados.keys())
                for i, ano in enumerate(anos_sorted[1:], 1):
                    ant = anos_sorted[i-1]
                    vant = todos_dados.get(ant, 0)
                    vat  = todos_dados.get(ano, 0)
                    if vant and vant != 0:
                        g = vat / abs(vant) - 1
                    else:
                        g = 0
                    col = col_mapa.get(ano)
                    if col:
                        self._escrever_valor(ws, row_yoy, col, g,
                                              eh_historico=(ano in self.anos_hist),
                                              num_fmt=PCT_FMT1)

    def popular_balanco(self, wb, bp_hist: pd.DataFrame,
                         projecoes_bp: dict):
        """Popula a aba Balanço Patrimonial."""
        ws       = wb["Balanço Patrimonial"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        for mapa in [self.MAPA_LINHAS_BP_ATIVO, self.MAPA_LINHAS_BP_PASSIVO]:
            for label, chave in mapa.items():
                row = self._match_label(labels, label)
                if not row:
                    continue

                hist_serie = {}
                if chave in bp_hist.index:
                    for ano in self.anos_hist:
                        try:
                            hist_serie[ano] = float(bp_hist.loc[chave, ano])
                        except Exception:
                            pass

                proj_serie = projecoes_bp.get(chave, {})
                self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa)

    def popular_dcf(self, wb, dre_hist: pd.DataFrame,
                     projecoes: dict, valuation: dict):
        """Popula a aba DRE + DCF incluindo o bloco de valuation."""
        ws       = wb["DRE + DCF"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        for label, chave in self.MAPA_LINHAS_DCF.items():
            row = self._match_label(labels, label)
            if not row:
                continue

            hist_serie = {}
            if chave in dre_hist.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(dre_hist.loc[chave, ano])
                    except Exception:
                        pass

            proj_serie = projecoes.get(chave, {})
            self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa)

        # Valuation
        campos_val = {
            "VALOR DO EQUITY (R$ MM)":     valuation.get("equity_mm", 0),
            "Preço Justo ON (R$)":         valuation.get("preco_justo_on", 0),
            "Preço Justo PN (R$)":         valuation.get("preco_justo_pn", 0),
            "UPSIDE ON (%)":               valuation.get("upside_on", 0),
            "UPSIDE PN (%)":               valuation.get("upside_pn", 0),
            "TIR (ON) — função XIRR":      valuation.get("tir_on", 0),
            "TIR (PN) — função XIRR":      valuation.get("tir_pn", 0),
            "PREÇO TETO ON":               valuation.get("preco_teto_on", 0),
            "PREÇO TETO PN":               valuation.get("preco_teto_pn", 0),
        }

        # Esses valores ficam numa única coluna (coluna final)
        col_val = col_mapa.get("Perpetuidade") or (max(col_mapa.values()) - 2)
        for label, valor in campos_val.items():
            row = self._match_label(labels, label)
            if row:
                fmt = PCT_FMT1 if "%" in label or "TIR" in label or "UPSIDE" in label else NUM_FMT
                self._escrever_valor(ws, row, 5, valor, eh_historico=False, num_fmt=fmt)

    def popular_nim(self, wb, indicadores_hist: pd.DataFrame,
                     macro: dict, projecoes: dict):
        """Popula a aba Projeções - NIM."""
        ws       = wb["Projeções - NIM"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        hist_macro = macro.get("historico", {})
        proj_macro = macro.get("projecao", {})

        for label, chave in self.MAPA_LINHAS_NIM.items():
            row = self._match_label(labels, label)
            if not row:
                continue

            # Dados históricos
            if chave in ["selic_efet", "ipca", "tjlp", "di", "cds"]:
                hist_serie = hist_macro.get(chave, {})
                proj_serie = proj_macro.get(chave, {})
                fmt = PCT_FMT2
            elif chave == "nim":
                hist_serie = {}
                if "nim" in indicadores_hist.columns:
                    for ano in self.anos_hist:
                        try:
                            hist_serie[ano] = float(indicadores_hist.loc[ano, "nim"])
                        except Exception:
                            pass
                proj_serie = projecoes.get("nim", {})
                fmt = PCT_FMT2
            else:
                hist_serie = {}
                if chave in (indicadores_hist.columns if not indicadores_hist.empty else []):
                    for ano in self.anos_hist:
                        try:
                            hist_serie[ano] = float(indicadores_hist.loc[ano, chave])
                        except Exception:
                            pass
                proj_serie = projecoes.get(chave, {})
                fmt = NUM_FMT

            self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa, fmt)

    def popular_indicadores(self, wb, indicadores: pd.DataFrame):
        """Popula a aba Painel de Índices."""
        ws       = wb["Painel de Índices"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        for label, chave in self.MAPA_INDICADORES.items():
            row = self._match_label(labels, label)
            if not row:
                continue

            hist_serie = {}
            if chave in indicadores.columns:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(indicadores.loc[ano, chave])
                    except Exception:
                        pass

            fmt = PCT_FMT2 if chave in [
                "roe","roa","nim","margem_liquida","spread_global",
                "independencia_financeira","pcld_carteira","part_emprestimos"
            ] else NUM_FMT

            self._preencher_linha(ws, row, hist_serie, {}, col_mapa, fmt)

    # ── Orquestrador principal ────────────────────────────────────────────────

    def escrever(self, dados_completos: dict,
                  nome_empresa: str = "Banco",
                  destino: Path = None) -> Path:
        """
        Escreve todos os dados no template e salva o arquivo.

        Args:
            dados_completos: dicionário consolidado do normalizador
            nome_empresa:    nome legível (ex: "Bradesco")
            destino:         caminho de saída (opcional)

        Returns:
            Caminho do arquivo gerado
        """
        if destino is None:
            destino = (self.template.parent / "outputs" /
                       f"Valuation_{self.ticker}_{nome_empresa}.xlsx")

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"Escrevendo template: {destino.name}")

        wb = self._abrir_template(destino)

        # Atualizar cabeçalhos
        self._atualizar_cabecalho(wb, nome_empresa, self.ticker)

        # Extrair componentes
        dre_hist  = dados_completos.get("dre", pd.DataFrame())
        bp_hist   = dados_completos.get("balanco", pd.DataFrame())
        ind_hist  = dados_completos.get("indicadores", pd.DataFrame())
        macro     = dados_completos.get("macro", {})
        mercado   = dados_completos.get("mercado", {})
        projecoes = dados_completos.get("projecoes", {})
        valuation = dados_completos.get("valuation", {})

        # Popular cada aba
        logger.info("  → Dashboard")
        self.popular_dashboard(wb, {**mercado, **valuation})

        logger.info("  → Ke")
        self.popular_ke(wb, macro)

        logger.info("  → Balanço Patrimonial")
        self.popular_balanco(wb, bp_hist, projecoes)

        logger.info("  → DRE Recorrente")
        self.popular_dre(wb, dre_hist, projecoes)

        logger.info("  → DRE + DCF")
        self.popular_dcf(wb, dre_hist, projecoes, valuation)

        logger.info("  → Projeções NIM")
        self.popular_nim(wb, ind_hist, macro, projecoes)

        logger.info("  → Painel de Índices")
        self.popular_indicadores(wb, ind_hist)

        wb.save(destino)
        logger.info(f"\nArquivo salvo: {destino}")
        return destino
