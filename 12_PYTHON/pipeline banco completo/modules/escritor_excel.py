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
import unicodedata

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter, column_index_from_string
from modules.excel_theme import THEME

logger = logging.getLogger("pipeline.excel")


# ── Constantes de formatação ────────────────────────────────────────────────
C_BLUE   = THEME.HIST
C_GREEN  = "008000"   # links / projeções
C_BLACK  = "000000"   # fórmulas
NUM_FMT  = '#,##0;(#,##0);"-"'
PCT_FMT2 = '0.00%;(0.00%);"-"'
PCT_FMT1 = '0.0%;(0.0%);"-"'
BRL_FMT  = THEME.BRL
NUM_FMT2 = THEME.NUM_2
C_WHITE  = THEME.WHITE
C_HEADER = THEME.HEADER
C_SUBHDR = THEME.SUBHEADER
C_ACCENT = THEME.ACCENT
C_GREEN  = THEME.PROJ
C_BLACK  = THEME.TEXT
NUM_FMT  = THEME.NUM
PCT_FMT2 = THEME.PCT_2
PCT_FMT1 = THEME.PCT_1


def _font(color=C_BLACK, bold=False, size=9):
    return THEME.font(color=color, bold=bold, size=size)


def _header_font(size=10):
    return THEME.header_font(size=size)


def _fill(color):
    return THEME.fill(color)

def _thin_bottom():
    s = Side(style="thin", color="BFBFBF")
    return Border(bottom=s)


def _norm_texto(valor: str) -> str:
    """Normaliza label para matching tolerante entre templates."""
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9%]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


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
        """Abre a base de layout; se for outro arquivo, copia para o destino."""
        destino = Path(destino)
        try:
            mesmo_arquivo = self.template.resolve() == destino.resolve()
        except OSError:
            mesmo_arquivo = False
        if not mesmo_arquivo:
            shutil.copy2(self.template, destino)
        try:
            return load_workbook(destino)
        except PermissionError as exc:
            raise PermissionError(
                f"Arquivo Excel bloqueado: {destino}. "
                "Feche a planilha no Excel/OneDrive e rode novamente."
            ) from exc

    # ── Mapeamento de colunas ─────────────────────────────────────────────────

    @staticmethod
    def _eh_coluna_periodo(valor) -> bool:
        """Identifica cabecalhos anuais ou pontes trimestrais antigas."""
        if valor is None:
            return False
        texto = str(valor).strip().upper()
        if re.fullmatch(r"\d{4}", texto):
            return True
        return bool(re.fullmatch(r"\dT\d{2}|YTD\d{2}|YTG\d{2}|YTD|YTG", texto))

    def _padronizar_colunas_anos(self, ws) -> None:
        """Normaliza a linha 4 para historico anual + projecao anual."""
        row = 4
        colunas_periodo = [
            col for col in range(1, ws.max_column + 1)
            if self._eh_coluna_periodo(ws.cell(row=row, column=col).value)
        ]
        start_col = min(colunas_periodo) if colunas_periodo else 5

        for i, ano in enumerate(self.todos_anos):
            col = start_col + i
            cell = ws.cell(row=row, column=col, value=ano)
            cell.font = _header_font(9)
            cell.fill = _fill(C_SUBHDR)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _thin_bottom()
            ws.column_dimensions[get_column_letter(col)].width = max(
                ws.column_dimensions[get_column_letter(col)].width or 0,
                11,
            )

        end_col = start_col + len(self.todos_anos)
        for col in range(end_col, ws.max_column + 1):
            if self._eh_coluna_periodo(ws.cell(row=row, column=col).value):
                ws.cell(row=row, column=col).value = None

    def _mapear_colunas_anos(self, ws) -> dict[Union[int, str], int]:
        """
        Percorre a linha 4 da aba e retorna {ano_ou_str: col_index}.
        Ex: {2019: 5, 2020: 6, ..., "1T25": 10, 2025: 11, ...}
        """
        self._padronizar_colunas_anos(ws)
        mapa = {}
        for col in range(1, ws.max_column + 1):
            val = ws.cell(row=4, column=col).value
            if val is None:
                continue
            try:
                mapa[int(str(val))] = col
            except (ValueError, TypeError):
                # Strings como "1T25", "YTD25", etc.
                if isinstance(val, str) and re.fullmatch(r'\dT\d{2}|YTD\d{2}|YTG\d{2}', val.strip().upper()):
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
                mapa[_norm_texto(val)] = row
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
        chave_norm = _norm_texto(label_procurado)
        if chave_norm in labels_ws:
            return labels_ws[chave_norm]
        # Partial match (remove espaços duplos, acentos alternativos)
        for k, v in labels_ws.items():
            if isinstance(k, str) and label_procurado.strip().lower() in k.lower():
                return v
            if isinstance(k, str):
                k_norm = _norm_texto(k)
                if chave_norm and (chave_norm in k_norm or k_norm in chave_norm):
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

    def _aba_metodologia(self, wb, nome: str, dados: dict):
        """Cria/atualiza a aba de metodologia para bancos."""
        if "Metodologia" in wb.sheetnames:
            del wb["Metodologia"]
        ws = wb.create_sheet("Metodologia", 1)

        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 42
        ws.column_dimensions["C"].width = 4
        ws.column_dimensions["D"].width = 34
        ws.column_dimensions["E"].width = 22
        ws.column_dimensions["F"].width = 22

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
        title = ws.cell(row=1, column=1, value=f"Metodologia - {nome} ({self.ticker})")
        title.font = _header_font(14)
        title.fill = _fill(C_HEADER)
        title.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 32

        meta = dados.get("metodologia", {}) or {}
        prem = meta.get("premissas", {}) or {}
        valuation = dados.get("valuation", {}) or {}
        proj = dados.get("projecoes", {}) or {}
        macro = dados.get("macro", {}) or {}

        setor = meta.get("setor") or "bancos"
        motor_proj = (meta.get("motor_projecao") or "fcfe").upper()
        motor_val = (meta.get("motor_valuation") or "ke").upper()
        tipo_acao = meta.get("tipo_acao") or "-"

        def header(row: int, title_text: str, start_col: int = 1, end_col: int = 6):
            for col in range(start_col, end_col + 1):
                cell = ws.cell(row=row, column=col)
                cell.fill = _fill(C_HEADER)
                cell.border = THEME.border()
            cell = ws.cell(row=row, column=start_col, value=title_text)
            cell.font = _header_font(10)

        def excel_value(value):
            if isinstance(value, dict):
                if "default" in value:
                    return value["default"]
                if not value:
                    return "-"
                itens = sorted(value.items(), key=lambda kv: str(kv[0]))
                return "; ".join(f"{k}: {v}" for k, v in itens)
            if isinstance(value, (list, tuple, set)):
                return "; ".join(str(v) for v in value)
            return value

        def pair(row: int, label: str, value, fmt: str | None = None, col: int = 1):
            value = excel_value(value)
            label_cell = ws.cell(row=row, column=col, value=label)
            label_cell.font = _font(bold=True)
            label_cell.fill = _fill(C_SUBHDR)
            label_cell.border = THEME.border()

            value_cell = ws.cell(row=row, column=col + 1, value=value)
            value_cell.alignment = Alignment(wrap_text=True, vertical="top")
            value_cell.border = THEME.border()
            if fmt and isinstance(value, (int, float)):
                value_cell.number_format = fmt
            return value_cell

        header(3, "Enquadramento")
        pair(4, "Setor", setor)
        pair(5, "Tipo de Empresa", "bank")
        pair(6, "Motor de Projecao", motor_proj)
        pair(7, "Motor de Valuation", motor_val)
        pair(8, "Tipo de Acao", tipo_acao)
        pair(
            9,
            "Tese metodologica",
            "Banco: valuation por FCFE/Ke, porque depositos, captacoes e "
            "divida financeira fazem parte da operacao bancaria e nao devem "
            "ser tratados como estrutura de capital comum.",
        )
        ws.merge_cells(start_row=9, start_column=2, end_row=9, end_column=6)
        ws.row_dimensions[9].height = 48

        header(11, "Leitura Economica do Banco")
        ws.cell(row=12, column=1, value="Foco Analitico").font = _font(bold=True)
        ws.cell(row=12, column=1).fill = _fill(C_SUBHDR)
        ws.cell(row=12, column=1).border = THEME.border()
        ws.merge_cells(start_row=12, start_column=2, end_row=12, end_column=6)
        foco = ws.cell(
            row=12,
            column=2,
            value=(
                "A analise prioriza NIM/spread, crescimento da carteira, "
                "qualidade de credito, provisoes, eficiencia operacional, "
                "capital regulatorio, payout sustentavel e custo de equity."
            ),
        )
        foco.alignment = Alignment(wrap_text=True, vertical="top")
        foco.border = THEME.border()
        ws.row_dimensions[12].height = 46

        header(15, "Premissas-Chave", 1, 3)
        premissas_chave = [
            ("NIM alvo", prem.get("nim_alvo"), PCT_FMT1),
            ("NIM maximo", prem.get("nim_maximo"), PCT_FMT1),
            ("PCLD / Carteira alvo", prem.get("pcld_pct_alvo"), PCT_FMT1),
            ("Payout projetado", prem.get("payout_projetado") or prem.get("payout"), PCT_FMT1),
            ("g perpetuidade", prem.get("g_perpetuidade"), PCT_FMT1),
            ("Beta utilizado", prem.get("beta_utilizado") or prem.get("beta"), NUM_FMT2),
            ("Crescimento credito", prem.get("crescimento_credito"), PCT_FMT1),
            ("Crescimento servicos", prem.get("crescimento_servicos"), PCT_FMT1),
            ("Relacao PN/ON", prem.get("relacao_pn_on"), NUM_FMT2),
        ]
        row = 16
        for label, value, fmt in premissas_chave:
            if value is None:
                continue
            pair(row, label, value, fmt)
            row += 1

        header(15, "Saidas do Modelo", 4, 6)
        fcfe = proj.get("fcfe") or {}
        fcfe_ultimo = fcfe.get(max(fcfe.keys())) if fcfe else None
        ke_por_ano = valuation.get("ke_por_ano") or macro.get("projecao", {}).get("ke", {})
        ke_ultimo = ke_por_ano.get(max(ke_por_ano.keys())) if ke_por_ano else None
        saidas = [
            ("Valor do Equity (R$ MM)", valuation.get("equity_mm"), NUM_FMT),
            ("Preco Justo ON", valuation.get("preco_justo_on"), BRL_FMT),
            ("Preco Justo PN", valuation.get("preco_justo_pn"), BRL_FMT),
            ("Upside ON", valuation.get("upside_on"), PCT_FMT1),
            ("TIR ON", valuation.get("tir_on"), PCT_FMT1),
            ("VP FCFE", valuation.get("vp_fcfe"), NUM_FMT),
            ("VP Perpetuidade", valuation.get("vp_perpetuidade"), NUM_FMT),
            ("FCFE ultimo ano", fcfe_ultimo, NUM_FMT),
            ("Ke ultimo ano", ke_ultimo, PCT_FMT1),
        ]
        row = 16
        for label, value, fmt in saidas:
            if value is None:
                continue
            pair(row, label, value, fmt, col=4)
            row += 1

        header(27, "Governanca do Modelo")
        notas = [
            "Layout visual padronizado pelo tema interno do pipeline.",
            "Metodologia definida por tipo de empresa, setor e premissas do empresas.yaml.",
            "Demonstrativos vem da CVM; mercado, preco, volume e liquidez vem de B3/yfinance/cache.",
            "Para bancos, o FCFE representa distribuicao economica ao acionista apos crescimento, risco de credito e capital.",
        ]
        for i, nota in enumerate(notas, start=28):
            ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
            cell = ws.cell(row=i, column=1, value=nota)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = THEME.border()
            ws.row_dimensions[i].height = 30

        ws.freeze_panes = "A3"

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
        """Popula a aba Ke com taxas históricas e projetadas, incluindo o Ke por ano."""
        ws       = wb["Ke"]
        hist     = macro.get("historico", {})
        proj     = macro.get("projecao", {})

        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        def linha(label, chave_hist, chave_proj, fmt=PCT_FMT2):
            row = self._match_label(labels, label)
            if not row:
                logger.debug(f"  Label Ke não encontrado: {label}")
                return
            h = hist.get(chave_hist, {})
            p = proj.get(chave_proj, {})
            self._preencher_linha(ws, row, h, p, col_mapa, fmt)

        linha("DI (% a.a.)",                "selic_efet",    "di")
        linha("CDS Brasil (% a.a.)",         "cds",           "cds")
        linha("Inflação Implícita (% a.a.)", "inflacao_impl", "inflacao_impl")
        linha("TJLP (% a.a.)",               "tjlp",          "tjlp")

        # Ke calculado por ano (projeção) — escrito apenas nas colunas de projeção
        ke_proj = proj.get("ke", {})
        if ke_proj:
            candidatos_ke = ["Ke (Custo do Capital Próprio)", "Custo do Capital (Ke)",
                             "Ke", "Ke (%)", "Ke (% a.a.)"]
            row_ke = None
            for lbl in candidatos_ke:
                row_ke = self._match_label(labels, lbl)
                if row_ke:
                    break
            if row_ke:
                self._preencher_linha(ws, row_ke, {}, ke_proj, col_mapa, PCT_FMT2)

        # Beta — série diária histórica
        beta_data = macro.get("beta", {})
        if beta_data.get("serie_diaria") is not None:
            serie = beta_data["serie_diaria"]
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

                row_pct = row + 1
                label_pct = ws.cell(row=row_pct, column=4).value
                if (
                    isinstance(label_pct, str)
                    and "% dos ativos remuneraveis" in _norm_texto(label_pct)
                    and "ativos_remuneraveis" in bp_hist.index
                ):
                    base_hist = bp_hist.loc["ativos_remuneraveis"]
                    pct_hist = {}
                    for ano, valor in hist_serie.items():
                        base = float(base_hist.get(ano, 0) or 0)
                        pct_hist[ano] = (valor / base) if base else 0
                    base_proj = projecoes_bp.get("ativos_remuneraveis", {})
                    pct_proj = {}
                    for ano, valor in proj_serie.items():
                        base = float(base_proj.get(ano, 0) or 0)
                        pct_proj[ano] = (valor / base) if base else 0
                    self._preencher_linha(
                        ws, row_pct, pct_hist, pct_proj, col_mapa, PCT_FMT1
                    )

    def popular_dcf(self, wb, dre_hist: pd.DataFrame,
                     projecoes: dict, valuation: dict,
                     bp_hist: pd.DataFrame = None,
                     metodologia: dict = None,
                     mercado: dict = None):
        """Popula a aba DRE + DCF incluindo o bloco de valuation."""
        ws       = wb["DRE + DCF"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)

        for label, chave in self.MAPA_LINHAS_DCF.items():
            row = self._match_label(labels, label)
            if not row:
                continue

            hist_serie = {}
            if chave == "da" and "da" not in dre_hist.index and "depreciacao_amortizacao" in dre_hist.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = abs(float(dre_hist.loc["depreciacao_amortizacao", ano]))
                    except Exception:
                        pass
            elif chave == "capex" and "capex" not in dre_hist.index and "depreciacao_amortizacao" in dre_hist.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = -abs(float(dre_hist.loc["depreciacao_amortizacao", ano]))
                    except Exception:
                        pass
            elif chave == "capital_regulatorio" and bp_hist is not None and not bp_hist.empty and "carteira_credito_bruta" in bp_hist.index:
                basileia = 0.135
                ponderacao_rwa = 0.60
                for i, ano in enumerate(self.anos_hist):
                    try:
                        atual = float(bp_hist.loc["carteira_credito_bruta", ano])
                        ant = float(bp_hist.loc["carteira_credito_bruta", self.anos_hist[i - 1]]) if i > 0 else atual
                        hist_serie[ano] = -((atual - ant) / ponderacao_rwa) * basileia
                    except Exception:
                        pass
            elif chave == "fcfe" and "fcfe" not in dre_hist.index and "lucro_liquido" in dre_hist.index:
                prem = (metodologia or {}).get("premissas", {}) or {}
                payout = prem.get("payout_projetado") or prem.get("payout") or 0.45
                if isinstance(payout, dict):
                    payout = payout.get("default", 0.45)
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(dre_hist.loc["lucro_liquido", ano]) * float(payout)
                    except Exception:
                        pass
            elif chave in dre_hist.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(dre_hist.loc[chave, ano])
                    except Exception:
                        pass

            proj_serie = projecoes.get(chave, {})
            self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa)

        # Valuation — resultados pontuais (não séries temporais)
        # A coluna de resultado é: "Perpetuidade" no col_mapa, ou penúltima coluna de dados,
        # ou coluna 5 como último recurso.
        row_yoy = self._match_label(labels, "Crescimento YoY (%)")
        if row_yoy and "lucro_liquido" in dre_hist.index:
            serie_ll = {}
            for ano in self.anos_hist:
                try:
                    serie_ll[ano] = float(dre_hist.loc["lucro_liquido", ano])
                except Exception:
                    pass
            serie_ll.update(projecoes.get("lucro_liquido", {}))
            anos = sorted(serie_ll.keys())
            for i, ano in enumerate(anos[1:], 1):
                ant = anos[i - 1]
                base = serie_ll.get(ant, 0)
                valor = serie_ll.get(ano, 0)
                col = col_mapa.get(ano)
                if col:
                    yoy = (valor / abs(base) - 1) if base else 0
                    self._escrever_valor(
                        ws, row_yoy, col, yoy,
                        eh_historico=(ano in self.anos_hist),
                        num_fmt=PCT_FMT1,
                    )

        linhas_series = {
            "Fator de Desconto (Ke acum.)": (valuation.get("fatores_desconto", {}), PCT_FMT2),
            "FCFE Descontado": (valuation.get("fcfe_descontado", {}), NUM_FMT),
        }
        for label, (serie, fmt) in linhas_series.items():
            row = self._match_label(labels, label)
            if not row:
                continue
            for ano, valor in (serie or {}).items():
                col = col_mapa.get(ano)
                if col:
                    self._escrever_valor(ws, row, col, valor, eh_historico=False, num_fmt=fmt)

        col_val = (col_mapa.get("Perpetuidade")
                   or col_mapa.get("perp")
                   or (max(col_mapa.values()) - 1 if col_mapa else 5))

        campos_val = {
            "VALOR DO EQUITY (R$ MM)":     (valuation.get("equity_mm", 0),   NUM_FMT),
            "Preço Justo ON (R$)":         (valuation.get("preco_justo_on", 0), NUM_FMT),
            "Preço Justo PN (R$)":         (valuation.get("preco_justo_pn", 0), NUM_FMT),
            "UPSIDE ON (%)":               (valuation.get("upside_on", 0),   PCT_FMT1),
            "UPSIDE PN (%)":               (valuation.get("upside_pn", 0),   PCT_FMT1),
            "TIR (ON) — função XIRR":      (valuation.get("tir_on", 0),      PCT_FMT1),
            "TIR (PN) — função XIRR":      (valuation.get("tir_pn", 0),      PCT_FMT1),
            "PREÇO TETO ON":               (valuation.get("preco_teto_on", 0), NUM_FMT),
            "PREÇO TETO PN":               (valuation.get("preco_teto_pn", 0), NUM_FMT),
            "VP FCFE (fase explícita)":    (valuation.get("vp_fcfe", 0),     NUM_FMT),
            "VP Perpetuidade":             (valuation.get("vp_perpetuidade", 0), NUM_FMT),
        }

        for label, (valor, fmt) in campos_val.items():
            row = self._match_label(labels, label)
            if row:
                self._escrever_valor(ws, row, col_val, valor,
                                     eh_historico=False, num_fmt=fmt)

        # Bloco de resultado do valuation no template vivo. Estes valores nao
        # pertencem a uma serie anual; escrever em 2026 deixa o resultado visivel
        # sem empurrar a leitura para o fim da planilha.
        col_resumo = (
            col_mapa.get(self.anos_proj[0]) if self.anos_proj else None
        ) or (col_mapa.get(max(self.anos_hist)) if self.anos_hist else None) or 5

        mercado = mercado or {}
        cotacao_on = mercado.get("preco") or mercado.get("cotacao_on") or 0
        cotacao_pn = mercado.get("preco_pn") or mercado.get("cotacao_pn") or 0

        campos_resumo = [
            (["Valor Presente do FCFE (10 anos)", "VP FCFE (fase explicita)", "VP FCFE"], valuation.get("vp_fcfe", 0), NUM_FMT),
            (["Valor da Perpetuidade (Gordon)", "Valor Perpetuidade", "Perpetuidade"], valuation.get("perpetuidade", 0), NUM_FMT),
            (["Valor da Perpetuidade Descontado", "VP Perpetuidade"], valuation.get("vp_perpetuidade", 0), NUM_FMT),
            (["VALOR DO EQUITY (R$ MM)", "Valor do Equity (R$ MM)"], valuation.get("equity_mm", 0), NUM_FMT),
            (["Preco Justo ON (R$)", "Preço Justo ON (R$)"], valuation.get("preco_justo_on", 0), NUM_FMT),
            (["Preco Justo PN (R$)", "Preço Justo PN (R$)"], valuation.get("preco_justo_pn", 0), NUM_FMT),
            (["Cotacao Atual ON (R$)", "Cotação Atual ON (R$)"], cotacao_on, NUM_FMT),
            (["Cotacao Atual PN (R$)", "Cotação Atual PN (R$)"], cotacao_pn, NUM_FMT),
            (["UPSIDE ON (%)"], valuation.get("upside_on", 0), PCT_FMT1),
            (["UPSIDE PN (%)"], valuation.get("upside_pn", 0), PCT_FMT1),
            (["TIR (ON) - funcao XIRR", "TIR (ON) — função XIRR"], valuation.get("tir_on", 0), PCT_FMT1),
            (["TIR (PN) - funcao XIRR", "TIR (PN) — função XIRR"], valuation.get("tir_pn", 0), PCT_FMT1),
            (["PRECO TETO ON (Ke = Preco-base)", "PREÇO TETO ON (Ke = Preço-base)", "PRECO TETO ON", "PREÇO TETO ON"], valuation.get("preco_teto_on", 0), NUM_FMT),
            (["PRECO TETO PN", "PREÇO TETO PN"], valuation.get("preco_teto_pn", 0), NUM_FMT),
        ]

        for candidatos, valor, fmt in campos_resumo:
            row = None
            for label in candidatos:
                row = self._match_label(labels, label)
                if row:
                    break
            if row:
                for col in col_mapa.values():
                    ws.cell(row=row, column=col).value = None
                self._escrever_valor(ws, row, col_resumo, valor, eh_historico=False, num_fmt=fmt)

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
                if "nim" in indicadores_hist.index:
                    for ano in self.anos_hist:
                        try:
                            hist_serie[ano] = float(indicadores_hist.loc["nim", ano])
                        except Exception:
                            pass
                proj_serie = projecoes.get("nim", {})
                fmt = PCT_FMT2
            else:
                hist_serie = {}
                if chave in (indicadores_hist.index if not indicadores_hist.empty else []):
                    for ano in self.anos_hist:
                        try:
                            hist_serie[ano] = float(indicadores_hist.loc[chave, ano])
                        except Exception:
                            pass
                proj_serie = projecoes.get(chave, {})
                fmt = NUM_FMT

            self._preencher_linha(ws, row, hist_serie, proj_serie, col_mapa, fmt)

    def popular_indicadores(self, wb, indicadores: pd.DataFrame,
                            projecoes: dict = None,
                            bp_hist: pd.DataFrame = None):
        """Popula a aba Painel de Índices."""
        ws       = wb["Painel de Índices"]
        col_mapa = self._mapear_colunas_anos(ws)
        labels   = self._mapear_linhas_por_label(ws, col_label=4)
        projecoes = projecoes or {}
        bp_hist = bp_hist if bp_hist is not None else pd.DataFrame()

        def ultimo(df: pd.DataFrame, chave: str) -> float:
            if df.empty or chave not in df.index:
                return 0.0
            vals = []
            for ano in self.anos_hist:
                try:
                    vals.append(float(df.loc[chave, ano]))
                except Exception:
                    pass
            vals = [v for v in vals if v not in (None, 0)]
            return vals[-1] if vals else 0.0

        def projetar_por_crescimento(valor_base: float, serie_base: dict) -> dict:
            anos = sorted((serie_base or {}).keys())
            if not anos or not valor_base:
                return {}
            ref = serie_base.get(anos[0]) or 0
            return {
                ano: round(valor_base * ((serie_base.get(ano, 0) or 0) / ref), 6)
                for ano in anos
                if ref
            }

        def div(num: dict, den: dict) -> dict:
            return {
                ano: (num.get(ano, 0) / den.get(ano, 0))
                for ano in set(num or {}) | set(den or {})
                if den.get(ano)
            }

        lucro = projecoes.get("lucro_liquido", {})
        mfb = projecoes.get("margem_financeira_bruta", {})
        carteira = projecoes.get("carteira_credito_bruta", {})
        ativos_rem = projecoes.get("ativos_remuneraveis", {})
        provisao = {a: abs(v) for a, v in projecoes.get("provisao_credito", {}).items()}
        ativo_total = projecoes.get("ativo_total") or projetar_por_crescimento(
            ultimo(bp_hist, "ativo_total"), ativos_rem or carteira
        )
        depositos = projecoes.get("depositos_total") or projetar_por_crescimento(
            ultimo(bp_hist, "depositos_total"), carteira
        )
        pl_base = ultimo(bp_hist, "patrimonio_liquido") or ultimo(bp_hist, "pl_controladores")
        pl_proj = {}
        pl = pl_base
        for ano in sorted(lucro.keys()):
            pl += lucro.get(ano, 0) * 0.55
            pl_proj[ano] = round(pl, 6)

        indicador_proj = {
            "nim": projecoes.get("nim", {}),
            "margem_liquida": div(lucro, mfb),
            "pcld_carteira": div(provisao, carteira),
            "emp_depositos": div(carteira, depositos),
            "part_emprestimos": div(carteira, ativo_total),
            "independencia_financeira": div(pl_proj, ativo_total),
            "alavancagem": div(ativo_total, pl_proj),
            "roe": div(lucro, pl_proj),
            "roa": div(lucro, ativo_total),
        }

        for label, chave in self.MAPA_INDICADORES.items():
            row = self._match_label(labels, label)
            if not row:
                continue

            hist_serie = {}
            if chave in indicadores.index:
                for ano in self.anos_hist:
                    try:
                        hist_serie[ano] = float(indicadores.loc[chave, ano])
                    except Exception:
                        pass

            fmt = PCT_FMT2 if chave in [
                "roe","roa","nim","margem_liquida","spread_global",
                "independencia_financeira","pcld_carteira","part_emprestimos"
            ] else NUM_FMT

            self._preencher_linha(
                ws, row, hist_serie, indicador_proj.get(chave, {}), col_mapa, fmt
            )

    # ── Orquestrador principal ────────────────────────────────────────────────

    def popular_trimestrais(self, wb, dre_hist: pd.DataFrame,
                             bp_hist: pd.DataFrame, projecoes: dict):
        """Reconstrói a aba trimestral para evitar zeros herdados do template."""
        if "Projeções Trimestrais" not in wb.sheetnames:
            return
        ws = wb["Projeções Trimestrais"]
        projecoes = projecoes or {}

        for row in range(1, max(ws.max_row, 60) + 1):
            for col in range(4, 11):
                ws.cell(row=row, column=col).value = None

        ws.cell(row=1, column=4, value=f"{self.ticker} - Projeções Trimestrais")
        ws.cell(row=1, column=4).font = _header_font(13)
        ws.cell(row=1, column=4).fill = _fill(C_HEADER)
        ws.cell(row=1, column=4).alignment = Alignment(horizontal="center")
        ws.merge_cells(start_row=1, start_column=4, end_row=1, end_column=10)

        headers = ["Indicador", "Ano", "1T", "2T", "3T", "4T", "Total/Media"]
        for i, header in enumerate(headers, start=4):
            cell = ws.cell(row=3, column=i, value=header)
            cell.font = _header_font(9)
            cell.fill = _fill(C_SUBHDR)
            cell.alignment = Alignment(horizontal="center")
            cell.border = _thin_bottom()

        def hist(df: pd.DataFrame, chave: str) -> dict:
            if df.empty or chave not in df.index:
                return {}
            out = {}
            for ano in self.anos_hist:
                try:
                    out[ano] = float(df.loc[chave, ano])
                except Exception:
                    pass
            return out

        def serie(chave: str, df: pd.DataFrame) -> dict:
            out = hist(df, chave)
            out.update(projecoes.get(chave, {}))
            return out

        blocos = [
            ("Lucro Líquido (R$ MM)", "lucro_liquido", dre_hist, "fluxo"),
            ("Margem Financeira Bruta (R$ MM)", "margem_financeira_bruta", dre_hist, "fluxo"),
            ("Despesa de Provisão (R$ MM)", "provisao_credito", dre_hist, "fluxo"),
            ("Margem Financeira Líquida (R$ MM)", "margem_financeira_liquida", dre_hist, "fluxo"),
            ("Receita de Serviços (R$ MM)", "receita_servicos", dre_hist, "fluxo"),
            ("Ativos Remuneráveis (R$ MM)", "ativos_remuneraveis", bp_hist, "saldo"),
            ("Carteira de Crédito (R$ MM)", "carteira_credito_bruta", bp_hist, "saldo"),
        ]
        anos = self.anos_hist[-4:] + self.anos_proj[:4]
        row = 4
        for titulo, chave, df, tipo in blocos:
            cell = ws.cell(row=row, column=4, value=titulo)
            cell.font = _font(bold=True)
            cell.fill = _fill(C_ACCENT)
            row += 1
            valores = serie(chave, df)
            for ano in anos:
                if ano not in valores:
                    continue
                valor = float(valores.get(ano, 0) or 0)
                ws.cell(row=row, column=4, value=ano)
                ws.cell(row=row, column=5, value=ano)
                partes = [valor / 4] * 4 if tipo == "fluxo" else [valor] * 4
                for i, parte in enumerate(partes, start=6):
                    self._escrever_valor(ws, row, i, parte, eh_historico=(ano in self.anos_hist))
                total = sum(partes) if tipo == "fluxo" else (sum(partes) / 4)
                self._escrever_valor(ws, row, 10, total, eh_historico=(ano in self.anos_hist))
                row += 1
            row += 1

        for col in range(4, 11):
            ws.column_dimensions[get_column_letter(col)].width = 16

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
        logger.info("  -> Metodologia")
        self._aba_metodologia(wb, nome_empresa, dados_completos)

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
        self.popular_dcf(
            wb,
            dre_hist,
            projecoes,
            valuation,
            bp_hist=bp_hist,
            metodologia=dados_completos.get("metodologia", {}),
            mercado=mercado,
        )

        logger.info("  → Projeções NIM")
        self.popular_nim(wb, ind_hist, macro, projecoes)

        logger.info("  → Painel de Índices")
        self.popular_indicadores(wb, ind_hist, projecoes=projecoes, bp_hist=bp_hist)

        logger.info("  -> Projecoes Trimestrais")
        self.popular_trimestrais(wb, dre_hist, bp_hist, projecoes)

        wb.save(destino)
        logger.info(f"\nArquivo salvo: {destino}")
        return destino


EscritorExcel.MAPA_LINHAS_BP_ATIVO.update({
    "  Relações Interfinanceiras": "compulsorios_bacen",
    "  Operações de Arrendamento Mercantil": "arrendamento_mercantil",
    "Disponibilidades e Outros": "disponibilidades",
    "Permanente": "permanente",
})

EscritorExcel.MAPA_LINHAS_BP_PASSIVO.update({
    "PASSIVO TOTAL": "passivo_total",
    "Outras Obrigações": "outras_obrigacoes",
    "  Capital Social + Reservas": "pl_controladores",
    "  Participações Não Controladoras": "participacoes_nao_controladoras_pl",
})
