from __future__ import annotations

import argparse
from datetime import date

from config.settings import load_settings
from db.database import create_database
from pipeline import run_weekly_pipeline
from utils.logging_utils import configure_error_logger, configure_logging
from utils.time_utils import shanghai_today


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the weekly Xianyu trend report.")
    parser.add_argument("--date", default=shanghai_today().isoformat(), help="参考日期，格式 YYYY-MM-DD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, "weekly")
    error_logger = configure_error_logger(settings.log_dir)
    database = create_database(settings)
    database.initialize()
    try:
        result = run_weekly_pipeline(settings, database, date.fromisoformat(args.date))
        logger.info("Weekly pipeline finished: %s", result)
        print(result)
    except Exception:
        error_logger.exception("Weekly pipeline crashed: date=%s", args.date)
        raise


if __name__ == "__main__":
    main()
