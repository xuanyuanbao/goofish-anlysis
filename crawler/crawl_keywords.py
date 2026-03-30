from __future__ import annotations

from datetime import date

from config.settings import Settings
from models import CrawledItem, KeywordRecord

from .base import BaseCrawler
from .fixture_provider import FixtureCrawler
from .xianyu_curl import XianyuCurlCrawler
from .xianyu_http import XianyuCrawlerError, XianyuHttpCrawler


class AutoFallbackCrawler(BaseCrawler):
    def __init__(self, primary: BaseCrawler, fallback: BaseCrawler) -> None:
        self.primary = primary
        self.fallback = fallback

    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        try:
            return self.primary.crawl_keyword(keyword, snapshot_date, limit)
        except XianyuCrawlerError as exc:
            print(
                f"[WARN] Live Xianyu crawl failed for keyword={keyword.keyword}, "
                f"fallback to fixture. reason={exc}"
            )
            return self.fallback.crawl_keyword(keyword, snapshot_date, limit)


class SequentialCrawler(BaseCrawler):
    def __init__(self, crawlers: list[BaseCrawler]) -> None:
        self.crawlers = crawlers

    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        last_error: Exception | None = None
        for crawler in self.crawlers:
            try:
                return crawler.crawl_keyword(keyword, snapshot_date, limit)
            except XianyuCrawlerError as exc:
                last_error = exc
        raise XianyuCrawlerError(str(last_error) if last_error else "No live crawler available")


def build_crawler(settings: Settings) -> BaseCrawler:
    if settings.crawler_mode == "fixture":
        return FixtureCrawler()
    if settings.crawler_mode == "xianyu_http":
        return XianyuHttpCrawler(settings)
    if settings.crawler_mode == "xianyu_curl":
        return XianyuCurlCrawler(settings)
    if settings.crawler_mode == "xianyu_auto":
        primary = SequentialCrawler(
            [XianyuCurlCrawler(settings), XianyuHttpCrawler(settings)]
        )
        return AutoFallbackCrawler(primary, FixtureCrawler())
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
