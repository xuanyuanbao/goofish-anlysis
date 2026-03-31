from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable

from analyzer.calc_daily_stats import calculate_daily_stats
from analyzer.calc_monthly_stats import calculate_monthly_stats
from analyzer.calc_weekly_stats import calculate_weekly_stats
from analyzer.clean_data import clean_items
from config.settings import Settings
from crawler.crawl_keywords import (
    KeywordCrawlFailure,
    build_crawler,
    crawl_keywords,
)
from db.base import BaseDatabase
from exporter.export_csv import export_csv
from exporter.export_excel import export_excel_workbook
from models import CrawledItem, DailyItemScore, DailyKeywordStat, KeywordRecord


def seed_keywords_if_needed(database: BaseDatabase, settings: Settings) -> int:
    return database.seed_keywords_from_csv(settings.fixture_dir / "keywords.csv")


def run_daily_pipeline(
    settings: Settings,
    database: BaseDatabase,
    snapshot_date: date,
    mode: str,
    limit: int,
    task_logger: logging.Logger | None = None,
    error_logger: logging.Logger | None = None,
) -> dict[str, int | str | list[str]]:
    keywords = database.fetch_active_keywords()
    if not keywords:
        raise RuntimeError("keyword_config is empty, please seed or import keywords first.")

    inserted_count = 0
    failures: list[KeywordCrawlFailure] = []
    if mode in {"full", "crawl"}:
        crawler = build_crawler(settings)
        raw_items, failures = crawl_keywords(
            crawler=crawler,
            keywords=keywords,
            snapshot_date=snapshot_date,
            limit=limit,
            task_logger=task_logger,
            error_logger=error_logger,
            continue_on_error=True,
        )
        cleaned_items = clean_items(raw_items)
        inserted_count = database.replace_snapshots(snapshot_date, cleaned_items)

    if mode == "crawl":
        return _build_daily_result(
            snapshot_date=snapshot_date,
            inserted_count=inserted_count,
            stats_count=0,
            score_count=0,
            failures=failures,
            total_keywords=len(keywords),
        )

    snapshot_rows = database.fetch_snapshots_by_date(snapshot_date)
    snapshot_items = _rows_to_items(snapshot_rows, keywords)
    previous_stats = database.fetch_previous_daily_stats(snapshot_date - timedelta(days=1))
    daily_stats, item_scores = calculate_daily_stats(
        snapshot_date, snapshot_items, keywords, previous_stats
    )
    stats_count = database.replace_daily_stats(snapshot_date, daily_stats)
    score_count = database.replace_item_scores(snapshot_date, item_scores)

    _export_daily_reports(settings, snapshot_date, daily_stats, item_scores)
    return _build_daily_result(
        snapshot_date=snapshot_date,
        inserted_count=inserted_count,
        stats_count=stats_count,
        score_count=score_count,
        failures=failures,
        total_keywords=len(keywords),
    )


def run_weekly_pipeline(
    settings: Settings,
    database: BaseDatabase,
    reference_date: date,
) -> dict[str, int | str]:
    week_start = reference_date - timedelta(days=reference_date.weekday())
    daily_stats = database.fetch_daily_stats_between(
        week_start - timedelta(days=7),
        week_start + timedelta(days=6),
    )
    weekly_rows = calculate_weekly_stats(daily_stats, week_start)
    report_rows = [row.to_dict() for row in weekly_rows]
    week_label = f"{week_start.isocalendar().year}-{week_start.isocalendar().week:02d}"
    csv_path = settings.weekly_report_dir / f"weekly_trend_report_{week_label}.csv"
    xlsx_path = settings.weekly_report_dir / f"weekly_trend_report_{week_label}.xlsx"
    export_csv(csv_path, report_rows)
    export_excel_workbook(xlsx_path, {"weekly_trend": report_rows})
    return {
        "week_start": week_start.isoformat(),
        "row_count": len(report_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
    }


def run_monthly_pipeline(
    settings: Settings,
    database: BaseDatabase,
    target_year: int,
    target_month: int,
) -> dict[str, int | str]:
    prev_year, prev_month = _previous_month(target_year, target_month)
    prev_start = date(prev_year, prev_month, 1)
    last_day = _month_end(target_year, target_month)
    daily_stats = database.fetch_daily_stats_between(prev_start, last_day)
    monthly_rows = calculate_monthly_stats(daily_stats, target_year, target_month)
    report_rows = [row.to_dict() for row in monthly_rows]
    month_label = f"{target_year:04d}-{target_month:02d}"
    csv_path = settings.monthly_report_dir / f"monthly_trend_report_{month_label}.csv"
    xlsx_path = settings.monthly_report_dir / f"monthly_trend_report_{month_label}.xlsx"
    export_csv(csv_path, report_rows)
    export_excel_workbook(xlsx_path, {"monthly_trend": report_rows})
    return {
        "month": month_label,
        "row_count": len(report_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
    }


def _build_daily_result(
    *,
    snapshot_date: date,
    inserted_count: int,
    stats_count: int,
    score_count: int,
    failures: list[KeywordCrawlFailure],
    total_keywords: int,
) -> dict[str, int | str | list[str]]:
    failed_keywords = [failure.keyword for failure in failures]
    return {
        "snapshot_date": snapshot_date.isoformat(),
        "inserted_snapshots": inserted_count,
        "daily_stats": stats_count,
        "item_scores": score_count,
        "keyword_total": total_keywords,
        "keyword_success": total_keywords - len(failures),
        "keyword_failed": len(failures),
        "failed_keywords": failed_keywords,
    }


def _export_daily_reports(
    settings: Settings,
    snapshot_date: date,
    daily_stats: list[DailyKeywordStat],
    item_scores: list[DailyItemScore],
) -> None:
    date_label = snapshot_date.isoformat()
    keyword_hot_rows = [
        {
            "date": row.stat_date.isoformat(),
            "category": row.category,
            "keyword": row.keyword,
            "item_count": row.item_count,
            "avg_price": row.avg_price,
            "hot_score": row.hot_score,
            "trend_up_down": row.trend_up_down,
            "opportunity_score": row.opportunity_score,
        }
        for row in daily_stats
    ]
    keyword_price_rows = [
        {
            "date": row.stat_date.isoformat(),
            "keyword": row.keyword,
            "min_price": row.min_price,
            "avg_price": row.avg_price,
            "max_price": row.max_price,
            "item_count": row.item_count,
        }
        for row in daily_stats
    ]
    item_rows = [
        {
            "date": row.stat_date.isoformat(),
            "keyword": row.keyword,
            "title": row.title,
            "price": row.price,
            "rank_pos": row.rank_pos,
            "score": row.score,
            "item_url": row.item_url,
        }
        for row in item_scores
    ]

    keyword_csv = settings.daily_report_dir / f"daily_keyword_report_{date_label}.csv"
    keyword_xlsx = settings.daily_report_dir / f"daily_keyword_report_{date_label}.xlsx"
    item_csv = settings.daily_report_dir / f"daily_item_report_{date_label}.csv"
    item_xlsx = settings.daily_report_dir / f"daily_item_report_{date_label}.xlsx"

    export_csv(keyword_csv, keyword_hot_rows)
    export_csv(item_csv, item_rows)
    export_excel_workbook(
        keyword_xlsx,
        {
            "keyword_hot": keyword_hot_rows,
            "keyword_price": keyword_price_rows,
        },
    )
    export_excel_workbook(item_xlsx, {"item_score": item_rows})


def _rows_to_items(
    rows: Iterable[dict[str, object]],
    keywords: list[KeywordRecord],
) -> list[CrawledItem]:
    category_map = {record.keyword: record.category for record in keywords}
    items: list[CrawledItem] = []
    for row in rows:
        items.append(
            CrawledItem(
                snapshot_date=date.fromisoformat(str(row["snapshot_date"])),
                snapshot_time=datetime.fromisoformat(str(row["snapshot_time"])),
                keyword=str(row["keyword"]),
                item_id=str(row["item_id"]) if row["item_id"] is not None else None,
                title=str(row["title"]),
                price=float(row["price"]) if row["price"] is not None else None,
                rank_pos=int(row["rank_pos"]) if row["rank_pos"] is not None else None,
                seller_name=str(row["seller_name"]) if row["seller_name"] is not None else None,
                item_url=str(row["item_url"]) if row["item_url"] is not None else None,
                desc_text=str(row["desc_text"]) if row["desc_text"] is not None else None,
                raw_text=str(row["raw_text"]) if row["raw_text"] is not None else None,
                category=category_map.get(str(row["keyword"]), "未分类"),
            )
        )
    return items


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, month, 31)
    return date(year, month + 1, 1) - timedelta(days=1)
