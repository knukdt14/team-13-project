"""RAG 공개 인터페이스.

박준혁의 실제 구현이 들어오기 전에는 ``RAG_STUB=true``가 검증용 스텁을 연결한다.
"""

from __future__ import annotations

import os

from src.rag import stub

USE_STUB = os.getenv("RAG_STUB", "true").lower() == "true"


def _real_not_available(*_args, **_kwargs):
    raise RuntimeError("실제 RAG 구현이 아직 연결되지 않았습니다. RAG_STUB=true를 사용하세요.")


search = stub.search if USE_STUB else _real_not_available
answer = stub.answer if USE_STUB else _real_not_available
stream_answer = stub.stream_answer if USE_STUB else _real_not_available

__all__ = ["USE_STUB", "answer", "search", "stream_answer"]
