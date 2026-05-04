import sqlite3
import time
from datetime import datetime
from typing import Any

import pandas as pd

from src.utils import load_config, project_path


def _to_float(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.replace("R$", "").replace("%", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(value)
    except Exception:
        return None


def _to_int(value: Any):
    x = _to_float(value)
    return int(x) if x is not None else None


def read_profit_excel(path: str, sheet_name: str) -> pd.DataFrame:
    """
    Lê a planilha aberta pelo Excel.
    Preferência: xlwings, porque preserva os valores em tempo real do RTD/DDE.
    Fallback: openpyxl, apenas para arquivo salvo em disco.
    """
    try:
        import xlwings as xw
        wb = xw.Book(path)
        sht = wb.sheets[sheet_name]
        data = sht.range("A1").expand().value
        df = pd.DataFrame(data[1:], columns=data[0])
    except Exception:
        df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_profit_df(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "Asset": "asset",
        "Data": "trade_date",
        "Hora": "trade_time",
        "Último": "last",
        "Abertura": "open",
        "Máximo": "high",
        "Mínimo": "low",
        "Fechamento Anterior": "prev_close",
        "Variação": "variation_pct",
        "Variação(pts)": "variation_pts",
        "Negócios": "trades",
        "Quantidade": "quantity",
        "Volume": "volume",
    }
    cols = [c for c in rename if c in df.columns]
    out = df[cols].rename(columns=rename).copy()
    out = out[out["asset"].notna()]
    out["captured_at"] = datetime.now().isoformat(timespec="seconds")

    for col in ["last", "open", "high", "low", "prev_close", "variation_pct", "variation_pts", "quantity", "volume"]:
        if col in out.columns:
            out[col] = out[col].apply(_to_float)
    if "trades" in out.columns:
        out["trades"] = out["trades"].apply(_to_int)

    expected = ["captured_at", "asset", "trade_date", "trade_time", "last", "open", "high", "low", "prev_close", "variation_pct", "variation_pts", "trades", "quantity", "volume"]
    for col in expected:
        if col not in out.columns:
            out[col] = None
    return out[expected]


def save_snapshots(df: pd.DataFrame, db_path: str):
    con = sqlite3.connect(db_path)
    df.to_sql("profit_snapshots", con, if_exists="append", index=False)
    con.close()


def main():
    cfg = load_config()
    path = cfg["profit_excel_path"]
    sheet = cfg.get("profit_sheet_name", "Planilha1")
    db_path = project_path(cfg["database_path"])
    interval = int(cfg.get("snapshot_interval_seconds", 5))

    print("Coletor iniciado. Para parar, use CTRL+C.")
    while True:
        raw = read_profit_excel(path, sheet)
        df = normalize_profit_df(raw)
        save_snapshots(df, str(db_path))
        print(f"{datetime.now().strftime('%H:%M:%S')} - {len(df)} ativos salvos")
        time.sleep(interval)


if __name__ == "__main__":
    main()
