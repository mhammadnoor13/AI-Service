from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.domain.models import DraftRecommendation


class CaseAssignedEvent(BaseModel):
    """
    Event consumed by the AI Service when a case is assigned to a consultant.
    """

    model_config = ConfigDict(populate_by_name=True)

    case_id: UUID = Field(alias="caseId")
    consultant_id: UUID = Field(alias="consultantId")


class CaseDraftGeneratedEvent(BaseModel):
    """
    Event published by the AI Service after generating draft recommendations.
    """

    case_id: UUID
    consultant_id: UUID
    recommendations: List[DraftRecommendation]