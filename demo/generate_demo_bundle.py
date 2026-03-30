from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_settings
from db.database import create_database
from pipeline import (
    run_daily_pipeline,
    run_monthly_pipeline,
    run_weekly_pipeline,
    seed_keywords_if_needed,
)
from utils.logging_utils import configure_logging


DEMO_ROOT = PROJECT_ROOT / "demo" / "generated"
DEMO_DATE = date(2026, 3, 30)
BACKFILL_DAYS = 40


def main() -> None:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)

    os.environ["XY_DATA_DIR"] = str(DEMO_ROOT / "data")
    os.environ["XY_REPORT_DIR"] = str(DEMO_ROOT / "reports")
    os.environ["XY_LOG_DIR"] = str(DEMO_ROOT / "logs")
    os.environ["XY_DB_PATH"] = str(DEMO_ROOT / "data" / "xianyu_demo.db")
    os.environ["XY_CRAWLER_MODE"] = "fixture"

    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, "demo")
    database = create_database(settings)
    database.initialize()

    seeded = seed_keywords_if_needed(database, settings)
    if seeded:
        logger.info("Seeded %s keywords for demo bundle", seeded)

    for offset in range(BACKFILL_DAYS):
        snapshot_date = DEMO_DATE - timedelta(days=BACKFILL_DAYS - offset - 1)
        result = run_daily_pipeline(
            settings=settings,
            database=database,
            snapshot_date=snapshot_date,
            mode="full",
            limit=12,
        )
        logger.info("Demo daily pipeline finished: %s", result)

    weekly_result = run_weekly_pipeline(settings, database, DEMO_DATE)
    monthly_result = run_monthly_pipeline(settings, database, DEMO_DATE.year, DEMO_DATE.month)
    logger.info("Demo weekly pipeline finished: %s", weekly_result)
    logger.info("Demo monthly pipeline finished: %s", monthly_result)

    _trim_daily_reports(settings.daily_report_dir, DEMO_DATE.isoformat())

    manifest = {
        "demo_date": DEMO_DATE.isoformat(),
        "backfill_days": BACKFILL_DAYS,
        "daily_reports_kept": DEMO_DATE.isoformat(),
        "weekly": weekly_result,
        "monthly": monthly_result,
    }
    manifest_path = DEMO_ROOT / "demo_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def _trim_daily_reports(report_dir: Path, date_label: str) -> None:
    for path in report_dir.glob("*"):
        if date_label not in path.name:
            path.unlink()


if __name__ == "__main__":
    main()
