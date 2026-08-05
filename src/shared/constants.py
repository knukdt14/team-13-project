"""여러 계층이 공유하는 값만 둔다. 업무 로직은 각 담당 패키지에 둔다."""

from __future__ import annotations

ANY_VALUE = "제한없음"
NATIONWIDE_MIN_CODES = 200
APPLY_ALWAYS_CODE = "0057002"
APPLY_CLOSED_CODE = "0057003"
SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

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
