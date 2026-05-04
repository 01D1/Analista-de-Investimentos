import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd

COLUMN_MAP = {
    "asset": "asset",
    "ativo": "asset",
    "ticker": "asset",
    "último": "last",
    "ultimo": "last",
    "last": "last",
    "abertura": "open",
    "open": "open",
    "máximo": "high",
    "maximo": "high",
    "max": "high",
    "mínimo": "low",
    "minimo": "low",
    "min": "low",
    "fechamento anterior": "prev_close",
    "fech ant": "prev_close",
    "prev close": "prev_close",
    "variação (%)": "variation_pct",
    "variacao (%)": "variation_pct",
    "variação": "variation_pct",
    "variacao": "variation_pct",
    "variação (pts)": "variation_pts",
    "variacao (pts)": "variation_pts",
    "negócios": "trades",
    "negocios": "trades",
    "quantidade": "quantity",
    "volume": "volume",
    "volume financeiro": "volume",
    "data": "date",
    "hora": "time",
}

def _clean_col(c):
    return str(c).strip().lower()

def read_profit_excel(path, sheet_name="Planilha1"):
    path = str(path)
    try:
        import xlwings as xw
        wb = xw.Book(path)
        sht = wb.sheets[sheet_name]
        values = sht.used_range.value
        if not values or len(values) < 2:
            return pd.DataFrame()
        return pd.DataFrame(values[1:], columns=values[0])
    except Exception:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, keep_links=False)
        ws = wb[sheet_name]
        rows = list(ws.values)
        if not rows or len(rows) < 2:
            return pd.DataFrame()
        return pd.DataFrame(rows[1:], columns=rows[0])

def normalize_profit_df(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    rename = {}
    for c in df.columns:
        key = _clean_col(c)
        if key in COLUMN_MAP:
            rename[c] = COLUMN_MAP[key]
    df = df.rename(columns=rename)

    if "asset" not in df.columns:
        df = df.rename(columns={df.columns[0]: "asset"})

    wanted = ["asset", "last", "open", "high", "low", "prev_close", "variation_pct", "variation_pts", "trades", "quantity", "volume"]
    for c in wanted:
        if c not in df.columns:
            df[c] = None

    df = df[wanted].copy()
    df["asset"] = df["asset"].astype(str).str.strip()

    for c in wanted:
        if c != "asset":
            df[c] = (
                df[c].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.replace("%", "", regex=False)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[df["asset"].notna() & (df["asset"] != "") & (df["asset"].str.lower() != "none")]
    df["captured_at"] = datetime.now().isoformat(timespec="seconds")
    return df

def save_snapshots(df, db_path):
    if df is None or df.empty:
        return
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cols = ["captured_at", "asset", "last", "open", "high", "low", "prev_close", "variation_pct", "variation_pts", "trades", "quantity", "volume"]
    df[[c for c in cols if c in df.columns]].to_sql("profit_snapshots", con, if_exists="append", index=False)
    con.close()
