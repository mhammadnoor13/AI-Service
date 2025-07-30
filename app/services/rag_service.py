import logging
from typing import List
from uuid import UUID
from app.domain.models import CaseQuery, Document, Suggestion, SolveCaseResult
from app.services.retrieval import RetrievalStrategy
from app.services.generation import GenerationStrategy
from app.core.exceptions import ServiceUnavailable
logger = logging.getLogger(__name__)

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
        consultant_id: UUID,       
        n: int = None,
    ) -> SolveCaseResult: 
        
        n_suggestions = n or case_query.k

        # TODO Query Translation
        for pp in self._pre_processors:
            case_query = await pp.run(case_query)

        try:
            docs: List[Document] = await self._retrieval.retrieve(case_query, consultant_id)
            logger.info(f"📄 Retrieved {len(docs)} documents for consultant_id={consultant_id}")

        except Exception as e:
            raise ServiceUnavailable(f"Retrieval failed: {e}")

        try:

            suggestions: List[Suggestion] = await self._generation.generate(
                case_query.text,
                [doc.dict() for doc in docs],  
                n_suggestions
            )
            logger.info(f"✅ Generated {len(suggestions)} suggestions for query.")
        except Exception as e:
            raise ServiceUnavailable(f"Generation failed: {e}")

        return SolveCaseResult(suggestions=suggestions)
