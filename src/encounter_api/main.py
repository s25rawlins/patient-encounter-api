"""Application factory and ASGI entrypoint."""

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from encounter_api.config import DEFAULT_JWT_SECRET, get_settings
from encounter_api.errors import register_exception_handlers
from encounter_api.logging_config import configure_logging
from encounter_api.repository import InMemoryAuditRepository, InMemoryEncounterRepository
from encounter_api.routes import audit, encounters
from encounter_api.service import AuditService, EncounterService


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every request for log correlation."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.jwt_secret == DEFAULT_JWT_SECRET:
        logging.getLogger(__name__).warning(
            "using the built-in development JWT secret; "
            "set ENCOUNTER_API_JWT_SECRET before any shared deployment"
        )

    app = FastAPI(
        title="Patient Encounter API",
        version="0.1.0",
        summary="Manage patient clinical encounters with PHI-aware logging and an audit trail.",
    )

    encounter_repository = InMemoryEncounterRepository()
    audit_repository = InMemoryAuditRepository()
    app.state.encounter_repository = encounter_repository
    app.state.audit_repository = audit_repository
    app.state.encounter_service = EncounterService(encounter_repository, audit_repository)
    app.state.audit_service = AuditService(audit_repository)

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(encounters.router)
    app.include_router(audit.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
