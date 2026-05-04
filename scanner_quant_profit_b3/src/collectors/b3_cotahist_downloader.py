import argparse
from pathlib import Path
import requests
from src.utils import load_config, project_path


def download_cotahist(year: int, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / f"COTAHIST_A{year}.ZIP"
    url = f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    out.write_bytes(r.content)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()

    cfg = load_config()
    raw_dir = project_path(cfg["b3"]["raw_dir"])
    try:
        path = download_cotahist(args.year, raw_dir)
        print(f"Arquivo baixado: {path}")
    except Exception as e:
        print("Não foi possível baixar automaticamente.")
        print("Baixe manualmente o COTAHIST no site da B3 e coloque o ZIP em data/raw.")
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
