from __future__ import annotations

import argparse
import json
import uuid
from datetime import date, datetime, timedelta

from config.settings import load_settings
from db.base import BaseDatabase
from db.database import create_database
from models import JobRunRecord
from pipeline import (
    run_daily_pipeline,
    run_monthly_pipeline,
    run_weekly_pipeline,
    seed_keywords_if_needed,
)
from utils.logging_utils import (
    configure_alert_logger,
    configure_error_logger,
    configure_logging,
)
from utils.time_utils import shanghai_month_label, shanghai_now, shanghai_today


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
        default=shanghai_today().isoformat(),
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
        default=shanghai_today().isoformat(),
        help="Reference date in YYYY-MM-DD format.",
    )

    monthly_parser = subparsers.add_parser(
        "monthly",
        help="Generate the monthly report.",
    )
    monthly_parser.add_argument(
        "--month",
        default=shanghai_month_label(),
        help="Target month in YYYY-MM format.",
    )

    return parser


def bootstrap_runtime(log_name: str) -> tuple[object, BaseDatabase, object, object, object]:
    settings = load_settings()
    settings.ensure_directories()
    logger = configure_logging(settings.log_dir, log_name)
    error_logger = configure_error_logger(settings.log_dir)
    alert_logger = configure_alert_logger(settings.log_dir)
    database = create_database(settings)
    database.initialize()
    seeded = seed_keywords_if_needed(database, settings)
    if seeded:
        logger.info("Seeded %s keywords from fixtures/keywords.csv", seeded)
    return settings, database, logger, error_logger, alert_logger


def run_daily(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger, alert_logger = bootstrap_runtime("daily")
    target_date = date.fromisoformat(args.date)
    limit = args.limit or settings.default_limit
    backfill_days = max(1, args.backfill_days)

    for offset in range(backfill_days):
        snapshot_date = target_date - timedelta(days=backfill_days - offset - 1)
        started_at = shanghai_now()
        run_id = _make_run_id("daily", snapshot_date.isoformat())
        try:
            snapshot_date = target_date - timedelta(days=backfill_days - offset - 1)
            result = run_daily_pipeline(
                settings=settings,
                database=database,
                snapshot_date=snapshot_date,
                mode=args.mode,
                limit=limit,
                run_id=run_id,
                task_logger=logger,
                error_logger=error_logger,
                alert_logger=alert_logger,
            )
            database.record_job_run(
                _build_job_run_record(
                    run_id=run_id,
                    job_name="daily",
                    run_mode=args.mode,
                    target_label=snapshot_date.isoformat(),
                    snapshot_date=snapshot_date,
                    started_at=started_at,
                    result=result,
                    status="success",
                )
            )
            logger.info("Daily pipeline finished: %s", result)
            print(result)
        except Exception as exc:
            database.record_job_run(
                _build_job_run_record(
                    run_id=run_id,
                    job_name="daily",
                    run_mode=args.mode,
                    target_label=snapshot_date.isoformat(),
                    snapshot_date=snapshot_date,
                    started_at=started_at,
                    result={},
                    status="failed",
                    error_message=str(exc),
                )
            )
            alert_logger.error(
                "daily | %s | job failed: %s",
                snapshot_date.isoformat(),
                exc,
            )
            error_logger.exception(
                "Daily pipeline crashed: date=%s mode=%s backfill_days=%s",
                args.date,
                args.mode,
                backfill_days,
            )
            raise


def run_weekly(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger, alert_logger = bootstrap_runtime("weekly")
    started_at = shanghai_now()
    target_label = date.fromisoformat(args.date).isoformat()
    run_id = _make_run_id("weekly", target_label)
    try:
        result = run_weekly_pipeline(settings, database, date.fromisoformat(args.date))
        database.record_job_run(
            _build_job_run_record(
                run_id=run_id,
                job_name="weekly",
                run_mode="report",
                target_label=target_label,
                snapshot_date=None,
                started_at=started_at,
                result=result,
                status="success",
            )
        )
        if result.get("alert_message"):
            alert_logger.warning("weekly | %s", result["alert_message"])
        logger.info("Weekly pipeline finished: %s", result)
        print(result)
    except Exception as exc:
        database.record_job_run(
            _build_job_run_record(
                run_id=run_id,
                job_name="weekly",
                run_mode="report",
                target_label=target_label,
                snapshot_date=None,
                started_at=started_at,
                result={},
                status="failed",
                error_message=str(exc),
            )
        )
        alert_logger.error("weekly | %s", exc)
        error_logger.exception("Weekly pipeline crashed: date=%s", args.date)
        raise


def run_monthly(args: argparse.Namespace) -> None:
    settings, database, logger, error_logger, alert_logger = bootstrap_runtime("monthly")
    year, month = [int(part) for part in args.month.split("-", 1)]
    started_at = shanghai_now()
    run_id = _make_run_id("monthly", args.month)
    try:
        result = run_monthly_pipeline(settings, database, year, month)
        database.record_job_run(
            _build_job_run_record(
                run_id=run_id,
                job_name="monthly",
                run_mode="report",
                target_label=args.month,
                snapshot_date=None,
                started_at=started_at,
                result=result,
                status="success",
            )
        )
        if result.get("alert_message"):
            alert_logger.warning("monthly | %s", result["alert_message"])
        logger.info("Monthly pipeline finished: %s", result)
        print(result)
    except Exception as exc:
        database.record_job_run(
            _build_job_run_record(
                run_id=run_id,
                job_name="monthly",
                run_mode="report",
                target_label=args.month,
                snapshot_date=None,
                started_at=started_at,
                result={},
                status="failed",
                error_message=str(exc),
            )
        )
        alert_logger.error("monthly | %s", exc)
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


def _make_run_id(job_name: str, target_label: str) -> str:
    timestamp = shanghai_now().strftime("%Y%m%d%H%M%S")
    return f"{job_name}-{target_label}-{timestamp}-{uuid.uuid4().hex[:8]}"


def _build_job_run_record(
    *,
    run_id: str,
    job_name: str,
    run_mode: str,
    target_label: str | None,
    snapshot_date: date | None,
    started_at: datetime,
    result: dict[str, object],
    status: str,
    error_message: str | None = None,
) -> JobRunRecord:
    finished_at = shanghai_now()
    metadata = dict(result)
    alert_level = str(metadata.pop("alert_level", "error" if status == "failed" else "info"))
    alert_message = error_message or metadata.pop("alert_message", None)
    report_paths = metadata.pop("report_paths", [])
    return JobRunRecord(
        run_id=run_id,
        job_name=job_name,
        run_mode=run_mode,
        run_status=status,
        target_label=target_label,
        snapshot_date=snapshot_date,
        started_at=started_at,
        finished_at=finished_at,
        keyword_total=int(result.get("keyword_total") or 0),
        keyword_success=int(result.get("keyword_success") or 0),
        keyword_failed=int(result.get("keyword_failed") or 0),
        inserted_snapshots=int(result.get("inserted_snapshots") or 0),
        daily_stats=int(result.get("daily_stats") or 0),
        item_scores=int(result.get("item_scores") or 0),
        alert_level=alert_level,
        alert_message=str(alert_message) if alert_message else None,
        report_paths=[str(path) for path in report_paths] if isinstance(report_paths, list) else [],
        metadata_json=json.dumps(metadata, ensure_ascii=False),
    )


if __name__ == "__main__":
    main()
