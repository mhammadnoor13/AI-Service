import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.application.use_cases.generate_case_draft import GenerateCaseDraftUseCase
from app.core.exceptions import ServiceUnavailable
from app.dependencies import get_generate_case_draft_use_case
from app.domain.models import CaseQuery, SolveCaseResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/draft-recommendation",
    response_model=SolveCaseResult,
    summary="Generate an AI-assisted draft recommendation for a case",
)
async def generate_draft_recommendation(
    case_query: CaseQuery,
    n: Optional[int] = Query(
        default=None,
        ge=1,
        le=5,
        description="Number of draft recommendations to generate.",
    ),
    x_user_id: UUID = Header(..., alias="X-User-Id"),
    use_case: GenerateCaseDraftUseCase = Depends(get_generate_case_draft_use_case),
) -> SolveCaseResult:
    """
    Generate AI-assisted draft recommendations for a case.

    The AI output is not final advice.
    It must be reviewed by a human consultant.
    """

    try:
        return await use_case.execute(
            query=case_query,
            consultant_id=x_user_id,
            n=n,
        )

    except ServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Unexpected error while generating draft recommendation")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from exc

