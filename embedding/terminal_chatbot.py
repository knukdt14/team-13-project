"""BGE-M3 검색과 Solar API를 연결한 터미널 청년정책 챗봇."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


def _bootstrap_direct_execution() -> None:
    """직접 실행 시 패키지 경로를 잡고 GPU 가상환경으로 다시 실행한다."""
    if __package__:
        return

    embedding_dir = Path(__file__).resolve().parent
    project_dir = embedding_dir.parent
    gpu_python = embedding_dir / ".venv-gpu" / "Scripts" / "python.exe"

    if gpu_python.exists() and Path(sys.executable).resolve() != gpu_python.resolve():
        completed = subprocess.run(
            [
                str(gpu_python),
                "-m",
                "embedding.terminal_chatbot",
                *sys.argv[1:],
            ],
            cwd=project_dir,
        )
        raise SystemExit(completed.returncode)

    project_path = str(project_dir)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)


_bootstrap_direct_execution()

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

if __package__:
    from .config import EMBEDDING_DIR
    from .retriever import PolicyRetriever
else:
    from embedding.config import EMBEDDING_DIR
    from embedding.retriever import PolicyRetriever


SYSTEM_PROMPT = """당신은 대한민국 청년정책 안내 챗봇입니다.
아래 원칙을 반드시 지키세요.
1. 제공된 검색 결과만 근거로 답하고, 자료에 없는 사실은 추측하지 마세요.
2. 사용자 조건과 맞는 이유, 지원 내용, 신청 기간과 방법을 이해하기 쉽게 설명하세요.
3. 근거 정책을 문장 끝에 [정책 1]처럼 표시하세요.
4. 신청 자격은 최종 확정이 아니므로 공식 신청 페이지에서 확인하도록 안내하세요.
5. 정책 자료가 서로 충돌하거나 정보가 없으면 그 사실을 솔직하게 말하세요.
6. 한국어로 간결하고 친절하게 답하세요.
"""

FOLLOW_UP_HINTS = (
    "그중",
    "그 정책",
    "이 정책",
    "첫 번째",
    "두 번째",
    "신청 방법",
    "어떻게 신청",
    "언제까지",
    "자세히",
    "링크",
)


class TerminalPolicyChatbot:
    def __init__(
        self,
        top_k: int = 5,
        include_closed: bool = False,
        mode: str = "hybrid",
    ) -> None:
        load_dotenv(EMBEDDING_DIR / ".env")
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "UPSTAGE_API_KEY가 없습니다. embedding/.env 파일을 확인하세요."
            )

        self.solar_model = os.getenv("UPSTAGE_MODEL", "solar-pro3")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.upstage.ai/v1",
        )
        self.retriever = PolicyRetriever()
        self.top_k = top_k
        self.include_closed = include_closed
        self.mode = mode
        self.history: list[dict[str, str]] = []
        self.previous_question: str | None = None

    def chat(self, question: str) -> None:
        retrieval_question = self._make_retrieval_question(question)
        result = self.retriever.search(
            retrieval_question,
            top_k=self.top_k,
            include_closed=self.include_closed,
            mode=self.mode,
        )

        self._print_search_summary(result)
        policies = result["policies"]
        if not policies:
            if self.include_closed:
                print("\nSolar: 조건에 맞는 정책을 찾지 못했습니다. 조건을 조금 넓혀 질문해 주세요.\n")
            else:
                print(
                    "\nSolar: 현재 접수 중인 정책을 찾지 못했습니다. "
                    "`/마감포함`을 입력하면 마감 정책도 함께 검색합니다.\n"
                )
            self.previous_question = question
            return

        context = self._format_context(policies)
        user_prompt = (
            f"사용자의 실제 질문:\n{question}\n\n"
            f"검색에 사용된 조건:\n"
            f"{json.dumps(result['extracted_conditions'], ensure_ascii=False)}\n\n"
            f"검색된 정책 자료:\n{context}"
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.history[-6:],
            {"role": "user", "content": user_prompt},
        ]

        print("\nSolar: ", end="", flush=True)
        answer_parts: list[str] = []
        try:
            stream = self.client.chat.completions.create(
                model=self.solar_model,
                messages=messages,
                stream=True,
                temperature=0.2,
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    answer_parts.append(content)
                    print(content, end="", flush=True)
        except OpenAIError as error:
            print(f"Solar API 호출에 실패했습니다: {error}")
            return

        answer = "".join(answer_parts)
        print("\n")
        self._print_sources(policies)
        self.history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
        )
        self.previous_question = question

    def _make_retrieval_question(self, question: str) -> str:
        is_follow_up = any(hint in question for hint in FOLLOW_UP_HINTS)
        if self.previous_question and (is_follow_up or len(question.strip()) <= 15):
            return f"{self.previous_question}\n후속 질문: {question}"
        return question

    @staticmethod
    def _format_context(policies: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        for number, policy in enumerate(policies, start=1):
            metadata = policy["metadata"]
            text = str(policy.get("matched_text") or "")[:4000]
            blocks.append(
                "\n".join(
                    [
                        f"[정책 {number}]",
                        f"정책 ID: {policy['policy_id']}",
                        f"정책명: {policy['policy_name']}",
                        f"유사도: {policy['score']}",
                        f"신청 기간: {metadata.get('application_start')} ~ "
                        f"{metadata.get('application_end')}",
                        f"접수 상태: {'접수 중' if metadata.get('is_open') else '마감/접수 전'}",
                        f"운영 기관: {metadata.get('organization')}",
                        f"소득 조건: {metadata.get('income_condition')} / "
                        f"{metadata.get('income_details')}",
                        f"신청 URL: {metadata.get('application_url')}",
                        f"참고 URL: {metadata.get('reference_url')}",
                        f"정책 내용:\n{text}",
                    ]
                )
            )
        return "\n\n".join(blocks)[:18000]

    @staticmethod
    def _print_search_summary(result: dict[str, Any]) -> None:
        conditions = result["extracted_conditions"]
        condition_text = ", ".join(f"{key}={value}" for key, value in conditions.items())
        print(f"\n[검색 조건] {condition_text or '추출된 조건 없음'}")
        print(f"[검색 결과] {result['result_count']}건")

    @staticmethod
    def _print_sources(policies: list[dict[str, Any]]) -> None:
        print("[참고 정책]")
        for number, policy in enumerate(policies, start=1):
            metadata = policy["metadata"]
            url = metadata.get("application_url") or metadata.get("reference_url") or "URL 없음"
            print(f"  [정책 {number}] {policy['policy_name']} - {url}")
        print()

    def reset(self) -> None:
        self.history.clear()
        self.previous_question = None


def print_help() -> None:
    print(
        """
명령어
  /도움말    명령어 보기
  /초기화    대화 기록 지우기
  /마감포함  마감 정책도 검색하기
  /마감제외  접수 중인 정책만 검색하기
  /종료      챗봇 종료
"""
    )


def main() -> None:
    # Solar 답변의 이모지·특수문자가 Windows CP949에서 출력을 중단시키지 않게 한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Solar 청년정책 터미널 챗봇")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-closed", action="store_true")
    parser.add_argument(
        "--mode", choices=("vector", "bm25", "hybrid"), default="hybrid"
    )
    parser.add_argument(
        "--question", help="질문 하나에 답한 뒤 종료합니다. 자동 테스트에 유용합니다."
    )
    args = parser.parse_args()

    print("BGE-M3 정책 검색기와 Solar 챗봇을 불러오는 중입니다...")
    chatbot = TerminalPolicyChatbot(args.top_k, args.include_closed, args.mode)
    if args.question:
        chatbot.chat(args.question)
        return
    print("\n청년정책 챗봇입니다. 궁금한 정책을 질문해 주세요. (`/도움말`, `/종료`)\n")

    while True:
        try:
            question = input("나: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n챗봇을 종료합니다.")
            break
        if not question:
            continue
        if question in {"/종료", "/exit", "exit", "quit"}:
            print("챗봇을 종료합니다.")
            break
        if question == "/도움말":
            print_help()
            continue
        if question == "/초기화":
            chatbot.reset()
            print("대화 기록을 초기화했습니다.\n")
            continue
        if question == "/마감포함":
            chatbot.include_closed = True
            print("마감 정책도 검색합니다.\n")
            continue
        if question == "/마감제외":
            chatbot.include_closed = False
            print("접수 중인 정책만 검색합니다.\n")
            continue
        chatbot.chat(question)


if __name__ == "__main__":
    main()
