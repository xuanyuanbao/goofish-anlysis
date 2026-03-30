from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean

from models import WeeklyTrendRow


def calculate_weekly_stats(
    daily_stats: list[dict[str, object]],
    week_start: date,
) -> list[WeeklyTrendRow]:
    current_end = week_start + timedelta(days=6)
    previous_start = week_start - timedelta(days=7)
    previous_end = week_start - timedelta(days=1)

    current_grouped = _group_period(daily_stats, week_start, current_end)
    previous_grouped = _group_period(daily_stats, previous_start, previous_end)
    keywords = sorted(set(current_grouped) | set(previous_grouped))

    rows: list[WeeklyTrendRow] = []
    for keyword in keywords:
        current_rows = current_grouped.get(keyword, [])
        previous_rows = previous_grouped.get(keyword, [])
        category = (
            current_rows[0]["category"]
            if current_rows
            else previous_rows[0]["category"]
            if previous_rows
            else "未分类"
        )
        current_avg_hot = _avg_metric(current_rows, "hot_score")
        previous_avg_hot = _avg_metric(previous_rows, "hot_score")
        current_avg_price = _avg_metric(current_rows, "avg_price")
        previous_avg_price = _avg_metric(previous_rows, "avg_price")
        wow_rate = _growth_rate(current_avg_hot, previous_avg_hot)
        rows.append(
            WeeklyTrendRow(
                week_start=week_start,
                week_end=current_end,
                keyword=keyword,
                category=category,
                current_avg_hot=current_avg_hot,
                previous_avg_hot=previous_avg_hot,
                wow_rate=wow_rate,
                current_avg_price=current_avg_price,
                previous_avg_price=previous_avg_price,
                attention_level=_attention_level(current_avg_hot, wow_rate),
            )
        )
    return sorted(rows, key=lambda row: (-(row.current_avg_hot or 0.0), row.keyword))


def _group_period(
    daily_stats: list[dict[str, object]], start_date: date, end_date: date
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in daily_stats:
        stat_date = date.fromisoformat(str(row["stat_date"]))
        if start_date <= stat_date <= end_date:
            grouped[str(row["keyword"])].append(row)
    return grouped


def _avg_metric(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(fmean(values), 2)


def _growth_rate(current: float | None, previous: float | None) -> float:
    if current is None or previous in (None, 0):
        return 0.0
    return round((current - previous) / previous, 4)


def _attention_level(current_hot: float | None, wow_rate: float) -> str:
    if current_hot is None:
        return "无数据"
    if current_hot >= 55 and wow_rate > 0.12:
        return "高"
    if current_hot >= 40 or wow_rate > 0.05:
        return "中"
    return "低"
