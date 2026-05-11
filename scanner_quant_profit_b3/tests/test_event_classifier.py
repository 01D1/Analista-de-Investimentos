from src.context.event_classifier import classify_event_type, estimate_event_impact


def test_classify_event_type_detects_core_types():
    assert classify_event_type("Lucro acima do esperado no resultado do 1T26") == "RESULTADO"
    assert classify_event_type("Companhia divulga fato relevante sobre fusão") == "FATO_RELEVANTE"
    assert classify_event_type("Guidance elevado para 2026") == "GUIDANCE"
    assert classify_event_type("Banco Central decide Selic") == "JUROS"


def test_estimate_event_impact_positive_negative_and_uncertain():
    positive = estimate_event_impact("lucro acima, recompra e dividendos maiores", event_type="RESULTADO")
    negative = estimate_event_impact("prejuízo, fraude e guidance cortado", event_type="FATO_RELEVANTE")
    uncertain = estimate_event_impact("companhia comunica mudança operacional")

    assert positive["impact_direction"] == "POSITIVO"
    assert positive["impact_score"] > 0
    assert negative["impact_direction"] == "NEGATIVO"
    assert negative["impact_score"] > positive["impact_score"] - 0.1
    assert uncertain["impact_direction"] in {"NEUTRO", "INCERTO"}

