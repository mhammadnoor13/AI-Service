import logging
from uuid import UUID

import httpx

from app.domain.models import CaseQuery, RetrievedContext
from app.domain.protocols import SimilaritySearchClient

logger = logging.getLogger(__name__)


class EmbeddingServiceClient(SimilaritySearchClient):
    """
    HTTP client for the Embedding Service.

    The AI Service uses this client only for similarity search.
    It does not store vectors, chunk PDFs, or manage embeddings.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 120,
        token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token = token

    async def search(
        self,
        query: CaseQuery,
        consultant_id: UUID,
    ) -> list[RetrievedContext]:
        url = f"{self._base_url}/embedding/similarity-search"

        payload = {
            "query": query.text,
            "k": query.k,
            "scope": "both",
            "min_similarity": query.min_similarity,
        }

        headers = {
            "X-User-Id": str(consultant_id),
        }

        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])

        contexts: list[RetrievedContext] = []

        for item in results:
            contexts.append(
                RetrievedContext(
                    id=item["id"],
                    source=item["source"],
                    raw_text=item["raw_text"],
                    pdf_id=item.get("pdf_id"),
                    similarity=item["similarity"],
                )
            )

        logger.info("Embedding Service returned %s context chunks", len(contexts))

        return contexts