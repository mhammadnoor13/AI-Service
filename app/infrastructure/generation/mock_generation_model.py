from app.domain.models import AIDraft, CaseQuery, DraftRecommendation, RetrievedContext
from app.domain.protocols import GenerationModel


class MockGenerationModel(GenerationModel):
    """
    Simple generation model for local development and tests.

    It does not call any external API.
    """

    async def generate_draft(
        self,
        query: CaseQuery,
        contexts: list[RetrievedContext],
        n: int,
    ) -> AIDraft:
        recommendations = [
            DraftRecommendation(
                title=f"Draft recommendation {index}",
                content=(
                    f"This is a mock draft recommendation for the case: "
                    f"{query.text[:120]}..."
                ),
                reasoning=(
                    "This mock recommendation is generated without calling an external model."
                ),
            )
            for index in range(1, n + 1)
        ]

        return AIDraft(
            summary="Mock summary of the submitted case.",
            recommendations=recommendations,
            missing_information=[
                "More case-specific details may be needed before giving final advice."
            ],
            important_notes=[
                "This is mock AI output for development only."
            ],
        )