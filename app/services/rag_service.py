# services/rag_service.py

from typing import List
from app.domain.models import CaseQuery, Document, Suggestion, SolveCaseResult
from app.services.retrieval import RetrievalStrategy
from app.services.generation import GenerationStrategy
from app.core.exceptions import ServiceUnavailable


class RagService:
    """
    Orchestrates the RAG pipeline:
      ── optional pre-processing (e.g. translation)
      ── document retrieval
      ── suggestion generation
    """

    def __init__(
        self,
        retrieval: RetrievalStrategy,
        generation: GenerationStrategy,
        pre_processors: List  = None,       
    ) -> None:
        self._retrieval      = retrieval
        self._generation     = generation
        self._pre_processors = pre_processors or []

    async def solve_case(
        self,
        case_query: CaseQuery,
        n: int = None,          
    ) -> SolveCaseResult:
        
        n_suggestions = n or case_query.k

        # TODO Query Translation
        for pp in self._pre_processors:
            case_query = await pp.run(case_query)

        try:
            docs: List[Document] = await self._retrieval.retrieve(case_query)
        except Exception as e:
            raise ServiceUnavailable(f"Retrieval failed: {e}")

        try:

            suggestions: List[Suggestion] = await self._generation.generate(
                case_query.text,
                [doc.dict() for doc in docs],  
                n_suggestions
            )
        except Exception as e:
            raise ServiceUnavailable(f"Generation failed: {e}")

        return SolveCaseResult(suggestions=suggestions)
