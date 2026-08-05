"""Open API 원본을 검색·필터용 구조로 정리한다."""

from __future__ import annotations

import json
import re
from datetime import datetime

from src.ingest.collect import _atomic_json
from src.ingest.config import IngestSettings, settings

CODE_FIELDS = ("mrgSttsCd", "earnCndSeCd", "aplyPrdSeCd", "bizPrdSeCd", "pvsnInstGroupCd", "plcyPvsnMthdCd", "plcyAprvSttsCd")
LIST_CODE_FIELDS = ("sbizCd", "jobCd", "schoolCd", "plcyMajorCd")


def _split(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[,|]", str(value or "")) if item.strip()]


def _date(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")[:8]
    if len(digits) != 8:
        return None
    try:
        return datetime.strptime(digits, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _periods(value: str | None) -> list[dict[str, str]]:
    values = re.findall(r"\d{4}[.\-/]?\d{2}[.\-/]?\d{2}", value or "")
    dates = [parsed for item in values if (parsed := _date(item))]
    return [
        {"start": dates[index], "end": dates[index + 1]}
        for index in range(0, len(dates) - 1, 2)
    ]


def _category(value: object) -> str:
    seen: list[str] = []
    for item in _split(value):
        if item not in seen:
            seen.append(item)
    return ",".join(seen)


def normalize_policy(raw: dict, definitions: dict[str, dict[str, str]]) -> dict:
    policy = dict(raw)
    policy["plcyNo"] = str(policy.get("plcyNo") or "")
    policy["lclsfNm"] = _category(policy.get("lclsfNm"))
    policy["zipCdList"] = _split(policy.get("zipCdList") or policy.get("zipCd"))

    for field in CODE_FIELDS:
        code = str(policy.get(field) or "")
        policy[f"{field}Nm"] = definitions.get(field, {}).get(code, policy.get(f"{field}Nm"))

    for field in LIST_CODE_FIELDS:
        codes = _split(policy.get(f"{field}List") or policy.get(field))
        policy[f"{field}List"] = codes
        policy[f"{field}NmList"] = [
            definitions.get(field, {}).get(code, code) for code in codes
        ]

    periods = policy.get("aplyPeriods") or _periods(policy.get("aplyYmd"))
    policy["aplyPeriods"] = periods
    policy["aplyStartYmd"] = policy.get("aplyStartYmd") or (periods[0]["start"] if periods else None)
    policy["aplyEndYmd"] = policy.get("aplyEndYmd") or (periods[-1]["end"] if periods else None)
    return policy


def normalize_policies(config: IngestSettings = settings) -> list[dict]:
    raw = json.loads(config.raw_path.read_text(encoding="utf-8"))
    definitions = json.loads(config.code_definitions_path.read_text(encoding="utf-8"))
    policies = [normalize_policy(item, definitions) for item in raw if item.get("plcyNo")]
    _atomic_json(config.structured_path, policies)
    return policies


def main() -> None:
    policies = normalize_policies()
    print(f"정규화 완료: {len(policies):,}건 → {settings.structured_path}")


if __name__ == "__main__":
    main()
