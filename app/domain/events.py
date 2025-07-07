from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.domain.models import Suggestion


class CaseAssignedEvent(BaseModel):
    caseId:       UUID
    consultantId: UUID

class CaseSolutionsGeneratedEvent(BaseModel):
    case_id: UUID
    solutions: List[Suggestion]