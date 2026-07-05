from uuid import UUID

import httpx
from fastapi.encoders import jsonable_encoder

from app.domain.models import AIDraft
from app.domain.protocols import CaseServiceClient


class HttpxCaseServiceClient(CaseServiceClient):
    """
    HTTP client for communicating with the Case Service.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_case(self, case_id: UUID) -> dict:
        url = f"{self._base_url}/cases/{case_id}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def add_ai_draft(
        self,
        case_id: UUID,
        draft: AIDraft,
    ) -> None:
        url = f"{self._base_url}/cases/{case_id}/ai-draft"

        payload = jsonable_encoder(draft)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()