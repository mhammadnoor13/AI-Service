from fastapi.encoders import jsonable_encoder
import httpx
from app.domain.events import CaseSuggestions
from app.domain.protocols import CaseServiceClient


class HttpxCaseServiceClient(CaseServiceClient):
    def __init__(self, base_url:str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    async def post_case(self, payload:CaseSuggestions):
        json_body = jsonable_encoder({"suggestions": payload.suggestions})
        breakpoint()
        response = await self._client.post(
            f"cases/{payload.case_id}/add-suggestions",
            json = json_body,
        )
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()
    async def get_case(self, case_id):
        response = await self._client.get(f"cases/{case_id}")
        response.raise_for_status()
        return response.json()
    