import logging

import httpx

from app.domain.models import AIDraft, CaseQuery, RetrievedContext
from app.domain.protocols import GenerationModel
from app.infrastructure.generation.response_parser import LLMResponseParser
from app.infrastructure.prompts.consultant_prompt_builder import ConsultantPromptBuilder

logger = logging.getLogger(__name__)


class OpenAICompatibleGenerationModel(GenerationModel):
    """
    Generation model implementation for OpenAI-compatible chat APIs.

    This keeps the AI Service provider-replaceable.
    It can work with local or hosted providers as long as they expose
    /chat/completions with OpenAI-style request/response format.
    """

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str | None = None,
        timeout: int = 120,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        prompt_builder: ConsultantPromptBuilder | None = None,
        response_parser: LLMResponseParser | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._api_key = api_key
        self._timeout = timeout
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._prompt_builder = prompt_builder or ConsultantPromptBuilder()
        self._response_parser = response_parser or LLMResponseParser()

    async def generate_draft(
        self,
        query: CaseQuery,
        contexts: list[RetrievedContext],
        n: int,
    ) -> AIDraft:
        messages = self._prompt_builder.build_messages(
            query=query,
            contexts=contexts,
            n=n,
        )

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "response_format": {
                "type": "json_object"
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code >= 400:
                logger.error(
                    "Generation provider error status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                response.raise_for_status()

            data = response.json()

        content = data["choices"][0]["message"]["content"]

        logger.info("Received generation response from model=%s", self._model_name)

        return self._response_parser.parse_ai_draft(content)