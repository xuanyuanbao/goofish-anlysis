from __future__ import annotations

import html
import json
import re
from datetime import date, datetime

from models import CrawledItem, KeywordRecord


DETAIL_FIELD_HINTS = {
    "desc",
    "description",
    "detail",
    "detailtext",
    "content",
    "summary",
    "itemdesc",
    "sellpoint",
    "memo",
    "remark",
}


def parse_search_items(
    payload: object,
    keyword: KeywordRecord,
    snapshot_date: date,
    snapshot_time: datetime,
) -> list[CrawledItem]:
    nodes = _extract_item_nodes(payload)
    items: list[CrawledItem] = []
    seen_keys: set[str] = set()

    for rank_pos, node in enumerate(nodes, start=1):
        item = _normalize_item_node(
            node=node,
            keyword=keyword,
            snapshot_date=snapshot_date,
            snapshot_time=snapshot_time,
            rank_pos=rank_pos,
        )
        if item is None:
            continue
        dedupe_key = item.item_id or f"{item.title}|{item.price}|{item.seller_name}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        items.append(item)
    return items


def merge_descriptions(search_desc: str | None, detail_desc: str | None) -> str | None:
    search_text = _clean_text(search_desc)
    detail_text = _clean_text(detail_desc)
    if detail_text and len(detail_text) >= len(search_text or ""):
        return detail_text
    return search_text


def extract_detail_description(html_text: str) -> str | None:
    if not html_text:
        return None

    candidates: list[str] = []

    for pattern in (
        r'<meta\s+name="description"\s+content="([^"]+)"',
        r'<meta\s+property="og:description"\s+content="([^"]+)"',
    ):
        for match in re.finditer(pattern, html_text, flags=re.IGNORECASE):
            candidates.append(match.group(1))

    for marker in (
        "window.__INITIAL_STATE__=",
        "window.__INITIAL_STATE__ =",
        "window.__NUXT__=",
        "window.__NUXT__ =",
        "__NEXT_DATA__",
    ):
        candidates.extend(_extract_candidates_from_json_marker(html_text, marker))

    for match in re.finditer(
        r'"(?:desc|description|itemDesc|summary|detailText|content)"\s*:\s*"([^"]{12,1200})"',
        html_text,
        flags=re.IGNORECASE,
    ):
        candidates.append(match.group(1))

    normalized = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = _clean_text(candidate)
        if not cleaned or len(cleaned) < 12:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    if not normalized:
        return None
    normalized.sort(key=len, reverse=True)
    return normalized[0]


def _extract_candidates_from_json_marker(html_text: str, marker: str) -> list[str]:
    start = html_text.find(marker)
    if start < 0:
        return []
    brace_start = html_text.find("{", start)
    if brace_start < 0:
        return []
    json_text = _extract_balanced_json_object(html_text, brace_start)
    if not json_text:
        return []

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    candidates: list[str] = []
    _collect_detail_candidates(payload, candidates, depth=0)
    return candidates


def _extract_balanced_json_object(source: str, start_index: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start_index, len(source)):
        char = source[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start_index : index + 1]
    return None


def _collect_detail_candidates(node: object, candidates: list[str], depth: int) -> None:
    if depth > 10:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = re.sub(r"[^a-z]", "", str(key).lower())
            if lowered in DETAIL_FIELD_HINTS and isinstance(value, str):
                candidates.append(value)
            _collect_detail_candidates(value, candidates, depth + 1)
        return
    if isinstance(node, list):
        for item in node:
            _collect_detail_candidates(item, candidates, depth + 1)


def _extract_item_nodes(payload: object) -> list[dict[str, object]]:
    if payload is None:
        return []

    nodes: list[dict[str, object]] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if _looks_like_item_node(node):
            nodes.append(node)
            return
        for value in node.values():
            walk(value)

    walk(payload)
    return nodes


def _looks_like_item_node(node: dict[str, object]) -> bool:
    data = node.get("data") if isinstance(node.get("data"), dict) else node
    if not isinstance(data, dict):
        return False
    if data.get("title") and any(key in data for key in ("id", "price", "picUrl")):
        return True
    main = _as_dict(_deep_get(data, "item", "main"))
    ex_content = _as_dict(main.get("exContent"))
    click_param = _as_dict(main.get("clickParam"))
    return bool(main and (ex_content.get("title") or click_param.get("targetUrl")))


def _normalize_item_node(
    *,
    node: dict[str, object],
    keyword: KeywordRecord,
    snapshot_date: date,
    snapshot_time: datetime,
    rank_pos: int,
) -> CrawledItem | None:
    data = node.get("data") if isinstance(node.get("data"), dict) else node
    if not isinstance(data, dict):
        return None

    main = _as_dict(_deep_get(data, "item", "main"))
    ex_content = _as_dict(main.get("exContent"))
    click_param = _as_dict(main.get("clickParam"))
    user_info = _as_dict(data.get("userInfo"))

    target_url = _first_non_empty(
        _stringify(click_param.get("targetUrl")),
        _stringify(data.get("itemUrl")),
        _stringify(data.get("targetUrl")),
        _stringify(_deep_get(data, "shareInfo", "targetUrl")),
    )
    item_id = _first_non_empty(
        _stringify(data.get("id")),
        _stringify(click_param.get("itemId")),
        _extract_item_id(target_url),
    )
    title = _first_non_empty(
        _stringify(data.get("title")),
        _stringify(ex_content.get("title")),
        _stringify(ex_content.get("mainTitle")),
        _stringify(_deep_get(ex_content, "content", "title")),
    )
    if not title:
        return None

    price = _first_float(
        data.get("price"),
        ex_content.get("price"),
        _deep_get(data, "priceInfo", "price"),
        _deep_get(ex_content, "priceInfo", "price"),
        data.get("priceText"),
        ex_content.get("priceText"),
    )
    seller_name = _first_non_empty(
        _stringify(user_info.get("nickName")),
        _stringify(user_info.get("userNick")),
        _stringify(data.get("sellerNick")),
        _stringify(data.get("city")),
    )
    item_url = _normalize_item_url(target_url, item_id)
    desc_text = _first_non_empty(
        _stringify(data.get("desc")),
        _stringify(data.get("summary")),
        _stringify(ex_content.get("desc")),
        _stringify(ex_content.get("subTitle")),
    )

    return CrawledItem(
        snapshot_date=snapshot_date,
        snapshot_time=snapshot_time,
        keyword=keyword.keyword,
        item_id=item_id,
        title=_clean_text(title) or title,
        price=price,
        rank_pos=rank_pos,
        seller_name=_clean_text(seller_name),
        item_url=item_url,
        desc_text=_clean_text(desc_text),
        raw_text=json.dumps(node, ensure_ascii=False, separators=(",", ":")),
        category=keyword.category,
    )


def _normalize_item_url(target_url: str | None, item_id: str | None) -> str | None:
    if target_url:
        if target_url.startswith("//"):
            return f"https:{target_url}"
        if target_url.startswith(("http://", "https://")):
            return target_url
        if target_url.startswith("/"):
            return f"https://www.goofish.com{target_url}"
    if item_id:
        return f"https://www.goofish.com/item?id={item_id}"
    return None


def _extract_item_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:id|itemId)=([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"/item/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None


def _deep_get(obj: object, *path: str) -> object | None:
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        text = _stringify(value)
        if text:
            return text
    return None


def _first_float(*values: object) -> float | None:
    for value in values:
        number = _coerce_float(value)
        if number is not None:
            return number
    return None


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, dict):
        for key in ("price", "amount", "value", "priceValue"):
            if key in value:
                number = _coerce_float(value.get(key))
                if number is not None:
                    return number
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None
    return round(float(match.group(1)), 2)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" |;,-")
    return text or None
