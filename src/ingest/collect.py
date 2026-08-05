"""온통청년 Open API 전체 페이지 수집."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.ingest.config import IngestSettings, settings


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _element_dict(element: ET.Element) -> dict:
    result: dict[str, object] = {}
    for child in element:
        key = _local_name(child.tag)
        value: object = _element_dict(child) if list(child) else (child.text or "").strip()
        if key in result:
            current = result[key]
            result[key] = current + [value] if isinstance(current, list) else [current, value]
        else:
            result[key] = value
    return result


def _xml_items(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    candidates = {"youthPolicy", "policy", "item", "row"}
    nodes = [node for node in root.iter() if _local_name(node.tag) in candidates and list(node)]
    # item 안에 youthPolicy가 중첩된 응답이면 가장 구체적인 정책 노드만 쓴다.
    specific = [node for node in nodes if _local_name(node.tag) in {"youthPolicy", "policy"}]
    nodes = specific or nodes
    return [item for node in nodes if (item := _element_dict(node)).get("plcyNo")]


def _json_items(value: object) -> list[dict]:
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            with_ids = [item for item in value if item.get("plcyNo")]
            return with_ids or value
        return []
    if isinstance(value, dict):
        for key in ("youthPolicy", "policies", "items", "item", "result", "data", "response"):
            if key in value:
                found = _json_items(value[key])
                if found:
                    return found
        for child in value.values():
            found = _json_items(child)
            if found:
                return found
    return []


def parse_response(payload: bytes, content_type: str = "") -> list[dict]:
    stripped = payload.lstrip()
    if "json" in content_type or stripped.startswith((b"[", b"{")):
        return _json_items(json.loads(payload.decode("utf-8-sig")))
    return _xml_items(payload)


def fetch_page(page: int, config: IngestSettings = settings) -> list[dict]:
    if not config.api_key:
        raise RuntimeError("ONTONG_API_KEY가 없습니다. .env 또는 환경변수에 인증키를 넣어주세요.")
    query = urlencode(
        {"openApiVlak": config.api_key, "pageIndex": page, "display": config.page_size}
    )
    request = Request(
        f"{config.api_url}?{query}",
        headers={"Accept": "application/json, application/xml;q=0.9", "User-Agent": "youth-policy-helper/1.0"},
    )
    with urlopen(request, timeout=config.timeout_seconds) as response:  # noqa: S310 - 고정 HTTPS API
        return parse_response(response.read(), response.headers.get("Content-Type", ""))


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def collect_policies(config: IngestSettings = settings, *, max_pages: int | None = None) -> list[dict]:
    collected: dict[str, dict] = {}
    page = 1
    while max_pages is None or page <= max_pages:
        items = fetch_page(page, config)
        if not items:
            break
        for item in items:
            policy_id = str(item.get("plcyNo") or "")
            if policy_id:
                collected[policy_id] = item
        print(f"collect: {page}페이지 · 누적 {len(collected):,}건")
        if len(items) < config.page_size:
            break
        page += 1
    policies = list(collected.values())
    _atomic_json(config.raw_path, policies)
    return policies


def main() -> None:
    policies = collect_policies()
    print(f"수집 완료: {len(policies):,}건 → {settings.raw_path}")


if __name__ == "__main__":
    main()
