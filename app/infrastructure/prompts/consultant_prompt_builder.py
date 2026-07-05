from app.domain.models import CaseQuery, RetrievedContext


class ConsultantPromptBuilder:
    """
    Builds prompts for consultant-facing draft generation.

    This class is intentionally separated from the LLM client so that
    prompt versions can be evaluated or replaced later.
    """

    def build_messages(
        self,
        query: CaseQuery,
        contexts: list[RetrievedContext],
        n: int,
    ) -> list[dict[str, str]]:
        prompt_version = query.prompt_version or "default_v1"
        speciality = query.speciality or "general consultation"
        language = query.language or "en"

        context_block = self._build_context_block(contexts)

        system_message = self._build_system_message(
            speciality=speciality,
            language=language,
            prompt_version=prompt_version,
        )

        user_message = f"""
CASE:
{query.text}

SPECIALITY:
{speciality}

RETRIEVED CONTEXT:
{context_block}

TASK:
Generate {n} draft recommendation(s) for a human consultant.

OUTPUT FORMAT:
Return only valid JSON.
Do not use markdown.
Do not wrap the JSON in triple backticks.
Do not add any explanation before or after the JSON.

The JSON must match this exact structure:

{{
  "summary": "Short neutral summary of the case.",
  "recommendations": [
    {{
      "title": "Short recommendation title",
      "content": "Draft recommendation content.",
      "reasoning": "Brief explanation of why this recommendation may be relevant."
    }}
  ],
  "missing_information": [
    "Important missing information the consultant may need."
  ],
  "important_notes": [
    "Important caution or limitation."
  ]
}}

STRICT JSON RULES:
- Use double quotes for all strings.
- Put a comma between every object field.
- Put a comma between every array item.
- Do not use trailing commas.
- Do not include comments.
- Do not include markdown.
- The number of recommendation objects must be exactly {n}.

CONTENT RULES:
- Do not make a final decision.
- Do not claim certainty when the context is insufficient.
- Do not invent facts that are not in the case or retrieved context.
- Keep the human consultant responsible for the final advice.
- Write the output in language code: {language}.
""".strip()

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def _build_system_message(
        self,
        speciality: str,
        language: str,
        prompt_version: str,
    ) -> str:
        return f"""
You are an AI assistant helping a human consultant prepare draft recommendations.

You are not the final decision-maker.
You must support the consultant by summarizing the case, using relevant retrieved context, and proposing possible draft recommendations.

Consultation speciality: {speciality}
Output language: {language}
Prompt version: {prompt_version}

Return structured JSON only.
Do not include markdown.
Do not include chain-of-thought.
""".strip()

    def _build_context_block(self, contexts: list[RetrievedContext]) -> str:
        if not contexts:
            return "No retrieved context was found."

        blocks = []

        for index, context in enumerate(contexts, start=1):
            blocks.append(
                f"[{index}] "
                f"source={context.source}, "
                f"similarity={context.similarity:.3f}\n"
                f"{context.raw_text}"
            )

        return "\n\n".join(blocks)