"""Gemini structured output schemas.

These are the Pydantic models used as response_schema for Gemini API calls.
They define what Gemini returns, NOT what the API returns to clients.
"""

from pydantic import BaseModel, Field


class TopicResult(BaseModel):
    """Gemini response schema for topic extraction (Step 1)."""

    topics: list[str] = Field(
        description=(
            "List of concise, descriptive topic labels (3-10 words) "
            "extracted from source text in order of appearance."
        )
    )


class ClaimWithTopicBaseResult(BaseModel):
    """A single topic with its extracted claims."""

    topic: str = Field(description="Topic label from the provided list")
    claims: list[str] = Field(
        description=(
            "List of factual, self-contained, atomic claims "
            "(5-32 words each) under this topic."
        )
    )


class ClaimWithTopicResult(BaseModel):
    """Gemini response schema for claim extraction (Step 2)."""

    claim_topics: list[ClaimWithTopicBaseResult] = Field(
        description="Claims organized by topic."
    )
