from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


APP_TIMEZONE_NAME = 'Asia/Shanghai'
if ZoneInfo is not None:
    try:
        APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)
    except ZoneInfoNotFoundError:  # pragma: no cover
        APP_TIMEZONE = timezone(timedelta(hours=8), name=APP_TIMEZONE_NAME)
else:  # pragma: no cover
    APP_TIMEZONE = timezone(timedelta(hours=8), name=APP_TIMEZONE_NAME)


def shanghai_now() -> datetime:
    return datetime.now(APP_TIMEZONE).replace(microsecond=0, tzinfo=None)


def shanghai_today() -> date:
    return shanghai_now().date()


def shanghai_month_label() -> str:
    return shanghai_today().strftime('%Y-%m')


def shanghai_timestamp_string() -> str:
    return shanghai_now().isoformat(sep=' ')


def sqlite_local_timestamp_sql() -> str:
    return "STRFTIME('%Y-%m-%d %H:%M:%S', 'now', 'localtime')"