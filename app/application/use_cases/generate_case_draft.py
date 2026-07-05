import logging
from uuid import UUID

from app.core.exceptions import ServiceUnavailable
from app.domain.models import (
    AIDraft,
    CaseQuery,
    RetrievedContext,
    SolveCaseResult,
    UsedContext,
)
from app.domain.protocols import GenerationModel, SimilaritySearchClient

logger = logging.getLogger(__name__)


class GenerateCaseDraftUseCase:
    """
    Application use case responsible for generating an AI-assisted draft
    recommendation for a submitted case.

    It orchestrates:
    - retrieval from the Embedding Service
    - generation through a replaceable generation model
    - formatting the result for the consultant

    It does not make final decisions.
    """

    def __init__(
        self,
        similarity_search_client: SimilaritySearchClient,
        generation_model: GenerationModel,
        default_suggestion_count: int = 3,
    ) -> None:
        self._similarity_search_client = similarity_search_client
        self._generation_model = generation_model
        self._default_suggestion_count = default_suggestion_count

    async def execute(
        self,
        query: CaseQuery,
        consultant_id: UUID,
        n: int | None = None,
    ) -> SolveCaseResult:
        suggestion_count = n or self._default_suggestion_count

        try:
            contexts = await self._similarity_search_client.search(
                query=query,
                consultant_id=consultant_id,
            )

            logger.info(
                "Retrieved %s context chunks for consultant_id=%s",
                len(contexts),
                consultant_id,
            )

        except Exception as exc:
            logger.exception("Similarity search failed")
            raise ServiceUnavailable(f"Similarity search failed: {exc}") from exc

        try:
            draft = await self._generation_model.generate_draft(
                query=query,
                contexts=contexts,
                n=suggestion_count,
            )

            draft = self._attach_used_context(draft, contexts)

            logger.info(
                "Generated AI draft with %s recommendations",
                len(draft.recommendations),
            )

        except Exception as exc:
            logger.exception("Draft generation failed")
            raise ServiceUnavailable(f"Draft generation failed: {exc}") from exc

        return SolveCaseResult(
            case_id=query.case_id,
            draft=draft,
        )

    def _attach_used_context(
        self,
        draft: AIDraft,
        contexts: list[RetrievedContext],
    ) -> AIDraft:
        used_context = [
            UsedContext(
                id=context.id,
                source=context.source,
                pdf_id=context.pdf_id,
                similarity=context.similarity,
                text_preview=self._preview(context.raw_text),
            )
            for context in contexts
        ]

        important_notes = list(draft.important_notes)

        human_review_note = (
            "This is an AI-generated draft and must be reviewed by a human consultant before being sent to the user."
        )

        if human_review_note not in important_notes:
            important_notes.append(human_review_note)

        return draft.model_copy(
            update={
                "used_context": used_context,
                "important_notes": important_notes,
            }
        )

    def _preview(self, text: str, max_length: int = 300) -> str:
        cleaned = " ".join(text.split())

        if len(cleaned) <= max_length:
            return cleaned

        return cleaned[:max_length].rstrip() + "..."