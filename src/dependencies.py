"""FastAPI dependency injection for service instances.

Provides configured service instances to route handlers via FastAPI's
Depends() mechanism. All instances are created during app lifespan and
stored on app.state for singleton behavior.
"""

from fastapi import HTTPException, Request, status

from src.services.claim_generation import ClaimGenerationService


def get_claim_generation_service(request: Request) -> ClaimGenerationService:
    """Retrieve the ClaimGenerationService from app state.

    The service is constructed during the app lifespan (see main.py)
    with all dependencies (extractors, Gemini client) already wired.

    Raises:
        HTTPException: 503 if Gemini API key is not configured.
    """
    service: ClaimGenerationService | None = getattr(
        request.app.state, "claim_generation_service", None
    )
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
        )
    return service
