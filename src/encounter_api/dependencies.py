"""FastAPI dependency providers.

Services are built once at startup and held on ``app.state``. Routes ask for
them through these providers, which keeps handlers free of construction logic
and lets tests swap implementations with ``app.dependency_overrides``.
"""

from typing import Annotated

from fastapi import Depends, Request

from encounter_api.service import EncounterService


def get_encounter_service(request: Request) -> EncounterService:
    return request.app.state.encounter_service


EncounterServiceDep = Annotated[EncounterService, Depends(get_encounter_service)]
