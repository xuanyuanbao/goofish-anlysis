from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import fmean

from models import CrawledItem, DailyItemScore, DailyKeywordStat, KeywordRecord

from analyzer.scoring import calc_rank_factor, score_items_for_keyword


def calculate_daily_stats(
    stat_date: date,
    items: list[CrawledItem],
    keywords: list[KeywordRecord],
    previous_stats: dict[str, dict[str, object]],
) -> tuple[list[DailyKeywordStat], list[DailyItemScore]]:
    keyword_map = {record.keyword: record for record in keywords}
    grouped: dict[str, list[CrawledItem]] = defaultdict(list)
    for item in items:
        grouped[item.keyword].append(item)

    stats_rows: list[DailyKeywordStat] = []
    score_rows: list[DailyItemScore] = []

    for keyword, keyword_items in grouped.items():
        ordered_items = sorted(keyword_items, key=lambda item: item.rank_pos or 9999)
        prices = [item.price for item in ordered_items if item.price is not None]
        avg_price = round(fmean(prices), 2) if prices else None
        min_price = round(min(prices), 2) if prices else None
        max_price = round(max(prices), 2) if prices else None
        top10 = ordered_items[:10]
        top10_avg_rank = (
            round(fmean([item.rank_pos for item in top10 if item.rank_pos is not None]), 2)
            if top10
            else None
        )
        item_count = len(ordered_items)
        rank_factor = calc_rank_factor(ordered_items)
        hot_score = round(item_count * 0.6 + rank_factor * 0.4, 2)

        previous_hot = float(previous_stats.get(keyword, {}).get("hot_score", 0.0) or 0.0)
        trend_up_down = round(hot_score - previous_hot, 2)
        trend_rate = (trend_up_down / previous_hot) if previous_hot else 0.0
        competition_factor = min(item_count / 20.0, 3.0)
        opportunity_score = round(
            hot_score * (1 + max(trend_rate, -0.9)) / (1 + competition_factor),
            2,
        )

        stats_rows.append(
            DailyKeywordStat(
                stat_date=stat_date,
                keyword=keyword,
                category=keyword_map[keyword].category if keyword in keyword_map else "未分类",
                item_count=item_count,
                avg_price=avg_price,
                min_price=min_price,
                max_price=max_price,
                top10_avg_rank=top10_avg_rank,
                hot_score=hot_score,
                trend_up_down=trend_up_down,
                opportunity_score=opportunity_score,
            )
        )
        score_rows.extend(score_items_for_keyword(stat_date, keyword, ordered_items))

    stats_rows.sort(key=lambda row: (-row.hot_score, row.keyword))
    return stats_rows, score_rows
