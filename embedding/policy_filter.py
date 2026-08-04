"""구조화된 정책 데이터의 정확 조건 필터."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

from .condition_extractor import REGION_ALIASES, REGION_PREFIXES


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [part.strip() for part in str(value).split(",") if part.strip()]


class PolicyFilter:
    def __init__(self, today: date | None = None):
        self.today = today or date.today()

    def matches(
        self,
        policy: Mapping[str, Any],
        conditions: Mapping[str, Any],
        include_closed: bool = False,
    ) -> bool:
        return all(
            (
                self._matches_age(policy, conditions.get("age")),
                self._matches_region(policy, conditions.get("region")),
                self._matches_named_list(
                    policy,
                    "jobCdNmList",
                    conditions.get("employment") or conditions.get("job_status"),
                ),
                self._matches_named_list(
                    policy,
                    "schoolCdNmList",
                    conditions.get("education") or conditions.get("school_status"),
                ),
                self._matches_income(policy, conditions.get("income_bracket")),
                self._matches_single_value(policy, "mrgSttsCdNm", conditions.get("marriage")),
                self._matches_category(policy, conditions.get("category")),
                include_closed or self.is_open(policy),
            )
        )

    @staticmethod
    def _matches_age(policy: Mapping[str, Any], age: Any) -> bool:
        if age is None or policy.get("sprtTrgtAgeLmtYn") != "Y":
            return True
        age = _as_int(age)
        if age is None:
            return True
        min_age = _as_int(policy.get("sprtTrgtMinAge"))
        max_age = _as_int(policy.get("sprtTrgtMaxAge"))
        return (min_age is None or age >= min_age) and (max_age is None or age <= max_age)

    @staticmethod
    def _matches_region(policy: Mapping[str, Any], region: Any) -> bool:
        if not region:
            return True
        prefixes = REGION_PREFIXES.get(str(region))
        if not prefixes:
            return True
        zip_codes = _as_list(policy.get("zipCdList") or policy.get("zipCd"))
        # 지역 데이터가 없는 정책은 지역 제한 여부를 판단할 수 없으므로 제외한다.
        if not zip_codes or not any(code.startswith(prefixes) for code in zip_codes):
            return False

        # 일부 지자체 정책에 전국 zip 코드가 잘못 들어간 경우가 있다. 코드가 전국에
        # 걸쳐 있으면 등록·운영기관명에 명시된 지역을 우선해 잘못된 추천을 막는다.
        covered_prefixes = {
            prefix
            for code in zip_codes
            for region_prefixes in REGION_PREFIXES.values()
            for prefix in region_prefixes
            if code.startswith(prefix)
        }
        if len(covered_prefixes) >= 5:
            provider_text = " ".join(
                str(policy.get(field) or "")
                for field in (
                    "operInstCdNm",
                    "rgtrInstCdNm",
                    "rgtrUpInstCdNm",
                    "rgtrHghrkInstCdNm",
                    "sprvsnInstCdNm",
                )
            )
            provider_regions = {
                canonical
                for canonical, aliases in REGION_ALIASES.items()
                if any(alias in provider_text for alias in aliases)
            }
            if provider_regions:
                return str(region) in provider_regions
        return True

    @staticmethod
    def _matches_named_list(policy: Mapping[str, Any], field: str, expected: Any) -> bool:
        if not expected:
            return True
        values = _as_list(policy.get(field))
        return "제한없음" in values or str(expected) in values

    @staticmethod
    def _matches_single_value(policy: Mapping[str, Any], field: str, expected: Any) -> bool:
        if not expected:
            return True
        actual = policy.get(field)
        return actual in (None, "", "제한없음", "무관", expected)

    @staticmethod
    def _matches_category(policy: Mapping[str, Any], expected: Any) -> bool:
        if not expected:
            return True
        category_text = " ".join(
            str(policy.get(field) or "") for field in ("lclsfNm", "mclsfNm", "plcyKywdNm")
        )
        expected_text = str(expected)
        aliases = {
            "교육": ("교육", "직업훈련"),
            "일자리": ("일자리", "취업", "창업"),
            "금융･복지･문화": ("금융", "복지", "문화"),
            "참여･기반": ("참여", "권리", "기반"),
        }.get(expected_text, (expected_text,))
        return any(alias in category_text for alias in aliases)

    @staticmethod
    def _matches_income(policy: Mapping[str, Any], income_bracket: Any) -> bool:
        """중위소득 퍼센트가 양쪽에 있을 때만 보수적으로 비교한다.

        정책의 연소득 금액(만원)과 사용자의 중위소득 퍼센트는 단위가 다르다.
        따라서 ``earnEtcCn``에 중위소득 비율이 명시된 정책만 비교하고, 정보가
        없거나 '무관'이면 이 단계에서는 탈락시키지 않는다.
        """
        bracket = _as_int(income_bracket)
        if bracket is None or policy.get("earnCndSeCdNm") in (None, "", "무관"):
            return True
        details = str(policy.get("earnEtcCn") or "")
        thresholds = [
            int(value)
            for value in re.findall(
                r"(?:기준\s*)?중위소득\s*(\d{1,3})\s*%", details
            )
        ]
        # 여러 유형의 기준이 함께 있으면 어느 한 유형에 해당할 가능성을 남긴다.
        return not thresholds or bracket <= max(thresholds)

    def is_open(self, policy: Mapping[str, Any]) -> bool:
        period_type = policy.get("aplyPrdSeCdNm")
        if period_type == "마감":
            return False
        if period_type == "상시":
            return True

        start = self._parse_date(policy.get("aplyStartYmd"))
        end = self._parse_date(policy.get("aplyEndYmd"))
        if start and self.today < start:
            return False
        if end and self.today > end:
            return False
        return True

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
