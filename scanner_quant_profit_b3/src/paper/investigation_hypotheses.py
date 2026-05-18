"""Hipoteses analiticas para investigar fragilidade no paper trading.

As hipoteses aqui nao alteram ranking, score ou regras operacionais. Elas
apenas descrevem experimentos simulados para comparar antes/depois.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


HYPOTHESIS_COLUMNS = [
    "hypothesis_id",
    "hypothesis_type",
    "title",
    "description",
    "target",
    "source_fragility",
    "proposed_adjustment",
    "expected_effect",
    "risk_of_overfitting",
    "can_simulate",
    "metadata_json",
]


@dataclass
class InvestigationHypothesis:
    hypothesis_id: str
    hypothesis_type: str
    title: str
    description: str
    target: str
    source_fragility: str
    proposed_adjustment: str
    expected_effect: str
    risk_of_overfitting: str
    can_simulate: bool = True
    metadata_json: str = "{}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _col(df: pd.DataFrame, name: str, default="") -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def _append(rows: list[dict], hyp: InvestigationHypothesis) -> None:
    if hyp.hypothesis_id not in {row["hypothesis_id"] for row in rows}:
        rows.append(hyp.to_dict())


def _asset_hypotheses(rows: list[dict], fragility_by_asset_df: pd.DataFrame) -> None:
    if fragility_by_asset_df is None or fragility_by_asset_df.empty:
        return
    for _, row in fragility_by_asset_df.iterrows():
        ticker = str(row.get("ticker", "")).upper()
        if not ticker:
            continue
        fragility_class = str(row.get("fragility_class", "")).upper()
        fragility_score = _num(row.get("fragility_score"))
        net_pnl = _num(row.get("net_pnl"))
        cost_drag = _num(row.get("cost_drag", row.get("total_cost_drag")))
        drawdown_contribution = abs(_num(row.get("drawdown_contribution")))
        metadata = {
            "ticker": ticker,
            "fragility_score": fragility_score,
            "fragility_class": fragility_class,
            "net_pnl": net_pnl,
            "cost_drag": cost_drag,
            "drawdown_contribution": drawdown_contribution,
        }
        if fragility_class in {"CRITICO", "FRAGIL"} or fragility_score >= 70 or net_pnl < 0:
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id=f"EXCLUDE_ASSET_{ticker}",
                    hypothesis_type="EXCLUDE_ASSET",
                    title=f"Investigar exclusao simulada de {ticker}",
                    description=f"{ticker} apresentou fragilidade detectada na carteira simulada.",
                    target=ticker,
                    source_fragility=fragility_class or "FRAGILIDADE_DETECTADA",
                    proposed_adjustment=f"Remover sinais de {ticker} apenas no experimento simulado.",
                    expected_effect="Testar se a retirada do ativo reduz fragilidade, drawdown ou custo sem destruir a amostra.",
                    risk_of_overfitting="MEDIO",
                    metadata_json=_json(metadata),
                ),
            )
        if cost_drag > 0 and (cost_drag > max(abs(net_pnl), 1.0) * 0.25 or fragility_class == "CRITICO"):
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id=f"LIMIT_ASSET_COST_{ticker}",
                    hypothesis_type="LIMIT_ASSET_COST",
                    title=f"Investigar limite de custo simulado em {ticker}",
                    description=f"{ticker} apresentou arrasto de custo relevante no paper trading.",
                    target=ticker,
                    source_fragility="COST_DRAG",
                    proposed_adjustment="Bloquear novas entradas simuladas quando o custo historico do ativo estiver acima do limite em estudo.",
                    expected_effect="Avaliar sensibilidade a custo/slippage sem alterar score ou ranking.",
                    risk_of_overfitting="ALTO",
                    metadata_json=_json(metadata | {"cost_limit_hint": 0.25}),
                ),
            )
        if drawdown_contribution >= 0.05:
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id=f"BLOCK_DRAWDOWN_CONTRIBUTOR_{ticker}",
                    hypothesis_type="BLOCK_DRAWDOWN_CONTRIBUTOR",
                    title=f"Investigar bloqueio simulado de contribuidor de drawdown: {ticker}",
                    description=f"{ticker} concentrou parte relevante do drawdown simulado.",
                    target=ticker,
                    source_fragility="DRAWDOWN_CONTRIBUTION",
                    proposed_adjustment=f"Remover sinais de {ticker} em experimento de drawdown attribution.",
                    expected_effect="Testar se o drawdown melhora sem perda material de retorno ou amostra.",
                    risk_of_overfitting="ALTO",
                    metadata_json=_json(metadata),
                ),
            )


def _signal_source_hypotheses(rows: list[dict], fragility_by_signal_source_df: pd.DataFrame) -> None:
    if fragility_by_signal_source_df is None or fragility_by_signal_source_df.empty:
        return
    for _, row in fragility_by_signal_source_df.iterrows():
        source = str(row.get("signal_source", "")).lower()
        if not source:
            continue
        fragility_class = str(row.get("fragility_class", "")).upper()
        trades = int(_num(row.get("trades_count", row.get("trades"))))
        net_pnl = _num(row.get("net_pnl"))
        cost_drag = _num(row.get("cost_drag"))
        fragility_score = _num(row.get("fragility_score"))
        metadata = {
            "signal_source": source,
            "trades_count": trades,
            "net_pnl": net_pnl,
            "cost_drag": cost_drag,
            "fragility_class": fragility_class,
            "fragility_score": fragility_score,
        }
        if source == "rebalance" and cost_drag > 0:
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id="DISABLE_REBALANCING",
                    hypothesis_type="DISABLE_REBALANCING",
                    title="Investigar carteira simulada sem rebalanceamento",
                    description="O rebalanceamento simulado gerou custo sem P&L direto atribuido.",
                    target="rebalance",
                    source_fragility="COST_DRAG",
                    proposed_adjustment="Desativar rebalanceamento apenas no experimento simulado.",
                    expected_effect="Medir se o custo cai sem piorar drawdown ou retorno.",
                    risk_of_overfitting="MEDIO",
                    metadata_json=_json(metadata),
                ),
            )
        if fragility_class in {"FRAGIL", "CRITICO", "DADOS_INSUFICIENTES"} or trades < 10 or fragility_score >= 60:
            hyp_type = "LIMIT_SIGNAL_SOURCE" if net_pnl >= 0 and trades >= 10 else "EXCLUDE_SIGNAL_SOURCE"
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id=f"{hyp_type}_{source.upper()}",
                    hypothesis_type=hyp_type,
                    title=f"Investigar fonte de sinal em observacao: {source}",
                    description=f"A fonte {source} apresentou fragilidade ou amostra insuficiente no paper trading.",
                    target=source,
                    source_fragility=fragility_class or "SINAL_EM_OBSERVACAO",
                    proposed_adjustment="Reduzir ou remover a fonte apenas no experimento simulado.",
                    expected_effect="Separar contribuicao real de possivel fragilidade por fonte de sinal.",
                    risk_of_overfitting="ALTO" if trades < 10 else "MEDIO",
                    metadata_json=_json(metadata),
                ),
            )


def _portfolio_level_hypotheses(rows: list[dict], fragility_by_asset_df: pd.DataFrame, drawdown_df: pd.DataFrame | None) -> None:
    if fragility_by_asset_df is not None and not fragility_by_asset_df.empty:
        fragile_assets = fragility_by_asset_df[
            (_col(fragility_by_asset_df, "fragility_class").astype(str).str.upper().isin(["CRITICO", "FRAGIL"]))
            | (pd.to_numeric(_col(fragility_by_asset_df, "fragility_score", 0), errors="coerce").fillna(0) >= 70)
        ]
        tickers = sorted(fragile_assets.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper().unique().tolist())
        if len(tickers) >= 2:
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id="EXCLUDE_HIGH_FRAGILITY",
                    hypothesis_type="EXCLUDE_HIGH_FRAGILITY",
                    title="Investigar limite por fragility_score",
                    description="Mais de um ativo apresentou fragilidade elevada na carteira simulada.",
                    target="portfolio",
                    source_fragility="HIGH_FRAGILITY_ASSETS",
                    proposed_adjustment="Remover ativos acima do limite de fragility_score apenas em simulação.",
                    expected_effect="Avaliar reducao agregada de fragilidade e custo.",
                    risk_of_overfitting="ALTO",
                    metadata_json=_json({"tickers": tickers, "fragility_threshold": 70}),
                ),
            )
    if drawdown_df is not None and not drawdown_df.empty:
        worst = drawdown_df.copy()
        worst["depth_num"] = pd.to_numeric(worst.get("depth"), errors="coerce")
        worst = worst.sort_values("depth_num").head(1)
        if not worst.empty and abs(_num(worst.iloc[0].get("depth"))) >= 0.08:
            _append(
                rows,
                InvestigationHypothesis(
                    hypothesis_id="REDUCE_VOLATILITY_EXPOSURE",
                    hypothesis_type="REDUCE_VOLATILITY_EXPOSURE",
                    title="Investigar reducao simulada de exposicao em drawdown",
                    description="O pior drawdown simulado foi profundo ou nao recuperado no recorte.",
                    target="portfolio",
                    source_fragility="DRAWDOWN",
                    proposed_adjustment="Reduzir risco_pct/max_positions no experimento simulado.",
                    expected_effect="Testar se menor exposicao reduz drawdown sem eliminar retorno.",
                    risk_of_overfitting="MEDIO",
                    metadata_json=_json(worst.iloc[0].drop(labels=["depth_num"], errors="ignore").to_dict()),
                ),
            )


def generate_hypotheses_from_fragility(
    fragility_by_asset_df: pd.DataFrame,
    fragility_by_signal_source_df: pd.DataFrame,
    drawdown_df: pd.DataFrame | None = None,
    cost_fragility_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Gera hipoteses de investigacao a partir do diagnostico de fragilidade."""
    rows: list[dict] = []
    _asset_hypotheses(rows, fragility_by_asset_df)
    _signal_source_hypotheses(rows, fragility_by_signal_source_df)
    _portfolio_level_hypotheses(rows, fragility_by_asset_df, drawdown_df)
    if cost_fragility_df is not None and not cost_fragility_df.empty:
        for _, row in cost_fragility_df.iterrows():
            ticker = str(row.get("ticker", "")).upper()
            cost_class = str(row.get("cost_fragility_class", row.get("fragility_class", ""))).upper()
            if ticker and cost_class in {"COST_FRAGILE", "COST_DOMINATED"}:
                _append(
                    rows,
                    InvestigationHypothesis(
                        hypothesis_id=f"LIMIT_ASSET_COST_{ticker}",
                        hypothesis_type="LIMIT_ASSET_COST",
                        title=f"Investigar limite de custo simulado em {ticker}",
                        description=f"{ticker} apresentou sensibilidade a custo/slippage.",
                        target=ticker,
                        source_fragility=cost_class,
                        proposed_adjustment="Remover sinais do ativo apenas em um experimento de custo.",
                        expected_effect="Medir se a sensibilidade a custo explica a perda de robustez.",
                        risk_of_overfitting="ALTO",
                        metadata_json=_json(row.to_dict()),
                    ),
                )
    return pd.DataFrame(rows, columns=HYPOTHESIS_COLUMNS)
