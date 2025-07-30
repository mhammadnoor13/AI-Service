from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from app.clients.embedding_client import EmbeddingClient
from app.domain.models import CaseQuery, Document


class RetrievalStrategy(ABC):

    @abstractmethod
    async def retrieve(self, case_query: CaseQuery, consultant_id: UUID) -> List[Document]:
        ...

class EmbeddingRetrieval(RetrievalStrategy):
    def __init__(self, embedding_client: EmbeddingClient) -> None:
        self._client = embedding_client
    
    async def retrieve(self, case_query, consultant_id: UUID) -> List[Document]:
        return await self._client.retrieve(case_query, consultant_id)