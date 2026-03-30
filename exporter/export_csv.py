from __future__ import annotations

import csv
from pathlib import Path


def export_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        headers = ["message"]
        records = [{"message": "no data"}]
    else:
        headers = list(rows[0].keys())
        records = rows
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
