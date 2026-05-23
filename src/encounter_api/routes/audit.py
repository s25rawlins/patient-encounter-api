"""Audit trail endpoint for compliance reads."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from encounter_api.auth import CurrentPrincipal
from encounter_api.dependencies import AuditServiceDep
from encounter_api.models import AuditEntry
from encounter_api.repository import AuditQuery

router = APIRouter(prefix="/audit", tags=["audit"])


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@router.get("/encounters", response_model=list[AuditEntry])
def list_encounter_audit(
    principal: CurrentPrincipal,
    service: AuditServiceDep,
    actor_id: Annotated[str | None, Query(alias="actorId")] = None,
    encounter_id: Annotated[UUID | None, Query(alias="encounterId")] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[AuditEntry]:
    """Return audit records, filtered by actor, encounter, or date range."""
    query = AuditQuery(
        actor_id=actor_id,
        encounter_id=encounter_id,
        date_from=_as_utc(date_from),
        date_to=_as_utc(date_to),
    )
    return service.list_entries(query)
