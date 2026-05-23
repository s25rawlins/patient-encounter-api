"""A created encounter can be read back unchanged, with server-assigned fields.

This is the end-to-end contract: validation, id generation, storage, and
serialization all have to agree for the roundtrip to hold.
"""

from typing import Any

from fastapi.testclient import TestClient


def test_create_then_get_returns_same_encounter(
    client: TestClient,
    auth_headers: dict[str, str],
    valid_encounter: dict[str, Any],
) -> None:
    created = client.post("/encounters", json=valid_encounter, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()

    assert body["encounterId"]
    assert body["patientId"] == valid_encounter["patientId"]
    assert body["encounterType"] == valid_encounter["encounterType"]
    assert body["clinicalData"] == valid_encounter["clinicalData"]
    assert body["metadata"]["createdBy"] == "dr-okafor"
    assert body["metadata"]["createdAt"]

    fetched = client.get(f"/encounters/{body['encounterId']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json() == body
