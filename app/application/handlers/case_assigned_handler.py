import logging

from app.domain.events import CaseAssignedEvent, CaseDraftGeneratedEvent
from app.domain.models import CaseQuery
from app.domain.protocols import CaseServiceClient, EventPublisher
from app.application.use_cases.generate_case_draft import GenerateCaseDraftUseCase

logger = logging.getLogger(__name__)


class CaseAssignedHandler:
    """
    Handles CaseAssignedEvent.

    When a case is assigned to a consultant, the AI Service:
    - fetches the case details
    - generates an AI draft
    - sends the draft back to the case/consultant workflow
    - optionally publishes a draft-generated event
    """

    def __init__(
        self,
        case_client: CaseServiceClient,
        generate_case_draft_use_case: GenerateCaseDraftUseCase,
        publisher: EventPublisher | None = None,
    ) -> None:
        self._case_client = case_client
        self._generate_case_draft_use_case = generate_case_draft_use_case
        self._publisher = publisher

    async def handle(self, event: CaseAssignedEvent) -> None:
        case_data = await self._case_client.get_case(event.case_id)

        case_text = self._extract_case_text(case_data)

        query = CaseQuery(
            case_id=event.case_id,
            text=case_text,
            k=10,
            min_similarity=0.7,
            speciality=case_data.get("speciality"),
            language=case_data.get("language", "en"),
            prompt_version=case_data.get("prompt_version"),
        )

        result = await self._generate_case_draft_use_case.execute(
            query=query,
            consultant_id=event.consultant_id,
            n=3,
        )

        await self._case_client.add_ai_draft(
            case_id=event.case_id,
            draft=result.draft,
        )

        if self._publisher is not None:
            await self._publisher.publish_case_draft_generated(
                CaseDraftGeneratedEvent(
                    case_id=event.case_id,
                    consultant_id=event.consultant_id,
                    recommendations=result.draft.recommendations,
                )
            )

        logger.info(
            "AI draft generated for case_id=%s and consultant_id=%s",
            event.case_id,
            event.consultant_id,
        )

    def _extract_case_text(self, case_data: dict) -> str:
        case_text = (
            case_data.get("description")
            or case_data.get("text")
            or case_data.get("caseText")
        )

        if not case_text:
            raise ValueError("Case data does not contain a valid case description")

        return case_text