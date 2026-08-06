"""대화 의도 해석기.

검색을 돌리기 전에 "이 입력이 무엇인지" 를 Solar 에게 한 번 물어본다.
단어 목록으로 판별하던 방식(``prompts.FOLLOW_UP_HINTS`` 등)을 대체한다.

세 가지를 한 번에 받아온다.

    intent               chat / search / follow_up
    standalone_question  "3번은?" -> "청년 월세지원 정책의 신청 방법은?"
    conditions           현재 입력에서 새로 확인된 사용자 조건

웹(``src/ai/main.py`` 의 ``POST /interpret``)과 터미널 챗봇
(``src/rag/cli/terminal_chatbot.py``)이 이 파일을 함께 쓴다. 판별 로직이
두 벌로 갈라지지 않게 하기 위해서다.

해석에 실패하면 예외를 던지지 않고 ``ok=False`` 를 돌려준다. 호출하는 쪽은
그때 기존 동작(무조건 검색)으로 되돌아가면 되므로, 이 단계가 고장 나도
서비스가 멈추지 않는다.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

INTENT_CHAT = "chat"
INTENT_SEARCH = "search"
INTENT_FOLLOW_UP = "follow_up"
VALID_INTENTS = frozenset({INTENT_CHAT, INTENT_SEARCH, INTENT_FOLLOW_UP})

CONDITION_KEYS = ("age", "region", "employment", "education", "income_bracket")

# 해석은 짧은 JSON 한 덩어리만 돌려주면 된다. 토큰을 작게 잡아 응답을 빠르게 한다.
MAX_TOKENS = 400
HISTORY_LIMIT = 4
POLICY_LIMIT = 10

INTERPRET_SYSTEM_PROMPT = """당신은 대한민국 청년정책 챗봇의 대화 분석기입니다.
사용자의 현재 입력을 읽고 아래 형식의 JSON 하나만 출력하세요.
설명, 코드블록 표시, 다른 문장을 절대 덧붙이지 마세요.

{
  "intent": "chat 또는 search 또는 follow_up",
  "standalone_question": "이전 대화를 모르는 사람도 이해할 수 있는 완전한 질문",
  "policy_ids": [],
  "conditions": {"age": null, "region": null, "employment": null, "education": null, "income_bracket": null}
}

[intent 판단]
- chat: 인사, 감사, 잡담, 챗봇 자신에 대한 질문처럼 정책을 찾을 필요가 없는 입력
- follow_up: [직전에 안내한 정책] 중 특정 정책을 가리키는 입력
  예) "3번은 어떻게 신청해?", "그 정책 기간이 언제야?", "두 번째 거 자세히"
- search: 그 외 전부. 새로운 정책을 찾으려는 입력

[standalone_question]
- 지시 표현("그중", "3번", "그 정책")을 실제 정책명으로 바꾼 문장으로 쓰세요.
- intent 가 chat 이면 현재 입력을 그대로 쓰세요.

[policy_ids]
- follow_up 일 때만 [직전에 안내한 정책] 목록에 있는 실제 ID 를 넣으세요.
- 가리키는 정책이 목록에 없으면 intent 를 search 로 하고 빈 배열을 쓰세요.

[conditions]
- 현재 입력에서 새로 확인된 값만 채우고 나머지는 null 로 두세요.
- 부정하는 표현은 조건이 아닙니다. "울산에 살지 않아요" 는 region 을 null 로 두세요.
- "울산 말고", "서울은 빼고" 같은 제외 표현도 조건으로 넣지 마세요.
- age 와 income_bracket 은 숫자, 나머지는 문자열입니다. 모르면 null 입니다.
"""


@dataclass
class Interpretation:
    """해석 결과. ``ok=False`` 면 호출하는 쪽이 기존 방식으로 처리한다."""

    intent: str = INTENT_SEARCH
    standalone_question: str = ""
    policy_ids: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    ok: bool = False
    error: str = ""

    @property
    def needs_search(self) -> bool:
        return self.intent == INTENT_SEARCH

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "standalone_question": self.standalone_question,
            "policy_ids": list(self.policy_ids),
            "conditions": dict(self.conditions),
            "ok": self.ok,
            "error": self.error,
        }


def _format_history(history: Sequence[Mapping[str, str]]) -> str:
    if not history:
        return "(없음)"
    lines = []
    for message in list(history)[-HISTORY_LIMIT:]:
        speaker = "사용자" if message.get("role") == "user" else "챗봇"
        content = " ".join(str(message.get("content") or "").split())[:300]
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def _format_policies(policies: Sequence[Mapping[str, Any]]) -> str:
    """직전에 안내한 정책 목록. 제목만 보낸다(본문을 보내면 느려진다)."""
    if not policies:
        return "(없음)"
    lines = []
    for number, policy in enumerate(list(policies)[:POLICY_LIMIT], start=1):
        policy_id = str(policy.get("plcy_no") or policy.get("policy_id") or "")
        title = str(policy.get("title") or policy.get("policy_name") or "이름 없는 정책")
        lines.append(f"{number}. (ID: {policy_id}) {title}")
    return "\n".join(lines)


def build_user_prompt(
    question: str,
    history: Sequence[Mapping[str, str]] = (),
    recent_policies: Sequence[Mapping[str, Any]] = (),
    profile: Mapping[str, Any] | None = None,
) -> str:
    return "\n\n".join(
        [
            "[저장된 사용자 조건]\n" + json.dumps(dict(profile or {}), ensure_ascii=False),
            "[최근 대화]\n" + _format_history(history),
            "[직전에 안내한 정책]\n" + _format_policies(recent_policies),
            "[현재 입력]\n" + question.strip(),
        ]
    )


def _extract_json(raw: str) -> dict[str, Any] | None:
    """모델이 코드블록이나 잡문을 섞어도 JSON 덩어리만 건져낸다."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _clean_conditions(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    cleaned: dict[str, Any] = {}
    for key in CONDITION_KEYS:
        item = value.get(key)
        if item is None or item == "" or item == "null":
            continue
        if key in {"age", "income_bracket"}:
            try:
                cleaned[key] = int(item)
            except (TypeError, ValueError):
                continue
        else:
            cleaned[key] = str(item).strip()
    return cleaned


def parse_interpretation(
    raw: str, question: str, known_policy_ids: Sequence[str] = ()
) -> Interpretation:
    """모델 출력 문자열을 Interpretation 으로 바꾼다. 실패해도 예외를 내지 않는다."""
    parsed = _extract_json(raw)
    if parsed is None:
        return Interpretation(
            standalone_question=question, ok=False, error="JSON을 찾지 못했습니다."
        )

    intent = str(parsed.get("intent") or "").strip()
    if intent not in VALID_INTENTS:
        return Interpretation(
            standalone_question=question, ok=False, error=f"알 수 없는 intent: {intent!r}"
        )

    standalone = str(parsed.get("standalone_question") or "").strip() or question

    known = {str(item) for item in known_policy_ids}
    policy_ids = [
        str(item)
        for item in (parsed.get("policy_ids") or [])
        if not known or str(item) in known
    ]
    # 가리킬 정책을 못 찾았으면 후속 질문으로 처리할 수 없다. 검색으로 되돌린다.
    if intent == INTENT_FOLLOW_UP and not policy_ids:
        intent = INTENT_SEARCH

    return Interpretation(
        intent=intent,
        standalone_question=standalone,
        policy_ids=policy_ids,
        conditions=_clean_conditions(parsed.get("conditions")),
        ok=True,
    )


class ConversationInterpreter:
    """Solar 로 의도를 해석한다. 생성기와 같은 클라이언트를 재사용한다."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @classmethod
    def from_generator(cls, generator: Any) -> "ConversationInterpreter":
        return cls(generator.client, generator.model)

    def interpret(
        self,
        question: str,
        history: Sequence[Mapping[str, str]] = (),
        recent_policies: Sequence[Mapping[str, Any]] = (),
        profile: Mapping[str, Any] | None = None,
    ) -> Interpretation:
        known_ids = [
            str(policy.get("plcy_no") or policy.get("policy_id") or "")
            for policy in recent_policies
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTERPRET_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            question, history, recent_policies, profile
                        ),
                    },
                ],
                temperature=0,
                max_tokens=MAX_TOKENS,
            )
            raw = response.choices[0].message.content or ""
        except Exception as error:  # noqa: BLE001 - 해석 실패가 서비스를 막으면 안 된다
            logger.warning("의도 해석 호출 실패: %s", error)
            return Interpretation(
                standalone_question=question, ok=False, error=str(error)
            )

        result = parse_interpretation(raw, question, known_ids)
        if not result.ok:
            logger.warning("의도 해석 파싱 실패(%s): %r", result.error, raw[:200])
        return result


__all__ = [
    "CONDITION_KEYS",
    "ConversationInterpreter",
    "INTENT_CHAT",
    "INTENT_FOLLOW_UP",
    "INTENT_SEARCH",
    "Interpretation",
    "build_user_prompt",
    "parse_interpretation",
]
