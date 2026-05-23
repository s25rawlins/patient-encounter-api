"""Audit trail endpoint for compliance reads."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from encounter_api.auth import CurrentPrincipal
from encounter_api.dependencies import AuditServiceDep
from encounter_api.models import AuditEntry
from encounter_api.repository import AuditQuery
from encounter_api.timeutils import ensure_utc

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/encounters", response_model=list[AuditEntry])
def list_encounter_audit(
    principal: CurrentPrincipal,
    service: AuditServiceDep,
    actor_id: Annotated[str | None, Query(alias="actorId")] = None,
    encounter_id: Annotated[UUID | None, Query(alias="encounterId")] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[AuditEntry]:
    query = AuditQuery(
        actor_id=actor_id,
        encounter_id=encounter_id,
        date_from=ensure_utc(date_from),
        date_to=ensure_utc(date_to),
    )
    return service.list_entries(query)
