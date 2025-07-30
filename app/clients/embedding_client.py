from typing import List
from uuid import UUID
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
    
    async def retrieve(self, case_query: CaseQuery, consultant_id: UUID) -> List[Document]:
        
        url = f"{self._base_url}/get-similar"

        payload: dict = {
            "query":case_query.text,
            "k": case_query.k,
            "scope": "both"
        }
        headers = {
            "X-User-Id": str(consultant_id) 
        }



        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url,json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        docs = []
        for item in data.get("documents",[]):
            docs.append(Document(id=item["id"], snippet = item["snippet"]))
        return docs
            
