from typing import Any, Dict, List
import httpx
from app.core.config import get_settings


settings = get_settings()


class LLMClient:
    def __init__(self):
        self._base_url = settings.LLM_API_BASE
        self._model = settings.LLM_MODEL_NAME
        self._timeout = settings.REQUEST_TIMEOUT
        self._api_key = settings.LLM_API_KEY

    async def chat(self, messages: List[Dict[str,Any]]) -> Dict[str,Any]:
        """
        Send a chat-style conversation to the LLM and return the full JSON response.

        messages: a list of {"role": "system" | "user" | "assistant", "content": str}
        """
        prompt = "\n\n".join(m["content"] for m in messages)

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": messages
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()