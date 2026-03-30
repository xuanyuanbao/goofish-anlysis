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
