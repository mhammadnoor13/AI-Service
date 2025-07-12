# api/v1/solve_case.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.domain.models import CaseQuery, SolveCaseResult
from app.services.rag_service import RagService
from app.core.exceptions import ServiceUnavailable
from app.core.config import get_settings

router = APIRouter()


def get_rag_service() -> RagService:
    from app.main import rag_service
    return rag_service


@router.post(
    "/solve-case",
    response_model=SolveCaseResult,
    summary="Retrieve context docs and generate suggestions for a case",
)
async def solve_case(
    case_query: CaseQuery,
    n: Optional[int] = Query(
        None,
        ge=1,
        description="Number of suggestions to generate (defaults to k)",
    ),
    rag_service: RagService = Depends(get_rag_service),
) -> SolveCaseResult:
    """
    Given a case description and desired top-k,
    retrieve relevant documents and generate solution suggestions.
    """
    try:
        result = await rag_service.solve_case(case_query, n)
        return result
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
