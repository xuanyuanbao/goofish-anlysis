from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from importlib import import_module
import json
from pathlib import Path
from typing import Any, Iterator

from models import (
    CrawledItem,
    DailyItemScore,
    DailyKeywordStat,
    DataQualityIssue,
    JobRunRecord,
    KeywordRecord,
)

from .base import BaseDatabase


class MysqlDatabase(BaseDatabase):
    def __init__(
        self,
        *,
        project_root: Path,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str,
        connect_timeout: int,
    ) -> None:
        self.project_root = project_root
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.connect_timeout = connect_timeout

    def _pymysql(self) -> Any:
        try:
            return import_module("pymysql")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "MySQL backend requires PyMySQL. Please run `pip install PyMySQL` "
                "or install requirements.txt before using XY_DB_BACKEND=mysql."
            ) from exc

    @contextmanager
    def connect(self) -> Iterator[Any]:
        pymysql = self._pymysql()
        connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            connect_timeout=self.connect_timeout,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = (self.project_root / "db" / "mysql_init.sql").read_text(
            encoding="utf-8"
        )
        statements = [statement.strip() for statement in schema.split(";") if statement.strip()]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    def keyword_count(self) -> int:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(1) AS cnt FROM keyword_config")
                row = cursor.fetchone()
        return int(row["cnt"])

    def insert_keywords(self, rows: list[tuple[str, str, int, int]]) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO keyword_config (keyword, category, status, priority)
                    VALUES (%s, %s, %s, %s)
                    """,
                    rows,
                )

    def fetch_active_keywords(self) -> list[KeywordRecord]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, keyword, category, status, priority
                    FROM keyword_config
                    WHERE status = 1
                    ORDER BY priority ASC, keyword ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            KeywordRecord(
                id=row["id"],
                keyword=row["keyword"],
                category=row["category"],
                status=row["status"],
                priority=row["priority"],
            )
            for row in rows
        ]

    def replace_snapshots(self, snapshot_date: date, items: list[CrawledItem]) -> int:
        if not items:
            return 0
        keywords = sorted({item.keyword for item in items})
        placeholders = ",".join(["%s"] * len(keywords))
        insert_rows = [
            (
                item.snapshot_date.isoformat(),
                item.snapshot_time.isoformat(sep=" "),
                item.keyword,
                item.item_id,
                item.title,
                item.price,
                item.rank_pos,
                item.seller_name,
                item.item_url,
                item.desc_text,
                item.raw_text,
            )
            for item in items
        ]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM item_snapshot WHERE snapshot_date = %s AND keyword IN ({placeholders})",
                    [snapshot_date.isoformat(), *keywords],
                )
                cursor.executemany(
                    """
                    INSERT INTO item_snapshot (
                        snapshot_date, snapshot_time, keyword, item_id, title, price,
                        rank_pos, seller_name, item_url, desc_text, raw_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    insert_rows,
                )
        return len(insert_rows)

    def fetch_snapshots_by_date(self, snapshot_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT snapshot_date, snapshot_time, keyword, item_id, title, price,
                           rank_pos, seller_name, item_url, desc_text, raw_text
                    FROM item_snapshot
                    WHERE snapshot_date = %s
                    ORDER BY keyword ASC, rank_pos ASC
                    """,
                    (snapshot_date.isoformat(),),
                )
                rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_previous_daily_stats(self, stat_date: date) -> dict[str, dict[str, object]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                           max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                    FROM keyword_daily_stats
                    WHERE stat_date = %s
                    """,
                    (stat_date.isoformat(),),
                )
                rows = cursor.fetchall()
        return {row["keyword"]: dict(row) for row in rows}

    def replace_daily_stats(self, stat_date: date, stats: list[DailyKeywordStat]) -> int:
        if not stats:
            return 0
        insert_rows = [
            (
                row.stat_date.isoformat(),
                row.keyword,
                row.category,
                row.item_count,
                row.avg_price,
                row.min_price,
                row.max_price,
                row.top10_avg_rank,
                row.hot_score,
                row.trend_up_down,
                row.opportunity_score,
                datetime.now().isoformat(sep=" "),
            )
            for row in stats
        ]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM keyword_daily_stats WHERE stat_date = %s",
                    (stat_date.isoformat(),),
                )
                cursor.executemany(
                    """
                    INSERT INTO keyword_daily_stats (
                        stat_date, keyword, category, item_count, avg_price, min_price,
                        max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    insert_rows,
                )
        return len(insert_rows)

    def replace_item_scores(self, stat_date: date, rows: list[DailyItemScore]) -> int:
        if not rows:
            return 0
        insert_rows = [
            (
                row.stat_date.isoformat(),
                row.keyword,
                row.item_id,
                row.title,
                row.rank_pos,
                row.price,
                row.score,
                row.item_url,
            )
            for row in rows
        ]
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM item_score_daily WHERE stat_date = %s",
                    (stat_date.isoformat(),),
                )
                cursor.executemany(
                    """
                    INSERT INTO item_score_daily (
                        stat_date, keyword, item_id, title, rank_pos, price, score, item_url
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    insert_rows,
                )
        return len(insert_rows)

    def fetch_item_scores_by_date(self, stat_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT stat_date, keyword, item_id, title, rank_pos, price, score, item_url
                    FROM item_score_daily
                    WHERE stat_date = %s
                    ORDER BY keyword ASC, score DESC, rank_pos ASC
                    """,
                    (stat_date.isoformat(),),
                )
                rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetch_daily_stats_between(
        self, start_date: date, end_date: date
    ) -> list[dict[str, object]]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                           max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                    FROM keyword_daily_stats
                    WHERE stat_date BETWEEN %s AND %s
                    ORDER BY stat_date ASC, keyword ASC
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                )
                rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def record_job_run(self, row: JobRunRecord) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO job_run_history (
                        run_id, job_name, run_mode, run_status, target_label, snapshot_date,
                        started_at, finished_at, duration_seconds, keyword_total, keyword_success,
                        keyword_failed, inserted_snapshots, daily_stats, item_scores, alert_level,
                        alert_message, report_paths_json, metadata_json
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CAST(%s AS JSON), %s
                    )
                    ON DUPLICATE KEY UPDATE
                        run_status = VALUES(run_status),
                        target_label = VALUES(target_label),
                        snapshot_date = VALUES(snapshot_date),
                        started_at = VALUES(started_at),
                        finished_at = VALUES(finished_at),
                        duration_seconds = VALUES(duration_seconds),
                        keyword_total = VALUES(keyword_total),
                        keyword_success = VALUES(keyword_success),
                        keyword_failed = VALUES(keyword_failed),
                        inserted_snapshots = VALUES(inserted_snapshots),
                        daily_stats = VALUES(daily_stats),
                        item_scores = VALUES(item_scores),
                        alert_level = VALUES(alert_level),
                        alert_message = VALUES(alert_message),
                        report_paths_json = VALUES(report_paths_json),
                        metadata_json = VALUES(metadata_json)
                    """,
                    (
                        row.run_id,
                        row.job_name,
                        row.run_mode,
                        row.run_status,
                        row.target_label,
                        row.snapshot_date.isoformat() if row.snapshot_date else None,
                        row.started_at.isoformat(sep=" "),
                        row.finished_at.isoformat(sep=" "),
                        row.duration_seconds,
                        row.keyword_total,
                        row.keyword_success,
                        row.keyword_failed,
                        row.inserted_snapshots,
                        row.daily_stats,
                        row.item_scores,
                        row.alert_level,
                        row.alert_message,
                        json.dumps(row.report_paths or [], ensure_ascii=False),
                        row.metadata_json,
                    ),
                )

    def replace_keyword_failures(
        self,
        run_id: str,
        job_name: str,
        failures: list[dict[str, object]],
    ) -> int:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM keyword_failure_log WHERE run_id = %s",
                    (run_id,),
                )
                if not failures:
                    return 0
                cursor.executemany(
                    """
                    INSERT INTO keyword_failure_log (
                        run_id, job_name, snapshot_date, keyword, category, error_type, error_message
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            run_id,
                            job_name,
                            failure.get("snapshot_date"),
                            failure.get("keyword"),
                            failure.get("category"),
                            failure.get("error_type"),
                            failure.get("error_message"),
                        )
                        for failure in failures
                    ],
                )
        return len(failures)

    def replace_data_quality_issues(
        self,
        run_id: str,
        issues: list[DataQualityIssue],
    ) -> int:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM data_quality_issue WHERE run_id = %s",
                    (run_id,),
                )
                if not issues:
                    return 0
                cursor.executemany(
                    """
                    INSERT INTO data_quality_issue (
                        run_id, snapshot_date, keyword, item_id, issue_type, severity,
                        issue_message, sample_value
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            run_id,
                            issue.snapshot_date.isoformat()
                            if issue.snapshot_date
                            else None,
                            issue.keyword,
                            issue.item_id,
                            issue.issue_type,
                            issue.severity,
                            issue.issue_message,
                            issue.sample_value,
                        )
                        for issue in issues
                    ],
                )
        return len(issues)
