from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from http.cookies import SimpleCookie

from config.settings import Settings
from models import CrawledItem, KeywordRecord

from .base import BaseCrawler
from .parser import extract_detail_description, merge_descriptions, parse_search_items


TOKEN_ERROR_MARKERS = ("FAIL_SYS_TOKEN_EXOIRED", "FAIL_SYS_TOKEN_EMPTY")
ANTI_BOT_MARKERS = (
    "RGV587_ERROR",
    "非法访问",
    "baxia",
    "请稍后重试",
)


@dataclass(slots=True)
class XianyuResponse:
    payload: dict[str, object]
    raw_text: str
    headers: dict[str, str]


class XianyuCrawlerError(RuntimeError):
    """Base error for live Xianyu crawling."""


class XianyuCrawlerBlockedError(XianyuCrawlerError):
    """Raised when the request is blocked by anti-bot or auth controls."""


class XianyuHttpCrawler(BaseCrawler):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_base = settings.xianyu_api_base.rstrip("/")
        self.api_name = settings.xianyu_api_name
        self.api_version = settings.xianyu_api_version
        self.app_key = settings.xianyu_app_key
        self.rows_per_page = settings.xianyu_rows_per_page
        self.timeout_seconds = settings.xianyu_timeout_seconds
        self.retry_count = settings.xianyu_retry_count
        self.request_delay_seconds = settings.xianyu_request_delay_seconds
        self.detail_fetch_enabled = settings.xianyu_detail_fetch_enabled
        self.detail_max_items = max(0, settings.xianyu_detail_max_items_per_keyword)
        self.detail_min_length = max(0, settings.xianyu_detail_min_length)
        self.cookies = SimpleCookie()
        self._load_cookie_string(settings.xianyu_cookie_string)

    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        if limit <= 0:
            return []

        collected: list[CrawledItem] = []
        page_number = 1
        snapshot_time = datetime.now().replace(microsecond=0)

        while len(collected) < limit:
            response = self._search(
                keyword.keyword,
                page_number,
                min(limit - len(collected), self.rows_per_page),
            )
            page_items = parse_search_items(
                response.payload.get("data"),
                keyword,
                snapshot_date,
                snapshot_time,
            )
            if not page_items:
                break
            collected.extend(page_items)
            if len(page_items) < self.rows_per_page:
                break
            page_number += 1
            if self.request_delay_seconds > 0:
                time.sleep(self.request_delay_seconds)

        self._enrich_detail_descriptions(collected[:limit])
        return collected[:limit]

    def _search(
        self, keyword: str, page_number: int, rows_per_page: int
    ) -> XianyuResponse:
        payload = {
            "pageNumber": page_number,
            "keyword": keyword,
            "rowsPerPage": rows_per_page,
            "searchReqFromPage": "pcSearch",
        }
        return self._request_mtop(payload)

    def _request_mtop(self, payload: dict[str, object]) -> XianyuResponse:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        last_error: Exception | None = None

        for attempt in range(self.retry_count + 1):
            request_url = self._build_request_url(data)
            headers = self._build_api_headers()
            try:
                raw_text, response_headers = self._make_request(request_url, headers)
                parsed = self._decode_response(raw_text)
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt >= self.retry_count:
                    break
                time.sleep(min(1 + attempt, 3))
                continue

            if response_headers:
                self._merge_set_cookie_headers(response_headers.get("set-cookie", []))

            if self._is_token_error(parsed.payload):
                if attempt >= self.retry_count:
                    raise XianyuCrawlerBlockedError(
                        "Xianyu token bootstrap failed. Provide a fresh "
                        "XY_XIANYU_COOKIE_STRING that includes _m_h5_tk."
                    )
                continue

            if self._is_anti_bot(parsed.payload):
                raise XianyuCrawlerBlockedError(
                    "Xianyu blocked the live request. Provide a fresh browser "
                    "cookie via XY_XIANYU_COOKIE_STRING, reduce request frequency, "
                    "or switch back to fixture mode for local testing."
                )

            return parsed

        raise XianyuCrawlerError(f"Xianyu request failed after retries: {last_error}")

    def _enrich_detail_descriptions(self, items: list[CrawledItem]) -> None:
        if not self.detail_fetch_enabled or not items:
            return

        enriched = 0
        for item in items:
            if enriched >= self.detail_max_items:
                break
            if item.desc_text and len(item.desc_text) >= self.detail_min_length:
                continue
            if not item.item_url:
                continue
            detail_desc = self._fetch_detail_description(item.item_url)
            merged = merge_descriptions(item.desc_text, detail_desc)
            if merged and merged != item.desc_text:
                item.desc_text = merged
            enriched += 1
            if self.request_delay_seconds > 0:
                time.sleep(min(self.request_delay_seconds, 1.2))

    def _fetch_detail_description(self, item_url: str) -> str | None:
        headers = self._build_detail_headers(item_url)
        try:
            raw_html, response_headers = self._make_text_request(item_url, headers)
        except urllib.error.URLError:
            return None
        if response_headers:
            self._merge_set_cookie_headers(response_headers.get("set-cookie", []))
        return extract_detail_description(raw_html)

    def _build_request_url(self, data: str) -> str:
        timestamp = str(int(time.time() * 1000))
        token = self._get_mtop_token()
        sign = hashlib.md5(
            f"{token}&{timestamp}&{self.app_key}&{data}".encode("utf-8")
        ).hexdigest()
        params = {
            "jsv": "2.7.2",
            "appKey": self.app_key,
            "t": timestamp,
            "sign": sign,
            "api": self.api_name,
            "v": self.api_version,
            "type": "originaljson",
            "dataType": "json",
            "timeout": str(int(self.timeout_seconds * 1000)),
            "needLogin": "false",
            "needLoginPC": "false",
            "preventFallback": "true",
            "sessionOption": "AutoLoginOnly",
            "accountSite": "xianyu",
            "data": data,
        }
        query = urllib.parse.urlencode(params)
        return f"{self.api_base}/{self.api_name}/{self.api_version}/?{query}"

    def _build_api_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self._build_search_referer(),
            "Origin": "https://www.goofish.com",
        }
        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    def _build_detail_headers(self, item_url: str) -> dict[str, str]:
        headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self._build_search_referer(),
        }
        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    def _build_search_referer(self) -> str:
        template = self.settings.xianyu_search_url_template
        keyword = urllib.parse.quote("高考真题解析")
        if template:
            return template.replace("{keyword}", keyword)
        return f"https://www.goofish.com/search?q={keyword}"

    def _make_request(
        self, request_url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        request = urllib.request.Request(request_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_text = response.read().decode("utf-8", errors="replace")
                response_headers = {
                    "set-cookie": response.headers.get_all("Set-Cookie") or []
                }
                return raw_text, response_headers
        except urllib.error.HTTPError as exc:
            raw_text = exc.read().decode("utf-8", errors="replace")
            response_headers = {
                "set-cookie": exc.headers.get_all("Set-Cookie") or []
            }
            return raw_text, response_headers

    def _make_text_request(
        self, url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        return self._make_request(url, headers)

    def _decode_response(self, raw_text: str) -> XianyuResponse:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise XianyuCrawlerError(
                f"Xianyu returned non-JSON content: {raw_text[:300]}"
            ) from exc
        return XianyuResponse(payload=payload, raw_text=raw_text, headers={})

    def _load_cookie_string(self, cookie_string: str | None) -> None:
        if cookie_string:
            self.cookies.load(cookie_string)

    def _merge_set_cookie_headers(self, headers: list[str]) -> None:
        for header in headers:
            jar = SimpleCookie()
            jar.load(header)
            for key, morsel in jar.items():
                self.cookies[key] = morsel.value

    def _cookie_header(self) -> str:
        return "; ".join(f"{key}={morsel.value}" for key, morsel in self.cookies.items())

    def _get_mtop_token(self) -> str:
        token_value = self.cookies.get("_m_h5_tk")
        if token_value is None:
            return ""
        return token_value.value.split("_", 1)[0]

    @staticmethod
    def _is_token_error(payload: dict[str, object]) -> bool:
        ret = payload.get("ret") or []
        return any(marker in " ".join(ret) for marker in TOKEN_ERROR_MARKERS)

    @staticmethod
    def _is_anti_bot(payload: dict[str, object]) -> bool:
        ret = " ".join(payload.get("ret") or [])
        body = json.dumps(payload.get("data") or {}, ensure_ascii=False)
        return any(marker in ret or marker in body for marker in ANTI_BOT_MARKERS)
