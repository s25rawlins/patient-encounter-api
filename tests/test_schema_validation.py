"""Malformed input is rejected with a clean 400 that leaks no internals.

The error names which fields failed, but it does not echo submitted values
(which could be PHI) and does not surface validation-library internals.
"""

from typing import Any

from fastapi.testclient import TestClient


def test_malformed_payload_returns_structured_400(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    # Missing patientId and an encounterType outside the allowed set.
    payload = {
        "providerId": "dr-okafor",
        "encounterDate": "2026-05-23T14:30:00Z",
        "encounterType": "telepathy",
        "clinicalData": {},
    }
    response = client.post("/encounters", json=payload, headers=auth_headers)

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "validation_error"
    assert isinstance(body["details"], list) and body["details"]
    assert all({"field", "issue"} <= set(item) for item in body["details"])

    text = response.text.lower()
    assert "telepathy" not in text  # submitted value is not reflected back
    assert "pydantic" not in text
    assert "traceback" not in text


def test_unknown_fields_are_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    valid_encounter: dict[str, Any],
) -> None:
    payload = valid_encounter | {"ssn": "123-45-6789"}
    response = client.post("/encounters", json=payload, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert "123-45-6789" not in response.text
