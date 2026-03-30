from __future__ import annotations

import re
from typing import Iterable

from models import CrawledItem


NOISE_WORDS = (
    "秒发",
    "自动发货",
    "全网最低",
    "亏本冲量",
    "引流",
    "低价",
    "高清",
    "全套",
    "最新版",
)


def clean_items(items: Iterable[CrawledItem]) -> list[CrawledItem]:
    cleaned: list[CrawledItem] = []
    seen_keys: set[str] = set()

    for item in items:
        title = clean_title(item.title)
        dedupe_key = (
            f"{item.keyword}|{item.item_id}"
            if item.item_id
            else f"{item.keyword}|{title}|{item.seller_name}|{item.price}"
        )
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        cleaned.append(
            CrawledItem(
                snapshot_date=item.snapshot_date,
                snapshot_time=item.snapshot_time,
                keyword=item.keyword,
                item_id=item.item_id,
                title=title,
                price=normalize_price(item.price),
                rank_pos=item.rank_pos,
                seller_name=item.seller_name,
                item_url=item.item_url,
                desc_text=item.desc_text.strip() if item.desc_text else None,
                raw_text=item.raw_text,
                category=item.category,
            )
        )
    return cleaned


def clean_title(title: str) -> str:
    normalized = title
    for word in NOISE_WORDS:
        normalized = normalized.replace(word, " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_price(value: float | int | None) -> float | None:
    if value is None:
        return None
    price = float(value)
    if price <= 0:
        return None
    return round(price, 2)
