"""여러 계층이 공유하는 값만 둔다. 업무 로직은 각 담당 패키지에 둔다."""

from __future__ import annotations

ANY_VALUE = "제한없음"
NATIONWIDE_MIN_CODES = 200
APPLY_ALWAYS_CODE = "0057002"
APPLY_CLOSED_CODE = "0057003"
SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

# 이 서비스가 다루는 청년 나이 범위. 두 곳에서 쓴다.
#   - UserProfile: 이 범위 밖 나이는 422로 거절한다
#   - PolicyFilter: 나이가 명시되지 않은 정책의 경계를 이 값으로 채운다
#
# 청년기본법은 19~34세지만 지자체 조례가 더 넓게 잡아 데이터가 훨씬 넓다.
# 수집한 2,698건 중 나이를 명시한 정책의 실제 분포는 이렇다.
#   하한  19세(814) · 18세(458) · 15세(60) · 17세(12)
#   상한  39세(890) · 45세(158) · 34세(136) · 49세(75)
#
# 상한을 39로 막으면 45·49세까지 받는 233건이 40대에게 안 보인다.
# 접수중인 708건 기준으로 39세는 681건, 40세는 53건까지 떨어진다.
#
# 하한을 15보다 낮추지 않는 이유: 15세 미만을 적은 정책 22건은 대부분
# 신청자가 아니라 자녀 나이다(가정양육수당 2~6세, 청소년 한부모 1~24세).
YOUTH_MIN_AGE = 15
YOUTH_MAX_AGE = 49

SIDO: dict[str, str] = {
    "11": "서울특별시",
    "12": "전남광주통합특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "30": "대전광역시",
    "31": "울산광역시",
    "36": "세종특별자치시",
    "41": "경기도",
    "43": "충청북도",
    "44": "충청남도",
    "47": "경상북도",
    "48": "경상남도",
    "50": "제주특별자치도",
    "51": "강원특별자치도",
    "52": "전북특별자치도",
}


def sido_code(value: str | None) -> str | None:
    """시도 코드 또는 이름을 정책 데이터의 2자리 코드로 바꾼다."""
    if not value:
        return None
    value = value.strip()
    if value[:2] in SIDO:
        return value[:2]
    for code, name in SIDO.items():
        if value == name or value in name or name in value:
            return code
    return None
