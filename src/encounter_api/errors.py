"""Domain exceptions and the handlers that turn them into clean responses.

Clients always receive a small, fixed-shape error body, never a stack trace or
internal detail. Unexpected failures are logged server-side with the request id
for correlation, and the logging filter screens any PHI from that record.
"""

import logging
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from encounter_api.models import ErrorResponse

logger = logging.getLogger(__name__)


class EncounterNotFound(Exception):
    def __init__(self, encounter_id: UUID) -> None:
        self.encounter_id = encounter_id
        super().__init__(f"encounter {encounter_id} not found")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error(status_code: int, body: ErrorResponse) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(by_alias=True, exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EncounterNotFound)
    async def handle_not_found(request: Request, exc: EncounterNotFound) -> JSONResponse:
        return _error(
            status.HTTP_404_NOT_FOUND,
            ErrorResponse(
                error="not_found",
                message="Encounter not found",
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Report which fields failed and why, but never echo the submitted
        # values back: a bad value could itself be PHI.
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "issue": error["msg"],
            }
            for error in exc.errors()
        ]
        return _error(
            status.HTTP_400_BAD_REQUEST,
            ErrorResponse(
                error="validation_error",
                message="Request failed validation",
                request_id=_request_id(request),
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(
            exc.status_code,
            ErrorResponse(
                error="http_error",
                message=str(exc.detail),
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled error",
            extra={
                "request_id": _request_id(request),
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred",
                request_id=_request_id(request),
            ),
        )
