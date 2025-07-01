from abc import ABC, abstractmethod
import json
import re
from typing import Dict, List

from fastapi import logger

from app.clients.llm_client import LLMClient
from app.domain.models import Suggestion

_PROMPT_TEMPLATE = """
SYSTEM:
You are an expert consultant. Using the following context documents, generate {{n}} distinct solution suggestions.

CONTEXT:
{{#each docs}}
— {{this.snippet}}
{{/each}}

INSTRUCTION:
Case: {{query}}

FORMAT:
Return a JSON array of plain-text suggestions.
"""


class GenerationStrategy(ABC):
    @abstractmethod
    async def generate(
        self, query: str, docs: List[Dict[str,str]], n: int
    ) -> List[Suggestion]:
        ...

class LlamaGeneration(GenerationStrategy):

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_template: str = _PROMPT_TEMPLATE,
        ) -> None:
            self._client = llm_client
            self._template = prompt_template
    
    async def generate(
        self, query:str, docs: List[Dict[str,str]], n: int
    ) -> List[Suggestion]:
        
        system_msg = {
            "role": "system",
            "content": "You are a knowledgeable consultant."
        }
        docs_snippet = "\n".join(f"— {d['snippet']}" for d in docs)
        user_content = (
            f"CONTEXT:\n{docs_snippet}\n\n"
            f"Case: {query}\n\n"
            f"Please generate {n} distinct solution suggestions.\n"
            f"Return them as a JSON array of strings."
        )
        user_msg = {"role": "user", "content": user_content}
        print([system_msg,user_msg])
        resp = await self._client.chat([system_msg, user_msg])
        breakpoint

        text = resp["choices"][0]["message"]["content"]
        m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1)
        else:
            # 2. Fallback: try to find the first “[” and last “]”
            start = text.find("[")
            end   = text.rfind("]") + 1
            candidate = text[start:end] if start != -1 and end != -1 else text
        try:

            suggestions = json.loads(candidate)

            if isinstance(suggestions, list) and all(isinstance(i, str) for i in suggestions):
                return [Suggestion(text=i) for i in suggestions]
        except json.JSONDecodeError:
            logger.warning("JSON parse failed on candidate: %r", candidate)
            pass
        return [Suggestion(text=text.strip())]
