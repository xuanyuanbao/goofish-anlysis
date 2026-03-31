from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Iterable

from analyzer.calc_daily_stats import calculate_daily_stats
from analyzer.calc_monthly_stats import calculate_monthly_stats
from analyzer.calc_weekly_stats import calculate_weekly_stats
from analyzer.clean_data import clean_items
from analyzer.data_quality import assess_items
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
    run_id: str | None = None,
    task_logger: logging.Logger | None = None,
    error_logger: logging.Logger | None = None,
    alert_logger: logging.Logger | None = None,
) -> dict[str, object]:
    _ensure_fixture_write_allowed(settings, mode)
    keywords = database.fetch_active_keywords()
    if not keywords:
        raise RuntimeError("keyword_config is empty, please seed or import keywords first.")

    inserted_count = 0
    failures: list[KeywordCrawlFailure] = []
    quality_assessment = assess_items([], duplicate_removed=0)
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
        quality_assessment = assess_items(
            cleaned_items,
            duplicate_removed=max(len(raw_items) - len(cleaned_items), 0),
        )
        inserted_count = database.replace_snapshots(snapshot_date, cleaned_items)
        if run_id is not None:
            database.replace_keyword_failures(
                run_id,
                "daily",
                [failure.to_dict() for failure in failures],
            )
            database.replace_data_quality_issues(run_id, quality_assessment.issues)

    if mode == "crawl":
        return _build_daily_result(
            snapshot_date=snapshot_date,
            mode=mode,
            inserted_count=inserted_count,
            stats_count=0,
            score_count=0,
            failures=failures,
            total_keywords=len(keywords),
            quality_summary=quality_assessment.summary.to_dict(),
            report_paths=[],
            alert_logger=alert_logger,
        )

    snapshot_rows = database.fetch_snapshots_by_date(snapshot_date)
    snapshot_items = _rows_to_items(snapshot_rows, keywords)
    if mode == "report":
        quality_assessment = assess_items(snapshot_items, duplicate_removed=0)
        if run_id is not None:
            database.replace_keyword_failures(run_id, "daily", [])
            database.replace_data_quality_issues(run_id, quality_assessment.issues)
    previous_stats = database.fetch_previous_daily_stats(snapshot_date - timedelta(days=1))
    daily_stats, item_scores = calculate_daily_stats(
        snapshot_date, snapshot_items, keywords, previous_stats
    )
    stats_count = database.replace_daily_stats(snapshot_date, daily_stats)
    score_count = database.replace_item_scores(snapshot_date, item_scores)

    report_paths = _export_daily_reports(
        settings,
        snapshot_date,
        daily_stats,
        item_scores,
        snapshot_items,
    )
    return _build_daily_result(
        snapshot_date=snapshot_date,
        mode=mode,
        inserted_count=inserted_count,
        stats_count=stats_count,
        score_count=score_count,
        failures=failures,
        total_keywords=len(keywords),
        quality_summary=quality_assessment.summary.to_dict(),
        report_paths=report_paths,
        alert_logger=alert_logger,
    )


def run_weekly_pipeline(
    settings: Settings,
    database: BaseDatabase,
    reference_date: date,
) -> dict[str, object]:
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
    summary_rows = _build_weekly_summary_rows(report_rows, week_label)
    export_excel_workbook(
        xlsx_path,
        {"summary": summary_rows, "weekly_trend": report_rows},
    )
    return {
        "week_start": week_start.isoformat(),
        "row_count": len(report_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "report_paths": [str(csv_path), str(xlsx_path)],
        "alert_level": "warning" if not report_rows else "info",
        "alert_message": None if report_rows else "Weekly report generated with no rows.",
    }


def run_monthly_pipeline(
    settings: Settings,
    database: BaseDatabase,
    target_year: int,
    target_month: int,
) -> dict[str, object]:
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
    summary_rows = _build_monthly_summary_rows(report_rows, month_label)
    export_excel_workbook(
        xlsx_path,
        {"summary": summary_rows, "monthly_trend": report_rows},
    )
    return {
        "month": month_label,
        "row_count": len(report_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "report_paths": [str(csv_path), str(xlsx_path)],
        "alert_level": "warning" if not report_rows else "info",
        "alert_message": None if report_rows else "Monthly report generated with no rows.",
    }


def _build_daily_result(
    *,
    snapshot_date: date,
    mode: str,
    inserted_count: int,
    stats_count: int,
    score_count: int,
    failures: list[KeywordCrawlFailure],
    total_keywords: int,
    quality_summary: dict[str, int],
    report_paths: list[str],
    alert_logger: logging.Logger | None = None,
) -> dict[str, object]:
    failed_keywords = [failure.keyword for failure in failures]
    result: dict[str, object] = {
        "snapshot_date": snapshot_date.isoformat(),
        "mode": mode,
        "inserted_snapshots": inserted_count,
        "daily_stats": stats_count,
        "item_scores": score_count,
        "keyword_total": total_keywords,
        "keyword_success": total_keywords - len(failures),
        "keyword_failed": len(failures),
        "failed_keywords": failed_keywords,
        "quality_summary": quality_summary,
        "quality_issue_count": _count_quality_issues(quality_summary),
        "report_paths": report_paths,
    }
    alert_level, alert_message = _build_alert_summary(result)
    result["alert_level"] = alert_level
    result["alert_message"] = alert_message
    if alert_message and alert_logger is not None:
        log_method = alert_logger.error if alert_level == "error" else alert_logger.warning
        log_method("daily | %s | %s", snapshot_date.isoformat(), alert_message)
    return result


def _ensure_fixture_write_allowed(settings: Settings, mode: str) -> None:
    if mode not in {"full", "crawl"}:
        return
    if settings.crawler_mode != "fixture":
        return
    if settings.allow_fixture_write:
        return
    raise RuntimeError(
        "Fixture crawler writes are blocked for this environment. "
        "Use xianyu_curl/xianyu_http for MySQL data collection, or set "
        "XY_ALLOW_FIXTURE_WRITE=1 only for isolated smoke testing."
    )


def _export_daily_reports(
    settings: Settings,
    snapshot_date: date,
    daily_stats: list[DailyKeywordStat],
    item_scores: list[DailyItemScore],
    snapshot_items: list[CrawledItem],
) -> list[str]:
    date_label = snapshot_date.isoformat()
    summary_rows = _build_daily_summary_rows(snapshot_date, daily_stats, item_scores, snapshot_items)
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
    keyword_opportunity_rows = [
        {
            "date": row.stat_date.isoformat(),
            "category": row.category,
            "keyword": row.keyword,
            "hot_score": row.hot_score,
            "trend_up_down": row.trend_up_down,
            "opportunity_score": row.opportunity_score,
        }
        for row in sorted(
            daily_stats,
            key=lambda item: (-item.opportunity_score, -item.hot_score, item.keyword),
        )
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
    snapshot_lookup = _build_snapshot_lookup(snapshot_items)
    item_rows = [
        {
            "date": row.stat_date.isoformat(),
            "category": snapshot_lookup.get(_item_lookup_key(row.keyword, row.item_id, row.title), {}).get(
                "category"
            ),
            "keyword": row.keyword,
            "title": row.title,
            "seller_name": snapshot_lookup.get(
                _item_lookup_key(row.keyword, row.item_id, row.title), {}
            ).get("seller_name"),
            "price": row.price,
            "rank_pos": row.rank_pos,
            "score": row.score,
            "desc_text": snapshot_lookup.get(
                _item_lookup_key(row.keyword, row.item_id, row.title), {}
            ).get("desc_text"),
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
            "summary": summary_rows,
            "keyword_hot": keyword_hot_rows,
            "keyword_opportunity": keyword_opportunity_rows,
            "keyword_price": keyword_price_rows,
        },
    )
    export_excel_workbook(item_xlsx, {"summary": summary_rows, "item_score": item_rows})
    return [str(keyword_csv), str(keyword_xlsx), str(item_csv), str(item_xlsx)]


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


def _build_snapshot_lookup(snapshot_items: list[CrawledItem]) -> dict[tuple[str, str | None, str], dict[str, object]]:
    lookup: dict[tuple[str, str | None, str], dict[str, object]] = {}
    for item in snapshot_items:
        lookup[_item_lookup_key(item.keyword, item.item_id, item.title)] = {
            "category": item.category,
            "seller_name": item.seller_name,
            "desc_text": item.desc_text,
        }
    return lookup


def _item_lookup_key(
    keyword: str,
    item_id: str | None,
    title: str,
) -> tuple[str, str | None, str]:
    return (keyword, item_id, title)


def _build_daily_summary_rows(
    snapshot_date: date,
    daily_stats: list[DailyKeywordStat],
    item_scores: list[DailyItemScore],
    snapshot_items: list[CrawledItem],
) -> list[dict[str, object]]:
    category_counter = Counter(item.category for item in snapshot_items)
    top_keyword = daily_stats[0].keyword if daily_stats else None
    top_hot_score = daily_stats[0].hot_score if daily_stats else None
    avg_price_values = [row.avg_price for row in daily_stats if row.avg_price is not None]
    average_market_price = (
        round(sum(avg_price_values) / len(avg_price_values), 2) if avg_price_values else None
    )
    summary_rows = [
        {"metric": "snapshot_date", "value": snapshot_date.isoformat()},
        {"metric": "keyword_count", "value": len(daily_stats)},
        {"metric": "snapshot_item_count", "value": len(snapshot_items)},
        {"metric": "scored_item_count", "value": len(item_scores)},
        {"metric": "top_keyword", "value": top_keyword},
        {"metric": "top_hot_score", "value": top_hot_score},
        {"metric": "average_market_price", "value": average_market_price},
        {
            "metric": "category_breakdown",
            "value": " | ".join(f"{name}:{count}" for name, count in category_counter.items()),
        },
    ]
    return summary_rows


def _build_weekly_summary_rows(
    report_rows: list[dict[str, object]],
    week_label: str,
) -> list[dict[str, object]]:
    top_row = report_rows[0] if report_rows else {}
    attention_levels = Counter(str(row.get("attention_level")) for row in report_rows)
    return [
        {"metric": "week_label", "value": week_label},
        {"metric": "keyword_count", "value": len(report_rows)},
        {"metric": "top_keyword", "value": top_row.get("keyword")},
        {"metric": "top_wow_rate", "value": top_row.get("wow_rate")},
        {
            "metric": "attention_breakdown",
            "value": " | ".join(
                f"{level}:{count}" for level, count in attention_levels.items() if level and level != "None"
            ),
        },
    ]


def _build_monthly_summary_rows(
    report_rows: list[dict[str, object]],
    month_label: str,
) -> list[dict[str, object]]:
    top_row = report_rows[0] if report_rows else {}
    rising_counter = Counter(str(row.get("rising_flag")) for row in report_rows)
    return [
        {"metric": "month_label", "value": month_label},
        {"metric": "keyword_count", "value": len(report_rows)},
        {"metric": "top_keyword", "value": top_row.get("keyword")},
        {"metric": "top_mom_rate", "value": top_row.get("mom_rate")},
        {
            "metric": "rising_flag_breakdown",
            "value": " | ".join(
                f"{flag}:{count}" for flag, count in rising_counter.items() if flag and flag != "None"
            ),
        },
    ]


def _build_alert_summary(result: dict[str, object]) -> tuple[str, str | None]:
    mode = str(result.get("mode") or "full")
    keyword_total = int(result.get("keyword_total") or 0)
    keyword_failed = int(result.get("keyword_failed") or 0)
    inserted_snapshots = int(result.get("inserted_snapshots") or 0)
    quality_summary = result.get("quality_summary")
    missing_urls = 0
    invalid_urls = 0
    short_desc = 0
    if isinstance(quality_summary, dict):
        missing_urls = int(quality_summary.get("missing_item_url") or 0)
        invalid_urls = int(quality_summary.get("invalid_item_url") or 0)
        short_desc = int(quality_summary.get("short_desc") or 0)

    if keyword_total and keyword_failed == keyword_total:
        return "error", "All keywords failed during the crawl run."
    if mode in {"full", "crawl"} and keyword_total and inserted_snapshots == 0:
        return "error", "The crawl finished without writing any snapshot rows."
    if keyword_failed > 0:
        return "warning", f"{keyword_failed} keyword(s) failed during the crawl run."
    if missing_urls > 0 or invalid_urls > 0:
        return "warning", (
            f"Detected {missing_urls} missing item_url row(s) and {invalid_urls} invalid URL row(s)."
        )
    if short_desc > max(int(result.get("keyword_total") or 0), 3):
        return "warning", "A large share of desc_text values are still too short."
    return "info", None


def _count_quality_issues(summary: dict[str, int]) -> int:
    return sum(
        int(summary.get(key) or 0)
        for key in (
            "missing_item_id",
            "missing_item_url",
            "invalid_item_url",
            "url_item_mismatch",
            "missing_price",
            "missing_seller_name",
            "short_desc",
        )
    )


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, month, 31)
    return date(year, month + 1, 1) - timedelta(days=1)
