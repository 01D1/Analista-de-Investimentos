"""
ML Ranking — Modelo de probabilidade de sucesso para setups de opções.

Fluxo:
  1. extract_features(opp) → dict de features numéricas
  2. train_model(opps, outcomes) → MLRankingModel
  3. predict(model, opp) → MLPrediction

Modelos disponíveis: RandomForest, XGBoost (se instalado), LogisticRegression.
Fallback: modelo analítico calibrado quando sem dados históricos suficientes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import math

import numpy as np
import pandas as pd


# ── Feature engineering ──────────────────────────────────────────────────────

_RISK_CAT_MAP = {
    "BAIXO":                      0,
    "MODERADO":                   1,
    "ALTO":                       2,
    "ALTO_RISCO_NAO_RECOMENDADO": 3,
}

_STRATEGY_MAP = {
    "SPREAD_ALTA":  0, "SPREAD_BAIXA": 1, "CONDOR":      2,
    "BUTTERFLY":    3, "VOLATILIDADE": 4, "RENDA":       5,
    "PROTECAO":     6, "DIRECIONAL":   7,
}

_MARKET_MAP = {
    "ALTA_FORTE": 2, "ALTA_MODERADA": 1, "LATERAL": 0,
    "BAIXA_MODERADA": -1, "BAIXA_FORTE": -2,
    "ALTA_VOL": 0, "BAIXA_VOL": 0, "INDEFINIDO": 0,
}


def extract_features(opp) -> dict:
    """
    Extrai vetor de features numéricas de um StrategyOpportunity.
    Retorna dict compatível com pandas DataFrame.
    """
    p = opp.payoff

    # Custo / ganho normalizados
    net_cost   = abs(p.net_cost) if not math.isinf(abs(p.net_cost)) else 9999.0
    max_profit = p.max_profit    if not math.isinf(p.max_profit)    else 9999.0
    max_loss   = p.max_loss      if not math.isinf(p.max_loss)      else 9999.0
    rr         = p.risk_reward   if not math.isinf(p.risk_reward)   else 10.0

    # Moneyness proxy: distância do primeiro strike ao spot
    main_leg  = next((l for l in p.legs if l.option_type != "STOCK"), None)
    moneyness = 0.0
    if main_leg and p.stock_price > 0:
        moneyness = (main_leg.strike / p.stock_price - 1.0) * 100.0

    return {
        # Score e probabilidade do scanner
        "score":              float(opp.score),
        "prob_profit":        float(opp.prob_profit),
        "scenario_adherence": float(opp.scenario_adherence),
        "hv":                 float(opp.hv),
        # Estrutura
        "dte":                float(p.dte),
        "moneyness_pct":      float(moneyness),
        "net_cost":           float(net_cost),
        "max_profit":         float(max_profit),
        "max_loss":           float(max_loss),
        "risk_reward":        float(rr),
        "num_legs":           float(len([l for l in p.legs if l.option_type != "STOCK"])),
        "has_margin":         float(1.0 if p.requires_margin else 0.0),
        "risk_definido":      float(1.0 if p.risk_level == "DEFINIDO" else 0.0),
        # Categorical (encoded)
        "risk_cat":           float(_RISK_CAT_MAP.get(p.risk_category, 1)),
        "strategy_type":      float(_STRATEGY_MAP.get(p.strategy_type, 0)),
        "market_direction":   float(_MARKET_MAP.get(opp.market_condition.value, 0)),
    }


FEATURE_NAMES = [
    "score", "prob_profit", "scenario_adherence", "hv", "dte",
    "moneyness_pct", "net_cost", "max_profit", "max_loss", "risk_reward",
    "num_legs", "has_margin", "risk_definido", "risk_cat",
    "strategy_type", "market_direction",
]

FEATURE_LABELS = {
    "score":              "Score do scanner",
    "prob_profit":        "Probabilidade de lucro (modelo)",
    "scenario_adherence": "Aderência ao cenário",
    "hv":                 "Volatilidade histórica",
    "dte":                "Dias até o vencimento",
    "moneyness_pct":      "Moneyness (%)",
    "net_cost":           "Custo líquido",
    "max_profit":         "Ganho máximo",
    "max_loss":           "Perda máxima",
    "risk_reward":        "Risk/Reward",
    "num_legs":           "Número de pernas",
    "has_margin":         "Exige margem",
    "risk_definido":      "Risco definido",
    "risk_cat":           "Categoria de risco",
    "strategy_type":      "Tipo de estratégia",
    "market_direction":   "Direção do mercado",
}


# ── Modelo ───────────────────────────────────────────────────────────────────

@dataclass
class MLPrediction:
    probability:   float          # 0.0 a 1.0
    confidence:    str            # ALTA / MÉDIA / BAIXA
    label:         str            # "Probabilidade de acerto: 68%"
    top_reasons:   List[str]      # por que escolheu esse trade
    risk_flags:    List[str]      # fatores negativos
    model_type:    str            # "RandomForest" | "analítico"
    feature_importances: dict = field(default_factory=dict)


@dataclass
class MLRankingModel:
    model:         object
    feature_names: List[str]
    model_type:    str
    n_train:       int
    accuracy:      float


def train_model(
    opps: list,
    outcomes: Optional[List[int]] = None,
    model_type: str = "rf",
) -> MLRankingModel:
    """
    Treina o modelo de ranking.

    Args:
        opps:     lista de StrategyOpportunity
        outcomes: 1 = lucro, 0 = perda (se None, usa score >= 60 como proxy)
        model_type: "rf" | "xgb" | "lr"
    """
    records = [extract_features(o) for o in opps]
    X = pd.DataFrame(records, columns=FEATURE_NAMES).fillna(0)

    if outcomes is None:
        # Label proxy: score >= 60 AND prob_profit >= 0.55
        y = np.array([
            1 if (o.score >= 60 and o.prob_profit >= 0.55) else 0
            for o in opps
        ])
    else:
        y = np.array(outcomes)

    if len(X) < 10:
        return _analytic_model()

    clf, name = _build_classifier(model_type, X, y)
    acc = float((clf.predict(X) == y).mean())

    return MLRankingModel(
        model=clf,
        feature_names=FEATURE_NAMES,
        model_type=name,
        n_train=len(X),
        accuracy=acc,
    )


def predict(model: MLRankingModel, opp) -> MLPrediction:
    """Gera predição de probabilidade para um setup."""
    if model.model is None:
        return _analytic_predict(opp)

    fv = extract_features(opp)
    X  = pd.DataFrame([fv], columns=model.feature_names).fillna(0)

    try:
        prob = float(model.model.predict_proba(X)[0][1])
    except Exception:
        prob = float(opp.prob_profit)

    # Feature importances (se RandomForest/XGBoost)
    importances = {}
    try:
        imp = model.model.feature_importances_
        importances = {
            FEATURE_LABELS.get(f, f): round(float(v), 4)
            for f, v in zip(model.feature_names, imp)
        }
        importances = dict(sorted(importances.items(), key=lambda x: -x[1]))
    except AttributeError:
        pass

    # Explicação: top 3 features favoráveis e desfavoráveis
    top_reasons, risk_flags = _explain(opp, importances)

    conf = "ALTA" if prob >= 0.70 else "MÉDIA" if prob >= 0.50 else "BAIXA"
    label = f"Probabilidade de acerto: {prob:.0%}"

    return MLPrediction(
        probability=prob,
        confidence=conf,
        label=label,
        top_reasons=top_reasons,
        risk_flags=risk_flags,
        model_type=model.model_type,
        feature_importances=importances,
    )


def predict_html(pred: MLPrediction) -> str:
    """Bloco HTML com o resultado da predição ML."""
    color = "#22C55E" if pred.probability >= 0.65 else "#F59E0B" if pred.probability >= 0.50 else "#EF4444"
    pct   = int(pred.probability * 100)

    reasons_html = "".join(
        f'<li style="color:#4ADE80;margin-bottom:3px">✓ {r}</li>'
        for r in pred.top_reasons[:3]
    )
    flags_html = "".join(
        f'<li style="color:#F87171;margin-bottom:3px">✗ {r}</li>'
        for r in pred.risk_flags[:3]
    )

    imp_html = ""
    for feat, val in list(pred.feature_importances.items())[:5]:
        bar_w = int(val * 400)
        imp_html += f"""
        <div style="margin-bottom:5px">
          <div style="display:flex;justify-content:space-between;font-size:0.68rem;color:#475569;margin-bottom:2px">
            <span>{feat}</span><span>{val:.2%}</span>
          </div>
          <div style="background:#1E2D42;border-radius:2px;height:3px">
            <div style="width:{min(bar_w,100)}%;height:3px;border-radius:2px;background:#3B82F6"></div>
          </div>
        </div>"""

    return f"""
<div style="background:#0D1421;border:1px solid #1E2D42;border-radius:10px;padding:16px;margin-top:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#334155">
      🤖 Modelo ML — {pred.model_type}
    </span>
    <span style="font-size:0.75rem;font-weight:700;color:#334155">Confiança: {pred.confidence}</span>
  </div>

  <div style="text-align:center;margin-bottom:14px">
    <div style="font-size:2.2rem;font-weight:900;color:{color}">{pct}%</div>
    <div style="font-size:0.78rem;color:#475569">{pred.label}</div>
    <div style="background:#1E2D42;border-radius:4px;height:6px;margin-top:8px">
      <div style="width:{pct}%;height:6px;border-radius:4px;background:{color}"></div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px">
    <div>
      <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Por que escolheu</div>
      <ul style="margin:0;padding-left:0;list-style:none;font-size:0.76rem">{reasons_html}</ul>
    </div>
    <div>
      <div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">Pontos de atenção</div>
      <ul style="margin:0;padding-left:0;list-style:none;font-size:0.76rem">{flags_html}</ul>
    </div>
  </div>

  {"<div><div style='font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px'>Features mais importantes</div>" + imp_html + "</div>" if imp_html else ""}
</div>
"""


# ── Modelo analítico (fallback) ───────────────────────────────────────────────

def _analytic_model() -> MLRankingModel:
    return MLRankingModel(
        model=None,
        feature_names=FEATURE_NAMES,
        model_type="analítico",
        n_train=0,
        accuracy=0.0,
    )


def _analytic_predict(opp) -> MLPrediction:
    """Probabilidade calibrada sem ML — combina as dimensões existentes."""
    p = opp.payoff

    # Calibração: score + prob_profit + aderência + categoria de risco
    risk_mult = {
        "BAIXO": 1.05, "MODERADO": 1.0,
        "ALTO": 0.85, "ALTO_RISCO_NAO_RECOMENDADO": 0.60,
    }.get(p.risk_category, 1.0)

    base = (
        opp.prob_profit * 0.45
        + (opp.score / 100.0) * 0.35
        + opp.scenario_adherence * 0.20
    ) * risk_mult
    prob = max(0.05, min(0.95, base))

    top_reasons, risk_flags = _explain(opp, {})
    conf  = "ALTA" if prob >= 0.70 else "MÉDIA" if prob >= 0.50 else "BAIXA"

    return MLPrediction(
        probability=prob,
        confidence=conf,
        label=f"Probabilidade de acerto: {prob:.0%}",
        top_reasons=top_reasons,
        risk_flags=risk_flags,
        model_type="analítico",
    )


def _explain(opp, importances: dict) -> Tuple[List[str], List[str]]:
    p = opp.payoff
    reasons, flags = [], []

    if opp.score >= 70:
        reasons.append(f"Score elevado ({opp.score:.0f}/100)")
    elif opp.score >= 55:
        reasons.append(f"Score moderado ({opp.score:.0f}/100)")

    if opp.prob_profit >= 0.65:
        reasons.append(f"Alta probabilidade de lucro ({opp.prob_profit:.0%})")
    elif opp.prob_profit >= 0.55:
        reasons.append(f"Probabilidade de lucro aceitável ({opp.prob_profit:.0%})")

    if opp.scenario_adherence >= 0.85:
        reasons.append("Alta aderência ao cenário de mercado")

    if p.risk_category == "BAIXO":
        reasons.append("Risco definido e baixo — adequado para conservadores")
    elif p.risk_category == "MODERADO" and not math.isinf(p.max_loss):
        reasons.append("Risco controlado com perda máxima definida")

    if not math.isinf(p.risk_reward) and p.risk_reward >= 2.0:
        reasons.append(f"Relação risco/retorno favorável ({p.risk_reward:.1f}x)")

    if 20 <= p.dte <= 40:
        reasons.append(f"DTE em zona ideal ({p.dte}d — theta/gamma equilibrados)")

    # Flags negativos
    if opp.prob_profit < 0.45:
        flags.append(f"Probabilidade de lucro abaixo de 50% ({opp.prob_profit:.0%})")
    if p.risk_category in ("ALTO", "ALTO_RISCO_NAO_RECOMENDADO"):
        flags.append(f"Categoria de risco elevada ({p.risk_category})")
    if p.requires_margin:
        flags.append("Exige depósito de margem")
    if math.isinf(p.max_loss):
        flags.append("Risco ilimitado — sem proteção de perda")
    if p.dte < 10:
        flags.append(f"DTE muito curto ({p.dte}d) — theta acelerado")
    if opp.score < 45:
        flags.append(f"Score baixo ({opp.score:.0f}/100) — setup especulativo")

    return reasons or ["Setup identificado pelo scanner"], flags or ["Sem alertas críticos"]


def _build_classifier(model_type: str, X: pd.DataFrame, y: np.ndarray):
    """Instancia e treina o classificador."""
    from sklearn.preprocessing import StandardScaler

    if model_type == "xgb":
        try:
            from xgboost import XGBClassifier
            clf = XGBClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.1,
                use_label_encoder=False, eval_metric="logloss",
                random_state=42, verbosity=0,
            )
            clf.fit(X, y)
            return clf, "XGBoost"
        except ImportError:
            pass

    if model_type == "lr":
        from sklearn.linear_model import LogisticRegression
        sc = StandardScaler()
        Xs = sc.fit_transform(X)
        clf = LogisticRegression(max_iter=500, random_state=42)
        clf.fit(Xs, y)

        class LRWrapper:
            def __init__(self, m, s):
                self._m, self._s = m, s
                self.feature_importances_ = np.abs(m.coef_[0]) / np.abs(m.coef_[0]).sum()
            def predict(self, X): return self._m.predict(self._s.transform(X))
            def predict_proba(self, X): return self._m.predict_proba(self._s.transform(X))

        return LRWrapper(clf, sc), "Logistic Regression"

    # Default: RandomForest
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=2,
        random_state=42, n_jobs=-1,
    )
    clf.fit(X, y)
    return clf, "Random Forest"
