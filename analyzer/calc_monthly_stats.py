from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import fmean

from models import MonthlyTrendRow


def calculate_monthly_stats(
    daily_stats: list[dict[str, object]],
    target_year: int,
    target_month: int,
) -> list[MonthlyTrendRow]:
    current_grouped = _group_month(daily_stats, target_year, target_month)
    previous_year, previous_month = _previous_month(target_year, target_month)
    previous_grouped = _group_month(daily_stats, previous_year, previous_month)
    keywords = sorted(set(current_grouped) | set(previous_grouped))

    month_label = f"{target_year:04d}-{target_month:02d}"
    rows: list[MonthlyTrendRow] = []
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
        mom_rate = _growth_rate(current_avg_hot, previous_avg_hot)
        rows.append(
            MonthlyTrendRow(
                month_label=month_label,
                keyword=keyword,
                category=category,
                current_avg_hot=current_avg_hot or 0.0,
                previous_avg_hot=previous_avg_hot or 0.0,
                mom_rate=mom_rate,
                current_avg_price=current_avg_price,
                previous_avg_price=previous_avg_price,
                rising_flag="是" if mom_rate > 0.08 else "否",
            )
        )
    return sorted(rows, key=lambda row: (-row.current_avg_hot, row.keyword))


def _group_month(
    daily_stats: list[dict[str, object]], year: int, month: int
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in daily_stats:
        stat_date = date.fromisoformat(str(row["stat_date"]))
        if stat_date.year == year and stat_date.month == month:
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


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1
