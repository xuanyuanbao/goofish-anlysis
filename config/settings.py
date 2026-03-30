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
    crawler_mode: str
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
    data_dir = PROJECT_ROOT / "data"
    report_dir = PROJECT_ROOT / "reports"
    fixture_dir = PROJECT_ROOT / "fixtures"
    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        report_dir=report_dir,
        daily_report_dir=report_dir / "daily",
        weekly_report_dir=report_dir / "weekly",
        monthly_report_dir=report_dir / "monthly",
        log_dir=PROJECT_ROOT / "logs",
        fixture_dir=fixture_dir,
        sqlite_db_path=Path(os.getenv("XY_DB_PATH", data_dir / "xianyu_report.db")),
        crawler_mode=os.getenv("XY_CRAWLER_MODE", "fixture").strip() or "fixture",
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
    )
