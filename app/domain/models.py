from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CaseQuery(BaseModel):
    """
    Input used by the AI Service to generate a draft recommendation.

    The submitted case is treated as a query.
    It is not automatically stored as reusable knowledge.
    """

    case_id: Optional[UUID] = Field(
        default=None,
        description="Optional case identifier when the request is linked to a stored case.",
    )

    text: str = Field(
        ...,
        min_length=5,
        description="The user case description or question.",
    )

    k: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of context chunks to retrieve from the Embedding Service.",
    )

    min_similarity: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for retrieved context.",
    )

    speciality: Optional[str] = Field(
        default=None,
        description="Optional consultation speciality/category.",
    )

    language: str = Field(
        default="en",
        description="Preferred output language. Default is English.",
    )

    prompt_version: Optional[str] = Field(
        default=None,
        description="Optional prompt version for prompt testing/evaluation.",
    )

class RetrievedContext(BaseModel):
    """
    Context returned by the Embedding Service.
    """

    id: UUID
    source: Literal["text", "pdf"]
    raw_text: str
    pdf_id: Optional[UUID] = None
    similarity: float


class UsedContext(BaseModel):
    """
    Lightweight context information returned to the frontend/Consultant Service.
    Avoid returning very large chunks in the final AI response.
    """

    id: UUID
    source: Literal["text", "pdf"]
    pdf_id: Optional[UUID] = None
    similarity: float
    text_preview: str


class DraftRecommendation(BaseModel):
    """
    One AI-generated draft recommendation.

    This is not final advice. It must be reviewed by a consultant.
    """

    title: str
    content: str
    reasoning: Optional[str] = None


class AIDraft(BaseModel):
    """
    Structured AI draft shown to the consultant.
    """

    summary: str
    recommendations: List[DraftRecommendation]
    missing_information: List[str] = Field(default_factory=list)
    important_notes: List[str] = Field(default_factory=list)
    used_context: List[UsedContext] = Field(default_factory=list)


class SolveCaseResult(BaseModel):
    """
    Final response returned by the AI Service.
    """

    case_id: Optional[UUID] = None
    draft: AIDraft