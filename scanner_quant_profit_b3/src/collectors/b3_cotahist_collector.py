import argparse
import sqlite3
import zipfile
from pathlib import Path
from urllib.request import urlretrieve
import pandas as pd

from src.utils import load_config, project_path

def cotahist_url(year):
    return f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"

def download_cotahist(year, raw_dir):
    import requests

    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / f"COTAHIST_A{year}.ZIP"

    if zip_path.exists() and zip_path.stat().st_size > 0:
        print(f"Arquivo já existe: {zip_path}")
        return zip_path

    url = cotahist_url(year)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/zip,application/octet-stream,*/*",
        "Referer": "https://www.b3.com.br/"
    }

    print(f"Baixando {url}")
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    with open(zip_path, "wb") as f:
        f.write(response.content)

    print(f"Salvo em: {zip_path}")
    return zip_path

def extract_txt(zip_path, raw_dir):
    with zipfile.ZipFile(zip_path, "r") as z:
        txts = [n for n in z.namelist() if n.upper().endswith(".TXT")]
        if not txts:
            raise ValueError(f"Nenhum TXT encontrado em {zip_path}")
        member = txts[0]
        out_path = raw_dir / Path(member).name
        if not out_path.exists():
            z.extract(member, raw_dir)
        return out_path

def parse_price(value):
    value = str(value).strip()
    if not value:
        return None
    return int(value) / 100

def parse_int(value):
    value = str(value).strip()
    if not value:
        return None
    return int(value)

def parse_cotahist_txt(txt_path, ativos_base=None):
    ativos_base = set(ativos_base or [])
    rows = []
    with open(txt_path, "r", encoding="latin-1") as f:
        for line in f:
            if not line.startswith("01"):
                continue

            trade_date = line[2:10]
            ticker = line[12:24].strip()
            market_type = int(line[24:27])
            company_name = line[27:39].strip()

            if ativos_base:
                is_stock_base = ticker in ativos_base
                is_related_option = any(ticker.startswith(a[:4]) for a in ativos_base)
                if not (is_stock_base or is_related_option):
                    continue

            row = {
                "trade_date": f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}",
                "ticker": ticker,
                "market_type": market_type,
                "company_name": company_name,
                "open": parse_price(line[56:69]),
                "high": parse_price(line[69:82]),
                "low": parse_price(line[82:95]),
                "average": parse_price(line[95:108]),
                "close": parse_price(line[108:121]),
                "best_bid": parse_price(line[121:134]),
                "best_ask": parse_price(line[134:147]),
                "trades": parse_int(line[147:152]),
                "quantity": parse_int(line[152:170]),
                "volume": parse_price(line[170:188]),
                "option_exercise_price": parse_price(line[188:201]),
                "option_maturity": line[202:210].strip(),
            }

            if market_type == 10:
                row["asset_type"] = "ACAO"
            elif market_type == 70:
                row["asset_type"] = "CALL"
            elif market_type == 80:
                row["asset_type"] = "PUT"
            else:
                row["asset_type"] = "OUTRO"

            rows.append(row)

    return pd.DataFrame(rows)

def save_b3_quotes(df, db_path):
    if df is None or df.empty:
        print("Nenhum dado para salvar.")
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    df.to_sql("b3_quotes", con, if_exists="append", index=False)
    con.close()
    print(f"{len(df)} linhas salvas em b3_quotes.")

def process_year(year, cfg, only_download=False):
    raw_dir = project_path(cfg["b3"]["raw_dir"])
    db_path = project_path(cfg["database_path"])
    zip_path = download_cotahist(year, raw_dir)
    txt_path = extract_txt(zip_path, raw_dir)

    if only_download:
        return

    ativos_base = cfg.get("ativos_base", [])
    df = parse_cotahist_txt(txt_path, ativos_base=ativos_base)
    print(df.head(10).to_string(index=False))
    save_b3_quotes(df, db_path)

def main():
    parser = argparse.ArgumentParser(description="Coletor automático B3 COTAHIST.")
    parser.add_argument("--year", type=int, default=None, help="Ano específico. Ex.: 2026")
    parser.add_argument("--all", action="store_true", help="Processa todos os anos do config.yaml.")
    parser.add_argument("--download-only", action="store_true", help="Apenas baixa e extrai o arquivo.")
    args = parser.parse_args()

    cfg = load_config()
    years = cfg.get("b3", {}).get("years", [])
    if args.year:
        years = [args.year]
    if not args.all and not args.year:
        raise SystemExit("Informe --year 2026 ou --all")

    for y in years:
        process_year(int(y), cfg, only_download=args.download_only)

if __name__ == "__main__":
    main()
