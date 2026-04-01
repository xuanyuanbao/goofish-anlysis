from __future__ import annotations

import atexit
import json
import time
import urllib.parse
import urllib.error
from http.cookies import SimpleCookie
from pathlib import Path

from config.settings import Settings

from .xianyu_http import XianyuCrawlerBlockedError, XianyuCrawlerError, XianyuHttpCrawler


class XianyuBrowserCrawler(XianyuHttpCrawler):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.browser_headless = settings.xianyu_browser_headless
        self.browser_channel = settings.xianyu_browser_channel
        self.browser_executable_path = settings.xianyu_browser_executable_path
        self.browser_user_data_dir = settings.xianyu_browser_user_data_dir
        self.browser_storage_state_path = settings.xianyu_browser_storage_state_path
        self.browser_timeout_ms = settings.xianyu_browser_timeout_ms
        self.browser_response_wait_ms = settings.xianyu_browser_response_wait_ms
        self.browser_manual_wait_seconds = settings.xianyu_browser_manual_wait_seconds
        self.browser_start_url = settings.xianyu_browser_start_url
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._manual_wait_done = False
        self._playwright_timeout_error = None
        atexit.register(self.close)

    def close(self) -> None:
        try:
            self._save_storage_state()
        except Exception:
            pass
        for target in (self._context, self._browser, self._playwright):
            try:
                if target is not None:
                    target.close()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def _make_request(
        self, request_url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        page = self._ensure_page()
        keyword = _extract_keyword_from_request_url(request_url)
        captured: list[str] = []

        def on_response(response) -> None:  # pragma: no cover - exercised via manual run
            if self.api_name not in response.url:
                return
            try:
                captured.append(response.text())
            except Exception:
                return

        page.on('response', on_response)
        try:
            if keyword:
                page.goto(self._build_search_page_url(keyword), wait_until='domcontentloaded')
                page.wait_for_timeout(self.browser_response_wait_ms)
            if captured:
                return captured[-1], {'set-cookie': []}
            return self._fetch_via_browser(request_url, headers), {'set-cookie': []}
        finally:
            page.remove_listener('response', on_response)
            self._save_storage_state()

    def _make_text_request(
        self, url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        page = self._ensure_page()
        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_timeout(min(self.browser_response_wait_ms, 1500))
        self._save_storage_state()
        return page.content(), {'set-cookie': []}

    def _build_api_headers(self) -> dict[str, str]:
        headers = super()._build_api_headers()
        for blocked_key in ('Cookie', 'Origin', 'Referer', 'User-Agent', 'Accept-Language'):
            headers.pop(blocked_key, None)
        return headers

    def _build_detail_headers(self, item_url: str) -> dict[str, str]:
        headers = super()._build_detail_headers(item_url)
        for blocked_key in ('Cookie', 'Referer', 'User-Agent', 'Accept-Language'):
            headers.pop(blocked_key, None)
        return headers

    def _ensure_page(self):
        if self._page is not None:
            return self._page

        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise XianyuCrawlerError(
                'xianyu_browser mode requires Playwright. Install it with '
                '`py -m pip install playwright` and then run '
                '`python -m playwright install chrome` or point to a local Chrome.'
            ) from exc

        self._playwright_timeout_error = PlaywrightTimeoutError
        self._playwright = sync_playwright().start()
        chromium = self._playwright.chromium
        launch_kwargs = {
            'headless': self.browser_headless,
            'channel': self.browser_channel,
            'executable_path': self.browser_executable_path,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--lang=zh-CN',
            ],
        }
        launch_kwargs = {key: value for key, value in launch_kwargs.items() if value not in (None, '')}

        if self.browser_user_data_dir is not None:
            self.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
            self._context = chromium.launch_persistent_context(
                user_data_dir=str(self.browser_user_data_dir),
                **launch_kwargs,
            )
        else:
            self._browser = chromium.launch(**launch_kwargs)
            context_kwargs = {
                'user_agent': self.settings.user_agent,
                'locale': 'zh-CN',
                'viewport': {'width': 1440, 'height': 900},
            }
            if self.browser_storage_state_path and self.browser_storage_state_path.exists():
                context_kwargs['storage_state'] = str(self.browser_storage_state_path)
            self._context = self._browser.new_context(**context_kwargs)

        self._context.set_default_timeout(self.browser_timeout_ms)
        try:
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
        except Exception:
            pass
        if self.settings.xianyu_cookie_string:
            cookies = _cookies_for_browser(self.settings.xianyu_cookie_string)
            if cookies:
                self._context.add_cookies(cookies)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto(self.browser_start_url, wait_until='domcontentloaded')
        if self.browser_manual_wait_seconds > 0 and not self._manual_wait_done:
            print(
                '[INFO] Browser warm-up window is open. '
                'Use this time to finish login or slider verification if needed.'
            )
            self._page.wait_for_timeout(int(self.browser_manual_wait_seconds * 1000))
            self._manual_wait_done = True
        return self._page

    def _fetch_via_browser(self, request_url: str, headers: dict[str, str]) -> str:
        page = self._ensure_page()
        payload = page.evaluate(
            """async ({url, headers}) => {
                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers,
                });
                return {
                    ok: response.ok,
                    text: await response.text(),
                    url: response.url,
                    status: response.status,
                };
            }""",
            {
                'url': request_url,
                'headers': _safe_browser_headers(headers),
            },
        )
        text = payload.get('text') or ''
        if not text:
            raise urllib.error.URLError(f'Empty browser response. status={payload.get("status")}')
        return text

    def _build_search_page_url(self, keyword: str) -> str:
        template = self.settings.xianyu_search_url_template
        encoded = urllib.parse.quote(keyword)
        if template:
            return template.replace('{keyword}', encoded)
        return f'https://www.goofish.com/search?q={encoded}'

    def _save_storage_state(self) -> None:
        if self._context is None or self.browser_storage_state_path is None:
            return
        self.browser_storage_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(self.browser_storage_state_path))


SAFE_BROWSER_HEADER_NAMES = {'accept', 'content-type', 'x-requested-with'}
BROWSER_COOKIE_DOMAINS = ('.goofish.com', '.m.goofish.com', '.taobao.com')


def _safe_browser_headers(headers: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SAFE_BROWSER_HEADER_NAMES:
            safe[key] = value
    return safe


def _extract_keyword_from_request_url(request_url: str) -> str | None:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(request_url).query)
    data_values = query.get('data')
    if not data_values:
        return None
    try:
        payload = json.loads(data_values[0])
    except json.JSONDecodeError:
        return None
    keyword = payload.get('keyword')
    if not isinstance(keyword, str):
        return None
    return keyword.strip() or None


def _cookies_for_browser(cookie_string: str) -> list[dict[str, object]]:
    jar = SimpleCookie()
    jar.load(cookie_string)
    cookies: list[dict[str, object]] = []
    for key, morsel in jar.items():
        for domain in BROWSER_COOKIE_DOMAINS:
            cookies.append(
                {
                    'name': key,
                    'value': morsel.value,
                    'domain': domain,
                    'path': '/',
                    'httpOnly': False,
                    'secure': True,
                    'sameSite': 'Lax',
                }
            )
    return cookies
