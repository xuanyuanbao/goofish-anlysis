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
    "itemdescription",
    "goodsdesc",
    "sellpoint",
    "memo",
    "remark",
    "introduce",
}

DETAIL_LABELS = (
    "商品描述",
    "宝贝描述",
    "商品详情",
    "资料说明",
    "内容说明",
    "详情描述",
)

JSON_STATE_MARKERS = (
    "window.__INITIAL_STATE__=",
    "window.__INITIAL_STATE__ =",
    "window.__NUXT__=",
    "window.__NUXT__ =",
    "window.__PRELOADED_STATE__=",
    "window.__PRELOADED_STATE__ =",
    "window.__APP_STATE__=",
    "window.__APP_STATE__ =",
    "__NEXT_DATA__",
)

WEAK_DESC_MARKERS = (
    "点击查看",
    "详聊",
    "见图",
    "如图",
    "默认发货",
    "自动发货",
)


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
    if detail_text and search_text and detail_text != search_text:
        if search_text not in detail_text and len(detail_text) < 1500:
            return _limit_text(f"{detail_text}\n\n搜索摘要：{search_text}", 2000)
    if detail_text and len(detail_text) >= len(search_text or ""):
        return detail_text
    return search_text


def is_weak_description(text: str | None, title: str | None = None) -> bool:
    cleaned = _clean_text(text)
    cleaned_title = _clean_text(title)
    if not cleaned or len(cleaned) < 18:
        return True
    if cleaned_title and cleaned == cleaned_title:
        return True
    if any(marker in cleaned for marker in WEAK_DESC_MARKERS):
        return True
    return False


def extract_detail_description(html_text: str) -> str | None:
    if not html_text:
        return None

    candidates: list[str] = []
    candidates.extend(_extract_meta_candidates(html_text))
    candidates.extend(_extract_title_candidates(html_text))
    candidates.extend(_extract_json_script_candidates(html_text))
    candidates.extend(_extract_json_parse_candidates(html_text))
    candidates.extend(_extract_inline_json_key_candidates(html_text))

    for marker in JSON_STATE_MARKERS:
        candidates.extend(_extract_candidates_from_json_marker(html_text, marker))

    candidates.extend(_extract_label_based_candidates(html_text))

    normalized = _normalize_detail_candidates(candidates)
    if not normalized:
        return None
    normalized.sort(key=_candidate_score, reverse=True)
    return normalized[0]


def _extract_meta_candidates(html_text: str) -> list[str]:
    candidates: list[str] = []
    for pattern in (
        r'<meta\s+name="description"\s+content="([^"]+)"',
        r'<meta\s+property="og:description"\s+content="([^"]+)"',
    ):
        for match in re.finditer(pattern, html_text, flags=re.IGNORECASE):
            candidates.append(match.group(1))
    return candidates


def _extract_title_candidates(html_text: str) -> list[str]:
    candidates: list[str] = []
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text)
    if match:
        candidates.append(match.group(1))
    return candidates


def _extract_json_script_candidates(html_text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(
        r"<script[^>]*type=[\"']application/(?:ld\+)?json[\"'][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        script_text = match.group(1).strip()
        if not script_text:
            continue
        try:
            payload = json.loads(script_text)
        except json.JSONDecodeError:
            candidates.extend(_extract_inline_json_key_candidates(script_text))
            continue
        _collect_detail_candidates(payload, candidates, depth=0)
    return candidates


def _extract_inline_json_key_candidates(html_text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(
        r'"(?:desc|description|itemDesc|itemDescription|summary|detailText|content|memo|sellPoint|goodsDesc)"\s*:\s*"([^"]{12,4000})"',
        html_text,
        flags=re.IGNORECASE,
    ):
        candidates.append(match.group(1))
    return candidates


def _extract_json_parse_candidates(html_text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(
        r"JSON\.parse\(\s*'((?:\\'|\\\\|[^']){20,20000})'\s*\)",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        encoded = match.group(1).replace("\\'", "'")
        decoded = _decode_possible_escapes(encoded)
        candidates.extend(_extract_inline_json_key_candidates(decoded))
    return candidates


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


def _extract_label_based_candidates(html_text: str) -> list[str]:
    plain_text = _html_to_text(html_text)
    lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
    candidates: list[str] = []

    for index, line in enumerate(lines):
        for label in DETAIL_LABELS:
            if label not in line:
                continue
            suffix = line.split(label, 1)[-1].strip(" ：:-")
            if len(suffix) >= 12:
                candidates.append(suffix)
                continue
            if index + 1 < len(lines) and len(lines[index + 1]) >= 12:
                candidates.append(lines[index + 1])

    return candidates


def _normalize_detail_candidates(candidates: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        cleaned = _decode_possible_escapes(candidate)
        cleaned = _clean_text(cleaned)
        if not cleaned or len(cleaned) < 12:
            continue
        if _looks_like_noise(cleaned):
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized


def _candidate_score(text: str) -> int:
    score = min(len(text), 260)
    if 18 <= len(text) <= 240:
        score += 200
    if re.search(r"[\u4e00-\u9fff]", text):
        score += 40
    if any(marker in text for marker in ("http", "function(", "window.", "undefined")):
        score -= 220
    if any(marker in text for marker in ("{", "}", "[", "]")):
        score -= 120
    return score


def _looks_like_noise(text: str) -> bool:
    if len(re.findall(r"[{}[\]]", text)) >= 4:
        return True
    if "function(" in text or "window." in text:
        return True
    return False


def _html_to_text(html_text: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", "\n", html_text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", "\n", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(?:p|div|li|section|article|h[1-6])>", "\n", text)
    return html.unescape(re.sub(r"(?is)<[^>]+>", " ", text))


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
        _stringify(main.get("targetUrl")),
        _stringify(click_param.get("targetUrl")),
        _stringify(data.get("itemUrl")),
        _stringify(data.get("targetUrl")),
        _stringify(_deep_get(data, "shareInfo", "targetUrl")),
    )
    item_id = _first_non_empty(
        _stringify(data.get("id")),
        _stringify(click_param.get("itemId")),
        _stringify(_deep_get(click_param, "args", "item_id")),
        _stringify(_deep_get(click_param, "args", "id")),
        _stringify(ex_content.get("itemId")),
        _stringify(_deep_get(ex_content, "detailParams", "itemId")),
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
        item_id=_limit_text(item_id, 100),
        title=_limit_text(_clean_text(title) or title, 500) or title[:500],
        price=price,
        rank_pos=rank_pos,
        seller_name=_limit_text(_clean_text(seller_name), 100),
        item_url=_limit_text(item_url, 1000),
        desc_text=_clean_text(desc_text),
        raw_text=json.dumps(node, ensure_ascii=False, separators=(",", ":")),
        category=keyword.category,
    )


def _normalize_item_url(target_url: str | None, item_id: str | None) -> str | None:
    if target_url:
        if target_url.startswith("fleamarket://"):
            extracted = _extract_item_id(target_url) or item_id
            if extracted:
                return f"https://www.goofish.com/item?id={extracted}"
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


def _decode_possible_escapes(value: str) -> str:
    text = str(value).strip()
    if "\\" not in text:
        return text
    try:
        return bytes(text, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return text


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" |;,-")
    return text or None


def _limit_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_length:
        return text
    return text[:max_length]
