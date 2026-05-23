"""Business logic for encounters.

The service owns the rules (id generation, timestamps, audit writes) and depends
only on repository interfaces, so it can be unit tested against fakes without a
web server or a real store. Every create and every read leaves an audit record.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from encounter_api.errors import EncounterNotFound
from encounter_api.models import (
    AuditAction,
    AuditEntry,
    Encounter,
    EncounterCreate,
    EncounterMetadata,
)
from encounter_api.repository import (
    AuditRepository,
    EncounterQuery,
    EncounterRepository,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class EncounterService:
    def __init__(self, encounters: EncounterRepository, audit: AuditRepository) -> None:
        self._encounters = encounters
        self._audit = audit

    def create_encounter(self, data: EncounterCreate, *, actor_id: str) -> Encounter:
        now = _now()
        encounter = Encounter(
            encounter_id=uuid4(),
            patient_id=data.patient_id,
            provider_id=data.provider_id,
            encounter_date=data.encounter_date,
            encounter_type=data.encounter_type,
            clinical_data=data.clinical_data,
            metadata=EncounterMetadata(created_at=now, updated_at=now, created_by=actor_id),
        )
        self._encounters.add(encounter)
        self._audit_access(AuditAction.CREATE, actor_id, encounter.encounter_id, now)
        logger.info(
            "encounter created",
            extra={"encounter_id": str(encounter.encounter_id), "actor_id": actor_id},
        )
        return encounter

    def get_encounter(self, encounter_id: UUID, *, actor_id: str) -> Encounter:
        encounter = self._encounters.get(encounter_id)
        if encounter is None:
            raise EncounterNotFound(encounter_id)
        self._audit_access(AuditAction.READ, actor_id, encounter_id, _now())
        return encounter

    def list_encounters(self, query: EncounterQuery, *, actor_id: str) -> list[Encounter]:
        results = self._encounters.find(query)
        self._audit_access(AuditAction.QUERY, actor_id, None, _now())
        return results

    def _audit_access(
        self,
        action: AuditAction,
        actor_id: str,
        encounter_id: UUID | None,
        when: datetime,
    ) -> None:
        self._audit.record(
            AuditEntry(
                audit_id=uuid4(),
                action=action,
                actor_id=actor_id,
                encounter_id=encounter_id,
                occurred_at=when,
            )
        )
