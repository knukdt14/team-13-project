"""긴 정책 설명을 카드에 넣을 한 문장으로 줄여 둔다.

    python -m src.ingest.build_summaries

관공서 설명문은 마침표 없이 "~하고, ~하여"로 길게 이어져서 앞 문장만 잘라
쓰는 방식이 통하지 않는다. 그래서 Solar 로 한 번 줄여 파일에 저장하고,
백엔드는 그 파일을 읽기만 한다. 요청할 때마다 부르면 너무 느리다.

만들어내는 게 아니라 있는 문장을 줄이는 일이라 환각 위험이 낮다. 그래도
원문에 없는 숫자가 생기면 그 건은 버리고 원문을 쓰게 한다. 금액·나이·인원이
틀리면 사용자가 잘못된 정보로 신청을 판단하게 된다.

이어서 돌릴 수 있다. 이미 만든 항목은 건너뛰므로 중간에 끊겨도 다시 실행하면
남은 것만 처리한다.
"""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from openai import OpenAI

from src.rag.core.config import RAG_DIR
from src.shared.paths import DATA_DIR, STRUCTURED_POLICIES

OUTPUT_PATH = DATA_DIR / "policy_summaries.json"

# 이 길이 아래는 카드 두 줄에 그대로 들어간다. 건드릴 이유가 없다.
MIN_LENGTH = 90
WORKERS = 4

MAX_TOKENS = 200

# 챗봇이 쓰는 UPSTAGE_MODEL 을 따라가지 않는다.
#
# .env 의 기본값인 solar-pro4 는 추론형이라 답을 쓰기 전에 생각하는 토큰을
# 먼저 쓴다. 요약 한 줄에 900토큰을 추론에 쓰고 content 가 None 으로 왔다
# (finish_reason='length', reasoning_tokens == max_tokens).
#
# 요약은 있는 문장을 줄이는 일이라 추론할 것이 없다. 비추론 모델이 맞고,
# 더 빠르고 싸다. 바꿔야 하면 SUMMARY_MODEL 로 덮어쓸 수 있다.
DEFAULT_MODEL = "solar-pro3"

PROMPT = """정책 설명을 한 문장으로 줄여라.

규칙:
- 원문에 있는 내용만 쓴다. 없는 사실을 더하지 않는다.
- 숫자(금액·기간·인원·나이)가 있으면 반드시 살린다.
- 60자 이내. 명사로 끝낸다. "~합니다" 같은 종결어미를 쓰지 않는다.
- 사업 목적("~하고자", "~위하여")보다 무엇을 주는지를 앞에 둔다.

예)
원문: 지역의 청년모임을 대상으로한 버스킹 경연을 통하여 청년들의 지역활동 참여 및 재능발현의 장을 마련하고, 지역 상권을 이용하는 주민들에게 공연을 제공
요약: 청년모임 대상 버스킹 경연 참가 지원 및 지역 주민 공연 제공"""


def _description(policy: dict) -> str:
    return " ".join(
        str(policy.get("plcyExplnCn") or policy.get("plcySprtCn") or "").split()
    )


def _tidy(text: str) -> str:
    """모델이 형식을 안 지킨 경우를 정리한다.

    원문을 한 번 되풀이한 뒤 "요약: ..." 을 덧붙여 오는 일이 있다. 그때는
    마지막 "요약:" 뒤만 쓴다. 줄바꿈도 한 줄로 눌러 카드에 맞춘다.
    """
    text = text.strip()
    if "요약:" in text:
        text = text.rsplit("요약:", 1)[1]
    return " ".join(text.split())


def _is_safe(source: str, summary: str) -> tuple[bool, str]:
    """요약을 받아들일지 판단한다. 의심스러우면 버린다."""
    if not summary or len(summary) < 8:
        return False, "너무 짧음"
    # 카드는 두 줄(약 90자)이라 넘치면 CSS 가 한 번 더 줄인다. 그래도 원문
    # 400자보다는 훨씬 낫기 때문에 여기서 버리지 않는다. 150자는 "요약을
    # 안 하고 원문을 옮겨 적은 것"을 걸러내기 위한 선이다.
    if len(summary) > 150:
        return False, "너무 김"
    # 원문에 없는 숫자가 생겼다면 지어낸 것이다. 금액·나이가 틀리면 치명적이다.
    invented = set(re.findall(r"\d+", summary)) - set(re.findall(r"\d+", source))
    if invented:
        return False, f"원문에 없는 숫자 {sorted(invented)}"
    if len(summary) >= len(source):
        return False, "줄지 않음"
    return True, ""


def main() -> None:
    load_dotenv(RAG_DIR / ".env")
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        sys.exit("UPSTAGE_API_KEY 가 없습니다. src/rag/.env 를 확인해주세요.")
    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    model = os.getenv("SUMMARY_MODEL", DEFAULT_MODEL)
    print(f"모델: {model}")

    policies = json.loads(STRUCTURED_POLICIES.read_text(encoding="utf-8"))
    done: dict[str, str] = {}
    if OUTPUT_PATH.exists():
        done = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        print(f"이미 만들어 둔 요약 {len(done):,}건을 건너뜁니다.")

    targets = [
        policy
        for policy in policies
        if len(_description(policy)) > MIN_LENGTH
        and str(policy.get("plcyNo") or "") not in done
    ]
    print(f"요약할 정책 {len(targets):,}건 (설명이 {MIN_LENGTH}자를 넘는 것)")
    if not targets:
        print("새로 만들 것이 없습니다.")
        return

    rejected: list[tuple[str, str]] = []

    def summarize(policy: dict) -> tuple[str, str] | None:
        source = _description(policy)
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": source[:1500]},
                ],
            )
        except Exception as error:  # 한 건 실패로 전체를 멈추지 않는다.
            rejected.append((str(policy.get("plcyNm"))[:24], f"호출 실패 {error.__class__.__name__}"))
            return None

        choice = response.choices[0]
        summary = _tidy(choice.message.content or "")
        if not summary:
            # 추론형 모델이 토큰을 다 쓰면 여기로 온다. 원인을 알 수 있게 남긴다.
            rejected.append(
                (str(policy.get("plcyNm"))[:24], f"응답 없음 ({choice.finish_reason})")
            )
            return None
        ok, reason = _is_safe(source, summary)
        if not ok:
            rejected.append((str(policy.get("plcyNm"))[:24], reason))
            return None
        return str(policy["plcyNo"]), summary

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for index, result in enumerate(pool.map(summarize, targets), start=1):
            if result:
                done[result[0]] = result[1]
            if index % 25 == 0 or index == len(targets):
                print(f"  {index:>4}/{len(targets)}  성공 {len(done):,}건")
                OUTPUT_PATH.write_text(
                    json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8"
                )

    OUTPUT_PATH.write_text(
        json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n요약 {len(done):,}건 저장 → {OUTPUT_PATH}")
    if rejected:
        print(f"\n버린 것 {len(rejected)}건 (원문을 그대로 씁니다)")
        for name, reason in rejected[:10]:
            print(f"  · {name} — {reason}")


if __name__ == "__main__":
    main()
