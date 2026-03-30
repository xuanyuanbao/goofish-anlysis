from __future__ import annotations

import hashlib
import json
import re
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


TOKEN_ERROR_MARKERS = ("FAIL_SYS_TOKEN_EXOIRED", "FAIL_SYS_TOKEN_EMPTY")
ANTI_BOT_MARKERS = (
    "RGV587_ERROR",
    "\u975e\u6cd5\u8bbf\u95ee",
    "baxia",
    "\u8bf7\u7a0d\u540e\u91cd\u8bd5",
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
        self.cookies = SimpleCookie()
        self._load_cookie_string(settings.xianyu_cookie_string)

    def crawl_keyword(
        self, keyword: KeywordRecord, snapshot_date: date, limit: int
    ) -> list[CrawledItem]:
        if limit <= 0:
            return []

        collected: list[CrawledItem] = []
        page_number = 1
        while len(collected) < limit:
            response = self._search(
                keyword.keyword,
                page_number,
                min(limit - len(collected), self.rows_per_page),
            )
            page_items = self._parse_search_items(response, keyword, snapshot_date)
            if not page_items:
                break
            collected.extend(page_items)
            if len(page_items) < self.rows_per_page:
                break
            page_number += 1
            if self.request_delay_seconds > 0:
                time.sleep(self.request_delay_seconds)
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
            headers = self._build_headers()
            request = urllib.request.Request(request_url, headers=headers, method="GET")

            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw_text = response.read().decode("utf-8", errors="replace")
                    self._merge_set_cookie_headers(response.headers.get_all("Set-Cookie") or [])
                    parsed = self._decode_response(raw_text)
            except urllib.error.HTTPError as exc:
                raw_text = exc.read().decode("utf-8", errors="replace")
                self._merge_set_cookie_headers(exc.headers.get_all("Set-Cookie") or [])
                parsed = self._decode_response(raw_text)
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt >= self.retry_count:
                    break
                time.sleep(min(1 + attempt, 3))
                continue

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

    def _build_headers(self) -> dict[str, str]:
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

    def _build_search_referer(self) -> str:
        template = self.settings.xianyu_search_url_template
        keyword = urllib.parse.quote("\u9ad8\u8003\u771f\u9898\u89e3\u6790")
        if template:
            return template.replace("{keyword}", keyword)
        return f"https://www.goofish.com/search?q={keyword}"

    def _decode_response(self, raw_text: str) -> XianyuResponse:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise XianyuCrawlerError(
                f"Xianyu returned non-JSON content: {raw_text[:300]}"
            ) from exc
        return XianyuResponse(payload=payload, raw_text=raw_text, headers={})

    def _parse_search_items(
        self,
        response: XianyuResponse,
        keyword: KeywordRecord,
        snapshot_date: date,
    ) -> list[CrawledItem]:
        nodes = self._extract_item_nodes(response.payload.get("data"))
        items: list[CrawledItem] = []
        seen_keys: set[str] = set()

        for rank_pos, node in enumerate(nodes, start=1):
            item = self._normalize_item_node(node, keyword, snapshot_date, rank_pos)
            if item is None:
                continue
            dedupe_key = item.item_id or f"{item.title}|{item.price}|{item.seller_name}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            items.append(item)
        return items

    def _normalize_item_node(
        self,
        node: dict[str, object],
        keyword: KeywordRecord,
        snapshot_date: date,
        rank_pos: int,
    ) -> CrawledItem | None:
        data = node.get("data") if isinstance(node.get("data"), dict) else node
        if not isinstance(data, dict):
            return None

        main = self._as_dict(self._deep_get(data, "item", "main"))
        ex_content = self._as_dict(main.get("exContent"))
        click_param = self._as_dict(main.get("clickParam"))
        user_info = self._as_dict(data.get("userInfo"))

        target_url = self._first_non_empty(
            self._stringify(click_param.get("targetUrl")),
            self._stringify(data.get("itemUrl")),
            self._stringify(data.get("targetUrl")),
            self._stringify(self._deep_get(data, "shareInfo", "targetUrl")),
        )
        item_id = self._first_non_empty(
            self._stringify(data.get("id")),
            self._stringify(click_param.get("itemId")),
            self._extract_item_id(target_url),
        )
        title = self._first_non_empty(
            self._stringify(data.get("title")),
            self._stringify(ex_content.get("title")),
            self._stringify(ex_content.get("mainTitle")),
            self._stringify(self._deep_get(ex_content, "content", "title")),
        )
        if not title:
            return None

        price = self._first_float(
            data.get("price"),
            ex_content.get("price"),
            self._deep_get(data, "priceInfo", "price"),
            self._deep_get(ex_content, "priceInfo", "price"),
            data.get("priceText"),
            ex_content.get("priceText"),
        )
        seller_name = self._first_non_empty(
            self._stringify(user_info.get("nickName")),
            self._stringify(user_info.get("userNick")),
            self._stringify(data.get("sellerNick")),
            self._stringify(data.get("city")),
        )
        item_url = self._normalize_item_url(target_url, item_id)
        desc_text = self._first_non_empty(
            self._stringify(data.get("desc")),
            self._stringify(data.get("summary")),
            self._stringify(ex_content.get("desc")),
            self._stringify(ex_content.get("subTitle")),
        )
        snapshot_time = datetime.combine(snapshot_date, datetime.now().time())

        return CrawledItem(
            snapshot_date=snapshot_date,
            snapshot_time=snapshot_time,
            keyword=keyword.keyword,
            item_id=item_id,
            title=title,
            price=price,
            rank_pos=rank_pos,
            seller_name=seller_name,
            item_url=item_url,
            desc_text=desc_text,
            raw_text=json.dumps(node, ensure_ascii=False, separators=(",", ":")),
            category=keyword.category,
        )

    def _extract_item_nodes(self, payload: object) -> list[dict[str, object]]:
        if payload is None:
            return []

        nodes: list[dict[str, object]] = []

        def walk(node: object) -> None:
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return
            if self._looks_like_item_node(node):
                nodes.append(node)
                return
            for value in node.values():
                walk(value)

        walk(payload)
        return nodes

    def _looks_like_item_node(self, node: dict[str, object]) -> bool:
        data = node.get("data") if isinstance(node.get("data"), dict) else node
        if not isinstance(data, dict):
            return False
        if data.get("title") and any(key in data for key in ("id", "price", "picUrl")):
            return True
        main = self._as_dict(self._deep_get(data, "item", "main"))
        ex_content = self._as_dict(main.get("exContent"))
        return bool(main and (ex_content.get("title") or self._as_dict(main.get("clickParam")).get("targetUrl")))

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

    @staticmethod
    def _normalize_item_url(target_url: str | None, item_id: str | None) -> str | None:
        if target_url:
            if target_url.startswith("//"):
                return f"https:{target_url}"
            if target_url.startswith("http://") or target_url.startswith("https://"):
                return target_url
            if target_url.startswith("/"):
                return f"https://www.goofish.com{target_url}"
        if item_id:
            return f"https://www.goofish.com/item?id={item_id}"
        return None

    @staticmethod
    def _extract_item_id(url: str | None) -> str | None:
        if not url:
            return None
        match = re.search(r"(?:id|itemId)=([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/item/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _deep_get(obj: object, *path: str) -> object | None:
        current = obj
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _as_dict(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _stringify(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _first_non_empty(*values: object) -> str | None:
        for value in values:
            text = XianyuHttpCrawler._stringify(value)
            if text:
                return text
        return None

    @staticmethod
    def _first_float(*values: object) -> float | None:
        for value in values:
            number = XianyuHttpCrawler._coerce_float(value)
            if number is not None:
                return number
        return None

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        if isinstance(value, dict):
            for key in ("price", "amount", "value", "priceValue"):
                if key in value:
                    number = XianyuHttpCrawler._coerce_float(value.get(key))
                    if number is not None:
                        return number
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", str(value))
        if not match:
            return None
        return round(float(match.group(1)), 2)
