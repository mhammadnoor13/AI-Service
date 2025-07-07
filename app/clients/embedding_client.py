from typing import List
import httpx
from app.core.config import get_settings
from app.domain.models import CaseQuery, Document


settings = get_settings()
class EmbeddingClient:
    '''
    Client to Call Embedding Service
    '''
    def __init__(self) -> None:
        self._base_url = settings.EMBEDDING_SERVICE_URL
        self._timeout = settings.REQUEST_TIMEOUT
    
    async def retrieve(self, case_query: CaseQuery) -> List[Document]:
        
        url = f"{self._base_url}/get-similar"

        payload: dict = {
            "raw_text":case_query.text,
            "top_k": case_query.k
        }

        if case_query.consultant_id:
            payload["consultant_id"] = case_query.consultant_id
        if case_query.speciality:
            payload["speciality"] = case_query.speciality

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url,json=payload)
            resp.raise_for_status()
            data = resp.json()
        docs = []
        for item in data.get("documents",[]):
            docs.append(Document(id=item["id"], snippet = item["snippet"]))
        return docs
            
