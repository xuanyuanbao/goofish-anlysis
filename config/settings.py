from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    data_dir: Path
    report_dir: Path
    daily_report_dir: Path
    weekly_report_dir: Path
    monthly_report_dir: Path
    log_dir: Path
    fixture_dir: Path
    sqlite_db_path: Path
    db_backend: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_charset: str
    mysql_connect_timeout: int
    crawler_mode: str
    allow_fixture_write: bool
    default_limit: int
    user_agent: str
    xianyu_search_url_template: str | None
    xianyu_cookie_string: str | None
    xianyu_api_base: str
    xianyu_api_name: str
    xianyu_api_version: str
    xianyu_app_key: str
    xianyu_rows_per_page: int
    xianyu_timeout_seconds: float
    xianyu_retry_count: int
    xianyu_request_delay_seconds: float
    xianyu_detail_fetch_enabled: bool
    xianyu_detail_max_items_per_keyword: int
    xianyu_detail_min_length: int
    xianyu_curl_bin: str

    def ensure_directories(self) -> None:
        for directory in (
            self.data_dir,
            self.report_dir,
            self.daily_report_dir,
            self.weekly_report_dir,
            self.monthly_report_dir,
            self.log_dir,
            self.fixture_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    data_dir = Path(os.getenv("XY_DATA_DIR", PROJECT_ROOT / "data"))
    report_dir = Path(os.getenv("XY_REPORT_DIR", PROJECT_ROOT / "reports"))
    fixture_dir = Path(os.getenv("XY_FIXTURE_DIR", PROJECT_ROOT / "fixtures"))
    log_dir = Path(os.getenv("XY_LOG_DIR", PROJECT_ROOT / "logs"))
    db_backend = (os.getenv("XY_DB_BACKEND", "sqlite").strip() or "sqlite").lower()
    raw_allow_fixture_write = os.getenv("XY_ALLOW_FIXTURE_WRITE")
    if raw_allow_fixture_write is None:
        allow_fixture_write = db_backend == "sqlite"
    else:
        allow_fixture_write = _as_bool(raw_allow_fixture_write)
    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        report_dir=report_dir,
        daily_report_dir=report_dir / "daily",
        weekly_report_dir=report_dir / "weekly",
        monthly_report_dir=report_dir / "monthly",
        log_dir=log_dir,
        fixture_dir=fixture_dir,
        sqlite_db_path=Path(
            os.getenv("XY_DB_PATH", data_dir / "xianyu_report.db")
        ),
        db_backend=db_backend,
        mysql_host=os.getenv("XY_MYSQL_HOST", "127.0.0.1"),
        mysql_port=int(os.getenv("XY_MYSQL_PORT", "3306")),
        mysql_user=os.getenv("XY_MYSQL_USER", "xianyu"),
        mysql_password=os.getenv("XY_MYSQL_PASSWORD", "xianyu123456"),
        mysql_database=os.getenv("XY_MYSQL_DATABASE", "xianyu_report"),
        mysql_charset=os.getenv("XY_MYSQL_CHARSET", "utf8mb4"),
        mysql_connect_timeout=int(os.getenv("XY_MYSQL_CONNECT_TIMEOUT", "10")),
        crawler_mode=os.getenv("XY_CRAWLER_MODE", "fixture").strip() or "fixture",
        allow_fixture_write=allow_fixture_write,
        default_limit=int(os.getenv("XY_DEFAULT_LIMIT", "30")),
        user_agent=os.getenv(
            "XY_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ),
        xianyu_search_url_template=(
            os.getenv("XY_XIANYU_SEARCH_URL_TEMPLATE")
            or os.getenv("XYANYU_SEARCH_URL_TEMPLATE")
        ),
        xianyu_cookie_string=os.getenv("XY_XIANYU_COOKIE_STRING"),
        xianyu_api_base=os.getenv(
            "XY_XIANYU_API_BASE",
            "https://h5api.m.goofish.com/h5",
        ),
        xianyu_api_name=os.getenv(
            "XY_XIANYU_API_NAME",
            "mtop.taobao.idlemtopsearch.pc.search",
        ),
        xianyu_api_version=os.getenv("XY_XIANYU_API_VERSION", "1.0"),
        xianyu_app_key=os.getenv("XY_XIANYU_APP_KEY", "34839810"),
        xianyu_rows_per_page=int(os.getenv("XY_XIANYU_ROWS_PER_PAGE", "30")),
        xianyu_timeout_seconds=float(os.getenv("XY_XIANYU_TIMEOUT_SECONDS", "20")),
        xianyu_retry_count=int(os.getenv("XY_XIANYU_RETRY_COUNT", "2")),
        xianyu_request_delay_seconds=float(
            os.getenv("XY_XIANYU_REQUEST_DELAY_SECONDS", "0.8")
        ),
        xianyu_detail_fetch_enabled=_as_bool(
            os.getenv("XY_XIANYU_FETCH_DETAIL_DESC", "1")
        ),
        xianyu_detail_max_items_per_keyword=int(
            os.getenv("XY_XIANYU_DETAIL_MAX_ITEMS_PER_KEYWORD", "5")
        ),
        xianyu_detail_min_length=int(
            os.getenv("XY_XIANYU_DETAIL_MIN_LENGTH", "18")
        ),
        xianyu_curl_bin=os.getenv("XY_XIANYU_CURL_BIN", "curl"),
    )


def _as_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}
