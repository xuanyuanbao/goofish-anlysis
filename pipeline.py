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
from models import (
    CrawledItem,
    DailyItemScore,
    DailyKeywordStat,
    KeywordRecord,
    MonthlyTrendRow,
    WeeklyTrendRow,
)


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
    localized_rows = _build_weekly_report_rows(weekly_rows)
    week_label = f"{week_start.isocalendar().year}-{week_start.isocalendar().week:02d}"
    csv_path = settings.weekly_report_dir / f"weekly_trend_report_{week_label}.csv"
    xlsx_path = settings.weekly_report_dir / f"weekly_trend_report_{week_label}.xlsx"
    export_csv(csv_path, localized_rows)
    summary_rows = _build_weekly_summary_rows(weekly_rows, week_label)
    export_excel_workbook(
        xlsx_path,
        {
            "报表概览": summary_rows,
            "计算说明": _build_weekly_formula_rows(),
            "周趋势": localized_rows,
        },
    )
    return {
        "week_start": week_start.isoformat(),
        "row_count": len(localized_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "report_paths": [str(csv_path), str(xlsx_path)],
        "alert_level": "warning" if not localized_rows else "info",
        "alert_message": None if localized_rows else "Weekly report generated with no rows.",
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
    localized_rows = _build_monthly_report_rows(monthly_rows)
    month_label = f"{target_year:04d}-{target_month:02d}"
    csv_path = settings.monthly_report_dir / f"monthly_trend_report_{month_label}.csv"
    xlsx_path = settings.monthly_report_dir / f"monthly_trend_report_{month_label}.xlsx"
    export_csv(csv_path, localized_rows)
    summary_rows = _build_monthly_summary_rows(monthly_rows, month_label)
    export_excel_workbook(
        xlsx_path,
        {
            "报表概览": summary_rows,
            "计算说明": _build_monthly_formula_rows(),
            "月趋势": localized_rows,
        },
    )
    return {
        "month": month_label,
        "row_count": len(localized_rows),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "report_paths": [str(csv_path), str(xlsx_path)],
        "alert_level": "warning" if not localized_rows else "info",
        "alert_message": None if localized_rows else "Monthly report generated with no rows.",
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
    formula_rows = _build_daily_formula_rows()
    keyword_hot_rows = _build_daily_keyword_hot_rows(daily_stats)
    keyword_opportunity_rows = _build_daily_keyword_opportunity_rows(daily_stats)
    keyword_price_rows = _build_daily_keyword_price_rows(daily_stats)
    snapshot_lookup = _build_snapshot_lookup(snapshot_items)
    item_rows = _build_daily_item_rows(item_scores, snapshot_lookup)

    keyword_csv = settings.daily_report_dir / f"daily_keyword_report_{date_label}.csv"
    keyword_xlsx = settings.daily_report_dir / f"daily_keyword_report_{date_label}.xlsx"
    item_csv = settings.daily_report_dir / f"daily_item_report_{date_label}.csv"
    item_xlsx = settings.daily_report_dir / f"daily_item_report_{date_label}.xlsx"

    export_csv(keyword_csv, keyword_hot_rows)
    export_csv(item_csv, item_rows)
    export_excel_workbook(
        keyword_xlsx,
        {
            "报表概览": summary_rows,
            "计算说明": formula_rows,
            "关键词热度": keyword_hot_rows,
            "机会词榜": keyword_opportunity_rows,
            "价格分布": keyword_price_rows,
        },
    )
    export_excel_workbook(
        item_xlsx,
        {
            "报表概览": summary_rows,
            "计算说明": formula_rows,
            "商品评分": item_rows,
        },
    )
    return [str(keyword_csv), str(keyword_xlsx), str(item_csv), str(item_xlsx)]


def _build_daily_keyword_hot_rows(daily_stats: list[DailyKeywordStat]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in daily_stats:
        rows.append(
            {
                "统计日期": row.stat_date.isoformat(),
                "类目": row.category,
                "关键词": row.keyword,
                "商品数": row.item_count,
                "平均价格": row.avg_price,
                "最低价格": row.min_price,
                "最高价格": row.max_price,
                "Top10平均排名": row.top10_avg_rank,
                "热度分": row.hot_score,
                "趋势值": row.trend_up_down,
                "机会分": row.opportunity_score,
            }
        )
    return rows


def _build_daily_keyword_opportunity_rows(
    daily_stats: list[DailyKeywordStat],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sorted_rows = sorted(
        daily_stats,
        key=lambda item: (-item.opportunity_score, -item.hot_score, item.keyword),
    )
    for index, row in enumerate(sorted_rows, start=1):
        rows.append(
            {
                "机会排名": index,
                "统计日期": row.stat_date.isoformat(),
                "类目": row.category,
                "关键词": row.keyword,
                "机会分": row.opportunity_score,
                "热度分": row.hot_score,
                "趋势值": row.trend_up_down,
                "商品数": row.item_count,
                "平均价格": row.avg_price,
            }
        )
    return rows


def _build_daily_keyword_price_rows(daily_stats: list[DailyKeywordStat]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in daily_stats:
        rows.append(
            {
                "统计日期": row.stat_date.isoformat(),
                "关键词": row.keyword,
                "最低价格": row.min_price,
                "平均价格": row.avg_price,
                "最高价格": row.max_price,
                "样本商品数": row.item_count,
            }
        )
    return rows


def _build_daily_item_rows(
    item_scores: list[DailyItemScore],
    snapshot_lookup: dict[tuple[str, str | None, str], dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in item_scores:
        snapshot_info = snapshot_lookup.get(_item_lookup_key(row.keyword, row.item_id, row.title), {})
        rows.append(
            {
                "统计日期": row.stat_date.isoformat(),
                "类目": snapshot_info.get("category"),
                "关键词": row.keyword,
                "商品ID": row.item_id,
                "商品标题": row.title,
                "卖家昵称": snapshot_info.get("seller_name"),
                "价格": row.price,
                "排名": row.rank_pos,
                "商品评分": row.score,
                "描述摘要": snapshot_info.get("desc_text"),
                "商品链接": row.item_url,
            }
        )
    return rows


def _build_weekly_report_rows(report_rows: list[WeeklyTrendRow]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in report_rows:
        rows.append(
            {
                "周开始日期": row.week_start.isoformat(),
                "周结束日期": row.week_end.isoformat(),
                "类目": row.category,
                "关键词": row.keyword,
                "本周平均热度": row.current_avg_hot,
                "上周平均热度": row.previous_avg_hot,
                "周环比": _format_ratio(row.wow_rate),
                "本周平均价格": row.current_avg_price,
                "上周平均价格": row.previous_avg_price,
                "关注等级": row.attention_level,
            }
        )
    return rows


def _build_monthly_report_rows(report_rows: list[MonthlyTrendRow]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in report_rows:
        rows.append(
            {
                "月份": row.month_label,
                "类目": row.category,
                "关键词": row.keyword,
                "本月平均热度": row.current_avg_hot,
                "上月平均热度": row.previous_avg_hot,
                "月环比": _format_ratio(row.mom_rate),
                "本月平均价格": row.current_avg_price,
                "上月平均价格": row.previous_avg_price,
                "是否进入上升期": row.rising_flag,
            }
        )
    return rows


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
    top_keyword = daily_stats[0].keyword if daily_stats else "?"
    top_hot_score = daily_stats[0].hot_score if daily_stats else "?"
    avg_price_values = [row.avg_price for row in daily_stats if row.avg_price is not None]
    average_market_price = (
        round(sum(avg_price_values) / len(avg_price_values), 2) if avg_price_values else "?"
    )
    category_breakdown = " | ".join(
        f"{name}:{count}" for name, count in category_counter.most_common()
    ) or "无"
    return [
        {"指标": "统计日期", "数值": snapshot_date.isoformat(), "说明": "本次日报对应的统计日期。"},
        {"指标": "关键词数量", "数值": len(daily_stats), "说明": "当日成功生成统计指标的关键词数量。"},
        {"指标": "快照商品数", "数值": len(snapshot_items), "说明": "当日入库并参与统计的商品快照总数。"},
        {"指标": "评分商品数", "数值": len(item_scores), "说明": "进入商品评分榜的商品数量。"},
        {"指标": "热度第一关键词", "数值": top_keyword, "说明": "按热度分倒序排序后的第一名关键词。"},
        {"指标": "最高热度分", "数值": top_hot_score, "说明": "关键词热度榜第一名的热度分。"},
        {"指标": "市场平均价格", "数值": average_market_price, "说明": "按关键词均价再做整体平均后的市场参考价格。"},
        {"指标": "类目分布", "数值": category_breakdown, "说明": "按商品快照统计的类目样本分布。"},
    ]


def _build_weekly_summary_rows(
    report_rows: list[WeeklyTrendRow],
    week_label: str,
) -> list[dict[str, object]]:
    top_row = report_rows[0] if report_rows else None
    attention_levels = Counter(row.attention_level for row in report_rows)
    attention_breakdown = " | ".join(
        f"{level}:{count}" for level, count in attention_levels.items() if level
    ) or "无"
    return [
        {"指标": "周标识", "数值": week_label, "说明": "本次周报覆盖的 ISO 周标签。"},
        {"指标": "关键词数量", "数值": len(report_rows), "说明": "进入周报统计的关键词数量。"},
        {"指标": "热度第一关键词", "数值": top_row.keyword if top_row else "无", "说明": "按本周平均热度排序后的第一名关键词。"},
        {"指标": "最高周环比", "数值": _format_ratio(top_row.wow_rate) if top_row else "无", "说明": "榜首关键词相对上周的热度变化比例。"},
        {"指标": "关注等级分布", "数值": attention_breakdown, "说明": "高 / 中 / 低关注等级的数量分布。"},
    ]


def _build_monthly_summary_rows(
    report_rows: list[MonthlyTrendRow],
    month_label: str,
) -> list[dict[str, object]]:
    top_row = report_rows[0] if report_rows else None
    rising_counter = Counter(row.rising_flag for row in report_rows)
    rising_breakdown = " | ".join(
        f"{flag}:{count}" for flag, count in rising_counter.items() if flag
    ) or "无"
    return [
        {"指标": "月份", "数值": month_label, "说明": "本次月报对应的自然月。"},
        {"指标": "关键词数量", "数值": len(report_rows), "说明": "进入月报统计的关键词数量。"},
        {"指标": "热度第一关键词", "数值": top_row.keyword if top_row else "无", "说明": "按本月平均热度排序后的第一名关键词。"},
        {"指标": "最高月环比", "数值": _format_ratio(top_row.mom_rate) if top_row else "无", "说明": "榜首关键词相对上月的热度变化比例。"},
        {"指标": "上升期分布", "数值": rising_breakdown, "说明": "进入上升期与否的数量分布。"},
    ]


def _build_daily_formula_rows() -> list[dict[str, object]]:
    return [
        {"模型项": "热度分", "计算方式": "商品数 × 0.6 + 排名因子 × 0.4", "解释": "热度分越高，表示该关键词当天供给规模和排名质量综合表现越强。"},
        {"模型项": "排名因子", "计算方式": "max(0, 100 - Top10平均排名 × 2)", "解释": "Top10 平均排名越靠前，排名因子越高。"},
        {"模型项": "趋势值", "计算方式": "今日热度分 - 昨日热度分", "解释": "正数表示升温，负数表示降温。"},
        {"模型项": "机会分", "计算方式": "热度分 × (1 + max(趋势率, -0.9)) ÷ (1 + min(商品数 ÷ 20, 3))", "解释": "热度越高、趋势越好、竞争越不过度拥挤时，机会分越高。"},
        {"模型项": "趋势率", "计算方式": "趋势值 ÷ 昨日热度分；若昨日热度分为空则记 0", "解释": "用于衡量相对变化速度。"},
        {"模型项": "商品评分", "计算方式": "排名分 × 0.5 + 标题匹配分 × 0.3 + 价格分 × 0.2", "解释": "用于在同一关键词下筛选更值得关注的商品。"},
        {"模型项": "排名分", "计算方式": "max(0, 100 - (排名 - 1) × 2.5)", "解释": "搜索排名越靠前，得分越高。"},
        {"模型项": "标题匹配分", "计算方式": "关键词命中比例 × 100；若完整关键词出现在标题中则至少记 100", "解释": "衡量标题与关键词的相关性。"},
        {"模型项": "价格分", "计算方式": "max(10, 100 - |商品价格 - 关键词中位价| ÷ 关键词中位价 × 100)", "解释": "价格越接近该关键词当日中位价，得分越高。"},
    ]


def _build_weekly_formula_rows() -> list[dict[str, object]]:
    return [
        {"模型项": "本周平均热度", "计算方式": "本周 7 天内每日热度分取平均值", "解释": "用于观察关键词在一周范围内的平均热度水平。"},
        {"模型项": "周环比", "计算方式": "(本周平均热度 - 上周平均热度) ÷ 上周平均热度", "解释": "正值表示比上周升温，负值表示比上周降温。"},
        {"模型项": "关注等级", "计算方式": "高：热度≥55 且周环比>12%；中：热度≥40 或周环比>5%；其余为低", "解释": "帮助快速定位本周值得优先关注的关键词。"},
    ]


def _build_monthly_formula_rows() -> list[dict[str, object]]:
    return [
        {"模型项": "本月平均热度", "计算方式": "本月每日热度分取平均值", "解释": "用于观察关键词在自然月范围内的平均热度水平。"},
        {"模型项": "月环比", "计算方式": "(本月平均热度 - 上月平均热度) ÷ 上月平均热度", "解释": "正值表示比上月升温，负值表示比上月降温。"},
        {"模型项": "是否进入上升期", "计算方式": "月环比 > 8% 记为“是”，否则记为“否”", "解释": "用于快速识别本月明显上升的关键词。"},
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


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "无"
    return f"{value * 100:.2f}%"


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, month, 31)
    return date(year, month + 1, 1) - timedelta(days=1)
