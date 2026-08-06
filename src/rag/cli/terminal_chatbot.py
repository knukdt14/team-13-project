"""BGE-M3 검색과 Solar API를 연결한 터미널 청년정책 챗봇."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any


def _bootstrap_direct_execution() -> None:
    """직접 실행 시 패키지 경로를 잡고 GPU 가상환경으로 다시 실행한다."""
    if __package__:
        return

    rag_dir = Path(__file__).resolve().parents[1]
    project_dir = rag_dir.parents[1]
    gpu_python = rag_dir / ".venv-gpu" / "Scripts" / "python.exe"

    if gpu_python.exists() and Path(sys.executable).resolve() != gpu_python.resolve():
        try:
            completed = subprocess.run(
                [
                    str(gpu_python),
                    "-m",
                    "src.rag.cli.terminal_chatbot",
                    *sys.argv[1:],
                ],
                cwd=project_dir,
            )
        except KeyboardInterrupt:
            # 자식 프로세스 종료 뒤 부모 프로세스에 전달된 Ctrl+C의 traceback을 숨긴다.
            raise SystemExit(130) from None
        raise SystemExit(completed.returncode)

    project_path = str(project_dir)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)


_bootstrap_direct_execution()

from openai import OpenAIError

if __package__:
    from ..generator import SolarGenerator
    from ..interpreter import (
        INTENT_CHAT,
        INTENT_FOLLOW_UP,
        ConversationInterpreter,
    )
    from ..retriever import PolicyRetriever
else:
    from src.rag.generator import SolarGenerator
    from src.rag.interpreter import (
        INTENT_CHAT,
        INTENT_FOLLOW_UP,
        ConversationInterpreter,
    )
    from src.rag.retriever import PolicyRetriever


class TerminalPolicyChatbot:
    def __init__(
        self,
        top_k: int = 5,
        include_closed: bool = False,
        mode: str = "hybrid",
    ) -> None:
        self.retriever = PolicyRetriever()
        self.generator = SolarGenerator()
        self.interpreter = ConversationInterpreter.from_generator(self.generator)
        self.top_k = top_k
        self.include_closed = include_closed
        self.mode = mode
        self.history: list[dict[str, str]] = []
        self.recent_policies: list[dict[str, Any]] = []
        self.profile: dict[str, Any] = {}

    def chat(self, question: str) -> None:
        interpretation = self.interpreter.interpret(
            question,
            history=self.history,
            recent_policies=self.recent_policies,
            profile=self.profile,
        )
        if interpretation.ok:
            self.profile.update(interpretation.conditions)

        if interpretation.ok and interpretation.intent == INTENT_CHAT:
            self._generate_answer(question, self.profile, [])
            return

        if interpretation.ok and interpretation.intent == INTENT_FOLLOW_UP:
            policies = self._select_recent_policies(interpretation.policy_ids)
            if policies:
                self._generate_answer(question, self.profile, policies)
                self.recent_policies = policies
                return

        retrieval_question = (
            interpretation.standalone_question if interpretation.ok else question
        )
        result = self.retriever.search(
            retrieval_question,
            top_k=self.top_k,
            filters=self.profile or None,
            include_closed=self.include_closed,
            mode=self.mode,
        )

        self._print_search_summary(result)
        policies = result["policies"]
        if not policies:
            if self.include_closed:
                answer = "조건에 맞는 정책을 찾지 못했습니다. 조건을 조금 넓혀 질문해 주세요."
            else:
                answer = (
                    "현재 접수 중인 정책을 찾지 못했습니다. "
                    "`/마감포함`을 입력하면 마감 정책도 함께 검색합니다."
                )
            print(f"\nSolar: {answer}\n")
            self._remember(question, answer)
            return

        self._generate_answer(
            question,
            result["extracted_conditions"],
            policies,
        )
        self.recent_policies = policies

    def _generate_answer(
        self,
        question: str,
        conditions: dict[str, Any],
        policies: list[dict[str, Any]],
    ) -> None:
        print("\nSolar: ", end="", flush=True)
        answer_parts: list[str] = []
        try:
            stream = self.generator.stream_answer(
                question,
                conditions,
                policies,
                self.history,
            )
            for content in stream:
                answer_parts.append(content)
                print(content, end="", flush=True)
        except OpenAIError as error:
            print(f"Solar API 호출에 실패했습니다: {error}")
            return

        answer = "".join(answer_parts)
        print("\n")
        if policies:
            self._print_sources(policies)
        self._remember(question, answer)

    def _select_recent_policies(self, policy_ids: list[str]) -> list[dict[str, Any]]:
        selected = set(policy_ids)
        return [
            policy
            for policy in self.recent_policies
            if str(policy.get("policy_id") or "") in selected
        ]

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
            print(f"  [정책 {number}] {policy['policy_name']}")
        print()

    def _remember(self, question: str, answer: str) -> None:
        self.history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
        )

    def reset(self) -> None:
        self.history.clear()
        self.recent_policies.clear()
        self.profile.clear()


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
