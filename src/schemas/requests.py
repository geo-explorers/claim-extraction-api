"""API request models."""

from pydantic import BaseModel, Field


class ClaimGenerationRequest(BaseModel):
    """Request body for claim generation endpoint."""

    source_text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="Source text to extract claims from (50-50,000 characters)",
    )
