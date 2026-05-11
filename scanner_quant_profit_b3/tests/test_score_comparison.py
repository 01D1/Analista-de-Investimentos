"""Testes para comparação, auditoria e calibração de scores."""
import pandas as pd

from src.quant.score_comparison import (
    compare_scores,
    detect_score_inflation,
    score_distribution,
    score_distribution_report,
    textual_comparison_report,
)


def _row(asset, legacy, new, legacy_signal="NEUTRO", new_signal="NEUTRO"):
    return {
        "asset": asset,
        "score": legacy,
        "score_final": new,
        "signal": legacy_signal,
        "signal_type": new_signal,
        "score_momentum": new,
        "score_tendencia": new,
        "score_liquidez": new,
        "score_volatilidade": new,
        "score_risco": new,
        "signal_confidence": "MEDIA",
        "explanation": f"{asset} aparece no radar.",
    }


def test_classifies_convergent_high_scores():
    df = pd.DataFrame([_row("PETR4", 90, 88, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ")])

    out = compare_scores(df)

    assert out.loc[0, "divergence_type"] == "CONVERGENTE_FORTE"
    assert out.loc[0, "score_diff_abs"] == 2
    assert out.loc[0, "score_diff_pct"] == -2.2222


def test_classifies_convergent_low_scores():
    df = pd.DataFrame([_row("ITUB4", 35, 32, "NEUTRO", "SEM ASSIMETRIA")])

    out = compare_scores(df)

    assert out.loc[0, "divergence_type"] == "CONVERGENTE_FRACO"


def test_classifies_new_score_more_strict():
    df = pd.DataFrame([_row("VALE3", 92, 58, "COMPRA/FORÇA", "OBSERVAR")])

    out = compare_scores(df)

    assert out.loc[0, "divergence_type"] == "NOVO_SCORE_MAIS_RIGOROSO"


def test_classifies_new_score_more_aggressive():
    df = pd.DataFrame([_row("BBAS3", 55, 86, "OBSERVAR", "ROMPIMENTO COM VOLUME")])

    out = compare_scores(df)

    assert out.loc[0, "divergence_type"] == "NOVO_SCORE_MAIS_AGRESSIVO"


def test_classifies_signal_or_rank_divergence():
    df = pd.DataFrame(
        [
            _row("A", 100, 10, "COMPRA/FORÇA", "SEM ASSIMETRIA"),
            _row("B", 90, 90, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ"),
            _row("C", 80, 85, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ"),
            _row("D", 70, 80, "OBSERVAR", "ROMPIMENTO COM VOLUME"),
            _row("E", 60, 75, "OBSERVAR", "OBSERVAR"),
        ]
    )

    out = compare_scores(df, rank_divergence_threshold=3)

    assert out.loc[out["asset"] == "A", "divergence_type"].iloc[0] == "DIVERGENTE"
    assert out.loc[out["asset"] == "A", "rank_change"].iloc[0] == 4


def test_score_distribution_statistics_and_buckets():
    df = pd.DataFrame([_row("A", 10, s) for s in [10, 30, 50, 70, 90]])

    dist = score_distribution(df)

    assert dist["mean"] == 50
    assert dist["median"] == 50
    assert dist["min"] == 10
    assert dist["max"] == 90
    assert dist["percentiles"]["p90"] == 82
    assert dist["buckets"]["0_20"] == 1
    assert dist["buckets"]["80_100"] == 1


def test_detects_score_inflation():
    df = pd.DataFrame([_row(str(i), 80, score) for i, score in enumerate([85, 90, 91, 30, 40])])

    alert = detect_score_inflation(df, high_threshold=80, max_share=0.40)

    assert alert["has_alert"] is True
    assert alert["high_score_share"] == 0.6
    assert "Possível inflação de score" in alert["message"]


def test_textual_report_summarizes_comparison():
    df = pd.DataFrame(
        [
            _row("A", 90, 90, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ"),
            _row("B", 20, 25, "NEUTRO", "SEM ASSIMETRIA"),
            _row("C", 90, 55, "COMPRA/FORÇA", "OBSERVAR"),
            _row("D", 45, 88, "NEUTRO", "ROMPIMENTO COM VOLUME"),
            _row("E", 80, 85, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ"),
        ]
    )

    compared = compare_scores(df)
    dist = score_distribution_report(compared)
    report = textual_comparison_report(compared, dist)

    assert "Dos 5 ativos analisados" in report
    assert "2 tiveram convergência forte" in report
    assert "1 casos, o novo score foi mais rigoroso" in report
    assert "1 casos, o novo score foi mais agressivo" in report
