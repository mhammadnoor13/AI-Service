import httpx
from app.domain.protocols import CaseServiceClient


class HttpxCaseServiceClient(CaseServiceClient):
    def __init__(self, base_url:str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    async def get_case(self, case_id):

        response = await self._client.get(f"cases/{case_id}")
        response.raise_for_status()
        return response.json()