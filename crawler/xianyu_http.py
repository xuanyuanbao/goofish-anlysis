from __future__ import annotations

from datetime import date

from models import CrawledItem, KeywordRecord

from .base import BaseCrawler


class XianyuHttpCrawler(BaseCrawler):
    def __init__(self, search_url_template: str | None) -> None:
        self.search_url_template = search_url_template

    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        raise RuntimeError(
            "当前仓库默认提供可直接运行的 fixture 采集器。"
            "真实闲鱼 HTTP 采集依赖稳定接口、鉴权参数或 cookies，"
            "需要在确认目标请求方式后补齐 crawler/xianyu_http.py。"
        )
