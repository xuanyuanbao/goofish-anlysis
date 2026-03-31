from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime


@dataclass(slots=True)
class KeywordRecord:
    id: int | None
    keyword: str
    category: str
    status: int = 1
    priority: int = 100

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CrawledItem:
    snapshot_date: date
    snapshot_time: datetime
    keyword: str
    item_id: str | None
    title: str
    price: float | None
    rank_pos: int | None
    seller_name: str | None
    item_url: str | None
    desc_text: str | None
    raw_text: str | None
    category: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["snapshot_date"] = self.snapshot_date.isoformat()
        data["snapshot_time"] = self.snapshot_time.isoformat(sep=" ")
        return data


@dataclass(slots=True)
class DailyKeywordStat:
    stat_date: date
    keyword: str
    category: str
    item_count: int
    avg_price: float | None
    min_price: float | None
    max_price: float | None
    top10_avg_rank: float | None
    hot_score: float
    trend_up_down: float
    opportunity_score: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["stat_date"] = self.stat_date.isoformat()
        return data


@dataclass(slots=True)
class DailyItemScore:
    stat_date: date
    keyword: str
    item_id: str | None
    title: str
    rank_pos: int | None
    price: float | None
    score: float
    item_url: str | None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["stat_date"] = self.stat_date.isoformat()
        return data


@dataclass(slots=True)
class WeeklyTrendRow:
    week_start: date
    week_end: date
    keyword: str
    category: str
    current_avg_hot: float | None
    previous_avg_hot: float | None
    wow_rate: float
    current_avg_price: float | None
    previous_avg_price: float | None
    attention_level: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["week_start"] = self.week_start.isoformat()
        data["week_end"] = self.week_end.isoformat()
        return data


@dataclass(slots=True)
class MonthlyTrendRow:
    month_label: str
    keyword: str
    category: str
    current_avg_hot: float
    previous_avg_hot: float
    mom_rate: float
    current_avg_price: float | None
    previous_avg_price: float | None
    rising_flag: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class DataQualityIssue:
    snapshot_date: date | None
    keyword: str
    item_id: str | None
    issue_type: str
    severity: str
    issue_message: str
    sample_value: str | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["snapshot_date"] = (
            self.snapshot_date.isoformat() if self.snapshot_date is not None else None
        )
        return data


@dataclass(slots=True)
class JobRunRecord:
    run_id: str
    job_name: str
    run_mode: str
    run_status: str
    target_label: str | None
    snapshot_date: date | None
    started_at: datetime
    finished_at: datetime
    keyword_total: int = 0
    keyword_success: int = 0
    keyword_failed: int = 0
    inserted_snapshots: int = 0
    daily_stats: int = 0
    item_scores: int = 0
    alert_level: str = "info"
    alert_message: str | None = None
    report_paths: list[str] | None = None
    metadata_json: str | None = None

    @property
    def duration_seconds(self) -> float:
        return round((self.finished_at - self.started_at).total_seconds(), 2)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "job_name": self.job_name,
            "run_mode": self.run_mode,
            "run_status": self.run_status,
            "target_label": self.target_label,
            "snapshot_date": (
                self.snapshot_date.isoformat() if self.snapshot_date is not None else None
            ),
            "started_at": self.started_at.isoformat(sep=" "),
            "finished_at": self.finished_at.isoformat(sep=" "),
            "duration_seconds": self.duration_seconds,
            "keyword_total": self.keyword_total,
            "keyword_success": self.keyword_success,
            "keyword_failed": self.keyword_failed,
            "inserted_snapshots": self.inserted_snapshots,
            "daily_stats": self.daily_stats,
            "item_scores": self.item_scores,
            "alert_level": self.alert_level,
            "alert_message": self.alert_message,
            "report_paths": self.report_paths or [],
            "metadata_json": self.metadata_json,
        }
