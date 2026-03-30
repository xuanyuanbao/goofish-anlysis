from __future__ import annotations

from statistics import median

from models import CrawledItem, DailyItemScore


def score_items_for_keyword(
    stat_date,
    keyword: str,
    items: list[CrawledItem],
) -> list[DailyItemScore]:
    prices = [item.price for item in items if item.price is not None]
    target_price = median(prices) if prices else None
    rows: list[DailyItemScore] = []

    for item in items:
        rank_score = calc_rank_score(item.rank_pos)
        title_match_score = calc_title_match_score(keyword, item.title)
        price_score = calc_price_score(item.price, target_price)
        total_score = round(rank_score * 0.5 + title_match_score * 0.3 + price_score * 0.2, 2)
        rows.append(
            DailyItemScore(
                stat_date=stat_date,
                keyword=keyword,
                item_id=item.item_id,
                title=item.title,
                rank_pos=item.rank_pos,
                price=item.price,
                score=total_score,
                item_url=item.item_url,
            )
        )
    return sorted(rows, key=lambda row: (-row.score, row.rank_pos or 9999, row.title))


def calc_rank_score(rank_pos: int | None) -> float:
    if rank_pos is None:
        return 0.0
    return round(max(0.0, 100.0 - (rank_pos - 1) * 2.5), 2)


def calc_title_match_score(keyword: str, title: str) -> float:
    keyword_tokens = [token for token in keyword.split() if token]
    if not keyword_tokens:
        keyword_tokens = [keyword]
    hit_count = sum(1 for token in keyword_tokens if token in title)
    ratio = hit_count / len(keyword_tokens)
    if keyword in title:
        ratio = max(ratio, 1.0)
    return round(ratio * 100, 2)


def calc_price_score(price: float | None, target_price: float | None) -> float:
    if price is None or target_price in (None, 0):
        return 60.0
    delta_ratio = abs(price - target_price) / target_price
    return round(max(10.0, 100.0 - delta_ratio * 100.0), 2)


def calc_rank_factor(items: list[CrawledItem]) -> float:
    if not items:
        return 0.0
    top_items = items[:10]
    avg_rank = sum(item.rank_pos or 100 for item in top_items) / len(top_items)
    return round(max(0.0, 100.0 - avg_rank * 2), 2)
