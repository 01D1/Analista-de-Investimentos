"""CLI para importar eventos de mercado a partir de CSV local."""
from __future__ import annotations

import argparse

from src.context.event_importer import load_events_from_csv, save_events_to_db
from src.utils import load_config, project_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa eventos/notícias locais para market_events.")
    parser.add_argument("--csv", required=True, help="Caminho do CSV de eventos.")
    parser.add_argument("--save-db", action="store_true", help="Salva os eventos no SQLite.")
    args = parser.parse_args()

    events = load_events_from_csv(args.csv)
    print(f"Eventos carregados: {len(events)}")
    if not events.empty:
        print(events[["event_date", "ticker", "event_type", "impact_direction", "event_title"]].head(10).to_string(index=False))
    if args.save_db:
        cfg = load_config()
        db_path = project_path(cfg["database_path"])
        saved = save_events_to_db(events, db_path)
        print(f"Eventos salvos no banco: {saved}")
    else:
        print("Use --save-db para persistir em market_events.")


if __name__ == "__main__":
    main()
