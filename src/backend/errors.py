"""서비스 예외를 일관된 JSON HTTP 응답으로 바꾼다."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    status_code = 400
    code = "service_error"

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(ServiceError):
    status_code = 404
    code = "not_found"


class InvalidFileError(ServiceError):
    status_code = 400
    code = "invalid_file"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, error: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "code": error.code},
        )
