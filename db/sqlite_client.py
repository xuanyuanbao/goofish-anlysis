from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from models import CrawledItem, DailyItemScore, DailyKeywordStat, KeywordRecord

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
        schema = (self.project_root / "db" / "sqlite_init.sql").read_text(
            encoding="utf-8"
        )
        with self.connect() as connection:
            connection.executescript(schema)

    def keyword_count(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(1) AS cnt FROM keyword_config"
            ).fetchone()
        return int(row["cnt"])

    def insert_keywords(self, rows: list[tuple[str, str, int, int]]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO keyword_config (keyword, category, status, priority)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

    def fetch_active_keywords(self) -> list[KeywordRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, keyword, category, status, priority
                FROM keyword_config
                WHERE status = 1
                ORDER BY priority ASC, keyword ASC
                """
            ).fetchall()
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
        placeholders = ",".join("?" for _ in keywords)
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
            connection.execute(
                f"DELETE FROM item_snapshot WHERE snapshot_date = ? AND keyword IN ({placeholders})",
                [snapshot_date.isoformat(), *keywords],
            )
            connection.executemany(
                """
                INSERT INTO item_snapshot (
                    snapshot_date, snapshot_time, keyword, item_id, title, price,
                    rank_pos, seller_name, item_url, desc_text, raw_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_rows,
            )
        return len(insert_rows)

    def fetch_snapshots_by_date(self, snapshot_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT snapshot_date, snapshot_time, keyword, item_id, title, price,
                       rank_pos, seller_name, item_url, desc_text, raw_text
                FROM item_snapshot
                WHERE snapshot_date = ?
                ORDER BY keyword ASC, rank_pos ASC
                """,
                (snapshot_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_previous_daily_stats(self, stat_date: date) -> dict[str, dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                       max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                FROM keyword_daily_stats
                WHERE stat_date = ?
                """,
                (stat_date.isoformat(),),
            ).fetchall()
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
            connection.execute(
                "DELETE FROM keyword_daily_stats WHERE stat_date = ?",
                (stat_date.isoformat(),),
            )
            connection.executemany(
                """
                INSERT INTO keyword_daily_stats (
                    stat_date, keyword, category, item_count, avg_price, min_price,
                    max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            connection.execute(
                "DELETE FROM item_score_daily WHERE stat_date = ?",
                (stat_date.isoformat(),),
            )
            connection.executemany(
                """
                INSERT INTO item_score_daily (
                    stat_date, keyword, item_id, title, rank_pos, price, score, item_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_rows,
            )
        return len(insert_rows)

    def fetch_item_scores_by_date(self, stat_date: date) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stat_date, keyword, item_id, title, rank_pos, price, score, item_url
                FROM item_score_daily
                WHERE stat_date = ?
                ORDER BY keyword ASC, score DESC, rank_pos ASC
                """,
                (stat_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_daily_stats_between(
        self, start_date: date, end_date: date
    ) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stat_date, keyword, category, item_count, avg_price, min_price,
                       max_price, top10_avg_rank, hot_score, trend_up_down, opportunity_score
                FROM keyword_daily_stats
                WHERE stat_date BETWEEN ? AND ?
                ORDER BY stat_date ASC, keyword ASC
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]
