"""S07: Generate coverage diagnostic for all 59 VALID tickers."""
import json, pandas as pd
from pathlib import Path
from datetime import datetime

from src.integration.asset_intelligence_engine import get_asset_detail

# Load eligibility matrix
df_elig = pd.read_csv('data/reports/eligibility_matrix.csv', sep=';')
tickers = df_elig['ticker'].tolist()
print(f'Processing {len(tickers)} tickers...')

results = {}
summary_counts = {
    "COMPLETO": 0,
    "QUASE_COMPLETO": 0,
    "PARCIAL": 0,
    "DADOS_INSUFICIENTES": 0,
    "BLOQUEADO_GOVERNANCA": 0,
}

for tk in tickers:
    d = get_asset_detail(tk)

    # Count non-null scores
    scores = {
        "technical_score": d.get("technical_score_final"),
        "quant_score": d.get("quant_score"),
        "risk_status": d.get("risk_status"),
        "valuation_available": d.get("valuation_available"),
        "news_score": d.get("news_score"),
        "qualitative_score": d.get("qualitative_score"),
    }

    # Helper functions
    def safe_str(v, default="N/A"):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return str(v)

    def safe_float(v):
        if v is None:
            return None
        try:
            f = float(v)
            if pd.isna(f):
                return None
            return f
        except (ValueError, TypeError):
            return None

    # Score count: non-NA values
    def is_not_na(v):
        if v is None:
            return False
        try:
            return not pd.isna(v)
        except Exception:
            return False

    score_count = sum(
        1 for v in scores.values()
        if v is not None and not isinstance(v, bool) and is_not_na(v)
    )

    # Add valuation count separately
    has_valuation = bool(d.get("valuation_available"))
    if has_valuation:
        score_count += 1

    risk_status = safe_str(d.get("risk_status"), "")

    # Classification
    if "RISK_BLOCKED" in risk_status:
        classification = "BLOQUEADO_GOVERNANCA"
    elif score_count >= 6:
        classification = "COMPLETO"
    elif score_count == 5:
        classification = "QUASE_COMPLETO"
    elif score_count >= 3:
        classification = "PARCIAL"
    else:
        classification = "DADOS_INSUFICIENTES"

    summary_counts[classification] += 1

    results[tk] = {
        "ticker": tk,
        "coverage_status": classification,
        "score_count": score_count,
        "scores": {
            "technical_score": safe_float(d.get("technical_score_final")),
            "technical_status": safe_str(d.get("technical_status"), "N/A"),
            "quant_score": safe_float(d.get("quant_score")),
            "quant_signal_type": safe_str(d.get("quant_signal_type"), "N/A"),
            "risk_status": risk_status if risk_status else None,
            "valuation_available": has_valuation,
            "fair_value": safe_float(d.get("fair_value")),
            "upside_pct": safe_float(d.get("upside_pct")),
            "news_score": safe_float(d.get("news_score")),
            "qualitative_score": safe_float(d.get("qualitative_score")),
            "qualitative_status": safe_str(d.get("qualitative", {}).get("status"), "N/A"),
        },
        "integrated_score": safe_float(d.get("integrated_score")),
        "data_quality_score": safe_float(d.get("data_quality_score")),
        "trade_date": str(d.get("trade_date") or ""),
        "risk_reason": str(d.get("risk_limiting_factor") or ""),
        "ohlcv_days": int(df_elig[df_elig['ticker'] == tk]['ohlcv_days'].iloc[0]) if tk in df_elig['ticker'].values else None,
        "ri_status": str(df_elig[df_elig['ticker'] == tk]['ri_status'].iloc[0]) if tk in df_elig['ticker'].values else "N/A",
        "qual_quant_eligible": bool(df_elig[df_elig['ticker'] == tk]['eligible_quant'].iloc[0]) if tk in df_elig['ticker'].values else False,
    }

# Build output
output = {
    "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    "total_tickers": len(tickers),
    "summary": {
        "COMPLETO": summary_counts["COMPLETO"],
        "QUASE_COMPLETO": summary_counts["QUASE_COMPLETO"],
        "PARCIAL": summary_counts["PARCIAL"],
        "DADOS_INSUFICIENTES": summary_counts["DADOS_INSUFICIENTES"],
        "BLOQUEADO_GOVERNANCA": summary_counts["BLOQUEADO_GOVERNANCA"],
    },
    "coverage_by_score": {
        "technical_score_coverage": sum(1 for t in results.values() if t["scores"]["technical_score"] is not None),
        "quant_score_coverage": sum(1 for t in results.values() if t["scores"]["quant_score"] is not None),
        "risk_coverage": sum(1 for t in results.values() if t["scores"]["risk_status"] is not None),
        "valuation_coverage": sum(1 for t in results.values() if t["scores"]["valuation_available"]),
        "news_coverage": sum(1 for t in results.values() if t["scores"]["news_score"] is not None and t["scores"]["news_score"] > 0),
        "qualitative_coverage": sum(1 for t in results.values() if t["scores"]["qualitative_score"] is not None and t["scores"]["qualitative_score"] > 0),
    },
    "tickers": results,
}

# Save
reports_dir = Path('data/reports')
reports_dir.mkdir(parents=True, exist_ok=True)
out_path = reports_dir / 'coverage_diagnostic_expanded.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'Saved to {out_path}')
print(f'\n=== COVERAGE SUMMARY ===')
for status, count in summary_counts.items():
    print(f'{status}: {count}')

print(f'\n=== SCORE COVERAGE ===')
for key, count in output['coverage_by_score'].items():
    print(f'{key}: {count}/{len(tickers)}')

# Top 10 by integrated_score
ranking = sorted(results.values(), key=lambda x: x['integrated_score'] or 0, reverse=True)
print(f'\n=== TOP 10 BY INTEGRATED_SCORE ===')
for item in ranking[:10]:
    print(f"  {item['ticker']}: {item['integrated_score']:.2f} [{item['coverage_status']}]")

# Blocked tickers
blocked = [t for t in results.values() if t['coverage_status'] == 'BLOQUEADO_GOVERNANCA']
print(f'\n=== BLOCKED TICKERS ({len(blocked)}) ===')
for item in blocked:
    print(f"  {item['ticker']}: {item['scores']['risk_status']} - {item['risk_reason']}")