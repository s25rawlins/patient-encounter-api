"""Storage interfaces and their in-memory implementations.

The service layer depends on the Protocols, never on a concrete store. The
in-memory versions back this demo; a Postgres-backed implementation would
satisfy the same Protocols and drop in without changing business logic.

Filtering is expressed as query value objects and pushed down to the store on
purpose. The in-memory version filters in Python, but the same shape maps
directly onto a SQL ``WHERE`` clause once a real database is behind it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from encounter_api.models import AuditEntry, Encounter


@dataclass(frozen=True, slots=True)
class EncounterQuery:
    patient_id: str | None = None
    provider_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuditQuery:
    actor_id: str | None = None
    encounter_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class EncounterRepository(Protocol):
    def add(self, encounter: Encounter) -> None: ...
    def get(self, encounter_id: UUID) -> Encounter | None: ...
    def find(self, query: EncounterQuery) -> list[Encounter]: ...


class AuditRepository(Protocol):
    def record(self, entry: AuditEntry) -> None: ...
    def find(self, query: AuditQuery) -> list[AuditEntry]: ...


class InMemoryEncounterRepository:
    def __init__(self) -> None:
        self._encounters: dict[UUID, Encounter] = {}

    def add(self, encounter: Encounter) -> None:
        self._encounters[encounter.encounter_id] = encounter

    def get(self, encounter_id: UUID) -> Encounter | None:
        return self._encounters.get(encounter_id)

    def find(self, query: EncounterQuery) -> list[Encounter]:
        matches = [e for e in self._encounters.values() if _encounter_matches(e, query)]
        matches.sort(key=lambda e: e.encounter_date)
        return matches


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    def find(self, query: AuditQuery) -> list[AuditEntry]:
        matches = [a for a in self._entries if _audit_matches(a, query)]
        matches.sort(key=lambda a: a.occurred_at)
        return matches


def _encounter_matches(encounter: Encounter, query: EncounterQuery) -> bool:
    if query.patient_id is not None and encounter.patient_id != query.patient_id:
        return False
    if query.provider_id is not None and encounter.provider_id != query.provider_id:
        return False
    if query.date_from is not None and encounter.encounter_date < query.date_from:
        return False
    if query.date_to is not None and encounter.encounter_date > query.date_to:
        return False
    return True


def _audit_matches(entry: AuditEntry, query: AuditQuery) -> bool:
    if query.actor_id is not None and entry.actor_id != query.actor_id:
        return False
    if query.encounter_id is not None and entry.encounter_id != query.encounter_id:
        return False
    if query.date_from is not None and entry.occurred_at < query.date_from:
        return False
    if query.date_to is not None and entry.occurred_at > query.date_to:
        return False
    return True
