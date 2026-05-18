import argparse
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import requests
from src.utils import load_config, project_path

from datetime import datetime, timedelta



def cotahist_daily_url(date_str: str) -> str:
    return (
        "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
        f"COTAHIST_D{date_str}.ZIP"
    )

def cotahist_url(year):
    return f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"

def download_cotahist(year, raw_dir):
    import requests

    raw_dir.mkdir(parents=True, exist_ok=True)
    annual_path = raw_dir / f"COTAHIST_A{year}.ZIP"
    daily_files = sorted(raw_dir.glob("COTAHIST_D*.ZIP"))
    if daily_files:
        zip_path = daily_files[-1]
    else:
        zip_path = annual_path

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

def process_daily_file(date_str: str, cfg):
    """Processa um arquivo diário específico (ex: '01012026')"""
    raw_dir = project_path(cfg["b3"]["raw_dir"])
    db_path = project_path(cfg["database_path"])
    ativos_base = cfg.get("ativos_base", [])
    
    zip_path = raw_dir / f"COTAHIST_D{date_str}.ZIP"
    if not zip_path.exists():
        print(f"Arquivo não encontrado: {zip_path}")
        return
    
    txt_path = extract_txt(zip_path, project_path("data/processed"))
    df = parse_cotahist_txt(txt_path, source_year=2026, ativos_base=ativos_base)
    save_cotahist_daily(df, db_path, source_year=2026)

def extract_txt(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        txts = [n for n in z.namelist() if n.upper().endswith(".TXT")]
        if not txts:
            raise ValueError(f"Nenhum TXT encontrado em {zip_path}")
        member = txts[0]
        out_path = extract_dir / Path(member).name
        if not out_path.exists():
            z.extract(member, extract_dir)
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

def parse_date(value):
    value = str(value).strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date().isoformat()
    except ValueError:
        return None

def parse_cotahist_txt(txt_path, source_year, ativos_base=None):
    ativos_base = set(ativos_base or [])
    rows = []
    with open(txt_path, "r", encoding="latin-1") as f:
        for line in f:
            if not line.startswith("01"):
                continue

            trade_date = line[2:10]
            ticker = line[12:24].strip()
            market_type = line[24:27].strip()
            company_name = line[27:39].strip()

            if ativos_base:
                is_stock_base = ticker in ativos_base
                is_related_option = any(ticker.startswith(a[:4]) for a in ativos_base)
                if not (is_stock_base or is_related_option):
                    continue

            row = {
                "trade_date": parse_date(trade_date),
                "ticker": ticker,
                "market_type": market_type,
                "bdi_code": line[10:12].strip(),
                "company_name": company_name,
                "specification": line[39:49].strip(),
                "term_days": line[49:52].strip(),
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
                "strike": parse_price(line[188:201]),
                "expiration_date": parse_date(line[202:210]),
                "source_year": source_year,
            }

            if market_type == "070":
                row["option_type"] = "CALL"
            elif market_type == "080":
                row["option_type"] = "PUT"
            else:
                row["option_type"] = None

            rows.append(row)

    return pd.DataFrame(rows)

def save_cotahist_daily(df, db_path, source_year):
    if df is None or df.empty:
        print("Nenhum dado para salvar.")
        return
    if df.duplicated(subset=["trade_date", "ticker", "market_type"]).any():
        dup_count = int(df.duplicated(subset=["trade_date", "ticker", "market_type"]).sum())
        print(f"Aviso: {dup_count} linhas duplicadas por (trade_date, ticker, market_type) serão removidas antes de salvar.")
        df = df.drop_duplicates(subset=["trade_date", "ticker", "market_type"], keep="last")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM cotahist_daily WHERE source_year = ?", (source_year,))
        df.to_sql("cotahist_daily", con, if_exists="append", index=False)
        con.commit()
    finally:
        con.close()
    print(f"{len(df)} linhas salvas em cotahist_daily.")

def process_year(year, cfg, only_download=False):
    raw_dir = project_path(cfg["b3"]["raw_dir"])
    db_path = project_path(cfg["database_path"])
    zip_path = download_cotahist(year, raw_dir)
    txt_path = extract_txt(zip_path, raw_dir)

    if only_download:
        return

    ativos_base = cfg.get("ativos_base", [])
    df = parse_cotahist_txt(txt_path, source_year=year, ativos_base=ativos_base)
    print(df.head(10).to_string(index=False))
    save_cotahist_daily(df, db_path, source_year=year)


def process_daily_zip(zip_path: Path, db_path: Path):
    import zipfile

    processed_dir = project_path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processando diário: {zip_path.name}")

    with zipfile.ZipFile(zip_path, "r") as z:
        txt_files = [n for n in z.namelist() if n.upper().endswith(".TXT")]

        if not txt_files:
            print(f"Nenhum TXT encontrado dentro de {zip_path.name}")
            return

        txt_name = txt_files[0]

        # Extrai para data/processed
        z.extract(txt_name, processed_dir)

        txt_path = processed_dir / txt_name

    print(f"TXT extraído: {txt_path}")

    df = parse_cotahist_txt(txt_path, source_year=2026)

    if df is None or df.empty:
        print("Nenhum dado no diário.")
        return

    df = df.drop_duplicates(
        subset=["trade_date", "ticker", "market_type"],
        keep="last"
    )

    dates = df["trade_date"].dropna().unique().tolist()

    con = sqlite3.connect(db_path)

    try:

        for dt in dates:
            con.execute(
                "DELETE FROM cotahist_daily WHERE trade_date = ?",
                (dt,)
            )

        df.to_sql(
            "cotahist_daily",
            con,
            if_exists="append",
            index=False
        )

        con.commit()

    finally:
        con.close()

    print(f"{len(df)} linhas adicionadas/atualizadas em cotahist_daily.")


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Coletor automático B3 COTAHIST.")
    parser.add_argument("--daily", type=str, default=None, help="Processa um diário específico. Ex: --daily 01012026")
    parser.add_argument("--year", type=int, default=None, help="Ano específico. Ex.: 2026")
    parser.add_argument("--all", action="store_true", help="Processa todos os anos do config.yaml.")
    parser.add_argument("--download-only", action="store_true", help="Apenas baixa e extrai o arquivo.")
    parser.add_argument(
        "--daily-history",
        action="store_true",
        help="Baixa histórico diário da B3"
    )
    args = parser.parse_args()
    if args.daily_history:

        raw_dir = project_path("data/raw")
        db_path = project_path(cfg["database_path"])
        
        download_daily_history(raw_dir, db_path)

        print("Download diário concluído.")
        raise SystemExit
    if args.daily:
        process_daily_file(args.daily, cfg)
        raise SystemExit


    cfg = load_config()
    years = cfg.get("b3", {}).get("years", [])
    if args.year:
        years = [args.year]
    if not args.all and not args.year:
        raise SystemExit("Informe --year 2026 ou --all")

    for y in years:
        process_year(int(y), cfg, only_download=args.download_only)

def download_daily_history(raw_dir, db_path: Path):

    start = datetime(2026, 1, 1)
    end = datetime.today()

    cur = start

    while cur <= end:

        ds = cur.strftime("%d%m%Y")

        filename = f"COTAHIST_D{ds}.ZIP"

        zip_path = raw_dir / filename

        if zip_path.exists():
            print(f"Já existe: {filename}")

            process_daily_zip(zip_path, db_path)

            cur += timedelta(days=1)
            continue

        url = (
            "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
            f"{filename}"
        )

        try:

            print(f"Baixando {filename}...")

            r = requests.get(url, timeout=30)

            if r.status_code == 200:

                zip_path.write_bytes(r.content)

                process_daily_zip(zip_path, db_path)

                print(f"OK: {filename}")

            else:
                print(f"Não encontrado: {filename}")

        except Exception as e:

            print(f"Erro em {filename}: {e}")

        cur += timedelta(days=1)

if __name__ == "__main__":
    main()
