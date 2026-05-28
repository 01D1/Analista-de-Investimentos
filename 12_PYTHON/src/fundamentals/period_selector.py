"""
period_selector.py
------------------
Seleciona o melhor período de referência para uso em valuation e ranking.

Hierarquia de prioridade (decrescente):
  1. DFP anual mais recente
  2. LTM calculado (12 meses móveis a partir de ITRs)
  3. ITR mais recente disponível (marcado como PARTIAL)
  4. Nenhum dado disponível

Campos adicionados ao período escolhido:
  period_basis : Literal["DFP", "LTM", "ITR_PARTIAL"]
  data_quality_note : str — razão da escolha e eventuais alertas

Regras:
  - Nunca usar Q1 de forma isolada como substituto de dado anual.
  - DFP deve ter reference_date == YYYY-12-31 para ser considerado anual padrão
    (exceção: empresas com fiscal year diferente, ex: RAIZ4 encerra em março).
  - ITR Q3 (setembro) é preferido sobre Q1/Q2 por cobrir 9 meses.
  - LTM = ITR(T) - ITR(T-4) + DFP(T-1), se disponível.

Uso:
    from src.fundamentals.period_selector import select_best_period, PeriodSelection

    rows = get_financial_inputs("PETR4")  # lista de dicts da VFI
    sel = select_best_period(rows)
    print(sel.period_basis, sel.period_end, sel.fiscal_year)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PeriodBasis = Literal["DFP", "LTM", "ITR_PARTIAL"]

# Meses que encerram cada trimestre CVM
_QUARTER_MONTH = {3: 1, 6: 2, 9: 3, 12: 4}


@dataclass
class PeriodSelection:
    """Resultado da seleção de período."""

    period_basis: PeriodBasis
    period_end: str                    # YYYY-MM-DD
    fiscal_year: int
    fiscal_quarter: int | None         # None para DFP anual; 1–4 para ITR

    # Dados do LTM quando period_basis == "LTM"
    ltm_quarters: list[str] = field(default_factory=list)  # reference_dates usadas

    data_quality_note: str = ""
    warnings: list[str] = field(default_factory=list)


def _quarter_from_date(date_str: str) -> int | None:
    """'2024-09-30' → 3 (trimestre). '2024-12-31' → None (anual)."""
    try:
        month = int(date_str[5:7])
        return _QUARTER_MONTH.get(month)
    except (ValueError, IndexError):
        return None


def _fiscal_year(date_str: str) -> int:
    return int(date_str[:4])


def _group_periods(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """
    Agrupa linhas de valuation_financial_inputs por período.

    Returns:
        dfp_periods: {period_end → linhas} para period_type='DFP'
        itr_periods: {period_end → linhas} para period_type='ITR'
    """
    dfp: dict[str, list[dict]] = {}
    itr: dict[str, list[dict]] = {}

    for row in rows:
        ptype = str(row.get("period_type", "")).upper()
        pend = row.get("period_end", "")
        if not pend:
            continue
        if ptype == "DFP":
            dfp.setdefault(pend, []).append(row)
        elif ptype == "ITR":
            itr.setdefault(pend, []).append(row)

    return dfp, itr


def _has_key_metrics(rows: list[dict], min_count: int = 3) -> bool:
    """Verifica se o período tem ao menos as métricas essenciais."""
    key = {"revenue", "net_income", "equity_book_value", "total_assets", "operating_cash_flow"}
    found = {r["metric_name"] for r in rows}
    return len(key & found) >= min_count


def _build_ltm(
    itr_periods: dict[str, list[dict]],
    dfp_periods: dict[str, list[dict]],
) -> PeriodSelection | None:
    """
    Tenta calcular LTM = ITR(último Q3 ou Q2) - ITR(mesmo Q do ano anterior) + DFP(ano anterior).

    Retorna PeriodSelection com period_basis='LTM' ou None se não for possível.

    Fórmula usada (LTM clássico):
        LTM = DFP(N-1) + [ITR_YTD(N) - ITR_YTD(N-1)]
    Onde ITR_YTD é o mais recente disponível (Q3 > Q2 > Q1).
    """
    if not itr_periods or not dfp_periods:
        return None

    # Ordenar ITRs por data DESC para pegar o mais recente
    sorted_itr = sorted(itr_periods.keys(), reverse=True)
    # Ordenar DFPs por data DESC para pegar o mais recente
    sorted_dfp = sorted(dfp_periods.keys(), reverse=True)

    for latest_itr in sorted_itr:
        q = _quarter_from_date(latest_itr)
        if q is None:
            continue
        # Só aceita Q2 ou Q3 para LTM confiável (Q1 = 3 meses, muito fragmentado)
        if q not in (2, 3):
            continue

        curr_year = _fiscal_year(latest_itr)
        # Procurar ITR do mesmo trimestre do ano anterior
        month = int(latest_itr[5:7])
        prev_itr_target = f"{curr_year - 1}-{latest_itr[5:7]}-{latest_itr[8:10]}"

        prior_itr_rows = itr_periods.get(prev_itr_target)
        # Procurar DFP do ano anterior
        prior_dfp_target = f"{curr_year - 1}-12-31"
        prior_dfp_rows = dfp_periods.get(prior_dfp_target)

        if prior_itr_rows is None or prior_dfp_rows is None:
            continue

        if not (_has_key_metrics(itr_periods[latest_itr]) and
                _has_key_metrics(prior_itr_rows) and
                _has_key_metrics(prior_dfp_rows)):
            continue

        # LTM disponível
        note = (
            f"LTM calculado: DFP {curr_year - 1} + ITR YTD {latest_itr} "
            f"- ITR YTD {prev_itr_target}"
        )
        return PeriodSelection(
            period_basis="LTM",
            period_end=latest_itr,
            fiscal_year=curr_year,
            fiscal_quarter=q,
            ltm_quarters=[prior_dfp_target, prev_itr_target, latest_itr],
            data_quality_note=note,
        )

    return None


def select_best_period(
    rows: list[dict[str, Any]],
    prefer_annual: bool = True,
    allow_ltm: bool = True,
) -> PeriodSelection | None:
    """
    Seleciona o melhor período de referência para um ticker.

    Args:
        rows: Lista de dicts da tabela valuation_financial_inputs para um ticker.
        prefer_annual: Se True, DFP anual é sempre preferido sobre ITR e LTM.
        allow_ltm: Se True, tenta calcular LTM quando DFP não disponível.

    Returns:
        PeriodSelection com period_basis, period_end, fiscal_year e notas.
        None se não houver dados.
    """
    if not rows:
        return None

    dfp_periods, itr_periods = _group_periods(rows)

    # ── 1. Preferir DFP anual mais recente ──────────────────────────────────────
    if prefer_annual and dfp_periods:
        # Ordenar DFPs por data DESC
        sorted_dfp = sorted(dfp_periods.keys(), reverse=True)
        for pend in sorted_dfp:
            period_rows = dfp_periods[pend]
            if _has_key_metrics(period_rows, min_count=3):
                fy = _fiscal_year(pend)
                month = int(pend[5:7])
                is_standard = (month == 12)  # dezembro = fiscal year padrão
                note = f"DFP anual {fy} {'(encerramento dez)' if is_standard else f'(encerramento {pend[5:7]})'}"
                return PeriodSelection(
                    period_basis="DFP",
                    period_end=pend,
                    fiscal_year=fy,
                    fiscal_quarter=4,
                    data_quality_note=note,
                )
        # Tem DFPs mas sem métricas suficientes
        warnings_dfp = [f"DFP {p} com dados insuficientes" for p in sorted_dfp[:2]]

    # ── 2. Tentar LTM (12 meses móveis) ────────────────────────────────────────
    if allow_ltm:
        ltm = _build_ltm(itr_periods, dfp_periods)
        if ltm is not None:
            return ltm

    # ── 3. Fallback: ITR mais recente ────────────────────────────────────────────
    if itr_periods:
        sorted_itr = sorted(itr_periods.keys(), reverse=True)
        for pend in sorted_itr:
            period_rows = itr_periods[pend]
            if _has_key_metrics(period_rows, min_count=2):
                q = _quarter_from_date(pend)
                fy = _fiscal_year(pend)
                note = (
                    f"ITR parcial Q{q} {fy} (sem DFP anual disponível) — "
                    "dados parciais, não anualizados"
                )
                return PeriodSelection(
                    period_basis="ITR_PARTIAL",
                    period_end=pend,
                    fiscal_year=fy,
                    fiscal_quarter=q,
                    data_quality_note=note,
                    warnings=[
                        "Período parcial: métricas de fluxo (receita, lucro) "
                        "representam apenas parte do ano fiscal"
                    ],
                )

    return None


def select_best_period_for_history(
    rows: list[dict[str, Any]],
) -> list[PeriodSelection]:
    """
    Retorna a melhor seleção POR ANO FISCAL para construção de série histórica.

    Para cada fiscal_year distinto, retorna:
      - DFP anual se existir
      - Caso contrário, ITR mais recente daquele ano

    Args:
        rows: Todos os registros VFI de um ticker.

    Returns:
        Lista de PeriodSelection ordenada por fiscal_year ASC.
    """
    dfp_periods, itr_periods = _group_periods(rows)

    # Coletar todos os anos presentes
    all_years: set[int] = set()
    for pend in dfp_periods:
        all_years.add(_fiscal_year(pend))
    for pend in itr_periods:
        all_years.add(_fiscal_year(pend))

    selections: list[PeriodSelection] = []
    for fy in sorted(all_years):
        # Procurar DFP deste ano
        dfp_match = sorted(
            [p for p in dfp_periods if _fiscal_year(p) == fy],
            reverse=True,
        )
        if dfp_match:
            pend = dfp_match[0]
            if _has_key_metrics(dfp_periods[pend], min_count=2):
                selections.append(PeriodSelection(
                    period_basis="DFP",
                    period_end=pend,
                    fiscal_year=fy,
                    fiscal_quarter=4,
                    data_quality_note=f"DFP anual {fy}",
                ))
                continue

        # Fallback: ITR mais recente do ano
        itr_match = sorted(
            [p for p in itr_periods if _fiscal_year(p) == fy],
            reverse=True,
        )
        for pend in itr_match:
            if _has_key_metrics(itr_periods[pend], min_count=2):
                q = _quarter_from_date(pend)
                selections.append(PeriodSelection(
                    period_basis="ITR_PARTIAL",
                    period_end=pend,
                    fiscal_year=fy,
                    fiscal_quarter=q,
                    data_quality_note=f"ITR parcial Q{q} {fy} (sem DFP)",
                    warnings=["Parcial"],
                ))
                break

    return selections
