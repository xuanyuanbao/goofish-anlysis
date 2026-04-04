from __future__ import annotations

import argparse
from datetime import date, timedelta

from config.settings import load_settings
from db.database import create_database
from pipeline import run_daily_pipeline, seed_keywords_if_needed
from utils.logging_utils import configure_error_logger, configure_logging
from utils.time_utils import shanghai_today


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily Xianyu trend pipeline.")
    parser.add_argument("--date", default=shanghai_today().isoformat(), help="统计日期，格式 YYYY-MM-DD")
    parser.add_argument(
        "--mode",
        choices=("full", "crawl", "report"),
        default="full",
        help="full=采集+统计+导出，crawl=仅采集，report=基于已有快照生成报表",
    )
    parser.add_argument("--backfill-days", type=int, default=1, help="回补天数，默认 1")
    parser.add_argument("--limit", type=int, default=None, help="每个关键词采集条数上限")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, "daily")
    error_logger = configure_error_logger(settings.log_dir)
    database = create_database(settings)
    database.initialize()
    seeded = seed_keywords_if_needed(database, settings)
    if seeded:
        logger.info("Seeded %s keywords from fixtures/keywords.csv", seeded)

    target_date = date.fromisoformat(args.date)
    limit = args.limit or settings.default_limit
    backfill_days = max(1, args.backfill_days)

    try:
        for offset in range(backfill_days):
            snapshot_date = target_date - timedelta(days=backfill_days - offset - 1)
            result = run_daily_pipeline(
                settings=settings,
                database=database,
                snapshot_date=snapshot_date,
                mode=args.mode,
                limit=limit,
                task_logger=logger,
                error_logger=error_logger,
            )
            logger.info("Daily pipeline finished: %s", result)
            print(result)
    except Exception:
        error_logger.exception(
            "Daily pipeline crashed: date=%s mode=%s backfill_days=%s",
            args.date,
            args.mode,
            backfill_days,
        )
        raise


if __name__ == "__main__":
    main()
