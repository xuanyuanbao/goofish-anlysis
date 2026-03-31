from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from models import (
    CrawledItem,
    DailyItemScore,
    DailyKeywordStat,
    DataQualityIssue,
    JobRunRecord,
    KeywordRecord,
)


class BaseDatabase(ABC):
    @abstractmethod
    def initialize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def keyword_count(self) -> int:
        raise NotImplementedError

    def seed_keywords_from_csv(self, csv_path: Path) -> int:
        if not csv_path.exists() or self.keyword_count() > 0:
            return 0

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [
                (
                    line["keyword"].strip(),
                    line["category"].strip(),
                    int(line.get("status", "1") or "1"),
                    int(line.get("priority", "100") or "100"),
                )
                for line in reader
                if line.get("keyword") and line.get("category")
            ]

        if not rows:
            return 0

        self.insert_keywords(rows)
        return len(rows)

    @abstractmethod
    def insert_keywords(self, rows: list[tuple[str, str, int, int]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_active_keywords(self) -> list[KeywordRecord]:
        raise NotImplementedError

    @abstractmethod
    def replace_snapshots(self, snapshot_date: date, items: list[CrawledItem]) -> int:
        raise NotImplementedError

    @abstractmethod
    def fetch_snapshots_by_date(self, snapshot_date: date) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_previous_daily_stats(self, stat_date: date) -> dict[str, dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def replace_daily_stats(self, stat_date: date, stats: list[DailyKeywordStat]) -> int:
        raise NotImplementedError

    @abstractmethod
    def replace_item_scores(self, stat_date: date, rows: list[DailyItemScore]) -> int:
        raise NotImplementedError

    @abstractmethod
    def fetch_item_scores_by_date(self, stat_date: date) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_daily_stats_between(
        self, start_date: date, end_date: date
    ) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def record_job_run(self, row: JobRunRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def replace_keyword_failures(
        self,
        run_id: str,
        job_name: str,
        failures: list[dict[str, object]],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def replace_data_quality_issues(
        self,
        run_id: str,
        issues: list[DataQualityIssue],
    ) -> int:
        raise NotImplementedError
