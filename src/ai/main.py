"""AI 서비스 FastAPI 앱.

컨테이너를 분리하면 백엔드가 ``from src.rag.retriever import PolicyRetriever``
처럼 파이썬 import로 RAG를 쓸 수 없다. 다른 프로세스·다른 파일시스템이기
때문이다. 그래서 무거운 객체는 이 프로세스에만 올리고 HTTP 창구 세 개로
노출한다.

    GET  /health     준비 상태 (백엔드 기동 순서 판정에 사용)
    POST /interpret  대화 의도 해석 (검색 전 단계)
    POST /search     PolicyRetriever.search
    POST /generate   SolarGenerator.stream_answer (NDJSON 스트리밍)
    POST /ocr        이미지에서 텍스트 추출 (F4·P3)

OCR도 여기 있는 이유는 torch 때문이다. easyocr 은 torch 를 끌고 오는데,
이 컨테이너에는 임베딩 모델용 torch 가 이미 있다. 백엔드에 넣으면 같은 2GB
라이브러리가 두 컨테이너에 중복으로 설치된다.

모델 적재는 수 분이 걸릴 수 있으므로 ``/health`` 는 모델이 없어도 즉시
응답해야 한다. 그래야 compose 의 healthcheck 가 "아직 준비 안 됨"을 구분한다.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.ai.schemas import (
    AIHealthResponse,
    ERROR_KEY,
    GenerateRequest,
    InterpretRequest,
    InterpretResponse,
    OcrResponse,
    SearchRequest,
    SearchResponse,
    TOKEN_KEY,
)

# 이미지 한 장 상한. 이보다 큰 사진은 OCR 정확도보다 메모리가 먼저 문제가 된다.
MAX_IMAGE_BYTES = 20 * 1024 * 1024

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
        from src.rag.interpreter import ConversationInterpreter

        application.state.generator = SolarGenerator()
        # 의도 해석기는 생성기와 같은 Solar 클라이언트를 재사용한다.
        application.state.interpreter = ConversationInterpreter.from_generator(
            application.state.generator
        )
        logger.info("SolarGenerator 준비 완료 · model=%s", application.state.generator.model)
    except Exception as error:  # noqa: BLE001
        # 키가 없어도 검색은 되어야 하므로 기동 자체는 막지 않는다.
        application.state.generator_error = str(error)
        logger.warning("SolarGenerator 준비 실패(검색은 계속 가능): %s", error)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.retriever = None
    application.state.generator = None
    application.state.interpreter = None
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


@app.post("/interpret", response_model=InterpretResponse, summary="대화 의도 해석")
def interpret(body: InterpretRequest, request: Request) -> InterpretResponse:
    """검색을 돌리기 전에 입력의 성격을 판단한다.

    실패해도 503 을 내지 않고 ``ok=False`` 로 응답한다. 백엔드가 그때
    기존 동작(무조건 검색)으로 되돌아가면 서비스는 그대로 굴러간다.
    """
    interpreter = request.app.state.interpreter
    if interpreter is None:
        return InterpretResponse(
            standalone_question=body.question,
            ok=False,
            error=request.app.state.generator_error or "의도 해석기가 준비되지 않았어요.",
        )
    result = interpreter.interpret(
        body.question, body.history, body.recent_policies, body.profile
    )
    logger.info(
        "의도 해석 · intent=%s ok=%s ids=%s conditions=%s",
        result.intent, result.ok, result.policy_ids, result.conditions,
    )
    return InterpretResponse(**result.to_dict())


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


@app.post("/ocr", response_model=OcrResponse, summary="이미지에서 텍스트 추출")
async def ocr(request: Request, filename: str = Query(default="image")):
    """원본 이미지 바이트를 그대로 본문에 담아 받는다.

    multipart 로 받으면 python-multipart 의존성이 하나 더 붙는데, 백엔드가
    이미 확장자를 검사한 뒤 넘기므로 파일 이름은 로그용으로만 쓴다.

    OCR 파이프라인은 팀 ingest 담당(김영민)이 만든
    ``src/ingest/documents/vision.py`` 를 그대로 쓴다. 같은 로직을 여기서
    다시 구현하지 않는다.
    """
    data = await request.body()
    if not data:
        return JSONResponse(
            status_code=400, content={"detail": "빈 이미지예요.", "code": "invalid_file"}
        )
    if len(data) > MAX_IMAGE_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "detail": f"이미지가 너무 커요({len(data) // (1024 * 1024)}MB). "
                          f"{MAX_IMAGE_BYTES // (1024 * 1024)}MB 이하로 올려주세요.",
                "code": "invalid_file",
            },
        )
    try:
        # easyocr 모델(약 100MB)은 첫 호출에서 내려받아 캐시된다. 그래서
        # import 도 함수 안에서 한다. 서비스 기동을 느리게 하지 않기 위해서다.
        from src.ingest.documents.vision import read_image

        text, note = read_image(data)
    except Exception as error:  # noqa: BLE001
        logger.exception("OCR 실패(%s): %s", filename, error)
        return _unavailable(f"이미지에서 글자를 읽지 못했어요: {error}", "ocr_failed")
    logger.info("OCR 완료(%s) · %d자", filename, len(text))
    return OcrResponse(text=text, note=note, chars=len(text))
