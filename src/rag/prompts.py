"""Solar 정책 답변 생성에 사용하는 프롬프트와 대화 의도 표현."""

from __future__ import annotations

import re

SYSTEM_PROMPT = """당신은 대한민국 청년정책 안내 챗봇입니다.

[기본 원칙]
- 검색된 정책만 근거로 답하고, 없는 정보나 사용자 조건을 추측하지 마세요.
- '검색에 사용된 조건'은 질문과 웹의 '내 조건'을 합친 결과이므로 반드시 반영하세요.
- 조건과 명백히 충돌하는 정책은 제외하고, 불확실한 내용은 확인이 필요하다고 말하세요.
- 전국·마감 정책 포함 여부는 검색 결과를 그대로 따르세요.
- 한국어 존댓말로 간결하게 답하고 이모지와 불필요한 맺음말은 쓰지 마세요.
- 사용자가 요청하지 않으면 URL을 본문에 쓰지 마세요.

[응답 방법]
- 인사나 일상 대화에는 정책을 추천하지 말고 짧게 응답하세요.
- 첫 추천은 "관련 정책을 알려드릴게요."로 시작하세요.
- 관련도 순으로 최대 5개를 아래 형식으로 작성하세요.
  1. 정책명
     - 핵심 지원 내용 또는 관련 이유 한 문장
- 같은 정책은 한 번만 표시하고, 조건에 맞는 정책이 없으면 짧게 알리세요.
- 특정 정책에 대한 후속 질문은 그 정책의 요청받은 정보만 답하세요.
- 신청 방법·기간·세부 자격은 사용자가 물었을 때만 설명하세요.
"""

FOLLOW_UP_HINTS = (
    "그중",
    "그 정책",
    "이 정책",
    "첫 번째",
    "두 번째",
    "세 번째",
    "네 번째",
    "다섯 번째",
    "번 정책",
    "신청 방법",
    "신청방법",
    "어떻게 신청",
    "언제까지",
    "자세히",
    "링크",
)

GREETING_INPUTS = frozenset(
    {
        "안녕",
        "안녕하세요",
        "반가워",
        "반갑습니다",
        "하이",
        "hello",
        "hi",
        "고마워",
        "고맙습니다",
        "감사합니다",
    }
)

PERSONALIZED_REQUEST_HINTS = (
    "나에게 맞는",
    "내게 맞는",
    "나한테 맞는",
    "나에게 가장 관련",
    "내게 가장 관련",
    "나한테 가장 관련",
)


def is_greeting(question: str) -> bool:
    """검색 없이 답할 수 있는 짧은 인사인지 판별한다."""
    normalized = re.sub(r"[\s!?.~,]+", "", question).lower()
    return normalized in GREETING_INPUTS


def is_personalized_request(question: str) -> bool:
    """사용자 조건을 전제로 한 맞춤 정책 요청인지 판별한다."""
    compact = " ".join(question.split())
    return any(hint in compact for hint in PERSONALIZED_REQUEST_HINTS)


__all__ = [
    "SYSTEM_PROMPT",
    "FOLLOW_UP_HINTS",
    "GREETING_INPUTS",
    "PERSONALIZED_REQUEST_HINTS",
    "is_greeting",
    "is_personalized_request",
]
