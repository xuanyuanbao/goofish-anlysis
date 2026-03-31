from __future__ import annotations

import re
from dataclasses import dataclass

from models import CrawledItem, DataQualityIssue


ITEM_URL_PATTERN = re.compile(
    r"^https://www\.goofish\.com/(?:item\?id=[A-Za-z0-9_-]+|search\?q=.+)$"
)


@dataclass(slots=True)
class DataQualitySummary:
    total_items: int
    missing_item_id: int
    missing_item_url: int
    invalid_item_url: int
    url_item_mismatch: int
    missing_price: int
    missing_seller_name: int
    short_desc: int
    duplicate_removed: int

    def to_dict(self) -> dict[str, int]:
        return {
            "total_items": self.total_items,
            "missing_item_id": self.missing_item_id,
            "missing_item_url": self.missing_item_url,
            "invalid_item_url": self.invalid_item_url,
            "url_item_mismatch": self.url_item_mismatch,
            "missing_price": self.missing_price,
            "missing_seller_name": self.missing_seller_name,
            "short_desc": self.short_desc,
            "duplicate_removed": self.duplicate_removed,
        }


@dataclass(slots=True)
class DataQualityAssessment:
    issues: list[DataQualityIssue]
    summary: DataQualitySummary


def assess_items(
    items: list[CrawledItem],
    *,
    duplicate_removed: int = 0,
) -> DataQualityAssessment:
    issues: list[DataQualityIssue] = []
    counters = {
        "missing_item_id": 0,
        "missing_item_url": 0,
        "invalid_item_url": 0,
        "url_item_mismatch": 0,
        "missing_price": 0,
        "missing_seller_name": 0,
        "short_desc": 0,
    }

    for item in items:
        if not item.item_id:
            counters["missing_item_id"] += 1
            issues.append(
                _issue(
                    item,
                    "missing_item_id",
                    "warning",
                    "item_id is missing; fallback dedupe keys will be less stable.",
                )
            )

        if not item.item_url:
            counters["missing_item_url"] += 1
            issues.append(
                _issue(
                    item,
                    "missing_item_url",
                    "error",
                    "item_url is missing; exported reports will not be directly clickable.",
                )
            )
        elif not ITEM_URL_PATTERN.match(item.item_url):
            counters["invalid_item_url"] += 1
            issues.append(
                _issue(
                    item,
                    "invalid_item_url",
                    "error",
                    "item_url is not a canonical Goofish item/search URL.",
                    sample_value=item.item_url,
                )
            )
        elif (
            item.item_id
            and "search?q=" not in item.item_url
            and item.item_id not in item.item_url
        ):
            counters["url_item_mismatch"] += 1
            issues.append(
                _issue(
                    item,
                    "url_item_mismatch",
                    "warning",
                    "item_url does not contain the resolved item_id.",
                    sample_value=item.item_url,
                )
            )

        if item.price is None:
            counters["missing_price"] += 1
            issues.append(
                _issue(
                    item,
                    "missing_price",
                    "warning",
                    "price is missing after normalization.",
                )
            )

        if not item.seller_name:
            counters["missing_seller_name"] += 1
            issues.append(
                _issue(
                    item,
                    "missing_seller_name",
                    "info",
                    "seller_name is empty.",
                )
            )

        if not item.desc_text or len(item.desc_text.strip()) < 12:
            counters["short_desc"] += 1
            issues.append(
                _issue(
                    item,
                    "short_desc",
                    "info",
                    "desc_text is missing or too short for downstream analysis.",
                )
            )

    summary = DataQualitySummary(
        total_items=len(items),
        missing_item_id=counters["missing_item_id"],
        missing_item_url=counters["missing_item_url"],
        invalid_item_url=counters["invalid_item_url"],
        url_item_mismatch=counters["url_item_mismatch"],
        missing_price=counters["missing_price"],
        missing_seller_name=counters["missing_seller_name"],
        short_desc=counters["short_desc"],
        duplicate_removed=max(duplicate_removed, 0),
    )
    return DataQualityAssessment(issues=issues, summary=summary)


def _issue(
    item: CrawledItem,
    issue_type: str,
    severity: str,
    issue_message: str,
    *,
    sample_value: str | None = None,
) -> DataQualityIssue:
    return DataQualityIssue(
        snapshot_date=item.snapshot_date,
        keyword=item.keyword,
        item_id=item.item_id,
        issue_type=issue_type,
        severity=severity,
        issue_message=issue_message,
        sample_value=sample_value,
    )
