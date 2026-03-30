from __future__ import annotations

from datetime import date

from config.settings import Settings
from models import CrawledItem, KeywordRecord

from .base import BaseCrawler
from .fixture_provider import FixtureCrawler
from .xianyu_http import XianyuHttpCrawler


def build_crawler(settings: Settings) -> BaseCrawler:
    if settings.crawler_mode == "fixture":
        return FixtureCrawler()
    if settings.crawler_mode == "xianyu_http":
        return XianyuHttpCrawler(settings.xianyu_search_url_template)
    raise ValueError(f"Unsupported crawler mode: {settings.crawler_mode}")


def crawl_keywords(
    crawler: BaseCrawler,
    keywords: list[KeywordRecord],
    snapshot_date: date,
    limit: int,
) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    for keyword in keywords:
        items.extend(crawler.crawl_keyword(keyword, snapshot_date, limit))
    return items
