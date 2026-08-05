"""AI 서비스 FastAPI 앱.

컨테이너를 분리하면 백엔드가 ``from src.rag.retriever import PolicyRetriever``
처럼 파이썬 import로 RAG를 쓸 수 없다. 다른 프로세스·다른 파일시스템이기
때문이다. 그래서 무거운 객체는 이 프로세스에만 올리고 HTTP 창구 세 개로
노출한다.

    GET  /health    준비 상태 (백엔드 기동 순서 판정에 사용)
    POST /search    PolicyRetriever.search
    POST /generate  SolarGenerator.stream_answer (NDJSON 스트리밍)

모델 적재는 수 분이 걸릴 수 있으므로 ``/health`` 는 모델이 없어도 즉시
응답해야 한다. 그래야 compose 의 healthcheck 가 "아직 준비 안 됨"을 구분한다.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.ai.schemas import (
    AIHealthResponse,
    ERROR_KEY,
    GenerateRequest,
    SearchRequest,
    SearchResponse,
    TOKEN_KEY,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [ai] %(message)s"
)
logger = logging.getLogger(__name__)


def _load_retriever(application: FastAPI) -> None:
    try:
        from src.rag.retriever import PolicyRetriever

        logger.info("PolicyRetriever 적재 시작 (임베딩 모델 다운로드에 수 분 걸릴 수 있음)")
        application.state.retriever = PolicyRetriever()
        logger.info(
            "PolicyRetriever 준비 완료 · 정책 %d건 · 청크 %d개 · device=%s",
            len(application.state.retriever.policies),
            len(application.state.retriever.documents),
            application.state.retriever.device,
        )
    except Exception as error:  # noqa: BLE001 - 어떤 실패든 상태로 보고한다
        application.state.retriever_error = str(error)
        logger.exception("PolicyRetriever 준비 실패: %s", error)


def _load_generator(application: FastAPI) -> None:
    try:
        from src.rag.generator import SolarGenerator

        application.state.generator = SolarGenerator()
        logger.info("SolarGenerator 준비 완료 · model=%s", application.state.generator.model)
    except Exception as error:  # noqa: BLE001
        # 키가 없어도 검색은 되어야 하므로 기동 자체는 막지 않는다.
        application.state.generator_error = str(error)
        logger.warning("SolarGenerator 준비 실패(검색은 계속 가능): %s", error)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.retriever = None
    application.state.generator = None
    application.state.retriever_error = None
    application.state.generator_error = None
    _load_retriever(application)
    _load_generator(application)
    yield


app = FastAPI(
    title="청년정책도우미 AI 서비스",
    description="FAISS 하이브리드 검색과 Solar 답변 생성을 HTTP로 노출한다.",
    version="1.0.0",
    lifespan=lifespan,
)


def _unavailable(detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": detail, "code": code})


@app.get("/health", response_model=AIHealthResponse, summary="AI 서비스 준비 상태")
def health(request: Request) -> AIHealthResponse:
    retriever = request.app.state.retriever
    generator = request.app.state.generator
    return AIHealthResponse(
        ok=retriever is not None,
        retriever_ready=retriever is not None,
        generator_ready=generator is not None,
        policies=len(retriever.policies) if retriever else 0,
        chunks=len(retriever.documents) if retriever else 0,
        device=getattr(retriever, "device", "") or "",
        retriever_error=request.app.state.retriever_error,
        generator_error=request.app.state.generator_error,
    )


@app.post("/search", response_model=SearchResponse, summary="정책 하이브리드 검색")
def search(body: SearchRequest, request: Request):
    retriever = request.app.state.retriever
    if retriever is None:
        return _unavailable(
            "정책 검색기가 준비되지 않았어요. "
            f"{request.app.state.retriever_error or 'FAISS 인덱스를 확인해주세요.'}",
            "rag_unavailable",
        )
    try:
        result = retriever.search(
            body.question,
            top_k=body.top_k,
            filters=body.filters or None,
            include_closed=body.include_closed,
            mode=body.mode,
        )
    except ValueError as error:
        return JSONResponse(
            status_code=400, content={"detail": str(error), "code": "invalid_request"}
        )
    return SearchResponse(**result)


@app.post("/generate", summary="Solar 답변 생성 (NDJSON 스트리밍)")
def generate(body: GenerateRequest, request: Request):
    generator = request.app.state.generator
    if generator is None:
        return _unavailable(
            "답변 생성기가 준비되지 않았어요. "
            f"{request.app.state.generator_error or 'UPSTAGE_API_KEY를 확인해주세요.'}",
            "rag_unavailable",
        )

    def lines() -> Iterator[str]:
        # 스트림이 시작된 뒤에는 HTTP 상태를 바꿀 수 없으므로, 도중 실패는
        # 마지막 줄에 error 로 실어 보내고 백엔드가 예외로 되살린다.
        try:
            for token in generator.stream_answer(
                body.question, body.conditions, body.policies, body.history
            ):
                yield json.dumps({TOKEN_KEY: token}, ensure_ascii=False) + "\n"
        except Exception as error:  # noqa: BLE001
            logger.exception("답변 생성 중 실패: %s", error)
            yield json.dumps({ERROR_KEY: str(error)}, ensure_ascii=False) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")
