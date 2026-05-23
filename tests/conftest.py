"""Shared test fixtures.

``create_app()`` builds fresh in-memory repositories on every call, so each test
gets an isolated application with no shared state and no teardown to remember.
"""

import pytest
from fastapi.testclient import TestClient

from encounter_api.auth import issue_token
from encounter_api.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token('dr-okafor')}"}


@pytest.fixture
def valid_encounter() -> dict:
    return {
        "patientId": "patient-2847",
        "providerId": "dr-okafor",
        "encounterDate": "2026-05-23T14:30:00Z",
        "encounterType": "follow_up",
        "clinicalData": {"note": "Patient reports improved sleep this week."},
    }
