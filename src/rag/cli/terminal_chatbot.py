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
        completed = subprocess.run(
            [
                str(gpu_python),
                "-m",
                "src.rag.cli.terminal_chatbot",
                *sys.argv[1:],
            ],
            cwd=project_dir,
        )
        raise SystemExit(completed.returncode)

    project_path = str(project_dir)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)


_bootstrap_direct_execution()

from openai import OpenAIError

if __package__:
    from ..generator import SolarGenerator
    from ..prompts import FOLLOW_UP_HINTS
    from ..retriever import PolicyRetriever
else:
    from src.rag.generator import SolarGenerator
    from src.rag.prompts import FOLLOW_UP_HINTS
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

        print("\nSolar: ", end="", flush=True)
        answer_parts: list[str] = []
        try:
            stream = self.generator.stream_answer(
                question,
                result["extracted_conditions"],
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
