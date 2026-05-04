import argparse
import sqlite3
from datetime import datetime
import pandas as pd

from src.utils import load_config, project_path


def infer_underlying_from_option(ticker: str, ativos_base: list[str]) -> str | None:
    """
    Inferência simples para opções brasileiras.
    Exemplo:
    PETRF35 começa com PETR -> PETR4
    VALEF60 começa com VALE -> VALE3
    ITUBF35 começa com ITUB -> ITUB4
    """
    ticker = str(ticker).strip().upper()
    for ativo in ativos_base:
        prefix = ativo[:4].upper()
        if ticker.startswith(prefix):
            return ativo
    return None


def get_latest_stock_signals(con: sqlite3.Connection, ativos_base: list[str]) -> pd.DataFrame:
    """
    Busca o sinal intraday mais recente salvo pelo scanner do Profit.
    Usa a tabela realtime_signals.
    """
    try:
        df = pd.read_sql("SELECT * FROM realtime_signals", con)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
    df = df[df["asset"].isin(ativos_base)].copy()

    if df.empty:
        return df

    df = (
        df.sort_values("captured_at")
        .groupby("asset", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    return df


def get_latest_b3_options(con: sqlite3.Connection, ativos_base: list[str]) -> pd.DataFrame:
    """
    Busca opções da B3 na tabela b3_quotes.
    Filtra CALL e PUT e infere o ativo-objeto pelo prefixo.
    """
    q = """
    SELECT *
    FROM b3_quotes
    WHERE asset_type IN ('CALL', 'PUT')
    """
    try:
        df = pd.read_sql(q, con)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df["underlying"] = df["ticker"].apply(lambda x: infer_underlying_from_option(x, ativos_base))
    df = df[df["underlying"].notna()].copy()

    if df.empty:
        return df

    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    latest_date = df["trade_date"].max()
    df = df[df["trade_date"] == latest_date].copy()

    for col in ["volume", "trades", "quantity", "close", "option_exercise_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def calculate_option_score(options: pd.DataFrame, min_volume: float, min_trades: int) -> pd.DataFrame:
    """
    Score inicial de opções.
    Nesta primeira versão, o foco é liquidez e operabilidade.
    """
    df = options.copy()

    df["option_score"] = 0

    df.loc[df["volume"] >= min_volume, "option_score"] += 30
    df.loc[df["trades"] >= min_trades, "option_score"] += 25
    df.loc[df["quantity"] > 0, "option_score"] += 15
    df.loc[df["close"] > 0, "option_score"] += 15
    df.loc[df["option_exercise_price"] > 0, "option_score"] += 15

    df["option_score"] = df["option_score"].clip(0, 100)

    return df


def build_combined_ranking(
    stock_signals: pd.DataFrame,
    options: pd.DataFrame,
    min_volume: float,
    min_trades: int,
) -> pd.DataFrame:
    """
    Conecta ação forte com opção líquida.
    Ranking final:
    60% score da ação
    40% score da opção
    """
    if stock_signals.empty or options.empty:
        return pd.DataFrame()

    options = calculate_option_score(options, min_volume=min_volume, min_trades=min_trades)

    merged = options.merge(
        stock_signals,
        left_on="underlying",
        right_on="asset",
        how="inner",
        suffixes=("_option", "_stock"),
    )

    if merged.empty:
        return merged

    merged["score"] = pd.to_numeric(merged["score"], errors="coerce").fillna(0)
    merged["option_score"] = pd.to_numeric(merged["option_score"], errors="coerce").fillna(0)

    merged["final_score"] = ((merged["score"] * 0.60) + (merged["option_score"] * 0.40)).round(2)

    def classify(row):
        if row["final_score"] >= 80:
            return "OPORTUNIDADE FORTE"
        if row["final_score"] >= 65:
            return "OBSERVAR"
        return "NEUTRO"

    merged["combined_signal"] = merged.apply(classify, axis=1)

    cols = [
        "trade_date",
        "underlying",
        "ticker",
        "asset_type",
        "close_option",
        "option_exercise_price",
        "option_maturity",
        "volume_option",
        "trades_option",
        "score",
        "signal",
        "option_score",
        "final_score",
        "combined_signal",
        "motivos",
    ]

    # Ajuste de nomes, pois algumas colunas não recebem suffix se só existem em um lado.
    rename_map = {
        "close": "close_option",
        "volume": "volume_option",
        "trades": "trades_option",
    }
    for old, new in rename_map.items():
        if old in merged.columns and new not in merged.columns:
            merged = merged.rename(columns={old: new})

    existing = [c for c in cols if c in merged.columns]
    out = merged[existing].sort_values(
        ["final_score", "option_score", "volume_option", "trades_option"],
        ascending=False,
    )

    return out


def save_report(df: pd.DataFrame) -> None:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"ranking_acoes_opcoes_{stamp}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",")
    print(f"\nRelatório salvo em: {path}")


def main():
    parser = argparse.ArgumentParser(description="Conecta scanner de ações do Profit com opções da B3.")
    parser.add_argument("--min-volume", type=float, default=100000, help="Volume financeiro mínimo da opção.")
    parser.add_argument("--min-trades", type=int, default=10, help="Número mínimo de negócios da opção.")
    parser.add_argument("--top", type=int, default=30, help="Quantidade de oportunidades no ranking.")
    parser.add_argument("--csv", action="store_true", help="Salva relatório CSV em data/reports.")
    args = parser.parse_args()

    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    ativos_base = cfg.get("ativos_base", [])

    con = sqlite3.connect(db_path)

    stock_signals = get_latest_stock_signals(con, ativos_base)
    options = get_latest_b3_options(con, ativos_base)

    con.close()

    if stock_signals.empty:
        print("Nenhum sinal de ação encontrado. Rode antes:")
        print("python -m src.scanners.realtime_profit_scanner --once --top 10")
        print("ou, fora do pregão:")
        print("python -m src.scanners.realtime_profit_scanner --once --top 10 --demo")
        return

    if options.empty:
        print("Nenhuma opção da B3 encontrada no banco. Rode antes:")
        print("python -m src.collectors.b3_cotahist_collector --year 2026")
        return

    ranking = build_combined_ranking(
        stock_signals=stock_signals,
        options=options,
        min_volume=args.min_volume,
        min_trades=args.min_trades,
    )

    if ranking.empty:
        print("Não houve cruzamento entre ações com sinal e opções disponíveis.")
        return

    print("\nTOP OPORTUNIDADES AÇÕES + OPÇÕES")
    print(ranking.head(args.top).to_string(index=False))

    if args.csv:
        save_report(ranking)


if __name__ == "__main__":
    main()
