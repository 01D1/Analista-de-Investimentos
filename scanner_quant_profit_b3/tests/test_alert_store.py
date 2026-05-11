import pandas as pd

from src.db.init_db import init_database
from src.notifications.alert_store import load_open_alerts, resolve_alert, save_alerts


def test_save_load_and_resolve_alerts(tmp_path):
    db_path = tmp_path / "scanner.db"
    init_database(db_path, verbose=False)
    alerts = pd.DataFrame(
        [
            {
                "created_at": "2026-01-01T10:00:00",
                "alert_type": "SOURCE_MISSING",
                "severity": "CRITICAL",
                "title": "Fonte ausente",
                "message": "missing",
                "source": "news_hunter",
                "metadata_json": "{}",
            }
        ]
    )

    saved = save_alerts(db_path, alerts)
    open_alerts = load_open_alerts(db_path)
    resolved = resolve_alert(db_path, int(open_alerts.loc[0, "id"]))

    assert saved == 1
    assert len(open_alerts) == 1
    assert resolved is True
    assert load_open_alerts(db_path).empty
