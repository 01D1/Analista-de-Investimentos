"""
Options RTD Watchlist Builder
==============================
Fluxo: B3 COTAHIST → filtro de universo → shortlist RTD → CSV para monitoramento.

Premissas:
  - A B3/COTAHIST descobre o universo completo de opções.
  - O RTD acompanha APENAS a shortlist filtrada (top 50-200).
  - Nunca carregar todas as opções no RTD.

Uso:
    python -m src.scanners.options_rtd_watchlist_builder [--top N] [--out PATH]

Saída:
    data/realtime/options_rtd_watchlist.csv
    (colunas: ticker, ativo_objeto, tipo, strike, vencimento, moneyness,
              adv_volume, negocios_media, prioridade)
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Caminhos ───────────────────────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[2]
DB_PATH      = SCANNER_ROOT / "data" / "database" / "scanner_quant.db"
OUT_DIR      = SCANNER_ROOT / "data" / "realtime"
OUT_FILE     = OUT_DIR / "options_rtd_watchlist.csv"

# ── Ativos objeto monitorados (ações com opções líquidas na B3) ────────────────
ATIVOS_OBJETO = [
    "PETR4", "PETR3",
    "VALE3",
    "ITUB4", "BBAS3", "BBDC4", "BPAC11",
    "WEGE3",
    "ABEV3",
    "B3SA3",
    "GGBR4",
    "RENT3",
    "RADL3",
    "SUZB3",
    "PRIO3",
    "RDOR3",
    # Índice
    "IBOV",
]

# ── Parâmetros de filtro ───────────────────────────────────────────────────────
ADV_VOLUME_MIN    = 500_000       # R$ 500K volume médio diário mínimo
NEGOCIOS_MIN      = 50            # mínimo de negócios nos últimos 21d
MONEYNESS_MAX     = 0.25          # |strike/spot - 1| máximo (25% OTM)
PRECO_MIN         = 0.05          # preço mínimo para opção ter relevância
ADV_WINDOW        = 21            # dias para calcular ADV
VENCIMENTOS_MAX   = 4             # quantos vencimentos monitorar (atual + próximo)


def _get_current_spot(conn: sqlite3.Connection, ticker: str) -> Optional[float]:
    """Busca o último preço de fechamento do ativo objeto."""
    row = conn.execute(
        """
        SELECT close FROM cotahist_daily
        WHERE ticker = ? AND market_type = '010'
        ORDER BY trade_date DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()
    return float(row[0]) if row else None


def _get_next_expirations(conn: sqlite3.Connection, ticker: str, n: int = 2) -> list[str]:
    """Retorna os N próximos vencimentos disponíveis para o ativo."""
    today = date.today().isoformat()
    rows = conn.execute(
        """
        SELECT DISTINCT expiration_date
        FROM cotahist_daily
        WHERE ticker LIKE ?
          AND expiration_date >= ?
          AND expiration_date != ''
          AND expiration_date IS NOT NULL
        ORDER BY expiration_date ASC
        LIMIT ?
        """,
        (f"{ticker[:4]}%", today, n),
    ).fetchall()
    return [r[0] for r in rows]


def _build_universe(conn: sqlite3.Connection, top_n: int = 50) -> pd.DataFrame:
    """
    Constrói o universo de opções a partir do cotahist_daily.
    Aplica todos os filtros de liquidez, moneyness e vencimento.
    Retorna DataFrame com colunas para a shortlist.
    """
    today = date.today().isoformat()
    window_start = (date.today() - timedelta(days=ADV_WINDOW * 2)).isoformat()

    # Construção dinâmica da cláusula IN para ativos objeto
    placeholders = ", ".join(["?" for _ in ATIVOS_OBJETO])

    # Extrai as 4 primeiras letras dos tickers monitorados como padrão de raiz
    raizes = [a[:4] for a in ATIVOS_OBJETO]
    raiz_placeholders = ", ".join(["?" for _ in raizes])

    try:
        df = pd.read_sql(
            f"""
            SELECT
                ticker,
                close,
                volume,
                trades,
                strike,
                option_type,
                expiration_date,
                trade_date,
                SUBSTR(ticker, 1, 4) as ativo_objeto_base
            FROM cotahist_daily
            WHERE
                market_type IN ('070', '080')   -- Opções de compra e venda
                AND expiration_date >= '{today}'
                AND close >= {PRECO_MIN}
                AND trade_date >= '{window_start}'
                AND SUBSTR(ticker, 1, 4) IN ({raiz_placeholders})
            ORDER BY trade_date DESC
            """,
            conn,
            params=raizes,
        )
    except Exception as e:
        print(f"[options_rtd_watchlist_builder] Erro ao ler cotahist_daily: {e}")
        return pd.DataFrame()

    # Confirma que apenas 070/080 entram (nunca 020/termo)
    if not df.empty:
        mt_found = df["option_type"].value_counts().to_dict()
        print(f"  [✓] market_type no resultado: apenas 070(CALL) e 080(PUT). option_type → {mt_found}")

    if df.empty:
        print("[options_rtd_watchlist_builder] cotahist_daily vazia — sem opções para filtrar.")
        print("Execute o coletor COTAHIST B3 para popular os dados históricos.")
        return pd.DataFrame()

    print(f"  [1] Candidatas brutas (070/080 + ativo objeto + janela): {len(df):,} linhas / {df['ticker'].nunique():,} tickers")

    # ── ADV e negócios médios ──────────────────────────────────────────────────
    agg = (
        df.groupby("ticker")
        .agg(
            adv_volume=("volume", "mean"),
            negocios_media=("trades", "mean"),
            last_close=("close", "last"),
            strike=("strike", "last"),
            option_type=("option_type", "last"),
            expiration_date=("expiration_date", "last"),
            ativo_objeto_base=("ativo_objeto_base", "last"),
        )
        .reset_index()
    )

    print(f"  [2] Após agregação (tickers únicos):                      {len(agg):,}")

    # ── Filtro de liquidez ─────────────────────────────────────────────────────
    agg = agg[
        (agg["adv_volume"] >= ADV_VOLUME_MIN) &
        (agg["negocios_media"] >= NEGOCIOS_MIN)
    ]

    print(f"  [3] Após filtro de liquidez (ADV≥R${ADV_VOLUME_MIN:,}, neg≥{NEGOCIOS_MIN}): {len(agg):,}")

    if agg.empty:
        print("[options_rtd_watchlist_builder] Nenhuma opção passou no filtro de liquidez.")
        return pd.DataFrame()

    # ── Enriquecer com spot e moneyness ────────────────────────────────────────
    spots = {}
    for base in agg["ativo_objeto_base"].unique():
        # Tenta matches parciais para PN/ON
        for sfx in ["4", "3", "11", ""]:
            spot = _get_current_spot(conn, f"{base}{sfx}")
            if spot and spot > 0:
                spots[base] = spot
                break

    agg["spot"] = agg["ativo_objeto_base"].map(spots)
    agg = agg[agg["spot"].notna() & (agg["spot"] > 0)]

    agg["moneyness"] = (agg["strike"] / agg["spot"] - 1).abs()
    antes_money = len(agg)
    agg = agg[agg["moneyness"] <= MONEYNESS_MAX]

    print(f"  [4] Após filtro de moneyness (≤{MONEYNESS_MAX:.0%} OTM):             {len(agg):,}  (descartadas: {antes_money - len(agg):,})")

    # ── Filtro de vencimentos ──────────────────────────────────────────────────
    venc_validos = set()
    for base in agg["ativo_objeto_base"].unique():
        nexts = _get_next_expirations(conn, base, VENCIMENTOS_MAX)
        venc_validos.update(nexts)

    antes_venc = len(agg)
    if venc_validos:
        agg = agg[agg["expiration_date"].isin(venc_validos)]

    print(f"  [5] Após filtro de vencimentos ({VENCIMENTOS_MAX} próximos):               {len(agg):,}  (venc válidos: {sorted(venc_validos)})")

    # ── Score de prioridade ────────────────────────────────────────────────────
    # Normalização min-max simples
    if len(agg) > 1:
        agg["score_liq"] = (agg["adv_volume"] - agg["adv_volume"].min()) / (
            agg["adv_volume"].max() - agg["adv_volume"].min() + 1
        )
        agg["score_money"] = 1 - (agg["moneyness"] / MONEYNESS_MAX)
    else:
        agg["score_liq"]  = 1.0
        agg["score_money"] = 0.5

    agg["prioridade"] = (agg["score_liq"] * 0.6 + agg["score_money"] * 0.4).round(4)
    agg = agg.sort_values("prioridade", ascending=False).head(top_n)

    print(f"  [6] Shortlist final (top {top_n}):                              {len(agg):,}")

    # ── Output formatado ───────────────────────────────────────────────────────
    result = pd.DataFrame({
        "ticker":           agg["ticker"],
        "ativo_objeto":     agg["ativo_objeto_base"],
        "tipo":             agg["option_type"].map({"C": "CALL", "P": "PUT"}).fillna(agg["option_type"]),
        "strike":           agg["strike"].round(2),
        "vencimento":       agg["expiration_date"],
        "ultimo_preco":     agg["last_close"].round(2),
        "spot":             agg["spot"].round(2),
        "moneyness":        agg["moneyness"].round(4),
        "adv_volume":       agg["adv_volume"].round(0).astype(int),
        "negocios_media":   agg["negocios_media"].round(1),
        "prioridade":       agg["prioridade"],
    })

    return result.reset_index(drop=True)


def run_diagnostico(df: pd.DataFrame) -> None:
    """Exibe diagnóstico da shortlist gerada."""
    if df.empty:
        print("\n❌ Shortlist vazia — sem opções para monitorar no RTD.")
        return

    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO — OPTIONS RTD WATCHLIST")
    print(f"{'='*60}")
    print(f"  Total na shortlist:  {len(df)}")
    print(f"  Ativos objeto:       {df['ativo_objeto'].nunique()}")
    print(f"  CALL:                {(df['tipo']=='CALL').sum()}")
    print(f"  PUT:                 {(df['tipo']=='PUT').sum()}")
    print(f"  Vencimentos:         {df['vencimento'].nunique()} ({', '.join(sorted(df['vencimento'].unique()))})")
    print(f"  Moneyness médio:     {df['moneyness'].mean():.2%}")
    print(f"  ADV médio:           R${df['adv_volume'].mean():,.0f}")
    print(f"\n  Top 10 por prioridade:")
    print(df.head(10)[["ticker", "ativo_objeto", "tipo", "strike", "vencimento", "moneyness", "prioridade"]].to_string(index=False))
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Gera shortlist de opções para monitoramento RTD")
    parser.add_argument("--top",  type=int, default=50,  help="Máximo de opções na shortlist (default: 50)")
    parser.add_argument("--out",  type=str, default=str(OUT_FILE), help="Caminho do CSV de saída")
    parser.add_argument("--db",   type=str, default=str(DB_PATH),  help="Caminho do banco SQLite")
    args = parser.parse_args()

    print(f"[options_rtd_watchlist_builder] Abrindo banco: {args.db}")
    conn = sqlite3.connect(args.db)

    # Verificar se cotahist tem dados
    total = conn.execute("SELECT COUNT(*) FROM cotahist_daily").fetchone()[0]
    if total == 0:
        print(
            "\n⚠️  cotahist_daily está VAZIA.\n"
            "   Execute o coletor B3 COTAHIST para popular os dados históricos:\n"
            "   python -m src.collectors.b3_cotahist_collector\n"
        )
        conn.close()
        return

    print(f"[options_rtd_watchlist_builder] cotahist_daily: {total:,} linhas")
    df = _build_universe(conn, top_n=args.top)
    conn.close()

    run_diagnostico(df)

    if not df.empty:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"✅ Shortlist salva em: {out_path}")
        print(f"   Configure o RTD Profit com os {len(df)} tickers desta lista.")
    else:
        print("❌ Nenhuma opção gerada. Verifique os dados do COTAHIST.")


if __name__ == "__main__":
    main()
