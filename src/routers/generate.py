"""Claim generation endpoint.

POST /generate/claims accepts source text and returns extracted claims
organized by topic. Delegates to ClaimGenerationService via dependency
injection. Exceptions propagate as HTTP errors automatically.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.dependencies import get_claim_generation_service
from src.schemas.requests import ClaimGenerationRequest
from src.schemas.responses import ClaimGenerationResponse, ErrorResponse
from src.services.claim_generation import ClaimGenerationService

router = APIRouter(tags=["generate"])


@router.post(
    "/generate/claims",
    response_model=ClaimGenerationResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def generate_claims(
    body: ClaimGenerationRequest,
    service: Annotated[ClaimGenerationService, Depends(get_claim_generation_service)],
) -> ClaimGenerationResponse:
    """Extract topic-organized claims from source text.

    Accepts raw text and returns a flat list of claim-topic pairs.
    Validation errors return 422, extraction failures return 502.
    """
    return await service.generate_claims(body.source_text)
