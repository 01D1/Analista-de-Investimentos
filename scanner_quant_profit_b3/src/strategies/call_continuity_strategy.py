"""
CALL_CONTINUIDADE — Motor de Decisão de Opções

Estratégia direcional para compra de CALLs em ativos em tendência de alta.
Gera apenas alertas, rankings e setups para decisão MANUAL do operador.
Nunca envia ordens reais.

Uso:
    python -m src.strategies.call_continuity_strategy \\
        --account 10000 --risk 0.005 \\
        --min-volume 100000 --min-trades 10 \\
        --min-dte 15 --max-dte 45 --top 20 --save
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

# Garante saída UTF-8 no Windows (terminal cp1252 não suporta emojis)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.utils import load_config, project_path
from src.quant.indicators import atr
from src.quant.volatility import historical_volatility
from src.quant.options_math import (
    black_scholes,
    days_to_expiration,
    liquidity_score,
    estimated_spread,
)
from src.quant.signal_engine import (
    trend_condition,
    momentum_condition,
    volume_condition,
    volatility_condition,
)
from src.quant.position_sizing import compute_sizing
from src.integration.signal_enricher import enrich_setups

# ---------------------------------------------------------------------------
# Status possíveis de um setup
# ---------------------------------------------------------------------------

SETUP_STATUS_LABELS = {
    "ENTRADA_VALIDADA": "✅ Todas as condições atendidas",
    "AGUARDAR_GATILHO": "⏳ Aguardar confirmação de entrada",
    "INVALIDADO": "❌ Condições de entrada não atendidas",
    "EM_ABERTO": "📌 Posição em aberto no diário",
    "ALVO_1": "🎯 Alvo 1 atingido",
    "ALVO_2": "🏆 Alvo 2 atingido",
    "STOPADO": "🛑 Stop financeiro ativado",
}

# ---------------------------------------------------------------------------
# Carregamento de configuração
# ---------------------------------------------------------------------------


def load_quant_config(path: str = "config_quant.yaml") -> dict:
    cfg_path = project_path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"config_quant.yaml não encontrado em: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Queries ao banco de dados
# ---------------------------------------------------------------------------


def get_stock_history(con: sqlite3.Connection, ticker: str, days: int = 60) -> pd.DataFrame:
    """
    Busca histórico OHLCV de um ativo na tabela b3_quotes (asset_type='ACAO').
    Agrupa por data para eliminar duplicatas de mercado (mesmo ticker, mesma data).
    """
    q = """
    SELECT
        trade_date,
        AVG(open)   AS open,
        MAX(high)   AS high,
        MIN(low)    AS low,
        AVG(close)  AS close,
        MAX(volume) AS volume,
        MAX(trades) AS trades
    FROM b3_quotes
    WHERE ticker = ?
      AND asset_type = 'ACAO'
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT ?
    """
    try:
        df = pd.read_sql_query(q, con, params=(ticker, days))
    except Exception:
        return pd.DataFrame()

    for col in ["open", "high", "low", "close", "volume", "trades"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def get_realtime_signal(con: sqlite3.Connection, ticker: str) -> Optional[dict]:
    """
    Busca o sinal intraday mais recente do Profit para o ativo.
    Retorna None se não houver dados intraday.
    """
    q = """
    SELECT * FROM realtime_signals
    WHERE asset = ?
    ORDER BY captured_at DESC
    LIMIT 1
    """
    try:
        df = pd.read_sql_query(q, con, params=(ticker,))
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    except Exception:
        return None


def get_options(
    con: sqlite3.Connection,
    underlying: str,
    option_type: str,
    min_dte: int,
    max_dte: int,
) -> pd.DataFrame:
    """
    Busca opções CALL ou PUT para um ativo na tabela b3_quotes.
    Usa o prefixo dos 4 primeiros caracteres para inferir o ativo objeto.
    Elimina duplicatas agrupando por ticker na última data.
    """
    prefix = underlying[:4].upper()
    asset_type = option_type.upper()  # 'CALL' ou 'PUT'
    q = f"""
    WITH last_date AS (
        SELECT MAX(trade_date) AS dt
        FROM b3_quotes
        WHERE asset_type = '{asset_type}'
    )
    SELECT
        trade_date,
        ticker,
        asset_type,
        AVG(open)                  AS open,
        MAX(high)                  AS high,
        MIN(low)                   AS low,
        AVG(close)                 AS close,
        MAX(volume)                AS volume,
        MAX(trades)                AS trades,
        AVG(quantity)              AS quantity,
        AVG(option_exercise_price) AS strike,
        option_maturity
    FROM b3_quotes
    WHERE ticker LIKE '{prefix}%'
      AND asset_type = '{asset_type}'
      AND trade_date = (SELECT dt FROM last_date)
    GROUP BY ticker, option_maturity
    ORDER BY volume DESC, trades DESC
    """
    try:
        df = pd.read_sql_query(q, con)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    for col in ["open", "high", "low", "close", "volume", "trades", "quantity", "strike"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # option_maturity vem no formato YYYYMMDD (ex: '20260529')
    ref_date = pd.to_datetime(df["trade_date"].iloc[0]).date()
    df["expiration_date"] = df["option_maturity"]
    df["dte"] = df["option_maturity"].apply(
        lambda x: days_to_expiration(ref_date, str(x)) if x else 0
    )
    df["option_type"] = asset_type
    df = df[(df["dte"] >= min_dte) & (df["dte"] <= max_dte)].copy()
    df["underlying"] = underlying
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Análise técnica do ativo objeto
# ---------------------------------------------------------------------------


def analyze_stock(history: pd.DataFrame, qcfg: dict) -> dict:
    """
    Roda análise técnica completa no histórico OHLCV do ativo.
    Retorna dict com todos os scores e metadados.
    """
    if len(history) < 5:
        return {
            "valid": False,
            "reason": f"Histórico insuficiente ({len(history)} registros)",
        }

    close = history["close"]
    high = history["high"]
    low = history["low"]
    volume = history["volume"]

    fast = qcfg.get("sma_fast", 9)
    slow = qcfg.get("sma_slow", 21)
    rsi_p = qcfg.get("rsi_period", 14)
    atr_p = qcfg.get("atr_period", 14)
    hv_w = qcfg.get("hv_window", 21)
    vol_w = qcfg.get("volume_avg_window", 20)

    trend = trend_condition(close, fast=fast, slow=slow)
    momentum = momentum_condition(close, period=rsi_p)
    vol_sig = volume_condition(volume, window=vol_w)
    volat = volatility_condition(close, window=hv_w)

    last_close = float(close.iloc[-1])
    last_atr = float(atr(high, low, close, period=atr_p).iloc[-1])

    return {
        "valid": True,
        "close": last_close,
        "atr": round(last_atr, 4),
        **trend,
        **momentum,
        **vol_sig,
        **volat,
    }


# ---------------------------------------------------------------------------
# Score e classificação de cada opção
# ---------------------------------------------------------------------------


def score_and_classify(
    opt: pd.Series,
    stock: dict,
    qcfg: dict,
) -> Optional[dict]:
    """
    Calcula o score final ponderado e classifica o setup da opção.
    Retorna None se a opção não tiver preço válido.
    """
    entry = float(opt.get("close", 0))
    strike = float(opt.get("strike", 0))
    dte = int(opt.get("dte", 0))
    trades = int(opt.get("trades", 0))
    volume_opt = float(opt.get("volume", 0))
    option_type = str(opt.get("option_type", "CALL"))
    stock_close = stock.get("close", 0)

    if entry <= 0 or stock_close <= 0:
        return None

    weights = qcfg.get("score_weights", {})
    min_dte = qcfg.get("min_dte", 15)
    max_dte = qcfg.get("max_dte", 45)
    min_trades = qcfg.get("min_negocios_opcao", 10)
    min_vol = qcfg.get("min_volume_opcao", 100_000)
    r = qcfg.get("taxa_livre_risco", 0.1475)

    # ---- DTE score ----
    ideal_dte = (min_dte + max_dte) / 2.0
    dte_score = max(0.0, 100.0 - abs(dte - ideal_dte) * 3.5)

    # ---- Moneyness ----
    moneyness_pct = (stock_close / strike - 1.0) * 100.0 if strike > 0 else 0.0
    if option_type == "CALL":
        # Preferência: ATM a levemente OTM (0% a +7%)
        if 0.0 <= moneyness_pct <= 7.0:
            moneyness_score = 100
        elif -2.0 <= moneyness_pct < 0.0:
            moneyness_score = 85
        elif 7.0 < moneyness_pct <= 15.0:
            moneyness_score = 60
        else:
            moneyness_score = 15
    else:
        if -7.0 <= moneyness_pct <= 0.0:
            moneyness_score = 100
        elif 0.0 < moneyness_pct <= 2.0:
            moneyness_score = 85
        elif -15.0 <= moneyness_pct < -7.0:
            moneyness_score = 60
        else:
            moneyness_score = 15

    # ---- Liquidez ----
    liq_score = liquidity_score(trades, volume_opt, min_trades, min_vol)

    # ---- Black-Scholes ----
    T = max(dte / 365.0, 1.0 / 365.0)
    sigma = max(stock.get("hist_vol", 0.30), 0.05)
    bs = black_scholes(stock_close, strike, T, r, sigma, option_type)

    # ---- Position sizing ----
    sizing = compute_sizing(
        capital=qcfg.get("capital_inicial", 10_000),
        risk_pct=qcfg.get("risco_por_trade", 0.005),
        entry=entry,
        stop_pct=qcfg.get("stop_opcao_pct", 0.30),
        target1_pct=qcfg.get("alvo_1_pct", 0.50),
        target2_pct=qcfg.get("alvo_2_pct", 1.00),
        win_rate_est=qcfg.get("win_rate_estimado", 0.45),
        contract_size=qcfg.get("contract_size", 100),
    )

    # ---- Score ponderado ----
    final_score = (
        stock.get("trend_score", 0) * weights.get("stock_trend_score", 0.25)
        + stock.get("momentum_score", 0) * weights.get("stock_momentum_score", 0.20)
        + stock.get("volume_score", 0) * weights.get("stock_volume_score", 0.15)
        + liq_score * weights.get("option_liquidity_score", 0.20)
        + moneyness_score * weights.get("option_moneyness_score", 0.10)
        + dte_score * weights.get("option_dte_score", 0.10)
    )

    # ---- Avaliação das condições individuais ----
    conditions = {
        "tendencia_alta": stock.get("trend") in ("ALTA", "ALTA_PARCIAL"),
        "momentum_ok": stock.get("momentum_condition") in ("FORTE", "POSITIVO", "NEUTRO"),
        "volume_ok": stock.get("volume_condition") in ("EXPLOSIVO", "MUITO_ALTO", "ALTO", "NORMAL"),
        "volatilidade_ok": stock.get("vol_condition") in ("MEDIA", "ALTA", "BAIXA"),
        "liquidez_ok": liq_score >= 50,
        "dte_ok": min_dte <= dte <= max_dte,
        "moneyness_ok": moneyness_score >= 70,
    }
    conditions_met = sum(conditions.values())
    total_conditions = len(conditions)

    # ---- Status do setup ----
    sc_validada = qcfg.get("score_entrada_validada", 70)
    sc_aguardar = qcfg.get("score_aguardar", 50)

    if final_score >= sc_validada and conditions_met >= total_conditions - 1:
        status = "ENTRADA_VALIDADA"
    elif final_score >= sc_aguardar or conditions_met >= total_conditions - 2:
        status = "AGUARDAR_GATILHO"
    else:
        status = "INVALIDADO"

    # ---- Explicação textual ----
    reasons = []
    trend_str = stock.get("trend", "?")
    rsi_val = stock.get("rsi", 0)
    vol_ratio = stock.get("volume_ratio", 1)
    vol_cond = stock.get("volume_condition", "?")
    hist_vol_pct = stock.get("hist_vol_pct", 0)

    reasons.append(f"Tendência={trend_str}")
    reasons.append(f"RSI={rsi_val:.1f}({stock.get('momentum_condition','?')})")
    reasons.append(f"Vol={vol_cond}({vol_ratio:.1f}x)")
    reasons.append(f"HV={hist_vol_pct:.1f}%")
    reasons.append(f"Liquidez={liq_score:.0f}/100")
    reasons.append(f"Moneyness={bs.moneyness}({moneyness_pct:+.1f}%)")
    reasons.append(f"DTE={dte}d")
    if bs.delta:
        reasons.append(f"Delta={bs.delta:.2f}")

    spread = estimated_spread(entry, volume_opt, trades)

    return {
        # Identificação
        "ticker": str(opt.get("ticker", "")),
        "underlying": str(opt.get("underlying", "")),
        "option_type": option_type,
        "trade_date": str(opt.get("trade_date", "")),
        "expiration_date": str(opt.get("expiration_date", "")),
        # Preços da opção
        "preco_opcao": entry,
        "strike": strike,
        "dte": dte,
        "spread_estimado": spread,
        # Liquidez
        "negocios": trades,
        "volume_opcao": volume_opt,
        # Ativo objeto
        "preco_ativo": stock_close,
        "atr_ativo": stock.get("atr", 0),
        # Greeks e BS
        "bs_price": bs.price,
        "delta": bs.delta,
        "gamma": bs.gamma,
        "theta": bs.theta,
        "vega": bs.vega,
        "moneyness": bs.moneyness,
        "moneyness_pct": round(moneyness_pct, 2),
        # Indicadores técnicos
        "trend": stock.get("trend"),
        "rsi": stock.get("rsi"),
        "macd_hist": stock.get("macd_hist"),
        "volume_ratio": stock.get("volume_ratio"),
        "volume_condition": stock.get("volume_condition"),
        "hist_vol": stock.get("hist_vol"),
        "hist_vol_pct": stock.get("hist_vol_pct"),
        "vol_condition": stock.get("vol_condition"),
        # Scores
        "trend_score": stock.get("trend_score", 0),
        "momentum_score": stock.get("momentum_score", 0),
        "volume_score": stock.get("volume_score", 0),
        "option_liquidity_score": round(liq_score, 2),
        "option_moneyness_score": moneyness_score,
        "option_dte_score": round(dte_score, 2),
        "final_score": round(final_score, 2),
        # Setup
        "status": status,
        "conditions_met": conditions_met,
        "total_conditions": total_conditions,
        "motivo": " | ".join(reasons),
        # Sizing
        "contratos": sizing["contracts"],
        "entrada_planejada": sizing["entry"],
        "stop": sizing["stop"],
        "alvo_1": sizing["alvo_1"],
        "alvo_2": sizing["alvo_2"],
        "risco_financeiro": sizing["risco_financeiro"],
        "risco_pct_capital": sizing["risco_pct_capital"],
        "payoff_ratio": sizing["payoff_ratio"],
        "kelly_fraction": sizing["kelly_fraction"],
    }


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------


def run_strategy(
    con: sqlite3.Connection,
    cfg: dict,
    qcfg: dict,
    account: float,
    risk: float,
    min_volume: float,
    min_trades: int,
    min_dte: int,
    max_dte: int,
    top: int,
) -> pd.DataFrame:
    """
    Executa a estratégia CALL_CONTINUIDADE para todos os ativos configurados.
    Retorna DataFrame com os setups ordenados por score.
    """
    # Sobrescreve config com parâmetros CLI
    qcfg = dict(qcfg)
    qcfg["capital_inicial"] = account
    qcfg["risco_por_trade"] = risk
    qcfg["min_volume_opcao"] = min_volume
    qcfg["min_negocios_opcao"] = min_trades
    qcfg["min_dte"] = min_dte
    qcfg["max_dte"] = max_dte

    ativos = qcfg.get("ativos_permitidos", cfg.get("ativos_base", []))
    tipos = qcfg.get("tipos_opcao_permitidos", ["CALL"])

    results = []

    for ativo in ativos:
        history = get_stock_history(con, ativo)
        if len(history) < 5:
            print(f"  [{ativo}] Histórico insuficiente ({len(history)} registros) — pulando.")
            continue

        stock_analysis = analyze_stock(history, qcfg)
        if not stock_analysis.get("valid"):
            print(f"  [{ativo}] {stock_analysis.get('reason')} — pulando.")
            continue

        # Enriquece com sinal intraday se disponível
        rt = get_realtime_signal(con, ativo)
        if rt:
            # Sobrescreve close com preço intraday mais recente
            stock_analysis["close"] = rt.get("last", stock_analysis["close"])
            stock_analysis["intraday_score"] = rt.get("score", 0)
            stock_analysis["intraday_signal"] = rt.get("signal", "N/A")

        for opt_type in tipos:
            options = get_options(con, ativo, opt_type, min_dte, max_dte)
            if options.empty:
                continue

            # Filtros de liquidez mínima antes de calcular scores
            options = options[options["volume"] >= min_volume].copy()
            options = options[options["trades"] >= min_trades].copy()

            if options.empty:
                continue

            for _, opt_row in options.iterrows():
                result = score_and_classify(opt_row, stock_analysis, qcfg)
                if result is not None:
                    results.append(result)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.sort_values(
        ["final_score", "option_liquidity_score", "volume_opcao"],
        ascending=False,
    )
    df = df.drop_duplicates(subset=["ticker"])

    # Limita opções por ativo para garantir diversificação
    max_per = qcfg.get("max_opcoes_por_ativo", 0)
    if max_per and max_per > 0:
        df = (
            df.groupby("underlying", group_keys=False)
            .apply(lambda x: x.head(max_per))
            .sort_values(["final_score", "option_liquidity_score", "volume_opcao"], ascending=False)
        )

    df = df.head(top).reset_index(drop=True)

    df = enrich_setups(df, qcfg)
    return df


# ---------------------------------------------------------------------------
# Saída no terminal
# ---------------------------------------------------------------------------


def print_results(df: pd.DataFrame) -> None:
    if df.empty:
        print("\nNenhum setup gerado com os filtros atuais.")
        return

    print("\n" + "=" * 90)
    print("  CALL_CONTINUIDADE — SETUPS DE ENTRADA")
    print("=" * 90)

    cols_display = [
        "ticker", "underlying", "status", "final_score",
        "preco_opcao", "strike", "dte",
        "delta", "theta",
        "contratos", "stop", "alvo_1", "alvo_2",
        "risco_financeiro",
    ]
    existing = [c for c in cols_display if c in df.columns]
    print(df[existing].to_string(index=False))

    print("\n--- Detalhamento dos setups ---")
    for _, row in df.iterrows():
        status_label = SETUP_STATUS_LABELS.get(row["status"], row["status"])
        print(f"\n{row['ticker']} ({row['underlying']}) | Score: {row['final_score']:.1f} | {status_label}")
        print(f"  Entrada: R$ {row['entrada_planejada']:.4f}  |  Stop: R$ {row['stop']:.4f}  "
              f"|  Alvo1: R$ {row['alvo_1']:.4f}  |  Alvo2: R$ {row['alvo_2']:.4f}")
        print(f"  Contratos: {row['contratos']}  |  Risco: R$ {row['risco_financeiro']:.2f}  "
              f"|  Payoff: {row['payoff_ratio']:.1f}x  |  Kelly: {row['kelly_fraction']:.4f}")
        print(f"  {row['motivo']}")


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def save_report(df: pd.DataFrame) -> Path:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"call_continuidade_{stamp}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    print(f"\nRelatório salvo em: {path}")
    return path


def append_to_journal(df: pd.DataFrame) -> None:
    """Salva os setups ENTRADA_VALIDADA no diário de trades."""
    journal_path = project_path("data/journal/trade_journal.csv")
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = df[df["status"] == "ENTRADA_VALIDADA"].copy()
    if candidates.empty:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    journal_rows = []
    for _, row in candidates.iterrows():
        journal_rows.append({
            "data_sinal": now,
            "ativo": row.get("underlying", ""),
            "opcao": row.get("ticker", ""),
            "tipo": row.get("option_type", ""),
            "direcao": "COMPRA",
            "entrada_planejada": row.get("entrada_planejada", ""),
            "preco_entrada": "",
            "stop": row.get("stop", ""),
            "alvo_1": row.get("alvo_1", ""),
            "alvo_2": row.get("alvo_2", ""),
            "quantidade": row.get("contratos", ""),
            "risco_financeiro": row.get("risco_financeiro", ""),
            "status": "AGUARDAR_ENTRADA",
            "resultado": "",
            "retorno_pct": "",
            "observacoes": row.get("motivo", ""),
        })

    new_df = pd.DataFrame(journal_rows)
    if journal_path.exists():
        existing = pd.read_csv(journal_path, sep=";", encoding="utf-8-sig")
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_csv(journal_path, index=False, sep=";", encoding="utf-8-sig")
    print(f"Diário atualizado com {len(journal_rows)} setup(s): {journal_path}")


# ---------------------------------------------------------------------------
# Entry point CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CALL_CONTINUIDADE — Motor de decisão de opções (apenas alertas, sem ordens reais).",
    )
    parser.add_argument("--account", type=float, default=10_000, help="Capital disponível (R$).")
    parser.add_argument("--risk", type=float, default=0.005, help="% do capital por trade (ex: 0.005).")
    parser.add_argument("--min-volume", type=float, default=100_000, help="Volume mínimo da opção.")
    parser.add_argument("--min-trades", type=int, default=10, help="Negócios mínimos da opção.")
    parser.add_argument("--min-dte", type=int, default=15, help="Dias mínimos até o vencimento.")
    parser.add_argument("--max-dte", type=int, default=45, help="Dias máximos até o vencimento.")
    parser.add_argument("--top", type=int, default=20, help="Número de setups no ranking.")
    parser.add_argument("--save", action="store_true", help="Salva relatório CSV em data/reports.")
    parser.add_argument("--journal", action="store_true", help="Adiciona ENTRADA_VALIDADA ao diário.")
    parser.add_argument("--config", default="config_quant.yaml", help="Arquivo de configuração quant.")
    args = parser.parse_args()

    print("=" * 60)
    print("CALL_CONTINUIDADE — Motor de Trade v1")
    print("⚠️  APENAS ALERTAS — Nenhuma ordem será enviada.")
    print("=" * 60)

    cfg = load_config()
    qcfg = load_quant_config(args.config)

    db_path = project_path(cfg["database_path"])
    if not db_path.exists():
        print(f"Banco de dados não encontrado: {db_path}")
        print("Execute primeiro: python -m src.db.init_db")
        return

    con = sqlite3.connect(db_path)
    try:
        df = run_strategy(
            con=con,
            cfg=cfg,
            qcfg=qcfg,
            account=args.account,
            risk=args.risk,
            min_volume=args.min_volume,
            min_trades=args.min_trades,
            min_dte=args.min_dte,
            max_dte=args.max_dte,
            top=args.top,
        )
    finally:
        con.close()

    print_results(df)

    if args.save and not df.empty:
        save_report(df)

    if args.journal and not df.empty:
        append_to_journal(df)

    if df.empty:
        print("\nDica: rode primeiro o coletor COTAHIST para ter dados de opções no banco:")
        print("  python -m src.collectors.b3_cotahist_collector --year 2026")


if __name__ == "__main__":
    main()
