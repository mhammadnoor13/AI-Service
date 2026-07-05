import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.domain.models import AIDraft, DraftRecommendation

logger = logging.getLogger(__name__)


class LLMResponseParser:
    """
    Parses LLM output into the AI Service domain model.

    The model is instructed to return JSON, but this parser is defensive
    because LLMs may still return markdown, text, or malformed JSON.
    """

    def parse_ai_draft(self, text: str) -> AIDraft:
        cleaned = self._clean_output(text)
        candidate = self._extract_json_candidate(cleaned)

        if candidate:
            parsed = self._try_parse_json(candidate)

            if parsed is not None:
                draft = self._try_build_ai_draft(parsed)

                if draft is not None:
                    return draft

        logger.warning("Falling back to plain-text AI draft parsing")

        return AIDraft(
            summary="The model returned an unstructured draft.",
            recommendations=[
                DraftRecommendation(
                    title="AI-generated draft",
                    content=cleaned,
                    reasoning="The response could not be parsed as structured JSON.",
                )
            ],
            missing_information=[],
            important_notes=[
                "The AI output could not be parsed as structured JSON and should be reviewed carefully."
            ],
        )

    def _clean_output(self, text: str) -> str:
        without_thinking = re.sub(
            r"<think>[\s\S]*?</think>\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return without_thinking.strip()

    def _extract_json_candidate(self, text: str) -> str | None:
        fenced_object = re.search(
            r"```json\s*(\{[\s\S]*?\})\s*```",
            text,
            flags=re.IGNORECASE,
        )

        if fenced_object:
            return fenced_object.group(1)

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        return None

    def _try_parse_json(self, candidate: str) -> Any | None:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON candidate")
            return None

    def _try_build_ai_draft(self, parsed: Any) -> AIDraft | None:
        try:
            if isinstance(parsed, dict):
                return AIDraft.model_validate(parsed)

            if isinstance(parsed, list):
                return AIDraft(
                    summary="Draft recommendations generated from retrieved context.",
                    recommendations=[
                        DraftRecommendation(
                            title=f"Recommendation {index}",
                            content=str(item),
                            reasoning=None,
                        )
                        for index, item in enumerate(parsed, start=1)
                    ],
                )

        except ValidationError:
            logger.warning("Parsed JSON does not match AIDraft schema")

        return None