import argparse
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.utils import load_config, project_path


def price(s: str):
    try:
        return int(s) / 100.0
    except Exception:
        return None


def date_fmt(s: str):
    try:
        return datetime.strptime(s, "%Y%m%d").date().isoformat()
    except Exception:
        return None


def parse_line(line: str, source_year: int):
    if line[:2] != "01":
        return None
    tpmerc = line[24:27]
    option_type = None
    if tpmerc == "070": option_type = "CALL"
    if tpmerc == "080": option_type = "PUT"

    return {
        "trade_date": date_fmt(line[2:10]),
        "ticker": line[12:24].strip(),
        "market_type": tpmerc,
        "bdi_code": line[10:12].strip(),
        "company_name": line[27:39].strip(),
        "specification": line[39:49].strip(),
        "term_days": line[49:52].strip(),
        "open": price(line[56:69]),
        "high": price(line[69:82]),
        "low": price(line[82:95]),
        "average": price(line[95:108]),
        "close": price(line[108:121]),
        "best_bid": price(line[121:134]),
        "best_ask": price(line[134:147]),
        "trades": int(line[147:152]),
        "quantity": int(line[152:170]),
        "volume": price(line[170:188]),
        "strike": price(line[188:201]),
        "option_type": option_type,
        "expiration_date": date_fmt(line[202:210]),
        "source_year": source_year,
    }


def find_zip(raw_dir: Path, year: int) -> Path:
    candidates = list(raw_dir.glob(f"*{year}*.ZIP")) + list(raw_dir.glob(f"*{year}*.zip"))
    if not candidates:
        raise FileNotFoundError(f"Nenhum ZIP do COTAHIST {year} encontrado em {raw_dir}")
    return candidates[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()

    cfg = load_config()
    raw_dir = project_path(cfg["b3"]["raw_dir"])
    db_path = project_path(cfg["database_path"])
    zip_path = find_zip(raw_dir, args.year)

    rows = []
    with zipfile.ZipFile(zip_path) as z:
        txt_name = [n for n in z.namelist() if n.upper().endswith(".TXT")][0]
        with z.open(txt_name) as f:
            for b in f:
                line = b.decode("latin1")
                item = parse_line(line, args.year)
                if item:
                    rows.append(item)

    df = pd.DataFrame(rows)
    con = sqlite3.connect(db_path)
    df.to_sql("cotahist_daily", con, if_exists="append", index=False)
    con.close()
    print(f"Importadas {len(df):,} linhas do COTAHIST {args.year}".replace(",", "."))


if __name__ == "__main__":
    main()
