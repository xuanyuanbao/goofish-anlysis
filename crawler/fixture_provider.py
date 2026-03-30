from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, time

from models import CrawledItem, KeywordRecord

from .base import BaseCrawler


SELLERS = [
    "资料小铺",
    "学霸笔记屋",
    "冲刺资料库",
    "提分小站",
    "考试速递",
    "高分同学",
    "上岸资料集",
    "备考补给站",
]

TITLE_SUFFIXES = [
    "全套电子版",
    "历年真题整理",
    "高频考点总结",
    "冲刺提分资料",
    "笔记讲义合集",
    "压轴专题训练",
    "内部精选版",
    "考前突击包",
]

DESC_SUFFIXES = [
    "支持即拍即发，适合短期冲刺。",
    "按章节整理，适合查漏补缺。",
    "资料经过清洗，便于打印和二次整理。",
    "覆盖近年热点题型，适合高频复习。",
]

CATEGORY_BASE_PRICE = {
    "小学资料": 8.0,
    "初中资料": 12.0,
    "高中资料": 16.0,
    "高考资料": 22.0,
    "考研资料": 35.0,
    "考公资料": 28.0,
    "考编资料": 26.0,
    "教资资料": 20.0,
    "大学资料": 18.0,
}


class FixtureCrawler(BaseCrawler):
    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        rng = random.Random(_daily_seed(keyword.keyword, snapshot_date))
        count = min(limit, _daily_count(keyword.keyword, snapshot_date))
        catalog_size = max(60, limit * 2)
        selected_indexes = _select_catalog_indexes(
            keyword.keyword, snapshot_date, catalog_size, count
        )
        timestamp = datetime.combine(snapshot_date, time(hour=9, minute=30))
        items: list[CrawledItem] = []

        for rank_pos, catalog_index in enumerate(selected_indexes, start=1):
            title = _build_title(keyword.keyword, catalog_index)
            price = _build_price(keyword.category, rank_pos, catalog_index, rng)
            items.append(
                CrawledItem(
                    snapshot_date=snapshot_date,
                    snapshot_time=timestamp,
                    keyword=keyword.keyword,
                    item_id=f"{_slugify(keyword.keyword)}-{catalog_index:03d}",
                    title=title,
                    price=price,
                    rank_pos=rank_pos,
                    seller_name=SELLERS[catalog_index % len(SELLERS)],
                    item_url=(
                        "https://www.goofish.com/item/"
                        f"{_slugify(keyword.keyword)}-{catalog_index:03d}"
                    ),
                    desc_text=f"{keyword.keyword} {DESC_SUFFIXES[catalog_index % len(DESC_SUFFIXES)]}",
                    raw_text=title,
                    category=keyword.category,
                )
            )
        return items


def _daily_seed(keyword: str, snapshot_date: date) -> int:
    payload = f"{keyword}|{snapshot_date.isoformat()}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16)


def _daily_count(keyword: str, snapshot_date: date) -> int:
    base = 18 + (sum(ord(char) for char in keyword) % 12)
    wave = (snapshot_date.toordinal() % 7) - 3
    return max(18, min(45, base + wave))


def _select_catalog_indexes(
    keyword: str, snapshot_date: date, catalog_size: int, count: int
) -> list[int]:
    rotation = (sum(ord(char) for char in keyword) + snapshot_date.toordinal()) % catalog_size
    return [((rotation + idx) % catalog_size) + 1 for idx in range(count)]


def _build_title(keyword: str, catalog_index: int) -> str:
    suffix = TITLE_SUFFIXES[catalog_index % len(TITLE_SUFFIXES)]
    edition = 2024 + (catalog_index % 3)
    return f"{keyword} {suffix} {edition}版"


def _build_price(category: str, rank_pos: int, catalog_index: int, rng: random.Random) -> float:
    base_price = CATEGORY_BASE_PRICE.get(category, 15.0)
    rank_discount = max(0.0, 3.5 - rank_pos * 0.08)
    catalog_premium = (catalog_index % 7) * 0.9
    jitter = rng.uniform(-1.5, 2.5)
    return round(max(1.9, base_price + rank_discount + catalog_premium + jitter), 2)


def _slugify(value: str) -> str:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return digest[:12]
