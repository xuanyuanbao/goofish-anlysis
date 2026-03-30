from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from models import CrawledItem, KeywordRecord


class BaseCrawler(ABC):
    @abstractmethod
    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        raise NotImplementedError
