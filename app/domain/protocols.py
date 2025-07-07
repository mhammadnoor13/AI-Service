from abc import ABC, abstractmethod
from typing import Dict
from uuid import UUID
from app.domain.events import CaseSolutionsGeneratedEvent


class CaseServiceClient(ABC):
    @abstractmethod
    async def get_case(self, case_id: UUID) -> Dict:
        """
        Fetch case details (e.g. description) from the CaseService API.
        Returns the raw JSON as a dict.
        """

class EventPublisher(ABC):
    @abstractmethod
    async def publish_solutions(self, evt:CaseSolutionsGeneratedEvent) -> None:
        """
        Publish CaseSolutionsGeneratedEvent to the message broker.
        """