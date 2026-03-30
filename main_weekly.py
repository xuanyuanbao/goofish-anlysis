from __future__ import annotations

import argparse
from datetime import date

from config.settings import load_settings
from db.database import Database
from pipeline import run_weekly_pipeline
from utils.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run weekly xianyu trend report.")
    parser.add_argument("--date", default=date.today().isoformat(), help="参考日期，格式 YYYY-MM-DD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, "weekly")
    database = Database(settings.sqlite_db_path, settings.project_root)
    database.initialize()
    result = run_weekly_pipeline(settings, database, date.fromisoformat(args.date))
    logger.info("Weekly pipeline finished: %s", result)
    print(result)


if __name__ == "__main__":
    main()
