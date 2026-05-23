"""PHI must never reach the logs, including on failure paths.

Two angles: the redaction filter scrubs PHI-named fields directly, and a request
that blows up mid-flight leaks nothing into the response or the logs.
"""

import io
import logging

from fastapi.testclient import TestClient

from encounter_api.auth import issue_token
from encounter_api.dependencies import get_encounter_service
from encounter_api.logging_config import JsonFormatter, PHIRedactionFilter
from encounter_api.main import create_app


def test_filter_redacts_phi_named_fields() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PHIRedactionFilter())

    logger = logging.getLogger("test.redaction")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info(
        "persisting encounter",
        extra={"patient_id": "patient-2847", "encounter_id": "enc-1", "request_id": "req-9"},
    )

    output = stream.getvalue()
    assert "patient-2847" not in output
    assert "[REDACTED]" in output
    # Safe correlation identifiers are kept so the log stays useful.
    assert "enc-1" in output
    assert "req-9" in output


class _FailingService:
    def create_encounter(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("backing store unavailable")


def test_error_path_leaks_no_phi(valid_encounter: dict) -> None:
    app = create_app()
    app.dependency_overrides[get_encounter_service] = _FailingService
    client = TestClient(app, raise_server_exceptions=False)

    captured = io.StringIO()
    handler = logging.StreamHandler(captured)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PHIRedactionFilter())
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        response = client.post(
            "/encounters",
            json=valid_encounter,
            headers={"Authorization": f"Bearer {issue_token('dr-okafor')}"},
        )
    finally:
        root.removeHandler(handler)

    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"
    # The patient id was in the request body but must surface nowhere.
    assert "patient-2847" not in response.text
    assert "patient-2847" not in captured.getvalue()
