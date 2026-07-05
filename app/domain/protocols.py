from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.events import CaseDraftGeneratedEvent
from app.domain.models import AIDraft, CaseQuery, RetrievedContext


class CaseServiceClient(ABC):
    @abstractmethod
    async def get_case(self, case_id: UUID) -> dict:
        """
        Fetch case details from the Case Service.
        """
        pass

    @abstractmethod
    async def add_ai_draft(self, case_id: UUID, draft: AIDraft) -> None:
        """
        Send the generated AI draft back to the Case Service or Consultant Service.
        """
        pass


class SimilaritySearchClient(ABC):
    @abstractmethod
    async def search(
        self,
        query: CaseQuery,
        consultant_id: UUID,
    ) -> list[RetrievedContext]:
        """
        Retrieve relevant context from the Embedding Service.
        """
        pass


class GenerationModel(ABC):
    @abstractmethod
    async def generate_draft(
        self,
        query: CaseQuery,
        contexts: list[RetrievedContext],
        n: int,
    ) -> AIDraft:
        """
        Generate a structured AI draft using the case query and retrieved context.
        """
        pass


class EventPublisher(ABC):
    @abstractmethod
    async def publish_case_draft_generated(
        self,
        event: CaseDraftGeneratedEvent,
    ) -> None:
        """
        Publish an event after AI draft generation.
        """
        pass