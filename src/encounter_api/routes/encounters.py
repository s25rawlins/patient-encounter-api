"""Encounter endpoints: create, fetch by id, and filtered list."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from encounter_api.auth import CurrentPrincipal
from encounter_api.dependencies import EncounterServiceDep
from encounter_api.models import Encounter, EncounterCreate
from encounter_api.repository import EncounterQuery

router = APIRouter(prefix="/encounters", tags=["encounters"])


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Encounter)
def create_encounter(
    payload: EncounterCreate,
    principal: CurrentPrincipal,
    service: EncounterServiceDep,
) -> Encounter:
    """Create an encounter and return it with its generated id."""
    return service.create_encounter(payload, actor_id=principal.subject)


@router.get("/{encounter_id}", response_model=Encounter)
def get_encounter(
    encounter_id: UUID,
    principal: CurrentPrincipal,
    service: EncounterServiceDep,
) -> Encounter:
    """Fetch a single encounter by id. The read is recorded in the audit trail."""
    return service.get_encounter(encounter_id, actor_id=principal.subject)


@router.get("", response_model=list[Encounter])
def list_encounters(
    principal: CurrentPrincipal,
    service: EncounterServiceDep,
    patient_id: Annotated[str | None, Query(alias="patientId")] = None,
    provider_id: Annotated[str | None, Query(alias="providerId")] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[Encounter]:
    """List encounters, optionally filtered by patient, provider, or date range."""
    query = EncounterQuery(
        patient_id=patient_id,
        provider_id=provider_id,
        date_from=_as_utc(date_from),
        date_to=_as_utc(date_to),
    )
    return service.list_encounters(query, actor_id=principal.subject)
