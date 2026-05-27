"""
Options RTD Watchlist Builder — Diversified Edition
===================================================
Gera shortlists diversificadas por ativo objeto.

Fluxo: COTAHIST (batch query única) → rank per ativo → shortlist diversificada
      → diagnóstico inline (sem queries extras por ativo)
      → vencimentos extraídos do resultado principal

Saídas:
  - data/realtime/options_rtd_watchlist.csv     (principal, máx 80 opts)
  - data/realtime/options_rtd_symbols.csv        (para Profit)
  - data/realtime/options_rtd_diagnostic.csv    (diagnóstico por ativo)

Regras:
  - Nunca puxar TODAS as opções.
  - RTD no Profit: máx 80 tickers.
  - Limite por ativo objeto para diversidade.
  - Opções com ADV < R$500K = "MONITORAMENTO", não oportunidade.
  - market_type: apenas 070 (CALL) e 080 (PUT).
  - Sem opções elegíveis → marcar no diagnóstico.
  - Performance: batch queries únicas; SEM loop de queries por ativo.
  - Vencimentos: extraídos do resultado batch (nenhuma query extra).

Uso:
    python -m src.scanners.options_rtd_watchlist_builder --top 80
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# ── Caminhos ───────────────────────────────────────────────────────────────────
SCANNER_ROOT   = Path(__file__).resolve().parents[2]
DB_PATH        = SCANNER_ROOT / "data" / "database" / "scanner_quant.db"
OUT_DIR        = SCANNER_ROOT / "data" / "realtime"

# ── Ativos objeto monitorados ─────────────────────────────────────────────────
# chave = 4 letras raiz; valor = limite máximo na shortlist
ATIVOS_OBJETO: dict[str, int] = {
    "PETR": 20,  # maiores volumes em R$
    "VALE": 20,
    "ITUB": 12,
    "BBDC": 12,
    "BBAS": 12,
    "WEGE":  8,
    "B3SA":  8,
    "ABEV":  8,
    "SUZB":  8,
    "RENT":  8,
    "BPAC":  8,
    "GGBR":  6,
    "RADL":  6,
    "PRIO":  6,
    "RDOR":  6,
    "HAPV":  6,
    "ENEV":  6,
    "CPLE":  6,
    "CMIG":  6,
    "EGIE":  6,
    "TAEE":  6,
    "CSNA":  6,
    "USIM":  6,
    "ALSO":  6,
    "META":  4,
    "SBFG":  4,
}

# ── Parâmetros ───────────────────────────────────────────────────────────────────
TOTAL_MAX           = 80
ADV_WINDOW_DAYS     = 10        # dias para calcular ADV
PRECO_MIN           = 0.05     # preço mínimo (R$ 0.05)
MONEYNESS_MAX       = 0.20      # |strike/spot - 1| ≤ 20%
ADV_VOLUME_MIN_OPP  = 500_000   # R$ 500K → OPORTUNIDADE
ADV_VOLUME_MIN_LIQ  = 100_000   # R$ 100K → MONITORAMENTO
NEGOCIOS_MIN        = 20        # negociações mínimas no período


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _window() -> tuple[str, str]:
    return (
        (date.today() - timedelta(days=ADV_WINDOW_DAYS)).isoformat(),
        (date.today() - timedelta(days=1)).isoformat(),
    )


# ── Leitura do banco ─────────────────────────────────────────────────────────

def _load_spots(conn: sqlite3.Connection) -> dict[str, float]:
    """Lê spots de todos os ativos com UMA query batch (~0.7s)."""
    all_combos = [f"{r}{s}" for r in ATIVOS_OBJETO for s in ("4", "3", "11", "")]
    ph = ",".join(["?" for _ in all_combos])
    rows = conn.execute(
        f"""
        SELECT ticker, MAX(close) AS spot
        FROM cotahist_daily
        WHERE ticker IN ({ph})
          AND market_type = '010'
          AND close > 0
        GROUP BY ticker
        """,
        all_combos,
    ).fetchall()
    spots, seen = {}, set()
    for ticker, spot in rows:
        raiz = ticker[:4]
        if raiz not in seen:
            spots[raiz] = float(spot)
            seen.add(raiz)
    return spots


def _load_options(conn: sqlite3.Connection, spots: dict[str, float]) -> tuple[pd.DataFrame, list[str]]:
    """
    Uma única query batch para todos os ativos.
    Retorna (df_options, vencimentos_unicos).
    Tempo: ~7.5s (dominado pela query HAVING com AVG sobre 7.8M rows).
    """
    window, _ = _window()
    raizes   = list(ATIVOS_OBJETO.keys())
    ph       = ",".join(["?" for _ in raizes])

    rows = conn.execute(
        f"""
        SELECT
            ticker,
            CASE WHEN market_type = '070' THEN 'CALL' ELSE 'PUT' END AS tipo,
            ROUND(AVG(strike), 2)                                 AS strike,
            MIN(expiration_date)                                   AS vencimento,
            ROUND(AVG(volume),  0)                                  AS adv_volume,
            ROUND(AVG(trades),  1)                                   AS negocios_media,
            MAX(close)                                              AS ultimo_preco,
            SUBSTR(ticker, 1, 4)                                    AS ativo_objeto,
            COUNT(DISTINCT trade_date)                              AS dias_ativos
        FROM cotahist_daily
        WHERE market_type    IN ('070', '080')
          AND close          >= ?
          AND trade_date     >= ?
          AND SUBSTR(ticker, 1, 4) IN ({ph})
        GROUP BY ticker, market_type
        HAVING adv_volume   >= ?
          AND negocios_media >= ?
        ORDER BY ativo_objeto, adv_volume DESC
        """,
        [PRECO_MIN, window] + raizes + [ADV_VOLUME_MIN_LIQ, NEGOCIOS_MIN],
    ).fetchall()

    if not rows:
        return pd.DataFrame(), []

    # Mapear spots e calcular moneyness
    records = []
    for row in rows:
        ticker, tipo, strike, venc, adv, neg, prec, ativo, dias = row
        spot = spots.get(ativo, 0)
        if not spot:
            continue
        mney = abs(float(strike) / spot - 1) if strike else 999
        records.append({
            "ticker":          ticker,
            "ativo_objeto":    ativo,
            "tipo":            tipo,
            "strike":          float(strike),
            "vencimento":      venc or "",
            "ultimo_preco":    float(prec) if prec else 0.0,
            "spot":            spot,
            "moneyness":       round(mney, 4),
            "adv_volume":      int(adv) if adv else 0,
            "negocios_media":  float(neg) if neg else 0.0,
            "dias_ativos":     dias or 0,
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df, []

    # Vencimentos extraídos do resultado (sem query extra)
    vencs = sorted(df["vencimento"].unique().tolist())
    print(f"[builder] Vencimentos únicos: {vencs[:4]}")

    # Filtro moneyness
    antes = len(df)
    df = df[df["moneyness"] <= MONEYNESS_MAX].copy()
    print(f"[builder] Filtro moneyness ≤{MONEYNESS_MAX:.0%}]: {antes} → {len(df)} "
          f"(descartadas: {antes - len(df)})")

    # Categoria
    df["categoria"] = df["adv_volume"].apply(
        lambda x: "OPORTUNIDADE" if x >= ADV_VOLUME_MIN_OPP else "MONITORAMENTO"
    )

    return df.reset_index(drop=True), vencs


def _diversify(df: pd.DataFrame, total_max: int = 80) -> pd.DataFrame:
    """
    Ranking diversificado:
      1. Ordena: OPORTUNIDADE > MONITORAMENTO, por ativo objeto.
      2. Aplica limite por ativo (não mais que X opções por ativo).
      3. Ordenação final: prioridade global.
      4. Limita ao total máximo (80).
    """
    if df.empty:
        return df

    cat_order = {"OPORTUNIDADE": 0, "MONITORAMENTO": 1}
    df = df.copy()
    df["cat_ord"] = df["categoria"].map(cat_order).fillna(2)
    df = df.sort_values(
        ["cat_ord", "ativo_objeto", "adv_volume"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    # Seleção com limite por ativo
    selected = []
    for ativo, limite in ATIVOS_OBJETO.items():
        taken = sum(1 for t in selected if t.startswith(ativo))
        remaining = max(0, limite - taken)
        if remaining > 0:
            subset = df[df["ativo_objeto"] == ativo].head(remaining)
            selected.extend(subset["ticker"].tolist())

    df_final = df[df["ticker"].isin(selected)].copy()
    df_final["cat_ord"] = df_final["categoria"].map(cat_order).fillna(2)
    df_final = df_final.sort_values(
        ["cat_ord", "ativo_objeto", "adv_volume"],
        ascending=[True, True, False],
    ).head(total_max).reset_index(drop=True)

    # Score de prioridade
    if len(df_final) > 0:
        mx = df_final["adv_volume"].max()
        mn = df_final["adv_volume"].min()
        rng = mx - mn if mx > mn else 1
        df_final["score_liq"]   = (df_final["adv_volume"] - mn) / rng
        df_final["score_money"]  = 1 - (df_final["moneyness"] / MONEYNESS_MAX)
        boost = df_final["categoria"].map({
            "OPORTUNIDADE": 0.2, "MONITORAMENTO": 0.0,
        }).fillna(0)
        df_final["prioridade"] = (
            df_final["score_liq"] * 0.6 +
            df_final["score_money"] * 0.3 +
            boost * 0.1
        ).round(4)

    return df_final


def _build_diagnostic(df_raw: pd.DataFrame, spots: dict[str, float],
                     df_final: pd.DataFrame) -> pd.DataFrame:
    """
    Diagnóstico inline — extraído dos dados já carregados.
    Para ativos sem opções: marca "SEM OPÇÕES NO COTAHIST" ou "SEM LIQUIDEZ MÍNIMA".
    """
    rows_out = []
    for ativo, limite in ATIVOS_OBJETO.items():
        sub      = df_raw[df_raw["ativo_objeto"] == ativo] if not df_raw.empty else pd.DataFrame()
        sub_out  = df_final[df_final["ativo_objeto"] == ativo] if not df_final.empty else pd.DataFrame()
        spot     = spots.get(ativo)
        in_short = len(sub_out)
        candid   = len(sub)
        opp      = int((sub["categoria"] == "OPORTUNIDADE").sum()) if not sub.empty else 0
        mon      = int((sub["categoria"] == "MONITORAMENTO").sum()) if not sub.empty else 0

        if candid == 0:
            status = "SEM OPÇÕES NO COTAHIST"
        elif candid > 0 and opp == 0 and mon == 0:
            # Filtradas por moneyness
            status = "SEM LIQUIDEZ MÍNIMA"
        else:
            status = f"OK — {candid} c/ liq ({opp} opp, {mon} mon) / {in_short}/{limite} na shortlist"

        rows_out.append({
            "ativo":         ativo,
            "spot":          round(spot, 2) if spot else None,
            "limite":        limite,
            "total_cand":    candid,
            "com_liquidez":  candid,
            "oportunidades": opp,
            "na_shortlist":  in_short,
            "status":        status,
        })

    return pd.DataFrame(rows_out)


# ── Output ─────────────────────────────────────────────────────────────────────

def _format_watchlist(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return pd.DataFrame({
        "ticker":         df["ticker"].values,
        "ativo_objeto":   df["ativo_objeto"].values,
        "tipo":           df["tipo"].values,
        "strike":         df["strike"].round(2).values,
        "vencimento":     df["vencimento"].values,
        "ultimo_preco":   df["ultimo_preco"].round(2).values,
        "spot":           df["spot"].round(2).values,
        "moneyness":      df["moneyness"].round(4).values,
        "adv_volume":     df["adv_volume"].values,
        "negocios_media": df["negocios_media"].round(1).values,
        "prioridade":     df["prioridade"].values,
        "categoria":      df["categoria"].values,
    })


def _print_summary(df: pd.DataFrame, diag: pd.DataFrame, vencs: list[str]) -> None:
    print(f"\n{'='*70}")
    print(f"DIAGNÓSTICO — SHORTLIST DIVERSIFICADA")
    print(f"{'='*70}")

    if not df.empty:
        print(f"\n  Total:             {len(df)} opções")
        print(f"  Ativos objeto:     {df['ativo_objeto'].nunique()}")
        print(f"  CALL:              {(df['tipo']=='CALL').sum()}")
        print(f"  PUT:               {(df['tipo']=='PUT').sum()}")
        print(f"  OPORTUNIDADE:      {(df['categoria']=='OPORTUNIDADE').sum()}")
        print(f"  MONITORAMENTO:     {(df['categoria']=='MONITORAMENTO').sum()}")
        print(f"  Vencimentos:       {len(vencs)} → {vencs[:4]}")

        print(f"\n  Distribuição por ativo objeto:")
        for ativo in sorted(df["ativo_objeto"].unique()):
            sub   = df[df["ativo_objeto"] == ativo]
            opp   = int((sub["categoria"] == "OPORTUNIDADE").sum())
            mon   = int((sub["categoria"] == "MONITORAMENTO").sum())
            tot   = len(sub)
            icon  = "🟢" if opp > 0 else ("🟡" if mon > 0 else "⚪")
            max_adv = sub["adv_volume"].max() / 1e6
            print(f"    {icon} {ativo:<6} tot={tot:>2}  "
                  f"opp={opp:>2}  mon={mon:>2}  ADV_max=R${max_adv:.1f}M")

    if not diag.empty:
        sem = diag[diag["status"].str.startswith("SEM")]
        if len(sem) > 0:
            print(f"\n  Ativos sem opções elegíveis ({len(sem)}):")
            for _, r in sem.iterrows():
                print(f"    ❌ {r['ativo']:6}  {r['status']}")

        cand = diag[diag["status"].str.startswith("OK") &
                    diag["na_shortlist"].lt(diag["limite"]) &
                    diag["na_shortlist"].gt(0)]
        if len(cand) > 0:
            print(f"\n  Ativos com opções mas limite não preenchido ({len(cand)}):")
            for _, r in cand.iterrows():
                print(f"    ⚠️  {r['ativo']:6}  {r['status']}")

    print(f"{'='*70}\n")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Shortlist diversificada de opções para RTD")
    ap.add_argument("--top",  type=int, default=TOTAL_MAX)
    ap.add_argument("--db",   type=str, default=str(DB_PATH))
    args = ap.parse_args()

    print(f"[builder] Banco: {args.db}")
    conn = sqlite3.connect(args.db)

    total_rows = conn.execute(
        "SELECT COUNT(*) FROM cotahist_daily"
    ).fetchone()[0] or 0
    if total_rows == 0:
        print("⚠️  cotahist_daily vazia. Execute o coletor COTAHIST primeiro.")
        conn.close()
        return
    print(f"[builder] cotahist_daily: {total_rows:,} linhas · "
          f"Ativos monitorados: {len(ATIVOS_OBJETO)}")

    # Load spots
    spots = _load_spots(conn)
    print(f"[builder] Spots: {len(spots)} → {', '.join(sorted(spots.keys()))[:60]}")

    # Load options (batch query ~7.5s)
    print("[builder] Query batch (~7s) ...")
    df_raw, vencs = _load_options(conn, spots)
    print(f"[builder] Opções candidatas: {len(df_raw)}")

    # Diversify
    df_div = _diversify(df_raw, total_max=args.top) if not df_raw.empty else pd.DataFrame()
    print(f"[builder] Shortlist final: {len(df_div)} opções (máx {args.top})")

    # Diagnostic inline
    diag = _build_diagnostic(df_raw, spots, df_div)
    conn.close()

    _print_summary(df_div, diag, vencs)

    # Save outputs
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not df_div.empty:
        df_out = _format_watchlist(df_div)

        watchlist_path = OUT_DIR / "options_rtd_watchlist.csv"
        df_out.to_csv(watchlist_path, index=False)
        print(f"  ✅ {watchlist_path.name}  ({len(df_out)} options)")

        symbols_path = OUT_DIR / "options_rtd_symbols.csv"
        df_out[["ticker","ativo_objeto","tipo","strike","vencimento","prioridade"]].to_csv(
            symbols_path, index=False
        )
        print(f"  ✅ {symbols_path.name}  ({len(df_out)} tickers)")
    else:
        watchlist_path = OUT_DIR / "options_rtd_watchlist.csv"
        watchlist_path.write_text(
            "ticker,ativo_objeto,tipo,strike,vencimento,"
            "ultimo_preco,spot,moneyness,adv_volume,"
            "negocios_media,prioridade,categoria\n"
        )
        print("  ⚠️  options_rtd_watchlist.csv  (vazio)")

    diag_path = OUT_DIR / "options_rtd_diagnostic.csv"
    diag.to_csv(diag_path, index=False)
    print(f"  ✅ {diag_path.name}  ({len(diag)} ativos verificados)")


if __name__ == "__main__":
    main()