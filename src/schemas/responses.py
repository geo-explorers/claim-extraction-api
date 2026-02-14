"""API response models."""

from pydantic import BaseModel


class ClaimResponse(BaseModel):
    """A single extracted claim with its topic."""

    claim_topic: str
    claim: str


class ClaimGenerationResponse(BaseModel):
    """Response body for claim generation endpoint."""

    claims: list[ClaimResponse]


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
