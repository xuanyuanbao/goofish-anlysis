from __future__ import annotations

import argparse
from datetime import date, timedelta

from config.settings import load_settings
from db.base import BaseDatabase
from db.database import create_database
from pipeline import (
    run_daily_pipeline,
    run_monthly_pipeline,
    run_weekly_pipeline,
    seed_keywords_if_needed,
)
from utils.logging_utils import configure_error_logger, configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified launcher for daily, weekly, and monthly Xianyu report jobs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily_parser = subparsers.add_parser(
        "daily",
        help="Run the daily crawl/report pipeline.",
    )
    daily_parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Target date in YYYY-MM-DD format.",
    )
    daily_parser.add_argument(
        "--mode",
        choices=("full", "crawl", "report"),
        default="full",
        help="full=crawl+report, crawl=only collect snapshots, report=build reports from existing snapshots.",
    )
    daily_parser.add_argument(
        "--backfill-days",
        type=int,
        default=1,
        help="Number of days to backfill, counting backwards from --date.",
    )
    daily_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of items to collect for each keyword.",
    )

    weekly_parser = subparsers.add_parser(
        "weekly",
        help="Generate the weekly report.",
    )
    weekly_parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Reference date in YYYY-MM-DD format.",
    )

    monthly_parser = subparsers.add_parser(
        "monthly",
        help="Generate the monthly report.",
    )
    monthly_parser.add_argument(
        "--month",
        default=date.today().strftime("%Y-%m"),
        help="Target month in YYYY-MM format.",
    )

    return parser


def bootstrap_runtime(log_name: str) -> tuple[object, BaseDatabase, object, object]:
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, log_name)
    error_logger = configure_error_logger(settings.log_dir)
    database = create_database(settings)
    database.initialize()
    seeded = seed_keywords_if_needed(database, settings)
    if seeded:
        logger.info("Seeded %s keywords from fixtures/keywords.csv", seeded)
    return settings, database, logger, error_logger


def run_daily(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger = bootstrap_runtime("daily")
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


def run_weekly(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger = bootstrap_runtime("weekly")
    try:
        result = run_weekly_pipeline(settings, database, date.fromisoformat(args.date))
        logger.info("Weekly pipeline finished: %s", result)
        print(result)
    except Exception:
        error_logger.exception("Weekly pipeline crashed: date=%s", args.date)
        raise


def run_monthly(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger = bootstrap_runtime("monthly")
    year, month = [int(part) for part in args.month.split("-", 1)]
    try:
        result = run_monthly_pipeline(settings, database, year, month)
        logger.info("Monthly pipeline finished: %s", result)
        print(result)
    except Exception:
        error_logger.exception("Monthly pipeline crashed: month=%s", args.month)
        raise


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "daily":
        run_daily(args)
        return
    if args.command == "weekly":
        run_weekly(args)
        return
    run_monthly(args)


if __name__ == "__main__":
    main()
