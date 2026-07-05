from fastapi import Request

from app.application.use_cases.generate_case_draft import GenerateCaseDraftUseCase


def get_generate_case_draft_use_case(
    request: Request,
) -> GenerateCaseDraftUseCase:
    return request.app.state.generate_case_draft_use_case