"""
Módulo 07b — Escritor Excel (empresas não-financeiras)
Cria planilha de valuation completa com layout interno, dados coletados,
normalizados e projetados. Arquivos externos podem servir como referencia
visual, mas nao sao usados como padrao operacional.

Abas geradas (13 abas):
  1.  Dashboard          → resumo executivo com navegação e equity bridge
  2.  Metodologia        → motor usado, leitura setorial e premissas-chave
  3.  WACC               → CAPM + custo dívida + WACC por ano
  4.  TIR ON             → fluxo de dividendos ON + TIR
  5.  TIR PN             → fluxo de dividendos PN + TIR
  6.  Valor do Equity    → EV → Equity bridge detalhado, preço justo
  7.  Preço Teto         → margem de segurança (10%, 15%, 20%, 25%)
  8.  DRE + DCF          → DRE IFRS completa + FCFF descontado
  9.  DRE Contas Abertas → abertura detalhada das contas DRE
  10. Balanço Patrimonial→ ativo, passivo, PL, NCG, dívida
  11. Painel de Índices  → ROIC, margens, alavancagem, múltiplos
  12. Projeções Premissas→ premissas usadas (crescimento, margens, CAPEX)
  13. Projeções Capex/CG → CAPEX e capital de giro detalhados
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from modules.excel_theme import THEME
from modules.excel_audit_sheet import adicionar_aba_auditoria
from modules.sector_operational_drivers import adicionar_aba_drivers_setoriais

try:
    from openpyxl.drawing.image import Image as XLImage
except Exception:  # Pillow pode nao estar disponivel no ambiente do usuario.
    XLImage = None

logger = logging.getLogger("pipeline.excel_geral")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE ESTILO (layout interno)
# ═══════════════════════════════════════════════════════════════════════════════

# Cores principais
C_BLUE    = THEME.HIST
C_GREEN   = THEME.PROJ
C_BLACK   = THEME.TEXT
C_WHITE   = THEME.WHITE
C_HEADER  = THEME.HEADER
C_SUBHDR  = THEME.SUBHEADER
C_ACCENT  = THEME.ACCENT
C_PROJ_BG = THEME.PROJECTION_BG
C_NAV_BG  = THEME.NAV_BG
C_RED     = THEME.NEGATIVE
C_ORANGE  = THEME.WARNING
C_GOLD    = THEME.GOLD
C_DKGREEN = THEME.DARK_GREEN

# Formatos numéricos
NUM_FMT    = THEME.NUM
NUM_FMT1   = THEME.NUM_1
NUM_FMT2   = THEME.NUM_2
PCT_FMT2   = THEME.PCT_2
PCT_FMT1   = THEME.PCT_1
BRL_FMT    = THEME.BRL
MULT_FMT   = THEME.MULT


def _f(color=C_BLACK, bold=False, size=9):
    """Font factory."""
    return THEME.font(color=color, bold=bold, size=size)

def _hf(size=10):
    """Header font (branco, bold)."""
    return THEME.header_font(size=size)

def _border():
    return THEME.border()

def _fill(color):
    return THEME.fill(color)

# Fills reutilizáveis
FILL_HDR    = _fill(C_HEADER)
FILL_SUBHDR = _fill(C_SUBHDR)
FILL_ACCENT = _fill(C_ACCENT)
FILL_PROJ   = _fill(C_PROJ_BG)
FILL_NAV    = _fill(C_NAV_BG)


def _safe_label(label: str) -> str:
    """Remove '=' do início para openpyxl não interpretar como fórmula."""
    if label.startswith("="):
        return label.lstrip("= ")
    return label


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class EscritorExcelGeral:
    """Gera planilha de valuation completa para empresas não-financeiras."""

    def __init__(self, caminho_template: Optional[Path], ticker: str,
                 anos_historicos: list[int], anos_projecao: list[int]):
        self.template   = Path(caminho_template) if caminho_template else None
        self.ticker     = ticker
        self.anos_hist  = sorted(anos_historicos)
        self.anos_proj  = sorted(anos_projecao)
        self.todos_anos = self.anos_hist + self.anos_proj
        self._col_start = 2  # coluna B = primeiro ano

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS DE ESCRITA
    # ═══════════════════════════════════════════════════════════════════════

    def _write_title(self, ws, text: str, row: int = 1, max_col: int = 6):
        """Escreve título mesclado com formatação do layout interno."""
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=max_col)
        cell = ws.cell(row=row, column=1, value=text)
        cell.font      = Font(color=C_WHITE, bold=True, size=14, name="Calibri")
        cell.fill       = FILL_HDR
        cell.alignment  = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 32

    def _localizar_logo(self) -> Optional[Path]:
        """Localiza logo corporativa opcional para aplicar no Dashboard."""
        root = Path(__file__).resolve().parents[1]
        candidatos = [
            root / "assets" / "logo_empresa.png",
            root / "assets" / "logo.png",
            root / "branding" / "logo_empresa.png",
            root / "branding" / "logo.png",
            root / "config" / "logo_empresa.png",
            root / "config" / "logo.png",
        ]
        return next((p for p in candidatos if p.exists()), None)

    def _aplicar_logo_dashboard(self, ws):
        """Insere logo opcional sem exigir edicao manual do arquivo gerado."""
        if XLImage is None:
            return
        logo = self._localizar_logo()
        if not logo:
            return
        try:
            img = XLImage(str(logo))
            img.height = min(img.height, 30)
            if img.width > 120:
                ratio = 120 / img.width
                img.width = 120
                img.height = int(img.height * ratio)
            ws.add_image(img, "H1")
        except Exception as exc:
            logger.warning(f"  Logo nao aplicado ({logo.name}): {exc}")

    def _write_section_header(self, ws, row: int, text: str, col_mapa: dict):
        """Escreve cabeçalho de seção (faixa azul escuro)."""
        cell = ws.cell(row=row, column=1, value=text)
        cell.font  = _hf(10)
        cell.fill  = FILL_HDR
        cell.border = _border()
        for col in col_mapa.values():
            c = ws.cell(row=row, column=col)
            c.fill   = FILL_HDR
            c.border = _border()

    def _write_header_anos(self, ws, row: int = 3) -> dict:
        """Escreve cabeçalho com anos. Retorna {ano: col}."""
        mapa = {}
        cell_label = ws.cell(row=row, column=1, value="(R$ MM)")
        cell_label.font = _f(bold=True)
        cell_label.fill = FILL_SUBHDR
        cell_label.border = _border()
        cell_label.alignment = Alignment(horizontal="left")

        for i, ano in enumerate(self.todos_anos):
            col = self._col_start + i
            cell = ws.cell(row=row, column=col, value=ano)
            cell.font      = _hf(9)
            cell.fill       = FILL_HDR
            cell.alignment  = Alignment(horizontal="center")
            cell.border     = _border()
            mapa[ano] = col
            ws.column_dimensions[get_column_letter(col)].width = 14.5
        ws.column_dimensions["A"].width = 44
        return mapa

    @staticmethod
    def _eh_coluna_periodo_template(valor) -> bool:
        """Identifica anos e pontes trimestrais herdadas em templates externos."""
        if valor is None:
            return False
        texto = str(valor).strip().upper()
        if re.fullmatch(r"\d{4}", texto):
            return True
        return bool(re.fullmatch(r"\dT\d{2}|YTD\d{2}|YTG\d{2}|YTD|YTG", texto))

    def _padronizar_colunas_template(self, ws) -> int:
        """Normaliza template externo para historico anual + projecao anual."""
        melhor_row = 4
        melhor_cols = []
        for row in [4, 3, 5]:
            cols = [
                col for col in range(1, ws.max_column + 1)
                if self._eh_coluna_periodo_template(ws.cell(row=row, column=col).value)
            ]
            if len(cols) > len(melhor_cols):
                melhor_row = row
                melhor_cols = cols

        start_col = min(melhor_cols) if melhor_cols else self._col_start
        for i, ano in enumerate(self.todos_anos):
            col = start_col + i
            cell = ws.cell(row=melhor_row, column=col, value=ano)
            cell.font = _hf(9)
            cell.fill = FILL_HDR
            cell.alignment = Alignment(horizontal="center")
            cell.border = _border()

        end_col = start_col + len(self.todos_anos)
        for col in range(end_col, ws.max_column + 1):
            if self._eh_coluna_periodo_template(ws.cell(row=melhor_row, column=col).value):
                ws.cell(row=melhor_row, column=col).value = None
        return melhor_row

    def _write_row(self, ws, row: int, label: str, col_mapa: dict,
                    hist_data: dict, proj_data: dict,
                    fmt: str = NUM_FMT, accent: bool = False,
                    indent: int = 0):
        """Escreve uma linha de dados (label + histórico + projeção)."""
        prefix = "  " * indent
        cell_l = ws.cell(row=row, column=1, value=prefix + _safe_label(label))
        cell_l.font  = _f(bold=accent)
        cell_l.fill  = FILL_ACCENT if accent else PatternFill()
        cell_l.border = _border()
        cell_l.alignment = Alignment(horizontal="left", vertical="center")

        for ano in self.todos_anos:
            col = col_mapa.get(ano)
            if not col:
                continue
            eh_hist = ano in self.anos_hist
            valor = hist_data.get(ano) if eh_hist else proj_data.get(ano)
            if valor is None:
                continue
            cell = ws.cell(row=row, column=col)
            cell.value = round(valor, 4) if isinstance(valor, float) else valor
            cell.font  = _f(C_BLUE if eh_hist else C_GREEN, bold=accent)
            cell.number_format = fmt
            cell.alignment = Alignment(horizontal="right")
            cell.border = _border()
            if accent:
                cell.fill = FILL_ACCENT
            elif not eh_hist:
                cell.fill = FILL_PROJ

    def _get_hist(self, df: pd.DataFrame, chave: str) -> dict:
        """Extrai série histórica de um DataFrame (index=conta, cols=anos)."""
        if df is None or df.empty or chave not in df.index:
            return {}
        result = {}
        for ano in self.anos_hist:
            if ano in df.columns:
                try:
                    v = float(df.loc[chave, ano])
                    if not pd.isna(v):
                        result[ano] = v
                except Exception:
                    pass
        return result

    def _get_ind(self, ind: pd.DataFrame, chave: str) -> dict:
        """Extrai série de indicadores (index=indicador, cols=anos)."""
        if ind is None or ind.empty or chave not in ind.index:
            return {}
        result = {}
        for ano in self.anos_hist:
            if ano in ind.columns:
                try:
                    v = float(ind.loc[chave, ano])
                    if not pd.isna(v):
                        result[ano] = v
                except Exception:
                    pass
        return result

    def _sum_hist(self, df: pd.DataFrame, chaves: list[str]) -> dict:
        """Soma linhas historicas existentes de um dataframe."""
        resultado = {}
        for chave in chaves:
            serie = self._get_hist(df, chave)
            for ano, valor in serie.items():
                resultado[ano] = resultado.get(ano, 0) + valor
        return resultado

    def _hist_modelo(self, dados: dict, chave: str) -> dict:
        """Resolve historico direto ou calculado para qualquer aba do valuation."""
        dre = dados.get("dre", pd.DataFrame())
        bp = dados.get("balanco", pd.DataFrame())
        dfc = dados.get("dfc", pd.DataFrame())
        ind = dados.get("indicadores", pd.DataFrame())

        aliases = {
            "realizavel_lp": "realizavel_longo_prazo",
            "outros_passivos_circulantes": "outras_obrigacoes_cp",
            "outros_passivos_nao_circ": "outras_obrigacoes_lp",
        }
        chave_real = aliases.get(chave, chave)

        direto = (
            self._get_hist(dre, chave_real)
            or self._get_hist(bp, chave_real)
            or self._get_hist(dfc, chave_real)
            or self._get_ind(ind, chave_real)
        )
        if direto:
            return direto

        if chave == "outros_passivos_circulantes":
            return self._sum_hist(
                bp,
                ["obrigacoes_sociais", "obrigacoes_fiscais_cp", "outras_obrigacoes_cp", "provisoes_cp"],
            )
        if chave == "outros_passivos_nao_circ":
            return self._sum_hist(bp, ["outras_obrigacoes_lp", "tributos_diferidos", "provisoes_lp"])

        if chave == "capex":
            capex = self._get_hist(dfc, "capex_total") or self._get_ind(ind, "capex_mm")
            return {ano: -abs(valor) for ano, valor in capex.items()}

        if chave == "delta_ncg":
            ncg = self._get_hist(bp, "capital_de_giro")
            resultado = {}
            for i, ano in enumerate(self.anos_hist):
                atual = ncg.get(ano)
                if atual is None:
                    continue
                if i == 0:
                    resultado[ano] = 0
                    continue
                anterior = ncg.get(self.anos_hist[i - 1])
                resultado[ano] = -(atual - anterior) if anterior is not None else 0
            return resultado

        if chave == "nopat":
            ebit = self._hist_modelo(dados, "ebit")
            ir = self._hist_modelo(dados, "ir_csll")
            ebt = self._hist_modelo(dados, "resultado_antes_ir")
            resultado = {}
            for ano, valor in ebit.items():
                aliq = abs(ir.get(ano, 0) / ebt.get(ano, 0)) if ebt.get(ano) else 0.34
                if aliq < 0.05 or aliq > 0.50:
                    aliq = 0.34
                resultado[ano] = valor * (1 - aliq)
            return resultado

        if chave == "fcff":
            nopat = self._hist_modelo(dados, "nopat")
            da = self._hist_modelo(dados, "depreciacao_amortizacao")
            capex = self._hist_modelo(dados, "capex")
            delta_ncg = self._hist_modelo(dados, "delta_ncg")
            resultado = {}
            for ano in self.anos_hist:
                if ano in nopat:
                    resultado[ano] = (
                        nopat.get(ano, 0)
                        + da.get(ano, 0)
                        + capex.get(ano, 0)
                        + delta_ncg.get(ano, 0)
                    )
            return resultado

        if chave == "capex_pct_receita":
            capex = self._hist_modelo(dados, "capex")
            receita = self._hist_modelo(dados, "receita_liquida")
            return {ano: abs(v) / receita[ano] for ano, v in capex.items() if receita.get(ano)}

        if chave == "da_pct_receita":
            da = self._hist_modelo(dados, "depreciacao_amortizacao")
            receita = self._hist_modelo(dados, "receita_liquida")
            return {ano: v / receita[ano] for ano, v in da.items() if receita.get(ano)}

        if chave == "capex_liquido":
            capex = self._hist_modelo(dados, "capex")
            da = self._hist_modelo(dados, "depreciacao_amortizacao")
            return {ano: capex.get(ano, 0) + da.get(ano, 0) for ano in self.anos_hist if ano in capex}

        if chave == "ncg_pct_receita":
            ncg = self._hist_modelo(dados, "capital_de_giro")
            receita = self._hist_modelo(dados, "receita_liquida")
            return {ano: v / receita[ano] for ano, v in ncg.items() if receita.get(ano)}

        return {}

    def _ultimo_hist(self, dados: dict, chave: str, default: float = 0.0) -> float:
        """Ultimo valor historico util de uma linha do modelo."""
        serie = self._hist_modelo(dados, chave)
        for ano in sorted(serie.keys(), reverse=True):
            valor = serie.get(ano)
            if valor is not None:
                try:
                    if not pd.isna(valor):
                        return float(valor)
                except Exception:
                    return float(valor)
        return default

    def _proj_por_receita(self, dados: dict, chave: str) -> dict:
        """Projeta uma linha mantendo a ultima proporcao sobre receita."""
        receita_proj = dados.get("projecoes", {}).get("receita_liquida", {})
        if not receita_proj:
            return {}

        hist_linha = self._hist_modelo(dados, chave)
        hist_receita = self._hist_modelo(dados, "receita_liquida")
        ano_ref = None
        for ano in sorted(self.anos_hist, reverse=True):
            if hist_linha.get(ano) is not None and hist_receita.get(ano):
                ano_ref = ano
                break
        if ano_ref is None:
            return {}

        ratio = float(hist_linha.get(ano_ref, 0)) / float(hist_receita.get(ano_ref, 1))
        return {
            ano: round(float(receita_proj.get(ano, 0)) * ratio, 3)
            for ano in self.anos_proj
            if ano in receita_proj
        }

    @staticmethod
    def _div_series(num: dict, den: dict) -> dict:
        return {
            ano: (num.get(ano, 0) / den.get(ano, 0))
            for ano in set(num or {}) | set(den or {})
            if den.get(ano)
        }

    def _proj_modelo(self, dados: dict, chave: str) -> dict:
        """Resolve serie projetada direta ou derivada para evitar abas vazias."""
        proj = dados.get("projecoes", {}) or {}
        val = dados.get("valuation", {}) or {}

        if chave in proj and proj.get(chave):
            return proj.get(chave, {})

        aliases = {
            "capital_de_giro": "ncg",
            "capex_receita": "capex_pct_receita",
            "receita_mm": "receita_liquida",
            "ebitda_mm": "ebitda",
            "ebit_mm": "ebit",
            "lucro_mm": "lucro_liquido",
            "nopat_mm": "nopat",
            "divida_liquida_mm": "divida_liquida",
            "pl_mm": "patrimonio_liquido",
            "ativo_total_mm": "ativo_total",
            "margem_ebitda": "margem_ebitda_proj",
            "margem_ebit": "margem_ebit_proj",
            "aliquota_efetiva": "aliquota_efetiva_proj",
        }
        if chave in aliases:
            return self._proj_modelo(dados, aliases[chave])

        receita = proj.get("receita_liquida", {})
        lucro = proj.get("lucro_liquido", {})
        ebitda = proj.get("ebitda", {})
        ebit = proj.get("ebit", {})
        nopat = proj.get("nopat", {})

        if chave == "margem_bruta":
            return self._div_series(self._proj_modelo(dados, "lucro_bruto"), receita)
        if chave == "margem_liquida":
            return self._div_series(lucro, receita)
        if chave == "capex_pct_receita":
            capex = self._proj_modelo(dados, "capex")
            return {ano: abs(v) / receita[ano] for ano, v in capex.items() if receita.get(ano)}
        if chave == "da_pct_receita":
            da = self._proj_modelo(dados, "depreciacao_amortizacao")
            return {ano: v / receita[ano] for ano, v in da.items() if receita.get(ano)}
        if chave == "ncg_pct_receita":
            return self._div_series(self._proj_modelo(dados, "capital_de_giro"), receita)
        if chave == "capex_liquido":
            capex = self._proj_modelo(dados, "capex")
            da = self._proj_modelo(dados, "depreciacao_amortizacao")
            return {ano: capex.get(ano, 0) + da.get(ano, 0) for ano in self.anos_proj if ano in capex}

        if chave == "patrimonio_liquido":
            pl = self._ultimo_hist(dados, "patrimonio_liquido")
            dividendos = proj.get("dividendos", {})
            saida = {}
            for ano in self.anos_proj:
                pl += lucro.get(ano, 0) - dividendos.get(ano, 0)
                saida[ano] = round(pl, 3)
            return saida

        if chave in {"divida_liquida", "divida_bruta"}:
            base = self._ultimo_hist(dados, chave)
            return {ano: round(base, 3) for ano in self.anos_proj} if base else {}

        if chave == "capital_investido":
            pl = self._proj_modelo(dados, "patrimonio_liquido")
            dl = self._proj_modelo(dados, "divida_liquida")
            return {ano: pl.get(ano, 0) + dl.get(ano, 0) for ano in self.anos_proj if pl.get(ano) or dl.get(ano)}

        if chave == "ativo_total":
            derivado = self._proj_por_receita(dados, "ativo_total")
            if derivado:
                return derivado
            pl = self._proj_modelo(dados, "patrimonio_liquido")
            dl = self._proj_modelo(dados, "divida_liquida")
            return {ano: pl.get(ano, 0) + dl.get(ano, 0) for ano in self.anos_proj if pl.get(ano) or dl.get(ano)}

        linhas_balanco = {
            "caixa_equivalentes", "aplicacoes_financeiras_cp", "contas_receber",
            "estoques", "outros_ativos_circulantes", "ativo_circulante",
            "realizavel_lp", "investimentos", "imobilizado", "intangivel",
            "ativo_nao_circulante", "fornecedores", "emprestimos_cp",
            "outros_passivos_circulantes", "passivo_circulante",
            "emprestimos_lp", "outros_passivos_nao_circ", "passivo_nao_circulante",
        }
        if chave in linhas_balanco:
            return self._proj_por_receita(dados, chave)

        ativo_total = self._proj_modelo(dados, "ativo_total")
        pl = self._proj_modelo(dados, "patrimonio_liquido")
        divida_liq = self._proj_modelo(dados, "divida_liquida")
        divida_bruta = self._proj_modelo(dados, "divida_bruta")

        if chave == "roe":
            return self._div_series(lucro, pl)
        if chave == "roa":
            return self._div_series(lucro, ativo_total)
        if chave == "roic":
            return self._div_series(nopat, self._proj_modelo(dados, "capital_investido"))
        if chave == "giro_ativo":
            return self._div_series(receita, ativo_total)
        if chave == "dl_ebitda":
            return self._div_series(divida_liq, ebitda)
        if chave == "dl_pl":
            return self._div_series(divida_liq, pl)
        if chave == "divida_bruta_pl":
            return self._div_series(divida_bruta, pl)
        if chave == "alavancagem":
            return self._div_series(ativo_total, pl)
        if chave in {"cobertura_juros_ebitda", "cobertura_juros_ebit"}:
            juros = {ano: abs(v) for ano, v in self._proj_modelo(dados, "resultado_financeiro").items()}
            return self._div_series(ebitda if chave.endswith("ebitda") else ebit, juros)
        if chave == "ev_ebitda":
            ev = val.get("ev_mm", 0)
            return {ano: ev / v for ano, v in ebitda.items() if v and ev}
        if chave == "p_l":
            equity = val.get("equity_mm", 0)
            return {ano: equity / v for ano, v in lucro.items() if v and equity}
        if chave == "p_vp":
            equity = val.get("equity_mm", 0)
            return {ano: equity / v for ano, v in pl.items() if v and equity}

        return {}

    def _calc_margin(self, dre, proj, num_key, den_key) -> (dict, dict):
        """Calcula margem (num/den) para histórico e projeção."""
        hist, proj_r = {}, {}
        # Histórico
        for ano in self.anos_hist:
            num = self._get_hist(dre, num_key).get(ano)
            den = self._get_hist(dre, den_key).get(ano)
            if num is not None and den and den != 0:
                hist[ano] = num / den
        # Projeção
        num_p = proj.get(num_key, {})
        den_p = proj.get(den_key, {})
        for ano in self.anos_proj:
            n, d = num_p.get(ano), den_p.get(ano)
            if n is not None and d and d != 0:
                proj_r[ano] = n / d
        return hist, proj_r

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 1 — DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_dashboard(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Dashboard", 0)
        val  = dados.get("valuation", {})
        merc = dados.get("mercado", {})

        # Título
        self._write_title(ws, f"VALUATION — {nome} ({self.ticker})", max_col=8)
        self._aplicar_logo_dashboard(ws)

        # ── Sidebar de navegação (col A-B, rows 3-15) ────────────────────
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 6
        ws.column_dimensions["C"].width = 3    # spacer
        ws.column_dimensions["D"].width = 32
        ws.column_dimensions["E"].width = 22
        ws.column_dimensions["F"].width = 3    # spacer
        ws.column_dimensions["G"].width = 32
        ws.column_dimensions["H"].width = 22

        nav_items = ["Dashboard", "WACC", "TIR ON", "TIR PN",
                     "Valor do Equity", "Preço Teto", "DRE + DCF",
                     "DRE Contas Abertas", "Balanço Patrimonial",
                     "Painel de Índices", "Projeções Premissas",
                     "Projeções Capex e CG"]

        ws.cell(row=3, column=1, value="Páginas").font = _f(bold=True, size=10)
        ws.cell(row=3, column=1).fill = FILL_SUBHDR
        ws.cell(row=3, column=1).border = _border()
        for i, item in enumerate(nav_items, start=4):
            c = ws.cell(row=i, column=1, value=item)
            c.font = _f(C_HEADER, size=9)
            c.fill = FILL_NAV
            c.border = _border()

        # ── Bloco central: Dados da empresa (col D-E) ────────────────────
        r = 3
        ws.cell(row=r, column=4, value="DADOS DA EMPRESA").font = _hf(10)
        ws.cell(row=r, column=4).fill = FILL_HDR
        ws.cell(row=r, column=5).fill = FILL_HDR
        ws.cell(row=r, column=4).border = _border()
        ws.cell(row=r, column=5).border = _border()

        dados_emp = [
            ("Trimestre Atual",              dados.get("_trimestre", "—")),
            ("Ticker",                       self.ticker),
            ("Ações ON Emitidas (mil)",      val.get("acoes_on_mil", 0)),
            ("Ações PN Emitidas (mil)",      val.get("acoes_pn_mil", 0)),
            ("Relação PN/ON",                val.get("relacao_pn_on", 1.0)),
            ("Total de Ações (mil)",         val.get("acoes_on_mil", 0) + val.get("acoes_pn_mil", 0)),
        ]
        for i, (lbl, v) in enumerate(dados_emp, start=4):
            ws.cell(row=i, column=4, value=lbl).font = _f(bold=True)
            ws.cell(row=i, column=4).border = _border()
            cell_v = ws.cell(row=i, column=5, value=v)
            cell_v.border = _border()
            cell_v.alignment = Alignment(horizontal="right")
            if isinstance(v, (int, float)) and v != 0:
                cell_v.number_format = NUM_FMT

        # ── Bloco direito: Resultado do Valuation (col G-H) ──────────────
        ws.cell(row=3, column=7, value="RESULTADO DO VALUATION").font = _hf(10)
        ws.cell(row=3, column=7).fill = FILL_HDR
        ws.cell(row=3, column=8).fill = FILL_HDR
        ws.cell(row=3, column=7).border = _border()
        ws.cell(row=3, column=8).border = _border()

        val_items = [
            ("VP FCFF (fase explícita)",   val.get("vp_fcff", 0),            NUM_FMT,  False),
            ("VP Perpetuidade",            val.get("vp_perpetuidade", 0),     NUM_FMT,  False),
            ("Enterprise Value (R$ MM)",   val.get("ev_mm", 0),              NUM_FMT,  True),
            ("(-) Dívida Líquida (R$ MM)", val.get("divida_liquida", 0),     NUM_FMT,  False),
            ("Valor do Equity (R$ MM)",    val.get("equity_mm", 0),          NUM_FMT,  True),
            ("",                           "",                               None,     False),
            ("Preço Justo ON (R$)",        val.get("preco_justo_on", 0),     BRL_FMT,  True),
            ("Preço Justo PN (R$)",        val.get("preco_justo_pn", 0),     BRL_FMT,  False),
            ("Cotação Atual ON (R$)",      merc.get("preco", 0),             BRL_FMT,  False),
            ("Upside ON (%)",              val.get("upside_on", 0),          PCT_FMT1, True),
            ("TIR ON (%)",                 val.get("tir_on", 0),             PCT_FMT1, False),
            ("Preço Teto ON (R$)",         val.get("preco_teto_on", 0),      BRL_FMT,  False),
        ]

        for i, (lbl, v, fmt, acc) in enumerate(val_items, start=4):
            if not lbl:
                continue
            cl = ws.cell(row=i, column=7, value=lbl)
            cl.font = _f(bold=acc)
            cl.border = _border()
            if acc:
                cl.fill = FILL_ACCENT
            cv = ws.cell(row=i, column=8, value=v)
            cv.border = _border()
            cv.alignment = Alignment(horizontal="right")
            if acc:
                cv.fill = FILL_ACCENT
                cv.font = _f(C_GREEN, bold=True)
            if fmt:
                cv.number_format = fmt

        # ── WACC summary (abaixo) ────────────────────────────────────────
        r_wacc = 18
        ws.cell(row=r_wacc, column=4, value="WACC").font = _hf(10)
        ws.cell(row=r_wacc, column=4).fill = FILL_HDR
        ws.cell(row=r_wacc, column=5).fill = FILL_HDR
        ws.cell(row=r_wacc, column=4).border = _border()

        macro = dados.get("macro", {})
        wacc_proj = macro.get("projecao", {}).get("wacc", {})
        ke_proj   = macro.get("projecao", {}).get("ke", {})
        primeiro_ano = self.anos_proj[0] if self.anos_proj else None

        wacc_items = [
            ("Ke (%)",   ke_proj.get(primeiro_ano, 0) if primeiro_ano else 0),
            ("WACC (%)", wacc_proj.get(primeiro_ano, 0) if primeiro_ano else 0),
            ("g perpetuidade (%)", val.get("g", 0.055)),
        ]
        for i, (lbl, v) in enumerate(wacc_items, start=r_wacc + 1):
            ws.cell(row=i, column=4, value=lbl).font = _f(bold=True)
            ws.cell(row=i, column=4).border = _border()
            cv = ws.cell(row=i, column=5, value=v)
            cv.number_format = PCT_FMT2
            cv.border = _border()
            cv.alignment = Alignment(horizontal="right")

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 2 — METODOLOGIA
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_metodologia(self, wb, nome: str, dados: dict):
        """Documenta o motor e as premissas usadas para a empresa."""
        ws = wb.create_sheet("Metodologia")
        self._write_title(ws, f"Metodologia — {nome} ({self.ticker})", max_col=6)

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 42
        ws.column_dimensions["C"].width = 4
        ws.column_dimensions["D"].width = 34
        ws.column_dimensions["E"].width = 22
        ws.column_dimensions["F"].width = 22

        meta = dados.get("metodologia", {}) or {}
        prem = meta.get("premissas", {}) or {}
        prem_efetivas = meta.get("premissas_efetivas", {}) or {}
        valuation = dados.get("valuation", {}) or {}
        proj = dados.get("projecoes", {}) or {}
        mercado = dados.get("mercado", {}) or {}

        setor = str(meta.get("setor") or "geral")
        motor_val = str(meta.get("motor_valuation") or "wacc").upper()
        motor_proj = str(meta.get("motor_projecao") or "fcff").upper()
        tipo_empresa = str(meta.get("tipo_empresa") or "general")

        descricao_setor = {
            "energia": "Utilities: fluxo regulado/contratado, CAPEX alto, payout geralmente elevado.",
            "saneamento": "Infraestrutura regulada: CAPEX alto, retorno de longo prazo e demanda resiliente.",
            "industrial": "Indústria: margens e reinvestimento dependem do ciclo e da vantagem competitiva.",
            "papel_celulose": "Commodity/exportadora: margens cíclicas, câmbio e CAPEX estrutural relevantes.",
            "logistica": "Ativos intensivos: alavancagem operacional, concessões/frota e reinvestimento relevantes.",
            "construcao_civil": "Ciclo imobiliário: estoque, lançamentos, velocidade de vendas e capital de giro pesam.",
            "consumo_varejo": "Varejo/consumo: margem, giro de estoque, NCG e sensibilidade a juros/renda.",
            "agro": "Agronegócio: ciclo de commodities, clima, capital de giro e expansão de área/capacidade.",
            "telecom": "Base recorrente: CAPEX de rede, churn, ARPU e crescimento moderado.",
            "saude": "Serviços/saúde: margem operacional, ocupação/escala, M&A e capital de giro.",
            "locacao_veiculos": "Locadoras: frota, depreciação, CAPEX elevado e ciclo de seminovos.",
            "petroleo": "Óleo e gás: preço de commodity, reservas, lifting cost, CAPEX e declínio dos campos.",
            "tecnologia": "Tecnologia: crescimento, margem incremental, retenção e intensidade de investimento.",
        }
        razao_motor = (
            "Banco: valuation por FCFE/Ke, pois dívida operacional não é tratada como estrutura de capital comum."
            if tipo_empresa == "bank"
            else "Empresa não-financeira: valuation por FCFF/WACC, separando valor operacional, dívida líquida e equity."
        )

        def header(row: int, title: str, start_col: int = 1, end_col: int = 6):
            for col in range(start_col, end_col + 1):
                c = ws.cell(row=row, column=col)
                c.fill = FILL_HDR
                c.border = _border()
            c0 = ws.cell(row=row, column=start_col, value=title)
            c0.font = _hf(10)

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
            ws.cell(row=row, column=col, value=label).font = _f(bold=True)
            ws.cell(row=row, column=col).border = _border()
            cell = ws.cell(row=row, column=col + 1, value=value)
            cell.border = _border()
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fmt and isinstance(value, (int, float)):
                cell.number_format = fmt
            return cell

        header(3, "Enquadramento")
        pair(4, "Setor", setor)
        pair(5, "Tipo de Empresa", tipo_empresa)
        pair(6, "Motor de Projeção", motor_proj)
        pair(7, "Motor de Valuation", motor_val)
        pair(8, "Tipo de Ação", meta.get("tipo_acao") or "-")
        pair(9, "Tese metodológica", razao_motor)
        ws.merge_cells(start_row=9, start_column=2, end_row=9, end_column=6)

        header(11, "Leitura Econômica do Setor")
        ws.cell(row=12, column=1, value="Foco Analítico").font = _f(bold=True)
        ws.cell(row=12, column=1).border = _border()
        ws.merge_cells(start_row=12, start_column=2, end_row=12, end_column=6)
        c = ws.cell(row=12, column=2, value=descricao_setor.get(setor, "Modelo geral: crescimento, margem, reinvestimento, risco e estrutura de capital."))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.border = _border()
        ws.row_dimensions[12].height = 42

        header(15, "Premissas-Chave", 1, 3)
        premissas_chave = [
            ("Margem EBITDA alvo", prem.get("margem_ebitda_alvo"), PCT_FMT1),
            ("CAPEX / Receita", prem.get("capex_pct_receita"), PCT_FMT1),
            ("NCG / Receita", prem.get("ncg_pct_receita"), PCT_FMT1),
            ("Payout", prem.get("payout"), PCT_FMT1),
            ("g perpetuidade", prem.get("g_perpetuidade"), PCT_FMT1),
            ("Beta", prem.get("beta"), NUM_FMT2),
            ("Spread dívida", prem.get("custo_divida_spread"), PCT_FMT1),
        ]
        r = 16
        for label, value, fmt in premissas_chave:
            if value is None:
                continue
            pair(r, label, value, fmt)
            r += 1

        header(15, "Saídas do Modelo", 4, 6)
        fcff = proj.get("fcff") or {}
        fcff_ultimo = fcff.get(max(fcff.keys())) if fcff else None
        saidas = [
            ("Enterprise Value (R$ MM)", valuation.get("ev_mm"), NUM_FMT),
            ("Valor do Equity (R$ MM)", valuation.get("equity_mm"), NUM_FMT),
            ("Preço Justo ON", valuation.get("preco_justo_on"), BRL_FMT),
            ("Upside ON", valuation.get("upside_on"), PCT_FMT1),
            ("TIR ON", valuation.get("tir_on"), PCT_FMT1),
            ("FCFF último ano", fcff_ultimo, NUM_FMT),
        ]
        r = 16
        for label, value, fmt in saidas:
            if value is None:
                continue
            pair(r, label, value, fmt, col=4)
            r += 1

        header(25, "Governança do Modelo")
        notas = [
            "Layout visual padronizado; metodologia determinada por setor, tipo de empresa e premissas no empresas.yaml.",
            "Histórico financeiro vem da CVM; mercado, preço, volume e liquidez vêm de B3/yfinance/cache.",
            "Premissas específicas da empresa sobrescrevem premissas setoriais, que sobrescrevem defaults globais.",
        ]
        for i, nota in enumerate(notas, start=26):
            ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
            cell = ws.cell(row=i, column=1, value=nota)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = _border()
            ws.row_dimensions[i].height = 30

        header(32, "Separação entre Dados e Premissas")
        fonte_rows = [
            ("Status do Valuation", prem_efetivas.get("status_valuation") or valuation.get("status_valuation")),
            ("Classe Principal", prem_efetivas.get("classe_principal") or valuation.get("classe_principal")),
            ("Beta usado", prem_efetivas.get("beta_usado")),
            ("Fonte do beta", prem_efetivas.get("beta_fonte")),
            ("g perpetuidade", prem_efetivas.get("g_perpetuidade")),
            ("Origem dos demonstrativos", "CVM/DFP/ITR normalizados"),
            ("Origem mercado", mercado.get("fonte_mercado") or "B3/yfinance/cache ou input CLI"),
            ("Premissas subjetivas", "empresas.yaml/settings/CLI; ver outputs/assumptions"),
        ]
        r = 33
        for label, value in fonte_rows:
            if value is None:
                continue
            pair(r, label, value)
            r += 1

        ws.freeze_panes = "A3"

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 3 — WACC
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_wacc(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("WACC")
        macro = dados.get("macro", {})
        hist  = macro.get("historico", {})
        proj  = macro.get("projecao", {})
        meta = dados.get("metodologia", {}) or {}
        prem = meta.get("premissas", {}) or {}
        merc = dados.get("mercado", {}) or {}
        val = dados.get("valuation", {}) or {}

        self._write_title(ws, f"WACC — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        beta = (
            prem.get("beta")
            or prem.get("beta_utilizado")
            or merc.get("beta_usar")
            or merc.get("beta_calc")
            or 0.85
        )
        erp = prem.get("premio_risco") or prem.get("equity_risk_premium") or 0.065
        spread_divida = prem.get("custo_divida_spread") or prem.get("spread_divida") or 0.02
        aliquota_ir = prem.get("aliquota_ir") or prem.get("aliquota_efetiva") or 0.34

        di_hist = hist.get("selic_efet", {}) or hist.get("di", {})
        di_proj = proj.get("di", {})
        cds_hist = hist.get("cds", {})
        cds_proj = proj.get("cds", {})

        def serie_constante(anos, valor):
            return {ano: valor for ano in anos}

        def calcular_ke(di, cds):
            resultado = {}
            for ano, rf in (di or {}).items():
                resultado[ano] = max((rf or 0) + (cds or {}).get(ano, 0) + beta * erp, 0.08)
            return resultado

        ke_hist = calcular_ke(di_hist, cds_hist)
        ke_proj = proj.get("ke", {}) or calcular_ke(di_proj, cds_proj)

        divida_liq = self._ultimo_hist(dados, "divida_liquida")
        acoes_total_mil = val.get("acoes_on_mil", 0) + val.get("acoes_pn_mil", 0)
        market_cap = merc.get("market_cap_mm") or 0
        preco = merc.get("preco") or merc.get("cotacao_on") or 0
        if not market_cap and preco and acoes_total_mil:
            market_cap = preco * acoes_total_mil / 1000
        ev_mercado = market_cap + max(divida_liq, 0)
        peso_equity = market_cap / ev_mercado if ev_mercado else prem.get("peso_equity", 0.60)
        peso_equity = max(0.20, min(float(peso_equity or 0.60), 0.95))
        peso_divida = 1 - peso_equity

        kd_bruto_hist = {ano: (di_hist.get(ano, 0) or 0) + spread_divida for ano in self.anos_hist if ano in di_hist}
        kd_bruto_proj = {ano: (di_proj.get(ano, 0) or 0) + spread_divida for ano in self.anos_proj if ano in di_proj}
        kd_liq_hist = {ano: kd_bruto_hist[ano] * (1 - aliquota_ir) for ano in kd_bruto_hist}
        kd_liq_proj = {ano: kd_bruto_proj[ano] * (1 - aliquota_ir) for ano in kd_bruto_proj}
        peso_e_hist = serie_constante(self.anos_hist, peso_equity)
        peso_e_proj = serie_constante(self.anos_proj, peso_equity)
        peso_d_hist = serie_constante(self.anos_hist, peso_divida)
        peso_d_proj = serie_constante(self.anos_proj, peso_divida)
        wacc_hist = {
            ano: max(ke_hist.get(ano, 0) * peso_equity + kd_liq_hist.get(ano, 0) * peso_divida, 0.06)
            for ano in self.anos_hist
            if ano in ke_hist or ano in kd_liq_hist
        }

        r = 5
        self._write_section_header(ws, r, "TAXAS MACROECONÔMICAS", col_mapa); r += 1

        taxas = [
            ("Selic / DI (% a.a.)",         "selic_efet",    "di",            PCT_FMT2),
            ("CDS Brasil (% a.a.)",         "cds",           "cds",           PCT_FMT2),
            ("IPCA / Inflação (% a.a.)",    "ipca",          "ipca",          PCT_FMT2),
        ]
        for lbl, hk, pk, fmt in taxas:
            h = hist.get(hk, {})
            p = proj.get(pk, {})
            # tentar inflação implícita como fallback
            if not p and pk == "ipca":
                p = proj.get("inflacao_impl", {})
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt); r += 1

        r += 1
        self._write_section_header(ws, r, "CAPM — CUSTO DO CAPITAL PRÓPRIO", col_mapa); r += 1

        capm = [
            ("Risk-Free Rate (DI pre)",     "di",            PCT_FMT2),
            ("CDS Brasil",                  "cds",           PCT_FMT2),
            ("Equity Risk Premium",         None,            PCT_FMT2),
            ("Beta",                        None,            "0.00"),
            ("Ke — Custo do Equity (%)",    "ke",            PCT_FMT2),
        ]
        for lbl, pk, fmt in capm:
            if pk == "di":
                h, p = di_hist, di_proj
            elif pk == "cds":
                h, p = cds_hist, cds_proj
            elif pk == "ke":
                h, p = ke_hist, ke_proj
            elif "Premium" in lbl:
                h = serie_constante(self.anos_hist, erp)
                p = serie_constante(self.anos_proj, erp)
            elif lbl == "Beta":
                h = serie_constante(self.anos_hist, beta)
                p = serie_constante(self.anos_proj, beta)
            else:
                h, p = {}, {}
            acc = "Ke" in lbl
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc); r += 1

        r += 1
        self._write_section_header(ws, r, "CUSTO DA DÍVIDA E WACC", col_mapa); r += 1

        wacc_items = [
            ("Kd bruto (DI + spread)",      {},    {a: (proj.get("di",{}).get(a,0) or 0) + 0.02 for a in self.anos_proj}, PCT_FMT2, False),
            ("Alíquota IR nominal",         {},    {a: 0.34 for a in self.anos_proj}, PCT_FMT2, False),
            ("Kd líquido de IR",            {},    {a: ((proj.get("di",{}).get(a,0) or 0) + 0.02) * (1 - 0.34) for a in self.anos_proj}, PCT_FMT2, False),
            ("E / (E+D) — Peso Equity",     {},    {},  PCT_FMT2, False),
            ("D / (E+D) — Peso Dívida",     {},    {},  PCT_FMT2, False),
            ("WACC (%)",                    {},    proj.get("wacc", {}), PCT_FMT2, True),
        ]
        wacc_items = [
            ("Kd bruto (DI + spread)", kd_bruto_hist, kd_bruto_proj, PCT_FMT2, False),
            ("Aliquota IR nominal", serie_constante(self.anos_hist, aliquota_ir), serie_constante(self.anos_proj, aliquota_ir), PCT_FMT2, False),
            ("Kd liquido de IR", kd_liq_hist, kd_liq_proj, PCT_FMT2, False),
            ("E / (E+D) - Peso Equity", peso_e_hist, peso_e_proj, PCT_FMT2, False),
            ("D / (E+D) - Peso Divida", peso_d_hist, peso_d_proj, PCT_FMT2, False),
            ("WACC (%)", wacc_hist, proj.get("wacc", {}), PCT_FMT2, True),
        ]
        for lbl, h, p, fmt, acc in wacc_items:
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc); r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABAS 3-4 — TIR ON / TIR PN
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_tir(self, wb, nome: str, dados: dict, tipo: str = "ON"):
        ws = wb.create_sheet(f"TIR {tipo}")
        val  = dados.get("valuation", {})
        proj = dados.get("projecoes", {})
        merc = dados.get("mercado", {})

        self._write_title(ws, f"TIR {tipo} — {nome}", max_col=len(self.anos_proj)+2)

        # Cabeçalho anos projeção + "Perpetuidade"
        ws.column_dimensions["A"].width = 36
        col_mapa = {}
        for i, ano in enumerate(self.anos_proj):
            col = 2 + i
            cell = ws.cell(row=3, column=col, value=ano)
            cell.font = _hf(9); cell.fill = FILL_HDR
            cell.alignment = Alignment(horizontal="center"); cell.border = _border()
            ws.column_dimensions[get_column_letter(col)].width = 14.5
            col_mapa[ano] = col
        col_perp = 2 + len(self.anos_proj)
        cell_p = ws.cell(row=3, column=col_perp, value="Perpetuidade")
        cell_p.font = _hf(9); cell_p.fill = FILL_HDR
        cell_p.alignment = Alignment(horizontal="center"); cell_p.border = _border()
        ws.column_dimensions[get_column_letter(col_perp)].width = 16

        ws.cell(row=3, column=1, value="(R$)").font = _f(bold=True)
        ws.cell(row=3, column=1).fill = FILL_SUBHDR
        ws.cell(row=3, column=1).border = _border()

        r = 5
        chave_preco = "preco_justo_on" if tipo == "ON" else "preco_justo_pn"
        chave_upside = "upside_on" if tipo == "ON" else "upside_pn"
        chave_tir = "tir_on" if tipo == "ON" else "tir_pn"

        cotacao = merc.get("preco", 0)
        preco_justo = val.get(chave_preco, 0)

        # Fluxo de caixa: investimento inicial = -cotação
        self._write_section_header(ws, r, f"FLUXO DE CAIXA — AÇÃO {tipo}", col_mapa); r += 1

        # Investimento (Ano 0)
        ws.cell(row=r, column=1, value="(-) Investimento Inicial (Cotação)").font = _f(bold=True)
        ws.cell(row=r, column=1).border = _border()
        ws.cell(row=r, column=2, value=-cotacao).font = _f(C_RED, bold=True)
        ws.cell(row=r, column=2).number_format = BRL_FMT
        ws.cell(row=r, column=2).border = _border()
        r += 1

        # Dividendos projetados
        div_proj = proj.get("dividendos", {})
        payout = proj.get("payout", {})
        lucro = proj.get("lucro_liquido", {})
        acoes_total = (val.get("acoes_on_mil", 0) + val.get("acoes_pn_mil", 0))

        ws.cell(row=r, column=1, value="Dividendos por Ação (R$)").font = _f()
        ws.cell(row=r, column=1).border = _border()
        for ano in self.anos_proj:
            col = col_mapa.get(ano)
            if col:
                dpa = div_proj.get(ano, 0)
                if dpa == 0 and lucro.get(ano) and acoes_total > 0:
                    pay = payout.get(ano, 0.4) if isinstance(payout, dict) else 0.4
                    dpa = lucro[ano] * pay / (acoes_total / 1000)
                cell = ws.cell(row=r, column=col, value=round(dpa, 4) if dpa else 0)
                cell.font = _f(C_GREEN); cell.number_format = BRL_FMT; cell.border = _border()
        r += 1

        # Valor terminal
        ws.cell(row=r, column=1, value="(+) Valor Terminal (Preço Justo)").font = _f(bold=True)
        ws.cell(row=r, column=1).fill = FILL_ACCENT; ws.cell(row=r, column=1).border = _border()
        ws.cell(row=r, column=col_perp, value=preco_justo).font = _f(C_GREEN, bold=True)
        ws.cell(row=r, column=col_perp).number_format = BRL_FMT
        ws.cell(row=r, column=col_perp).fill = FILL_ACCENT; ws.cell(row=r, column=col_perp).border = _border()
        r += 2

        # Resultado
        self._write_section_header(ws, r, "RESULTADO", col_mapa); r += 1
        result_items = [
            ("Cotação Atual (R$)",       cotacao,                 BRL_FMT,  False),
            ("Preço Justo (R$)",         preco_justo,             BRL_FMT,  True),
            ("Upside (%)",               val.get(chave_upside, 0), PCT_FMT1, True),
            ("TIR (%)",                  val.get(chave_tir, 0),    PCT_FMT1, True),
        ]
        for lbl, v, fmt, acc in result_items:
            cl = ws.cell(row=r, column=1, value=lbl)
            cl.font = _f(bold=acc); cl.border = _border()
            if acc: cl.fill = FILL_ACCENT
            cv = ws.cell(row=r, column=2, value=v)
            cv.number_format = fmt; cv.border = _border()
            cv.alignment = Alignment(horizontal="right")
            if acc:
                cv.fill = FILL_ACCENT
                cv.font = _f(C_GREEN, bold=True)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 5 — VALOR DO EQUITY
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_equity(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Valor do Equity")
        val = dados.get("valuation", {})

        self._write_title(ws, f"Valor do Equity — {nome}", max_col=4)
        ws.column_dimensions["A"].width = 42
        ws.column_dimensions["B"].width = 24

        r = 3
        self._write_section_header(ws, r, "ENTERPRISE VALUE", {})
        r += 1

        bridge = [
            ("VP dos FCFF (fase explícita, R$ MM)", val.get("vp_fcff", 0),          NUM_FMT,  False),
            ("VP da Perpetuidade (R$ MM)",           val.get("vp_perpetuidade", 0),   NUM_FMT,  False),
            ("ENTERPRISE VALUE (R$ MM)",             val.get("ev_mm", 0),             NUM_FMT,  True),
            ("",                                     "",                              None,     False),
            ("(-) Dívida Líquida (R$ MM)",           val.get("divida_liquida", 0),    NUM_FMT,  False),
            ("(+) Ativos Não-Operacionais",          0,                               NUM_FMT,  False),
            ("(-) Passivos Não-Operacionais",        0,                               NUM_FMT,  False),
            ("",                                     "",                              None,     False),
            ("VALOR DO EQUITY (R$ MM)",              val.get("equity_mm", 0),         NUM_FMT,  True),
        ]

        for lbl, v, fmt, acc in bridge:
            if not lbl:
                r += 1; continue
            cl = ws.cell(row=r, column=1, value=lbl)
            cl.font = _f(bold=acc); cl.border = _border()
            if acc: cl.fill = FILL_ACCENT
            cv = ws.cell(row=r, column=2, value=v)
            cv.number_format = fmt or NUM_FMT; cv.border = _border()
            cv.alignment = Alignment(horizontal="right")
            if acc: cv.fill = FILL_ACCENT; cv.font = _f(C_GREEN, bold=True)
            r += 1

        r += 1
        self._write_section_header(ws, r, "PREÇO POR AÇÃO", {}); r += 1

        acoes_on  = val.get("acoes_on_mil", 0)
        acoes_pn  = val.get("acoes_pn_mil", 0)
        preco_items = [
            ("Ações ON Emitidas (mil)",      acoes_on,                          NUM_FMT,  False),
            ("Ações PN Emitidas (mil)",      acoes_pn,                          NUM_FMT,  False),
            ("Total de Ações (mil)",         acoes_on + acoes_pn,               NUM_FMT,  False),
            ("Relação PN/ON",                val.get("relacao_pn_on", 1.0),     "0.00",   False),
            ("",                             "",                                None,     False),
            ("Preço Justo ON (R$)",          val.get("preco_justo_on", 0),      BRL_FMT,  True),
            ("Preço Justo PN (R$)",          val.get("preco_justo_pn", 0),      BRL_FMT,  True),
        ]
        for lbl, v, fmt, acc in preco_items:
            if not lbl: r += 1; continue
            cl = ws.cell(row=r, column=1, value=lbl); cl.font = _f(bold=acc); cl.border = _border()
            if acc: cl.fill = FILL_ACCENT
            cv = ws.cell(row=r, column=2, value=v)
            cv.number_format = fmt or NUM_FMT; cv.border = _border()
            cv.alignment = Alignment(horizontal="right")
            if acc: cv.fill = FILL_ACCENT; cv.font = _f(C_GREEN, bold=True)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 6 — PREÇO TETO
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_preco_teto(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Preço Teto")
        val  = dados.get("valuation", {})
        merc = dados.get("mercado", {})

        self._write_title(ws, f"Preço Teto — {nome}", max_col=5)
        ws.column_dimensions["A"].width = 38
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 20
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 20

        r = 3
        pj_on = val.get("preco_justo_on", 0)
        pj_pn = val.get("preco_justo_pn", 0)
        cotacao = merc.get("preco", 0)

        self._write_section_header(ws, r, "MARGEM DE SEGURANÇA — AÇÃO ON", {}); r += 1

        # Header
        for ci, label in [(1, "Margem de Segurança"), (2, "Preço Teto (R$)"),
                          (3, "Upside vs. Cotação"), (4, "Recomendação")]:
            c = ws.cell(row=r, column=ci, value=label)
            c.font = _hf(9); c.fill = FILL_HDR; c.border = _border()
            c.alignment = Alignment(horizontal="center")
        r += 1

        margens = [0.0, 0.10, 0.15, 0.20, 0.25, 0.30]
        for mg in margens:
            teto = pj_on * (1 - mg)
            upside_teto = (teto / cotacao - 1) if cotacao > 0 else 0
            if mg == 0:
                rec = "Preço Justo"
            elif cotacao <= teto:
                rec = "COMPRA"
            else:
                rec = "Aguardar"

            ws.cell(row=r, column=1, value=mg).number_format = PCT_FMT1
            ws.cell(row=r, column=1).font = _f(bold=(mg==0))
            ws.cell(row=r, column=1).border = _border()
            ws.cell(row=r, column=1).alignment = Alignment(horizontal="center")

            ws.cell(row=r, column=2, value=teto).number_format = BRL_FMT
            ws.cell(row=r, column=2).font = _f(C_GREEN, bold=(mg==0))
            ws.cell(row=r, column=2).border = _border()
            ws.cell(row=r, column=2).alignment = Alignment(horizontal="right")

            ws.cell(row=r, column=3, value=upside_teto).number_format = PCT_FMT1
            ws.cell(row=r, column=3).border = _border()
            ws.cell(row=r, column=3).alignment = Alignment(horizontal="right")

            c_rec = ws.cell(row=r, column=4, value=rec)
            c_rec.border = _border()
            c_rec.alignment = Alignment(horizontal="center")
            if rec == "COMPRA":
                c_rec.font = _f(C_DKGREEN, bold=True)
                c_rec.fill = FILL_ACCENT
            elif rec == "Preço Justo":
                c_rec.font = _f(C_GREEN, bold=True)
            else:
                c_rec.font = _f(C_ORANGE)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 7 — DRE + DCF
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_dre_dcf(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("DRE + DCF")
        dre  = dados.get("dre", pd.DataFrame())
        proj = dados.get("projecoes", {})
        val  = dados.get("valuation", {})
        macro = dados.get("macro", {})

        self._write_title(ws, f"DRE + DCF — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        r = 5

        # ── DRE ──────────────────────────────────────────────────────────
        self._write_section_header(ws, r, "DEMONSTRAÇÃO DE RESULTADO (DRE)", col_mapa); r += 1

        dre_lines = [
            ("Receita Líquida",                  "receita_liquida",              NUM_FMT,  True,  0),
            ("Crescimento Receita (%)",          "_cresc",                       PCT_FMT1, False, 1),
            ("(-) Custo dos Produtos/Serviços",  "custo_mercadorias",            NUM_FMT,  False, 0),
            ("Lucro Bruto",                      "lucro_bruto",                  NUM_FMT,  True,  0),
            ("Margem Bruta (%)",                 "_mgb",                         PCT_FMT1, False, 1),
            ("(-) Despesas com Vendas",          "despesas_vendas",              NUM_FMT,  False, 0),
            ("(-) Despesas Gerais e Admin.",      "despesas_gerais_adm",          NUM_FMT,  False, 0),
            ("(-) Outras Despesas Operacionais", "outras_despesas_operacionais",  NUM_FMT,  False, 0),
            ("(+) Outras Receitas Operacionais", "outras_receitas_operacionais",  NUM_FMT,  False, 0),
            ("(+) Resultado de Equivalência",    "resultado_equivalencia",        NUM_FMT,  False, 0),
            ("EBITDA",                           "ebitda",                        NUM_FMT,  True,  0),
            ("Margem EBITDA (%)",                "_mge",                          PCT_FMT1, False, 1),
            ("(-) Depreciação e Amortização",    "depreciacao_amortizacao",       NUM_FMT,  False, 0),
            ("EBIT",                             "ebit",                          NUM_FMT,  True,  0),
            ("Margem EBIT (%)",                  "_mgebit",                       PCT_FMT1, False, 1),
            ("(+/-) Resultado Financeiro",       "resultado_financeiro",          NUM_FMT,  False, 0),
            ("Receitas Financeiras",             "receitas_financeiras",          NUM_FMT,  False, 1),
            ("Despesas Financeiras",             "despesas_financeiras",          NUM_FMT,  False, 1),
            ("Resultado Antes do IR (EBT)",      "resultado_antes_ir",           NUM_FMT,  False, 0),
            ("(-) IR e CSLL",                    "ir_csll",                       NUM_FMT,  False, 0),
            ("Lucro Líquido",                    "lucro_liquido",                 NUM_FMT,  True,  0),
            ("Margem Líquida (%)",               "_mgl",                          PCT_FMT1, False, 1),
        ]

        for lbl, chave, fmt, acc, indent in dre_lines:
            if chave.startswith("_"):
                h, p = self._resolve_calc(chave, dre, proj)
            else:
                h = self._hist_modelo(dados, chave)
                p = self._proj_modelo(dados, chave)
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc, indent=indent)
            r += 1

        # ── DCF ──────────────────────────────────────────────────────────
        r += 1
        self._write_section_header(ws, r, "FLUXO DE CAIXA DESCONTADO (FCFF)", col_mapa); r += 1

        dcf_lines = [
            ("EBIT",                               "ebit",                  NUM_FMT,  False, 0),
            ("(-) IR sobre EBIT",                  "_ir_ebit",              NUM_FMT,  False, 0),
            ("NOPAT",                              "nopat",                 NUM_FMT,  True,  0),
            ("(+) Depreciação e Amortização",      "depreciacao_amortizacao", NUM_FMT, False, 0),
            ("(-) CAPEX",                          "capex",                 NUM_FMT,  False, 0),
            ("(-) Variação do Capital de Giro",    "delta_ncg",             NUM_FMT,  False, 0),
            ("FCFF",                               "fcff",                  NUM_FMT,  True,  0),
        ]

        for lbl, chave, fmt, acc, indent in dcf_lines:
            if chave.startswith("_"):
                h, p = self._resolve_calc(chave, dre, proj)
            else:
                h = self._hist_modelo(dados, chave)
                p = self._proj_modelo(dados, chave)
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc, indent=indent)
            r += 1

        r += 1
        # WACC e desconto
        wacc_proj = dados.get("macro", {}).get("projecao", {}).get("wacc", {})
        self._write_row(ws, r, "WACC (%)", col_mapa, {}, wacc_proj, fmt=PCT_FMT2)
        r += 1

        fatores = val.get("fatores_desconto", {})
        self._write_row(ws, r, "Fator de Desconto", col_mapa, {}, fatores, fmt="0.0000")
        r += 1

        vp_ano = val.get("vp_fcff_por_ano", {})
        self._write_row(ws, r, "VP do FCFF", col_mapa, {}, vp_ano, fmt=NUM_FMT, accent=True)
        r += 2

        # Resumo Valuation
        self._write_section_header(ws, r, "RESUMO DO VALUATION", col_mapa); r += 1

        resumo = [
            ("VP FCFF (fase explícita)",    val.get("vp_fcff", 0),           NUM_FMT,  False),
            ("VP Perpetuidade",             val.get("vp_perpetuidade", 0),    NUM_FMT,  False),
            ("Enterprise Value (R$ MM)",    val.get("ev_mm", 0),             NUM_FMT,  True),
            ("(-) Dívida Líquida (R$ MM)",  val.get("divida_liquida", 0),    NUM_FMT,  False),
            ("Valor do Equity (R$ MM)",     val.get("equity_mm", 0),         NUM_FMT,  True),
            ("Preço Justo ON (R$)",         val.get("preco_justo_on", 0),    BRL_FMT,  True),
            ("Preço Justo PN (R$)",         val.get("preco_justo_pn", 0),    BRL_FMT,  False),
            ("Upside ON (%)",               val.get("upside_on", 0),         PCT_FMT1, True),
        ]

        for lbl, v, fmt, acc in resumo:
            cl = ws.cell(row=r, column=1, value=lbl)
            cl.font = _f(bold=acc); cl.border = _border()
            if acc: cl.fill = FILL_ACCENT
            cv = ws.cell(row=r, column=2, value=v)
            cv.number_format = fmt; cv.border = _border()
            cv.alignment = Alignment(horizontal="right")
            if acc: cv.fill = FILL_ACCENT; cv.font = _f(C_GREEN, bold=True)
            r += 1

    def _resolve_calc(self, chave: str, dre, proj) -> tuple:
        """Resolve campos calculados (_cresc, _mgb, etc.)."""
        if chave == "_cresc":
            return self._calc_growth(dre, proj)
        if chave == "_mgb":
            return self._calc_margin(dre, proj, "lucro_bruto", "receita_liquida")
        if chave == "_mge":
            return self._calc_margin(dre, proj, "ebitda", "receita_liquida")
        if chave == "_mgebit":
            return self._calc_margin(dre, proj, "ebit", "receita_liquida")
        if chave == "_mgl":
            return self._calc_margin(dre, proj, "lucro_liquido", "receita_liquida")
        if chave == "_ir_ebit":
            return self._calc_ir_ebit(dre, proj)
        return {}, {}

    def _calc_growth(self, dre, proj) -> tuple:
        """Crescimento YoY da receita."""
        hist, proj_r = {}, {}
        rec_h = self._get_hist(dre, "receita_liquida")
        rec_p = proj.get("receita_liquida", {})
        all_rec = {**rec_h, **rec_p}
        for ano in self.todos_anos:
            cur = all_rec.get(ano)
            prev = all_rec.get(ano - 1)
            if cur and prev and prev != 0:
                g = cur / prev - 1
                if ano in self.anos_hist:
                    hist[ano] = g
                else:
                    proj_r[ano] = g
        return hist, proj_r

    def _calc_ir_ebit(self, dre, proj) -> tuple:
        """IR sobre EBIT (para cálculo do NOPAT)."""
        hist, proj_r = {}, {}
        ebit_h = self._get_hist(dre, "ebit")
        ebit_p = proj.get("ebit", {})
        aliq = proj.get("aliquota_efetiva", 0.34)
        if isinstance(aliq, (int, float)):
            aliq_d = {a: aliq for a in self.todos_anos}
        else:
            aliq_d = aliq

        for ano in self.anos_hist:
            e = ebit_h.get(ano)
            if e:
                a = aliq_d.get(ano, 0.34)
                hist[ano] = -abs(e) * a

        for ano in self.anos_proj:
            e = ebit_p.get(ano)
            if e:
                a = aliq_d.get(ano, 0.34)
                proj_r[ano] = -abs(e) * a

        return hist, proj_r

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 8 — DRE CONTAS ABERTAS
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_dre_abertas(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("DRE Contas Abertas")
        dre  = dados.get("dre", pd.DataFrame())
        proj = dados.get("projecoes", {})

        self._write_title(ws, f"DRE Contas Abertas — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        r = 5
        self._write_section_header(ws, r, "ABERTURA DETALHADA DA DRE", col_mapa); r += 1

        # Todas as contas disponíveis no DataFrame
        contas_importantes = [
            "receita_bruta", "deducoes_receita", "receita_liquida",
            "custo_mercadorias", "lucro_bruto",
            "despesas_vendas", "despesas_gerais_adm",
            "outras_receitas_operacionais", "outras_despesas_operacionais",
            "resultado_equivalencia", "despesas_operacionais_total",
            "ebitda", "depreciacao_amortizacao", "ebit",
            "receitas_financeiras", "despesas_financeiras", "resultado_financeiro",
            "resultado_antes_ir", "ir_csll",
            "lucro_controladores", "lucro_minoritarios", "lucro_liquido",
        ]

        acc_keys = {"receita_liquida", "lucro_bruto", "ebitda", "ebit", "lucro_liquido"}

        for chave in contas_importantes:
            h = self._get_hist(dre, chave)
            p = self._proj_modelo(dados, chave)
            if not h and not p:
                continue
            label = chave.replace("_", " ").title()
            acc = chave in acc_keys
            self._write_row(ws, r, label, col_mapa, h, p, accent=acc)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 9 — BALANÇO PATRIMONIAL
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_balanco(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Balanço Patrimonial")
        bp   = dados.get("balanco", pd.DataFrame())
        proj = dados.get("projecoes", {})

        self._write_title(ws, f"Balanço Patrimonial — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        r = 5
        self._write_section_header(ws, r, "ATIVO", col_mapa); r += 1

        ativo = [
            ("Caixa e Equivalentes",         "caixa_equivalentes",        False, 0),
            ("Aplicações Financeiras CP",    "aplicacoes_financeiras_cp", False, 0),
            ("Contas a Receber",             "contas_receber",            False, 0),
            ("Estoques",                     "estoques",                  False, 0),
            ("Outros Ativos Circulantes",    "outros_ativos_circulantes", False, 0),
            ("Ativo Circulante",             "ativo_circulante",          True,  0),
            ("Realizável a Longo Prazo",     "realizavel_lp",             False, 0),
            ("Investimentos",                "investimentos",             False, 0),
            ("Imobilizado",                  "imobilizado",               False, 0),
            ("Intangível",                   "intangivel",                False, 0),
            ("Ativo Não Circulante",         "ativo_nao_circulante",      True,  0),
            ("ATIVO TOTAL",                  "ativo_total",               True,  0),
        ]

        for lbl, chave, acc, indent in ativo:
            h = self._hist_modelo(dados, chave)
            p = self._proj_modelo(dados, chave)
            if not h and not p and not acc:
                continue
            self._write_row(ws, r, lbl, col_mapa, h, p, accent=acc, indent=indent)
            r += 1

        r += 1
        self._write_section_header(ws, r, "PASSIVO + PATRIMÔNIO LÍQUIDO", col_mapa); r += 1

        passivo = [
            ("Fornecedores",                    "fornecedores",              False, 0),
            ("Empréstimos e Financiamentos CP", "emprestimos_cp",            False, 0),
            ("Outros Passivos Circulantes",     "outros_passivos_circulantes",False, 0),
            ("Passivo Circulante",              "passivo_circulante",        True,  0),
            ("Empréstimos e Financiamentos LP", "emprestimos_lp",            False, 0),
            ("Outros Passivos Não Circulantes", "outros_passivos_nao_circ",  False, 0),
            ("Passivo Não Circulante",          "passivo_nao_circulante",    True,  0),
            ("",                                None,                        False, 0),
            ("Dívida Bruta",                    "divida_bruta",              True,  0),
            ("Dívida Líquida",                  "divida_liquida",            True,  0),
            ("Capital de Giro (NCG)",           "capital_de_giro",           False, 0),
            ("Capital Investido",               "capital_investido",         False, 0),
            ("",                                None,                        False, 0),
            ("PATRIMÔNIO LÍQUIDO",              "patrimonio_liquido",        True,  0),
        ]

        for lbl, chave, acc, indent in passivo:
            if not lbl:
                r += 1; continue
            h = self._hist_modelo(dados, chave) if chave else {}
            p = self._proj_modelo(dados, chave) if chave else {}
            if not h and not p and not acc:
                continue
            self._write_row(ws, r, lbl, col_mapa, h, p, accent=acc, indent=indent)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 10 — PAINEL DE ÍNDICES
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_indicadores(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Painel de Índices")
        ind  = dados.get("indicadores", pd.DataFrame())
        proj = dados.get("projecoes", {})

        self._write_title(ws, f"Painel de Índices — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        r = 5

        blocos = [
            ("RENTABILIDADE", [
                ("ROE (%)",                  "roe",                  PCT_FMT1, False),
                ("ROA (%)",                  "roa",                  PCT_FMT1, False),
                ("ROIC (%)",                 "roic",                 PCT_FMT1, True),
                ("Giro do Ativo",            "giro_ativo",           MULT_FMT, False),
            ]),
            ("MARGENS", [
                ("Margem Bruta (%)",         "margem_bruta",         PCT_FMT1, False),
                ("Margem EBITDA (%)",        "margem_ebitda",        PCT_FMT1, True),
                ("Margem EBIT (%)",          "margem_ebit",          PCT_FMT1, False),
                ("Margem Líquida (%)",       "margem_liquida",       PCT_FMT1, False),
                ("SGA / Receita (%)",        "sga_receita",          PCT_FMT1, False),
                ("CAPEX / Receita (%)",      "capex_receita",        PCT_FMT1, False),
                ("NCG / Receita (%)",        "ncg_receita",          PCT_FMT1, False),
            ]),
            ("ALAVANCAGEM E COBERTURA", [
                ("Dívida Líquida / EBITDA",  "dl_ebitda",            MULT_FMT, True),
                ("Dívida Líquida / PL",      "dl_pl",                MULT_FMT, False),
                ("Dívida Bruta / PL",        "divida_bruta_pl",      MULT_FMT, False),
                ("Alavancagem (Ativo/PL)",   "alavancagem",          MULT_FMT, False),
                ("Cobertura Juros (EBITDA)", "cobertura_juros_ebitda", MULT_FMT, False),
                ("Cobertura Juros (EBIT)",   "cobertura_juros_ebit",  MULT_FMT, False),
            ]),
            ("MÚLTIPLOS DE MERCADO", [
                ("EV / EBITDA",              "ev_ebitda",            MULT_FMT, True),
                ("P / L",                    "p_l",                  MULT_FMT, False),
                ("P / VP",                   "p_vp",                 MULT_FMT, False),
            ]),
            ("VALORES ABSOLUTOS (R$ MM)", [
                ("Receita Líquida",          "receita_mm",           NUM_FMT,  False),
                ("EBITDA",                   "ebitda_mm",            NUM_FMT,  True),
                ("EBIT",                     "ebit_mm",              NUM_FMT,  False),
                ("Lucro Líquido",            "lucro_mm",             NUM_FMT,  False),
                ("NOPAT",                    "nopat_mm",             NUM_FMT,  False),
                ("Ativo Total",              "ativo_total_mm",       NUM_FMT,  False),
                ("Dívida Líquida",           "divida_liquida_mm",    NUM_FMT,  False),
                ("Patrimônio Líquido",       "pl_mm",                NUM_FMT,  False),
            ]),
        ]

        for section_name, items in blocos:
            self._write_section_header(ws, r, section_name, col_mapa); r += 1
            for lbl, chave, fmt, acc in items:
                h = self._get_ind(ind, chave)
                p = self._proj_modelo(dados, chave)
                if not h and not p:
                    continue
                self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc)
                r += 1
            r += 1  # espaço entre seções

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 11 — PROJEÇÕES PREMISSAS
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_premissas(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Projeções Premissas")
        proj = dados.get("projecoes", {})

        self._write_title(ws, f"Premissas de Projeção — {nome}", max_col=len(self.anos_proj)+1)

        # Só anos de projeção
        ws.column_dimensions["A"].width = 44
        col_mapa = {}
        cell_l = ws.cell(row=3, column=1, value="Premissa")
        cell_l.font = _f(bold=True); cell_l.fill = FILL_SUBHDR; cell_l.border = _border()
        for i, ano in enumerate(self.anos_proj):
            col = 2 + i
            c = ws.cell(row=3, column=col, value=ano)
            c.font = _hf(9); c.fill = FILL_HDR; c.border = _border()
            c.alignment = Alignment(horizontal="center")
            ws.column_dimensions[get_column_letter(col)].width = 14.5
            col_mapa[ano] = col

        r = 5
        self._write_section_header(ws, r, "RECEITA E CRESCIMENTO", col_mapa); r += 1

        premissas = [
            ("Crescimento da Receita (%)",      "crescimento_receita",      PCT_FMT1),
            ("Receita Líquida Projetada",       "receita_liquida",          NUM_FMT),
        ]
        for lbl, chave, fmt in premissas:
            p = proj.get(chave, {})
            proj_filtered = {a: p[a] for a in self.anos_proj if a in p}
            self._write_row(ws, r, lbl, col_mapa, {}, proj_filtered, fmt=fmt)
            r += 1

        r += 1
        self._write_section_header(ws, r, "MARGENS E CUSTOS", col_mapa); r += 1

        margens = [
            ("Margem EBITDA (%)",               "margem_ebitda_proj",        PCT_FMT1),
            ("EBITDA Projetado",                "ebitda",                    NUM_FMT),
            ("D&A / Receita (%)",               "da_pct_receita",           PCT_FMT1),
            ("Margem EBIT (%)",                 "margem_ebit_proj",          PCT_FMT1),
            ("EBIT Projetado",                  "ebit",                      NUM_FMT),
        ]
        for lbl, chave, fmt in margens:
            p = proj.get(chave, {})
            proj_filtered = {a: p[a] for a in self.anos_proj if a in p}
            if not proj_filtered:
                continue
            self._write_row(ws, r, lbl, col_mapa, {}, proj_filtered, fmt=fmt)
            r += 1

        r += 1
        self._write_section_header(ws, r, "RESULTADO FINANCEIRO E IR", col_mapa); r += 1

        rf_items = [
            ("Resultado Financeiro",            "resultado_financeiro",      NUM_FMT),
            ("Alíquota Efetiva IR (%)",         "aliquota_efetiva_proj",     PCT_FMT1),
            ("IR e CSLL",                       "ir_csll",                   NUM_FMT),
            ("Lucro Líquido",                   "lucro_liquido",             NUM_FMT),
        ]
        for lbl, chave, fmt in rf_items:
            p = proj.get(chave, {})
            proj_filtered = {a: p[a] for a in self.anos_proj if a in p}
            if not proj_filtered:
                continue
            self._write_row(ws, r, lbl, col_mapa, {}, proj_filtered, fmt=fmt)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ABA 12 — PROJEÇÕES CAPEX E CG
    # ═══════════════════════════════════════════════════════════════════════

    def _aba_capex_cg(self, wb, nome: str, dados: dict):
        ws = wb.create_sheet("Projeções Capex e CG")
        proj = dados.get("projecoes", {})
        dre  = dados.get("dre", pd.DataFrame())
        bp   = dados.get("balanco", pd.DataFrame())

        self._write_title(ws, f"CAPEX e Capital de Giro — {nome}", max_col=len(self.todos_anos)+1)
        col_mapa = self._write_header_anos(ws, row=3)

        r = 5
        self._write_section_header(ws, r, "CAPEX", col_mapa); r += 1

        capex_items = [
            ("CAPEX Total",                     "capex",                NUM_FMT,  True),
            ("CAPEX / Receita (%)",             "capex_pct_receita",     PCT_FMT1, False),
            ("Depreciação e Amortização",       "depreciacao_amortizacao", NUM_FMT, False),
            ("D&A / Receita (%)",               "da_pct_receita",        PCT_FMT1, False),
            ("CAPEX Líquido (CAPEX - D&A)",     "capex_liquido",         NUM_FMT,  False),
        ]
        for lbl, chave, fmt, acc in capex_items:
            h = self._hist_modelo(dados, chave)
            p = self._proj_modelo(dados, chave)
            if not h and not p:
                continue
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc)
            r += 1

        r += 1
        self._write_section_header(ws, r, "CAPITAL DE GIRO (NCG)", col_mapa); r += 1

        ncg_items = [
            ("Contas a Receber",                "contas_receber",        NUM_FMT,  False),
            ("Estoques",                        "estoques",              NUM_FMT,  False),
            ("(-) Fornecedores",                "fornecedores",          NUM_FMT,  False),
            ("NCG (Necessidade de Capital)",     "capital_de_giro",       NUM_FMT,  True),
            ("NCG / Receita (%)",               "ncg_pct_receita",       PCT_FMT1, False),
            ("Δ NCG (variação)",                "delta_ncg",             NUM_FMT,  True),
        ]
        for lbl, chave, fmt, acc in ncg_items:
            h = self._hist_modelo(dados, chave)
            p = self._proj_modelo(dados, chave)
            if not h and not p:
                continue
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc)
            r += 1

        r += 1
        self._write_section_header(ws, r, "FCFF — MONTAGEM", col_mapa); r += 1

        fcff_items = [
            ("NOPAT",                           "nopat",                 NUM_FMT,  False),
            ("(+) D&A",                         "depreciacao_amortizacao", NUM_FMT, False),
            ("(-) CAPEX",                       "capex",                 NUM_FMT,  False),
            ("(-) Δ NCG",                       "delta_ncg",             NUM_FMT,  False),
            ("FCFF",                            "fcff",                  NUM_FMT,  True),
        ]
        for lbl, chave, fmt, acc in fcff_items:
            h = self._hist_modelo(dados, chave)
            p = self._proj_modelo(dados, chave)
            self._write_row(ws, r, lbl, col_mapa, h, p, fmt=fmt, accent=acc)
            r += 1

    # ═══════════════════════════════════════════════════════════════════════
    # ORQUESTRADOR PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════

    def escrever(self, dados_completos: dict,
                  nome_empresa: str = "Empresa",
                  destino: Path = None) -> Path:
        """
        Gera planilha completa de valuation.
        """
        if destino is None:
            destino = Path("outputs") / f"Valuation_{self.ticker}_{nome_empresa}.xlsx"

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n{'='*60}")

        if self.template and self.template.exists():
            # Verificar se o template cobre todos os anos históricos
            try:
                wb_check = load_workbook(self.template, read_only=True, data_only=True)
                col_mapa_check: dict = {}
                for aba_nome in ["DRE", "DRE + DCF", "Income Statement"]:
                    for sname in wb_check.sheetnames:
                        if aba_nome.lower() in sname.lower():
                            col_mapa_check = self._mapear_colunas_template(
                                wb_check[sname], padronizar=False
                            )
                            break
                    if col_mapa_check:
                        break
                wb_check.close()
            except Exception:
                col_mapa_check = {}

            anos_faltando = [a for a in self.anos_hist if a not in col_mapa_check]
            if anos_faltando:
                logger.warning(
                    f"Template '{self.template.name}' não possui colunas para {anos_faltando} "
                    f"— gerando Excel completo (13 abas) em substituição."
                )
            else:
                logger.info(f"Escrevendo com template explicito: {self.template.name}")
                return self._escrever_com_template(dados_completos, nome_empresa, destino)

        logger.info(f"Criando Excel completo (13 abas) para: {nome_empresa} ({self.ticker})")
        return self._criar_workbook_completo(nome_empresa, dados_completos, destino)

    def _criar_workbook_completo(self, nome: str, dados: dict, destino: Path) -> Path:
        """Cria workbook completo com layout interno (13 abas)."""
        wb = Workbook()
        wb.remove(wb.active)

        logger.info("  → 1/13  Dashboard")
        self._aba_dashboard(wb, nome, dados)

        logger.info("  → 2/13  Metodologia")
        self._aba_metodologia(wb, nome, dados)

        logger.info("  → 3/13  WACC")
        self._aba_wacc(wb, nome, dados)

        logger.info("  → 4/13  TIR ON")
        self._aba_tir(wb, nome, dados, "ON")

        logger.info("  → 5/13  TIR PN")
        self._aba_tir(wb, nome, dados, "PN")

        logger.info("  → 6/13  Valor do Equity")
        self._aba_equity(wb, nome, dados)

        logger.info("  → 7/13  Preço Teto")
        self._aba_preco_teto(wb, nome, dados)

        logger.info("  → 8/13  DRE + DCF")
        self._aba_dre_dcf(wb, nome, dados)

        logger.info("  → 9/13  DRE Contas Abertas")
        self._aba_dre_abertas(wb, nome, dados)

        logger.info("  → 10/13 Balanço Patrimonial")
        self._aba_balanco(wb, nome, dados)

        logger.info("  → 11/13 Painel de Índices")
        self._aba_indicadores(wb, nome, dados)

        logger.info("  → 12/13 Projeções Premissas")
        self._aba_premissas(wb, nome, dados)

        logger.info("  → 13/13 Projeções Capex e CG")
        self._aba_capex_cg(wb, nome, dados)

        logger.info("  → Drivers Setoriais")
        adicionar_aba_drivers_setoriais(wb, dados, nome, self.ticker)

        logger.info("  → Status & Fontes")
        adicionar_aba_auditoria(wb, dados, nome, self.ticker)

        try:
            wb.save(destino)
        except PermissionError as exc:
            raise PermissionError(
                f"Arquivo Excel bloqueado: {destino}. "
                "Feche a planilha no Excel/OneDrive e rode novamente."
            ) from exc
        logger.info(f"\nArquivo salvo: {destino}")
        return destino

    # ═══════════════════════════════════════════════════════════════════════
    # MODO TEMPLATE EXPLÍCITO
    # ═══════════════════════════════════════════════════════════════════════

    def _escrever_com_template(self, dados: dict, nome: str, destino: Path) -> Path:
        """Copia template informado explicitamente e preenche por label matching."""
        destino = Path(destino)
        try:
            mesmo_arquivo = self.template.resolve() == destino.resolve()
        except OSError:
            mesmo_arquivo = False
        if not mesmo_arquivo:
            shutil.copy2(self.template, destino)
        try:
            wb = load_workbook(destino)
        except PermissionError as exc:
            raise PermissionError(
                f"Arquivo Excel bloqueado: {destino}. "
                "Feche a planilha no Excel/OneDrive e rode novamente."
            ) from exc

        dre  = dados.get("dre", pd.DataFrame())
        proj = dados.get("projecoes", {})

        MAPA = {
            "Receita Líquida": "receita_liquida",
            "Receita de Venda de Bens e/ou Serviços": "receita_liquida",
            "Custo dos Bens e/ou Serviços Vendidos": "custo_mercadorias",
            "RESULTADO BRUTO": "lucro_bruto", "Lucro Bruto": "lucro_bruto",
            "EBITDA": "ebitda", "EBIT": "ebit",
            "Resultado Financeiro": "resultado_financeiro",
            "Resultado Antes dos Tributos": "resultado_antes_ir",
            "Imposto de Renda e CSLL": "ir_csll",
            "LUCRO LÍQUIDO": "lucro_liquido", "Lucro Líquido": "lucro_liquido",
        }

        for aba in ["DRE", "DRE + DCF", "Income Statement"]:
            ws = None
            for name in wb.sheetnames:
                if aba.lower() in name.lower():
                    ws = wb[name]; break
            if ws:
                col_mapa = self._mapear_colunas_template(ws)
                labels = self._mapear_linhas_template(ws)
                for label, chave in MAPA.items():
                    row = self._match_label_template(labels, label)
                    if not row or chave not in dre.index:
                        continue
                    h = {a: float(dre.loc[chave, a]) for a in self.anos_hist if a in dre.columns}
                    p = proj.get(chave, {})
                    for ano, val in {**h, **p}.items():
                        col = col_mapa.get(ano)
                        if col:
                            eh = ano in self.anos_hist
                            c = ws.cell(row=row, column=col, value=round(val, 3))
                            c.font = _f(C_BLUE if eh else C_GREEN)
                            c.number_format = NUM_FMT
                break

        adicionar_aba_auditoria(wb, dados, nome, self.ticker)

        try:
            wb.save(destino)
        except PermissionError as exc:
            raise PermissionError(
                f"Arquivo Excel bloqueado: {destino}. "
                "Feche a planilha no Excel/OneDrive e rode novamente."
            ) from exc
        logger.info(f"\nArquivo salvo: {destino}")
        return destino

    def _mapear_colunas_template(self, ws, padronizar: bool = True) -> dict:
        if padronizar:
            self._padronizar_colunas_template(ws)
        mapa = {}
        for hr in [4, 3, 5]:
            for col in range(1, ws.max_column + 1):
                v = ws.cell(row=hr, column=col).value
                if v is None: continue
                try:
                    ano = int(str(v).strip())
                    if 2015 <= ano <= 2040 and ano not in mapa:
                        mapa[ano] = col
                except (ValueError, TypeError):
                    pass
        return mapa

    def _mapear_linhas_template(self, ws, col=4) -> dict:
        mapa = {}
        for row in range(1, ws.max_row + 1):
            v = ws.cell(row=row, column=col).value
            if v and isinstance(v, str):
                mapa[v.strip()] = row
                mapa[v.strip().lower()] = row
        return mapa

    def _match_label_template(self, labels: dict, label: str) -> Optional[int]:
        if label in labels: return labels[label]
        lw = label.strip().lower()
        if lw in labels: return labels[lw]
        for k, v in labels.items():
            if isinstance(k, str) and lw in k.lower(): return v
        return None
