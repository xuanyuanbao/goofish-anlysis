from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

from models import (
    CrawledItem,
    DailyItemScore,
    DailyKeywordStat,
    DataQualityIssue,
    JobRunRecord,
    KeywordRecord,
)
from utils.time_utils import shanghai_timestamp_string

from .base import BaseDatabase


class SqliteDatabase(BaseDatabase):
    def __init__(self, db_path: Path, project_root: Path) -> None:
        self.db_path = db_path
        self.project_root = project_root

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = (self.project_root / 'db' / 'sqlite_init.sql').read_text(
            encoding='utf-8'
        )
        with self.connect() as connection:
            connection.executescript(schema)

    def keyword_count(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                'SELECT COUNT(1) AS cnt FROM keyword_config'
            ).fetchone()
        return int(row['cnt'])

    def insert_keywords(self, rows: list[tuple[str, str, int, int]]) -> None:
        current_ts = shanghai_timestamp_string()
        insert_rows = [(*row, current_ts, current_ts) for row in rows]
        with self.connect() as connection:
            connection.executemany(
                '''
                INSERT OR IGNORE INTO keyword_config (
                    keyword, category, status, priority, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                insert_rows,
            )

    def fetch_active_keywords(self) -> list[KeywordRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                '''
                SELECT id, keyword, category, status, priority
                FROM keyword_config
                WHERE status = 1
                ORDER BY priority ASC, keyword ASC
                '''
            ).fetchall()
        return [
            KeywordRecord(
                id=row['id'],
                keyword=row['keyword'],
                category=row['category'],
                status=row['status'],
                priority=row['priority'],
            )
            for row in rows
        ]

    def replace_snapshots(self, snapshot_date: date, items: list[CrawledItem]) -> int:
        if not items:
            return 0
        keywords = sorted({item.keyword for item in items})
        placeholders = ','.join('?' for _ in keywords)
        current_ts = shanghai_timestamp_string()
        insert_rows = [
            (
                item.snapshot_date.isoformat(),
                item.snapshot_time.isoformat(sep=' '),
                item.keyword,
                item.item_id,
                item.title,
                item.price,
                item.rank_pos,
                item.seller_name,
                item.item_url,
                item.desc_text,
                item.raw_text,
                current_ts,
            )
            for item in items
        ]

        with self.connect() as connection:
            connection.execute(
                f'DELETE FROM item_snapshot WHERE snapshot_date = ? AND keyword IN ({placeholders})',
                [snapshot_date.isoformat(), *keywords],
            )
            connection.executemany(
                '''
                INSERT INTO item_snapshot (
                    snapshot_date, snapshot_time, keyword, item_id, title, price,
                    rank_pos, seller_name, item_url, desc_text, raw_text, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                insert_rows,
            )
        return len(insert_rows)

    def fetch_snapshots_by_date(self, snapshot_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                '''
                SELECT snapshot_date, snapshot_time, keyword, item_id, title, price,
                       rank_pos, seller_name, item_url, desc_text, raw_text
                FROM item_snapshot
                WHERE snapshot_date = ?
                ORDER BY keyword ASC, rank_pos ASC
                ''',
                (snapshot_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_previous_daily_stats(self, stat_date: date) -> dict[str, dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                '''
                SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                       max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                FROM keyword_daily_stats
                WHERE stat_date = ?
                ''',
                (stat_date.isoformat(),),
            ).fetchall()
        return {row['keyword']: dict(row) for row in rows}

    def replace_daily_stats(self, stat_date: date, stats: list[DailyKeywordStat]) -> int:
        if not stats:
            return 0
        current_ts = shanghai_timestamp_string()
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
                current_ts,
                current_ts,
            )
            for row in stats
        ]
        with self.connect() as connection:
            connection.execute(
                'DELETE FROM keyword_daily_stats WHERE stat_date = ?',
                (stat_date.isoformat(),),
            )
            connection.executemany(
                '''
                INSERT INTO keyword_daily_stats (
                    stat_date, keyword, category, item_count, avg_price, min_price,
                    max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                insert_rows,
            )
        return len(insert_rows)

    def replace_item_scores(self, stat_date: date, rows: list[DailyItemScore]) -> int:
        if not rows:
            return 0
        current_ts = shanghai_timestamp_string()
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
                current_ts,
            )
            for row in rows
        ]
        with self.connect() as connection:
            connection.execute(
                'DELETE FROM item_score_daily WHERE stat_date = ?',
                (stat_date.isoformat(),),
            )
            connection.executemany(
                '''
                INSERT INTO item_score_daily (
                    stat_date, keyword, item_id, title, rank_pos, price, score, item_url,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                insert_rows,
            )
        return len(insert_rows)

    def fetch_item_scores_by_date(self, stat_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                '''
                SELECT stat_date, keyword, item_id, title, rank_pos, price, score, item_url
                FROM item_score_daily
                WHERE stat_date = ?
                ORDER BY keyword ASC, score DESC, rank_pos ASC
                ''',
                (stat_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_daily_stats_between(
        self, start_date: date, end_date: date
    ) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                '''
                SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                       max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                FROM keyword_daily_stats
                WHERE stat_date BETWEEN ? AND ?
                ORDER BY stat_date ASC, keyword ASC
                ''',
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_job_run(self, row: JobRunRecord) -> None:
        current_ts = shanghai_timestamp_string()
        with self.connect() as connection:
            connection.execute(
                '''
                INSERT INTO job_run_history (
                    run_id, job_name, run_mode, run_status, target_label, snapshot_date,
                    started_at, finished_at, duration_seconds, keyword_total, keyword_success,
                    keyword_failed, inserted_snapshots, daily_stats, item_scores, alert_level,
                    alert_message, report_paths_json, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    run_status=excluded.run_status,
                    target_label=excluded.target_label,
                    snapshot_date=excluded.snapshot_date,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    duration_seconds=excluded.duration_seconds,
                    keyword_total=excluded.keyword_total,
                    keyword_success=excluded.keyword_success,
                    keyword_failed=excluded.keyword_failed,
                    inserted_snapshots=excluded.inserted_snapshots,
                    daily_stats=excluded.daily_stats,
                    item_scores=excluded.item_scores,
                    alert_level=excluded.alert_level,
                    alert_message=excluded.alert_message,
                    report_paths_json=excluded.report_paths_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                ''',
                (
                    row.run_id,
                    row.job_name,
                    row.run_mode,
                    row.run_status,
                    row.target_label,
                    row.snapshot_date.isoformat() if row.snapshot_date else None,
                    row.started_at.isoformat(sep=' '),
                    row.finished_at.isoformat(sep=' '),
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
                    current_ts,
                    current_ts,
                ),
            )

    def replace_keyword_failures(
        self,
        run_id: str,
        job_name: str,
        failures: list[dict[str, object]],
    ) -> int:
        current_ts = shanghai_timestamp_string()
        with self.connect() as connection:
            connection.execute(
                'DELETE FROM keyword_failure_log WHERE run_id = ?',
                (run_id,),
            )
            if not failures:
                return 0
            connection.executemany(
                '''
                INSERT INTO keyword_failure_log (
                    run_id, job_name, snapshot_date, keyword, category, error_type,
                    error_message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                [
                    (
                        run_id,
                        job_name,
                        failure.get('snapshot_date'),
                        failure.get('keyword'),
                        failure.get('category'),
                        failure.get('error_type'),
                        failure.get('error_message'),
                        current_ts,
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
        current_ts = shanghai_timestamp_string()
        with self.connect() as connection:
            connection.execute(
                'DELETE FROM data_quality_issue WHERE run_id = ?',
                (run_id,),
            )
            if not issues:
                return 0
            connection.executemany(
                '''
                INSERT INTO data_quality_issue (
                    run_id, snapshot_date, keyword, item_id, issue_type, severity,
                    issue_message, sample_value, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                [
                    (
                        run_id,
                        issue.snapshot_date.isoformat() if issue.snapshot_date else None,
                        issue.keyword,
                        issue.item_id,
                        issue.issue_type,
                        issue.severity,
                        issue.issue_message,
                        issue.sample_value,
                        current_ts,
                    )
                    for issue in issues
                ],
            )
        return len(issues)
