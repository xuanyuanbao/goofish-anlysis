from __future__ import annotations

import argparse
from datetime import date

from config.settings import load_settings
from db.database import Database
from pipeline import run_monthly_pipeline
from utils.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the monthly Xianyu trend report.")
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"), help="目标月份，格式 YYYY-MM")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, "monthly")
    database = Database(settings.sqlite_db_path, settings.project_root)
    database.initialize()
    year, month = [int(part) for part in args.month.split("-", 1)]
    result = run_monthly_pipeline(settings, database, year, month)
    logger.info("Monthly pipeline finished: %s", result)
    print(result)


if __name__ == "__main__":
    main()
