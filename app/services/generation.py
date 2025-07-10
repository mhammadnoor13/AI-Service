from abc import ABC, abstractmethod
import json
import re
from typing import Dict, List

from fastapi import logger

from app.clients.llm_client import LLMClient
from app.domain.models import Suggestion

import requests
from dataclasses import dataclass
from typing import List, Dict
from groq import Groq

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
        #TODO Remove
        n = 1
        user_content = (
            f"CONTEXT:\n{docs_snippet}\n\n"
            f"Case: {query}\n\n"
            f"Please generate {n} distinct solution suggestions.\n"
            f"Return them as a JSON array of strings."
        )
        user_msg = {"role": "user", "content": user_content}
        print([system_msg,user_msg])
        resp = await self._client.chat([system_msg, user_msg])

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

        print("----> This Break Point")
        return [Suggestion(text=text.strip())]



@dataclass
class APIGenerator(GenerationStrategy):
    api_key: str
    model_name: str
    system_prompt: str = (
        "You are a careful medical assistant. "
        "Use ONLY the provided CONTEXT to answer, citing sources as [1], [2] …"
    )
    temperature: float = 0.2
    max_tokens: int = 512
    stream: bool = False

    def _build_prompt(self, question: str, contexts: List[str]) -> List[Dict]:
        numbered = [f"[{i+1}] {c}" for i, c in enumerate(contexts)]
        context_block = "\n\n".join(numbered)
        user_block = f"CONTEXT:\n{context_block}\n\nQUESTION:\n{question}\n\nANSWER:"
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": user_block},
        ]

    def generate(self, question: str, contexts: List[Dict[str,str]]) -> str:
        client = Groq(api_key=self.api_key)
        snippets = contexts['snippet']
        completion = client.chat.completions.create(
            model      = self.model_name,
            messages   = self._build_prompt(question, snippets),
            temperature= self.temperature,
            max_completion_tokens = self.max_tokens,
            top_p      = 0.95,
            stream     = self.stream,
        )

        if self.stream:
            parts = (
                chunk.choices[0].delta.content
                for chunk in completion
                if chunk.choices[0].delta.content
            )
            return "".join(parts).strip()
        else:
            return completion.choices[0].message.content.strip()
