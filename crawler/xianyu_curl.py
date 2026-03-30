from __future__ import annotations

import re
import subprocess
import urllib.error

from config.settings import Settings

from .xianyu_http import XianyuCrawlerError, XianyuHttpCrawler


class XianyuCurlCrawler(XianyuHttpCrawler):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.curl_bin = settings.xianyu_curl_bin

    def _make_request(
        self, request_url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        return self._run_curl(request_url, headers)

    def _make_text_request(
        self, url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        return self._run_curl(url, headers)

    def _run_curl(
        self, url: str, headers: dict[str, str]
    ) -> tuple[str, dict[str, list[str]]]:
        command = [
            self.curl_bin,
            "--location",
            "--compressed",
            "--http1.1",
            "--silent",
            "--show-error",
            "--max-time",
            str(int(self.timeout_seconds)),
            "--dump-header",
            "-",
            url,
        ]
        for key, value in headers.items():
            command.extend(["-H", f"{key}: {value}"])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=False,
                check=False,
            )
        except FileNotFoundError as exc:
            raise XianyuCrawlerError(
                f"curl binary not found: {self.curl_bin}. "
                "Install curl on Linux or set XY_XIANYU_CURL_BIN."
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise urllib.error.URLError(
                f"curl request failed with exit code {result.returncode}: {stderr}"
            )

        merged = result.stdout.decode("utf-8", errors="replace")
        header_text, body = _split_headers_and_body(merged)
        response_headers = {
            "set-cookie": _extract_set_cookie_headers(header_text),
        }
        return body, response_headers


def _split_headers_and_body(raw_text: str) -> tuple[str, str]:
    remaining = raw_text.lstrip("\ufeff")
    header_block = ""

    while remaining.startswith("HTTP/"):
        match = re.search(r"\r?\n\r?\n", remaining)
        if not match:
            return header_block, remaining
        header_block = remaining[: match.start()]
        remaining = remaining[match.end() :]
        if not remaining.startswith("HTTP/"):
            return header_block, remaining

    return "", raw_text


def _extract_set_cookie_headers(header_text: str) -> list[str]:
    if not header_text:
        return []
    cookies: list[str] = []
    for line in header_text.splitlines():
        if line.lower().startswith("set-cookie:"):
            cookies.append(line.split(":", 1)[1].strip())
    return cookies
