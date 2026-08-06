"""구조화된 정책 데이터에 정확 조건 필터를 적용한다."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping

from src.shared.constants import YOUTH_MAX_AGE, YOUTH_MIN_AGE

from .condition_extractor import REGION_ALIASES, REGION_PREFIXES

# 이 서비스가 다루는 "청년" 나이 범위. 정책 자체에 나이 제한이 없어도,
# 사용자가 입력한 나이가 이 범위 밖이면(예: 13세) 청년정책 서비스 대상이
# 아니므로 매칭에서 제외한다.
#
# 값은 src/shared/constants.py 에 한 번만 둔다. 백엔드 UserProfile 도 같은
# 값으로 입력을 거르므로 두 곳이 어긋나면 "입력은 받는데 결과는 0건"이 된다.


# 카테고리 탭이 보내는 값 → 데이터의 lclsfNm 값.
#
# 온통청년 데이터에 표기가 두 벌 섞여 있다. 수집 시기에 따라 분류 체계가
# 바뀐 것으로 보인다. 둘 다 잡지 않으면 절반이 사라진다.
#
#   일자리 1,070 · 복지문화 369 · 금융･복지･문화 283 · 주거 280
#   교육 214 · 참여권리 208 · 참여･기반 170 · 교육･직업훈련 153
CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "일자리": ("일자리",),
    "주거": ("주거",),
    "교육": ("교육", "교육･직업훈련"),
    "복지": ("복지문화", "금융･복지･문화"),
    "참여": ("참여권리", "참여･기반"),
}


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
        if age is None:
            return True
        age = _as_int(age)
        if age is None:
            return True

        # 온통청년 데이터에서는 N이 연령 제한 있음, Y가 제한 없음을 뜻한다.
        # N이어도 최소·최대 나이가 0 또는 결측이면 실질적으로 "그쪽 경계는
        # 명시 안 됨"이다. 이 서비스는 청년정책 챗봇이므로, 명시 안 된 경계는
        # 0이나 무한대가 아니라 이 서비스가 다루는 청년 범위
        # (YOUTH_MIN_AGE~YOUTH_MAX_AGE)로 채운다.
        if policy.get("sprtTrgtAgeLmtYn") != "N":
            return YOUTH_MIN_AGE <= age <= YOUTH_MAX_AGE

        min_age = _as_int(policy.get("sprtTrgtMinAge"))
        max_age = _as_int(policy.get("sprtTrgtMaxAge"))
        has_minimum = min_age is not None and min_age > 0
        has_maximum = max_age is not None and max_age > 0
        effective_min = min_age if has_minimum else YOUTH_MIN_AGE
        effective_max = max_age if has_maximum else YOUTH_MAX_AGE
        return effective_min <= age <= effective_max

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
        """대분류(lclsfNm)로만 판정한다.

        전에는 mclsfNm 과 plcyKywdNm 까지 이어 붙인 문자열에서 별칭을 찾았다.
        그래서 키워드가 '교육지원'이면 대분류가 일자리인 정책까지 교육 필터에
        걸렸다. 실제로 `청년미래플러스`(일자리)와 `경계선지능청년지원`
        (금융･복지･문화)이 교육 목록에 섞여 나왔다.

        중분류·키워드는 검색어(`q`)가 훑는 자리다. 카테고리 탭은 사용자가
        고른 대분류 하나만 보여줘야 한다.
        """
        if not expected:
            return True
        # '일자리,교육'처럼 서로 다른 대분류가 여럿인 정책이 50건 있다. 그중 하나만
        # 맞아도 해당 카테고리로 본다.
        actual = {
            part.strip()
            for part in str(policy.get("lclsfNm") or "").split(",")
            if part.strip()
        }
        aliases = CATEGORY_ALIASES.get(str(expected), (str(expected),))
        return any(alias in actual for alias in aliases)

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
