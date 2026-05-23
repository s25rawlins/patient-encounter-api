"""Encounter endpoints: create, fetch by id, and filtered list."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from encounter_api.auth import CurrentPrincipal
from encounter_api.dependencies import EncounterServiceDep
from encounter_api.models import Encounter, EncounterCreate
from encounter_api.repository import EncounterQuery
from encounter_api.timeutils import ensure_utc

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Encounter)
def create_encounter(
    payload: EncounterCreate,
    principal: CurrentPrincipal,
    service: EncounterServiceDep,
) -> Encounter:
    return service.create_encounter(payload, actor_id=principal.subject)


@router.get("/{encounter_id}", response_model=Encounter)
def get_encounter(
    encounter_id: UUID,
    principal: CurrentPrincipal,
    service: EncounterServiceDep,
) -> Encounter:
    """Reading an encounter is recorded in the audit trail."""
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
    query = EncounterQuery(
        patient_id=patient_id,
        provider_id=provider_id,
        date_from=ensure_utc(date_from),
        date_to=ensure_utc(date_to),
    )
    return service.list_encounters(query, actor_id=principal.subject)
