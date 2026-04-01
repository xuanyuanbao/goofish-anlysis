from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from config.settings import Settings
from models import CrawledItem, KeywordRecord

from .base import BaseCrawler
from .fixture_provider import FixtureCrawler
from .xianyu_curl import XianyuCurlCrawler
from .xianyu_http import XianyuCrawlerError, XianyuHttpCrawler


@dataclass(slots=True)
class KeywordCrawlFailure:
    keyword: str
    category: str
    snapshot_date: date
    error_type: str
    error_message: str

    def to_dict(self) -> dict[str, object]:
        return {
            'keyword': self.keyword,
            'category': self.category,
            'snapshot_date': self.snapshot_date.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
        }


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
                f'[WARN] Live Xianyu crawl failed for keyword={keyword.keyword}, '
                f'fallback to fixture. reason={exc}'
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
        raise XianyuCrawlerError(
            str(last_error) if last_error else 'No live crawler available'
        )


def build_crawler(settings: Settings) -> BaseCrawler:
    if settings.crawler_mode == 'fixture':
        return FixtureCrawler()
    if settings.crawler_mode == 'xianyu_http':
        return XianyuHttpCrawler(settings)
    if settings.crawler_mode == 'xianyu_curl':
        return XianyuCurlCrawler(settings)
    if settings.crawler_mode == 'xianyu_browser':
        from .xianyu_browser import XianyuBrowserCrawler

        return XianyuBrowserCrawler(settings)
    if settings.crawler_mode == 'xianyu_auto':
        primary = SequentialCrawler([XianyuCurlCrawler(settings), XianyuHttpCrawler(settings)])
        return AutoFallbackCrawler(primary, FixtureCrawler())
    raise ValueError(f'Unsupported crawler mode: {settings.crawler_mode}')


def crawl_keywords(
    crawler: BaseCrawler,
    keywords: list[KeywordRecord],
    snapshot_date: date,
    limit: int,
    task_logger: logging.Logger | None = None,
    error_logger: logging.Logger | None = None,
    continue_on_error: bool = True,
) -> tuple[list[CrawledItem], list[KeywordCrawlFailure]]:
    items: list[CrawledItem] = []
    failures: list[KeywordCrawlFailure] = []

    for keyword in keywords:
        try:
            keyword_items = crawler.crawl_keyword(keyword, snapshot_date, limit)
        except Exception as exc:
            failure = KeywordCrawlFailure(
                keyword=keyword.keyword,
                category=keyword.category,
                snapshot_date=snapshot_date,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            failures.append(failure)
            if task_logger is not None:
                task_logger.warning(
                    'Keyword crawl failed: keyword=%s category=%s reason=%s',
                    keyword.keyword,
                    keyword.category,
                    exc,
                )
            if error_logger is not None:
                error_logger.exception(
                    'Keyword crawl failed: keyword=%s category=%s snapshot_date=%s',
                    keyword.keyword,
                    keyword.category,
                    snapshot_date.isoformat(),
                )
            if not continue_on_error:
                raise
            continue

        items.extend(keyword_items)
        if task_logger is not None:
            task_logger.info(
                'Keyword crawl succeeded: keyword=%s category=%s item_count=%s',
                keyword.keyword,
                keyword.category,
                len(keyword_items),
            )

    return items, failures
