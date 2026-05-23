"""Request, response, and audit models for the encounter API.

The API speaks camelCase on the wire (``patientId``, ``encounterDate``) while
the Python code stays snake_case. A camelCase alias generator bridges the two,
so callers and handlers each get the convention they expect.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class EncounterType(StrEnum):
    INITIAL_ASSESSMENT = "initial_assessment"
    FOLLOW_UP = "follow_up"
    TREATMENT_SESSION = "treatment_session"


class EncounterCreate(CamelModel):
    """Incoming payload for creating an encounter.

    ``extra="forbid"`` (inherited) rejects unknown top-level fields, which keeps
    typos and unexpected input from silently passing validation. ``clinicalData``
    is intentionally open, since clinical content varies by encounter type.
    """

    patient_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    encounter_date: datetime
    encounter_type: EncounterType
    clinical_data: dict[str, Any] = Field(default_factory=dict)


class EncounterMetadata(CamelModel):
    created_at: datetime
    updated_at: datetime
    created_by: str


class Encounter(CamelModel):
    encounter_id: UUID
    patient_id: str
    provider_id: str
    encounter_date: datetime
    encounter_type: EncounterType
    clinical_data: dict[str, Any]
    metadata: EncounterMetadata


class AuditAction(StrEnum):
    CREATE = "create"
    READ = "read"
    QUERY = "query"


class AuditEntry(CamelModel):
    """A single access record for the compliance trail.

    Deliberately holds no PHI. It references the encounter by id, not the
    patient, so the audit store never becomes a second copy of patient data.
    """

    audit_id: UUID
    action: AuditAction
    actor_id: str
    encounter_id: UUID | None = None
    occurred_at: datetime


class ErrorResponse(CamelModel):
    error: str
    message: str
    request_id: str | None = None
    details: list[dict[str, str]] | None = None
